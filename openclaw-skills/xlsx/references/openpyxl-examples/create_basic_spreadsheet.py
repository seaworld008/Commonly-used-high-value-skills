#!/usr/bin/env python3
# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Create a small synthetic inventory. Run with --output OUTPUT.xlsx."""

import argparse
from pathlib import Path
import sys

from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from create_formatted_excel import save_verified_workbook


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    wb = Workbook()
    ws = wb.active
    ws.title = 'Inventory'
    ws.append(['Item', 'Quantity', 'Unit price', 'Amount'])
    ws.append(['Notebook', 12, 3.5, '=B2*C2'])
    ws.append(['Pen', 20, 1.25, '=B3*C3'])
    ws.append(['Total', None, None, '=SUM(D2:D3)'])
    for row in ws.iter_rows(min_row=2, min_col=3, max_col=4):
        for cell in row:
            cell.number_format = '#,##0.00'
    def check_style(book):
        if book['Inventory']['D2'].number_format != '#,##0.00':
            raise ValueError('Amount format was lost')

    print(save_verified_workbook(wb, args.output, [
        ('Inventory', 'B2', 12), ('Inventory', 'D4', '=SUM(D2:D3)'),
        check_style,
    ]).resolve())
    print('Synthetic inventory; formula caches require a spreadsheet calculation engine.')


if __name__ == '__main__':
    main()
