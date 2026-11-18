---
name: lark-okr
description: '飞书 OKR：管理目标与关键结果。查看和编辑 OKR 周期、目标、关键结果、对齐关系、量化指标和进展记录。当用户需要查看或创建 OKR、管理目标和关键结果、查看对齐关系时使用。不负责：待办任务管理（lark-task）、日程/会议安排（lark-calendar）、绩效评估'
zh_description: "飞书 OKR：管理目标与关键结果。"
version: "1.0.9"
author: larksuite
source: "github:larksuite/cli"
source_url: "https://github.com/larksuite/cli/tree/7beffb086d7fa3c5b843d8affa7c089f49cfc65e/skills/lark-okr"
license: MIT
tags: [feishu, lark, lark-cli, okr, planning]
created_at: "2026-05-19"
updated_at: "2026-11-17"
quality: 4
complexity: intermediate
metadata:
  requires:
    bins: [ "lark-cli" ]
  cliHelp: "lark-cli okr --help"
---

# okr (v2)

**CRITICAL — 开始前 MUST 先用 Read 工具读取 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md)，其中包含认证、权限处理**

**身份**：OKR 操作默认使用 `--as user`（查看当前用户/上下级的 OKR 时）。也支持 `--as bot` 查看他人 OKR（需相应权限，仅在用户明确要求时使用，不自动切换身份读取草稿）。

## 快速决策

| 用户需求                     | 操作路径                                                                                                                | 参考文档                                                                                                                                                                                                             |
|------------------------------|-------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 查看自己/他人的 OKR          | 获取用户 ID -> `+cycle-list` -> `+cycle-detail` -> 按需查指标/进展记录                                                  | [`cycle-list`](references/lark-okr-cycle-list.md), [`cycle-detail`](references/lark-okr-cycle-detail.md), [`indicators`](references/lark-okr-indicators.md), [`progress-list`](references/lark-okr-progress-list.md) |
| 为自己写一组 OKR             | 优先用 `+batch-create` 创建 Objective/KR 骨架                                                                           | [`batch-create`](references/lark-okr-batch-create.md), [`contentblock`](references/lark-okr-contentblock.md)                                                                                                         |
| 只新增一条 O 或单条 KR       | 用 `+create`                                                                                                            | [`create`](references/lark-okr-create.md)                                                                                                                                                                            |
| 编辑内容/备注/截止时间       | 用 `+patch`                                                                                                             | [`patch`](references/lark-okr-patch.md)                                                                                                                                                                              |
| 修改 OKR 分数                | 只有用户明确说“分数”“评分”“打分”“score”时才用 `+patch --score --apply-to-draft=false`；分数不是进度/完成度，草稿不支持 score                                     | [`patch`](references/lark-okr-patch.md)                                                                                                                                                                              |
| 调整顺序或权重               | 用 `+reorder` / `+weight`                                                                                               | [`reorder`](references/lark-okr-reorder.md), [`weight`](references/lark-okr-weight.md)                                                                                                                               |
| 更新数字进度/完成度          | 百分比或不带单位数字用 `+indicator-update`；需要改单位/目标值时查指标后用 `indicators patch`                            | [`indicator-update`](references/lark-okr-indicator-update.md), [`indicators`](references/lark-okr-indicators.md)                                                                                                     |
| 写文字进展                   | 用 `+progress-create`；如果文本和数字都有，百分比或默认单位可使用 `--progress-percent` 统一改，非百分比单位更新量化指标 | [`progress-create`](references/lark-okr-progress-create.md), [`progress-list`](references/lark-okr-progress-list.md), [`progress-update`](references/lark-okr-progress-update.md)                                    |
| 对齐目标                     | 直接按对齐关系工作流处理                                                                                                | [`alignments`](references/lark-okr-alignments.md)                                                                                                                                                                    |
| 发布或撤销 Objective 草稿 | `+publish-draft` / `+drop-draft --yes`；需覆盖整个聚合的具体授权 | [草稿工作流](references/lark-okr-drafts.md) |
| 查询/创建/修改/解决 OKR 评论 | 获取周期下全部评论聚合用 `+comment-detail`，查询单个 O/KR/进展或仅查询周期全局评论用 `+comment-list`；                | [`comment`](references/lark-okr-comment-list.md), [`comment-create`](references/lark-okr-comment-create.md), [`comment-solve-reopen`](references/lark-okr-comment-solve-reopen.md)                                   |

## 显式选择草稿或发布态

修改已有 O/KR 前，用 `+cycle-detail --prefer-draft=true` 读取并查看所属 Objective 的 `is_draft`。仅在当前身份有草稿可见性且可编辑时，`false` 才能用于判断无草稿；user 只能读取本人草稿，查看他人时返回发布态。不要将不可见或空列表当作没有草稿。

- 支持草稿的写入显式选择 `--apply-to-draft=true|false`；`true` 在尚无草稿时会自动创建所属 Objective 的草稿。未指定状态时优先保存草稿并说明尚未发布。
- 用户指定发布态且对象、字段和范围明确，或会话已有对应具体授权时，可直接使用 `false`，无需额外一轮确认。已有草稿须保留，说明其之后发布可能覆盖本次发布态修改；不擅自发布或撤销。
- 发布用 `+publish-draft`，放弃整份草稿用 `+drop-draft --yes`。两者覆盖 Objective、其全部 KR、O/KR 指标及发起的对齐；授权必须覆盖整份当前草稿，复用会话已有具体授权，不把编辑单条 KR 当作聚合发布/撤销授权。
- Objective 的位置和权重两态共用、立即生效，撤销草稿不回滚；KR 的位置和权重分态。`+reorder` 固定草稿优先且写 KR 草稿，不暴露状态 flag；发布态 KR 排序走原生接口。
- `score`、Objective `notes` 只在发布态更新，使用独立 `+patch --apply-to-draft=false` 请求；评论、文字进展、进展记录/图片和分类也操作发布态，不附加草稿参数。

完整语义、权限和发布/撤销边界见 [OKR 草稿工作流](references/lark-okr-drafts.md)。所有暴露状态选择的命令示例显式传值；shortcut 用顶层 flag，原生接口用 `--params` / `--data` JSON，不能混用。

分类只在用户明确要求分类，或创建 Objective 返回 `invalid parameters` 且怀疑租户强制开启分类时处理：用 `lark-cli okr categories list --params '{"owner_type":"user","page_size":100}' --as user` 查可用分类，选择语义合适且`enabled=true` 的分类 ID；分类可后续调整，不必停下等待用户确认。

获取当前用户用 `contact +get-user`；按姓名/邮箱查他人用 `contact +search-user`，拿到 `open_id` 后再查 OKR。

```bash
lark-cli contact +search-user --query "张三" --has-chatted --as user
```

最常用 OKR 命令示例：

```bash
# 查用户周期，再用周期 ID 查详情
lark-cli okr +cycle-list --user-id "ou_xxx" --as user
lark-cli okr +cycle-detail --cycle-id 7000000000000000001 --as user --prefer-draft=true

# 批量创建 Objective/KR
lark-cli okr +batch-create --apply-to-draft=true \
  --cycle-id 7000000000000000001 \
  --input '[{"text":"提升产品用户体验","krs":[{"text":"核心流程满意度达到 4.8 分"}]}]' \
  --as user

# 更新数字进度/完成度
lark-cli okr +indicator-update --apply-to-draft=true \
  --level key-result \
  --id 7000000000000000003 \
  --value 75 \
  --as user
```

分数和进度不要混用：用户说“进度”“完成度”“当前做到 75%”时，通常是在改量化指标或写进展记录，不是在改 `score`。只有明确要求修改 OKR 分数/评分/打分时，才使用 [`+patch --score --apply-to-draft=false`](references/lark-okr-patch.md)；`score` 取值是 0-1，最多一位小数；score 和 notes 不支持草稿，草稿读取中可能不返回。

进度判断规则：用户说“进度”“完成度”时，先判断是否是量化数字。数字进度通常对应量化指标；不可量化文本对应进展记录。需要修改指标单位时看 [`lark-okr-indicators.md`](references/lark-okr-indicators.md)

## Shortcuts（推荐优先使用）

Shortcut 是对常用操作的高级封装（`lark-cli okr +<verb> [flags]`）。有 Shortcut 的操作优先使用。

| Shortcut                                                         | 说明                                                                                                          |
|------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| [`+cycle-list`](references/lark-okr-cycle-list.md)               | 分页获取特定用户的 OKR 周期列表，可以用 `--time-range` 对当前页后置筛选                                       |
| [`+cycle-detail`](references/lark-okr-cycle-detail.md)           | 获取特定 OKR 中所有目标和关键结果的内容                                                                       |
| [`+create`](references/lark-okr-create.md)                       | 创建单个 Objective（可带备注），或向已有 Objective 新增 KR                                                    |
| [`+progress-list`](references/lark-okr-progress-list.md)         | 分页获取目标或关键结果的进展记录列表                                                                          |
| [`+progress-get`](references/lark-okr-progress-get.md)           | 根据 ID 获取单条 OKR 进展记录                                                                                 |
| [`+progress-create`](references/lark-okr-progress-create.md)     | 为目标或关键结果创建进展记录                                                                                  |
| [`+progress-update`](references/lark-okr-progress-update.md)     | 更新指定 ID 的进展记录内容                                                                                    |
| [`+progress-delete`](references/lark-okr-progress-delete.md)     | 删除指定 ID 的进展记录（不可恢复）                                                                            |
| [`+upload-image`](references/lark-okr-image-upload.md)           | 上传图片用于 OKR 进展记录的富文本内容                                                                         |
| [`+batch-create`](references/lark-okr-batch-create.md)           | 批量创建 Objective（可带备注）和 KR                                                                           |
| [`+reorder`](references/lark-okr-reorder.md)                     | 调整 Objective 或 KR 的顺位                                                                                   |
| [`+weight`](references/lark-okr-weight.md)                       | 调整 Objective 或 KR 的权重                                                                                   |
| [`+indicator-update`](references/lark-okr-indicator-update.md)   | 更新 Objective 或 KR 的当前进度指标。更复杂的量化指标操作见 [量化指标管理](references/lark-okr-indicators.md) |
| [`+patch`](references/lark-okr-patch.md)                         | 部分更新 Objective 或 KR（content、notes、score、deadline）                                                   |
| [`+publish-draft`](references/lark-okr-drafts.md) | 发布整个 Objective 草稿聚合 |
| [`+drop-draft`](references/lark-okr-drafts.md) | 放弃整个 Objective 草稿聚合，显式传 `--yes` |
| [`+comment-detail`](references/lark-okr-comment-detail.md)       | 获取周期下 Cycle/Objective/KeyResult/Progress 的全部评论                                                      |
| [`+comment-list`](references/lark-okr-comment-list.md)           | 分页获取单个 OKR 实体下的评论                                                                                 |
| [`+comment-get`](references/lark-okr-comment-get.md)             | 获取单条评论详情                                                                                              |
| [`+comment-create`](references/lark-okr-comment-create.md)       | 创建新评论或回复已有评论(仅支持 --as user)                                                                    |
| [`+comment-patch`](references/lark-okr-comment-patch.md)         | 修改评论内容(仅支持 --as user)                                                                                |
| [`+comment-delete`](references/lark-okr-comment-delete.md)       | 永久删除单条评论(仅支持 --as user)                                                                            |
| [`+comment-solve`](references/lark-okr-comment-solve-reopen.md)  | 解决评论或划词评论串(仅支持 --as user)                                                                        |
| [`+comment-reopen`](references/lark-okr-comment-solve-reopen.md) | 重新打开评论或划词评论串(仅支持 --as user)                                                                    |

### 创建场景选择

- **单条创建优先用 [`+create`](references/lark-okr-create.md)**：适合创建一个 Objective，或给已有 Objective 增加一个 KR。
- **批量创建用 [`+batch-create`](references/lark-okr-batch-create.md)**：适合一次创建多个 Objective，并可同时附带多个 KR。
- 如果你只需要修改已有 Objective / KR 的内容、备注、分数或截止时间，使用 [`+patch`](references/lark-okr-patch.md)。

## 格式说明

- [`OKR 业务实体`](references/lark-okr-entities.md) 获取 OKR 实体结构，定义和关系，帮助你更好的使用 OKR 功能
- [`ContentBlock 富文本格式`](references/lark-okr-contentblock.md) — Objective/KeyResult/Progress 中 Content/Note
  字段使用的富文本格式说明，以及简化的半纯文本（SemiPlainContent）格式的进一步说明。
- **强烈建议** 在操作 OKR 前，阅读[`OKR 业务实体`](references/lark-okr-entities.md)以了解基础概念

## API Resources

原生接口若暴露状态字段，读取用 `--params '{"prefer_draft":true}'`（草稿优先）或 `false`（仅发布态）；创建/更新用 `--data` 中的 `apply_to_draft`，删除用 `--params` 中的 `apply_to_draft`。不要把 shortcut 的 `--prefer-draft` / `--apply-to-draft` 顶层 flag 套到原生接口。无状态字段的接口不添加这些参数。

### alignments

- `delete` — 删除选定状态的对齐：`--params` 中显式传 `apply_to_draft`。
- `get` — 获取对齐：`--params` 中显式传 `prefer_draft`。

> [对齐工作流](references/lark-okr-alignments.md) 包含 list/create/delete 和发起方权限规则。

### categories / cycles

- `categories list` — 批量获取分类；分类操作发布态。
- `cycles list` — 批量获取用户周期。

### cycle.objectives

- `create` — 创建目标，`--data` 中显式传 `apply_to_draft`；优先用 [+create](references/lark-okr-create.md) 或 [+batch-create](references/lark-okr-batch-create.md)。
- `list` — 获取周期目标，`--params` 中显式传 `prefer_draft`；优先用 [+cycle-detail](references/lark-okr-cycle-detail.md)。

### indicators

- `patch` — 更新量化指标，`--data` 中显式传 `apply_to_draft`。

> [量化指标管理](references/lark-okr-indicators.md) 包含状态一致的查询和更新示例。

### key_results

- `delete` — 删除选定状态的 KR，`--params` 中显式传 `apply_to_draft`；两态互不干涉，对应状态中不存在时返回 `1001004: okr data not found`，不自动切换状态重试。
- `get` — 获取 KR，`--params` 中显式传 `prefer_draft`。
- `patch` — 更新 KR，`--data` 中显式传 `apply_to_draft`；优先用 [+patch](references/lark-okr-patch.md)。

### key_result.indicators / objective.indicators

- `list` — 获取 KR / Objective 指标，`--params` 中显式传 `prefer_draft`；见 [量化指标管理](references/lark-okr-indicators.md)。

### objectives

- `delete` — 同时删除 Objective 的草稿和发布态，也可删除仅有草稿的 O；不是撤销草稿的替代操作。
- `get` — 获取目标，`--params` 中显式传 `prefer_draft`。
- `key_results_position` — 更新该 Objective 下选定状态的全部 KR 顺序，`--data` 中显式传 `apply_to_draft`，携带该目标在对应状态的全部 KR ID；见 [排序](references/lark-okr-reorder.md)。
- `key_results_weight` — 更新该 Objective 下选定状态的全部 KR 权重，`--data` 中显式传 `apply_to_draft`，携带全部 KR 且权重和等于 1；见 [权重](references/lark-okr-weight.md)。
- `patch` — 更新目标，`--data` 中显式传 `apply_to_draft`；score/notes 只写发布态，见 [+patch](references/lark-okr-patch.md)。

### objective.alignments

- `create` — 创建对齐，`--data` 中显式传 `apply_to_draft`；不能对齐自己的目标，双方周期时间必须重叠，被对齐目标使用发布态。
- `list` — 获取对齐，`--params` 中显式传 `prefer_draft`；可混合返回草稿与发布态，见 [对齐工作流](references/lark-okr-alignments.md)。

### objective.key_results

- `create` — 创建 KR，`--data` 中显式传 `apply_to_draft`；优先用 [+create](references/lark-okr-create.md)。
- `list` — 获取 KR 列表，`--params` 中显式传 `prefer_draft`。

## 不在本 skill 范围

- 待办任务管理 → 使用 [`lark-task`](../lark-task/SKILL.md)
- 日程安排 → 使用 [`lark-calendar`](../lark-calendar/SKILL.md)
- 绩效评估 → 使用 [`lark-openapi-explorer`](../lark-openapi-explorer/SKILL.md) 查找原生接口

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

- Prefer the upstream workflow for Lark Okr; this section only adds local quality
  guardrails.
- Do not invent project facts when required files, vaults, services, or tools are
  unavailable.
- Stop and ask for clarification when the next action could overwrite user work,
  expose private data, or change production state.
- Treat skill selection as routing, not ceremony: invoke only the narrowest
  applicable workflow and keep user or repository instructions authoritative.
<!-- LOCAL-QUALITY-SUPPLEMENT:END -->
