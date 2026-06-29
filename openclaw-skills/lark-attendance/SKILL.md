---
name: lark-attendance
description: 'Use when users need to query Feishu/Lark attendance records, audit punch-in gaps, summarize abnormal attendance, or reconcile missing check-ins with HR-facing evidence.'
zh_description: "用于查询飞书考勤记录、核对打卡缺失、整理异常考勤并生成可追溯说明。"
version: "1.0.2"
author: larksuite
source: "github:larksuite/cli"
source_url: "https://github.com/larksuite/cli/tree/main/skills/lark-attendance"
license: MIT
tags: '[feishu, lark, lark-cli, attendance]'
created_at: "2026-05-19"
updated_at: "2026-06-29"
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

- Prefer the upstream workflow for Lark Attendance; this section only adds local quality
  guardrails.
- Do not invent project facts when required files, vaults, services, or tools are
  unavailable.
- Stop and ask for clarification when the next action could overwrite user work,
  expose private data, or change production state.
<!-- LOCAL-QUALITY-SUPPLEMENT:END -->

<!-- LOCAL-CURATION-SUPPLEMENT:START -->
## Attendance Review Checklist

Use this checklist before returning attendance findings:

- Confirm the target date range, timezone, and whether the user wants raw records, exception summaries, or reconciliation evidence.
- Resolve the person identifier first; do not mix `open_id`, employee number, and user display name in the same API call.
- Keep `employee_type` consistent with the identifier type required by the endpoint.
- Treat empty results as ambiguous until the date range, permission scope, and user identity are verified.
- Separate late arrival, early leave, missing punch, leave approval, business trip, and holiday explanations when the API data supports it.
- If multiple employees are queried, preserve one row per employee per day so downstream HR review can audit the result.

## Output Format

Prefer a compact table for user-facing summaries:

| Date | Person | Status | Evidence | Follow-up |
|---|---|---|---|---|
| 2026-06-29 | Example | Missing PM punch | `user_tasks.query` returned no end record | Ask employee to confirm |

When uncertainty remains, state exactly which API response, scope, or identifier prevented a definitive conclusion.
<!-- LOCAL-CURATION-SUPPLEMENT:END -->
