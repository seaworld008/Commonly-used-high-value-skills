# AI 平台与 Agent 开发 / AI Agent Platform

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

围绕 AI 平台能力、Agent 构建、设计到代码以及主动式工作流的技能集合。

当前分类共 **13** 个技能。

## 推荐先看

- [develop-web-game](./develop-web-game/) - Use when Codex is building or iterating on a web game (HTML/JS) and needs a reliable development + testing loop: implement small changes, run a Playwright-based test script with short input bursts and intentional pauses, inspect screenshots/text, and review console errors with render_game_to_text.
- [chatgpt-apps](./chatgpt-apps/) - Build, scaffold, refactor, and troubleshoot ChatGPT Apps SDK applications that combine an MCP server and widget UI. Use when Codex needs to design tools, register UI resources, wire the MCP Apps bridge or ChatGPT compatibility APIs, apply Apps SDK metadata or CSP or domain settings, or produce a docs-aligned project scaffold. Prefer a docs-first workflow by invoking the openai-docs skill or OpenAI developer docs MCP tools before generating code.
- [figma](./figma/) - Use the Figma MCP server to fetch design context, screenshots, variables, and assets from Figma, and to translate Figma nodes into production code. Trigger when a task involves Figma URLs, node IDs, design-to-code implementation, or Figma MCP setup and troubleshooting.
- [figma-implement-design](./figma-implement-design/) - Translate Figma nodes into production-ready code with 1:1 visual fidelity using the Figma MCP workflow (design context, screenshots, assets, and project-convention translation). Trigger when the user provides Figma URLs or node IDs, or asks to implement designs or components that must match Figma specs. Requires a working Figma MCP server connection.

<a id="hermes-graphify-gsd-global-workflow"></a>
## Hermes + graphify + GSD 全局非侵入式工作流

`hermes-graphify-gsd-nonintrusive-workflow` 适合在还没有进入具体项目之前，先把 Hermes Agent、graphify 和 GSD 组合成一套可复用、可升级、非侵入式的本机工作流。

### 什么时候使用

- 想让 Hermes 负责 orchestration / memory / execution。
- 想让 graphify 负责代码图谱、架构回忆和低成本刷新。
- 想让 GSD 负责 planning cadence、phase management 和执行节奏。
- 想保留 Hermes、graphify、GSD 上游仓库的干净状态，不希望为了本机集成去 patch 上游源码。
- 想把适配层放在 wrappers、项目脚本和文档中，方便未来升级。

### 推荐提示词

```text
请使用 hermes-graphify-gsd-nonintrusive-workflow，帮我检查本机 Hermes 是否已安装，并在不修改上游仓库代码的前提下，配置 graphify 和 GSD 的全局工作流。
```

### 核心执行原则

1. 先检查 `command -v hermes` 和 `hermes --version`。
2. 如果 Hermes 不存在，只提示用户手动安装 Hermes，不自动安装 Hermes。
3. 如果 Hermes 已存在，再安装或升级 graphify 与 GSD。
4. graphify 使用当前 PyPI 包名 `graphifyy`，CLI 入口仍是 `graphify`。
5. GSD 默认使用 Codex runtime：`npx -y get-shit-done-cc@latest --codex --global --sdk`。
6. 优先创建或复用 `~/.local/bin/` wrappers，不直接修改 Hermes、graphify、GSD 上游源码。

### 可复用文件

| 文件 | 用途 |
|------|------|
| `templates/bootstrap-toolchain.sh` | 检查 Hermes，并安装/升级 graphify 与 GSD。 |
| `templates/graphify-wrapper.sh` | 在多个 Python 环境中寻找可 import graphify 的解释器。 |
| `templates/gsd-sdk-wrapper.sh` | 通过稳定路径调用 GSD SDK CLI。 |
| `templates/ai-workflow.sh` | 给项目提供统一的 `doctor` / `context` / `sync` 入口。 |
| `references/first-install.md` | 首次安装策略和推荐命令。 |
| `references/upgrade-contract.md` | 升级时优先修 wrappers 和项目脚本，而不是上游源码。 |

### 常用验证命令

```bash
command -v hermes
hermes --version
command -v graphify
graphify --help
command -v gsd-sdk
gsd-sdk --version
```

<a id="hermes-graphify-gsd-runtime-operator"></a>
## Hermes + graphify + GSD Runtime Operator

`hermes-graphify-gsd-runtime-operator` 适合在仓库已经完成接入之后，专门处理运行态诊断、writer ownership、auto-continue、handoff / blocked / lease / cron 等状态问题。

### 什么时候使用

- 想知道“现在是谁在写”。
- 想确认当前 repo 还是不是推荐 writer surface。
- 想排查 `auto-progress` 一直显示 running 的原因。
- 想清理旧 sandbox / worktree 遗留的 writer lease。
- 想确认 handoff、blocked、planning mirror、lease 状态是否一致。

### 推荐提示词

```text
请使用 hermes-graphify-gsd-runtime-operator，检查当前仓库的 auto-continue / writer lease / blocked / handoff 状态，并告诉我现在是否还是主仓库在负责写入。
```

### 推荐先跑的命令

```bash
./scripts/ai-workflow.sh doctor
./scripts/ai-workflow.sh auto-execution-surface-show
./scripts/ai-workflow.sh auto-runner-show
./scripts/ai-workflow.sh auto-progress
./scripts/ai-workflow.sh auto-workflow-state-show
```

### 和其他技能的关系

- 还没接入工作流时，先用 `hermes-graphify-gsd-nonintrusive-workflow` 或 `hermes-graphify-gsd-project-integration`。
- 已经接入，只是运行态异常时，优先切到 `hermes-graphify-gsd-runtime-operator`。

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `agent-hub` | Multi-agent collaboration plugin that spawns N parallel subagents competing on the same task via git worktree isolation. Agents work independently, results are evaluated by metric or LLM judge, and the best branch is merged. Use when: user wants multiple approaches tried in parallel — code optimization, content variation, research exploration, or any task that benefits from parallel competition. Requires: a git repo. | [目录](./agent-hub/) | [SKILL.md](./agent-hub/SKILL.md) |
| `chatgpt-apps` | Build, scaffold, refactor, and troubleshoot ChatGPT Apps SDK applications that combine an MCP server and widget UI. Use when Codex needs to design tools, register UI resources, wire the MCP Apps bridge or ChatGPT compatibility APIs, apply Apps SDK metadata or CSP or domain settings, or produce a docs-aligned project scaffold. Prefer a docs-first workflow by invoking the openai-docs skill or OpenAI developer docs MCP tools before generating code. | [目录](./chatgpt-apps/) | [SKILL.md](./chatgpt-apps/SKILL.md) |
| `develop-web-game` | Use when Codex is building or iterating on a web game (HTML/JS) and needs a reliable development + testing loop: implement small changes, run a Playwright-based test script with short input bursts and intentional pauses, inspect screenshots/text, and review console errors with render_game_to_text. | [目录](./develop-web-game/) | [SKILL.md](./develop-web-game/SKILL.md) |
| `figma` | Use the Figma MCP server to fetch design context, screenshots, variables, and assets from Figma, and to translate Figma nodes into production code. Trigger when a task involves Figma URLs, node IDs, design-to-code implementation, or Figma MCP setup and troubleshooting. | [目录](./figma/) | [SKILL.md](./figma/SKILL.md) |
| `figma-implement-design` | Translate Figma nodes into production-ready code with 1:1 visual fidelity using the Figma MCP workflow (design context, screenshots, assets, and project-convention translation). Trigger when the user provides Figma URLs or node IDs, or asks to implement designs or components that must match Figma specs. Requires a working Figma MCP server connection. | [目录](./figma-implement-design/) | [SKILL.md](./figma-implement-design/SKILL.md) |
| `hermes-agent` | Complete guide to using and extending Hermes Agent — CLI usage, setup, configuration, spawning additional agents, gateway platforms, skills, voice, tools, profiles, and a concise contributor reference. Load this skill when helping users configure Hermes, troubleshoot issues, spawn agent instances, or make code contributions. | [目录](./hermes-agent/) | [SKILL.md](./hermes-agent/SKILL.md) |
| `hermes-graphify-gsd-nonintrusive-workflow` | Use when integrating Hermes Agent, graphify, and GSD into a local development workflow without modifying upstream repositories, especially when the user wants upgrade-safe wrappers, project-level workflow scripts, graph-aware planning, and a reusable setup that survives future upstream updates. | [目录](./hermes-graphify-gsd-nonintrusive-workflow/) | [SKILL.md](./hermes-graphify-gsd-nonintrusive-workflow/SKILL.md) |
| `hermes-graphify-gsd-runtime-operator` | Use when operating or debugging a repo-local Hermes + graphify + GSD autonomous runtime, especially when checking writer ownership, execution-surface eligibility, handoff/blocked state, stale cron or lease metadata, and whether the main project repo is still the only recommended writer surface. | [目录](./hermes-graphify-gsd-runtime-operator/) | [SKILL.md](./hermes-graphify-gsd-runtime-operator/SKILL.md) |
| `mcporter` | Use the mcporter CLI to list, configure, auth, and call MCP servers/tools directly (HTTP or stdio), including ad-hoc servers, config edits, and CLI/type generation. | [目录](./mcporter/) | [SKILL.md](./mcporter/SKILL.md) |
| `native-mcp` | Built-in MCP (Model Context Protocol) client that connects to external MCP servers, discovers their tools, and registers them as native Hermes Agent tools. Supports stdio and HTTP transports with automatic reconnection, security filtering, and zero-config tool injection. | [目录](./native-mcp/) | [SKILL.md](./native-mcp/SKILL.md) |
| `openai-docs` | Use when the user asks how to build with OpenAI products or APIs and needs up-to-date official documentation with citations (for example: Codex, Responses API, Chat Completions, Apps SDK, Agents SDK, Realtime, model capabilities or limits); prioritize OpenAI docs MCP tools and restrict any fallback browsing to official OpenAI domains. | [目录](./openai-docs/) | [SKILL.md](./openai-docs/SKILL.md) |
| `proactive-agent` | 增强 Agent 的主动规划与自我迭代能力，从被动执行升级为主动协作。 | [目录](./proactive-agent/) | [SKILL.md](./proactive-agent/SKILL.md) |
| `self-improving-agent` | 带记忆与自我优化机制的 Agent 技能，能在迭代中持续改进行为。 | [目录](./self-improving-agent/) | [SKILL.md](./self-improving-agent/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
