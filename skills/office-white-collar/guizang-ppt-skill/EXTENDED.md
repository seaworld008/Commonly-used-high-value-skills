# Extended procedures and examples

Use [SKILL.md](SKILL.md) to select the task. Read only the sections it links for the current step.

<a id="section-1"></a>

#### 3.1 · 挑布局

**不要从零写 slide**。打开对应的 layouts 文件,里面有 10 种现成布局骨架,每种都是完整可粘贴的 `<section>` 代码块。

**风格 A** → `references/layouts.md`:

| Layout | 用途 |
|---|---|
| 1. 开场封面 | 第 1 页 |
| 2. 章节幕封 | 每幕开场 |
| 3. 数据大字报 | 抛硬数据 |
| 4. 左文右图(Quote + Image) | 身份反差 / 故事 |
| 5. 图片网格 | 多图对比 / 截图实证 |
| 6. 两列流水线(Pipeline) | 工作流程 |
| 7. 悬念收束 / 问题页 | 幕末 / 收尾 |
| 8. 大引用页(Big Quote) | 衬线金句 / takeaway |
| 9. 并列对比(Before / After) | 旧模式 vs 新模式 |
| 10. 图文混排(Lead Image + Side Text) | 信息密集的图文页 |

**风格 B** → 先读 `references/swiss-layout-lock.md`,再读 `references/layouts-swiss.md`。

瑞士主题默认进入 **Swiss locked mode**:

- 正文页只能使用原始参考 PPT 登记的 22 个版式 `S01-S22`;新增首页/尾页只能使用 Skill 明确提供的 `SWISS-COVER-ASCII` / `SWISS-CLOSING-ASCII`。
- 每个 `<section class="slide">` 必须写 `data-layout="Sxx"`。没有 `data-layout` 就视为未登记版式。
- 不允许临时发明 `P23/P24`、`Swiss Image Split`、`Evidence Grid` 这类原始 22P 之外的正文结构,除非用户明确要求实验版式。
- 顶部中文标题默认左对齐、处在左上内容轴。不要把小标题放左列、大标题放右列,造成视觉居中;只有原始 statement/split 版式允许强中心叙事。
- SVG 只负责几何图形。不要在 SVG 里写文字标签,所有标签改用 HTML 网格/卡片/caption。
- 地理/历史/城市路线/地点关系页使用 `S08 + Swiss Map Component`:先读 `references/swiss-map-component.md`,仍保留 `data-layout="S08"`。

原始 22 个正文版式如下:

| Layout | 用途 |
|---|---|
| S01 Index Cover | 原始索引封面 |
| S02 Vertical Timeline + KPI | 演化对比 / 年代变迁 |
| S03 Split Statement | 核心论点 / 左右分屏 |
| S04 Six Cells | 6 项概念定义 |
| S05 Three Layers | 三层架构 |
| S06 KPI Tower | 4 项数据视觉化高度差 |
| S07 H-Bar Chart | 5-10 项排名比较 |
| S08 Duo Compare | Before/After 对照 |
| S09 Dot Matrix Statement | 大引述 / statement |
| S10 Split Closing | 收束页 |
| S11 Horizontal Timeline | 4-7 步流程 |
| S12 Manifesto + Ink Banner | 阶段性结论 |
| S13 Three Forces | 3 个对等概念深化 |
| S14 Loop Form | 自学闭环 / 自动化 |
| S15 Matrix + Hero Stat | 8-12 项矩阵 + 总数据 |
| S16 Multi-card Brief | 6 项快讯小卡 |
| S17 System Diagram | 三层架构 / 生态地图 |
| S18 Why Now | 三论点 + 数据支撑 |
| S19 Four Cards | 4 项等权特性 |
| S20 Stacked KPI Ledger | 纵向账单数据 |
| S21 Tech Spec Sheet | 产品规格 / benchmark |
| S22 Image Hero | 21:9 顶图 + 标题块 + 三列 KPI |

**登记扩展**:`S08 + Swiss Map Component` 用于地点、人物住所、路线、城市关系。它不是新 layout,而是 S08 右侧插槽的 MapLibre 地图组件;必须按 `references/swiss-map-component.md` 的点位、连线、卡片和右上角缩放/拖动控制实现。

选对应 layout,粘过去,改文案和图片路径即可。**务必先完成 3.0 预检**。

**风格 B 版式多样性硬规则**:
- 7-8 页 deck 至少使用 **6 个不同 S 编号版式**;10 页以上至少使用 8 个不同版式。
- 如果用户说"测试模板 / 看看效果 / 多一点版式",必须覆盖:一个封面、一个收尾、至少 1 个对比或时间线(S08/S11/S02)、至少 1 个结构图(S14/S17/S15)、至少 1 个图片版式(S22 或 S15/S16 图片格改造)。
- 不允许连续 3 页使用同一种主体结构,例如连续三页 `head + grid + card`。
- 图片页不能偷懒发明新结构。2-3 张图时,用 S15/S16 的原始网格骨架改造成图片格;单张大图用 S22。
- 开写 HTML 前先列一张 `页码 → data-layout → 选用理由 → 图片槽位` 草稿;交付前运行 `node <SKILL_ROOT>/scripts/validate-swiss-deck.mjs index.html`。校验器会先做静态结构检查;如果环境中能解析到 Playwright,还会做真实渲染后的可见边界、底部空白、nav 安全线和标题间距测量。

<a id="section-2"></a>

## 资源文件导览

```
guizang-ppt-skill/
├── SKILL.md                  ← 你正在读
├── assets/
│   ├── template.html         ← 风格 A · 电子杂志风模板（种子文件）
│   ├── template-swiss.html   ← 风格 B · 瑞士国际主义风模板（种子文件）
│   ├── screenshot-backgrounds/ ← 截图美化内置背景(WebP):style-a 5 套 / style-b 4 套
│   └── motion.min.js         ← Motion One 本地副本（离线兜底,约 64KB,共用）
├── scripts/
│   ├── validate-swiss-deck.mjs ← 风格 B 静态校验:登记版式、图片槽位、SVG 文本、标题对齐
│   └── validate-presenter-mode.mjs ← 两种风格共用:页面 ID、演讲备注、时长和演讲者运行时校验
└── references/
    ├── components.md         ← 组件手册（字体、色、网格、图标、callout、stat、pipeline、动效... 风格 A 适用）
    ├── layouts.md            ← 风格 A · 10 种页面布局骨架（可直接粘贴,含动效标记）
    ├── swiss-layout-lock.md  ← 风格 B · 原始 22P 版式锁,正文页必须按这里登记
    ├── layouts-swiss.md      ← 风格 B · 原始 22P 骨架说明 + 少量明确标注的实验区
    ├── swiss-map-component.md ← 风格 B · S08 地图扩展组件(MapLibre 点位/连线/卡片/控制)
    ├── themes.md             ← 风格 A · 5 套主题色预设（只能选不能自定义）
    ├── themes-swiss.md       ← 风格 B · 4 套瑞士风主题色预设（IKB / 柠檬黄 / 柠檬绿 / 安全橙）
    ├── image-prompts.md      ← GPT-M 2.0 配图类型、比例和基础提示词
    ├── screenshot-framing.md ← CleanShot X 式截图适配语义 + 内置背景资产映射
    ├── presenter-mode.md     ← 演讲者 UI、AI 备注结构、观众屏同步与恢复契约
    └── checklist.md          ← 质量检查清单（P0/P1/P2/P3 分级）
```

**加载顺序建议**：
1. 先读完 `SKILL.md`(这个文件)了解整体
2. Step 1 需求澄清**第一问**先确定风格 A 还是 B,然后:
   - 风格 A:读 `themes.md` 帮用户选一套主题色
   - 风格 B:读 `themes-swiss.md` 帮用户选一套主题色
3. **动手前 Read 对应模板的 `<style>` 块**——这是类名的唯一来源,缺类会导致整页样式崩
   - 风格 A → `assets/template.html`
   - 风格 B → `assets/template-swiss.html`
4. 读对应的 layouts 文件挑布局:
   - 风格 A → `layouts.md`(顶部有 Pre-flight 类名清单、主题节奏规划、动效 recipe 决策树)
   - 风格 B → **先读 `swiss-layout-lock.md`**,再读 `layouts-swiss.md`;正文页必须从 S01-S22 选择,每页写 `data-layout`
5. 如果风格 B 需要地点、路线、人物住所或城市关系地图,读 `swiss-map-component.md`
6. 如果在 Codex 中生成配图,读 `image-prompts.md` 挑图片类型、比例和基础提示词;如果是用户原始截图,先读 `screenshot-framing.md`,优先使用 `assets/screenshot-backgrounds/` 的内置背景资产
7. 细节调整时读 `components.md` 查组件(含 Motion 动效系统章节,主要服务风格 A;风格 B 的组件细节在 `layouts-swiss.md` 附录)
8. 正式演讲先读 `presenter-mode.md`,生成稳定页面 ID 和 `SPEAKER_NOTES`
9. 生成后先运行 `validate-presenter-mode.mjs`;风格 B 再运行 `validate-swiss-deck.mjs`,最后读 `checklist.md` 自检

**动效相关**:模板已把 Motion One 的加载和 recipe 逻辑内嵌到底部 module script。你不需要改 JS,只需要按 `layouts.md` / `layouts-swiss.md` 的骨架在 HTML 里加 `data-anim` / `data-animate` 即可。离线演示靠 `assets/motion.min.js`,断网时自动降级为"无动画但内容可读"。风格 B 模板必须保留 `B` 键低功耗模式:切换后停止 WebGL/ASCII canvas RAF,取消正在运行的 Web Animations,并把当前页内容直接 reveal 到静态最终态。

<a id="section-3"></a>

#### 3.2.2 · 瑞士风演示最小字号与字重阶梯(风格 B 必做)

瑞士风用于投屏演示时,小字不能按网页注释的 10-12px 写。默认遵守以下下限:

| 文本类型 | 最小字号 |
|---|---|
| 正文段落 / 主要说明 | `18px` |
| 卡片描述 / 列表 / 时间线说明 / caption / 图注 | `16px` |
| meta / kicker / mono label / 图表标签 | `14px` |

如果内容放不下,先删减文案、拆成两页、换更适合的 Sxx 版式,不要把字号压到 10/11/12/13px。尤其是中文 deck,不要为了塞三行解释把 `body-sm`、caption、timeline label 改小。

**字号与字重阶梯(瑞士风核心)** — "越大越细,越小越粗"不是感性描述,而是具体映射:

| 字号区间 | 推荐字重 | 典型场景 |
|---|---|---|
| ≥ 8vw | 200 (ExtraLight) | 封面大字、巨号 KPI、h-statement |
| 4-7.9vw | 200-300 | 章节标题(h-xl/h-xl-zh)、大编号 |
| 1.8-3.9vw | 300-400 | 中型标题、takeaway 标题(≈1.8vw)、中号数字 |
| 1-1.7vw / 16-20px | 400-500 | 正文段落、卡片描述、说明文字 |
| 13-15px(小字) | 500-600 | meta、kicker、角标、图表标签、caption 强调 |

**硬规则:**
- 同一页内,字号越小的元素字重必须 ≥ 字号越大的元素(不允许 16px 正文用 300 而 1.8vw 标题用 500)
- 16px 左右的小字拒绝使用 weight 300(太细不可读),最低 400,推荐 500
- 封面/IkB 反白大标题内强调字用 `italic + weight 300`,不要用 accent 色(蓝压蓝看不见)

组件细节(字体、颜色、网格、图标、callout、stat-card 等)在 `references/components.md`。

<a id="section-4"></a>

#### 风格 B · 瑞士国际主义必查

1. **全程无衬线**——任何衬线字体出现都是错的(检查 `font-family` 没用 `--serif` 类变量)
2. **只有一个 accent 色**——一份 deck 不能同时出现 IKB 蓝 + 柠檬黄 + 安全橙等多个高亮色
3. **不允许渐变 / 阴影 / 圆角**——所有色块直角纯色,任何 `box-shadow` / `linear-gradient` / `border-radius` > 0 都要砍掉(rule 横线除外)
4. **极致字号对比**——主标题与正文比例 ≥ 8:1
5. **大字号必须双约束限高**——`font-size:min(Xvw, Yvh)`,只用 vw 在标准 16:9 屏会溢出(吸取 P15/P20/P22 教训)
6. **大字字重 200**(ExtraLight)——字号越大越细,瑞士风灵魂;**禁止** 600/700/800 大字
7. **卡片填充类型互斥**——`card-ink` / `card-accent` / `card-fill` / `card-outlined` 四类**不能混用**(禁止"蓝底+蓝描边"、"灰底+描边"等)
8. **多卡并列时统一样式**——3-12 张卡用同一类(优先 `card-fill` 灰底);只突出一项时单独换 `card-accent`,且**只允许一张**
9. **直角到底**——任何 `border-radius` 都不允许;装饰用 8×8 直角小方块,**不要** 9px 圆形点
10. **图标用 lucide,不自己画 SVG**——`<i data-lucide="name"></i>` + `lucide.createIcons()`,选棱角风格(避免圆胖)
11. **时间线对齐**——axis 列固定 12px + dot 绝对定位,**不要**用 grid `justify-self`(会与虚线错位)
12. **章节级标题与内容间距 ≥ 9vh**——避免拥挤(吸取 P15/P16 教训)
13. **每页一个语义化动效 recipe**——不是统一 fade-up,数字 scale 弹入、bar scaleY 拉起、SVG stroke 描线、节点序列点亮等;**禁止**所有页用同一个 generic 配方
14. **playSlide 入口 reveal 容器**——`[data-anim]` 容器先强制 opacity:1,recipe 内再用 motion `{opacity:[0,1]}` 覆盖,否则有些页会"看不见"
15. **ESC 索引页可见性**——cloned slide 必须有 CSS override 让 `[data-anim]` 在缩略图里 opacity:1
16. **Helvetica/Inter 兜底中文字体**——Windows 用户没有"苹方",必须 fallback 到 `"Microsoft YaHei UI", "Noto Sans SC"`
17. **字体粗细体例**:大字 200 / 正文 300 / `t-cat` SemiBold 600 / `t-meta` mono uppercase
18. **保留低功耗快捷键**——右下角必须提示 `B 静态`;按 `B` 切换 `body.low-power`,停止 WebGL/ASCII canvas RAF 和 Motion 入场动画
19. **装饰元素严格在 grid 内**——bars 矩阵、点阵、ring-mat 不能贴边或溢出页面
20. **底部内容预留 nav 空间**——nav 在 ~97vh,内容收尾不要过 93vh(吸取 P22 KPI 大字溢底教训)
21. **图片容器直角无阴影**——`.frame-img` 不加 `border-radius` / `box-shadow`;边界只用 hairline
22. **S15/S16/S22 图片同组一致**——同一组图片统一比例、高度、边距、线条粗细;信息图/UI 图加 `.fit-contain`
23. **组件角色要正确**——S15/S16 图片格需要 caption 信息锚点;S22 的 KPI/说明是必选;数据专用版式必须有真实数据,不能靠文案硬填
24. **通用/非通用版式要分清**——S03/S08/S11/S19 较通用;S06/S07/S20/S21/S22 是数据/案例专用;S14/S15/S17 是结构专用

<a id="section-5"></a>

#### 3.2 · 图片比例规范

永远用**标准比例**,不要用原图奇葩比例(如 `2592/1798`):

| 场景 | 推荐比例 |
|------|---------|
| S22 顶部主图 | **21:9**;照片关键主体放中央安全区 |
| S15/S16 多图格 | 统一 21:9 或统一 16:10,不能混用 |
| 左文右图 主图(风格 A) | 16:10 或 4:3 + `max-height:56vh` |
| 图片网格(风格 A) | **固定 `height:26vh`**,不用 aspect-ratio |
| 左小图 + 右文字 | 1:1 或 3:2 |
| 全屏主视觉 | 16:9 + `max-height:64vh` |
| 图文混排小插图 | 3:2 或 3:4 |

**默认不要让图片 `align-self:end`**——会滑到页面底部,很容易碰到分页组件。用 grid 容器 + `align-items:start`(template 已预设)让图片贴顶即可;如果确实需要图文底对齐,必须先控制图片高度,再使用模板已有安全区类 `.nav-safe-bottom` / `.nav-safe-bottom-tight`,不要让最低处碰到分页组件。

**风格 B 瑞士风额外规则**:
- 单张大图用 S22;多图测试用 S15/S16 的原始卡片网格改造,不要用未登记的 P23/P24
- 生成图片前先写 `data-image-slot`:例如 `s22-hero-21x9` / `s15-grid-21x9` / `s16-brief-21x9`
- S22 配图默认生成 21:9,提示词必须包含 `subject centered in the safe middle area`;照片容器用 `object-position:center 35%`,不要用 `top center`
- 图片容器必须直角、无阴影、无圆角;默认背景用白色 `var(--paper)`,不要用灰底包白底信息图
- 白底 GPT 信息图/流程图/UI 图默认不要加外框描边,不要随手套 `.swiss-keyline`;需要强调时只用 `.swiss-lined` 的顶部 accent 线
- UI/信息图如果是用户原始截图或文字密集图,才用 `.fit-contain`;如果已按 S15/S16 槽位重生成,必须用 `.frame-img.r-21x9` / `.frame-img.r-16x10` 铺满容器,不要固定 `height:18vh` 后把图缩小
- 多图同组必须统一图片槽位、比例和高度,不能混用
- GPT-M 2.0 生成图使用 `image-prompts.md` 的"风格 B:瑞士国际主义配图规则"
- 任何图片、caption、timeline label、footnote 的最低处都不能进入底部分页区域;需要贴底时用 `.nav-safe-bottom` / `.nav-safe-bottom-tight`,不要手写 `bottom:2vh`
