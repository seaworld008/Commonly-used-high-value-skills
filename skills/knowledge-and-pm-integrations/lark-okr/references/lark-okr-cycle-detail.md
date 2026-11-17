# okr +cycle-detail

> **前置条件：** 先阅读 [`lark-shared/SKILL.md`](../../lark-shared/SKILL.md) 了解认证、全局参数和安全规则。

列出指定 OKR 周期下的所有目标及其关键结果。

## 推荐命令

```bash
# 列出指定周期的目标和关键结果（默认 simple 风格，半纯文本格式，推荐使用，更简洁）
lark-cli okr +cycle-detail --cycle-id 1234567890123456789 --prefer-draft=true --as user

# 列出指定周期的目标和关键结果（richtext 风格，原始 ContentBlock JSON）
lark-cli okr +cycle-detail --cycle-id 1234567890123456789 --prefer-draft=true --style richtext --as user

# 预览 API 调用而不实际执行
lark-cli okr +cycle-detail --cycle-id 1234567890123456789 --prefer-draft=false --dry-run --as user
```

## 参数

| 参数           | 必填 | 默认值      | 说明                                                                                                                          |
|--------------|----|----------|-----------------------------------------------------------------------------------------------------------------------------|
| `--cycle-id` | 是  | —        | OKR 周期 ID（int64 类型）。从 `+cycle-list` 获取。                                                                                     |
| `--style`    | 否  | `simple` | 输出风格：`simple`（半纯文本格式，不涉及字体/颜色等信息时推荐使用） \| `richtext`（原始 ContentBlock JSON）。请参考 [ContentBlock 格式](lark-okr-contentblock.md)。 |
| `--prefer-draft` | 否 | `true` | 优先读取可见草稿，无草稿时读取发布态；`false` 只读发布态。命令中显式传值。 |
| `--dry-run`  | 否  | —        | 预览 API 调用而不实际执行。                                                                                                            |
| `--format`   | 否  | `json`   | 输出格式。                                                                                                                       |

## 工作流程

1. 使用 `lark-cli okr +cycle-list` 获取 OKR 周期 ID。
2. 查看本人 OKR 用 `lark-cli okr +cycle-detail --cycle-id "123456" --prefer-draft=true --as user`；明确只看发布态或查看他人时用 `--prefer-draft=false`。user 只能看到本人草稿；bot 仅在用户明确要求且具有对应数据权限时使用。
3. 报告目标数量、各目标 ID、状态、权重和 KR；分数等发布态字段只在实际返回时报告。

## 输出

发布态 richtext 示例 JSON（`--prefer-draft=false --style richtext`，content/notes 字符串以占位内容表示；草稿返回 `is_draft=true`，不展示 score/notes）：

```json
{
  "cycle_id": "1234567890123456789",
  "objectives": [
    {
      "id": "2345678901234567890",
      "create_time": "2025-01-01 00:00:00",
      "update_time": "2025-01-15 12:00:00",
      "owner": {
        "owner_type": "user",
        "user_id": "ou_xxx"
      },
      "cycle_id": "1234567890123456789",
      "position": 1,
      "score": 0.7,
      "weight": 1.0,
      "deadline": "2025-06-30 23:59:59",
      "category_id": "cat_456",
      "is_draft": false,
      "content": "{...}",
      "notes": "{...}",
      "key_results": [
        {
          "id": "3456789012345678901",
          "create_time": "2025-01-01 00:00:00",
          "update_time": "2025-01-15 12:00:00",
          "owner": {
            "owner_type": "user",
            "user_id": "ou_xxx"
          },
          "objective_id": "2345678901234567890",
          "position": 1,
          "score": 0.8,
          "weight": 0.5,
          "deadline": "2025-06-30 23:59:59",
          "content": "{...}",
          "is_draft": false
        }
      ]
    }
  ],
  "total": 1
}
```

其中，content 和 notes 字段格式由 `--style` 控制：
- `--style simple`（默认）：`SemiPlainContent` 对象，包含 `text`、`mention`、`docs` 字段
- `--style richtext`：JSON 字符串，为 OKR ContentBlock 富文本格式

请参考 [lark-okr-contentblock.md](lark-okr-contentblock.md) 了解两种格式的详细信息。

`is_draft` 表示这次返回的实体状态，不表示所有调用者都能看到草稿。只有当前身份可见草稿且可编辑时才能据 Objective 的 `is_draft=false` 判断无草稿；不可见或空结果不能作为证据。读取不会创建草稿；写前按 [草稿工作流](lark-okr-drafts.md) 选择状态。

## 参考

- [lark-okr](../SKILL.md) -- 所有 OKR 命令(shortcut 和 API 接口)
- [lark-shared](../../lark-shared/SKILL.md) -- 认证和全局参数
