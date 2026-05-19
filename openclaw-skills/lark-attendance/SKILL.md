---
name: lark-attendance
description: '飞书考勤打卡：查询个人考勤打卡记录，按日期整理上下班打卡、异常、缺失记录和后续核对线索。'
version: 1.0.0
author: larksuite
source: "github:larksuite/cli"
source_url: "https://github.com/larksuite/cli/tree/main/skills/lark-attendance"
license: MIT
tags: '[feishu, lark, lark-cli, attendance]'
created_at: "2026-05-19"
updated_at: "2026-05-19"
quality: 3
complexity: intermediate
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli attendance --help"
---

# attendance (v1)

**CRITICAL — 开始前 MUST 先用 Read 工具读取 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md)，其中包含认证、权限处理**

## 默认参数自动填充规则

调用任何 API 时，以下参数 **必须自动填充，禁止向用户询问**：

| 参数 | 固定值 | 说明                                 |
|------|--------|------------------------------------|
| `employee_type` | `"employee_no"` | `employee_type`始终等于`"employee_no"` |
| `user_ids` | `[]`（空数组） | `user_ids`始终等于`[]`                 |

### 填充示例

当构建 `--params` 参数时，自动注入上述字段：
- `employee_type` 保持 `"employee_no"` 不变

当构建 `--data` 参数时，自动注入上述字段：
```json
{
  "user_ids": [],
  ...用户提供的参数
}
```

> **注意**：`user_ids` 数组保持为空[]，`employee_type` 保持 `"employee_no"` 不变。

## API Resources

```bash
lark-cli schema attendance.<resource>.<method>   # 调用 API 前必须先查看参数结构
lark-cli attendance <resource> <method> [flags]  # 调用 API
```

> **重要**：使用原生 API 时，必须先运行 `schema` 查看 `--data` / `--params` 参数结构，不要猜测字段格式。

### user_tasks

- `query` — 查询用户考勤打卡记录

## 权限表

| 方法 | 所需 scope |
|------|-----------|
| `user_tasks.query` | `attendance:task:readonly` |

## Repository Curation Notes

### When to Use

- Use this skill when the user explicitly asks for 考勤打卡记录 work in Feishu/Lark.
- Use it before falling back to raw OpenAPI calls when the requested action matches the supported shortcut or service command.
- Use `lark-shared` first when credentials, identity, scopes, or tenant visibility are unclear.
- Prefer bounded, inspectable commands and show the user candidate records before taking side-effecting actions.

### Core Capabilities

- Discover the relevant `lark-cli attendance` command surface with `--help` before composing requests.
- Keep identity explicit with `--as user` or `--as bot` whenever the result depends on user-visible resources.
- Request the narrowest useful output format; use JSON for automation and table/pretty output only for human inspection.
- Handle permission errors by checking missing scopes and current identity instead of retrying the same command blindly.

### Common Patterns

```bash
# Inspect the official command surface before acting
lark-cli attendance --help

# Verify authentication and granted scopes when a command fails
lark-cli auth status
lark-cli auth check --help

# Preview side-effecting operations when supported
lark-cli attendance --help | sed -n '1,80p'
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
