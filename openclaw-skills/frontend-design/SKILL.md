---
name: frontend-design
description: 'Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications (examples include websites, landing pages, dashboards, React components, HTML/CSS layouts, or when styling/beautifying any web UI). Generates creative, polished code and UI design that avoids generic AI aesthetics.'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["design", "development", "frontend"]'
created_at: "2026-03-04"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
license: Complete terms in LICENSE.txt
---

# Frontend Design (高级前端设计)

Frontend Design 技能致力于创建极具辨识度、生产级且具备高审美水准的前端界面。本技能不仅生成可运行的代码，更融入了深厚的“设计思维”，坚决避免平庸的、流水线式的“AI 塑料感”审美，助力开发者打造令人难忘的数字体验。

## 安装与使用建议

```bash
# 无需安装，此为指导性技能
# 在启动 Web Artifact 或前端页面开发前激活
```

## 设计思维 (Design Thinking)

在编写代码之前，必须先确定一个 **大胆且明确** 的审美方向：

- **明确目的 (Purpose)**：该界面解决什么问题？受众是谁？是极客工具、奢侈品电商还是艺术展示？
- **选定基调 (Tone)**：在极端之间做选择 —— 绝对简约 (Brutally Minimal)、极致主义混乱 (Maximalist Chaos)、复古未来主义 (Retro-futuristic)、有机自然感 (Organic/Natural)、高级精致感 (Luxury/Refined)、玩具感 (Playful/Toy-like)、杂志排版感 (Editorial/Magazine)、新粗犷主义 (Neo-brutalism)。
- **约束边界 (Constraints)**：框架要求（React/Vue）、性能阈值、无障碍 (Accessibility) 标准。
- **差异化点 (Differentiation)**：什么是该页面的“灵魂”？是一个独特的转场动画、一种从未见过的网格布局，还是极具张力的排版？

**关键原则**：无论选择哪种风格，执行必须精准。简约不代表简陋，繁复不代表杂乱。意图比强度更重要。

## 核心能力 / Core Capabilities

### 1. 突破常规的排版系统 (Advanced Typography)
- **操作步骤**：
  1. 放弃 Arial, Inter, Roboto 等通用字体。
  2. 寻找具备性格的字体对：一个极具冲击力的标题字（Display Font）搭配一个极致可读的正文字（Body Font）。
  3. 利用 `clamp()` 函数实现流式排版（Fluid Typography），确保在任何屏幕上都具备完美的节奏感。
- **最佳实践**：使用超大字号作为背景装饰，或尝试垂直/斜向排版。

### 2. 深度质感与氛围营造 (Atmosphere & Texture)
- **操作步骤**：
  1. 放弃纯色背景。
  2. 使用 CSS 渐变网格 (Gradient Meshes)、噪点纹理 (Noise Textures)、几何图案层叠或磨砂玻璃 (Glassmorphism) 效果。
  3. 应用动态光影：利用 `box-shadow` 的多层堆叠模拟真实的物理深度。
- **最佳实践**：添加一个轻微的 `grain` 滤镜覆盖全页面，消除数码冰冷感。

### 3. 高级动效与交互微调 (Motion & Micro-interactions)
- **操作步骤**：
  1. 优先使用 CSS 动画实现轻量级效果。
  2. 对于复杂交互，引入 `Framer Motion` (React) 或 `GSAP`。
  3. 实施“交错揭示” (Staggered Reveals)：通过 `animation-delay` 让页面加载具备电影感。
- **最佳实践**：关注鼠标指针的交互（Custom Cursor）和滚动联动（Scroll-triggering）。

### 4. 响应式与无障碍闭环 (Responsive & A11y)
- **操作步骤**：
  1. 利用容器查询 (Container Queries) 实现更智能的组件自适应。
  2. 严格遵守 WCAG 2.1 对比度标准，确保美观的同时兼顾可用性。
  3. 优化 LCP (最大内容绘制) 和 CLS (累积布局偏移)。

## 常用命令/模板 / Common Patterns

### 前端开发任务描述模板 (Project Blueprint)
```markdown
### 🎨 审美提案 (Aesthetic Pitch)
- **风格**: 新粗犷主义 (Neo-brutalism)
- **核心色**: #FFD600 (高饱和黄) + #000000 (粗边框)
- **字体**: `Clash Display` (标题) + `JetBrains Mono` (正文)

### 🛠️ 技术栈
- React + Tailwind CSS + Framer Motion
- 布局: 12-column Grid, 非对称偏移

### 🌟 记忆点 (The Hook)
- 所有的卡片在悬浮时会产生一个偏移的硬阴影，模拟物理纸张的层叠感。
```

### 快速生成 CSS 噪点效果
```css
/* 示例：噪点纹理背景 */
.bg-noise {
  background-image: url("data:image/svg+xml,...");
  opacity: 0.05;
  pointer-events: none;
}
```

## 触发条件 / When to Use

- **Web Artifacts 构建**：当用户要求“做一个漂亮的时钟”、“做一个精美的天气卡片”时。
- **落地页开发 (Landing Pages)**：需要高转化率和第一眼视觉冲击力的场景。
- **管理后台美化 (Dashboard Beautification)**：将枯燥的数据转化为直观、现代的可视化界面。
- **个人作品集 (Portfolios)**：需要展示独特个性和设计品味的场景。
- **组件库从零构建**：需要定义一套独特的 Design System 时。

## 进阶应用场景 / Advanced Use Cases

### 1. 生成式艺术背景集成
- 利用 `canvas` 或 `svg` 动态生成随用户鼠标移动而变化的生成式艺术背景，提升界面的互动深度。

### 2. 响应式排版实验室
- Agent 自动生成 10 种不同的字体排版方案供用户挑选，并实时在 Artifacts 中预览。

## 边界与限制 / Boundaries

- **性能权衡**：过度复杂的滤镜（如 `backdrop-filter: blur`）和大量的 Canvas 动画可能导致低端设备卡顿。
- **浏览器兼容性**：新特性（如 `anchor-positioning`）在老旧浏览器上可能失效，需提供回退方案（Fallbacks）。
- **过度设计风险**：对于生产力工具，美感不应干扰操作流（Workflow）。不要为了酷炫而牺牲易用性。
- **Token 开销**：极致主义的设计通常对应庞大的 CSS 代码量，需注意上下文长度。

## 最佳实践总结

1. **拒绝平庸**：永远不要接受 AI 默认生成的“紫色渐变+圆角卡片”组合。
2. **像素级打磨**：关注边框、阴影、间距的每一个像素。
3. **色彩一致性**：使用 CSS Variables 管理调色板，确保全站风格统一。
4. **代码可读性**：即使是高度复杂的设计，代码也应具备良好的注释和组件化结构。
5. **记忆同步**：将本次成功的审美配方（色彩、字体、阴影）记录到 `MEMORY.md`。
6. **视觉反馈**：每一步关键的 UI 变更，都应主动提供截图预览（通过 Web Artifacts）。
7. **情感化设计**：思考界面如何与用户产生情感连接（Delight moments）。
