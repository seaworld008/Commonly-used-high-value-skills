#!/usr/bin/env python3
# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Original openpyxl formatting helpers and a synthetic finance workbook.

No market data is used. Formulas are written, never evaluated or given invented
caches. Run with an explicit output: create_formatted_excel.py OUTPUT.xlsx.
"""
from __future__ import annotations

import argparse
import errno
import os
from pathlib import Path
import tempfile
from copy import copy

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties

MONEY = '#,##0.00;[Red](#,##0.00);"—"'
PERCENT = '0.0%;[Red](0.0%);"—"'


def publish_verified_file(staged, output_path):
    """Atomically publish; TMPDIR and output must be on the same filesystem."""
    output = Path(output_path)
    try:
        os.replace(staged, output)
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise
        raise OSError(errno.EXDEV,
                      'Atomic publication requires TMPDIR and output on the same filesystem') from exc
    return output


def save_verified_workbook(wb, output_path, checks=()):
    """Stage in TMPDIR, reopen, check (sheet, cell, value), then publish.

    checks may also contain callables receiving the reopened workbook, for style
    assertions. Validation failures leave an existing output untouched.
    """
    with tempfile.TemporaryDirectory(prefix='original-excel-') as temp:
        staged = Path(temp) / 'verified.xlsx'
        wb.save(staged)
        check = load_workbook(staged, data_only=False)
        try:
            for item in checks:
                if callable(item):
                    item(check)
                else:
                    sheet, address, expected = item
                    actual = check[sheet][address].value
                    if actual != expected:
                        raise ValueError(f"Validation failed: {sheet}!{address}: {actual!r}")
        finally:
            check.close()
        return publish_verified_file(staged, output_path)


def apply_header_style(cell, fill_hex='17365D'):
    cell.font = Font(name='Calibri', bold=True, color='FFFFFF')
    cell.fill = PatternFill('solid', fgColor=fill_hex)
    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)


def apply_header_row(ws, row, labels, start_col=1):
    for col, label in enumerate(labels, start_col):
        cell = ws.cell(row, col, label)
        apply_header_style(cell)
    ws.row_dimensions[row].height = 30


def apply_data_row(ws, row, values, start_col=1, font=None,
                   number_format=None, fill=None, border=None):
    for col, value in enumerate(values, start_col):
        cell = ws.cell(row, col)
        cell.value = value  # None remains missing, never coerced to zero.
        for attribute, setting in [('font', font), ('fill', fill), ('border', border)]:
            if setting is not None:
                setattr(cell, attribute, copy(setting))
        if number_format is not None:
            cell.number_format = number_format


def apply_input_cell(ws, row, col, value, number_format=MONEY):
    cell = ws.cell(row, col)
    cell.value = value
    cell.font = Font(color='0000FF')
    cell.fill = PatternFill('solid', fgColor='FFF2CC')
    cell.number_format = number_format
    return cell


def add_sensitivity_table(ws, start_row, start_col, row_header, col_header,
                          row_values, col_values, data_matrix):
    """Write a rectangular scenario grid, rejecting shape errors before writing."""
    rows, cols = list(row_values), list(col_values)
    matrix = [list(row) for row in data_matrix]
    if start_row < 1 or start_col < 1:
        raise ValueError('Table coordinates must be positive')
    if len(matrix) != len(rows) or any(len(row) != len(cols) for row in matrix):
        raise ValueError('Sensitivity matrix dimensions must match both axes')
    apply_header_row(ws, start_row, [f'{row_header} / {col_header}', *cols], start_col)
    for offset, (label, values) in enumerate(zip(rows, matrix), 1):
        apply_data_row(ws, start_row + offset, [label, *values], start_col,
                       number_format=MONEY)
        ws.cell(start_row + offset, start_col).font = Font(bold=True)
    return start_row + len(rows), start_col + len(cols)


def auto_column_widths(ws, min_width=10, max_width=48):
    if not 0 < min_width <= max_width:
        raise ValueError('Expected 0 < min_width <= max_width')
    for column in ws.iter_cols():
        sizes = [len(str(cell.value)) for cell in column
                 if cell.value is not None and cell.data_type != 'f']
        ws.column_dimensions[get_column_letter(column[0].column)].width = min(
            max_width, max(min_width, max(sizes, default=0) + 2))


def apply_financial_style(ws):
    """Style a worksheet without changing its values or formulas."""
    for row in ws:
        for cell in row:
            cell.font = Font(name='Calibri', size=11,
                             color='000000' if cell.data_type == 'f' else '0000FF')
            if isinstance(cell.value, (int, float)) or cell.data_type == 'f':
                cell.number_format = MONEY
    ws.freeze_panes = 'B4'
    ws.sheet_view.showGridLines = False


def create_example_workbook(output_path):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Financial Model'
    ws.merge_cells('A1:D1')
    ws['A1'] = 'Synthetic finance example — amounts in example units'
    ws.append(['Educational assumptions; no live data or calculated formula cache'])
    ws.append(['Metric', 'Year 1', 'Year 2', 'Year 3'])
    for row in [
        ['Revenue', 1200, 1320, 1452],
        ['Operating costs', 780, 858, 943.8],
        ['Operating profit', '=B4-B5', '=C4-C5', '=D4-D5'],
        ['Tax rate', 0.25, 0.25, 0.25],
        ['After-tax profit', '=B6*(1-B7)', '=C6*(1-C7)', '=D6*(1-D7)'],
        ['Reinvestment', 95, 105, 115],
        ['Free cash flow', '=B8-B9', '=C8-C9', '=D8-D9'],
    ]:
        ws.append(row)
    apply_financial_style(ws)
    for cell in ws[3]:
        apply_header_style(cell)
    for cell in ws[7][1:]:
        cell.number_format = PERCENT
    for cell in ws[10]:
        cell.border = Border(top=Side(style='thin', color='17365D'))
        cell.font = Font(bold=True, color='000000')
    ws.column_dimensions['A'].width = 46
    for col in 'BCD':
        ws.column_dimensions[col].width = 19

    dcf = wb.create_sheet('DCF')
    for row in [
        ['Synthetic DCF — educational only', 'Assumption / formula'],
        ['Discount rate', 0.10], ['Terminal growth rate', 0.025],
        ['Year 1 FCF', "='Financial Model'!B10"],
        ['Year 2 FCF', "='Financial Model'!C10"],
        ['Year 3 FCF', "='Financial Model'!D10"],
        ['PV of explicit cash flows', '=B4/(1+B2)+B5/(1+B2)^2+B6/(1+B2)^3'],
        ['Terminal value', '=IF(B2>B3,B6*(1+B3)/(B2-B3),NA())'],
        ['Illustrative enterprise value', '=B7+B8/(1+B2)^3'],
    ]:
        dcf.append(row)
    apply_financial_style(dcf)
    dcf['B2'].number_format = dcf['B3'].number_format = PERCENT
    for cell in dcf[1]:
        apply_header_style(cell)
    dcf.column_dimensions['A'].width = 44
    dcf.column_dimensions['B'].width = 62

    sensitivity = wb.create_sheet('Sensitivity')
    sensitivity.append(['Synthetic discount / growth scenarios', 0.015, 0.025, 0.035])
    for row_num, rate in enumerate([0.08, 0.10, 0.12], start=2):
        sensitivity.cell(row_num, 1, rate)
        for col_num in range(2, 5):
            col = get_column_letter(col_num)
            sensitivity.cell(row_num, col_num,
                f'=IF($A{row_num}>{col}$1,DCF!B4/(1+$A{row_num})'
                f'+DCF!B5/(1+$A{row_num})^2+DCF!B6/(1+$A{row_num})^3'
                f'+DCF!B6*(1+{col}$1)/($A{row_num}-{col}$1)/(1+$A{row_num})^3,NA())')
    apply_financial_style(sensitivity)
    for cell in sensitivity[1]:
        apply_header_style(cell)
        cell.number_format = PERCENT
    for row in range(2, 5):
        sensitivity.cell(row, 1).number_format = PERCENT
    sensitivity.column_dimensions['A'].width = 44
    for col in 'BCD':
        sensitivity.column_dimensions[col].width = 20
    wb.calculation = CalcProperties(calcId=0, fullCalcOnLoad=True, forceFullCalc=True)

    def check_style(check):
        if not check['Financial Model']['B3'].font.bold:
            raise ValueError('Header style was not saved')
        if check['DCF']['B2'].number_format != PERCENT:
            raise ValueError('Percentage format was not saved')

    return save_verified_workbook(wb, output_path, [
        ('Financial Model', 'B4', 1200), ('Financial Model', 'B10', '=B8-B9'),
        ('DCF', 'B9', '=B7+B8/(1+B2)^3'),
        ('Sensitivity', 'B2', sensitivity['B2'].value), check_style,
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output_path', type=Path)
    args = parser.parse_args()
    print(create_example_workbook(args.output_path).resolve())
    print('Synthetic example; formulas have not been recalculated and have no cached results.')


if __name__ == '__main__':
    main()
