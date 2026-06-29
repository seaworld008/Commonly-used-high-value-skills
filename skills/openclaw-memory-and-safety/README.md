# 记忆与安全 / Memory and Safety

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

聚焦输入防护、RAG 和标准化操作手册的安全与记忆技能集合。

当前分类共 **7** 个技能。

## 推荐先看

- [cast](./cast/) - 用于cast，支持记忆管理、安全防护和运行治理。
- [input-guard](./input-guard/) - 用于输入安全检查、提示注入防护和高风险请求拦截。
- [omen](./omen/) - 用于omen，支持记忆管理、安全防护和运行治理。
- [rag-architect](./rag-architect/) - 用于设计 RAG 架构、检索策略、索引和评估流程。

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `cast` | 用于cast，支持记忆管理、安全防护和运行治理。 | [目录](./cast/) | [SKILL.md](./cast/SKILL.md) |
| `honcho` | 用于管理 Agent 记忆、运行状态、协作上下文和安全边界。 | [目录](./honcho/) | [SKILL.md](./honcho/SKILL.md) |
| `input-guard` | 用于输入安全检查、提示注入防护和高风险请求拦截。 | [目录](./input-guard/) | [SKILL.md](./input-guard/SKILL.md) |
| `omen` | 用于omen，支持记忆管理、安全防护和运行治理。 | [目录](./omen/) | [SKILL.md](./omen/SKILL.md) |
| `rag-architect` | 用于设计 RAG 架构、检索策略、索引和评估流程。 | [目录](./rag-architect/) | [SKILL.md](./rag-architect/SKILL.md) |
| `runbook-generator` | 用于runbook、生成，支持记忆管理、安全防护和运行治理。 | [目录](./runbook-generator/) | [SKILL.md](./runbook-generator/SKILL.md) |
| `warden` | 用于warden，支持记忆管理、安全防护和运行治理。 | [目录](./warden/) | [SKILL.md](./warden/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
