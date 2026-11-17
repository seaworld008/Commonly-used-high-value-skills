# 使用 PptxGenJS 创建可编辑页面

方法改编自 [Anthropic pptx/SKILL.md](https://github.com/anthropics/skills/blob/e4bb5d960d87126ff3b3a8af1a104b7db67560ba/skills/pptx/SKILL.md)，Apache-2.0；原许可说明：`Complete terms in LICENSE.txt`。
本地修改：seaworld008，2026-11-18；提供独立示例与本地可用工具路径，不依赖未附带的 JS helper。
SPDX-License-Identifier: Apache-2.0

## 建模顺序

先设置画布、主题字体、颜色和页面框架，再创建文字、形状、表格与图表。
每份文件使用新的 `pptxgenjs` 实例；坐标以英寸表示，加入对象前计算其右边与下边是否超出画布。
通过 `defineSlideMaster()` 定义可复用版式时，给占位符稳定名称，再按名称填充。
主题字体与版式应服务后续编辑；使用主题色前检查当前库能否实际写入需要的主题颜色，不能仅设置字体就声称主题配色已应用。
无占位符的文本框设置 `isTextBox: true`，让读屏工具识别为文本；演讲备注使用 `slide.addNotes()`。

## 可执行的新建示例

以下 JavaScript 为本地独立编写，Copyright (c) 2026 seaworld008；SPDX-License-Identifier: MIT。
将代码保存为 `create-deck.cjs`，在已有 `pptxgenjs` 的环境执行 `node create-deck.cjs output.pptx`。
示例不需要旧 JS 库。当前重建环境缺少 `pptxgenjs`，仅验证语法；字体和图表实际呈现需另行渲染验收。

```javascript
// Copyright (c) 2026 seaworld008
// SPDX-License-Identifier: MIT
const PptxGenJS = require("pptxgenjs");

async function main() {
  const fileName = process.argv[2];
  if (!fileName) throw new Error("Usage: node create-deck.cjs output.pptx");
  const deck = new PptxGenJS();
  deck.layout = "LAYOUT_WIDE";
  deck.author = "seaworld008";
  deck.subject = "Synthetic chart example";
  deck.title = "季度交付数量";
  deck.lang = "zh-CN";
  deck.theme = { headFontFace: "Arial", bodyFontFace: "Arial", lang: "zh-CN" };
  const slide = deck.addSlide();
  slide.background = { color: "FFFFFF" };
  slide.addText("交付数量在第三季度增加", {
    x: 0.6, y: 0.4, w: 12, h: 0.7, fontSize: 32,
    bold: true, color: "172D40", margin: 0, isTextBox: true,
  });
  slide.addChart(deck.ChartType.bar, [{
    name: "交付数量", labels: ["Q1", "Q2", "Q3"], values: [18, 21, 29],
  }], {
    x: 0.7, y: 1.5, w: 8.3, h: 4.8,
    catAxisLabelFontFace: "Arial", catAxisLabelFontSize: 18,
    valAxisLabelFontFace: "Arial", valAxisLabelFontSize: 14,
    chartColors: ["176B87"], showLegend: false,
    showValue: true, dataLabelPosition: "outEnd",
    valAxisMinVal: 0, valAxisMaxVal: 40,
    showTitle: true, title: "交付数量（件）",
  });
  slide.addText("第三季度比第二季度多 8 件", {
    x: 9.5, y: 2.2, w: 3.1, h: 1.8, fontSize: 24,
    color: "172D40", margin: 0, isTextBox: true,
  });
  slide.addText("来源：本地合成示例，不代表实际业务数据", {
    x: 0.7, y: 6.9, w: 12, h: 0.3, fontSize: 12,
    color: "445566", margin: 0, isTextBox: true,
  });
  slide.addNotes("验收时打开图表的编辑数据，核对 Q1/Q2/Q3 对应 18/21/29。");
  await deck.writeFile({ fileName });
}
main().catch((error) => { console.error(error.message); process.exitCode = 1; });
```

验收：标题、正文和图表可分别选择；图表系列的值是 18、21、29；数轴从零开始；右侧说明与数据一致。
此例用普通柱状图，`outEnd` 不可直接照搬到堆积柱/条形图；后者用 `ctr`、`inEnd` 或 `inBase`。

## 容易写出错误文件的选项

| 位置 | 使用方式 | 检查点 |
| --- | --- | --- |
| 颜色 | 六位十六进制，不带 `#` | 不把透明度拼为八位颜色 |
| 透明度 | 填充使用 `transparency`，阴影使用 `opacity` | 查看渲染后实际效果 |
| 阴影 | 非负 `offset`，方向使用 `angle` | 阴影不能遮挡标签 |
| 选项对象 | 每次调用构造新对象，尤其阴影 | 防止库内部单位转换污染复用对象 |
| 字距 | 使用 `charSpacing` | 不以无效选项判定视觉已生效 |
| 列表 | `bullet`、段落换行和段后间距 | 不手写圆点导致双重项目符号 |
| 文本边距 | 对齐对象时显式 `margin` | 文字可见边缘与形状边缘一致 |

表格超出一页时检查续页标题、页脚与实际行数；自动分页结果同样逐页验收。
组合图使用第二轴时，同时声明相应 `valAxes` 与 `catAxes`，检查每个轴 ID 有定义且连接正确。
某些元数据或版式字段的 XML 转义行为随库版本不同；带 `&` 的名称要检查生成 XML，避免遗漏或重复转义。
写入成功、Python 能打开或 LibreOffice 能渲染，均不足以排除 PowerPoint 对图表的修复提示。

## 图像与数据来源

原生支持的图表优先 `addChart()`；不支持的视觉再使用静态图像，并保留源数据。
本地 [chartkit.py](scripts/chartkit.py) 的数据、类型、轴和输出参数如下；输出为图形素材，不能冒充可编辑图表。

```bash
python scripts/chartkit.py --data metrics.csv --type bar --x quarter --y deliveries --out charts --filename deliveries --title "季度交付"
```

它支持 `line`、`area`、`bar`、`barh`、`scatter`、`hist`、`waterfall`；选择图型前检查数据口径、缺失值与单位。
插入图片时保持比例，预留清晰的来源脚注；为辅助技术提供说明文本。

## 生成后的检查

运行 `python scripts/office/validate.py output.pptx`，按诊断修改生成代码后重新生成。
按 [SKILL.md](SKILL.md#内容文件视觉分别验收) 转成 PDF 和逐页图片，检查所有文字和图表标签。
在目标 PowerPoint 打开并试改图表值，检查图形随数据变化，字体无异常替换，所有对象没有越界。
若使用模板而非从零创建，转到 [editing.md](editing.md)，不要用新建库重新绘制整个模板来代替编辑。
