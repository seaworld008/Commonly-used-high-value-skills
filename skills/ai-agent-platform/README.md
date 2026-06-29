# AI 平台与 Agent 开发 / AI Agent Platform

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

围绕 AI 平台能力、Agent 构建、设计到代码以及主动式工作流的技能集合。

当前分类共 **16** 个技能。

## 推荐先看

- [develop-web-game](./develop-web-game/) - 用于开发网页游戏原型、玩法循环、交互逻辑和前端实现。
- [chatgpt-apps](./chatgpt-apps/) - 用于设计、构建和调试 ChatGPT Apps 与相关集成能力。
- [figma](./figma/) - 用于处理 Figma 设计读取、解析、交付和实现协作。
- [arena](./arena/) - 用于构建和运行 Agent 竞技场、评测对战和能力比较流程。

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
| `agent-hub` | 用于管理 Agent 能力中心、技能发现、路由和协作工作流。 | [目录](./agent-hub/) | [SKILL.md](./agent-hub/SKILL.md) |
| `arena` | 用于构建和运行 Agent 竞技场、评测对战和能力比较流程。 | [目录](./arena/) | [SKILL.md](./arena/SKILL.md) |
| `chatgpt-apps` | 用于设计、构建和调试 ChatGPT Apps 与相关集成能力。 | [目录](./chatgpt-apps/) | [SKILL.md](./chatgpt-apps/SKILL.md) |
| `develop-web-game` | 用于开发网页游戏原型、玩法循环、交互逻辑和前端实现。 | [目录](./develop-web-game/) | [SKILL.md](./develop-web-game/SKILL.md) |
| `figma` | 用于处理 Figma 设计读取、解析、交付和实现协作。 | [目录](./figma/) | [SKILL.md](./figma/SKILL.md) |
| `figma-implement-design` | 用于将 Figma 设计转化为可实现的前端界面和组件。 | [目录](./figma-implement-design/) | [SKILL.md](./figma-implement-design/SKILL.md) |
| `hermes-agent` | 用于配置、扩展、调试和贡献 Hermes Agent，包括多 Agent、CLI 和网关工作流。 | [目录](./hermes-agent/) | [SKILL.md](./hermes-agent/SKILL.md) |
| `hermes-graphify-gsd-nonintrusive-workflow` | 用于hermes、Graphify、gsd、nonintrusive、工作流，支持 Agent 平台编排、集成和运行管理。 | [目录](./hermes-graphify-gsd-nonintrusive-workflow/) | [SKILL.md](./hermes-graphify-gsd-nonintrusive-workflow/SKILL.md) |
| `hermes-graphify-gsd-runtime-operator` | 用于hermes、Graphify、gsd、runtime、operator，支持 Agent 平台编排、集成和运行管理。 | [目录](./hermes-graphify-gsd-runtime-operator/) | [SKILL.md](./hermes-graphify-gsd-runtime-operator/SKILL.md) |
| `mcporter` | 用于通过 mcporter CLI 列出、配置、鉴权和调用 MCP 服务器或工具。 | [目录](./mcporter/) | [SKILL.md](./mcporter/SKILL.md) |
| `native-mcp` | 用于构建和调试原生 MCP 集成、服务器和工具调用流程。 | [目录](./native-mcp/) | [SKILL.md](./native-mcp/SKILL.md) |
| `openai-docs` | 用于查阅和应用 OpenAI 官方文档、API 行为和集成指南。 | [目录](./openai-docs/) | [SKILL.md](./openai-docs/SKILL.md) |
| `oracle` | 用于oracle，支持 Agent 平台编排、集成和运行管理。 | [目录](./oracle/) | [SKILL.md](./oracle/SKILL.md) |
| `proactive-agent` | 用于让 Agent 主动规划、跟踪进展、暴露风险并提出下一步行动。 | [目录](./proactive-agent/) | [SKILL.md](./proactive-agent/SKILL.md) |
| `self-improving-agent` | 用于构建具备记忆、反馈吸收和安全自我优化机制的持续改进型 Agent。 | [目录](./self-improving-agent/) | [SKILL.md](./self-improving-agent/SKILL.md) |
| `sigil` | 用于sigil，支持 Agent 平台编排、集成和运行管理。 | [目录](./sigil/) | [SKILL.md](./sigil/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
