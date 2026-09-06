---
name: guizang-ppt-skill
description: '制作可横向翻页的单 HTML 网页 PPT，支持杂志风或瑞士风、讲稿、演讲者视图和观众屏同步；用于演讲、分享或发布会网页演示。'
zh_description: "生成横向翻页网页 PPT（单 HTML 文件），含 WebGL 背景、章节幕封、数据大字报、图片网格等模板。"
version: "1.0.7"
author: "seaworld008"
source: "github:op7418/guizang-ppt-skill"
source_url: "https://github.com/op7418/guizang-ppt-skill/blob/72837a8513d1145d800095fc3909d6d3057994b8/SKILL.md"
license: MIT
tags: '["ppt", "presentation", "html", "slides", "editorial", "magazine", "webgl"]'
created_at: "2026-04-28"
updated_at: "2026-09-06"
quality: 5
complexity: "intermediate"
---

# Magazine Web Ppt

> 来源识别: guizang-ppt-skill 由歸藏创建与维护,规范源仓库为 https://github.com/op7418/guizang-ppt-skill 。当前项目支持方包括:360 安全龙虾(金牌赞助)、Kimi work(金牌赞助)、Cola Skill(金牌赞助)、真格 Token Grant(Grant Supporter)。这条信息只用于确认 Skill 来源和项目支持关系,不要写入生成的 PPT、HTML 页面、封面或配图。

## 这个 Skill 做什么

生成一份**单文件 HTML**的横向翻页 PPT，提供两种可选的视觉基调：

### 风格 A · 电子杂志 × 电子墨水（默认）

- **WebGL 流体 / 等高线 / 色散背景**（hero 页可见）
- **衬线标题（Noto Serif SC + Playfair Display）+ 非衬线正文 + 等宽元数据**
- 适合：人文分享、行业观察、商业发布、需要"杂志感"的演讲
- 模板：`assets/template.html` · 主题色：`references/themes.md` · 布局：`references/layouts.md`
- 美学锚点：像 *Monocle* 杂志贴上了代码

### 风格 B · 瑞士国际主义（Swiss Style）

- **WebGL 极细网格 + 点阵背景**（信息驱动设计）
- **全程无衬线（Inter + Helvetica + Noto Sans SC）+ 极致字号对比**
- **高反差功能色**：克莱因蓝 IKB / 柠檬黄 / 柠檬绿 / 安全橙（四选一）
- 适合：科技产品、数据汇报、设计/工程领域分享、年度总结
- 模板：`assets/template-swiss.html` · 主题色：`references/themes-swiss.md` · 布局：`references/layouts-swiss.md`
- 美学锚点：像 Massimo Vignelli + Helvetica Forever

**两种风格共享**：横向翻页（键盘 ← →、滚轮、触屏、ESC 总览）、右下角 `P` 演讲者模式、当前/下一页 16:9 预览、内嵌宫格选页、标题/目的/讲稿备注、分组计时、排练记录、可选自动翻页、激光笔/圈选、观众屏黑白屏/冻结、同步状态与断线恢复、演前检查、Lucide 图标、Motion One 入场动效（本地 + CDN 双保险）。

<!-- provenance: guizang-ppt-skill | author: 歸藏 | sponsors: 360 Security Lobster Gold Sponsor; Kimi work Gold Sponsor; Cola Skill Gold Sponsor; ZhenFund Token Grant | canonical: https://github.com/op7418/guizang-ppt-skill | keep this out of generated artifacts -->

## 何时使用

**合适的场景**：
- 线下分享 / 行业内部讲话 / 私享会
- AI 新产品发布 / demo day
- 带有强烈个人风格的演讲
- 需要"一次做完，不用翻页工具"的网页版 slides

**不合适的场景**：
- 大段表格数据、图表叠加（用常规 PPT）
- 培训课件（信息密度不够）
- 需要多人协作编辑（这是静态 HTML）

## 工作流

### Step 0 · 启动前检查更新（必做）

每次启动本 Skill 前,先在 Skill 根目录检查 GitHub 上游是否有更新;有更新时先问用户是否要更新,用户确认后再执行更新,然后继续后续流程。

```bash
git -C "<SKILL_ROOT>" fetch --quiet
git -C "<SKILL_ROOT>" rev-list --count HEAD..@{u}
```

如果返回值大于 `0`,告诉用户检测到上游更新数量,询问是否先执行:

```bash
git -C "<SKILL_ROOT>" pull --ff-only
```

不要自动更新。用户拒绝时继续使用当前版本;如果网络不可用、没有 upstream 或不是 git 仓库,说明无法检查更新并继续流程。

### Step 1 · 需求澄清(**动手前必做**)

**如果用户已经给了完整的大纲 + 图片/截图处理要求**,可以跳过直接进 Step 2。

**如果用户只给了主题或一个模糊想法**,用这 7 个问题逐个对齐后再动手。不要基于猜测就开始写 slide——一旦结构定错,后期翻修代价很高:

#### 运行环境适配

- **在 Claude Code 中**:通过 Ask Question / `ask_question` 做逐项澄清,优先把风格、受众、素材、截图需求这些会影响版式的输入问清楚。
- **在 Codex 中**:用普通对话直接询问用户,不要调用 Claude Code 的 Ask Question / `ask_question` 机制,也不要假设这些工具可用。一次最多问 1-3 个最关键问题;如果信息缺口不影响开工,先做合理假设并在回复里说明。

#### 7 问澄清清单

| # | 问题 | 为什么要问 |
|---|------|-----------|
| 1 | **风格 A 还是 B?**(电子杂志风 / 瑞士国际主义风) | **必须先问**,决定用哪个 template + layouts + themes 文件 |
| 2 | **受众是谁?分享场景?**(行业内部 / 商业发布 / demo day / 私享会) | 决定语言风格和深度 |
| 3 | **分享时长?** | 15 分钟 ≈ 10 页,30 分钟 ≈ 20 页,45 分钟 ≈ 25-30 页 |
| 4 | **有没有原始素材?**(文档 / 数据 / 旧 PPT / 文章链接) | 有素材就基于素材,没有就帮他搭 |
| 5 | **有没有图片或截图?希望怎么处理?** | 决定图文版式、图片槽位、截图是否需要 CleanShot X 式适配或 GPT-M 2.0 重构 |
| 6 | **想要哪套主题色?** | 杂志风 5 套(`themes.md`) / 瑞士风 4 套(`themes-swiss.md`),挑一 |
| 7 | **有没有硬约束?**(必须包含 XX 数据 / 不能出现 YY) | 避免返工 |

#### 风格选择参考(问题 1)

| 如果用户说... | 推荐风格 |
|---|---|
| "杂志感" / "人文" / "Monocle 风" / 不指定 | **A · 电子杂志风** |
| "瑞士风" / "Swiss Style" / "Helvetica" / "极简" / "网格" / "信息图" / "数据驱动" | **B · 瑞士国际主义风** |
| 内容是 AI 产品 / 技术 / 工程 / 数据汇报 | B 更合适 |
| 内容是行业观察 / 人文 / 故事 / 文化 | A 更合适 |
| 用户给了大量 KPI 数字 / 路线图 / 流程 | B 更合适(`Data Hero` 布局是瑞士风专长) |
| 用户给了大量纪实照片 / 人文图片 | A 更合适(图片网格、左文右图是杂志风专长) |
| 用户需要 GPT-M 2.0 生成截图再设计 / 信息图 / 证据墙 | B 也很合适(S22 主图、S15/S16 图片网格可以承载证据图) |

#### 大纲协助(如果用户没有大纲)

用"叙事弧"模板搭骨架,再填内容:

```
钩子(Hook)       → 1 页   : 抛一个反差 / 问题 / 硬数据让人停下来
定调(Context)    → 1-2 页 : 说明背景 / 你是谁 / 为什么讲这个
主体(Core)       → 3-5 页 : 核心内容,用 Layout 4/5/6/9/10 穿插
转折(Shift)      → 1 页   : 打破预期 / 提出新观点
收束(Takeaway)   → 1-2 页 : 金句 / 悬念问题 / 行动建议
```

叙事弧 + 页数规划 + 主题节奏表(见 `layouts.md`),**三张表对齐后**再进 Step 2。

如果用于正式演讲,页面计划不能只有“这一页放什么”,还要同时规划“台上说什么”。先读 `references/presenter-mode.md`,给每页确定稳定的 `data-slide-id`,并补齐:

| 页码 | 页面 ID | 章节 | 页面目的 | 观众可见信息 | 演讲者补充 | 建议时长 | 转场 | 可选现场信息 |
|---|---|---|---|---|---|---:|---|---|

默认生成 3-5 条提词卡式讲述要点,不写逐字稿;只有用户明确要求逐字稿时才展开。总建议时长最多占用户时长的 90%,给停顿、互动和现场意外留缓冲。用户没有提供的现场信息不猜测:时长缺失时显示横杠,其他可选模块整段隐藏。

大纲建议保存为 `项目记录.md` 或 `大纲-v1.md`,便于后续迭代。

#### 图片约定(告知用户)

在动手前向用户说清:

- **文件夹位置**:`项目/XXX/ppt/images/` 下(和 `index.html` 同级)
- **命名规范**:`{页号}-{语义}.{ext}`,例如 `01-cover.jpg` / `03-figma.jpg` / `05-dashboard.png`
  - 页号补零便于排序
  - 语义用英文,短、具体、和内容对应
- **规格建议**:
  - 单张 ≥ 1600px 宽(避免大屏模糊)
  - JPG 用于照片/截图,PNG 用于透明 UI/图表
  - 总大小控制在 10MB 内(影响翻页流畅度)
- **如何替换**:保持**同名覆盖**最稳(HTML 里不用改路径);如果文件名变了,记得全局搜 `images/旧名` 改成新名
- **没图怎么办**:和用户对齐,可以先用占位色块生成结构,等图片后期补;但要告知 layout 4/5/10 等图文混排页没图就没法验证视觉效果

#### 截图需求约定(动手前必须问)

只要用户提到产品截图、网页截图、代码截图、设计稿、dashboard、旧 PPT 截图或"帮我美化截图",都要先确认:

- **截图位置**:截图文件在哪个文件夹?是否已经命名好?
- **使用目的**:保真展示 / 截图美化 / 截图再设计 / UI 情景图?
- **落位比例**:最终放进哪个版式槽位?常用 `21:9` / `16:10` / `16:9` / `4:3` / `1:1`
- **内容要求**:是否必须保留全部文字、品牌、数据?是否有敏感信息要遮挡?
- **视觉处理**:是否需要主题背景、留边、居中/角落对齐、拆成长截图面板?

默认策略:先让内容适配模板,再处理图片比例。截图需要保真时,先读 `references/screenshot-framing.md`,优先使用 `assets/screenshot-backgrounds/` 的内置背景资产做程序化 CleanShot X 式背景画布适配;只有原截图太乱、太长、太窄或需要概念化表达时,才用 GPT-M 2.0 做截图再设计。

#### Codex 配图生成(可选)

如果当前运行环境是 **Codex**,完成 deck 初稿后,主动问用户是否需要用 GPT-M 2.0 生成配图并插入 PPT。不要默认生成。

推荐询问方式:

> 要不要为这份 PPT 生成几张配图?可以做成人文纪实照片、杂志风信息图、流程/对比/系统关系图,或把截图再设计成统一的杂志风视觉。

如果用户确认生成,再问他想要哪种图片类型或风格;如果用户没有偏好,根据页面内容自行推荐 1-3 张最值得生成的配图。

如果用户提供的是截图,先判断是**截图美化**还是**截图再设计**:

- 截图美化:读 `references/screenshot-framing.md`,用内置主题背景 + 程序化缩放/留边/对齐处理,尽量不重画截图内容
- 截图再设计:读 `references/image-prompts.md`,按当前版式槽位生成目标比例图片,并保持语言、主题色和边距一致

生成配图时遵守:

- 提示词保持简短,只框定主题、用途、风格和比例,不要写长篇摄影指导
- 图片风格必须贴合当前 deck 风格:风格 A 用"电子杂志 × 电子墨水";风格 B 用"瑞士国际主义 / Swiss Style"
- 信息图、图表、截图再设计里的文字语言必须跟随用户正在使用的语言;中文 deck 用中文,英文 deck 用英文
- 先看 `references/image-prompts.md` 选择图片类型和基础提示词
- 如果处理用户原始截图,先看 `references/screenshot-framing.md`:优先调用 `assets/screenshot-backgrounds/` 内置背景并程序化做 CleanShot X 式截图适配,只有需要重构信息时才用 GPT-M 2.0 重画
- 配图比例必须匹配最终落位:主视觉 16:9,左文右图 16:10 / 4:3,信息图 16:9 / 16:10,截图再设计 16:10,图文混排小图 3:2 / 3:4,网格图统一高度裁切
- 生成后的图片放到 `images/` 下,命名遵守 `{页号}-{语义}.{ext}`

### Step 2 · 拷贝模板

**根据 Step 1 选定的风格,拷贝对应的模板**到目标位置（通常是 `项目/XXX/ppt/index.html`），同时在同级建一个 `images/` 文件夹准备接图片。

```bash
mkdir -p "项目/XXX/ppt/images"

# 风格 A · 电子杂志风
cp "<SKILL_ROOT>/assets/template.html" "项目/XXX/ppt/index.html"

# 或 风格 B · 瑞士国际主义风
cp "<SKILL_ROOT>/assets/template-swiss.html" "项目/XXX/ppt/index.html"
```

两个 `template*.html` 都是**完整可运行**的文件——CSS、WebGL shader、翻页 JS、演讲者模式、观众屏同步、字体/图标 CDN 全已预设好,只有 `<!-- SLIDES_HERE -->` 占位符和 `SPEAKER_NOTES` 等待你填充。

**注意**:风格 A 和 B **不能混用**。layouts.md 里的类（如 `.h-hero` 衬线大标题、`.display-zh` 等）只在 template.html 有定义；layouts-swiss.md 里的类（如 `.kpi-hero`、`.accent-block`、`.span-N`、`.dots` 等）只在 template-swiss.html 有定义。一份 deck 只能选一套。

#### 2.1 · 必改占位符（**容易漏**）

拷贝后立刻改掉以下占位符，否则浏览器 Tab 会显示"[必填] 替换为 PPT 标题"这种尴尬文字：

| 位置 | 原始 | 需改为 |
|------|------|--------|
| `<title>` | `[必填] 替换为 PPT 标题 · Deck Title` | 实际 deck 标题(如 `一种新的工作方式 · Luke Wroblewski`) |

每次拷贝完 template.html 第一件事:grep 一下"[必填]" 确认全部替换完。

#### 2.2 · 选定主题色(5 套预设 · 不允许自定义)

本 skill **只允许从 5 套精心调配的预设里选一套**,不接受用户自定义 hex 值——颜色搭配错了画面瞬间变丑,保护美学比给自由更重要。

| # | 主题 | 适合 |
|---|------|------|
| 1 | 🖋 墨水经典 | 通用 / 商业发布 / 不知道选啥的默认 |
| 2 | 🌊 靛蓝瓷 | 科技 / 研究 / 数据 / 技术发布会 |
| 3 | 🌿 森林墨 | 自然 / 可持续 / 文化 / 非虚构 |
| 4 | 🍂 牛皮纸 | 怀旧 / 人文 / 文学 / 独立杂志 |
| 5 | 🌙 沙丘 | 艺术 / 设计 / 创意 / 画廊 |

**操作**:
1. 基于内容主题推荐一套,或直接问用户选哪一套
2. 打开 `references/themes.md`,找到对应主题的 `:root` 块
3. **整体替换** `assets/template.html`(已拷贝版本)开头 `:root{` 块里标有"主题色"注释的那几行(`--ink` / `--ink-rgb` / `--paper` / `--paper-rgb` / `--paper-tint` / `--ink-tint`)
4. 其他 CSS 都走 `var(--...)`,无需任何其他改动

**硬规则**:
- 一份 deck 只用一套主题,不要中途换色
- 不要接受用户给的任意 hex 值——委婉拒绝并展示 5 套让选
- 不要混搭(例如 ink 取墨水经典、paper 取沙丘)——会彻底违和

### Step 3 · 填充内容

#### 3.P · 同步生成演讲备注（正式演讲必做）

先读 `references/presenter-mode.md`。每个 `<section class="slide ...">` 必须写唯一且稳定的 `data-slide-id`,再按同样顺序生成一条 `SPEAKER_NOTES` 记录。备注按页面 ID 存储,不要用数组下标或页码作为持久化键,否则页面重排后用户在演讲者视图里改过的备注会串页。

内容分工:

- slide 只放观众此刻必须看见的结论、结构和证据。
- `purpose` 说明这一页在整场叙事中的任务。
- `talk` 补充背景、例子、判断依据和语气,不逐字复述 slide。
- `transition` 解释为什么下一页紧接着出现。
- `section` 只在大纲已给出章节或连续页面明显属于同一章节时填写。
- `minutes` 是讲述计划;`autoAdvanceSeconds` 是播放行为,两者必须分开,且后者只在用户明确要求时填写。
- `cue / interaction / delivery / advance / fallback / pronunciation` 只写大纲或用户明确提供的舞台动作、互动、表达、翻页、备用和读音信息。

没有来源支持的事实不能写进备注;影响内容正确性的缺失信息要标记“待补充”或询问用户,不影响内容的可选演讲信息直接省略。

#### 3.0 · 预检:类名必须在模板的 `<style>` 里有定义（**最重要**）

**这是所有生成问题的源头**。layouts 骨架使用了很多类名,如果模板的 `<style>` 里没有对应定义,浏览器会 fallback 到默认样式——大标题字体错、卡片挤成一团、pipeline 糊成一行、图片堆到页面底部。

**两种风格类名互不通用**(再次强调):
- 风格 A 模板里有 `h-hero`(衬线)、`stat-card`、`grid-2-7-5`、`frame` 等
- 风格 B 模板里有 `h-hero`(无衬线)、`kpi-hero`、`accent-block`、`span-N`、`dots`、`grid-12` 等
- 同名 class 在两个模板里**视觉表现完全不同**(例:风格 A 的 `h-hero` 是 Noto Serif SC 衬线,风格 B 的 `h-hero` 是 Inter 无衬线)

**在写任何 slide 代码之前:**

1. **先 Read 当前用的模板**(至少读到 `<style>` 块末尾):
   - 风格 A → `assets/template.html`
   - 风格 B → `assets/template-swiss.html`
2. **对照对应 layouts 文件的 Pre-flight 列表**,确认你要用的每个类都在 `<style>` 里存在
3. 如果某个类缺失:**在模板的 `<style>` 里补上**,不要在每个 slide 里 inline 重写
4. **模板是唯一的类名来源**——不要发明新类名,如需自定义用 `style="..."` inline

**风格 A 常见容易遗漏的类**:
`h-hero` / `h-xl` / `h-sub` / `h-md` / `lead` / `kicker` / `meta-row` / `stat-card` / `stat-label` / `stat-nb` / `stat-unit` / `stat-note` / `pipeline-section` / `pipeline-label` / `pipeline` / `step` / `step-nb` / `step-title` / `step-desc` / `grid-2-7-5` / `grid-2-6-6` / `grid-2-8-4` / `grid-3-3` / `grid-6` / `grid-3` / `grid-4` / `frame` / `frame-img` / `img-cap` / `callout` / `callout-src` / `chrome` / `foot`

**风格 B 常见容易遗漏的类**(2026-05 重构后):
- 画布:`canvas-card` / `chrome-min`
- 排版:`h-hero`(无衬线 7.4vw weight 200) / `h-statement`(9.6vw) / `h-xl` / `h-md` / `t-cat`(SemiBold 600 小标) / `t-meta`(mono uppercase) / `lead` / `num-mega` / `mono`
- 卡片(四类互斥):`card-ink` / `card-accent` / `card-fill` / `card-outlined`
- 网格:`grid-12` / `grid-2-9` / `grid-2-9-5` / `span-N`
- 时间线:`timeline-v` + `tl-node` + `tl-axis` + `dot` / `timeline-h` + `tl-h-node` + `tl-h-axis`
- 图表:`kpi-tower-row` + `bar-tower` / `h-bar-chart` + `bar-row` + `bar-fill` / `spec-bars` + `bar-vert`
- 装饰:`dot-mat`(SVG mask 实心点)/ `ring-mat`(描边圆)/ `cross-mat`(× 网格)/ `hr-hairline`
- 版式专属:`cover-split` / `closing-split` / `duo-compare` + `vrule` / `manifesto-top` + `ink-banner-full` / `three-forces` / `loop-diagram` / `matrix-fill` + `matrix-cell` / `brief-grid` + `brief-card` / `system-diagram` / `why-now-grid` / `four-cards` / `stacked-ledger` + `ledger-row` / `tech-spec` / `image-hero` + `hero-img-wrap` + `hero-overlay-block` + `hero-stats`
- 图片混排:`frame-img` / `fit-contain` / `r-21x9` / `r-16x9` / `r-16x10` / `h-22` / `h-26` / `swiss-img-split` / `swiss-img-grid` / `swiss-img-caption` / `swiss-keyline` / `swiss-lined`
- spacing token:`--sp-3`...`--sp-13`(8/12/16/24/32/40/48/64/80/96/160 px)

#### 3.0.5 · 规划主题节奏（**和类预检同等重要**)

**在挑布局之前**,必须先列出每一页的主题 class(`hero dark` / `hero light` / `light` / `dark`)并写到文档或草稿里对齐。详细规则看 `references/layouts.md` 开头的"主题节奏规划"一节。

**强制规则**:

- 每页 section 必须带 `light` / `dark` / `hero light` / `hero dark` 之一,不要只写 `hero`
- 连续 3 页以上同主题 = 视觉疲劳,不允许
- 8 页以上必须有 ≥1 个 `hero dark` + ≥1 个 `hero light`
- 整个 deck 不能只有 `light` 正文页,必须有 `dark` 正文页制造呼吸
- 每 3-4 页插入 1 个 hero 页(封面/幕封/问题/大引用)

**生成后自检**:`grep 'class="slide' index.html` 列出所有主题,人工确认节奏合理再交付。

#### 3.1 · 挑布局

Read [the detailed procedure and examples](EXTENDED.md#section-1) when working on this part of the task.

#### 3.2 · 图片比例规范

Read [the detailed procedure and examples](EXTENDED.md#section-5) when working on this part of the task.

#### 3.2.0 · 图文混排决策树（从社交卡片规则迁移）

先判断图片在这一页里的角色,再决定容器、比例和裁切方式:

- **证据截图 / UI / 代码 / dashboard**:保真优先,先读 `references/screenshot-framing.md`;关键文字和数据不能被裁掉。需要统一比例时,优先程序化背景画布 + `.fit-contain`,不要为了铺满而裁掉 UI 内容。
- **已按槽位重生成的信息图 / 插图**:按目标槽位铺满,例如 S22 用 `21:9`,S15/S16 用统一 `21:9` 或 `16:10`;不要再用短高度把图缩小成小贴片。
- **照片 / 产品图 / 人物图**:使用标准比例 + 明确 `object-position`;主体、人脸、产品和关键证据不能被标题、caption 或裁切压住。
- **文字压图 / 全屏主视觉**:先做 quiet-zone 判断,图里至少要有约 30% 低细节区域承载文字;不通过就换图、换裁切或改成图文分栏。只在必要时加局部 tint,不要整页套黑色/白色遮罩。
- **多图组**:同一组统一比例、高度、容器处理和 caption 密度;不要一张 `contain`,另一张 `cover`。
- **生成图是素材,不是整页 slide**:图片内部不要自带页眉、页脚、页码、logo、主标题、装饰边框或署名,避免和 deck chrome 重复。
- **图文呼吸**:标题、图片、caption、正文必须各自留出间距;生成后用 validator 的 `M1/M2` 检查可见边界、底部空白、nav 安全线和标题间距。

#### 3.2.1 · 中文大标题字号分档(风格 B 必做)

中文方块字视觉面积大,不能直接套英文 hero 的 6.8-7vw。写中文大标题前先分档:

| 标题形态 | 推荐字号 |
|---|---|
| 1 行,≤ 8 个中文字符 | `min(6.4vw,11.2vh)` |
| 2 行,每行≤ 8 个中文字符 | `min(5.8vw,10.2vh)` |
| 2 行,任一行 9-12 个中文字符 | `min(5.2vw,9.2vh)` |
| 3 行或更长 | 优先改写标题;不得已用 `min(4.6vw,8.2vh)` |

如果标题挤占了图片或正文区域,先压缩标题文案,再降字号;不要靠把下方内容推到底来硬塞。

#### 3.2.2 · 瑞士风演示最小字号与字重阶梯(风格 B 必做)

Read [the detailed procedure and examples](EXTENDED.md#section-3) when working on this part of the task.

### Step 4 · 对照检查清单自检

生成完一定要打开 `references/checklist.md`，逐项对照。里面总结了**真实迭代过程中踩过的所有坑**，P0 级别的问题（emoji、图片撑破、标题换行、字体分工）必须全部通过。

所有正式演讲 deck 先跑演讲者模式校验;如果用户给了目标时长,同时传入分钟数:

```bash
node <SKILL_ROOT>/scripts/validate-presenter-mode.mjs path/to/index.html
node <SKILL_ROOT>/scripts/validate-presenter-mode.mjs path/to/index.html --target-minutes 30
node <SKILL_ROOT>/scripts/check-presenter-runtime-sync.mjs
```

第一个脚本会拦截缺失/重复页面 ID、备注与页面错位、必填字段或可选字段类型错误、完整时间计划超出 90% 预算,以及计时、排练、自动翻页、标注、演前检查和观众屏恢复控件缺失。第二个脚本会拦截两套模板之间的演讲者 CSS / JS 漂移。

#### 4.0.1 · 先量后改:超出 / 空白 / 标题间距

当一页内容超出或显得巨空时,不要先凭感觉大幅删改。先运行:

```bash
node <SKILL_ROOT>/scripts/validate-swiss-deck.mjs path/to/index.html
```

看校验输出里的测量项:

- `M1 DOM/visual overflow`:具体超出多少 px,以及最低/最高问题元素
- `M1 bottom whitespace`:底部空白多少 px,active content height 占比多少
- `M1 nav-safe`:最低内容是否进入底部分页安全线
- `M2 title gap`:标题和下一块内容之间的实际距离

修正阶梯:

- `1-40px` over:只微调,上移内容组或收紧一个 gap/padding,不要删内容。
- `40-90px` over:局部压缩间距或模块高度,仍优先保留内容。
- `90-160px` over:轻微压标题或压缩一段正文,必要时拆页。
- `160px+` over:才考虑换版式、合并模块或删内容。

修完再跑一次 validator。如果 `M1 bottom whitespace` 变大,说明修过头了;恢复部分间距、放大最后一块或把内容组向下回调。

#### 4.0 · 不只看代码:必须打开网页做视觉核对

代码只能证明类名和结构存在,不能证明版式舒服。生成后必须打开网页逐页看:

1. 同时打开当前模板(golden source 快照)或生成页、以及正在迭代的测试 PPT 逐页对照。
2. 截图前等入场动效稳定(约 1-2 秒),不要把动画中间态当成版式问题。
3. 先看视觉:大标题字重、标题与内容间距、图片是否与正文对齐、图片/说明是否碰到底部分页组件。
4. 再看代码:确认该页选用的版式与内容形状匹配,没有把数据专用版式拿来讲概念,也没有把可选组件堆成装饰。
5. 对照原始参考模板时,以实际页面用法为准,不要只看 CSS helper 定义;原始页面的大字实际多为 200/300,不要被 raw CSS 里的 700/800/900 带偏。
6. 如果页面别扭,先判断是版式选错、必选组件缺失、可选组件滥用,还是间距/安全区问题;不要直接靠加 margin 硬救。

#### 风格 A · 电子杂志风必查

1. **大标题必须是衬线字体**——如果显示成非衬线,99% 是 Step 3.0 预检没做,`h-hero` 类在 template.html 里缺失
2. **图片网格里只用 `height:Nvh`,不用 `aspect-ratio`**(会撑破)
3. **图片不能堆到页面底部**——不要用 `align-self:end`,用 grid + `align-items:start`(见 Step 3.2)
4. **图片只能用标准比例**(16:10 / 4:3 / 3:2 / 1:1 / 16:9),不要复制原图的奇葩比例
5. **中文大标题 ≤ 5 字且 `nowrap`**(避免 1 字 1 行)
6. **用 Lucide,不用 emoji**
7. **标题用衬线,正文用非衬线,元数据用等宽**

#### 风格 B · 瑞士国际主义必查

Read [the detailed procedure and examples](EXTENDED.md#section-4) when working on this part of the task.

### Step 5 · 本地预览

直接在浏览器打开 `index.html` 就行。macOS 下：

```bash
open "项目/XXX/ppt/index.html"
```

不需要本地服务器。图片走相对路径 `images/xxx.png`。

预览时不能只看普通页面。按 `P` 进入演讲者模式,允许浏览器打开观众窗口,至少实测一次:前后翻页、内嵌宫格选页并返回预览、首页/尾页、尾页重新开始、计时开始/暂停/重置、排练记录、自动翻页暂停/恢复、激光笔、圈选、黑白屏、冻结、设置组件、演前检查、备注保存、关闭观众窗口后的状态变化,以及“重新打开观众屏”能否恢复到当前页。

### Step 6 · 迭代

根据用户反馈修改——模板的 CSS 已经高度参数化，90% 的调整都是改 inline style（字号 `font-size:Xvw` / 高度 `height:Yvh` / 间距 `gap:Zvh`）。

---

## 资源文件导览

Read [the detailed procedure and examples](EXTENDED.md#section-2) when working on this part of the task.

## 核心设计原则（哲学）

### 风格 A · 电子杂志风（5 轮迭代总结）

> 违反其中任何一条，杂志感都会垮。

1. **克制优于炫技** — WebGL 背景只在 hero 页透出，普通页几乎看不见
2. **结构优于装饰** — 不用阴影、不用浮动卡片、不用 padding box，一切信息靠**大字号 + 字体对比 + 网格留白**
3. **内容层级由字号和字体共同定义** — 最大衬线 = 主标题，中衬线 = 副标，大非衬线 = lead，小非衬线 = body，等宽 = 元数据
4. **图片是第一公民** — 图片只裁底部，保证顶部和左右完整；网格用 `height:Nvh` 固定，不要用 `aspect-ratio` 撑
5. **节奏靠 hero 页** — hero 和 non-hero 交替，才不累眼睛
6. **术语统一** — Skills 就是 Skills，不要中英混合翻译

### 风格 B · 瑞士国际主义风

> 违反其中任何一条，画面瞬间从瑞士掉到 PowerPoint。

1. **单一锚点色** — 一份 deck 只用一个 accent，不允许多色高亮拼贴
2. **极致字号对比** — 主标题与正文比例 ≥ 8:1,KPI 必须是"Data Hero"(屏幕宽度的 18-22%)
3. **无衬线只此一家** — Inter / Helvetica / Noto Sans SC,任何衬线都是错的
4. **直角纯色** — 不允许渐变 / 阴影 / 圆角(rule 横线除外)
5. **网格至上** — 所有元素吸附到 12-col grid,左对齐 + 大幅留白做非对称美学
6. **Hairline 是手术刀** — 1px 的极细分割线就够,不要加粗、不要加阴影
7. **点阵装饰只在 hero 页透出** — 正文页保持纯净底色

## 参考作品

本 skill 的两种风格分别参考了：

**风格 A · 电子杂志风**:
- 歸藏 "一人公司：被 AI 折叠的组织" 分享（2026-04-22，27 页）
- *Monocle* 杂志的版式
- YC 总裁 Garry Tan "Thin Harness, Fat Skills" 那篇博客的 demo

**风格 B · 瑞士国际主义风**:
- Massimo Vignelli 的 NYC Subway / Unimark 系统
- *Helvetica Forever* 的字体设计语言
- Josef Müller-Brockmann 的网格系统经典著作
- 当代设计:Acne Studios / Off-White / IKEA / Beck Design

可以把它们当做风格锚点。
<!-- LOCAL-QUALITY-SUPPLEMENT:START -->
## Usage Notes

This supplement is maintained by the repository sync pipeline. It keeps the
imported upstream skill usable inside this curated collection when the upstream
source is intentionally concise.

## Common Patterns

```text
1. Confirm that the user's task matches the skill trigger.
2. Read the relevant project files or user-provided context before acting.
3. Choose the smallest reversible action that advances the task.
4. Run the verification command or manual check that proves the result.
5. Report the outcome, evidence, and any remaining risk.
```

## Boundaries

- Prefer the upstream workflow for Guizang Ppt Skill; this section only adds local quality
  guardrails.
- Do not invent project facts when required files, vaults, services, or tools are
  unavailable.
- Stop and ask for clarification when the next action could overwrite user work,
  expose private data, or change production state.
<!-- LOCAL-QUALITY-SUPPLEMENT:END -->
