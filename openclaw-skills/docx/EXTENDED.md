# Word 细节与可执行示例

改编依据：[Anthropic docx/SKILL.md](https://github.com/anthropics/skills/blob/e4bb5d960d87126ff3b3a8af1a104b7db67560ba/skills/docx/SKILL.md)，Apache-2.0；原许可说明：`Complete terms in LICENSE.txt`。
本地修改：seaworld008，2026-11-18；重新编排并补充本地接口、示例与检查方法。
SPDX-License-Identifier: Apache-2.0

## 新建文档示例

以下 JavaScript 为本地独立编写，Copyright (c) 2026 seaworld008；SPDX-License-Identifier: MIT。
保存为 `create-document.cjs`，在已有 `docx` 包的环境用 `node create-document.cjs output.docx` 执行。
本次重建仅检查其语法；未在缺少 `docx` Node 包的环境声明生成成功。

```javascript
// Copyright (c) 2026 seaworld008
// SPDX-License-Identifier: MIT
const fs = require("node:fs/promises");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, HeadingLevel, ShadingType,
} = require("docx");

async function main() {
  const destination = process.argv[2];
  if (!destination) throw new Error("Usage: node create-document.cjs output.docx");
  const widths = [1800, 7200];
  const rows = [
    ["项目", "验收依据"],
    ["样本文档", "标题与表格保持可编辑，表格不超过正文宽度。"],
  ];
  const table = new Table({
    width: { size: 9000, type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((values, index) => new TableRow({
      tableHeader: index === 0,
      children: values.map((text, column) => new TableCell({
        width: { size: widths[column], type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: index === 0 ? "E7EEF5" : "FFFFFF" },
        children: [new Paragraph({ children: [new TextRun({ text, bold: index === 0 })] })],
      })),
    })),
  });
  const document = new Document({
    styles: {
      default: {
        document: { run: { font: "Arial", size: 22 } },
        heading1: {
          run: { font: "Arial", size: 32, bold: true },
          paragraph: { spacing: { before: 160, after: 160 }, keepNext: true },
        },
      },
    },
    sections: [{
      properties: { page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1620, bottom: 1440, left: 1620 },
      } },
      children: [
        new Paragraph({ text: "交付核对", heading: HeadingLevel.HEADING_1 }),
        new Paragraph("此示例用于检查结构和排版；中文字体是否可用须在目标环境确认。"),
        table,
      ],
    }],
  });
  await fs.writeFile(destination, await Packer.toBuffer(document));
}
main().catch((error) => { console.error(error.message); process.exitCode = 1; });
```

宽度验算：12240 − 1620 − 1620 = 9000 DXA，列宽 1800 + 7200 = 9000。
若改为横向纸张，应按 `docx` 的 `PageOrientation.LANDSCAPE` 语义传参，并重新核对正文宽度。
颜色、字体和纸张应服从用户模板；示例中的 Arial 不代表目标机器必有中文字形。

## 表格与样式验收

| 部件 | 正向验收 | 常见反例 |
| --- | --- | --- |
| 标题 | 导航窗格显示正确层级；与下段同页 | 仅放大加粗普通段落，目录漏项 |
| 表格 | 列宽与单元格宽度一致；长行跨页可读 | 百分比宽度与固定宽度混用导致布局漂移 |
| 长表 | 重复表头；合并单元格无丢失 | 复制视觉表头但没有设置重复表头属性 |
| 列表 | 真正编号；续接或重新开始符合要求 | 文字前手工加圆点，换行后缩进错位 |
| 页码 | 使用域，前后章节连续性正确 | 手写数字，增页后页码失真 |
| 图片 | 保持比例、清晰度与替代文字 | 拖伸图像或把正文截成图片 |

生成器保存成功后，仍要用目标应用更新目录与域，检查目录页码和实际分页一致。

## OOXML 包编辑

先使用 [unpack.py](scripts/office/unpack.py) 得到工作目录；使用 [pack.py](scripts/office/pack.py) 产生新输出。
编辑通常涉及 `word/document.xml`；样式、编号、页眉页脚、图片各有自己的部件与关系。
添加部件后检查 `_rels/.rels`、相应部件旁的 `_rels/*.rels` 与 `[Content_Types].xml`。
关系目标应解析到正确包内位置；ID 在所属关系表内唯一，不要求跨整个包统一编号。
文本前后空格需要 `xml:space="preserve"`；使用 XML 转义，不将 `&` 或 `<` 直接拼入文本。
不要为了改一句话重写所有部件；保留命名空间声明、样式引用与未知扩展。
验证器的 `--auto-repair` 会修改内容，只在工作副本中使用，随后检查修复结果。

## 修订与接受视图

下面为本地原创的独立 XML 片段，Copyright (c) 2026 seaworld008；SPDX-License-Identifier: MIT。
其中命名空间、作者和 ID 仅作示例；整合前需检查包内唯一性。

```xml
<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:r><w:t xml:space="preserve">交付日期为 </w:t></w:r>
  <w:del w:id="31" w:author="Reviewer" w:date="2026-11-18T00:00:00Z">
    <w:r><w:delText>周二</w:delText></w:r>
  </w:del>
  <w:ins w:id="32" w:author="Reviewer" w:date="2026-11-18T00:00:00Z">
    <w:r><w:t>周三</w:t></w:r>
  </w:ins>
  <w:r><w:t>。</w:t></w:r>
</w:p>
```

接受该片段的修订应显示“交付日期为 周三。”；拒绝后应显示“交付日期为 周二。”。
在既有文档中保留不受影响运行的格式，避免把同段全部文字包装成一次更改。
若删除整段，要同时表达段落标记删除与段内文字删除；仅删除文字可能留下空段或空项目符号。
段落标记的 `w:del` 放在 `w:pPr/w:rPr` 内，遵守其子元素顺序；不能直接删除整段来假装修订。
接受视图转换器在空白分隔段附近可能与 Word 合并段落的行为不同，需检查 XML 和 Word 的接受/拒绝结果。
`accept_changes.py in.docx clean.docx` 产物是单独的清洁副本，不能替换仍需审阅的带修订稿。

## 批注关联

[comment.py](scripts/comment.py) 的本地接口是 `unpacked_dir comment_id text`，支持 `--author`、`--initials`、`--parent`。
调用后检查批注正文部件、扩展元数据、关系和内容类型；仅存在 `comments.xml` 不代表批注可见。
目标范围必须在 `word/document.xml` 中有以下三个同 ID 标记；范围不能穿越无关文本。
下面为本地原创片段，Copyright (c) 2026 seaworld008；SPDX-License-Identifier: MIT。

```xml
<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:commentRangeStart w:id="12"/>
  <w:r><w:t>交付日期</w:t></w:r>
  <w:commentRangeEnd w:id="12"/>
  <w:r><w:commentReference w:id="12"/></w:r>
</w:p>
```

新回复应关联已有父批注，而不是复用父批注 ID。打开 Word 后点击批注，应高亮“交付日期”，并显示回复线程。

## 渲染与最终应用检查

运行 `python scripts/render_docx.py edited.docx --output_dir rendered --dpi 120` 后，核实本次输出文件数量与页数。
逐页检查标题、页眉页脚、编号续接、长表跨页、图片裁切和最后一页空白；只看首页不能覆盖全文。
同时运行 `python scripts/office/validate.py edited.docx --original original.docx --author Reviewer` 检查跟踪修改。
最终在 Word 打开输出：无修复提示；修订面板可逐项接受/拒绝；批注锚点与回复正确；打印预览中所有页面完整。
记录实际跑过的工具、版本和产物；缺少渲染依赖时只能报告结构结果及尚未执行的视觉检查。
