# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Offline regression for original Excel assets; use --basetemp under TMPDIR."""
import errno
from hashlib import sha256
import importlib.util
import inspect
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from zipfile import ZipFile

from lxml import etree
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.workbook.defined_name import DefinedName
import pytest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'skills/office-white-collar/xlsx'
EXAMPLES = BASE / 'references/openpyxl-examples'
S = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG = 'http://schemas.openxmlformats.org/package/2006/relationships'


def module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture
def creator():
    return module(BASE / 'scripts/create_formatted_excel.py')


@pytest.fixture
def parser():
    return module(BASE / 'scripts/parse_complex_excel.py')


def run(path, *args, cwd=None):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    return subprocess.run([sys.executable, str(path), *map(str, args)],
                          cwd=cwd, env=env, text=True, capture_output=True, timeout=30)


def synthetic(path):
    """Real OOXML fixture: merges, typed caches, names, relocated sheet, external cache."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Ops' North"
    ws.merge_cells('A1:B1')
    ws['A1'] = 'Synthetic fixture'
    ws['A2'], ws['B2'] = 0, False
    for ref, formula in [('A3', '=1-1'), ('B3', '=FALSE()'), ('C3', '=1/0'),
                         ('D3', '="cached"'), ('E3', '=5*2')]:
        ws[ref] = formula
    ws['A3'].number_format = '#,##0.00'
    ws['A3'].font = Font(bold=True, color='17365D')
    wb.create_sheet('#REF! literal')
    for name, ref in [
        ('LegalRange', "'Ops'' North'!$A$2:$B$3"),
        ('Literal', '"#REF!"'), ('Constant', '0.125'),
        ('LiteralSheet', "'#REF! literal'!$A$1"),
        ('Dynamic', 'OFFSET(\'Ops\'\' North\'!$A$1,0,0,2,1)'),
        ('External', '[1]Remote!$A$1'), ('Broken', '#REF!'),
        ('MissingSheet', "'Gone'!$A$1"), ('TooWide', "'Ops'' North'!$XFE$1"),
    ]:
        wb.defined_names.add(DefinedName(name, attr_text=ref))
    ws.defined_names.add(DefinedName('LocalValid', attr_text="$A$2", localSheetId=0))
    wb.save(path)
    with ZipFile(path) as zf:
        content = {info.filename: zf.read(info.filename) for info in zf.infolist()}
    root = etree.fromstring(content['xl/worksheets/sheet1.xml'])
    for ref, kind, value in [('A3', 'n', '0'), ('B3', 'b', '0'),
                             ('C3', 'e', '#DIV/0!'), ('D3', 'str', 'cached')]:
        cell = root.find(f'{{{S}}}sheetData/{{{S}}}row/{{{S}}}c[@r="{ref}"]')
        cell.set('t', kind)
        cell.find(f'{{{S}}}v').text = value
    content['xl/worksheets/shifted.xml'] = etree.tostring(root)
    del content['xl/worksheets/sheet1.xml']
    content['xl/_rels/workbook.xml.rels'] = content['xl/_rels/workbook.xml.rels'].replace(
        b'/xl/worksheets/sheet1.xml', b'/xl/worksheets/shifted.xml')
    content['[Content_Types].xml'] = content['[Content_Types].xml'].replace(
        b'/xl/worksheets/sheet1.xml', b'/xl/worksheets/shifted.xml')
    workbook = etree.fromstring(content['xl/workbook.xml'])
    external = etree.SubElement(workbook, f'{{{S}}}externalReferences')
    etree.SubElement(external, f'{{{S}}}externalReference', {f'{{{R}}}id': 'rExternal'})
    content['xl/workbook.xml'] = etree.tostring(workbook)
    rels = etree.fromstring(content['xl/_rels/workbook.xml.rels'])
    etree.SubElement(rels, f'{{{PKG}}}Relationship', Id='rExternal',
                     Type=R + '/externalLink', Target='externalLinks/externalLink1.xml')
    content['xl/_rels/workbook.xml.rels'] = etree.tostring(rels)
    content['xl/externalLinks/externalLink1.xml'] = (
        f'<externalLink xmlns="{S}" xmlns:r="{R}"><externalBook r:id="rId1">'
        '<sheetNames><sheetName val="Remote"/></sheetNames><sheetDataSet>'
        '<sheetData sheetId="0"><row r="1"><cell r="A1" t="n"><v>42</v>'
        '</cell></row></sheetData></sheetDataSet></externalBook></externalLink>').encode()
    content['xl/externalLinks/_rels/externalLink1.xml.rels'] = (
        f'<Relationships xmlns="{PKG}"><Relationship Id="rId1" '
        f'Type="{R}/externalLinkPath" TargetMode="External" '
        'Target="https://example.invalid/never-open.xlsx"/></Relationships>').encode()
    types = etree.fromstring(content['[Content_Types].xml'])
    etree.SubElement(types, '{http://schemas.openxmlformats.org/package/2006/content-types}Override',
                     PartName='/xl/externalLinks/externalLink1.xml',
                     ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.externalLink+xml')
    content['[Content_Types].xml'] = etree.tostring(types)
    with ZipFile(path, 'w') as zf:
        for name, data in content.items():
            zf.writestr(name, data)
    return path


def rewrite_parts(path, edit):
    with ZipFile(path) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    edit(parts)
    with ZipFile(path, 'w') as archive:
        for name, data in parts.items():
            archive.writestr(name, data)


def test_interface_fact_signatures_present(creator, parser):
    expected = {
        creator: {'apply_header_row': ['ws', 'row', 'labels', 'start_col'],
                  'apply_data_row': ['ws', 'row', 'values', 'start_col', 'font', 'number_format', 'fill', 'border'],
                  'apply_input_cell': ['ws', 'row', 'col', 'value', 'number_format'],
                  'add_sensitivity_table': ['ws', 'start_row', 'start_col', 'row_header', 'col_header', 'row_values', 'col_values', 'data_matrix'],
                  'auto_column_widths': ['ws', 'min_width', 'max_width'],
                  'create_example_workbook': ['output_path']},
        parser: {'verify_format': ['file_path'], 'list_sheets': ['zf'],
                 'get_sheet_path': ['zf', 'sheet_name'], 'build_shared_strings': ['zf'],
                 'parse_cell_ref': ['ref'], 'extract_cells': ['zf', 'sheet_path', 'shared'],
                 'extract_rows': ['cells', 'start_row', 'end_row'],
                 'fix_defined_names': ['input_path', 'output_path']},
    }
    for mod, functions in expected.items():
        for name, args in functions.items():
            assert list(inspect.signature(getattr(mod, name)).parameters) == args


def test_helpers_keep_missing_values_and_reject_shape_before_edit(creator):
    ws = Workbook().active
    creator.apply_header_row(ws, 1, ['Assumption', 'Value'])
    creator.apply_data_row(ws, 2, ['Revenue', None], font=Font(italic=True),
                           fill=PatternFill('solid', fgColor='FFFF00'), number_format='0.00')
    creator.apply_input_cell(ws, 3, 2, 0.125, '0.0%')
    assert ws['B2'].value is None and ws['B2'].font.italic
    assert ws['B3'].number_format == '0.0%'
    before = list(ws.values)
    with pytest.raises(ValueError, match='dimensions'):
        creator.add_sensitivity_table(ws, 5, 1, 'Rate', 'Growth', [0.1], [0.02, 0.03], [[10]])
    assert list(ws.values) == before
    creator.add_sensitivity_table(ws, 5, 1, 'Rate', 'Growth', [0.1], [0.02, 0.03], [[None, '=2+3']])
    assert ws['B6'].value is None and ws['C6'].value == '=2+3'
    creator.auto_column_widths(ws, 8, 28)
    assert 8 <= ws.column_dimensions['A'].width <= 28


def test_financial_model_reopens_with_styles_and_uncalculated_formulas(creator, tmp_path):
    path = tmp_path / 'finance.xlsx'
    creator.create_example_workbook(path)
    wb = load_workbook(path, data_only=False)
    try:
        assert wb['Financial Model']['B4'].value == 1200
        assert wb['Financial Model']['B3'].font.bold
        assert wb['Financial Model']['B10'].value == '=B8-B9'
        assert wb['DCF']['B8'].value == '=IF(B2>B3,B6*(1+B3)/(B2-B3),NA())'
        assert '$A2>B$1' in wb['Sensitivity']['B2'].value
        assert wb['DCF']['B2'].number_format == creator.PERCENT
        assert wb.calculation.fullCalcOnLoad
    finally:
        wb.close()
    wb = load_workbook(path, data_only=True)
    assert wb['DCF']['B9'].value is None
    wb.close()


def test_financial_cli_publishes_one_explicit_output(tmp_path):
    output = tmp_path / 'cli-financial.xlsx'
    result = run(BASE / 'scripts/create_formatted_excel.py', output, cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines().count(str(output)) == 1
    assert 'not been recalculated' in result.stdout
    wb = load_workbook(output)
    assert wb['Financial Model']['B4'].value == 1200
    assert wb['Sensitivity']['C3'].value.startswith('=IF($A3>C$1,')
    wb.close()


@pytest.mark.parametrize('script,sheet,ref,expected', [
    ('create_basic_spreadsheet.py', 'Inventory', 'D4', '=SUM(D2:D3)'),
    ('styling_spreadsheet.py', 'Sales', 'C3', 0.18),
    ('create_spreadsheet_with_styling.py', 'Game Results', 'D2', '=SUM(B2:C2)'),
])
def test_writer_examples_real_cli(script, sheet, ref, expected, tmp_path):
    output = tmp_path / script.replace('.py', '.xlsx')
    result = run(EXAMPLES / script, '--output', output, cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert str(output) in result.stdout
    wb = load_workbook(output)
    try:
        assert wb[sheet][ref].value == expected
        if sheet == 'Inventory':
            assert wb[sheet]['D2'].number_format == '#,##0.00'
        elif sheet == 'Sales':
            assert wb[sheet]['A2'].font.bold
            assert len(wb[sheet].conditional_formatting) == 1
        else:
            assert wb[sheet]['D2'].font.bold and wb[sheet]['D2'].font.italic
    finally:
        wb.close()


def test_all_modules_import_without_writing(tmp_path):
    paths = [BASE / 'scripts/create_formatted_excel.py', BASE / 'scripts/parse_complex_excel.py',
             *EXAMPLES.glob('*.py')]
    before = set(tmp_path.iterdir())
    for path in paths:
        result = subprocess.run([sys.executable, '-B', '-c',
            'import runpy,sys; runpy.run_path(sys.argv[1], run_name="import_check")', str(path)],
            cwd=tmp_path, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
    assert set(tmp_path.iterdir()) == before


def test_readonly_complex_parse_and_typed_caches(parser, tmp_path):
    source = synthetic(tmp_path / 'complex.xlsx')
    digest = sha256(source.read_bytes()).hexdigest()
    report = parser.inspect_workbook(source, "Ops' North", 2, 3)
    assert report['input_sha256'] == digest
    sheet = report['sheets'][0]
    assert sheet['path'] == 'xl/worksheets/shifted.xml'
    assert sheet['merged_ranges'] == ['A1:B1']
    cells = sheet['rows'][1]['cells']
    assert cells['A3']['formula'] == '=1-1' and cells['A3']['cached_value'] == 0
    assert cells['B3']['cached_value'] is False and cells['B3']['cache_status'] == 'present'
    assert cells['C3']['cached_value'] == '#DIV/0!'
    assert cells['D3']['cached_value'] == 'cached'
    assert cells['E3']['cached_value'] is None and cells['E3']['cache_status'] == 'missing'
    assert cells['A3']['number_format'] == '#,##0.00'
    assert sha256(source.read_bytes()).hexdigest() == digest
    assert parser.parse_cell_ref('$AA$12') == (12, 27)
    with pytest.raises(ValueError):
        parser.parse_cell_ref('XFE1')
    cli = run(BASE / 'scripts/parse_complex_excel.py', source, '--sheet', "Ops' North")
    assert cli.returncode == 0, cli.stderr
    assert json.loads(cli.stdout)['input_sha256'] == digest
    read = run(EXAMPLES / 'read_existing_spreadsheet.py', '--input', source)
    assert read.returncode == 0, read.stderr
    assert json.loads(read.stdout)['sha256'] == digest
    assert sha256(source.read_bytes()).hexdigest() == digest


def test_targeted_name_repair_preserves_all_other_parts(parser, tmp_path):
    source = synthetic(tmp_path / 'complex.xlsx')
    before = source.read_bytes()
    dest = tmp_path / 'repaired.xlsx'
    report = parser.fix_defined_names(source, dest)
    assert report['removed_count'] == 3
    actions = {row['name']: row for row in report['defined_names']}
    for name in ['LegalRange', 'Literal', 'Constant', 'LiteralSheet', 'Dynamic', 'External', 'LocalValid']:
        assert actions[name]['action'] == 'preserved', actions[name]
    for name in ['Broken', 'MissingSheet', 'TooWide']:
        assert actions[name]['action'] == 'removed' and actions[name]['problem']
    assert source.read_bytes() == before
    with ZipFile(source) as original, ZipFile(dest) as fixed:
        assert original.namelist() == fixed.namelist()
        for name in original.namelist():
            if name != 'xl/workbook.xml':
                assert original.read(name) == fixed.read(name), name
    wb = load_workbook(dest, data_only=False, keep_links=True)
    assert wb.defined_names['LegalRange'].attr_text == "'Ops'' North'!$A$2:$B$3"
    assert 'LocalValid' in wb["Ops' North"].defined_names
    assert wb["Ops' North"]['A3'].font.bold
    assert wb["Ops' North"]['A3'].value == '=1-1'
    wb.close()
    cached = load_workbook(dest, data_only=True, keep_links=True)
    assert cached["Ops' North"]['A3'].value == 0
    cached.close()
    cli = run(BASE / 'scripts/parse_complex_excel.py', source, '--repair', '--output', tmp_path / 'cli.xlsx')
    assert cli.returncode == 0, cli.stderr
    assert json.loads(cli.stdout)['removed_count'] == 3


def test_no_bad_names_preserves_workbook_xml_exactly(parser, tmp_path):
    source = tmp_path / 'legal.xlsx'
    wb = Workbook()
    wb.active['A1'] = 5
    wb.defined_names.add(DefinedName('Valid', attr_text="'Sheet'!$A$1"))
    wb.save(source)
    dest = tmp_path / 'legal-copy.xlsx'
    report = parser.fix_defined_names(source, dest)
    assert report['removed_count'] == 0
    with ZipFile(source) as before, ZipFile(dest) as after:
        for name in before.namelist():
            assert before.read(name) == after.read(name)


def test_repair_failures_and_validation_failure_preserve_evidence(parser, creator, tmp_path, monkeypatch):
    source = synthetic(tmp_path / 'complex.xlsx')
    before = source.read_bytes()
    with pytest.raises(ValueError, match='distinct output'):
        parser.fix_defined_names(source, source)
    old = tmp_path / 'old.xlsx'
    old.write_bytes(b'previous evidence')
    with pytest.raises(ValueError, match='Validation failed'):
        creator.save_verified_workbook(Workbook(), old, [('Sheet', 'A1', 'wrong')])
    assert old.read_bytes() == b'previous evidence'
    def fail_load(*args, **kwargs):
        raise ValueError('injected reopen failure')
    monkeypatch.setattr(parser, 'load_workbook', fail_load)
    with pytest.raises(ValueError, match='injected'):
        parser.fix_defined_names(source, old)
    assert old.read_bytes() == b'previous evidence' and source.read_bytes() == before
    def cross_device(*args):
        raise OSError(errno.EXDEV, 'injected cross-device publication')
    monkeypatch.setattr(creator.os, 'replace', cross_device)
    with pytest.raises(OSError, match='same filesystem'):
        creator.save_verified_workbook(Workbook(), old)
    assert old.read_bytes() == b'previous evidence'


def test_read_sample_and_documented_example_are_executable(tmp_path):
    read = run(EXAMPLES / 'read_existing_spreadsheet.py', cwd=tmp_path)
    assert read.returncode == 0, read.stderr
    report = json.loads(read.stdout)
    assert not Path(report['input']).exists()  # Temporary sample was cleaned.
    assert Path(report['input']).is_relative_to(Path(os.environ['TMPDIR']).resolve())
    doc = (BASE / 'references/excel-automation/formatting-reference.md').read_text()
    snippets = re.findall(r'```python\n(.*?)```', doc, re.S)
    assert snippets
    for snippet in snippets:
        script = tmp_path / 'format_demo.py'
        script.write_text(snippet)
        result = run(script, tmp_path / 'documented.xlsx', cwd=ROOT)
        assert result.returncode == 0, result.stderr


def test_empty_string_cache_is_present_but_empty_numeric_is_missing(parser, tmp_path):
    source = synthetic(tmp_path / 'empty-cache.xlsx')
    def edit(parts):
        root = etree.fromstring(parts['xl/worksheets/shifted.xml'])
        root.find(f'.//{{{S}}}c[@r="D3"]/{{{S}}}v').text = None
        parts['xl/worksheets/shifted.xml'] = etree.tostring(root)
    rewrite_parts(source, edit)
    before = source.read_bytes()
    rows = parser.inspect_workbook(source, "Ops' North", 3, 3)['sheets'][0]['rows']
    assert rows[0]['cells']['D3']['cached_value'] == ''
    assert rows[0]['cells']['D3']['cache_status'] == 'present'
    assert rows[0]['cells']['E3']['cache_status'] == 'missing'
    assert source.read_bytes() == before


def test_bad_local_scope_is_diagnosed_and_targeted_without_losing_good_scope(parser, tmp_path):
    source = synthetic(tmp_path / 'scope.xlsx')
    def edit(parts):
        root = etree.fromstring(parts['xl/workbook.xml'])
        names = root.find(f'{{{S}}}definedNames')
        for name, scope in [('BadScope', '99'), ('BadScopeType', 'text')]:
            node = etree.SubElement(names, f'{{{S}}}definedName', name=name, localSheetId=scope)
            node.text = "'Ops'' North'!$A$1"
        parts['xl/workbook.xml'] = etree.tostring(root)
    rewrite_parts(source, edit)
    before = source.read_bytes()
    diagnostics = parser.inspect_workbook(source)['defined_names']
    assert all(item['problem'].startswith('localSheetId')
               for item in diagnostics if item['name'].startswith('BadScope'))
    report = parser.fix_defined_names(source, tmp_path / 'scope-fixed.xlsx')
    assert report['removed_count'] == 5
    assert next(item for item in report['defined_names'] if item['name'] == 'LocalValid')['action'] == 'preserved'
    assert source.read_bytes() == before


def test_shared_strings_and_shared_formulas_decode_without_editing(parser, tmp_path):
    source = synthetic(tmp_path / 'shared.xlsx')
    def edit(parts):
        root = etree.fromstring(parts['xl/worksheets/shifted.xml'])
        data = root.find(f'{{{S}}}sheetData')
        for n, value in [(4, 2), (5, 4)]:
            row = etree.SubElement(data, f'{{{S}}}row', r=str(n))
            cell = etree.SubElement(row, f'{{{S}}}c', r=f'A{n}', t='n')
            etree.SubElement(cell, f'{{{S}}}v').text = str(value)
            formula = etree.SubElement(row, f'{{{S}}}c', r=f'B{n}')
            f = etree.SubElement(formula, f'{{{S}}}f', t='shared', si='0')
            if n == 4:
                f.set('ref', 'B4:B5')
                f.text = 'A4*3'
                text = etree.SubElement(row, f'{{{S}}}c', r='F4', t='s')
                etree.SubElement(text, f'{{{S}}}v').text = '0'
        parts['xl/worksheets/shifted.xml'] = etree.tostring(root)
        parts['xl/sharedStrings.xml'] = (
            f'<sst xmlns="{S}" count="1" uniqueCount="1"><si><r><t>合成</t></r>'
            '<r><t>文字</t></r><rPh sb="0" eb="1"><t>ignored-phonetic</t></rPh></si></sst>').encode()
        types = etree.fromstring(parts['[Content_Types].xml'])
        etree.SubElement(types, '{http://schemas.openxmlformats.org/package/2006/content-types}Override',
                         PartName='/xl/sharedStrings.xml',
                         ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml')
        parts['[Content_Types].xml'] = etree.tostring(types)
    rewrite_parts(source, edit)
    before = source.read_bytes()
    with ZipFile(source) as archive:
        shared = parser.build_shared_strings(archive)
        assert shared == ['合成文字']
        cells = parser.extract_cells(archive, parser.get_sheet_path(archive, "Ops' North"), shared)
        assert cells['F4']['value'] == '合成文字'
        assert cells['B4']['formula'] == '=A4*3'
        assert cells['B5']['formula'] == '=A5*3'
        # Repeat reads on the same ZipFile catch source ZipInfo mutation.
        assert parser.list_sheets(archive) == ["Ops' North", '#REF! literal']
    assert source.read_bytes() == before


def test_cli_output_requires_explicit_repair_and_signed_repair_is_rejected(parser, tmp_path):
    source = synthetic(tmp_path / 'signed.xlsx')
    output = tmp_path / 'evidence.xlsx'
    output.write_bytes(b'prior evidence')
    result = run(BASE / 'scripts/parse_complex_excel.py', source, '--output', output)
    assert result.returncode != 0 and 'specified together' in result.stderr
    rewrite_parts(source, lambda parts: parts.update({'_xmlsignatures/sig1.xml': b'synthetic-signature'}))
    before = source.read_bytes()
    with pytest.raises(ValueError, match='digitally signed'):
        parser.fix_defined_names(source, output)
    assert source.read_bytes() == before and output.read_bytes() == b'prior evidence'
