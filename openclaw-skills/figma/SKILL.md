---
name: figma
description: 'Fetch Figma design context, variables, screenshots, and assets through MCP when working from Figma URLs or node IDs, or diagnosing its integration.'
zh_description: "通过 Figma MCP 读取设计上下文、变量、截图和素材，并排查连接问题。"
version: "1.1.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["agent", "ai", "figma"]'
created_at: "2026-03-04"
updated_at: "2026-11-04"
quality: 3
complexity: "intermediate"
---

# Figma MCP

通过 Figma MCP server 读取设计数据：结构化上下文、变量与样式、截图、Code Connect 映射和素材。
本技能负责“读懂设计并给出可实现的事实”；把设计落成页面或组件时，配合 `figma-implement-design`。

## 触发条件 / When to Use

- 用户给出 Figma 链接（`figma.com/design/<fileKey>/...?node-id=1-2`）或节点 ID，要求查看、解释或提取信息。
- 需要设计中的颜色、间距、字号等变量，与代码中的 design tokens 对照。
- 需要节点截图作为视觉对照，或导出图标与图片素材。
- Figma MCP 未连接、认证失败或返回截断，需要排查。

## 前提条件 / Prerequisites

- 宿主已配置 Figma MCP：远程 server 为 `https://mcp.figma.com/mcp`（见 `agents/openai.yaml`），
  或 Figma 桌面应用提供的本地 server。配置、环境变量和验证清单见
  [references/figma-mcp-config.md](references/figma-mcp-config.md)。
- 当前账号对目标文件有查看权限。远程 server 可用 `whoami` 确认身份与席位。
- 工具名以宿主实际暴露的为准；未连接时如实说明，不要模拟工具调用结果。

## 工具选择 / Tools

| 目的 | 工具 | 说明 |
|---|---|---|
| 主要入口 | `get_design_context` | 结构化设计数据，默认附 React + Tailwind 参考代码 |
| 大节点概览 | `get_metadata` | 稀疏 XML：图层 ID、名称、类型、位置、尺寸 |
| 变量与样式 | `get_variable_defs` | 选区用到的颜色、间距、字体等变量 |
| 视觉对照 | `get_screenshot` | 节点渲染图 |
| 组件映射 | `get_code_connect_map` | 节点到代码组件的映射，用于复用现有组件 |
| FigJam | `get_figjam` | 白板图的 XML 与截图 |

完整列表和提示词示例见 [references/figma-tools-and-prompts.md](references/figma-tools-and-prompts.md)。

## 工作流程 / Workflow

1. **解析链接**：从 URL 取 `fileKey` 与 `node-id`；URL 中的 `1-2` 对应节点 ID `1:2`。
   远程 server 依赖链接定位节点；桌面 server 也可使用当前选区。
2. **先上下文**：调用 `get_design_context`。若返回过大或被截断，先用 `get_metadata`
   取得子节点 ID，再按需对子节点分别取上下文。
3. **取变量**：调用 `get_variable_defs`，把设计变量映射到项目已有 token；没有对应 token 时列出差异，不硬编码新值。
4. **取截图**：调用 `get_screenshot`，作为实现和验收的视觉基准。
5. **查组件映射**：存在 Code Connect 时调用 `get_code_connect_map`，优先复用映射到的代码组件。
6. **处理素材**：server 返回的图片或 SVG 地址（本地 server 常为 localhost 资源）按返回内容直接使用；
   不另装图标库替代设计素材，命名遵循项目约定。

## 输出 / Output

```markdown
设计：<文件名> / <节点名>（fileKey，node-id）
结构：<主要区块与布局方式，如 Auto Layout 方向、gap、padding>
变量：<设计变量 → 项目 token；缺失项>
组件：<Code Connect 映射或建议复用的组件>
素材：<需要的图标/图片及来源>
差异与疑问：<设计与代码规范的冲突、含义不明的图层名>
未获取：<工具失败、权限不足或截断的部分>
```

把 `get_design_context` 返回的代码当作参考，而非最终实现：按项目框架、组件库和 token 改写。

## 排查 / Troubleshooting

- **工具不存在**：确认宿主已启用 Figma MCP，必要时重启客户端；远程 server 需要完成 OAuth。
- **403 / 无权限**：账号对文件无访问权，或使用了错误的团队账号；用 `whoami` 核对。
- **返回截断**：节点过大，改用 `get_metadata` 后分块获取。
- **节点找不到**：检查 `node-id` 中的 `-` 是否已转换为 `:`，以及链接是否指向正确的分支或页面。
- **截图过于频繁失败**：可能触发速率限制，减少重复调用并复用已获取结果。

## 边界与限制 / Boundaries

- 只读取用户提供或有权访问的文件；不修改 Figma 文件，除非用户请求且工具支持写操作。
- 交互原型中的复杂触发和动画无法从静态上下文完全还原，需向用户确认。
- 访问令牌放在宿主配置或环境变量中，不写入仓库或输出。
- 视觉一致性需要在浏览器中对照截图验收；静态读取不等于实现已完成。
