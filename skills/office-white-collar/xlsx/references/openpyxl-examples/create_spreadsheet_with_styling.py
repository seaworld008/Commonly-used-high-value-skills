#!/usr/bin/env python3
# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Extend copied styles on a synthetic game results sheet; --output is required."""

import argparse
from pathlib import Path
import sys

from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from create_formatted_excel import save_verified_workbook

from copy import copy
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


def apply_header_style(cell, fill_hex='245A81'):
    cell.fill = PatternFill('solid', fgColor=fill_hex)
    cell.font = Font(bold=True, color='FFFFFF')
    cell.alignment = Alignment(horizontal='center')


def apply_highlight_style(cell, fill_hex='FFF2CC'):
    # Copy the existing Font before extension; other attributes survive.
    font = copy(cell.font)
    font.bold = True
    cell.font = font
    cell.fill = PatternFill('solid', fgColor=fill_hex)
    cell.border = Border(bottom=Side(style='double', color='245A81'))


def populate_game_sheet(ws):
    ws.title = 'Game Results'
    ws.append(['Player', 'Round 1', 'Round 2', 'Total'])
    for row in [('Aster', 8, 12, '=SUM(B2:C2)'),
                ('Birch', 11, 7, '=SUM(B3:C3)')]:
        ws.append(row)
    for cell in ws[1]:
        apply_header_style(cell)
    for row in range(2, 4):
        ws.cell(row, 4).font = Font(name='Calibri', italic=True, color='17365D')
        apply_highlight_style(ws.cell(row, 4))
    ws.freeze_panes = 'B2'
    for col in 'ABCD':
        ws.column_dimensions[col].width = 18


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    wb = Workbook()
    populate_game_sheet(wb.active)

    def style_check(check):
        font = check['Game Results']['D2'].font
        if not (font.bold and font.italic):
            raise ValueError('Style extension lost the original italic font')

    print(save_verified_workbook(wb, args.output, [
        ('Game Results', 'D2', '=SUM(B2:C2)'), style_check,
    ]).resolve())
    print('Synthetic scores; formulas are written without cached calculation results.')


if __name__ == '__main__':
    main()
