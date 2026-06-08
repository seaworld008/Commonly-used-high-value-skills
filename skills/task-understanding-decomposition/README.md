# 任务理解与拆解 / Task Understanding

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

聚焦 brainstorming、research、计划编写、skills 检索与任务拆解。

当前分类共 **5** 个技能。

## 推荐先看

- [reflect-learn](./reflect-learn/) - Self-improvement through conversation analysis. Extracts learnings from corrections and success patterns, proposes updates to agent files or creates new skills. Philosophy: "Correct once, never again." Use when: (1) User explicitly corrects behavior ("never do X", "always Y"), (2) Session ending or context compaction, (3) User requests /reflect, (4) Successful pattern worth preserving.
- [lens](./lens/) - Comprehending and investigating codebases. Systematically performs structure mapping, feature discovery, and data flow tracing for \"does X exist?\", \"how does Y work?\", or \"what is this module''s responsibility?\". Does not write code.
- [ripple](./ripple/) - Analyzing pre-change impact by evaluating risk across vertical (dependency chains, affected files) and horizontal (pattern consistency, naming) dimensions. Does not write code. Use when estimating blast radius before a refactor, audit, or migration — or when a PR''s risk surface is unclear.
- [scout](./scout/) - Investigating bugs via root cause analysis (RCA), reproduction steps, and impact assessment. Investigation-only — identifies why bugs occur and where to fix them, no code. Use when a bug needs RCA, reproduction must be established before fix, or impact radius needs assessment.

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `lens` | Comprehending and investigating codebases. Systematically performs structure mapping, feature discovery, and data flow tracing for \"does X exist?\", \"how does Y work?\", or \"what is this module''s responsibility?\". Does not write code. | [目录](./lens/) | [SKILL.md](./lens/SKILL.md) |
| `reflect-learn` | Self-improvement through conversation analysis. Extracts learnings from corrections and success patterns, proposes updates to agent files or creates new skills. Philosophy: "Correct once, never again." Use when: (1) User explicitly corrects behavior ("never do X", "always Y"), (2) Session ending or context compaction, (3) User requests /reflect, (4) Successful pattern worth preserving. | [目录](./reflect-learn/) | [SKILL.md](./reflect-learn/SKILL.md) |
| `ripple` | Analyzing pre-change impact by evaluating risk across vertical (dependency chains, affected files) and horizontal (pattern consistency, naming) dimensions. Does not write code. Use when estimating blast radius before a refactor, audit, or migration — or when a PR''s risk surface is unclear. | [目录](./ripple/) | [SKILL.md](./ripple/SKILL.md) |
| `scout` | Investigating bugs via root cause analysis (RCA), reproduction steps, and impact assessment. Investigation-only — identifies why bugs occur and where to fix them, no code. Use when a bug needs RCA, reproduction must be established before fix, or impact radius needs assessment. | [目录](./scout/) | [SKILL.md](./scout/SKILL.md) |
| `tavily-search` | 提供实时联网检索能力，帮助 Agent 获取最新资讯、数据与来源证据。 | [目录](./tavily-search/) | [SKILL.md](./tavily-search/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
