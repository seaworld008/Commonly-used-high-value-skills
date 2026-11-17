<!-- Copyright (c) 2026 seaworld008 -->
<!-- SPDX-License-Identifier: MIT -->

# Excel 格式与可验证示例

本文及配套示例是本地原创实现。运行环境需要 Python、openpyxl；
复杂解析器还需要 lxml。以下命令均从仓库根目录执行，输出明确放入
任务目录；代码不会请求网络、启动 Excel 或替你重算工作簿。

## 先选择数据表示

| 数据含义 | 实际值示例 | number_format | 显示意图 |
| --- | --- | --- | --- |
| 金额 | 1234.5 | `#,##0.00;[Red](#,##0.00);"—"` | 两位小数，负数红色括号，零显示破折号 |
| 百分比 | 0.125 | `0.0%` | 12.5%，不要写入 12.5 再套百分比 |
| 整数 | 1200 | `#,##0` | 千位分隔 |
| 日期 | Python datetime | `yyyy-mm-dd` | 保留日期类型 |
| 持续时长 | Python timedelta | `[h]:mm` | 累计小时可超过 24 |
| 产品编号 | "00127" | `@` | 保留前导零；实际值也必须是字符串 |

格式只改变显示；它不会转换单位、修复原始值或计算公式。
缺失值写入 `None`，不要为了格式整齐补成零。
输入假设用蓝色字体和浅黄色底，公式用黑色字体。
颜色同时配合文字标签，避免仅凭颜色区分含义。
合并标题时只给左上角单元格赋值，其他位置属于合并占位格。
表格主体尽量不合并，以便排序、筛选和机器读取。

## 可直接运行的格式示例

将下面代码保存为任务目录内的 Python 文件，从仓库根目录执行：
`python "$TMPDIR/format_demo.py" "$TMPDIR/format_demo.xlsx"`。
输出先写到 TMPDIR，重开核对值、公式和格式后再发布。
TMPDIR 与输出必须位于同一文件系统；跨文件系统会明确报错，
避免用非原子的复制覆盖旧结果。输出父目录需要事先存在。

```python
from datetime import datetime, timedelta
from pathlib import Path
import sys
from openpyxl import Workbook
from openpyxl.styles import Font
sys.path.insert(0, str(Path("skills/office-white-collar/xlsx/scripts").resolve()))
from create_formatted_excel import (
    apply_header_row, apply_data_row, apply_input_cell,
    auto_column_widths, save_verified_workbook,
)

output = Path(sys.argv[1])
wb = Workbook()
ws = wb.active
ws.title = "Budget"
ws.merge_cells("A1:D1")
ws["A1"] = "Synthetic workshop budget"
ws["A1"].font = Font(size=16, bold=True)
apply_header_row(ws, 3, ["Item", "Units", "Price", "Amount"])
apply_data_row(ws, 4, ["Training kits", 8, 25.5, "=B4*C4"])
apply_data_row(ws, 5, ["Venue", None, None, None])
apply_input_cell(ws, 4, 2, 8, "0")
for address in ("C4", "D4"):
    ws[address].number_format = '#,##0.00;[Red](#,##0.00);"—"'
ws["A7"], ws["B7"] = "Tax rate", 0.125
ws["B7"].number_format = "0.0%"
ws["A8"], ws["B8"] = "Start date", datetime(2026, 1, 15)
ws["B8"].number_format = "yyyy-mm-dd"
ws["A9"], ws["B9"] = "Preparation", timedelta(hours=27, minutes=30)
ws["B9"].number_format = "[h]:mm"
ws.freeze_panes = "B4"
ws.auto_filter.ref = "A3:D5"
auto_column_widths(ws, 12, 40)

def verify_style(book):
    if book["Budget"]["D4"].number_format != '#,##0.00;[Red](#,##0.00);"—"':
        raise ValueError("Amount number format was lost")
    if not book["Budget"]["A3"].font.bold:
        raise ValueError("Header style was lost")

print(save_verified_workbook(wb, output, [
    ("Budget", "B4", 8), ("Budget", "D4", "=B4*C4"),
    ("Budget", "B5", None), verify_style,
]).resolve())
```

## 财务表与敏感性表

执行 `python skills/office-white-collar/xlsx/scripts/create_formatted_excel.py "$TMPDIR/finance.xlsx"`。
生成 Financial Model、DCF 和 Sensitivity 三张合成示例表。
DCF 使用三期自由现金流、折现率及永续增长率；
终值为末期现金流乘以增长因子，再除以折现率与增长率之差。
折现率不大于增长率时，公式返回 `NA()`，不能把异常终值解释为估值结果。
Sensitivity 的每个场景独立使用对应折现率和终值增长率，
同时折现明确预测期与终值，不复用基准场景的现值。
这些假设不来自市场，也不构成实际财务预测或投资建议。

`add_sensitivity_table(ws, start_row, start_col, row_header, col_header,
row_values, col_values, data_matrix)` 可写入自己的二维场景矩阵；
矩阵形状错误会在写入前拒绝。数值、公式与 None 均保持原含义。
`apply_data_row` 的 font、fill、border 可传入 openpyxl 样式对象；
number_format 应传入格式字符串。样式使用复制，避免意外共享修改。

## 复杂文件的读取与名称修复

默认只读：
`python skills/office-white-collar/xlsx/scripts/parse_complex_excel.py "$TMPDIR/finance.xlsx" --sheet DCF`。
可加 `--start-row 4 --end-row 9` 限定报告行。
JSON 包含输入 SHA-256、工作表实际部件路径、合并区域、
每格原值、公式、缓存值、缓存状态和数字格式。
公式存在不代表缓存存在；缓存存在也不证明它与当前输入一致。
数值缓存 0、布尔缓存 False 与缺失缓存 None 必须分别处理。

低层接口 list_sheets 返回工作表名称列表；get_sheet_path 通过关系表找路径；
parse_cell_ref 返回从 1 开始的 (行, 列)。
extract_cells 返回以 A1 地址为键的单元格记录；
extract_rows 返回按行排序的 {row, cells} 记录列表。
共享字符串与普通/共享公式交由 openpyxl 解码。
不支持加密文件、旧式二进制 .xls、非标准迁移的 workbook.xml 入口；
特殊数据表公式不提供计算能力。不会访问外链 URL。

显式修复：
`python skills/office-white-collar/xlsx/scripts/parse_complex_excel.py "$TMPDIR/input.xlsx" --repair --output "$TMPDIR/repaired.xlsx"`。
输入与输出必须不同，不能原地修复。
报告逐个列出名称的原引用、诊断及 preserved/removed 操作。
修复针对明确的 #REF!、不存在的工作表、越界范围或非法 localSheetId。
合法区域、常量、动态表达式、外部引用和暂无法判定的表达式保留。
含有 "#REF!" 的字符串常量或合法带引号工作表名也保留。
工作簿签名包拒绝修复；修改签名文档需要专门的签名流程。
修复只改 workbook.xml 中被确认有问题的名称，其余 ZIP 成员逐字节验证。
不会通过 openpyxl 重新保存输入，所以保留公式缓存及外链缓存部件。

## 四个独立示例与验收

- create_basic_spreadsheet.py：库存数量、单价、金额与总额公式。
- styling_spreadsheet.py：合并标题、表头、金额与百分比、条件格式。
- read_existing_spreadsheet.py：通过 --input 只读检查已有文件；不传时在 TMPDIR 生成并清理合成样例。
- create_spreadsheet_with_styling.py：复用表头与高亮函数，扩展已有字体样式。

三个写表示例使用 `--output "$TMPDIR/文件名.xlsx"`。
每个写入路径都会用 openpyxl 重开检查关键内容，导入模块本身不写文件。
自动测试验证序列化后的样式及公式；屏幕上的列宽、换行、
条件色阶和日期显示仍需要负责人在真实表格软件中验收。
重算后应检查错误单元格和缓存，再将结果用于后续读取；
openpyxl 本身没有 Excel 公式计算引擎。
