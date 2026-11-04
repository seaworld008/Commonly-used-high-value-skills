# AI 平台与 Agent 开发 / AI Agent Platform

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

围绕 AI 平台能力、Agent 构建、设计到代码以及主动式工作流的技能集合。

当前分类共 **13** 个技能。

## 推荐先看

- [develop-web-game](./develop-web-game/) - 用于开发网页游戏原型、玩法循环、交互逻辑和前端实现。
- [agent-hub](./agent-hub/) - 需要多个智能体并行竞争同一任务时使用：在隔离的 Git worktree 中产出方案、评估结果并合并胜出版本。
- [chatgpt-apps](./chatgpt-apps/) - 用于设计、构建和调试 ChatGPT Apps 与相关集成能力。
- [figma](./figma/) - 通过 Figma MCP 读取设计上下文、变量、截图和素材，并排查连接问题。

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `agent-hub` | 需要多个智能体并行竞争同一任务时使用：在隔离的 Git worktree 中产出方案、评估结果并合并胜出版本。 | [目录](./agent-hub/) | [SKILL.md](./agent-hub/SKILL.md) |
| `arena` | 用于通过 codex exec 或 Antigravity CLI 编排多引擎竞争（多方案择优）或协作（拆分任务后集成），支持 Solo/Team/Quick 模式。 | [目录](./arena/) | [SKILL.md](./arena/SKILL.md) |
| `chatgpt-apps` | 用于设计、构建和调试 ChatGPT Apps 与相关集成能力。 | [目录](./chatgpt-apps/) | [SKILL.md](./chatgpt-apps/SKILL.md) |
| `develop-web-game` | 用于开发网页游戏原型、玩法循环、交互逻辑和前端实现。 | [目录](./develop-web-game/) | [SKILL.md](./develop-web-game/SKILL.md) |
| `figma` | 通过 Figma MCP 读取设计上下文、变量、截图和素材，并排查连接问题。 | [目录](./figma/) | [SKILL.md](./figma/SKILL.md) |
| `figma-implement-design` | 用于将 Figma 设计转化为可实现的前端界面和组件。 | [目录](./figma-implement-design/) | [SKILL.md](./figma-implement-design/SKILL.md) |
| `hermes-agent` | 用于配置、扩展、调试和贡献 Hermes Agent，包括多 Agent、CLI 和网关工作流。 | [目录](./hermes-agent/) | [SKILL.md](./hermes-agent/SKILL.md) |
| `hermes-open-gsd-workflow` | 在 Hermes Agent、Graphify、Open GSD Core 与可选 GSD Pi 之间做薄路由，不复制上游安装器和状态机。 | [目录](./hermes-open-gsd-workflow/) | [SKILL.md](./hermes-open-gsd-workflow/SKILL.md) |
| `mcporter` | 用于通过 mcporter CLI 列出、配置、鉴权和调用 MCP 服务器或工具。 | [目录](./mcporter/) | [SKILL.md](./mcporter/SKILL.md) |
| `native-mcp` | 用于配置 Hermes Agent 内置 MCP 客户端：服务器发现、stdio/HTTP 连接、工具注册、认证和重连排查。 | [目录](./native-mcp/) | [SKILL.md](./native-mcp/SKILL.md) |
| `openai-docs` | 用于查阅和应用 OpenAI 官方文档、API 行为和集成指南。 | [目录](./openai-docs/) | [SKILL.md](./openai-docs/SKILL.md) |
| `oracle` | 设计或评审大模型应用时使用：提示词、RAG、智能体工具循环、评测、安全护栏和成本路由。 | [目录](./oracle/) | [SKILL.md](./oracle/SKILL.md) |
| `sigil` | 需要根据仓库技术栈与约定生成、校验或更新项目专属技能时使用。 | [目录](./sigil/) | [SKILL.md](./sigil/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
