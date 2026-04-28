# 项目管理与知识库集成 / Knowledge and PM Integrations

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

连接 Notion、Linear 和规格到实施流程的知识与项目管理技能集合。

当前分类共 **11** 个技能。

## 推荐先看

- [grove](./grove/) - 仓库结构、文档布局、测试脚本组织和迁移规划。
- [linear](./linear/) - Manage Linear issues, projects, and teams via the GraphQL API. Create, update, search, and organize issues. Uses API key auth (no OAuth needed). All operations via curl — no dependencies.
- [lore](./lore/) - 跨智能体知识沉淀、模式提炼和最佳实践传播。
- [notion-knowledge-capture](./notion-knowledge-capture/) - Capture conversations and decisions into structured Notion pages; use when turning chats/notes into wiki entries, how-tos, decisions, or FAQs with proper linking.

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `arxiv` | Search and retrieve academic papers from arXiv using their free REST API. No API key needed. Search by keyword, author, category, or ID. Combine with web_extract or the ocr-and-documents skill to read full paper content. | [目录](./arxiv/) | [SKILL.md](./arxiv/SKILL.md) |
| `grove` | 仓库结构、文档布局、测试脚本组织和迁移规划。 | [目录](./grove/) | [SKILL.md](./grove/SKILL.md) |
| `linear` | Manage Linear issues, projects, and teams via the GraphQL API. Create, update, search, and organize issues. Uses API key auth (no OAuth needed). All operations via curl — no dependencies. | [目录](./linear/) | [SKILL.md](./linear/SKILL.md) |
| `llm-wiki` | Karpathy''s LLM Wiki — build and maintain a persistent, interlinked markdown knowledge base. Ingest sources, query compiled knowledge, and lint for consistency. | [目录](./llm-wiki/) | [SKILL.md](./llm-wiki/SKILL.md) |
| `lore` | 跨智能体知识沉淀、模式提炼和最佳实践传播。 | [目录](./lore/) | [SKILL.md](./lore/SKILL.md) |
| `notion-knowledge-capture` | Capture conversations and decisions into structured Notion pages; use when turning chats/notes into wiki entries, how-tos, decisions, or FAQs with proper linking. | [目录](./notion-knowledge-capture/) | [SKILL.md](./notion-knowledge-capture/SKILL.md) |
| `notion-meeting-intelligence` | Prepare meeting materials with Notion context and Codex research; use when gathering context, drafting agendas/pre-reads, and tailoring materials to attendees. | [目录](./notion-meeting-intelligence/) | [SKILL.md](./notion-meeting-intelligence/SKILL.md) |
| `notion-research-documentation` | Research across Notion and synthesize into structured documentation; use when gathering info from multiple Notion sources to produce briefs, comparisons, or reports with citations. | [目录](./notion-research-documentation/) | [SKILL.md](./notion-research-documentation/SKILL.md) |
| `notion-spec-to-implementation` | Turn Notion specs into implementation plans, tasks, and progress tracking; use when implementing PRDs/feature specs and creating Notion plans + tasks from them. | [目录](./notion-spec-to-implementation/) | [SKILL.md](./notion-spec-to-implementation/SKILL.md) |
| `obsidian` | Read, search, and create notes in the Obsidian vault. | [目录](./obsidian/) | [SKILL.md](./obsidian/SKILL.md) |
| `tome` | Converts repository changes into detailed learning documents. Use when turning diffs into teaching materials, recording design decisions, or creating onboarding materials for new members. | [目录](./tome/) | [SKILL.md](./tome/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
