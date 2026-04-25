# 2026-04-25 技能精选与升级报告

## 本轮目标

- 全网筛选高质量 `SKILL.md` 技能源。
- 每个现有分类先补充 3 个高价值技能，避免一次性扩张过猛。
- 对已有外部技能执行上游同步，发现可升级内容时优先升级，不轻易删除仍有独立价值的老技能。
- 所有新增外源技能必须进入来源追踪，后续可继续同步升级。

## 主要来源

### 已采用

- `simota/agent-skills`
  - 近期活跃。
  - 覆盖开发、工作流、运维、增长、安全、设计、多模态等多个场景。
  - 单个技能内容较厚，多数超过 250 行。
  - 目录结构清晰，适合建立精确上游路径同步。

### 已参考但本轮未直接导入

- `kodustech/awesome-agent-skills`
  - 更偏索引和聚合，适合作为后续发现入口。
- `VoltAgent/awesome-claude-skills`
  - 覆盖面很广，适合下一轮按垂直领域继续筛选。
- 技能市场与社区索引站点
  - 用于发现趋势和交叉验证，不直接作为代码来源。

## 新增策略

本轮采用“每类 3 个”的保守扩充策略：

- 先补足每个分类的能力缺口。
- 优先选择和现有技能互补的能力。
- 对明显重叠的技能不做替换，除非新技能在内容深度、维护状态、可执行性上显著更强。
- 每个新增技能都写入 `docs/sources/simota-agent-skills-2026-04.skills.json`，包含上游仓库、路径、同步提交和本地落点。

## 新增技能概览

| 分类 | 新增技能 |
|---|---|
| `developer-engineering` | `builder`, `gateway`, `schema` |
| `ai-workflow` | `nexus`, `sherpa`, `rally` |
| `ai-agent-platform` | `oracle`, `arena`, `sigil` |
| `engineering-workflow-automation` | `guardian`, `harvest`, `latch` |
| `devops-sre` | `beacon`, `triage`, `gear` |
| `finance-investing` | `ledger`, `helm`, `levy` |
| `growth-operations-xiaohongshu` | `growth`, `compete`, `pulse` |
| `office-white-collar` | `morph`, `stage`, `prism` |
| `knowledge-and-pm-integrations` | `lore`, `tome`, `grove` |
| `operations-general` | `crest`, `hearth`, `dawn` |
| `product-design` | `voice`, `trace`, `researcher` |
| `security-and-reliability` | `breach`, `cloak`, `comply` |
| `multimodal-media` | `sketch`, `clay`, `tone` |
| `deployment-platforms` | `scaffold`, `pipe`, `shard` |
| `openclaw-memory-and-safety` | `cast`, `omen`, `warden` |
| `task-understanding-decomposition` | `lens`, `scout`, `ripple` |

## 旧技能升级与替换判断

### 已升级

- `landing-page-generator`
  - 来源：`github:alirezarezvani/claude-skills`
  - 处理：同步上游更新。
- `llm-wiki`
  - 来源：`github:NousResearch/hermes-agent`
  - 处理：同步上游更新，内容从 465 行扩展到 542 行。
- `addyosmani/agent-skills` 系列技能
  - 处理：重新同步到上游最新提交，并更新来源映射。

### 暂不替换

- `codebase-onboarding` 与新增 `lens`
  - 判断：一个偏新成员上手文档，一个偏问题调查和数据流追踪，互补大于重叠。
- `systematic-debugging` 与新增 `scout`
  - 判断：一个是通用调试方法论，一个是缺陷调查报告型技能，可并存。
- `agent-workflow-designer` 与新增 `nexus`
  - 判断：一个偏工作流设计，一个偏执行链路编排，可形成上下游关系。
- `security-threat-model` 与新增 `breach`
  - 判断：一个偏威胁建模，一个偏红队场景和对抗演练，不替换。
- `observability-designer` 与新增 `beacon`
  - 判断：存在一定重叠，但 `beacon` 覆盖服务目标、告警和容量规划更完整，先并存观察。

## 后续建议

- 下一轮可从 `VoltAgent/awesome-claude-skills` 和 `kodustech/awesome-agent-skills` 中继续筛选每类第 4-5 个技能。
- 当某个分类技能数量明显过多时，再做合并或替换，而不是本轮直接删除。
- 对功能重叠技能建议增加使用频次、质量评分和最近同步时间三项指标后再做淘汰。
