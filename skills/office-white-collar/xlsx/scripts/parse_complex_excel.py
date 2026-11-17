#!/usr/bin/env python3
# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Read complex .xlsx files without recalculating or altering the input.

Usage: parse_complex_excel.py INPUT.xlsx [--sheet NAME] [--start-row N]
       [--end-row N] [--repair --output REPAIRED.xlsx]
The JSON report separates formulas and caches. Repair changes only positively
identified invalid definedName elements, leaving other ZIP members byte-identical.
Inspection returns only stored cells in the requested rows, with no padding for
empty coordinates. Archive, cell and JSON output limits below fail explicitly;
narrow the row range when only the output exceeds its limit.
"""
from __future__ import annotations

import argparse
from copy import copy
from contextlib import contextmanager, ExitStack
import importlib.util
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import posixpath
import re
import tempfile
from zipfile import ZipFile, is_zipfile

from lxml import etree
from openpyxl import load_workbook
from openpyxl.formula.tokenizer import Tokenizer
from openpyxl.utils.cell import coordinate_to_tuple, range_boundaries

_helper_spec = importlib.util.spec_from_file_location(
    '_original_excel_output', Path(__file__).with_name('create_formatted_excel.py'))
_helper = importlib.util.module_from_spec(_helper_spec)
_helper_spec.loader.exec_module(_helper)
publish_verified_file = _helper.publish_verified_file

S = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS = {'s': S}

# Limits apply to the whole archive, including unselected/hidden sheets. They
# count stored cells, never the worksheet dimension's bounding rectangle.
MAX_ZIP_BYTES = 64 * 1024 * 1024
MAX_ZIP_MEMBERS = 4096
MAX_UNCOMPRESSED_BYTES = 128 * 1024 * 1024
MAX_XML_BYTES = 64 * 1024 * 1024
MAX_XML_PART_BYTES = 16 * 1024 * 1024
MAX_STORED_CELLS = 100_000
MAX_MERGED_CELLS = 100_000
MAX_OUTPUT_CELLS = 10_000
MAX_OUTPUT_BYTES = 8 * 1024 * 1024


def _check_archive(zf):
    position = zf.fp.tell()
    try:
        zf.fp.seek(0, 2)
        if zf.fp.tell() > MAX_ZIP_BYTES:
            raise ValueError(f'ZIP size exceeds {MAX_ZIP_BYTES} bytes')
    finally:
        zf.fp.seek(position)
    members = zf.infolist()
    if len(members) > MAX_ZIP_MEMBERS:
        raise ValueError(f'ZIP member count exceeds {MAX_ZIP_MEMBERS}')
    if len(members) != len({info.filename for info in members}):
        raise ValueError('Duplicate ZIP members are unsupported')
    if sum(info.file_size for info in members) > MAX_UNCOMPRESSED_BYTES:
        raise ValueError(f'ZIP uncompressed size exceeds {MAX_UNCOMPRESSED_BYTES} bytes')
    xml_members = [info for info in members
                   if info.filename.lower().endswith(('.xml', '.rels'))]
    if sum(info.file_size for info in xml_members) > MAX_XML_BYTES:
        raise ValueError(f'XML total size exceeds {MAX_XML_BYTES} bytes')
    for info in xml_members:
        if info.file_size > MAX_XML_PART_BYTES:
            raise ValueError(f'XML part exceeds {MAX_XML_PART_BYTES} bytes: {info.filename}')
        # Reject DTDs also in styles, strings and other parts openpyxl will read.
        _xml(zf.read(info))


def _check_worksheets(zf):
    stored = merged = 0
    for path in {s['path'] for s in _sheet_info(zf) if s['path']}:
        root = _xml(zf.read(path))
        seen = set()
        for cell in root.iterfind('s:sheetData/s:row/s:c', NS):
            stored += 1
            if stored > MAX_STORED_CELLS:
                raise ValueError(f'Stored cell count exceeds {MAX_STORED_CELLS}')
            ref = cell.get('r', '')
            coord = parse_cell_ref(ref)
            if coord in seen:
                raise ValueError(f'Duplicate stored cell coordinate: {ref}')
            seen.add(coord)
        for node in root.iterfind('s:mergeCells/s:mergeCell', NS):
            bounds = range_boundaries(node.get('ref', ''))
            left, top, right, bottom = bounds
            if (None in bounds or not 1 <= left <= right <= 16384
                    or not 1 <= top <= bottom <= 1048576):
                raise ValueError('Merged range outside Excel limits')
            merged += (right - left + 1) * (bottom - top + 1)
            # Normal-mode openpyxl materializes merged placeholders on load.
            if merged > MAX_MERGED_CELLS:
                raise ValueError(f'Merged cell expansion exceeds {MAX_MERGED_CELLS}')


def _check_rows(start_row, end_row):
    if (not isinstance(start_row, int) or not 1 <= start_row <= 1048576
            or (end_row is not None and (not isinstance(end_row, int)
                or not start_row <= end_row <= 1048576))):
        raise ValueError('Expected 1 <= start_row <= end_row <= 1048576')


class _OutputBudget:
    def __init__(self):
        self.cells = 0
        self.bytes = 0

    def add_cell(self, ref, cell):
        self.cells += 1
        if self.cells > MAX_OUTPUT_CELLS:
            raise ValueError(f'Extracted cell count exceeds {MAX_OUTPUT_CELLS}; narrow the row range')
        self.bytes += len(json.dumps({ref: cell}, ensure_ascii=False, default=str).encode('utf-8'))
        if self.bytes > MAX_OUTPUT_BYTES:
            raise ValueError(f'Extracted output exceeds {MAX_OUTPUT_BYTES} bytes; narrow the row range')


def _check_output(result):
    size = 0
    for chunk in json.JSONEncoder(ensure_ascii=False, indent=2, default=str).iterencode(result):
        size += len(chunk.encode('utf-8'))
        if size > MAX_OUTPUT_BYTES:
            raise ValueError(f'Extracted output exceeds {MAX_OUTPUT_BYTES} bytes; narrow the row range')


def _xml(data):
    if len(data) > MAX_XML_PART_BYTES:
        raise ValueError(f'XML part exceeds {MAX_XML_PART_BYTES} bytes')
    root = etree.fromstring(data, etree.XMLParser(resolve_entities=False, no_network=True))
    if root.getroottree().docinfo.doctype:
        raise ValueError('DTD declarations are unsupported')
    return root


def _sheet_info(zf):
    workbook = _xml(zf.read('xl/workbook.xml'))
    rels = _xml(zf.read('xl/_rels/workbook.xml.rels'))
    targets = {}
    for rel in rels:
        if rel.get('TargetMode') == 'External':
            continue
        if not rel.get('Type', '').endswith('/worksheet'):
            continue
        target = rel.get('Target', '')
        path = posixpath.normpath(target.lstrip('/') if target.startswith('/')
                                  else posixpath.join('xl', target))
        if path.startswith('../') or not path.startswith('xl/'):
            raise ValueError('Unsafe worksheet relationship path')
        targets[rel.get('Id')] = path
    return [{'name': sh.get('name'), 'path': targets.get(sh.get(f'{{{R}}}id')),
             'state': sh.get('state', 'visible')}
            for sh in workbook.findall('s:sheets/s:sheet', NS)]


def verify_format(file_path):
    """Return True for a readable OOXML workbook; reject binary .xls files."""
    if not is_zipfile(file_path):
        raise ValueError('Expected a ZIP-based .xlsx workbook, not binary .xls')
    with ZipFile(file_path) as zf:
        _check_archive(zf)
        _check_worksheets(zf)
        if zf.testzip() is not None:
            raise ValueError('Corrupt ZIP member')
    return True


def list_sheets(zf):
    """Return worksheet names in workbook order, including hidden worksheets."""
    return [sheet['name'] for sheet in _sheet_info(zf) if sheet['path']]


def get_sheet_path(zf, sheet_name):
    for sheet in _sheet_info(zf):
        if sheet['name'] == sheet_name and sheet['path']:
            return sheet['path']
    raise KeyError(f'Worksheet not found: {sheet_name}')


def build_shared_strings(zf):
    if 'xl/sharedStrings.xml' not in zf.namelist():
        return []
    root = _xml(zf.read('xl/sharedStrings.xml'))
    return [''.join(t.text or '' for t in
                    (si.findall('s:t', NS) or si.findall('s:r/s:t', NS)))
            for si in root.findall('s:si', NS)]


def parse_cell_ref(ref):
    """Return (one-based row, one-based column), accepting absolute A1 syntax."""
    if not re.fullmatch(r'\$?[A-Za-z]{1,3}\$?[1-9][0-9]*', ref):
        raise ValueError(f'Invalid cell reference: {ref}')
    row, col = coordinate_to_tuple(ref.replace('$', '').upper())
    if row > 1048576 or col > 16384:
        raise ValueError(f'Cell reference outside Excel limits: {ref}')
    return row, col


def _zip_bytes(zf):
    # ZipFile may have been opened from BytesIO, so do not rely on .filename.
    # openpyxl cannot load an out-of-range localSheetId. Skip only such names in
    # this disposable memory view; diagnostics still inspect the original XML.
    root = _xml(zf.read('xl/workbook.xml'))
    names = [s.get('name') for s in root.findall('s:sheets/s:sheet', NS)]
    skipped = False
    for node in root.findall('s:definedNames/s:definedName', NS):
        if (_name_problem(node, names) or '').startswith('localSheetId'):
            node.getparent().remove(node)
            skipped = True
    stream = BytesIO()
    with ZipFile(stream, 'w') as archive:
        for info in zf.infolist():
            data = (etree.tostring(root, encoding='UTF-8', xml_declaration=True)
                    if skipped and info.filename == 'xl/workbook.xml'
                    else zf.read(info.filename))
            archive.writestr(copy(info), data)
    return stream.getvalue()


def extract_cells(zf, sheet_path, shared):
    """Return {A1: {value, formula, cached_value, cache_status, ...}}.

    shared is retained for callers of the legacy helper. openpyxl resolves actual
    shared strings, rich text and shared formulas using workbook relationships.
    """
    _check_archive(zf)
    _check_worksheets(zf)
    result = _extract_cells(zf, sheet_path, 1, None, _OutputBudget())
    _check_output(result)
    return result


def _extract_cells(zf, sheet_path, start_row, end_row, budget, readers=None):
    _check_rows(start_row, end_row)
    name = next((s['name'] for s in _sheet_info(zf) if s['path'] == sheet_path), None)
    if name is None:
        raise KeyError(f'Worksheet part not found: {sheet_path}')
    raw = []
    for node in _xml(zf.read(sheet_path)).iterfind('s:sheetData/s:row/s:c', NS):
        row, col = parse_cell_ref(node.get('r', ''))
        if row >= start_row and (end_row is None or row <= end_row):
            raw.append((row, col, node))
    if not raw:
        return {}
    with ExitStack() as stack:
        if readers is None:
            readers = stack.enter_context(_workbooks(zf))
        formulas, cached = readers
        ws, values = formulas[name], cached[name]
        result = {}
        for row, col, raw_cell in raw:
            cell = ws.cell(row, col)
            if cell.value is None and not cell.has_style:
                continue
            formula = cell.value if cell.data_type == 'f' else None
            if formula is not None and not isinstance(formula, str):
                formula = getattr(formula, 'text', None)
                if formula is None:
                    raise NotImplementedError('Data-table formulas are not supported')
            raw_formula = raw_cell.find('s:f', NS)
            if (raw_formula is not None and raw_formula.get('t') == 'shared'
                    and not raw_formula.text and formula == '='):
                raise ValueError(f'Unresolved shared formula: {cell.coordinate}')
            value = values.cell(row, col).value if formula else None
            raw_cache = raw_cell.find('s:v', NS)
            if (formula and raw_cell.get('t') == 'str'
                    and raw_cache is not None and raw_cache.text is None):
                value = ''  # Explicit empty string cache is distinct from no cache.
            result[cell.coordinate] = {
                'value': formula if formula else cell.value,
                'formula': formula, 'cached_value': value,
                'cache_status': ('missing' if value is None else 'present') if formula
                                else 'not_formula',
                'data_type': cell.data_type, 'number_format': cell.number_format,
            }
            budget.add_cell(cell.coordinate, result[cell.coordinate])
        return result


@contextmanager
def _workbooks(zf):
    data = _zip_bytes(zf)
    formulas = load_workbook(BytesIO(data), data_only=False, keep_links=True)
    cached = None
    try:
        cached = load_workbook(BytesIO(data), data_only=True, keep_links=True)
        yield formulas, cached
    finally:
        formulas.close()
        if cached is not None:
            cached.close()


def extract_rows(cells, start_row=1, end_row=None):
    _check_rows(start_row, end_row)
    grouped = {}
    budget = _OutputBudget()
    for ref, cell in sorted(cells.items(), key=lambda item: parse_cell_ref(item[0])):
        row, _ = parse_cell_ref(ref)
        if row >= start_row and (end_row is None or row <= end_row):
            budget.add_cell(ref, cell)
            grouped.setdefault(row, {})[ref] = cell
    result = [{'row': row, 'cells': entries} for row, entries in grouped.items()]
    _check_output(result)
    return result


def _name_problem(node, sheet_names):
    local = node.get('localSheetId')
    if local is not None:
        try:
            if not 0 <= int(local) < len(sheet_names):
                return 'localSheetId outside workbook sheet range'
        except ValueError:
            return 'localSheetId is not an integer'
    text = node.text or ''
    try:
        tokens = Tokenizer(text if text.startswith('=') else '=' + text).items
    except Exception:
        # Unrecognized/dynamic formulas are diagnostic-only, not deletion targets.
        return None
    for token in tokens:
        if token.type != 'OPERAND':
            continue
        if token.subtype == 'ERROR' and token.value.upper() == '#REF!':
            return 'explicit #REF! reference'
        if token.subtype != 'RANGE':
            continue
        ref = token.value
        if '[' in ref or ']' in ref:
            continue  # external/structured reference: never open or infer deletion
        # A quoted sheet name may itself contain the characters #REF!.
        unquoted = re.sub(r"'(?:[^']|'')*'", '', ref)
        if '#REF!' in unquoted.upper():
            return 'explicit #REF! reference'
        if '!' not in ref:
            continue  # constants, relative names and dynamic names remain intact
        sheet, address = ref.rsplit('!', 1)
        if sheet.startswith("'") and sheet.endswith("'"):
            sheet = sheet[1:-1].replace("''", "'")
        if ':' in sheet:  # 3D references need a dedicated evaluator; preserve them.
            continue
        if sheet.casefold() not in {s.casefold() for s in sheet_names}:
            return f'missing worksheet: {sheet}'
        try:
            bounds = range_boundaries(address.replace('$', ''))
        except ValueError:
            continue
        if any(v is not None and v < 1 for v in bounds):
            return 'reference outside worksheet bounds'
        if any(v is not None and v > limit
               for v, limit in zip(bounds, [16384, 1048576, 16384, 1048576])):
            return 'reference outside worksheet bounds'
    return None


def diagnose_defined_names(zf):
    root = _xml(zf.read('xl/workbook.xml'))
    names = [s.get('name') for s in root.findall('s:sheets/s:sheet', NS)]
    return [{'name': node.get('name'), 'localSheetId': node.get('localSheetId'),
             'reference': node.text, 'problem': _name_problem(node, names),
             'action': 'diagnostic_only'}
            for node in root.findall('s:definedNames/s:definedName', NS)]


def fix_defined_names(input_path, output_path):
    """Remove diagnosed broken names in a distinct output, return an audit report.

    Other members, including worksheet formulas/caches, styles, external-link
    data and embedded VBA, are copied unchanged. Signed packages are rejected.
    """
    source, output = Path(input_path), Path(output_path)
    if source.resolve() == output.resolve() or (output.exists() and source.samefile(output)):
        raise ValueError('Repair requires a distinct output; input is always read-only')
    # Reject signatures before XML validation so even an opaque/unsupported
    # signature part retains the existing explicit no-repair diagnostic.
    if is_zipfile(source):
        with ZipFile(source) as archive:
            if any(n.lower().startswith('_xmlsignatures/') for n in archive.namelist()):
                raise ValueError('Repair of digitally signed workbooks is unsupported')
    verify_format(source)
    before = source.read_bytes()
    with ZipFile(BytesIO(before)) as zf:
        report = diagnose_defined_names(zf)
        root = _xml(zf.read('xl/workbook.xml'))
        nodes = root.findall('s:definedNames/s:definedName', NS)
        for node, item in zip(nodes, report):
            if item['problem']:
                node.getparent().remove(node)
                item['action'] = 'removed'
            else:
                item['action'] = 'preserved'
        removed = sum(item['action'] == 'removed' for item in report)
        workbook_xml = (etree.tostring(root, encoding='UTF-8', xml_declaration=True)
                        if removed else zf.read('xl/workbook.xml'))
        with tempfile.TemporaryDirectory(prefix='excel-name-repair-') as temp:
            staged = Path(temp) / 'repaired.xlsx'
            with ZipFile(staged, 'w') as dest:
                dest.comment = zf.comment
                for info in zf.infolist():
                    dest.writestr(copy(info), workbook_xml if info.filename == 'xl/workbook.xml'
                                  else zf.read(info.filename))
            verify_format(staged)
            with ZipFile(staged) as check:
                for info in zf.infolist():
                    if info.filename != 'xl/workbook.xml' and check.read(info.filename) != zf.read(info.filename):
                        raise ValueError(f'Unexpected change: {info.filename}')
                if any(d['problem'] for d in diagnose_defined_names(check)):
                    raise ValueError('Name repair did not resolve diagnosed references')
            # Verify actual workbook readability without resaving it.
            check_wb = load_workbook(staged, data_only=False, keep_links=True)
            check_wb.close()
            if source.read_bytes() != before:
                raise RuntimeError('Input changed during repair; refusing publication')
            publish_verified_file(staged, output)
    return {'input_sha256': sha256(before).hexdigest(),
            'output': str(output.resolve()), 'removed_count': removed, 'defined_names': report}


def inspect_workbook(input_path, sheet=None, start_row=1, end_row=None):
    _check_rows(start_row, end_row)
    verify_format(input_path)
    before = Path(input_path).read_bytes()
    with ZipFile(BytesIO(before)) as zf:
        names = list_sheets(zf)
        selected = [sheet] if sheet else names
        sheets = []
        budget = _OutputBudget()
        with _workbooks(zf) as readers:
            for name in selected:
                path = get_sheet_path(zf, name)
                cells = _extract_cells(zf, path, start_row, end_row, budget, readers)
                root = _xml(zf.read(path))
                sheets.append({'name': name, 'path': path,
                               'merged_ranges': [n.get('ref') for n in root.findall('s:mergeCells/s:mergeCell', NS)],
                               'rows': extract_rows(cells, start_row, end_row)})
        result = {'input_sha256': sha256(before).hexdigest(),
                  'sheets': sheets, 'defined_names': diagnose_defined_names(zf),
                  'read_notes': 'Invalid local-scope names are skipped only in the in-memory reader view.',
                  'calculation': 'No recalculation performed; caches may be absent or stale.'}
        _check_output(result)
    if Path(input_path).read_bytes() != before:
        raise RuntimeError('Input changed during inspection')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_path', type=Path)
    parser.add_argument('--sheet')
    parser.add_argument('--start-row', type=int, default=1)
    parser.add_argument('--end-row', type=int)
    parser.add_argument('--repair', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.repair != (args.output is not None):
        parser.error('--repair and --output must be specified together')
    result = (fix_defined_names(args.input_path, args.output) if args.repair else
              inspect_workbook(args.input_path, args.sheet, args.start_row, args.end_row))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()
