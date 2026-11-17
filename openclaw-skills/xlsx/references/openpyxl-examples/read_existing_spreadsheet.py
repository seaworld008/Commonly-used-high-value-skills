#!/usr/bin/env python3
# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Read values and formulas without editing an input workbook.

Use --input INPUT.xlsx. Without --input a synthetic sample is created and read in
a TemporaryDirectory under TMPDIR, whose location is printed before cleanup.
"""

import argparse
from pathlib import Path
import sys

from openpyxl import Workbook, load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from create_formatted_excel import save_verified_workbook

from hashlib import sha256
import json
import tempfile


def create_sample(path):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Measurements'
    ws.append(['Batch', 'Count', 'Double'])
    ws.append(['Synthetic A', 7, '=B2*2'])
    ws.append(['Synthetic B', None, '=IF(ISBLANK(B3),NA(),B3*2)'])
    ws['B2'].number_format = '0'

    def check_style(book):
        if book['Measurements']['B2'].number_format != '0':
            raise ValueError('Count format was lost')

    return save_verified_workbook(wb, path, [
        ('Measurements', 'B2', 7), ('Measurements', 'C2', '=B2*2'),
        check_style,
    ])


def _read(path):
    before = sha256(path.read_bytes()).hexdigest()
    formulas = load_workbook(path, data_only=False, keep_links=True)
    cached = None
    try:
        cached = load_workbook(path, data_only=True, keep_links=True)
        rows = []
        for ws in formulas:
            for row in ws:
                for cell in row:
                    if cell.value is None:
                        continue
                    rows.append({'sheet': ws.title, 'cell': cell.coordinate,
                                 'value': cell.value,
                                 'cached_value': cached[ws.title][cell.coordinate].value
                                                 if cell.data_type == 'f' else None,
                                 'is_formula': cell.data_type == 'f'})
        print(json.dumps({'input': str(path.resolve()), 'sha256': before,
                          'calculation': 'No recalculation; caches may be missing or stale.',
                          'cells': rows}, ensure_ascii=False, default=str))
    finally:
        formulas.close()
        if cached is not None:
            cached.close()
    if sha256(path.read_bytes()).hexdigest() != before:
        raise RuntimeError('Input changed while reading')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path)
    args = parser.parse_args()
    if args.input is not None:
        _read(args.input)
    else:
        with tempfile.TemporaryDirectory(prefix='excel-reading-example-') as temp:
            _read(create_sample(Path(temp) / 'synthetic-measurements.xlsx'))


if __name__ == '__main__':
    main()
