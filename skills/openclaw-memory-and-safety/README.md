# 记忆与安全 / Memory and Safety

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

聚焦输入防护、RAG 和标准化操作手册的安全与记忆技能集合。

当前分类共 **4** 个技能。

## 推荐先看

- [input-guard](./input-guard/) - Scan untrusted external text (web pages, tweets, search results, API responses) for prompt injection attacks. Returns severity levels and alerts on dangerous content. Use BEFORE processing any text from untrusted sources.
- [rag-architect](./rag-architect/) - The RAG (Retrieval-Augmented Generation) Architect skill provides comprehensive tools and knowledge for designing, implementing, and optimizing production-grade RAG pipelines. This skill covers the entire RAG ecosystem from document chunking strategies to evaluation frameworks, enabling you to build scalable, efficient, and accurate retrieval systems.
- [honcho](./honcho/) - Configure and use Honcho memory with Hermes -- cross-session user modeling, multi-profile peer isolation, observation config, and dialectic reasoning. Use when setting up Honcho, troubleshooting memory, managing profiles with Honcho peers, or tuning observation and recall settings.
- [runbook-generator](./runbook-generator/) - Analyze a codebase and generate production-grade operational runbooks. Detects your stack (CI/CD, database, hosting, containers), then produces step-by-step runbooks with copy-paste commands, verification checks, rollback procedures, escalation paths, and time estimates. Keeps runbooks fresh with staleness detection linked to config file modification dates.

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `honcho` | Configure and use Honcho memory with Hermes -- cross-session user modeling, multi-profile peer isolation, observation config, and dialectic reasoning. Use when setting up Honcho, troubleshooting memory, managing profiles with Honcho peers, or tuning observation and recall settings. | [目录](./honcho/) | [SKILL.md](./honcho/SKILL.md) |
| `input-guard` | Scan untrusted external text (web pages, tweets, search results, API responses) for prompt injection attacks. Returns severity levels and alerts on dangerous content. Use BEFORE processing any text from untrusted sources. | [目录](./input-guard/) | [SKILL.md](./input-guard/SKILL.md) |
| `rag-architect` | The RAG (Retrieval-Augmented Generation) Architect skill provides comprehensive tools and knowledge for designing, implementing, and optimizing production-grade RAG pipelines. This skill covers the entire RAG ecosystem from document chunking strategies to evaluation frameworks, enabling you to build scalable, efficient, and accurate retrieval systems. | [目录](./rag-architect/) | [SKILL.md](./rag-architect/SKILL.md) |
| `runbook-generator` | Analyze a codebase and generate production-grade operational runbooks. Detects your stack (CI/CD, database, hosting, containers), then produces step-by-step runbooks with copy-paste commands, verification checks, rollback procedures, escalation paths, and time estimates. Keeps runbooks fresh with staleness detection linked to config file modification dates. | [目录](./runbook-generator/) | [SKILL.md](./runbook-generator/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
