---
name: lark-approval
description: '飞书审批 API：审批实例、审批任务管理。'
version: "1.0.1"
author: larksuite
source: "github:larksuite/cli"
source_url: "https://github.com/larksuite/cli/tree/main/skills/lark-approval"
license: MIT
tags: '[feishu, lark, lark-cli, approval, workflow]'
created_at: "2026-05-19"
updated_at: "2026-05-20"
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
<!-- LOCAL-QUALITY-SUPPLEMENT:START -->
## Usage Notes

This supplement is maintained by the repository sync pipeline. It keeps the
imported upstream skill usable inside this curated collection when the upstream
source is intentionally concise.

## Common Patterns

```text
1. Confirm that the user's task matches the skill trigger.
2. Read the relevant project files or user-provided context before acting.
3. Choose the smallest reversible action that advances the task.
4. Run the verification command or manual check that proves the result.
5. Report the outcome, evidence, and any remaining risk.
```

## Boundaries

- Prefer the upstream workflow for Lark Approval; this section only adds local quality
  guardrails.
- Do not invent project facts when required files, vaults, services, or tools are
  unavailable.
- Stop and ask for clarification when the next action could overwrite user work,
  expose private data, or change production state.
<!-- LOCAL-QUALITY-SUPPLEMENT:END -->
