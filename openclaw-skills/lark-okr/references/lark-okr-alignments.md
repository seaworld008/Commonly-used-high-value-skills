# OKR 对齐关系管理

> **前置条件：** 先阅读 [`lark-shared/SKILL.md`](../../lark-shared/SKILL.md) 了解认证、全局参数和安全规则。

管理 OKR 目标之间的对齐关系，包括查询、创建和删除对齐。

## 对齐关系说明

OKR 对齐关系表示两个目标之间的关联：
- **对齐（aligning）**：目标 A 对齐到目标 B，表示 A 的完成有助于 B 的完成
- **被对齐（aligned）**：目标 B 被目标 A 对齐

每个对齐关系有唯一的 `alignment_id`，用于删除操作。被对齐目标使用发布态；草稿对齐属于发起方 Objective，随其整个聚合发布或撤销，也可单独删除（user 仅能删除自己发起的对齐）。

原生接口通过 JSON 选择状态：读取用 `--params` 中的 `prefer_draft`；创建用 `--data` 中的 `apply_to_draft`；删除用 `--params` 中的 `apply_to_draft`。这些对齐接口默认 `false`，按 [草稿工作流](lark-okr-drafts.md) 显式选择，不使用 shortcut 顶层 flag。

---

## 一、查询对齐关系

### 命令

```bash
lark-cli okr objective.alignments list --objective-id "<目标ID>" [flags] --params '{"prefer_draft":true}' --as user
```

### 常用示例

```bash
# 获取目标的所有对齐关系（同时包含对齐和被对齐）
lark-cli okr objective.alignments list --params '{"prefer_draft":true}' --as user \
  --objective-id "7652569715131075772"

# 只查询该目标主动对齐他人的关系
lark-cli okr objective.alignments list --params '{"prefer_draft":true}' --as user \
  --objective-id "7652569715131075772" \
  --align-type "aligning"

# 只查询他人对齐该目标的关系
lark-cli okr objective.alignments list --params '{"prefer_draft":true}' --as user \
  --objective-id "7652569715131075772" \
  --align-type "aligned"

# 自动分页获取全部数据
lark-cli okr objective.alignments list --params '{"prefer_draft":true}' --as user \
  --objective-id "7652569715131075772" \
  --page-all
```

### 参数

| 参数                   | 必填 | 默认值            | 说明                                                                 |
|----------------------|----|----------------|--------------------------------------------------------------------|
| `--objective-id`     | 是  | —              | 目标 ID                                                              |
| `--align-type`       | 否  | —              | 对齐类型：`aligning`（该目标对齐他人）\| `aligned`（他人对齐该目标）。留空返回全部。 |
| `--user-id-type`     | 否  | `open_id`      | 用户 ID 类型：`open_id` \| `union_id` \| `user_id`                    |
| `--page-size`        | 否  | `10`           | 分页大小，最大 100                                                    |
| `--page-all` | 否 | — | 自动分页获取全部数据 |
| `--params` | 否 | — | JSON query：显式传 prefer_draft=true（草稿优先）或 false（仅发布态）。 |

### 返回字段说明

- `items[].id`：对齐关系 ID（删除时需要）
- `items[].from_entity_id`：发起对齐的目标 ID
- `items[].to_entity_id`：被对齐的目标 ID
- `items[].from_owner` / `to_owner`：双方所有者信息
- `items[].is_draft`：本条返回草稿（`true`）或发布态（`false`）；同一列表可以混合返回两者。

草稿可见性按每条对齐的**发起方所有者**判断：user 可读取本人发起的草稿，不能读取他人发起的草稿；bot 在查询目标属于应用数据权限范围时可读取草稿，仅在用户明确要求时使用。user 读取他人发布态对齐仍受阅览权限过滤，不根据空列表断言无草稿。

仅看发布态时改传 `--params '{"prefer_draft":false}'`。单条查询同样显式选择视图：

```bash
lark-cli okr alignments get --alignment-id "<对齐ID>" --params '{"prefer_draft":true}' --as user
```

---

## 二、创建对齐关系

### 命令

```bash
lark-cli okr objective.alignments create --objective-id "<发起对齐的目标ID>" --data '{"to_entity_id":"<目标ID>","to_entity_type":2,"apply_to_draft":true}' --as user
```

### 常用示例

```bash
# 创建对齐关系：目标 7652569715131075772 对齐到目标 7652569715131075773
lark-cli okr objective.alignments create --as user \
  --objective-id "7652569715131075772" \
  --data '{"apply_to_draft":true,"to_entity_id":"7652569715131075773","to_entity_type":2}'

# 从文件读取请求体（alignment.json 也需显式包含 apply_to_draft）
lark-cli okr objective.alignments create --as user \
  --objective-id "7652569715131075772" \
  --data @alignment.json
```

### 参数

| 参数               | 必填 | 说明                                                                 |
|------------------|----|--------------------------------------------------------------------|
| `--objective-id` | 是  | 发起对齐的目标 ID（"我"的目标）                                          |
| `--data`         | 是  | JSON 请求体，格式见下方。支持 `@文件路径` 从文件读取。                           |

### 请求体格式

```json
{
  "to_entity_id": "7652569715131075773",
  "to_entity_type": 2,
  "apply_to_draft": true
}
```

`to_entity_id` 为被对齐目标 ID，`to_entity_type=2` 表示 Objective。`apply_to_draft=true` 写入发起方草稿，无草稿时先创建所属 Objective 草稿；`false` 写入发布态。

### 对齐规则

- **禁止自对齐**：不能自己对齐自己
- **周期时间重叠**：两个目标所在周期的时间范围必须有重叠
- **权限要求**：需要对发起对齐的目标有编辑权限

### 返回

成功后返回 `alignment_id`，保存好以便后续删除。

---

## 三、删除对齐关系

### 命令

```bash
lark-cli okr alignments delete --alignment-id "<对齐关系ID>" --params '{"apply_to_draft":true}' --as user
```

### 常用示例

```bash
# 删除指定的对齐关系
lark-cli okr alignments delete --params '{"apply_to_draft":true}' --as user \
  --alignment-id "7652569715131075780"
```

### 参数

| 参数               | 必填 | 说明                                   |
|------------------|----|--------------------------------------|
| `--alignment-id` | 是 | 对齐关系 ID（从 list 或 create 返回） |
| `--params` | 否 | JSON query：显式传 apply_to_draft=true 删除草稿对齐（无草稿时先创建发起方草稿），false 删除发布态对齐。 |

### 注意事项

- 删除前核对对齐 ID、选定状态和已有授权范围；草稿变更随发起方 Objective 聚合发布或撤销
- 需要对关联的目标有编辑权限

---

## 完整工作流示例

### 场景：将目标 A 对齐到目标 B

1. **查询现有对齐关系**并按 [草稿工作流](lark-okr-drafts.md) 选择状态。以下以草稿操作为例；发布态读取和写入均改为显式 false。
   ```bash
   lark-cli okr objective.alignments list --params '{"prefer_draft":true}' --as user \
     --objective-id "目标A的ID" \
     --align-type "aligning"
   ```

2. **创建对齐关系**
   ```bash
   lark-cli okr objective.alignments create --as user \
     --objective-id "目标A的ID" \
     --data '{"apply_to_draft":true,"to_entity_id":"目标B的ID","to_entity_type":2}'
   ```

3. **验证对齐结果**
   ```bash
   lark-cli okr objective.alignments list --params '{"prefer_draft":true}' --as user \
     --objective-id "目标A的ID" \
     --align-type "aligning"
   ```

4. **报告草稿结果**，说明尚未发布。只有已有授权覆盖当前整个 Objective 草稿时才发布；用户指定发布态且范围明确时直接写 false，保留已有草稿，不先建草稿再自动发布。

5. **（如需且已授权）删除草稿对齐**
   ```bash
   lark-cli okr alignments delete --params '{"apply_to_draft":true}' --as user \
     --alignment-id "从步骤1返回的alignment_id"
   ```

## 参考

- [lark-okr](../SKILL.md) -- 所有 OKR 命令
- [lark-shared](../../lark-shared/SKILL.md) -- 认证和全局参数
