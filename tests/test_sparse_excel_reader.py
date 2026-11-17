# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Real sparse OOXML regressions; run pytest with --basetemp under TMPDIR."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.worksheet.worksheet import Worksheet
import pytest

SCRIPT = (Path(__file__).resolve().parents[1] /
          'skills/office-white-collar/xlsx/scripts/parse_complex_excel.py')
S = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
SHEET = 'xl/worksheets/sheet1.xml'


@pytest.fixture
def reader():
    spec = importlib.util.spec_from_file_location('sparse_reader', SCRIPT)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def workbook(path, points):
    wb = Workbook()
    for ref, value in points.items():
        wb.active[ref] = value
    wb.save(path)
    wb.close()
    return path


def rewrite(path, edit):
    with ZipFile(path) as zf:
        parts = {name: zf.read(name) for name in zf.namelist()}
    edit(parts)
    with ZipFile(path, 'w', compression=ZIP_DEFLATED) as zf:
        for name, data in parts.items():
            zf.writestr(name, data)


def edit_sheet(path, edit):
    def change(parts):
        root = etree.fromstring(parts[SHEET])
        edit(root)
        parts[SHEET] = etree.tostring(root)
    rewrite(path, change)


def cells(report, sheet=0):
    return {ref: cell for row in report['sheets'][sheet]['rows']
            for ref, cell in row['cells'].items()}


def guard_access(monkeypatch, allowed, limit):
    original = Worksheet.cell
    visits = []

    def guarded(self, row, column, value=None):
        visits.append((row, column))
        assert len(visits) <= limit, 'Sparse inspection enumerated empty cells'
        assert (row, column) in allowed, 'Access outside selected stored coordinates'
        return original(self, row, column, value)

    monkeypatch.setattr(Worksheet, 'cell', guarded)
    return visits


def test_two_extreme_points_small_output_and_unchanged_hash(reader, tmp_path, monkeypatch):
    path = workbook(tmp_path / 'two.xlsx', {'A1': 1, 'XFD1048576': 2})
    assert path.stat().st_size < 6000
    before = path.read_bytes()
    visits = guard_access(monkeypatch, {(1, 1)}, 1)
    report = reader.inspect_workbook(path, start_row=1, end_row=1)
    assert visits == [(1, 1)]
    assert list(cells(report)) == ['A1']
    assert cells(report)['A1']['value'] == 1
    assert len(json.dumps(report)) < 1500
    assert report['input_sha256'] == sha256(before).hexdigest()
    assert path.read_bytes() == before


@pytest.mark.parametrize('start,end,expected', [
    (1, None, ['A1', 'XFD1', 'A1048576', 'XFD1048576']),
    (1, 1, ['A1', 'XFD1']),
    (1048576, 1048576, ['A1048576', 'XFD1048576']),
    (2, 1048575, []),
])
def test_four_corners_and_row_intervals(reader, tmp_path, monkeypatch, start, end, expected):
    points = {'A1': 0, 'XFD1': False, 'A1048576': '  ', 'XFD1048576': 42}
    path = workbook(tmp_path / 'corners.xlsx', points)
    before = path.read_bytes()
    allowed = {reader.parse_cell_ref(ref) for ref in expected}
    visits = guard_access(monkeypatch, allowed, len(expected))
    report = reader.inspect_workbook(path, start_row=start, end_row=end)
    assert list(cells(report)) == expected
    assert {ref: cell['value'] for ref, cell in cells(report).items()} == {
        ref: points[ref] for ref in expected}
    assert len(visits) == len(expected)
    assert path.read_bytes() == before


def test_dimension_is_not_cell_count_and_formatted_far_cell(reader, tmp_path, monkeypatch):
    path = tmp_path / 'dimension.xlsx'
    wb = Workbook()
    wb.active['A1'] = 'first'
    wb.active['XFD1048576'].font = Font(bold=True)
    wb.save(path)
    wb.close()
    monkeypatch.setattr(reader, 'MAX_STORED_CELLS', 2)
    visits = guard_access(monkeypatch, {(1, 1), (1048576, 16384)}, 2)
    output = cells(reader.inspect_workbook(path))
    assert len(visits) == 2
    assert output['XFD1048576']['value'] is None
    assert output['XFD1048576']['data_type'] == 'n'
    # Even a dimension with no stored far cell must not cause a fabricated cell.
    edit_sheet(path, lambda root: root.find(f'{{{S}}}sheetData').remove(
        root.find(f'{{{S}}}sheetData/{{{S}}}row[@r="1048576"]')))
    visits.clear()
    assert list(cells(reader.inspect_workbook(path))) == ['A1']
    assert visits == [(1, 1)]


def test_shared_formula_master_outside_range_and_missing_cache(reader, tmp_path, monkeypatch):
    path = workbook(tmp_path / 'shared.xlsx', {'A1': 2, 'B1': '=A1*3',
                                             'A1048576': 4, 'B1048576': '=A1048576*3'})

    def shared(root):
        for ref in ['B1', 'B1048576']:
            cell = root.find(f'.//{{{S}}}c[@r="{ref}"]')
            formula = cell.find(f'{{{S}}}f')
            formula.set('t', 'shared')
            formula.set('si', '0')
            if ref == 'B1':
                formula.set('ref', 'B1:B1048576')
            else:
                formula.text = None
    edit_sheet(path, shared)
    before = path.read_bytes()
    visits = guard_access(monkeypatch, {(1048576, 1), (1048576, 2)}, 3)
    output = cells(reader.inspect_workbook(path, start_row=1048576, end_row=1048576))
    assert len(visits) == 3
    assert output['B1048576']['formula'] == '=A1048576*3'
    assert output['B1048576']['cached_value'] is None
    assert output['B1048576']['cache_status'] == 'missing'
    assert path.read_bytes() == before


def test_hidden_sheets_merges_and_no_formula_evaluation(reader, tmp_path, monkeypatch):
    path = tmp_path / 'hidden.xlsx'
    wb = Workbook()
    wb.active['A1'] = '  spaced  '
    wb.active.merge_cells('A1:B1')
    hidden = wb.create_sheet('Hidden')
    hidden.sheet_state = 'hidden'
    hidden['XFD1048576'] = '=HYPERLINK("https://example.invalid/never-open","x")'
    wb.save(path)
    wb.close()
    before = path.read_bytes()
    real_load = reader.load_workbook
    loads = []

    def load(*args, **kwargs):
        loads.append(kwargs['data_only'])
        return real_load(*args, **kwargs)
    monkeypatch.setattr(reader, 'load_workbook', load)
    report = reader.inspect_workbook(path)
    assert loads == [False, True]
    assert [s['name'] for s in report['sheets']] == ['Sheet', 'Hidden']
    assert report['sheets'][0]['merged_ranges'] == ['A1:B1']
    assert cells(report)['A1']['value'] == '  spaced  '
    formula = cells(report, 1)['XFD1048576']
    assert formula['formula'].startswith('=HYPERLINK(')
    assert formula['cached_value'] is None
    assert path.read_bytes() == before


def no_load(*args, **kwargs):
    pytest.fail('Resource rejection must happen before loading workbooks')


def test_stored_cell_limit_applies_before_load_even_outside_selected_rows(reader, tmp_path, monkeypatch):
    path = workbook(tmp_path / 'limit.xlsx', {'A1': 1, 'A2': 2, 'XFD1048576': 3})
    before = path.read_bytes()
    monkeypatch.setattr(reader, 'MAX_STORED_CELLS', 2)
    monkeypatch.setattr(reader, 'load_workbook', no_load)
    with pytest.raises(ValueError, match='Stored cell count exceeds 2'):
        reader.inspect_workbook(path, start_row=1, end_row=1)
    with ZipFile(path) as zf, pytest.raises(ValueError, match='Stored cell count'):
        reader.extract_cells(zf, SHEET, [])
    assert path.read_bytes() == before


@pytest.mark.parametrize('limit,message', [
    ('MAX_ZIP_BYTES', 'ZIP size'), ('MAX_ZIP_MEMBERS', 'ZIP member count'),
    ('MAX_UNCOMPRESSED_BYTES', 'ZIP uncompressed size'),
    ('MAX_XML_BYTES', 'XML total size'), ('MAX_XML_PART_BYTES', 'XML part'),
])
def test_archive_limits_before_loading(reader, tmp_path, monkeypatch, limit, message):
    path = workbook(tmp_path / 'archive.xlsx', {'A1': 1})
    before = path.read_bytes()
    monkeypatch.setattr(reader, limit, 1)
    monkeypatch.setattr(reader, 'load_workbook', no_load)
    with pytest.raises(ValueError, match=message):
        reader.inspect_workbook(path)
    assert path.read_bytes() == before


def test_large_merge_rejected_before_placeholder_allocation(reader, tmp_path, monkeypatch):
    path = workbook(tmp_path / 'merge.xlsx', {'A1': 1})

    def merge(root):
        merges = etree.SubElement(root, f'{{{S}}}mergeCells', count='1')
        etree.SubElement(merges, f'{{{S}}}mergeCell', ref='A1:XFD1048576')
    edit_sheet(path, merge)
    before = path.read_bytes()
    monkeypatch.setattr(reader, 'load_workbook', no_load)
    with pytest.raises(ValueError, match='Merged cell expansion'):
        reader.inspect_workbook(path)
    assert path.read_bytes() == before


@pytest.mark.parametrize('start,end', [(0, 1), (2, 1), (1048577, None), (1, 1048577)])
def test_row_bounds_rejected_before_loading(reader, tmp_path, monkeypatch, start, end):
    path = workbook(tmp_path / 'rows.xlsx', {'A1': 1})
    monkeypatch.setattr(reader, 'load_workbook', no_load)
    with pytest.raises(ValueError, match='1048576'):
        reader.inspect_workbook(path, start_row=start, end_row=end)


def test_output_cell_budget_shared_across_sheets_and_narrowable(reader, tmp_path, monkeypatch):
    path = tmp_path / 'outputs.xlsx'
    wb = Workbook()
    wb.active['A1'] = 1
    wb.create_sheet('Second')['A2'] = 2
    wb.save(path)
    wb.close()
    before = path.read_bytes()
    monkeypatch.setattr(reader, 'MAX_OUTPUT_CELLS', 1)
    with pytest.raises(ValueError, match='Extracted cell count exceeds 1'):
        reader.inspect_workbook(path)
    report = reader.inspect_workbook(path, start_row=1, end_row=1)
    assert list(cells(report)) == ['A1'] and cells(report, 1) == {}
    assert path.read_bytes() == before


def test_output_byte_budget_exact_serialized_boundary(reader, tmp_path, monkeypatch):
    path = workbook(tmp_path / 'output-bytes.xlsx', {'A1': '中文' * 200})
    before = path.read_bytes()
    report = reader.inspect_workbook(path)
    size = len(json.dumps(report, ensure_ascii=False, indent=2, default=str).encode('utf-8'))
    monkeypatch.setattr(reader, 'MAX_OUTPUT_BYTES', size)
    assert reader.inspect_workbook(path) == report
    monkeypatch.setattr(reader, 'MAX_OUTPUT_BYTES', size - 1)
    with pytest.raises(ValueError, match='Extracted output exceeds'):
        reader.inspect_workbook(path)
    monkeypatch.setattr(reader, 'MAX_OUTPUT_BYTES', 100)
    with ZipFile(path) as zf, pytest.raises(ValueError, match='Extracted output exceeds'):
        reader.extract_cells(zf, SHEET, [])
    assert path.read_bytes() == before


def test_public_helpers_remain_bounded(reader, tmp_path, monkeypatch):
    path = workbook(tmp_path / 'helpers.xlsx', {'A1': 1, 'XFD1048576': 2})
    visits = guard_access(monkeypatch, {(1, 1), (1048576, 16384)}, 2)
    with ZipFile(path) as zf:
        output = reader.extract_cells(zf, SHEET, [])
    assert len(visits) == 2
    monkeypatch.setattr(reader, 'MAX_OUTPUT_CELLS', 1)
    with pytest.raises(ValueError, match='Extracted cell count'):
        reader.extract_rows(output)
    assert reader.extract_rows(output, 1048576, 1048576)[0]['row'] == 1048576


def test_unresolved_shared_formula_is_rejected_without_inventing_value(reader, tmp_path):
    path = workbook(tmp_path / 'orphan.xlsx', {'A1': '=2*3'})

    def orphan(root):
        formula = root.find(f'.//{{{S}}}f')
        formula.set('t', 'shared')
        formula.set('si', '99')
        formula.text = None
    edit_sheet(path, orphan)
    before = path.read_bytes()
    with pytest.raises(ValueError, match='Unresolved shared formula: A1'):
        reader.inspect_workbook(path)
    assert path.read_bytes() == before


@pytest.mark.parametrize('encoding', ['utf-8', 'utf-16'])
def test_dtd_rejected_in_auxiliary_xml_before_openpyxl(reader, tmp_path, monkeypatch, encoding):
    path = workbook(tmp_path / 'dtd.xlsx', {'A1': 1})
    xml = ('<?xml version="1.0" encoding="' + encoding + '"?>'
           '<!DOCTYPE styleSheet [<!ENTITY injected "bad">]>'
           f'<styleSheet xmlns="{S}">&injected;</styleSheet>')
    rewrite(path, lambda parts: parts.update({'xl/styles.xml': xml.encode(encoding)}))
    before = path.read_bytes()
    monkeypatch.setattr(reader, 'load_workbook', no_load)
    with pytest.raises(ValueError, match='DTD declarations'):
        reader.inspect_workbook(path)
    assert path.read_bytes() == before


def test_blank_cells_and_date_types_are_preserved(reader, tmp_path):
    from datetime import datetime
    path = tmp_path / 'types.xlsx'
    wb = Workbook()
    ws = wb.active
    ws['A1'] = datetime(2026, 1, 2)
    ws['B1'].font = Font(bold=True)
    ws['C1'] = '   '
    ws['D1'] = ''
    ws['E1'] = False
    ws['F1'] = 0
    wb.save(path)
    wb.close()
    before = path.read_bytes()
    output = cells(reader.inspect_workbook(path))
    assert output['A1']['value'] == datetime(2026, 1, 2)
    assert output['A1']['data_type'] == 'd'
    assert output['B1']['value'] is None
    assert output['C1']['value'] == '   '
    assert 'D1' not in output  # Existing behavior for unstyled, empty inlineStr.
    assert output['E1']['value'] is False
    assert output['F1']['value'] == 0
    assert path.read_bytes() == before
