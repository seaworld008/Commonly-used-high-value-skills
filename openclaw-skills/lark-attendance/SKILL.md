---
name: lark-attendance
description: 'Use when querying Lark attendance records, checking missing clock-ins, and preparing traceable explanations for attendance exceptions.'
zh_description: "用于查询飞书考勤记录、核对打卡缺失、整理异常考勤并生成可追溯说明。"
version: "1.0.5"
author: larksuite
source: "github:larksuite/cli"
source_url: "https://github.com/larksuite/cli/tree/7beffb086d7fa3c5b843d8affa7c089f49cfc65e/skills/lark-attendance"
license: MIT
tags: '[feishu, lark, lark-cli, attendance]'
created_at: "2026-05-19"
updated_at: "2026-10-12"
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

## 查询工作流

考勤查询是只读操作，但结果通常会进入异常说明或工资核对。每次查询都保留
查询时间范围、身份、原始返回和时区，避免把“没有记录”误写成“没有打卡”。

### 1. 先确认查询边界

- 明确是查询当前用户，还是用户明确授权的员工编号；没有授权时不要扩大到全员。
- 明确日期范围和组织时区。日期边界应使用业务时区解释，不要直接把本地日期拼成 UTC。
- 先读取 `../lark-shared/SKILL.md`，默认使用 `--as user`；不要用 bot 身份猜测个人考勤。

### 2. 读取当前 schema

资源字段可能随 Lark API 版本变化。先执行：

```bash
lark-cli schema attendance.user_tasks.query
```

以 schema 输出为准确认 `--params` / `--data` 的字段、时间格式、分页字段和返回结构。
不要根据旧示例补写未声明的字段，也不要把员工姓名当成 `user_ids`。

### 3. 以最小范围执行查询

按照 schema 生成参数后再调用：

```bash
lark-cli attendance user_tasks query --params '<schema-confirmed-json>' --as user
```

参数必须保留默认值 `employee_type=employee_no` 与 `user_ids=[]`，除非当前
schema 明确要求不同值。一次只查询必要的日期范围；需要翻页时使用返回的分页游标，
不要通过重复请求扩大范围。

### 4. 解释结果而不是猜测原因

| 结果 | 处理 |
|------|------|
| 有打卡记录 | 按返回的事件时间和类型整理，不自行补齐缺失事件。 |
| 空结果 | 报告“该范围未返回记录”，同时保留范围、身份和 schema 版本；不要直接判定旷工。 |
| `permission denied` / `missing scope` | 停止重试，转 `lark-shared` 的权限流程；不要切换 bot 身份绕过。 |
| 参数或 schema 错误 | 重新读取当前 schema，只修正已确认的字段；不要盲目重放旧请求。 |
| rate limit 或临时网络错误 | 最多做一次有限重试；仍失败就报告未验证，不生成考勤结论。 |

如果返回记录使用 UTC 或带偏移时间，先统一显示时区，再进行“迟到、早退、缺卡”
等派生判断。派生判断必须标注规则和证据；跨午夜班次、补卡和人工修正应列为待确认。

## 可追溯输出模板

完成查询后，用简洁表格记录：

```text
身份：user（不要记录 access token）
范围：<业务时区下的开始/结束日期>
请求：attendance.user_tasks.query
参数来源：本次 schema 输出；employee_type=employee_no；user_ids=[]
结果：<记录数量 / 空结果 / 错误>
时区：<显示时区>
证据：<脱敏后的返回字段或原始输出位置>
限制：<权限、分页、跨午夜或服务端延迟等>
```

不要把身份证号、手机号、access token 或完整员工数据复制进报告。只保留支撑结论
所需的最小字段；如需把结果交给 HR 或财务，先按组织的数据保留和脱敏规则处理。

## 验证清单

- [ ] 已读取 `lark-shared` 并确认 `--as user` 与授权范围。
- [ ] 已在同一轮执行 `lark-cli schema attendance.user_tasks.query`。
- [ ] 参数只包含 schema 声明的字段，并保留默认参数规则。
- [ ] 日期范围、时区、分页游标和原始结果已记录。
- [ ] 空结果、权限错误和临时失败没有被改写成考勤结论。
- [ ] 输出已脱敏，且没有执行任何写入或权限变更命令。

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
- Treat skill selection as routing, not ceremony: invoke only the narrowest
  applicable workflow and keep user or repository instructions authoritative.
<!-- LOCAL-QUALITY-SUPPLEMENT:END -->
