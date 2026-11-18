---
name: docx
description: 'Create, read, edit, or review Word documents (.docx), including styles, tables, headers, tracked changes, and comments. Use when Word is the input or required deliverable.'
zh_description: "创建、编辑和检查 Word 文档、修订、批注与排版。"
version: "1.1.3"
author: "Anthropic contributors; local curators"
source: "https://github.com/anthropics/skills"
source_url: "https://github.com/anthropics/skills/blob/e4bb5d960d87126ff3b3a8af1a104b7db67560ba/skills/docx/SKILL.md"
license: "Apache-2.0"
tags: ["docx"]
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 5
complexity: "intermediate"
---

# Word 文档制作与审阅

本指南改编自 Anthropic 的 [docx/SKILL.md](https://github.com/anthropics/skills/blob/e4bb5d960d87126ff3b3a8af1a104b7db67560ba/skills/docx/SKILL.md)，许可 Apache-2.0；原许可说明为 `Complete terms in LICENSE.txt`。
本地修改：seaworld008 于 2026-11-17 UTC 重组方法、对齐本仓库辅助程序，并补充原创案例与验收步骤。并非上游原样发布。
SPDX-License-Identifier: Apache-2.0

## When to Use

输入或交付是 Word 文档，且需要正文、样式、目录、表格、批注或修订时使用。
普通通知、项目报告和操作手册可走新建路径；合同审阅与模板微调走保留原包的编辑路径。
“导出一份 PDF”若同时要求可编辑 Word 源稿，也属于本技能范围。
只有纯文本摘要且不要求 Word 结构时，无需构造 OOXML 包。
先区分三种目标：内容正确的普通文档、沿用模板的排版稿、保留审阅证据的修订稿。
同一交付可同时满足三者，但验收证据分别记录，不能靠一张首页预览代替。

## 选择工作路径

| 任务 | 方法与入口 |
| --- | --- |
| 新建 `.docx` | 用 `docx` Node 库构造段落、样式、表格；示例见 [EXTENDED.md](EXTENDED.md#新建文档示例) |
| 修改既有文档 | 解包，定位相关 XML 节点，最小范围修改，重新打包 |
| 审阅并显示修改 | 在 XML 中保留作者、时间和插入/删除边界，按原稿验证 |
| 加批注或回复 | 使用 [comment.py](scripts/comment.py)，再放置锚点 |
| 检查版面 | 使用 [render_docx.py](scripts/render_docx.py) 渲染并逐页检查 |
| 检查包结构 | 使用 [validate.py](scripts/office/validate.py)，结合原稿比较 |

以下命令路径均相对于本技能目录。`.docx` 是 OOXML ZIP 包；改扩展名不会把 PDF 或旧 `.doc` 转成 OOXML。
需要旧格式转换时先生成新的 `.docx`，确认内容完整后再进入编辑流程。

## 新建时的布局约束

先确定纸张、页边距和正文区域，再安排标题、列表、表格、页眉页脚与图片。
页尺寸使用 DXA，1440 DXA 为一英寸；不要依赖不同生成器的默认纸张。
为每一级标题设置字体、段前段后间距及与下段同页；目录使用真实标题层级。
列表使用编号定义，避免输入装饰性圆点来模拟项目符号。
表格同时设置列宽与单元格宽度，所有列之和等于表宽，表宽不得超出正文区域。
用独立段落表达段落边界；分页符置于段落内；图片声明类型并保持纵横比。
新建的表格、目录和页码都应能在 Word 中继续编辑。
详细代码及表格验收见 [EXTENDED.md](EXTENDED.md)。

## 编辑与修订

```bash
python scripts/office/unpack.py original.docx work
# 编辑 work/word/document.xml 及确有需要的关联部件
python scripts/office/pack.py work edited.docx --original original.docx
python scripts/office/validate.py edited.docx --original original.docx
```

可见句子可能横跨多个 `w:r`；先找段落和运行边界，不能假定 XML 中有整句连续文本。
`unpack.py` 提供 `--merge-runs` 与 `--simplify-redlines`；须保留原修订边界时先确认选项含义，不能把规范化结果当原始证据。
更改普通文本时保留同一运行中的格式和空格属性；避免全包重新格式化 XML。
修订使用 `w:ins` / `w:del` 包含受影响运行，并设置 `w:id`、`w:author`、`w:date`。
删除内容使用 `w:delText`；删除段落标记与删除段内文字是两件事，详见 [修订验收](EXTENDED.md#修订与接受视图)。

```bash
python scripts/office/validate.py edited.docx --original original.docx --author Reviewer
```

不能以“接受修订视图看起来正确”证明所有变动都已跟踪；同时检查拒绝视图应恢复原文。
需要接受全部修订的独立副本时，可用 [accept_changes.py](scripts/accept_changes.py) 的 `input_file output_file` 接口；保留带修订版本供审阅。

## 批注必须有可见锚点

```bash
python scripts/comment.py work 12 "请核对交付日期" --author Reviewer --initials RV
python scripts/comment.py work 13 "已确认" --author Editor --initials ED --parent 12
```

本地 CLI 显式接收整数 `comment_id`；先检查现有 ID，避免碰撞。
批注正文、关系和内容类型齐全后，还须在文档中放置匹配 ID 的范围起点、终点和引用。
批注验收应在 Word 审阅面板定位到目标文字，并能看到回复的父子关系。
锚点 XML 及关联部件清单见 [EXTENDED.md](EXTENDED.md#批注关联)。

## 交付前的三层检查

```bash
python scripts/office/validate.py edited.docx --original original.docx
python scripts/render_docx.py edited.docx --output_dir rendered --dpi 120
```

1. 内容：标题、表格数字、链接、页眉页脚与原始要求相符；无占位文本或意外遗漏。
2. 结构：读取验证退出状态及具体错误；审阅修订时显式启用拒绝视图检查，修复后重新打包验证。
3. 视觉：检查本次输出的每页图像，关注表格跨页、孤立标题、截断、批注与页码。

本地渲染依赖 LibreOffice、PyMuPDF、Pillow 与 defusedxml，不依赖 Poppler；缺少依赖或宿主限制导致转换失败时，记录“未渲染”，不据此声称视觉通过。
XML 验证通过不能证明分页正确，也不能证明 Word 打开时不会提示修复；最终应用检查步骤见扩展指南。

## Examples：普通报告到复杂长文档

以下案例和检查片段为本地原创补充，按本文件 Apache-2.0 许可提供。
案例一：制作两页项目周报，正文包含一段摘要、三个真实一级标题和一张进度表。
先用纸张宽减左右页边距算正文宽；例如 12240 − 1620 − 1620 = 9000 DXA。
进度表三列可设 1800、4500、2700 DXA；表宽、网格列宽、单元格宽度应一致。
表格中的日期保留文字或域的明确语义；“未确认”不能被空白或零日期替代。
验收关注摘要是否完整、表头是否重复、状态说明是否可编辑，以及第二页是否出现孤立标题。

案例二：将长报告整理为三级标题、自动目录、横向附录表和分节页码。
先建立标题样式映射，再应用到原段落；不能只把字号相似的行全部当标题。
目录域的结果需要更新后再检查；域代码存在不代表目录文字和页码已刷新。
分节符决定纸张方向及页眉页脚继承，分页符只决定下一页开始位置，二者不可互换。
检查横向附录前后两节的纸张、页码起始值和链接到前一节状态。
不应因一张宽表把整份报告变成横向；可拆表、分节或缩短表头，但须保留单位。

### 表格对象与跨页边界

| 对象 | 编辑时要保留 | 输出中的检查方式 |
| --- | --- | --- |
| `w:tblGrid` | 逻辑列宽及顺序 | 各列与表头对齐，宽度不溢出正文 |
| `w:gridSpan` | 横向合并覆盖的网格数 | 多级表头仍对应正确数据列 |
| `w:vMerge` | 合并起点及后续连续单元格 | 跨行标题无重复文字、无断裂含义 |
| `w:tblHeader` | 连续的表头行 | 跨页后重复表头，不把数据行当表头 |
| `w:cantSplit` | 不允许拆行的实际业务需要 | 长行能放下一页，避免异常留白 |
| `w:trHeight` | 精确值与最小值的区别 | 多行内容未被固定高度截断 |

表格宽度正确仍可能溢出：检查单元格边距、段落缩进、不可断长串和内嵌图片。
长 URL 可以设置合理换行或显示短标签；不要删除链接目的地址来解决宽度问题。
合并单元格中的说明应放在正确锚点，并检查读屏或复制文本的逻辑顺序。
只把确需同页的小块设为不拆分；整张长表逐行绑定会造成分页空白。

## 包内关系与定点编辑

`word/document.xml` 的 `r:id` 由 `word/_rels/document.xml.rels` 解释。
页眉图片的关系属于页眉自己的关系表；不能从正文关系表随意借用同名 ID。
内部关系目标按所属部件路径解析；检查存在性，也检查内容类型与实际部件一致。
新增图片需同时具备媒体文件、关系、引用和内容类型；漏一项可能只在 Word 打开时暴露。
样式 ID、编号 ID、关系 ID 和批注 ID 各有作用域，不应混用一个全局编号器。
编辑前后列出新增、删除和变化的包成员；意外消失的页眉或脚注需要追查。
纯文本读取不能证明脚注、文本框、域结果和页眉内容均被覆盖，应按需求逐部件盘点。

下面片段保存为 `inspect-text.py`，用 `python inspect-text.py sample.docx` 检查合成或可信小文档。
它只提取正文主部件的普通文本与修订文本计数，不是完整性验证器或拒绝视图实现。

```python
import sys
from zipfile import ZipFile
from defusedxml import ElementTree as ET

ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
with ZipFile(sys.argv[1]) as package:
    root = ET.fromstring(package.read("word/document.xml"))
paragraphs = root.findall(".//w:body/w:p", ns)
for index, paragraph in enumerate(paragraphs, 1):
    runs = paragraph.findall(".//w:t", ns)
    text = "".join(node.text or "" for node in runs)
    deletions = paragraph.findall(".//w:delText", ns)
    print(index, repr(text), "deleted_runs=", len(deletions))
```

同一个可见词被拆成三段运行并不意味着内容损坏，可能分别承载语言、加粗或书签边界。
定位替换应先拼接用于搜索的段落文本，再映射回运行；不能用字符串替换整个 XML。

## 审阅案例：作者、锚点与拒绝结果

案例三：把“首批交付 12 台”改为“首批交付 15 台”，同时批注要求确认验收日期。
只对 12 的删除和 15 的插入记录修订，保持其余文字、标点、段落样式不变。
用真实本次审阅作者替换示例 `Reviewer`，保留原稿已有其他作者的修订。
`--author Reviewer` 显式启用修订检查，不按该姓名过滤未跟踪改动；不要把旧修订作者重写成本次作者。
拒绝本次更改后应恢复“首批交付 12 台”；接受后应显示“首批交付 15 台”。
原稿已有未决修订时，先明确比较的是哪一基线视图，不能默认它们已被接受。
仅新增批注而未修改正文时，不应凭空制造修订或要求一个不存在的修订作者。

批注若针对“验收日期”四字，应使起止标记只围住该范围，引用置于相应范围之后。
重复文字场景需用段落位置和上下文定位，不能把锚点放在第一次同词出现的位置就算成功。
跨段或跨表格范围需在目标应用验证；无法稳定定位时优先缩小到有意义的连续范围。
回复使用新批注 ID 并指向既有父批注，不能只在正文写“回复：”模拟线程。
删除被批注文字时明确保留、迁移或移除批注的意图，再核对范围和批注部件一致。

`--original` 提供结构错误基线比较，不表示普通编辑必须包含修订。
基线允许排除继承的 XSD 问题；“相对基线通过”不能写成整个包完全符合 XSD。
有修订且需检查拒绝结果时显式给 `--author`；无修订的普通编辑使用结构校验路径。
若打包或校验误把普通稿当修订稿，保留诊断并修正工具契约，不以关闭验证来交付。

## 渲染边界与故障归因

渲染器不执行输入宏、嵌入执行对象或远程资源更新；不要为了出图开启这些能力。
普通 HTTPS、mailto 超链接是文档注释，可保留而不 fetch；外链图片和远程模板另属资源加载。
动态域、嵌入对象等不受支持时记录部件与拒绝原因，不把删除内容后的产物冒充完整原稿。
应在新的输出目录运行本次渲染，核对产物页数、时间与当前交付版本，再逐页查看。
若输出页数异常，先查分节、分页和字体替换，再查图片尺寸及表格不拆行设置。
若目录错页，先更新目录域并重渲染；不要直接改目录结果文字掩盖域未更新。
若批注存在但看不到锚点，先查匹配 ID 的三个标记，再查关系和批注扩展元数据。
若拒绝视图丢标点，查标点是否误包在插入节点；若多空段，查段落标记修订。
若只在某一环境换行不同，记录字体实际解析和渲染器版本，再决定排版修正范围。
最终交付应标明逐页检查范围、未跑的 Word 应用检查和剩余问题，而非只写“文件生成成功”。
