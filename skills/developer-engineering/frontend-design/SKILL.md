---
name: frontend-design
description: 'Design and implement web pages, components, and application interfaces with a product-specific visual direction, responsive layouts, and usable interaction states.'
zh_description: "按产品目标与品牌约束设计和实现网页、组件及应用界面，兼顾视觉表达、响应式和交互验收。"
version: "1.0.4"
author: "Anthropic contributors; local curators"
source: "https://github.com/anthropics/skills"
source_url: "https://github.com/anthropics/skills/blob/e4bb5d960d87126ff3b3a8af1a104b7db67560ba/skills/frontend-design/SKILL.md"
license: "Apache-2.0"
tags: ["design", "development", "frontend"]
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 4
complexity: "intermediate"
---

# 前端设计与实现

本地修改说明：依据 Anthropic 的 `skills/frontend-design/SKILL.md`（固定提交 `e4bb5d960d87126ff3b3a8af1a104b7db67560ba`）重新编写中文方法，新增示例及验收标准；与上游文件不同字节。上游许可说明为 `Complete terms in LICENSE.txt`，继续适用 Apache-2.0，完整条款见同目录 `LICENSE.txt`。
本地原创增补：Copyright (c) 2026 seaworld008。下方原创 SVG、CSS 示例另标 `SPDX-License-Identifier: MIT`；该标记不替换上游材料的 Apache-2.0 许可。

## 触发条件

用于需要视觉与实现共同决策的页面、组件、仪表盘或 Web 应用改造。先明确用户要完成的真实任务，再决定界面如何表达它。
已有品牌、设计系统、布局规范或指定参考时，以这些约束为起点；不要因本技能而替换框架或另建一套组件库。
纯逻辑修复只涉及受影响的界面状态时，保持其余视觉结构稳定。

## 核心能力：把产品约束变成设计决策

动手前检查项目入口、现有组件、设计 token、字体资源、路由及测试方式。沿用项目正在使用的技术栈和构建命令。
用一个简短设计说明记录以下内容；已有答案从任务和项目读取，只有会改变结果的缺口才需要补充信息。

| 决策 | 要回答的问题 | 可观察结果 |
| --- | --- | --- |
| 受众与任务 | 谁在什么环境下做什么？ | 首屏可以找到主要动作及其前提 |
| 内容密度 | 用户要浏览、比较，还是逐项处理？ | 关键信息保持邻近，次要信息可以展开 |
| 视觉方向 | 产品主题中什么值得突出？ | 字体、图片、布局服务同一个表达重点 |
| 约束 | 品牌、设备、语言、资源及实现范围是什么？ | 可以说明每项设计选择的依据 |

先用真实标题、合理长度的数据和明确动作搭起内容骨架。缺少业务数据时使用清楚标注的示例数据，不编造客户背书或运行指标。
选一个主要视觉重点，例如作品预览、可操作的筛选器或清晰的数据比较；其余区域建立阅读秩序。
将设计说明与任务逐项对照：如果装饰挤占了主要动作、信息密度不适合受众，先调整布局再编码。
风格取舍取决于场景。渐变、卡片、衬线字体、深色背景都可以使用，前提是能解释它们对品牌、分组或阅读的贡献。

## 字体、网格、间距与色彩

- 优先复用品牌字体和合法可用的资源；没有专用字体时使用可靠的系统字体栈，并检查中文及数字的回退效果。
- 为页面标题、分区标题、正文和辅助信息分配字号、字重、行高。用一到两个字体家族通常足以形成角色区分，避免同级内容随意变化。
- 长文限制行宽，中文可从约 30–40 个字宽试起，再按实际字体和设备检查；表格与代码另行处理，不强迫所有内容共用行宽。
- 以内容建立网格：比较任务让项目对齐，步骤任务保留先后顺序，阅读任务保持连续。边框、编号和留白要表示实际关系。
- 从项目 token 选间距层级，先区分组件内部与组件之间的距离，再统一同级间距；不要靠大量绝对定位维持对齐。
- 区分背景、正文、次要文本、操作与状态色。错误或成功同时给出文字或图标，避免只靠颜色表达。
- 按实际前景和背景测对比度：普通文本至少 4.5:1，大字及必要界面边界通常至少 3:1；半透明层、图片背景和暗色主题分别检查。

## 响应式与可直接使用的 CSS 示例

以下是原创的社区工具借用目录样式。接入时将 token 映射到项目设计系统，选择器统一使用 `guide-` 前缀，避免覆盖已有组件。
固定声明提供基础回退，`clamp()` 在支持它的浏览器中连续调节字号及边距；根字号放大时也保留相对单位。
网格按卡片的最低可读宽度换列，`min(100%, 17rem)` 允许窄容器退成一列；长名称可以换行。

```css
/* Copyright (c) 2026 seaworld008 */
/* SPDX-License-Identifier: MIT */
:root {
  --guide-surface: #ffffff;
  --guide-ink: #182b38;
  --guide-muted: #4b5f6d;
  --guide-action: #075269;
  --guide-space: 1rem;
}
.guide-page {
  font-family: system-ui, sans-serif;
  color: var(--guide-ink);
  background: var(--guide-surface);
  padding: 1rem;
  padding: clamp(1rem, 3vw, 3rem);
  max-width: 72rem;
  margin-inline: auto;
}
.guide-title {
  font-size: 2rem;
  font-size: clamp(2rem, 1.25rem + 3vw, 3.5rem);
  line-height: 1.15;
  overflow-wrap: anywhere;
}
.guide-summary {
  max-width: 36ch;
  color: var(--guide-muted);
  line-height: 1.6;
}
.guide-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 17rem), 1fr));
  gap: var(--guide-space);
}
.guide-card {
  min-width: 0;
  padding: var(--guide-space);
  border: 1px solid var(--guide-muted);
  overflow-wrap: anywhere;
}
.guide-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 2.75rem;
  padding: 0.5rem 1rem;
  border: 2px solid transparent;
  color: var(--guide-surface);
  background: var(--guide-action);
  font: inherit;
  transition: transform 120ms ease-out;
}
.guide-action:active { transform: translateY(1px); }
.guide-action:focus-visible {
  outline: 3px solid var(--guide-ink);
  outline-offset: 3px;
}
@media (prefers-reduced-motion: reduce) {
  .guide-action { transition: none; transform: none; }
}
```

将 `.guide-action` 用于原生 `button` 或带有效 `href` 的链接，保留清晰的动作名称；不要把可点击的 `div` 当按钮。
`clamp()` 不能自动保证所有文字都不溢出。还需检查长译文、200% 缩放、空数据、滚动区域及粘性区域是否遮挡焦点。
在内容真实拥挤的位置设断点。窄屏优先保留主要任务；数据表可以在有名称的区域内横向滚动，不能把整个页面撑宽。

## 可选的 SVG 纹理

纹理只用于需要材料质感的非关键装饰区域；简洁的业务表单通常无需添加。以下完整 SVG 可以直接作为装饰图保存或嵌入，没有截断的 data URL。
噪点由 `feTurbulence` 生成，颜色矩阵将它变成低透明度黑色纹理。没有滤镜支持时透明矩形仍不承载必需信息。
重复内联时，为每个实例使用不同的 filter ID，并同步更新引用；装饰不能覆盖交互层或降低文字对比度。

```svg
<!-- Copyright (c) 2026 seaworld008 -->
<!-- SPDX-License-Identifier: MIT -->
<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160"
     viewBox="0 0 160 160" aria-hidden="true" focusable="false">
  <defs>
    <filter id="guide-grain" x="0%" y="0%" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.68"
                    numOctaves="2" seed="23" stitchTiles="stitch"/>
      <feColorMatrix type="matrix"
        values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.09 0"/>
    </filter>
  </defs>
  <rect width="160" height="160" fill="transparent" filter="url(#guide-grain)"/>
</svg>
```

## 交互、状态与实现质量

实现主任务的完整路径：输入、处理中、成功、空态、错误及恢复。空态说明如何开始，错误说明哪项失败及下一步；提交失败保留用户输入。
控件使用语义元素、可访问名称和可见标签。按 Tab 顺序检查焦点；对话框打开后管理焦点，关闭后回到触发位置，Escape 和背景操作按项目既有模式处理。
异步结果要让辅助技术能够获知，合适时使用简短的状态播报，避免反复朗读整页内容。禁用、加载和选中状态都需要可辨识。
动效解释动作与结果的关系，例如展开区域或确认操作；自动播放要有明确用途。尊重 `prefers-reduced-motion`，移除非必要位移及循环效果，保留静态反馈。
优先组合现有组件；重复的卡片和状态用共享组件与数据驱动，布局和样式按项目约定组织。检查 CSS 优先级，避免多个规则相互抵消间距或焦点样式。
图片提供尺寸或宽高比以减少布局跳动；按显示尺寸加载资源，首屏关键图片不盲目懒加载，离屏图片可延迟加载。
字体按需加载并提供回退，避免装饰脚本阻塞主任务。用项目已有性能工具检查实际资源与渲染开销，不凭代码短小宣称性能达标。
渐进增强从可读内容和基本操作开始，再加动画或高级布局。字体、图片、滤镜或脚本失败时，说明与关键操作仍应可用。

## 小案例：社区工具借用目录

受众是用手机寻找可借工具的居民，主要任务是找到有库存的物品并查看借用条件；首页不需要大幅宣传图。
复用社区站点品牌，以分类筛选和当前可借数量建立扫描顺序。卡片展示名称、库存和押金条件；“查看借用条件”进入详情，“申请借用”只在详情提供。
用上面的网格承载卡片：窄屏单列，宽屏按容器宽度自动分列。库存为零显示“暂时借完”，筛选无结果显示“没有符合条件的工具”及“清除筛选”。
请求失败显示“工具列表未能加载”与“重新加载”，保留筛选；处理中显示文字状态并防止重复请求，恢复后保留合理焦点位置。
验收时用三种长度的物品名、零库存及失败响应检查布局与恢复，不把示例中的库存当成真实接口结果。

## 可测验收与交付

- 对照真实任务：首屏能够识别用途、主要动作及必要条件；同一动作在按钮、状态反馈与完成页使用一致名称。
- 在 360px、768px、1440px 宽度以及项目要求的设备检查；页面无意外横向滚动，长标题不压住操作，内容顺序保持可理解。
- 用键盘完成主流程，核对可见焦点、控件名称、弹层关闭与焦点返回；检查普通、悬停、按下、禁用和加载状态。
- 模拟空数据、慢请求及失败重试，确认下一步可执行、输入不丢失且不会产生重复提交。
- 在减少动态效果模式、200% 缩放和字体或图片加载失败时复测；对比度按实际组合测量，透明叠层和纹理也计入检查。
- 若环境支持，保存宽屏和窄屏截图，标明视口、路由、数据状态及提交版本；比较对齐、文字折行和层级，而非仅检查代码是否运行。
- 运行与变更相关的项目构建、组件及交互测试；记录命令、结果和实际覆盖。静态解析不能代替浏览器渲染、键盘操作或模型效果评测。
- 交付说明列出设计选择、复用组件、已验证状态和剩余风险；缺少浏览器或截图工具时明确标注待验收项及复现步骤，不宣称完整浏览器评测已通过。
