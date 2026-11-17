# 编辑既有 PowerPoint 与模板

改编依据：[Anthropic pptx/SKILL.md](https://github.com/anthropics/skills/blob/e4bb5d960d87126ff3b3a8af1a104b7db67560ba/skills/pptx/SKILL.md)，Apache-2.0；原许可说明：`Complete terms in LICENSE.txt`。
本地修改：seaworld008，2026-11-18；对齐本地解包/打包接口，补充资源共享与验收说明。
SPDX-License-Identifier: Apache-2.0

## 先确定模板的结构

保留输入包，以独立输出编辑。用 `python scripts/thumbnail.py template.pptx template-grid` 查看各页布局。
缩略图用于选版式，不足以判定小字、重叠或文本溢出；视觉验收仍需逐页全尺寸图像。
核对每一页的标题、正文、备注、图片、图表、隐藏状态，形成“输入页 → 输出页 → 修改内容”的映射。
当旧 `.ppt` 需要转换时，先产生 `.pptx`，比较转换前后页数与内容；更改后缀不构成转换。
`.potx` 作为模板容器处理，输出仍需要模板时保留扩展名与正确内容类型。

## 解包、结构修改、清理、内容修改

```bash
python scripts/office/unpack.py template.pptx work
python scripts/add_slide.py work slide2.xml
```

`add_slide.py` 接收已解包目录与来源页面或版式文件；先阅读命令输出确认新页面和注册情况。
使用工具生成的页面 ID 与关系，不手工复制一个 `slideN.xml` 就当作新增成功。
通过 `ppt/presentation.xml` 的 `p:sldIdLst` 调整最终页序或移除页面入口。
关系文件将 `r:id` 映射到实际 slide 部件；页面文件编号不是显示页码。
完成增删和页序后运行 `python scripts/clean.py work`，检查没有误清理仍需使用的部件。
随后再填充最终保留页面，避免重复页面内容或修改孤立页面。

## 保留模板格式

OOXML 中可见文字在 `a:t`，但格式可能来自 `a:rPr`、段落 `a:pPr`、版式或母版。
只替换对应运行的文字，保留其字号、语言和颜色继承；不要把整段富文本压成一个字符串。
每个列表条目应有独立 `a:p`；项目符号从版式继承，必要时才显式覆盖。
文字前后空格使用 `xml:space="preserve"`；由 XML 库处理特殊字符转义。
可以使用 `defusedxml.minidom` 保留命名空间前缀进行局部修改；避免无意重写整棵树的前缀和扩展声明。
若使用 `python-pptx`，修改 `run.text` 可保留对应运行格式；`text_frame.text` 会重建运行。
它的 `add_slide(layout)` 不是复制已有页面；SVG/EMF 也不能假定能作为普通位图重新插入。
模板有四个成员槽位而实际只有三个时，删除整个多余组，包括图片和说明文字，随后检查动画关系。

## 图表与嵌入对象的共享

复制页面可能仍共享 `ppt/charts/`、嵌入工作簿或 SmartArt 部件。
在副本中修改图表前追踪页面关系：若两页指向同一图表，改其中一份会影响另一页。
需要独立图表时复制相关图表、关系及嵌入工作簿，并建立新的关系目标；同时更新内容类型。
修改系列值时同步图表缓存与嵌入数据，否则显示图像和“编辑数据”的内容会不一致。
原生图表应能在 PowerPoint 中选择系列并编辑数据；只有图片文件不能满足这一验收。
共享模板图片可复用关系；替换某一页图片前同样检查它是否被其他页引用。

## 动画、备注与母版

移除形状或整组后检查 `p:timing` 是否仍指向已删除对象。
对于不再保留动画的页面，可移除其整个动画树；若需要保留其他动画，应修复对应目标而不是全删。
备注页应属于正确页面，备注关系不应交叉到另一个 slide。
保留 `p:presentation` 的子元素顺序，不为“整齐”任意重排。
需要替换标识或页脚时优先改母版/版式中的相应对象，避免每页重复覆盖且留下旧对象。

## 打包与回归检查

```bash
python scripts/office/pack.py work output.pptx --original template.pptx
python scripts/office/validate.py output.pptx --original template.pptx
python scripts/thumbnail.py output.pptx output-grid
```

模板派生文件始终提供 `--original`，并阅读诊断；它不是忽略新错误的开关。
独立核对页数、页序、隐藏页、备注、图表数据和所有删除槽位；确认没有残留 `TODO`、示例名或空图片框。
渲染输出后逐页检查裁切、溢出、重叠、脚注与来源、字体替换、表格和图表标签；修复后重渲染。
最终在 PowerPoint 打开，确认没有修复提示；更改一处图表数据，检查仅预期页面受影响，再撤销该试改。
相关新建对象方法见 [pptxgenjs.md](pptxgenjs.md)；完整入口见 [SKILL.md](SKILL.md)。
