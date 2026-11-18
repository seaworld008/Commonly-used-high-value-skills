---
name: guizang-ppt-skill
description: 'Create browser-based HTML slide decks from supplied content using the bundled magazine-style template, with slide navigation and presentation review. Use when the user requests a web presentation rather than a PowerPoint file.'
zh_description: "使用随包杂志风模板制作可翻页的 HTML 网页演示，适用于内容已提供的网页 PPT 请求。"
version: "1.0.10"
author: "seaworld008"
source: "github:op7418/guizang-ppt-skill"
source_url: "https://github.com/op7418/guizang-ppt-skill/blob/72837a8513d1145d800095fc3909d6d3057994b8/SKILL.md"
license: MIT
tags: ["ppt", "presentation", "html", "slides", "editorial", "magazine", "webgl"]
created_at: "2026-04-28"
updated_at: "2026-11-17"
quality: 5
complexity: "intermediate"
---

# Magazine Web Ppt

## 来源与可执行范围

本入口及 [EXTENDED.md](EXTENDED.md) 是固定 MIT 快照的本地改编，
依据为歸藏的 `op7418/guizang-ppt-skill` 入口和随包 7 个模板、动效及参考文件。
固定引用为 `72837a8513d1145d800095fc3909d6d3057994b8`；
来源与许可证核验记录见 EXTENDED.md。
该 MIT 授权只对应此固定来源，不表示当前 AGPL 上游已经改回 MIT。

随包可用于制作演示的是电子杂志 × 电子墨水模板 `assets/template.html`。
成品以 `index.html` 为入口，图片和本地 Motion 模块随目录交付；
“单文件 HTML”指页面结构、CSS、导航和 shader 在一个 HTML 中，不表示依赖全部内联。
模板提供横向翻页、底部圆点、ESC 索引和 Motion 入场逻辑。
Chrome 等浏览器、WebGL、网络字体及模块加载是否可用，取决于实际宿主环境。
文档重建仅作静态核对，未完成真实浏览器验收；制作具体 deck 时需另行预览。

## 触发条件

- 用户要把已有内容制作成网页演示、杂志风 PPT 或横向翻页 deck。
- 适合线下分享、行业观察、产品发布、demo day 和个人风格较强的演讲。
- 用户只给主题时，可先搭叙事骨架，再补齐影响内容和版式的关键信息。
- 大量表格、密集培训材料或多人协作编辑需求，应先说明静态网页演示的适配限制。
- 用户要 `.pptx` 时，先明确输出格式差异；本包不提供 PowerPoint 转换能力。

## 核心能力与设计方法

以衬线大标题、非衬线正文、等宽元数据建立层级，用网格和留白组织信息。
电子杂志的视觉重点是内容秩序：每页一个主张，数据或图片承担证据。
hero 页承担封面、幕封和转折，正文页留给阅读；背景效果应服从文字可读性。
用 Lucide 线性图标，避免用 emoji 作成品图标。
不用厚重阴影、浮动卡片或装饰性框盒挤占内容区。
术语和图注语言跟随 deck，Skills 等专有词保持统一。

## 工作流

### 1. 收敛需求和素材

已有大纲、图片和输出位置时，直接使用，不重复询问。
缺失信息按影响程度收敛，一次只问 1–3 个会改变叙事或版式的问题。
不影响开工的细节采用合理默认值，在项目记录中说明。

| 输入 | 决定什么 | 缺失时的处理 |
|---|---|---|
| 受众与场景 | 语言、术语解释、内容深度 | 优先询问目标受众 |
| 时长与页数 | 信息粒度和叙事节奏 | 用暂定页数起草，不冒充用户要求 |
| 文档、数据、旧稿 | 页面论点与证据 | 先列结构，事实和数字留待素材补齐 |
| 图片及路径 | 图文页和网格页能否落地 | 可用明确的占位块，标记视觉待验 |
| 主题偏好 | 整套 deck 的色板 | 默认墨水经典 |
| 必含、禁含内容 | 页面取舍与文案 | 已给约束直接落实 |

页数可先参考 15 分钟约 10 页、30 分钟约 20 页、45 分钟约 25–30 页，
再按内容密度调整；这只是规划起点。
大纲建议随项目保存为 `大纲-v1.md`，不把临时假设写成事实。

### 2. 将叙事、布局和主题排成一张表

用“钩子 → 定调 → 主体 → 转折 → 收束”组织内容。
钩子用一个反差、问题或已证实的数据；主体每页只保留一个重点。
收束给可记住的观点或行动，不重复整套正文。

| 阶段 | 建议篇幅 | 适合内容 |
|---|---|---|
| Hook | 1 页 | 问题或硬数据 |
| Context | 1–2 页 | 背景、身份、为什么现在讲 |
| Core | 3–5 页起 | 故事、流程、比较、截图证据 |
| Shift | 1 页 | 反直觉判断、视角变化 |
| Takeaway | 1–2 页 | 金句、行动、开放问题 |

把每页的“目的、主张、素材、布局、主题”写在同一行。
布局从 [references/layouts.md](references/layouts.md) 的 10 种骨架中选，
完整的 8 页示例及修改策略见 EXTENDED.md。

主题 class 使用 `light`、`dark`、`hero light` 或 `hero dark`，每页明确标出。
避免连续超过 3 页同主题；每 3–4 页安排一次 hero 呼吸。
8 页及以上同时包含 `hero dark` 和 `hero light`，并保留 dark 正文页。
主题节奏是亮暗变化，整套 deck 的色板仍只使用一套。

### 3. 从种子模板建立成品目录

先读 [assets/template.html](assets/template.html) 的 `<style>` 和脚本，
确认组件类及运行依赖，再复制到用户指定的输出位置。
以下 `<SKILL_ROOT>` 是实际技能目录的占位符，执行前替换为真实路径。

```bash
mkdir -p "项目/XXX/ppt/images" "项目/XXX/ppt/assets"
cp "<SKILL_ROOT>/assets/template.html" "项目/XXX/ppt/index.html"
cp "<SKILL_ROOT>/assets/motion.min.js" "项目/XXX/ppt/assets/motion.min.js"
cp "<SKILL_ROOT>/LICENSE.upstream.txt" "项目/XXX/ppt/LICENSE.guizang.txt"
cp "<SKILL_ROOT>/LICENSE.motion.txt" "项目/XXX/ppt/LICENSE.motion.txt"
```

实际模板的 `#deck` 内只有 `<!-- SLIDES_HERE -->` 插槽，尚无示例 slide。
用选定的 `<section class="slide ...">` 替换该标记，至少插入一页后再预览。
空 deck 会使导航脚本访问不存在的当前页，不能作为成品交付。
保留 `#deck`、`#nav`、两张背景 canvas 及导航脚本之间的对应关系。
模板注释提到的额外参考文件不在本包中；布局以随包 `references/layouts.md` 为准。

立即替换 `<title>` 中的 `[必填]` 和示例内容，避免浏览器标签页暴露模板占位符。
后续修改作用于项目中的副本，不回写技能种子和参考文件。

```bash
rg -n '\[必填\]|SLIDES_HERE' "项目/XXX/ppt/index.html"
```

成品中这两个标记应无匹配；继续检查复制的布局里是否还残留示例人物、日期和数字。

### 4. 选色并核对样式类

从 [references/themes.md](references/themes.md) 选一套完整色板。

| 主题 | 适合内容 |
|---|---|
| 墨水经典 | 通用分享、商业发布、默认选择 |
| 靛蓝瓷 | 科技、研究、数据、技术发布 |
| 森林墨 | 自然、文化、可持续、非虚构 |
| 牛皮纸 | 阅读、文学、人文、独立杂志 |
| 沙丘 | 艺术、设计、创意、画廊 |

在成品的 `:root` 一次替换 `--ink`、`--ink-rgb`、`--paper`、`--paper-rgb`、
`--paper-tint`、`--ink-tint`，不要混搭不同预设的变量。
若用户明确要求品牌配色，按现有授权处理，并说明超出预设后需要重新检查对比度。

写 slide 前，把所选骨架的类名和模板定义逐个对应。
尤其核对 `h-hero`、`h-xl`、`lead`、`stat-card`、`pipeline`、`step`、
`frame`、`frame-img`、`img-cap`、`callout-src` 及所用 `grid-*`。
不要凭名称猜测某个类已经存在。
确需补充共享样式时，集中加到成品 `<style>`；局部微调用 inline，避免每页重复定义。

模板字体以实际 CSS 为准：中文标题 Noto Serif SC、英文标题 Playfair Display，
正文 Noto Sans SC、元数据 IBM Plex Mono，另有 Source Serif 4 和系统 fallback。
模板没有加载 Inter；`.lead` 实际为衬线引语，正文段落使用 `.body-zh`。
离线或字体请求失败会改变字宽，标题断行必须在目标环境再验。

### 5. 填充布局和图片

| Layout | 主要用途 |
|---|---|
| 1 开场封面 | 主标题、身份、分享主题 |
| 2 章节幕封 | 章节转场、叙事换气 |
| 3 数据大字报 | 一个关键数字或少量指标 |
| 4 左文右图 | 故事、身份反差、证据解释 |
| 5 图片网格 | 多图比较、截图实证 |
| 6 两列流水线 | 工作过程、步骤关系 |
| 7 问题页 | 悬念、幕末、收束 |
| 8 大引用 | 金句、核心判断、takeaway |
| 9 并列对比 | 旧模式与新模式 |
| 10 图文混排 | 主图与多段短说明 |

先粘贴骨架，再替换内容和路径，不从零重写导航系统。
页眉 `.chrome` 表示栏目或章节，`.kicker` 表示本页钩子，避免互相翻译或重复。
页码与实际顺序一致；数据保留单位、统计口径和来源，不沿用示例数字。
最大中文标题尽量控制在 5 字内；长标题降级到 `h-xl` 或手工断行。
`nowrap` 只用于宽度确实容得下的短标题，不用于隐藏溢出问题。

图片放在成品 `images/`，命名如 `01-cover.jpg`、`03-workflow.png`。
同名覆盖便于替换；改名后同步所有 `images/旧名` 引用。
主图建议宽度至少 1600px，总素材体积先以 10MB 为目标，再按现场设备调整。
照片可用 JPG；透明图、UI 或图表可用 PNG，优先保证文字清晰。

| 槽位 | 容器方式 | 注意事项 |
|---|---|---|
| 左文右图 | `r-16x10` 或 `r-4x3` | 最大高度 56vh，避免压住页脚 |
| 全屏主视觉 | `r-16x9` | 最大高度 64vh |
| 图片网格 | 统一 `h-22` 或 `h-26` | 不再叠加 aspect-ratio |
| 小型面板组 | 统一 `h-16` 或 `h-18` | 同组同高、同缩放逻辑 |
| 图文小图 | `r-3x2`、`r-3x4` 或 `r-1x1` | 按可用空间选取 |
| 截图、信息图 | 标准比例加 `fit-contain` | 保留完整文字和标注 |

图文混排用 `.frame.grid-2-7-5` 等已定义 grid，保持 `align-items:start`。
不要用 `align-self:end` 或 `bottom:0` 把图片贴到底部导航区。
模板照片默认 `cover`、`top center`；这有利于保留顶部，但不能保证所有比例下左右不裁切。
检查真实裁切结果，必须完整展示的截图改用 `fit-contain`，接受留白。
超长 UI 截图可拆成 2–3 个等高局部面板，保留原始证据语义。
缺图先用明确占位块；图文页的最终视觉验收需等真实图片补齐。

### 6. 配置动效并预览

五种 recipe 为 `cascade`、`hero`、`quote`、`directional`、`pipeline`。
通常只需按布局添加 `data-anim`、`data-animate`，无需改写动效引擎。
quote 每行标记 `data-anim="line"`；对比列分别用 `left` 和 `right`。
流水线用 `data-animate="pipeline"`，步骤用 `data-anim="step"`。
按空格或向前导航会先推进步骤，全部揭示后才翻页；检查时不要误判为翻页失效。

Motion 按 `./assets/motion.min.js` → CDN 顺序导入；都失败时脚本包含显式显示内容的兜底。
`file://` 的模块导入可能受浏览器策略限制，复制模块不等于已验证离线动效。
Google Fonts 和 Lucide 仍使用远程资源；不能把整个 deck 宣称为完整离线可用。
降级检查及动效 recipe 对照见 EXTENDED.md。

在宿主允许且具备浏览器时打开成品 `index.html` 预览，无需默认启动服务器。
若当前环境禁止浏览器或不能渲染，完成静态检查并列出待验步骤，不能声称已看到效果。

### 7. 交付前验收

参照 [references/checklist.md](references/checklist.md) 检查 P0–P3，
其中字体、裁切和模块加载的解释以本入口的实际模板核对结果为准。

- 内容：一页一个重点，无残留示例、占位符和未经证实的数据。
- 排版：大标题为衬线，正文与元数据层级清晰；无单字成行、文字截断和重叠。
- 图片：网格同高，截图文字完整，真实裁切不丢证据，页脚与圆点不遮图。
- 主题：亮暗节奏合理，hero 与正文区分明确，背景不影响文字对比度。
- 导航：键盘、滚轮、触屏、圆点、ESC 索引逐项核对；圆点数等于页数。
- 动效：内容最终可见，步骤推进顺序正确，返回页面和切换窗口后仍可读。
- 依赖：图片和本地 Motion 路径存在；在线、断网和目标屏幕分别记录结果。

交付 `index.html`、实际引用的 `images/`、`assets/motion.min.js`、`LICENSE.guizang.txt`、`LICENSE.motion.txt` 和必要的项目大纲。
模板的 op7418 通知与 Motion 11.11.17 的 Framer MIT 通知都须随成品保留，不只留在已安装的技能中。
报告页数、主题、文件位置及已执行检查，分清静态通过、真实浏览器通过和待验项目。
根据反馈优先删减文案、拆页、换布局，再调整字号、间距和图片高度。

## 按需资源

- [EXTENDED.md](EXTENDED.md)：8 页案例、组件片段、依赖诊断与人工验收步骤。
- [references/layouts.md](references/layouts.md)：10 种完整页面骨架及动效标记。
- [references/themes.md](references/themes.md)：5 套完整色板。
- [references/components.md](references/components.md)：字体、网格、数据、引用和图标组件。
- [references/image-prompts.md](references/image-prompts.md)：配图类型与比例，工具可用性另核对。
- [references/checklist.md](references/checklist.md)：按严重性整理的领域检查清单。
- [assets/template.html](assets/template.html)、[assets/motion.min.js](assets/motion.min.js)：随包种子和本地模块。

<!-- LOCAL-CURATION-SUPPLEMENT:START -->
## 本地策展：宿主与范围边界

使用当前已审阅的安装快照，不在制作演示过程中自动拉取上游或安装工具。
仅在明确的来源维护任务中更新技能；项目内只改用户指定的演示副本。
普通澄清使用宿主已有的对话或输入能力，不假设特定 Agent 的工具名存在。
当前授权足够时直接推进，缺失信息会实质改变结果时才补问。
浏览器、图像生成和文件操作均以当前宿主实际能力为准，不虚构调用或成功结果。
配图生成是可选步骤：用户已经要求生成时直接按授权执行，否则先说明可选方案。
生成图像不能作为真实产品截图或事实证据；重设计不得伪造数值、界面状态或来源。
缺失素材、工具、网络或视觉检查时明确标注限制，交付仍可完成的页面和检查记录。
不将模板示例中的人物、项目事实或来源署名误写成用户自己的信息。
<!-- LOCAL-CURATION-SUPPLEMENT:END -->
