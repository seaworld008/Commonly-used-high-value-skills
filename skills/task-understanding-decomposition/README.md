# 任务理解与拆解 / Task Understanding

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

聚焦 brainstorming、research、计划编写、skills 检索与任务拆解。

当前分类共 **5** 个技能。

## 推荐先看

- [reflect-learn](./reflect-learn/) - Self-improvement through conversation analysis. Extracts learnings from corrections and success patterns, proposes updates to agent files or creates new skills. Philosophy: "Correct once, never again." Use when: (1) User explicitly corrects behavior ("never do X", "always Y"), (2) Session ending or context compaction, (3) User requests /reflect, (4) Successful pattern worth preserving.
- [lens](./lens/) - 代码库理解、功能发现、数据流追踪和上下文调查。
- [ripple](./ripple/) - 变更前影响分析，评估依赖链和一致性风险。
- [scout](./scout/) - 缺陷调查、复现步骤、根因分析和影响评估。

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `lens` | 代码库理解、功能发现、数据流追踪和上下文调查。 | [目录](./lens/) | [SKILL.md](./lens/SKILL.md) |
| `reflect-learn` | Self-improvement through conversation analysis. Extracts learnings from corrections and success patterns, proposes updates to agent files or creates new skills. Philosophy: "Correct once, never again." Use when: (1) User explicitly corrects behavior ("never do X", "always Y"), (2) Session ending or context compaction, (3) User requests /reflect, (4) Successful pattern worth preserving. | [目录](./reflect-learn/) | [SKILL.md](./reflect-learn/SKILL.md) |
| `ripple` | 变更前影响分析，评估依赖链和一致性风险。 | [目录](./ripple/) | [SKILL.md](./ripple/SKILL.md) |
| `scout` | 缺陷调查、复现步骤、根因分析和影响评估。 | [目录](./scout/) | [SKILL.md](./scout/SKILL.md) |
| `tavily-search` | 提供实时联网检索能力，帮助 Agent 获取最新资讯、数据与来源证据。 | [目录](./tavily-search/) | [SKILL.md](./tavily-search/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
