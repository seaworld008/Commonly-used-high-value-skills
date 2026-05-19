---
name: lark-approval
description: '飞书审批 API：审批实例、审批任务管理。'
version: 1.0.0
author: larksuite
source: "github:larksuite/cli"
source_url: "https://github.com/larksuite/cli/tree/main/skills/lark-approval"
license: MIT
tags: '[feishu, lark, lark-cli, approval, workflow]'
created_at: "2026-05-19"
updated_at: "2026-05-19"
quality: 3
complexity: intermediate
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli approval --help"
---

# approval (v4)

**CRITICAL — 开始前 MUST 先用 Read 工具读取 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md)，其中包含认证、权限处理**

## API Resources

```bash
lark-cli schema approval.<resource>.<method>   # 调用 API 前必须先查看参数结构
lark-cli approval <resource> <method> [flags] # 调用 API
```

> **重要**：使用原生 API 时，必须先运行 `schema` 查看 `--data` / `--params` 参数结构，不要猜测字段格式。

### instances

  - `get` — 获取单个审批实例详情
  - `cancel` — 撤回审批实例
  - `cc` — 抄送审批实例
  - `initiated` — 查询用户的已发起列表

### tasks

  - `remind` — 催办审批人
  - `approve` — 同意审批任务
  - `reject` — 拒绝审批任务
  - `transfer` — 转交审批任务
  - `query` — 查询用户的任务列表
  - `add_sign` — 审批任务加签
  - `rollback` — 退回审批任务

## 权限表

| 方法 | 所需 scope |
|------|-----------|
| `instances.get` | `approval:instance:read` |
| `instances.cancel` | `approval:instance:write` |
| `instances.cc` | `approval:instance:write` |
| `instances.initiated` | `approval:instance:read` |
| `tasks.remind` | `approval:instance:write` |
| `tasks.approve` | `approval:task:write` |
| `tasks.reject` | `approval:task:write` |
| `tasks.transfer` | `approval:task:write` |
| `tasks.query` | `approval:task:read` |
| `tasks.add_sign` | `approval:task:write` |
| `tasks.rollback` | `approval:task:write` |

## Repository Curation Notes

### When to Use

- Use this skill when the user explicitly asks for 审批任务和实例 work in Feishu/Lark.
- Use it before falling back to raw OpenAPI calls when the requested action matches the supported shortcut or service command.
- Use `lark-shared` first when credentials, identity, scopes, or tenant visibility are unclear.
- Prefer bounded, inspectable commands and show the user candidate records before taking side-effecting actions.

### Core Capabilities

- Discover the relevant `lark-cli approval` command surface with `--help` before composing requests.
- Keep identity explicit with `--as user` or `--as bot` whenever the result depends on user-visible resources.
- Request the narrowest useful output format; use JSON for automation and table/pretty output only for human inspection.
- Handle permission errors by checking missing scopes and current identity instead of retrying the same command blindly.

### Common Patterns

```bash
# Inspect the official command surface before acting
lark-cli approval --help

# Verify authentication and granted scopes when a command fails
lark-cli auth status
lark-cli auth check --help

# Preview side-effecting operations when supported
lark-cli approval --help | sed -n '1,80p'
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
