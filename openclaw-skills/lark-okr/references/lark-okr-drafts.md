# OKR 草稿工作流

> 来源：[larksuite/cli](https://github.com/larksuite/cli/tree/3d82c85419ad7560ad017db7a3972a596b5fbeb1/skills/lark-okr)，固定提交 `3d82c85419ad7560ad017db7a3972a596b5fbeb1`，MIT 许可。本文基于该版本草稿指南策展，授权措辞和字段边界由本仓库于 2026-11-17 调整，不代表上游原文。
>
> **前置条件：** 先阅读 [`lark-shared/SKILL.md`](../../lark-shared/SKILL.md) 了解认证、全局参数和高风险操作规则；具体授权复用当前会话，不要求机械地增加确认轮次。

Objective、KR、对齐关系和量化指标都可能返回 `is_draft`。`true` 表示本次读取返回草稿态内容，`false` 表示返回发布态内容。草稿以整个 Objective 聚合为单位发布或撤销，包含其 KR、O/KR 的指标和该 Objective **发起的**对齐。

**`--apply-to-draft=true` 会强制使用草稿，不要求事先已有草稿。** 编辑 O、KR、指标、对齐或 KR 权重时，若所属 Objective 尚无草稿，会先为整个 Objective 创建草稿再写入；新建 O 则直接创建未发布的草稿 O。`--prefer-draft=true` 只选择读取视图，不会创建草稿。

## 操作决策

1. 修改已有 O/KR 前，用 `+cycle-detail --prefer-draft=true` 获取当前内容，查看所属 Objective 的 `is_draft`。仅在当前身份有相应草稿可见性且可编辑该 OKR 时，才能据 `false` 判断无草稿；读取失败、列表为空或他人发布态结果不能证明没有草稿。新建 O 先核对周期和所有者。
2. 用户指定发布态且对象、字段和范围明确，或会话已有直接完成发布态变更的具体授权时，显式传 `--apply-to-draft=false`，无需用户额外声明“不要二次确认”。
3. 未指定状态时，支持草稿的变更优先用 `--apply-to-draft=true`，展示草稿结果并说明尚未发布。若用户意图确实影响状态选择，才询问缺失信息；不因通用规则重复索取已有授权。
4. 发布必须有覆盖当前 Objective 整份草稿的具体授权。已有明确的“发布这份草稿”授权即可核对内容和范围后执行，不强制增加一轮“看过后再确认”；仅授权编辑草稿不包含发布。
5. 直接修改发布态时，如 Objective 已有草稿，保留草稿，不自动发布或撤销，并说明之后发布草稿可能覆盖本次发布态修改。无法读取草稿时，不把不可见当作不存在，也不擅自改用发布态。

```bash
# 草稿优先读取；有可见草稿时返回草稿内容
lark-cli okr +cycle-detail \
  --cycle-id 7000000000000000001 \
  --prefer-draft=true \
  --as user

# 编辑草稿
lark-cli okr +patch \
  --level objective \
  --target-id 7000000000000000002 \
  --content '{"text":"更新后的目标"}' \
  --apply-to-draft=true \
  --as user

# 已有覆盖当前整份草稿的发布授权，核对后发布整个 Objective 草稿
lark-cli okr +publish-draft \
  --objective-id 7000000000000000002 \
  --as user

# 用户指定发布态且范围明确时，直接修改发布态
lark-cli okr +patch \
  --level objective \
  --target-id 7000000000000000002 \
  --content '{"text":"直接更新发布态"}' \
  --apply-to-draft=false \
  --as user
```

## 发布与撤销

发布前读取当前整份草稿，核对 O、全部 KR、指标和发起的对齐是否都在已有发布授权内；有未授权的已有变更时不能顺带发布，需澄清范围。

```bash
lark-cli okr +publish-draft \
  --objective-id 7000000000000000002 \
  --as user
```

撤销整个 Objective 草稿是 `high-risk-write` 操作，不支持只撤销单个 KR。已有明确放弃整份草稿的授权时显式传 `--yes`；只授权删除某个 KR 不等于授权撤销整份草稿。

```bash
lark-cli okr +drop-draft \
  --objective-id 7000000000000000002 \
  --yes \
  --as user
```

已有发布态 O 进入草稿时会复制当时的聚合快照。之后发布态的修改不会自动同步进草稿，Objective 的位置和权重除外。发布时草稿支持的内容覆盖对应发布态；撤销时丢弃草稿、保留当前发布态，不回滚发布态修改或共用位置/权重。仅有草稿的 O 在撤销后不留下发布态 O；发布后才生成发布态目标。

`objectives delete` 会同时删除 Objective 的草稿和发布态，也可删除仅草稿的 O；它不是撤销草稿的替代命令。KR 删除按选定状态操作，在该状态不存在时会返回 `1001004: okr data not found`，不得自动切换状态重试。

## 参数适用范围

- `--prefer-draft`：shortcut 读取选择。`+cycle-detail` 默认 `true`，命令中仍应显式传值；有可见草稿时优先取草稿，否则取对应发布态，`false` 只读发布态。
- `--apply-to-draft`：shortcut 写入选择。`+create`、`+batch-create`、`+patch`、`+indicator-update` 和 KR `+weight` 默认 `true`，命令中仍应显式传值。
- 原生接口不要照抄 shortcut 的顶层 flag：读取在 `--params` JSON 中传 `prefer_draft`；有草稿选择的创建/更新在 `--data` 中传 `apply_to_draft`；有草稿选择的删除在 `--params` 中传 `apply_to_draft`。对齐接口默认 `false`，也应显式选择，见 [对齐工作流](lark-okr-alignments.md)。
- `+reorder` 不暴露草稿参数：固定按草稿优先视图读取，并对 KR 草稿排序；需要调整发布态 KR 顺序时使用 [原生排序接口](lark-okr-reorder.md)，不能给 shortcut 虚构 flag。
- Objective 位置和权重两态共用，修改立即影响两态；`+weight --level objective` 的状态参数不隔离存储，撤销草稿不能撤回这些修改。KR 位置和权重分别保存。
- `score` 和 Objective `notes` 不支持草稿，更新时使用独立的 `+patch --apply-to-draft=false` 请求，不混入草稿正文/截止时间。草稿读取不支持的字段可能不返回；只有草稿的 O 不应为写备注或评分而被擅自发布。
- 评论、文字进展、进展记录、进展图片和分类操作发布态，不使用草稿参数。进展记录附带的数字进度也属于发布态操作；需要草稿指标时使用 `+indicator-update` 或原生指标接口。

## 权限边界

草稿读取只对 OKR 所有者本人的用户身份（`--as user`）和具备相应应用数据权限的 bot 身份（`--as bot`）生效。以 user 身份查看他人 OKR 总是发布态；bot 仅在用户明确要求且具有对应权限时使用，不为读取不可见草稿而自动切换身份。

对齐草稿的可见性按每条关系的**发起方所有者**判断；同一对齐列表可能混合草稿与发布态。user 可读自己发起的草稿，他人发布态对齐仍受阅览权限过滤；bot 在查询目标属于应用数据权限范围时可读草稿。不要从空列表判断无草稿。

## 参考

- [`okr +cycle-detail`](lark-okr-cycle-detail.md)
- [`okr +create`](lark-okr-create.md)
- [`okr +batch-create`](lark-okr-batch-create.md)
- [`okr +patch`](lark-okr-patch.md)
- [`okr +indicator-update`](lark-okr-indicator-update.md)
- [`量化指标原生接口`](lark-okr-indicators.md)
- [`okr +weight`](lark-okr-weight.md)
- [`OKR 实体定义`](lark-okr-entities.md)
