<!-- Copyright (c) 2026 seaworld008 -->
<!-- SPDX-License-Identifier: MIT -->

# 可编辑 PPTX 的制作路线

从 brief 的可编辑要求倒推工具。先检查宿主已有能力，再使用当前可用的实现；
本文中的路线不是安装指令，也不假定任意命令已存在。

## 路线选择
| 需求 | 可选路线 | 交付前必须验证 |
| --- | --- | --- |
| 原生文本、形状、表格、数据图表 | 已安装的 PptxGenJS 或 python-pptx | 对象类型、内嵌数据、修改后的重排 |
| 快速验证叙事、简单讲义、固定阅读稿 | 已安装的 Marp CLI | 当前版本支持的导出格式和实际输出 |
| 对已有品牌模板精细编辑 | 宿主可用的模板编辑工具 | 母版、字体和关系未损坏 |

可分别用下列只读检查了解依赖：
```sh
python -c "import pptx; print(pptx.__version__)"
node -e "console.log(require.resolve('pptxgenjs'))"
command -v marp
```
某项失败只表示该路线不可立即执行；不能据此声称另一项已安装。
本地没有依赖时保留源稿、数据与未完成说明，按授权选可用工具。

## 直接制作的对象策略
标题、正文、注释和来源用原生文本框；比较表优先用原生表格。
流程图用形状和连接线，尽量保留可选择与可修改的对象。
需要改数据的图表用库的原生图表接口，把数据嵌入文件。
照片与渲染图可以是图片；整页截图只能满足固定阅读，不能满足页面元素可编辑。
在资产台账标注每个图表是原生图表、SVG 还是 PNG，避免混淆。

## python-pptx 最小原生示例（仅在已安装时）
以下数据完全合成。示例将可编辑标题、来源和原生柱状图写入 TMPDIR。
```python
import os
from pathlib import Path
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches, Pt

root = Path(os.environ["TMPDIR"])
deck = Presentation()
deck.slide_width, deck.slide_height = Inches(13.333), Inches(7.5)
slide = deck.slides.add_slide(deck.slide_layouts[6])
title = slide.shapes.add_textbox(Inches(.55), Inches(.35), Inches(12.2), Inches(.8))
title.text_frame.paragraphs[0].text = "Synthetic: training requests lead the pilot"
title.text_frame.paragraphs[0].font.size = Pt(30)
data = CategoryChartData()
data.categories = ["Training", "Support", "Planning"]
data.add_series("Requests", (14, 9, 6))
slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED,
    Inches(.8), Inches(1.5), Inches(11.7), Inches(4.9), data,
)
note = slide.shapes.add_textbox(Inches(.55), Inches(6.8), Inches(12), Inches(.4))
note.text = "Source: synthetic demonstration data; requests per team"
note.text_frame.paragraphs[0].font.size = Pt(14)
deck.save(root / "synthetic-editable.pptx")
```
生成后检查 PPTX 内的图表与嵌入工作簿，并在目标应用修改一个数值验证更新。
示例不是完整视觉验收，也未包含任务所需的全部备注与无障碍设置。

## PptxGenJS 路线
使用当前项目已有版本与其对应接口，集中定义页面大小、字体、颜色和边距。
按页面卡片调用文本、形状、表格与原生图表构建方法，等待写入完成后再验收文件。
将数据计算与绘图参数分离，便于复算；不要把整页 HTML 截图作为默认可编辑交付。
记录运行时、包版本、源代码入口和生成文件路径。

## Marp 快速稿路线
Markdown 一段对应一页，用页分隔线控制结构，先验证断言顺序和讲述时间。
只有 command -v marp 成功后才运行 marp --help，使用该版本明确列出的选项。
可从[示例稿](EXAMPLES.md)开始；未安装时源稿仍可交付为待导出草稿。
Marp 的 PDF/PPTX 导出能力可能依赖浏览器或运行环境；未实际导出不要写“已完成”。
即便生成 PPTX，也必须检查文本和图表是否为原生对象，不能承诺默认可编辑。

## 文件与应用检查
制作、渲染和最终应用检查是三项独立证据。
解包检查只能证明部分结构有效；渲染只证明该渲染器的显示结果。
目标应用中打开、选择对象、编辑图表数据并保存，才验证实际编辑体验。
任何未执行步骤写入[交付清单](CHECKLIST.md)。
