---
name: lark-skill-maker
description: '创建 lark-cli 的自定义 Skill。当用户需要把飞书 API 操作封装成可复用的 Skill（包装原子 API 或编排多步流程）时使用。'
version: 1.0.0
author: larksuite
source: "github:larksuite/cli"
source_url: "https://github.com/larksuite/cli/tree/main/skills/lark-skill-maker"
license: MIT
tags: '[feishu, lark, lark-cli, skills, agent-workflow]'
created_at: "2026-05-19"
updated_at: "2026-05-19"
quality: 3
complexity: intermediate
metadata:
  requires:
    bins: ["lark-cli"]
---

# Skill Maker

基于 lark-cli 创建新 Skill。Skill = 一份 `SKILL.md`，教 AI 用 CLI 命令完成任务。

## CLI 核心能力

```bash
lark-cli <service> <resource> <method>          # 已注册 API
lark-cli <service> +<verb>                      # Shortcut（高级封装）
lark-cli api <METHOD> <path> [--data/--params]  # 任意飞书 OpenAPI
lark-cli schema <service.resource.method>       # 查参数定义
```

优先级：Shortcut > 已注册 API > `api` 裸调。

## 调研 API

```bash
# 1. 查看已有的 API 资源和 Shortcut
lark-cli <service> --help

# 2. 查参数定义
lark-cli schema <service.resource.method>

# 3. 未注册的 API，用 api 直接调用
lark-cli api GET /open-apis/vc/v1/rooms --params '{"page_size":"50"}'
lark-cli api POST /open-apis/vc/v1/rooms/search --data '{"query":"5F"}'
```

如果以上命令无法覆盖需求（CLI 没有对应的已注册 API 或 Shortcut），使用 [lark-openapi-explorer](../lark-openapi-explorer/SKILL.md) 从飞书官方文档库逐层挖掘原生 OpenAPI 接口，获取完整的方法、路径、参数和权限信息，再通过 `lark-cli api` 裸调完成任务。

通过以上流程确定需要哪些 API、参数和 scope。

## SKILL.md 模板

文件放在 `skills/lark-<name>/SKILL.md`：

```markdown
---
name: lark-<name>
version: 1.0.0
description: "<功能描述>。当用户需要<触发场景>时使用。"
metadata:
  requires:
    bins: ["lark-cli"]
---


# <标题>

> **前置条件：** 先阅读 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md)。

## 命令

\```bash
# 单步操作
lark-cli api POST /open-apis/xxx --data '{...}'

# 多步编排：说明步骤间数据传递
# Step 1: ...（记录返回的 xxx_id）
# Step 2: 使用 Step 1 的 xxx_id
\```

## 权限

| 操作 | 所需 scope |
|------|-----------|
| xxx | `scope:name` |
```

## 关键原则

- **description 决定触发** — 包含功能关键词 + "当用户需要...时使用"
- **认证** — 说明所需 scope，登录用 `lark-cli auth login --domain <name>`
- **安全** — 写入操作前确认用户意图，建议 `--dry-run` 预览
- **编排** — 说明数据传递、失败回滚、可并行步骤

## Repository Curation Notes

### When to Use

- Use this skill when the user explicitly asks for lark-cli 自定义技能 work in Feishu/Lark.
- Use it before falling back to raw OpenAPI calls when the requested action matches the supported shortcut or service command.
- Use `lark-shared` first when credentials, identity, scopes, or tenant visibility are unclear.
- Prefer bounded, inspectable commands and show the user candidate records before taking side-effecting actions.

### Core Capabilities

- Discover the relevant `lark-cli skill` command surface with `--help` before composing requests.
- Keep identity explicit with `--as user` or `--as bot` whenever the result depends on user-visible resources.
- Request the narrowest useful output format; use JSON for automation and table/pretty output only for human inspection.
- Handle permission errors by checking missing scopes and current identity instead of retrying the same command blindly.

### Common Patterns

```bash
# Inspect the official command surface before acting
lark-cli skill --help

# Verify authentication and granted scopes when a command fails
lark-cli auth status
lark-cli auth check --help

# Preview side-effecting operations when supported
lark-cli skill --help | sed -n '1,80p'
```

- For read flows, first locate the target resource, then fetch details with an ID-based command.
- For write flows, validate IDs, scopes, and ownership before issuing create/update/delete operations.
- For ambiguous people, chats, documents, tables, or meetings, list candidates and ask the user to choose.
- For automation output, keep stable IDs, URLs, timestamps, and the exact command used in the final summary.

### Boundaries

- Do not invent Feishu tokens, open IDs, chat IDs, document tokens, table IDs, or meeting IDs.
- Do not bypass tenant permission controls; ask the user or administrator to grant the required scope or visibility.
- Do not use raw `lark-cli api` until the skill-specific shortcuts and registered commands have been checked.
- Do not perform destructive changes without a clear user request and, when possible, a dry-run or read-back verification.
