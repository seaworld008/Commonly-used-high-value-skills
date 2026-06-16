---
name: lark-approval
description: '飞书审批：当前用户审批的查询与全部处理操作，覆盖待本人审批的任务与本人发起的实例。审批待办不是飞书任务（任务类待办走 lark-task）；不负责创建审批定义和发起新审批。'
version: "1.0.3"
author: larksuite
source: "github:larksuite/cli"
source_url: "https://github.com/larksuite/cli/tree/main/skills/lark-approval"
license: MIT
tags: '[feishu, lark, lark-cli, approval, workflow]'
created_at: "2026-05-19"
updated_at: "2026-06-16"
quality: 3
complexity: intermediate
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli approval --help"
---

**CRITICAL — 开始前 MUST 先用 Read 工具读取 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md)，其中包含认证、权限处理**

所有命令默认 `--as user`（审批是人的动作）。调用前先 `lark-cli schema approval.<resource>.<method>` 查参数结构，不要猜字段。

## 选哪个命令

| 想做什么 | 命令 |
|---|---|
| 查待办/已办 | `tasks query`（`topic`：1待办 2已办 17未读 18已读）|
| 看表单/进度/当前节点 | `instances get` |
| 同意/拒绝 | `tasks approve` / `tasks reject` |
| 转交/加签/退回 | `tasks transfer` / `tasks add_sign` / `tasks rollback` |
| 催办 | `tasks remind` |
| 撤回/抄送/按定义查已发起 | `instances cancel` / `instances cc` / `instances initiated` |

处理链：`tasks query` 拿 `instance_code` + `task_id`（操作必须成对带上）→ 需要细节再 `instances get` → 执行操作。

```bash
lark-cli approval tasks query --params '{"topic":"1"}' --as user
lark-cli approval tasks approve --data '{"instance_code":"<ic>","task_id":"<tid>","comment":"同意"}' --as user
```

## 不在本 skill 范围

创建审批定义/发起新审批（走飞书客户端或审批管理后台）；非审批类待办 → [`lark-task`](../lark-task/SKILL.md)

## 操作前检查

审批动作通常不可随意撤销。执行 `approve`、`reject`、`transfer`、
`add_sign`、`rollback`、`cancel` 前先确认：

1. `instance_code` 和 `task_id` 来自同一次 `tasks query` 或可信上下文。
2. 当前登录身份确实是审批人、发起人或有权限的代办人。
3. 用户给出的意见文本已经明确，不要替用户编写实质性审批理由。
4. 批量处理时先展示待处理清单和数量，再执行单条或小批量操作。

## 常见错误处理

| 现象 | 处理 |
|---|---|
| 查不到待办 | 确认 `topic`、租户、登录身份和审批范围，不要改走任务 API |
| `task_id` 失效 | 重新 `tasks query`，审批流可能已被别人处理或节点已流转 |
| 无权限 | 读取 `lark-shared` 的认证说明，确认是否需要切换用户身份 |
| 表单字段不清楚 | 先 `instances get`，只总结字段，不猜测业务含义 |

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
