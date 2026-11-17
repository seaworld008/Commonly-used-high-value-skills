---
name: pptx
description: 'Create, read, edit, or combine PowerPoint (.pptx) decks, including layouts, notes, comments, and templates. Use when PowerPoint is an input or deliverable.'
zh_description: "创建和编辑 PowerPoint，检查图表、模板、字体与逐页版面。"
version: "1.1.3"
author: "Anthropic contributors; local curators"
source: "https://github.com/anthropics/skills"
source_url: "https://github.com/anthropics/skills/blob/e4bb5d960d87126ff3b3a8af1a104b7db67560ba/skills/pptx/SKILL.md"
license: "Apache-2.0"
tags: '["pptx"]'
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 5
complexity: "intermediate"
---

# PowerPoint 制作与编辑

改编自 [Anthropic pptx/SKILL.md](https://github.com/anthropics/skills/blob/e4bb5d960d87126ff3b3a8af1a104b7db67560ba/skills/pptx/SKILL.md)，Apache-2.0；原许可说明：`Complete terms in LICENSE.txt`。
本地修改：seaworld008，2026-11-17 UTC；重组入口，补充本地工具路由、原创案例和验收方法。并非上游原样发布。
SPDX-License-Identifier: Apache-2.0

## When to Use

用户要新建、编辑、合并或重排 PowerPoint，或以 PPTX 为必需交付时使用。
涉及品牌模板、母版、可编辑图表、讲稿备注与逐页版面，也属于本技能范围。
只有静态海报而无演示或编辑需求时，无需强制包装为幻灯片。
先确认是投影演讲、远程共享还是会后阅读；三者对文字密度、来源和备注的要求不同。
若用户要求“可编辑”，具体列明文字、表格、图表数据和图片裁切中哪些必须可改。

## 按任务读取

| 任务 | 入口 |
| --- | --- |
| 从零创建演示文稿 | [pptxgenjs.md](pptxgenjs.md)：原生对象与可编辑图表示例 |
| 套用模板、修改或重排页面 | [editing.md](editing.md)：关系、页序与编辑范围 |
| 整理受众、证据和叙事 | [INTAKE.md](references/creator-workflow/INTAKE.md)、[WORKFLOW.md](references/creator-workflow/WORKFLOW.md) |
| 规划图表、页面风格与验收 | [ORCHESTRATION_DATA_CHARTS.md](references/creator-workflow/ORCHESTRATION_DATA_CHARTS.md)、[STYLE-GUIDE.md](references/creator-workflow/STYLE-GUIDE.md)、[CHECKLIST.md](references/creator-workflow/CHECKLIST.md) |
| 从数据制作图形素材 | [chartkit.py](scripts/chartkit.py)，适用于不要求原生图表编辑的场景 |

以下脚本路径相对于本技能目录。`.pptx` 是 OOXML ZIP 包；模板编辑应保留母版、版式与资源关系。
制作前确认页数范围、屏幕比例、受众、关键结论、数据口径以及用户要继续编辑的对象。

## 新建稿的内容与可编辑性

先写每页要传达的一条主结论，再分配证据、图表、图像与说明。
叙事按结论、依据、影响与行动展开；标题与图表需支持同一判断。
文字、表格、普通形状使用原生对象，不将整页栅格化成一张图片。
PowerPoint 支持的数据图表优先用 `addChart()`；验收时能打开“编辑数据”。
对于网络图等缺乏原生表达的视觉，使用图像并交付其数据与生成来源，标明图像不可逐系列编辑。
每个数字注明单位、时间范围和来源；截图中的轴标签不能替代可核验数据。
参考 [pptxgenjs.md](pptxgenjs.md) 设置画布、字体、颜色、注释和图表。

## 模板编辑路径

先生成缩略图索引并查看原稿，把内容映射到适合的页面，再执行结构与文本更改。

```bash
python scripts/thumbnail.py template.pptx template-grid
python scripts/office/unpack.py template.pptx work
# 用 add_slide.py 新增页面；在 presentation.xml 完成页序与删页
python scripts/clean.py work
# 编辑最终保留页面的文本、表格、图片或图表关联
python scripts/office/pack.py work output.pptx --original template.pptx
python scripts/office/validate.py output.pptx --original template.pptx
```

使用 [add_slide.py](scripts/add_slide.py) 维护页面注册；[clean.py](scripts/clean.py) 只在工作副本中清理孤立资源。
先复制、删除和重排，再填内容；否则可能复制已填好的页面或清理掉刚新增但未登记的内容。
模板中的布局和字号优先；保留富文本运行的样式，删除多余占位组时检查图片和动画引用。
页序由 `ppt/presentation.xml` 的 `p:sldIdLst` 决定，不能按文件名排序猜测。
操作与共享图表风险详见 [editing.md](editing.md)。

## 字体与视觉设计

记录目标环境与渲染环境实际可用的字体，确认中文、英文和数字均有字形覆盖。
不要以字体名称推断系统已安装，也不要把一种环境的替代字体宽度当作另一环境的保证。
先确定标题与正文层级、留白和配色；同类型页面使用一致的标题基线与图表标签。
新建稿可从标题 32–40pt、正文 18–24pt 起步，再根据展示距离和内容密度调整；模板编辑匹配其原规格。
留出页边和内容间距；文本过多时删减或拆页，不以持续缩小字号解决。
检查内容与背景的对比度、图片清晰度、数字与单位是否断行，以及来源脚注是否碰撞图表。

## 内容、文件、视觉分别验收

1. 内容：逐页核对结论、数据、来源、页序、演讲备注和占位文本；图表数据与所述指标一致。
2. 文件：运行 `scripts/office/validate.py`，模板派生稿带 `--original`；检查退出状态与具体诊断。
3. 视觉：渲染完整的本次文件，逐页看全尺寸图像；缩略图只用于检查整体节奏和布局分布。
4. 编辑：在 PowerPoint 中选择文字、表格与图表，确认可编辑；无“修复文件”提示，主题与母版仍可使用。

```bash
python scripts/office/soffice.py --headless --convert-to pdf --outdir rendered output.pptx
pdftoppm -png -r 120 rendered/output.pdf rendered/slide
```

执行前创建独立的 `rendered` 目录；修复页面后重新生成 PDF 与相应图像，避免查看上一次的旧图。
验证器通过不等于 PowerPoint 一定无修复提示；渲染成功也不等于字体与目标 Office 完全一致。
工具缺失或宿主限制时注明未执行的层次、受影响页面及剩余检查，不把代码检查写成视觉通过。

## 完整 creator-workflow 路由

下列 11 篇是配套资产的数量，不是必须顺序执行的 11 个步骤。
按任务缺口读取；内容、证据、设计、制作和验收可以由同一执行者连续完成。

| 文件 | 何时读取 | 应留下的产物 |
| --- | --- | --- |
| [INTAKE.md](references/creator-workflow/INTAKE.md) | 明确受众、决策和交付范围 | brief、证据边界与可编辑要求 |
| [WORKFLOW.md](references/creator-workflow/WORKFLOW.md) | 组织全程依赖与迭代顺序 | 从需求到最终文件的连续记录 |
| [ORCHESTRATION_OVERVIEW.md](references/creator-workflow/ORCHESTRATION_OVERVIEW.md) | 需要职责交接或追踪跨页变更 | 稳定页面 ID、输入输出和影响范围 |
| [TEMPLATES.md](references/creator-workflow/TEMPLATES.md) | 创建 brief、证据和页面卡 | 带真实定位与状态的记录 |
| [STYLE-GUIDE.md](references/creator-workflow/STYLE-GUIDE.md) | 固定网格、字号和颜色角色 | 一致的主题参数与样页 |
| [ORCHESTRATION_DATA_CHARTS.md](references/creator-workflow/ORCHESTRATION_DATA_CHARTS.md) | 校验口径、选择图形与生成素材 | 可复算数据及图表资产清单 |
| [ORCHESTRATION_PPTX.md](references/creator-workflow/ORCHESTRATION_PPTX.md) | 选择原生制作或快速稿路线 | 源文件、对象策略与依赖记录 |
| [EXAMPLES.md](references/creator-workflow/EXAMPLES.md) | 需要合成数据贯穿示例 | 可对照的输入、图表与叙事 |
| [VIS-GUIDE.md](references/creator-workflow/VIS-GUIDE.md) | 逐页检查最终输出 | 内容、视觉和技术缺陷定位 |
| [RUBRIC.md](references/creator-workflow/RUBRIC.md) | 评分、排序修复及复评 | 十项各 10 分的评分与前三弱点 |
| [CHECKLIST.md](references/creator-workflow/CHECKLIST.md) | 包装交付与最终判定 | 文件清单、版本、检查状态和限制 |

评分总分 100，完成门槛至少 75；关键数据错误、遮挡、文件打不开或可编辑要求失效仍须阻断。
分数未达 75 时按前三项弱点修复并复评，不得用未经检查的预期结果补分。
已达 75 但缺目标应用检查时准确标记待验收；静态检测不能补作应用打开证据。

## Examples：从单页结论到模板派生稿

以下案例和关系检查代码为本地原创补充，按本文件 Apache-2.0 许可提供。
案例一：向运营负责人说明合成季度交付量 18、21、29 件，并讨论容量安排。
页面标题写“第三季度比第二季度多交付 8 件”，图表用同口径柱形并从零起始。
18、21、29 是数量，不足以证明利润或效率增长；相应推断须有成本或工时证据。
讲稿补充样本和限制，页脚标明合成数据；关键限定不能只藏在演讲者看得到的备注里。
标题、图表、来源各为可选择对象；验收时改 Q3 数据，检查图形和结论是否仍一致。

案例二：把品牌模板的六页压缩成四页，保留“封面—发现—对比—行动”的论证。
建立稳定页面 ID 与原页到新页映射，记录被删页中的证据、备注和链接去向。
重排以 `p:sldIdLst` 为准；内部跳转链接也要指向当前保留页面，而非已删除部件。
删除团队槽位时同时清理头像、姓名、职位和其动画目标，不能只删可见文字。
最后逐页检查隐藏页、讲稿、页脚日期和旧客户名称，防止模板信息残留。

### 母版、版式和页面关系

幻灯片通过关系选择版式，版式关联母版，母版再使用主题与共享资源。
字号、颜色和背景可能来自继承；本地运行未设置字号不表示没有字号。
改一页的局部覆盖和改全套母版影响范围不同，先确定需要哪一种。
复制页面文件不能自动复制其关系；新增关系还需登记内容类型与 presentation 页入口。
关系 ID 只在当前关系文件内唯一，页面 ID 在 `p:sldIdLst` 中唯一，不能混为一谈。
删页后清理资源要检查可达性；被另一页、母版或版式共享的图片不应一起删除。

下面保存为 `inspect-order.py`，用 `python inspect-order.py sample.pptx` 读取页序。
它验证显示顺序对应的 slide 目标存在；不覆盖母版完整性、动画或所有 OOXML 约束。

```python
import posixpath
import sys
from zipfile import ZipFile
from defusedxml import ElementTree as ET

p = "http://schemas.openxmlformats.org/presentationml/2006/main"
r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
with ZipFile(sys.argv[1]) as package:
    root = ET.fromstring(package.read("ppt/presentation.xml"))
    rels = ET.fromstring(package.read("ppt/_rels/presentation.xml.rels"))
    targets = {item.get("Id"): item for item in rels}
    seen = set()
    for index, slide in enumerate(root.findall(f"{{{p}}}sldIdLst/{{{p}}}sldId"), 1):
        identity = slide.get("id")
        assert identity not in seen, "duplicate slide id"
        seen.add(identity)
        relation = targets[slide.get(f"{{{r}}}id")]
        assert relation.get("TargetMode") != "External"
        target = relation.get("Target")
        path = posixpath.normpath(target.lstrip("/") if target.startswith("/")
                                  else posixpath.join("ppt", target))
        assert path.startswith("ppt/") and path in package.namelist(), path
        print(index, identity, path)
```

## 图表与图片的编辑边界

原生图表常同时有显示缓存和嵌入工作簿；只改缓存可能在编辑数据后恢复旧值。
系列名、类别顺序、轴单位和数值需要与嵌入数据同步；多轴图还要查系列所属轴。
两页共享同一图表时，先决定联动还是独立；独立编辑必须分离图表及其相关嵌入数据。
SVG 保留文本也仍是媒体，不能因此声称可按图表系列编辑；在清单中准确标注对象类型。
照片替换要保留框的尺寸、裁切和焦点，再判断是否需要调整到不同纵横比。
`a:srcRect` 表达相对原图的裁切比例；更换不同构图后沿用旧比例可能裁掉人物或标签。
不要把 contain 的留白问题用 stretch 拉伸解决；优先按 cover 裁切并核对重点区域。
共享媒体替换会影响多个引用；只改一页时新增独立媒体与关系，而不是覆盖共享文件。
图片替代文字描述信息用途，装饰图不应把文件名读给辅助工具。

## 字体、备注与来源核对

对最长标题、中文混排、负数和百分比检查实际字体覆盖，记录替代字体造成的换行变化。
母版字体调整后应复查全套，局部字体覆盖可能使部分页面不跟随主题。
备注要与对应页面绑定，重排后查备注关系和讲述顺序；不要把旧页的讲稿错贴到新结论。
每页的关键数字应可沿证据 ID 找到源数据区域及计算口径，不能只给机构首页。
将来源、单位、样本限制放在可读的位置；讲稿可放详细推导，但不能隐藏影响判断的条件。
页脚署名、图片许可和演示数据说明需在导出 PDF 中仍能读清。

## 分层验收与非镜像诊断

| 层次 | 证据 | 失败时先检查 |
| --- | --- | --- |
| 模板完整性 | 页序、母版/版式引用、备注及共享资产清单 | 删除入口、孤立关系、内容类型和继承覆盖 |
| 视觉 | 当前输出的全尺寸逐页图及总览 | 字体、文本框边距、溢出、裁切、图表标签 |
| 编辑能力 | 目标应用实际改文字、数据及图片的记录 | 原生对象类型、嵌入数据和共享关系 |
| 内容 | 与来源独立复算的数值及论证 | 分母、排序、时间范围和标题断言 |

若缩略图看起来正确而投影小字不可读，应调信息密度和层级，而不是提高缩略图分辨率交差。
若图表显示正确但编辑数据不一致，优先查嵌入工作簿与缓存，不要只重绘预览。
若只改一页却另一页也变化，沿关系检查共享图表、媒体或母版，确认是否需要独立副本。
若备注错页，检查 slide 到 notesSlide 的关系，而不是按 notes 文件编号重新排序。
若 PowerPoint 提示修复而其他库可读，保留修复日志并查图表轴、关系及元素顺序。
每次修复重建受影响页预览；共享字体、主题或母版变化则重新检查全部页面。
交付文件、PDF 和预览要来自同一最终版本；任何缺失层次写明未验证及具体复核动作。
