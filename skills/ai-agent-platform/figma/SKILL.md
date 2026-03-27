---
name: figma
description: 'Use the Figma MCP server to fetch design context, screenshots, variables, and assets from Figma, and to translate Figma nodes into production code. Trigger when a task involves Figma URLs, node IDs, design-to-code implementation, or Figma MCP setup and troubleshooting.'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["agent", "ai", "figma"]'
created_at: "2026-03-04"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
---

# Figma MCP (Design-to-Code)

Figma MCP 是连接设计稿与生产代码的超级引擎。它通过 Figma API 获取结构化设计上下文、变量定义及原始素材，并结合大模型的推理能力，将视觉稿一键转化为符合项目规范的 React/Tailwind/Vue 代码。

## 安装与前提条件

```bash
# 确保已安装 Figma MCP Server
mcp_call({ action: "search", keyword: "figma" });
# 获取访问令牌 (PAT)
# 详见 references/figma-mcp-config.md
```

## Figma MCP 核心集成流程 (Workflow)

为了确保 1:1 的视觉还原度和高性能的代码实现，必须严格遵循以下流程：

1. **获取设计上下文 (get_design_context)**：首先获取目标 Node ID 的结构化 JSON 表示，理解其层级、间距、填充和排版属性。
2. **处理大数据量 (Metadata First)**：如果 Node 层级过深，先运行 `get_metadata` 获取高层级节点地图，再精准抓取需要的子节点。
3. **视觉对齐 (get_screenshot)**：运行 `get_screenshot` 获取节点的实时渲染图片，作为实现时的绝对参考。
4. **素材下载 (Asset Acquisition)**：在开始编码前，下载所有图标（Icons）和装饰图（Images）。
5. **规范化翻译 (Code Translation)**：将 Figma 的属性（如 `cornerRadius: 8`）映射到项目的 Design Tokens（如 `rounded-lg`）。
6. **最终验证 (Visual Regression)**：完成开发后，再次对比 Figma 截图，确保 1:1 还原。

## 触发条件 / When to Use

- **新功能 UI 开发**：用户给出一个 Figma 链接，要求实现对应的组件或页面。
- **UI 细节优化**：针对现有页面进行微调，以对齐设计稿的最新改动。
- **设计规范审计 (Design Audit)**：自动提取 Figma 里的 Color Palette 或 Typography 并与代码库中的 `tailwind.config.js` 对比。
- **图标与静态资源同步**：需要批量导出 SVG 图标并转换为 React 组件。
- **响应式布局实现**：需要查看不同 Breakpoints（Desktop, Tablet, Mobile）下的设计差异。

## 核心能力 / Core Capabilities

### 1. 结构化设计解析 (Structural Parsing)
- **操作步骤**：
  1. 调用 `mcp_call({ name: "get_design_context", arguments: { fileKey, nodeIds } })`。
  2. 解析 `children` 数组，识别 `TEXT`, `VECTOR`, `INSTANCE` 等节点类型。
  3. 自动计算 Auto-layout 属性（Gap, Padding, Alignment）。
- **最佳实践**：如果发现节点名称是“Frame 1234”，主动询问设计人员其真实的语义名称（如“Primary Button”）。

### 2. 图像与变量提取 (Variable Extraction)
- **操作步骤**：
  1. 检索 Figma Variables 和 Styles。
  2. 将十六进制颜色码转换为项目使用的命名变量（如 `#3B82F6` -> `brand-primary`）。
  3. 通过 `get_file_variables` 获取全局主题定义。
- **最佳实践**：优先使用 `variable-id` 而非硬编码颜色。

### 3. 视觉引导编码 (Vision-guided Coding)
- **操作步骤**：
  1. 在编写 CSS/Tailwind 时，将 `get_screenshot` 的结果传入多模态模型进行视觉校验。
  2. 捕捉微小的阴影（Box-shadow）和渐变（Gradient）细节。
- **最佳实践**：使用 `image_edit` 技能在截图上标注出具体的像素间距，辅助编码。

### 4. 资产自动化处理 (Asset Handling)
- **操作步骤**：
  1. 检测 Figma 返回的 localhost 素材源。
  2. 自动将其下载并命名为合规的格式（如 `icon-user-profile.svg`）。
  3. 如果是 SVG，自动通过 `svgr` 转化为 React 组件。

## 常用命令/模板 / Common Patterns

### Figma-to-Code 任务描述模板 (Prompt Template)
```markdown
### 🎨 设计稿信息
- **File Key**: [例如：vO3S...]
- **Node ID**: [例如：12:456]
- **截图参考**: [URL 或本地路径]

### 🛠️ 实现要求
- **框架**: Next.js + Tailwind CSS
- **组件库**: 优先复用 `src/components/ui/` 下的 ShadcnUI。
- **交互**: 悬浮状态需增加 `hover:scale-105` 动画。

### 📦 素材处理
- 所有图标导出为 Inline SVG。
- 背景图放在 `public/images/`。
```

### 快速获取元数据示例
```javascript
// 示例：获取整个 Figma 文件的页面结构
mcp_call({
  name: "get_metadata",
  arguments: {
    fileKey: "XYZ789..."
  }
});
```

## 进阶应用场景 / Advanced Use Cases

### 1. 自动化 UI 回归测试集生成
- Agent 定期抓取 Figma 的最新版截图，并与本地 Artifacts 的渲染图进行 Pixel-by-pixel 对比。如果差异超过 5%，自动创建 PR 进行修复。

### 2. 多语言内容填充 (Copy Sync)
- 提取 Figma 文案节点。结合 `i18n-expert` 技能，自动生成多语言 JSON 文件并替换设计稿中的占位符。

## 边界与限制 / Boundaries

- **Token 限制 (Rate Limits)**：Figma API 对频繁的 `get_screenshot` 调用有严格限制，需注意缓存。
- **私有文件访问**：必须拥有对应的 PAT (Personal Access Token) 且具备该文件的查看权限。
- **复杂原型逻辑**：Figma 的“交互原型”（Prototyping）逻辑（如复杂的触发器）难以通过静态上下文完全还原，需人工补充。
- **非标准属性处理**：部分设计师使用的“偏僻”插件生成的属性，Figma MCP 可能解析为 `undefined`。
- **样式冲突**：自动生成的 Tailwind 类名可能与项目现有的全局样式冲突，需进行 Scoped 处理。

## 最佳实践总结

1. **复用优先**：不要 100% 照抄 Figma 生成的原始代码，必须将其“组件化”。
2. **重视语义化**：将 Figma 的图层名转化为 HTML5 语义标签（如 `header`, `nav`, `main`）。
3. **间距一致性**：如果 Figma 是 15px，代码库规范是 16px (rem-4)，应遵循代码库规范。
4. **资产轻量化**：导出的 SVG 必须经过 `SVGO` 压缩，禁止直接引入未经过滤的大型图片。
5. **记忆同步**：将常用的 Node ID 映射关系存入 `MEMORY.md`。
6. **视觉复核**：在提交 PR 前，强制在 `webapp-testing` 技能中运行一次视觉差异分析。
7. **配置隔离**：将 Figma API Key 存入 `.env.local`，严禁提交到代码仓库。
