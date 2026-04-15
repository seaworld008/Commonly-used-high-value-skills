# AI 平台与 Agent 开发 / AI Agent Platform

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

围绕 AI 平台能力、Agent 构建、设计到代码以及主动式工作流的技能集合。

当前分类共 **12** 个技能。

## 推荐先看

- [develop-web-game](./develop-web-game/) - Use when Codex is building or iterating on a web game (HTML/JS) and needs a reliable development + testing loop: implement small changes, run a Playwright-based test script with short input bursts and intentional pauses, inspect screenshots/text, and review console errors with render_game_to_text.
- [chatgpt-apps](./chatgpt-apps/) - Build, scaffold, refactor, and troubleshoot ChatGPT Apps SDK applications that combine an MCP server and widget UI. Use when Codex needs to design tools, register UI resources, wire the MCP Apps bridge or ChatGPT compatibility APIs, apply Apps SDK metadata or CSP or domain settings, or produce a docs-aligned project scaffold. Prefer a docs-first workflow by invoking the openai-docs skill or OpenAI developer docs MCP tools before generating code.
- [figma](./figma/) - Use the Figma MCP server to fetch design context, screenshots, variables, and assets from Figma, and to translate Figma nodes into production code. Trigger when a task involves Figma URLs, node IDs, design-to-code implementation, or Figma MCP setup and troubleshooting.
- [figma-implement-design](./figma-implement-design/) - Translate Figma nodes into production-ready code with 1:1 visual fidelity using the Figma MCP workflow (design context, screenshots, assets, and project-convention translation). Trigger when the user provides Figma URLs or node IDs, or asks to implement designs or components that must match Figma specs. Requires a working Figma MCP server connection.

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `agent-hub` | 用于多 Agent 系统编排、Agent 间通信协议设计与生命周期管理。来源：alirezarezvani/claude-skills POWERFUL tier。 | [目录](./agent-hub/) | [SKILL.md](./agent-hub/SKILL.md) |
| `chatgpt-apps` | Build, scaffold, refactor, and troubleshoot ChatGPT Apps SDK applications that combine an MCP server and widget UI. Use when Codex needs to design tools, register UI resources, wire the MCP Apps bridge or ChatGPT compatibility APIs, apply Apps SDK metadata or CSP or domain settings, or produce a docs-aligned project scaffold. Prefer a docs-first workflow by invoking the openai-docs skill or OpenAI developer docs MCP tools before generating code. | [目录](./chatgpt-apps/) | [SKILL.md](./chatgpt-apps/SKILL.md) |
| `develop-web-game` | Use when Codex is building or iterating on a web game (HTML/JS) and needs a reliable development + testing loop: implement small changes, run a Playwright-based test script with short input bursts and intentional pauses, inspect screenshots/text, and review console errors with render_game_to_text. | [目录](./develop-web-game/) | [SKILL.md](./develop-web-game/SKILL.md) |
| `figma` | Use the Figma MCP server to fetch design context, screenshots, variables, and assets from Figma, and to translate Figma nodes into production code. Trigger when a task involves Figma URLs, node IDs, design-to-code implementation, or Figma MCP setup and troubleshooting. | [目录](./figma/) | [SKILL.md](./figma/SKILL.md) |
| `figma-implement-design` | Translate Figma nodes into production-ready code with 1:1 visual fidelity using the Figma MCP workflow (design context, screenshots, assets, and project-convention translation). Trigger when the user provides Figma URLs or node IDs, or asks to implement designs or components that must match Figma specs. Requires a working Figma MCP server connection. | [目录](./figma-implement-design/) | [SKILL.md](./figma-implement-design/SKILL.md) |
| `hermes-agent` | Complete guide to using and extending Hermes Agent — CLI usage, setup, configuration, spawning additional agents, gateway platforms, skills, voice, tools, profiles, and a concise contributor reference. Load this skill when helping users configure Hermes, troubleshoot issues, spawn agent instances, or make code contributions. | [目录](./hermes-agent/) | [SKILL.md](./hermes-agent/SKILL.md) |
| `hermes-graphify-gsd-nonintrusive-workflow` | Use when integrating Hermes Agent, graphify, and GSD into a local development workflow without modifying upstream repositories, especially when the user wants upgrade-safe wrappers, project-level workflow scripts, graph-aware planning, and a reusable setup that survives future upstream updates. | [目录](./hermes-graphify-gsd-nonintrusive-workflow/) | [SKILL.md](./hermes-graphify-gsd-nonintrusive-workflow/SKILL.md) |
| `mcporter` | Use the mcporter CLI to list, configure, auth, and call MCP servers/tools directly (HTTP or stdio), including ad-hoc servers, config edits, and CLI/type generation. | [目录](./mcporter/) | [SKILL.md](./mcporter/SKILL.md) |
| `native-mcp` | Built-in MCP (Model Context Protocol) client that connects to external MCP servers, discovers their tools, and registers them as native Hermes Agent tools. Supports stdio and HTTP transports with automatic reconnection, security filtering, and zero-config tool injection. | [目录](./native-mcp/) | [SKILL.md](./native-mcp/SKILL.md) |
| `openai-docs` | Use when the user asks how to build with OpenAI products or APIs and needs up-to-date official documentation with citations (for example: Codex, Responses API, Chat Completions, Apps SDK, Agents SDK, Realtime, model capabilities or limits); prioritize OpenAI docs MCP tools and restrict any fallback browsing to official OpenAI domains. | [目录](./openai-docs/) | [SKILL.md](./openai-docs/SKILL.md) |
| `proactive-agent` | 增强 Agent 的主动规划与自我迭代能力，从被动执行升级为主动协作。 | [目录](./proactive-agent/) | [SKILL.md](./proactive-agent/SKILL.md) |
| `self-improving-agent` | 带记忆与自我优化机制的 Agent 技能，能在迭代中持续改进行为。 | [目录](./self-improving-agent/) | [SKILL.md](./self-improving-agent/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
