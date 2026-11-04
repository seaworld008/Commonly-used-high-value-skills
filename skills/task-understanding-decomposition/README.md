# 任务理解与拆解 / Task Understanding

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

聚焦 brainstorming、research、计划编写、skills 检索与任务拆解。

当前分类共 **5** 个技能。

## 推荐先看

- [reflect-learn](./reflect-learn/) - 分析用户纠正和任务结果，提出可复用的改进建议。
- [grill-me](./grill-me/) - 对方案、设计和关键决策进行追问，检验假设、取舍与遗漏的需求。
- [lens](./lens/) - 需要理解陌生代码库时使用：确认功能是否存在、追踪执行与数据流、梳理模块边界。
- [ripple](./ripple/) - 实施高风险变更前使用：评估依赖链、破坏性影响和一致性风险，并给出是否推进的建议。

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `grill-me` | 对方案、设计和关键决策进行追问，检验假设、取舍与遗漏的需求。 | [目录](./grill-me/) | [SKILL.md](./grill-me/SKILL.md) |
| `lens` | 需要理解陌生代码库时使用：确认功能是否存在、追踪执行与数据流、梳理模块边界。 | [目录](./lens/) | [SKILL.md](./lens/SKILL.md) |
| `reflect-learn` | 分析用户纠正和任务结果，提出可复用的改进建议。 | [目录](./reflect-learn/) | [SKILL.md](./reflect-learn/SKILL.md) |
| `ripple` | 实施高风险变更前使用：评估依赖链、破坏性影响和一致性风险，并给出是否推进的建议。 | [目录](./ripple/) | [SKILL.md](./ripple/SKILL.md) |
| `scout` | 调查缺陷时使用：复现问题、逐一验证假设、定位根因并评估影响，在修复前完成。 | [目录](./scout/) | [SKILL.md](./scout/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
