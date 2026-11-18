---
name: xlsx
description: 'Create, read, edit, repair, or convert spreadsheet files (.xlsx, .xlsm, .csv, .tsv), including formulas, charts, and formatting. Use when a spreadsheet is the main input or deliverable.'
zh_description: "创建、编辑和检查电子表格、公式、样式与重算结果。"
version: "1.1.3"
author: "Anthropic contributors; local curators"
source: "https://github.com/anthropics/skills"
source_url: "https://github.com/anthropics/skills/blob/e4bb5d960d87126ff3b3a8af1a104b7db67560ba/skills/xlsx/SKILL.md"
license: "Apache-2.0"
tags: ["xlsx"]
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 5
complexity: "intermediate"
---

# 电子表格制作、修改与验证

改编自 [Anthropic xlsx/SKILL.md](https://github.com/anthropics/skills/blob/e4bb5d960d87126ff3b3a8af1a104b7db67560ba/skills/xlsx/SKILL.md)，Apache-2.0；原许可说明：`Complete terms in LICENSE.txt`。
本地修改：seaworld008，2026-11-17 UTC；重写示例，对齐本地重算状态、回执与缓存验收，并补充原创核算案例。并非上游原样发布。
SPDX-License-Identifier: Apache-2.0

## When to Use

电子表格是主要输入或交付，任务包含数据整理、公式、工作表结构、图表或格式时使用。
财务模型、进度跟踪、跨期汇总和既有工作簿修复都需明确输入区、公式区及验收数值。
CSV/TSV 清洗可走文本路径；只有要求保留多表、样式或公式时才生成工作簿。
先区分“读取分析”“编辑另存”“重算求值”和“修复结构”，不要因读取而保存原始 input。
用户只要求核查时保留原文件字节不变，修复建议与修复副本分开交付。

## 按任务选择工具

| 任务 | 入口 |
| --- | --- |
| 保留公式、样式与工作表结构 | `openpyxl`；先读取公式和缓存两种视图 |
| 大批量整理数据 | `pandas` 进行表格清洗；写回前检查数据类型与样式需求 |
| 基础创建与读取 | [create_basic_spreadsheet.py](references/openpyxl-examples/create_basic_spreadsheet.py)、[read_existing_spreadsheet.py](references/openpyxl-examples/read_existing_spreadsheet.py) |
| 样式与可读性 | [styling_spreadsheet.py](references/openpyxl-examples/styling_spreadsheet.py)、[create_spreadsheet_with_styling.py](references/openpyxl-examples/create_spreadsheet_with_styling.py) |
| 格式化与敏感性表 | [create_formatted_excel.py](scripts/create_formatted_excel.py)、[formatting-reference.md](references/excel-automation/formatting-reference.md) |
| 读取复杂 OOXML 或检查定义名称 | [parse_complex_excel.py](scripts/parse_complex_excel.py) |
| 公式求值与缓存检查 | [recalc.py](scripts/recalc.py) |

脚本路径相对于本技能目录。CSV/TSV 只有文本字段；工作表、公式样式、图表与多表关系需要 XLSX 等适当容器。
先确认表名、表头、单位、日期约定、缺失值与用户可编辑区域；编辑既有工作簿时保留其命名和样式惯例。

## 数值、公式与来源

输入数据保留数值类型：百分比存小数，日期存日期值，标识符和带前导零的编码保留文本。
公式引用有标签的输入单元格，不把同一假设重复写成多个公式常量。
同一行的跨期公式检查相对与绝对引用；分母为零的处理必须符合业务含义，不能用 `IFERROR(...,0)` 掩盖未知值。
对每个外部数值注明来源、时间、单位与适用范围，可放在邻近说明格、批注或 Sources 页。
用户提供的数据直接标“用户提供”；合成演示数据明确标“合成”，不虚构引用。
新模板应说明输入区并提供明确示例；修改真实表格不擅自加入演示行。

## 独立编写的公式与样式示例

以下 Python 为本地原创，Copyright (c) 2026 seaworld008；SPDX-License-Identifier: MIT。
保存为 `make-workbook.py`，执行 `python make-workbook.py output.xlsx`；此步写入公式但不计算它。

```python
# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
import sys
from pathlib import Path
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Font, PatternFill, Alignment

destination = Path(sys.argv[1])
book = Workbook()
sheet = book.active
sheet.title = "Delivery"
sheet.append(["期间", "计划数量（件）", "实际数量（件）", "完成率"])
sheet.append(["示例期", 20, 18, "=C2/B2"])
sheet.append(["合计", "=SUM(B2:B2)", "=SUM(C2:C2)", "=C3/B3"])
for cell in sheet[1]:
    cell.font = Font(name="Arial", bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="245269")
    cell.alignment = Alignment(wrap_text=True)
for row in sheet.iter_rows(min_row=2):
    for cell in row:
        cell.font = Font(name="Arial", color="172D40")
        cell.number_format = "0.0%" if cell.column == 4 else "0"
for address in ("B2", "C2"):
    sheet[address].fill = PatternFill("solid", fgColor="FFF1B8")
    sheet[address].comment = Comment("来源：本地合成示例；非实际业务数据。", "seaworld008")
for column, width in {"A": 16, "B": 24, "C": 24, "D": 18}.items():
    sheet.column_dimensions[column].width = width
sheet.freeze_panes = "B2"
sheet.auto_filter.ref = "A1:D2"
sources = book.create_sheet("Sources")
sources.append(["范围", "说明"])
sources.append(["Delivery!B2:C2", "合成示例。黄色单元格为输入；数量须为非负数且计划数大于零。"])
book.save(destination)
book.close()
```

验收：四个公式仍是公式；B2、C2 是数值且有来源批注；完成率格式为百分比。
重算后 D2 和 D3 应为 0.9，B3 为 20，C3 为 18；改 C2 后相关公式应更新。

## 读取和保留既有工作簿

分别用 `load_workbook(path, data_only=False)` 查看公式，用 `data_only=True` 查看已有缓存。
缓存读取视图中公式已不可见；不能保存该视图代替原文件，否则公式会被数值覆盖。
openpyxl 新写入的公式通常没有缓存，`data_only=True` 得到 `None` 不能解释成数值零。
公式结果为空字符串也可能读成 `None`；应结合 OOXML 单元格类型、公式与缓存部件区分真空字符串和缺缓存。
合并区域只写左上角锚点；逐格写入合并区域的其余位置会失败。
宏工作簿读取需按需要使用 `keep_vba=True`，保留 VBA 不等于授权执行输入文档宏。
先检查图形、切片器和富文本等对象是否被当前库完整支持；需无损保留时采用局部 OOXML 编辑并与原包比较。
跨表引用的工作表名包含空格时加单引号；公式名称、参数数目与计算引擎兼容性需实际验证。
不能把某个引擎未支持的函数改成硬编码数值来假装通过重算。

## 重算的成功条件

```bash
python scripts/recalc.py output.xlsx 60
```

本地 `recalc(filename, timeout=...)` 使用同一个任务私有 `UserInstallation`：先初始化配置，再安装本地受控宏。
宏同步加载指定文档，禁止输入文档宏执行及外链更新，重算并保存，成功保存后才写回执。
它不应写用户的真实 LibreOffice 宏目录；初始化和实际执行共享超时预算。
只有保存回执与实际公式缓存检查均成功，才接受结果；进程退出零、存在旧缓存或文件时间改变均不够。
维护者已在官方稳定 LibreOffice 26.8.3 实际验证该流程；宿主 Alpha 未产生受支持回执时应报告 `unverified`，不能宣称重算成功或改写用户宏来规避。
这是既有运行证据的适用范围；当前环境是否成功仍以本次回执、缓存和日志为准。

| `status` | 含义与处理 |
| --- | --- |
| `success` | 回执有效，缓存检查完成且没有已检测公式错误；仍需业务数值验算 |
| `errors_found` | 缓存中发现错误，查看 `total_errors` 与 `error_summary` 中的位置，修正公式或数据 |
| `unverified` | 缺少回执或必要缓存，不能证明本次求值；不得当作无错误成功 |
| `recalculation_failed` | 初始化、启动、超时或处理失败；查看 `error` 与适用的 `returncode` |

本地 CLI 对错误、缺缓存和未验证结果返回非零；同时解析 JSON 状态，不能只检查其中一个信号。
检查 `total_formulas`、`total_errors`、`missing_cached_values`、`missing_cache_locations` 等适用字段；字段集合随结果阶段而异。
数字零、布尔假和有效空字符串都是可能的计算结果；不要使用 Python 真值判断来统计缺失缓存。
重算绿色结果仅说明公式可求值，不能发现范围错一行或引用了错误输入；用独立预期值核对关键单元格。

## 格式、图表与交付验收

数值保留单位并使用相应 `number_format`；不要把货币、百分比与日期都转成展示字符串。
冻结表头、设置列宽和必要换行；颜色含义给出图例，不能只靠颜色区分输入与公式。
新图表显式检查标题、图例、轴、单位与标签，数据系列与来源范围一致；在目标应用中确认图表仍可编辑。
格式器可按 `apply_header_row`、`apply_data_row`、`apply_input_cell`、`add_sensitivity_table` 与 `auto_column_widths` 组合使用，接口详见对应脚本。
复杂解析器提供 `verify_format`、`list_sheets`、`get_sheet_path`、`extract_cells`、`extract_rows`；修复定义名称时使用 `fix_defined_names(input_path, output_path)` 另存副本并验证。
交付前重新读取文件，核对表名、行数、类型、公式、来源、关键数值和样式；在 Excel/LibreOffice 中检查打开无修复提示、无截断且计算可更新。
将静态检查、合成替身回归与实际 Office 重算分开记录；缺少真实渲染或计算条件时，明确留下未执行的检查项。

## Examples：类型、跨期与敏感性

以下补充案例和 Decimal 核算代码为本地原创，按本文件 Apache-2.0 许可提供。
案例一：导入订单编码 `001204`、数量 8、单价 12.50 元及带时区的收件时间。
编码存文本，数量存整数，单价存数值并格式化两位小数；不能以显示为“001204”掩盖底层编码已变。
Excel 日期值没有时区语义；将时间统一到约定时区后写入日期值，并在邻列保留时区或原始 ISO 文本。
跨夏令时的本地时间可能重复或不存在，先用原始偏移确认实际时刻，不能凭单元格显示猜测。
检查工作簿日期系统，1900 与 1904 系统不能不加转换地交换序列值。
金额区分元与万元，比例区分 0.15 与 15；百分比格式只改变显示，不改变业务单位。

案例二：核对合成两期库存，期初 100、入库 25、出库 18，期末应为 107。
下期期初必须连接上期期末；同时检查期初＋入库－出库＝期末以及跨期期初衔接。
公式能算出数值仍可能错引前两期；用独立平衡式和已知边界值验算，不复制工作簿同一引用逻辑。
更换筛选、插入行、隐藏行和扩展月份后，复查合计范围是否含全部记录且没有重复计入小计。
比较前后两期时统一币种、税口径和期间长度，不能把格式一致当成口径一致。

案例三：合成销量 100 件、单价 12 元、单位成本 7 元、固定成本 200 元，利润应为 300 元。
敏感性表的行是销量 80/100/120，列是单价 11/12/13；每格独立应用同一业务定义。
中心格应等于基础利润；销量固定 100 时单价每升 1 元利润升 100 元。
这是业务关系检查，能发现轴标签互换或绝对引用锁错，即使所有公式均无错误值。
以下保存为 `truth.py`，执行 `python truth.py`；它不打开 Office，也不为 XLSX 写入计算缓存。

```python
from decimal import Decimal as D

def profit(quantity, price):
    return D(quantity) * (D(price) - D("7")) - D("200")

quantities = (80, 100, 120)
prices = ("11", "12", "13")
truth = [[profit(q, p) for p in prices] for q in quantities]
assert D("100") + D("25") - D("18") == D("107")
assert truth[1][1] == D("300")
assert truth[1][2] - truth[1][1] == D("100")
assert truth[2][1] - truth[1][1] == D("100")
for quantity, row in zip(quantities, truth):
    print(quantity, [str(value) for value in row])
```

预期三行为 120/200/280、200/300/400、280/400/520；用这些值对照重算后的敏感性区域。
对金额规定舍入发生在哪一步；独立真值按同一业务舍入规则计算，不能只凭显示小数相同判定。

## OOXML 读取边界与结构修复

| 情形 | 应保留的区分 | 核对方式 |
| --- | --- | --- |
| 共享公式 | 锚点公式与跟随单元格的共享索引 | 展开相对引用后核对实际坐标，不能把空公式文本当空格 |
| 稀疏工作表 | 省略的行/单元格与显式空值 | 以单元格坐标定位，不能把 XML 顺序当连续列号 |
| 共享字符串 | 字符串索引与字符串实际内容 | 解析 sharedStrings，含富文本时保留文字顺序 |
| 合并区域 | 左上角值与其余占位格 | 不把空占位计作缺失记录或自动向下填充 |
| 公式缓存 | 公式定义与上次计算值 | 分别读取并记录缓存是否存在、类型及本次计算证据 |
| 定义名称 | 全局名称与 sheet 局部作用域 | 核对引用范围、localSheetId、有效表名及用途 |

稀疏表末端坐标很大时限制读取区域，不遍历一个巨大的空矩形来“填齐”数据。
解析器按当前实际接口使用；若发现稀疏遍历问题，记录最小样本交给实现修复，不在指南里复制缺陷算法。
数组公式、动态数组和共享公式的保留能力依赖编辑库；输出后核对其范围与相关元数据。
空格、空字符串、未生成缓存、数值零和布尔假须分别解释；统计缺失值前先建立字段规则。
外部链接可能保有旧缓存；不授权联网更新，也不能据旧缓存推断源工作簿当前数值。
保留 VBA 的容器不等于可运行输入宏；重算过程应继续禁止输入宏与外链更新。
保护、签名、切片器、透视缓存等内容若无法无损处理，保留原包并明确编辑范围及限制。

定义名修复先只读诊断，再使用 `fix_defined_names(input_path, output_path)` 写到不同路径。
删除名称前检查公式、打印区域、图表和数据验证是否依赖它，不能只看名称字符串是否陌生。
名称引用 `#REF!` 或失效表名需定位业务含义；自动删除并不等于恢复正确范围。
验收比较输入哈希未变、修复副本能读取、合法名称仍在及关键公式数值未受影响。
若修复后仍需手工确定范围，标记未完成，不用重算成功掩盖结构含义未恢复。

## 故障归因与验收记录

重算后全是零时先核对缓存类型、原始输入及单位，不能先把零当缺缓存或强行填值。
出现 `#NAME?` 时检查函数拼写、定义名及引擎支持；出现 `#REF!` 时查删除的表、列和名称。
结果无报错但跨期不平衡时查遗漏行、重复小计和锁定引用，重算不会修正这些业务错误。
公式正确但显示为日期时检查 number_format；日期显示正确但时刻错误时检查时区转换。
导出 CSV 后重新导入要复查前导零、长编码和公式样式文本；文本容器不保留原工作簿类型约束。
记录本次输入版本、输出路径、关键真值、实际回执状态与未执行的应用检查，避免沿用旧结果。
