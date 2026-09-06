# 记忆与安全 / Memory and Safety

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

聚焦输入防护、RAG 和标准化操作手册的安全与记忆技能集合。

当前分类共 **7** 个技能。

## 推荐先看

- [cast](./cast/) - 用户画像生成、角色注册、生命周期和跨智能体同步。
- [input-guard](./input-guard/) - 用于输入安全检查、提示注入防护和高风险请求拦截。
- [omen](./omen/) - 预演失败模式，识别计划风险并给出优先级。
- [rag-architect](./rag-architect/) - 用于以评测为先设计和诊断生产级 RAG，包括权限、混合检索、重排、引用和监控。

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `cast` | 用户画像生成、角色注册、生命周期和跨智能体同步。 | [目录](./cast/) | [SKILL.md](./cast/SKILL.md) |
| `honcho` | 用于管理 Agent 记忆、运行状态、协作上下文和安全边界。 | [目录](./honcho/) | [SKILL.md](./honcho/SKILL.md) |
| `input-guard` | 用于输入安全检查、提示注入防护和高风险请求拦截。 | [目录](./input-guard/) | [SKILL.md](./input-guard/SKILL.md) |
| `omen` | 预演失败模式，识别计划风险并给出优先级。 | [目录](./omen/) | [SKILL.md](./omen/SKILL.md) |
| `rag-architect` | 用于以评测为先设计和诊断生产级 RAG，包括权限、混合检索、重排、引用和监控。 | [目录](./rag-architect/) | [SKILL.md](./rag-architect/SKILL.md) |
| `runbook-generator` | 用于基于仓库和平台证据编写安全、可演练、可验证的生产运维 Runbook。 | [目录](./runbook-generator/) | [SKILL.md](./runbook-generator/SKILL.md) |
| `warden` | 按价值、用户自主性和体验韧性评估产品质量。 | [目录](./warden/) | [SKILL.md](./warden/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
