#!/usr/bin/env python3
# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Create a styled synthetic sales worksheet. Run with --output OUTPUT.xlsx."""

import argparse
from pathlib import Path
import sys

from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from create_formatted_excel import save_verified_workbook

from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    wb = Workbook()
    ws = wb.active
    ws.title = 'Sales'
    ws.merge_cells('A1:C1')
    ws['A1'] = 'Synthetic quarterly sales'
    ws['A1'].font = Font(size=16, bold=True, color='17365D')
    ws.append(['Quarter', 'Revenue', 'Margin'])
    for row in [('Q1', 240, 0.18), ('Q2', 280, 0.22), ('Q3', 260, 0.20)]:
        ws.append(row)
    for cell in ws[2]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='17365D')
        cell.alignment = Alignment(horizontal='center')
        cell.border = Border(bottom=Side(style='thin', color='FFFFFF'))
    for row in range(3, 6):
        ws.cell(row, 2).number_format = '#,##0.00;[Red](#,##0.00)'
        ws.cell(row, 3).number_format = '0.0%'
    ws.conditional_formatting.add('B3:B5', ColorScaleRule(
        start_type='min', start_color='FFFFFF', end_type='max', end_color='63BE7B'))
    ws.freeze_panes = 'B3'
    ws.auto_filter.ref = 'A2:C5'
    for col in 'ABC':
        ws.column_dimensions[col].width = 22

    def style_check(check):
        sh = check['Sales']
        if not sh['A2'].font.bold or sh['C3'].number_format != '0.0%':
            raise ValueError('Expected header and percentage styles')
        if len(sh.conditional_formatting) != 1:
            raise ValueError('Conditional format was not retained')

    print(save_verified_workbook(wb, args.output, [
        ('Sales', 'B3', 240), style_check,
    ]).resolve())


if __name__ == '__main__':
    main()
