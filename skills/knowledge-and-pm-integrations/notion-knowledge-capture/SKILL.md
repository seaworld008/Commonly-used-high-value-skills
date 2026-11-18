---
name: notion-knowledge-capture
description: 'Use when turning a conversation, decision, or rough notes into a structured Notion page, or updating an existing wiki page instead of creating a duplicate.'
zh_description: "需要把对话、决策或笔记整理成结构化 Notion 页面，或更新已有知识页时使用。"
version: "1.0.2"
author: "Notion Labs, Inc.; local curators"
source: "https://github.com/openai/skills"
source_url: "https://github.com/openai/skills/blob/49f948faa9258a0c61caceaf225e179651397431/skills/.curated/notion-knowledge-capture/SKILL.md"
license: "MIT"
tags: ["capture", "knowledge", "notion"]
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 3
complexity: "intermediate"
metadata:
short-description: Capture conversations into structured Notion pages
---

# Knowledge Capture

Convert conversations and notes into structured, linkable Notion pages for easy reuse.

## When to Use

Use this skill when the user wants to:

- turn a chat, meeting note, or rough draft into a durable Notion page
- capture a decision, FAQ, how-to, or learning note in a reusable format
- update an existing wiki page instead of creating duplicate documentation
- connect new knowledge to existing hub pages, databases, or related records

Use a different skill when:

- the task is specifically meeting prep before the meeting starts → use `notion-meeting-intelligence`
- the main job is research synthesis across many Notion pages → use `notion-research-documentation`
- the main job is breaking a PRD/spec into implementation artifacts → use `notion-spec-to-implementation`

## Quick start
1) Clarify what to capture (decision, how-to, FAQ, learning, documentation) and target audience.
2) Identify the right database/template in `reference/` (team wiki, how-to, FAQ, decision log, learning, documentation).
3) Pull any prior context from Notion with `Notion:notion-search` → `Notion:notion-fetch` (existing pages to update/link).
4) Draft the page with `Notion:notion-create-pages` using the database’s schema; include summary, context, source links, and tags/owners.
5) Link from hub pages and related records; update status/owners with `Notion:notion-update-page` as the source evolves.

## Usage

Typical usage pattern:

```text
search existing page/database
-> fetch target schema or page content
-> decide create vs update
-> write structured content
-> link related records
-> verify final page destination
```

Default output shape:

- short summary at the top
- structured sections instead of raw transcript dump
- source links or discussion references
- explicit owners/tags if the destination database supports them

## Workflow

### 0) Discover the available Notion connection
Discover and use the host's available Notion connector; map the example tool names below to its supported operations. If unavailable, explain the missing capability and continue independent local drafting from supplied material. Do not claim to have fetched or published pages without a working connection.

Installation, configuration, and OAuth setup are separate user-requested tasks. For such a task, check the installed CLI help and host instructions before changing configuration; do not assume a specific feature flag or restart requirement.

Ask about source or destination only when ambiguity materially changes the result and cannot be resolved from the request or workspace context.

### 1) Define the capture
- Ask purpose, audience, freshness, and whether this is new or an update.
- Determine content type: decision, how-to, FAQ, concept/wiki entry, learning/note, documentation page.

### 2) Locate destination
- Pick the correct database using `reference/*-database.md` guides; confirm required properties (title, tags, owner, status, date, relations).
- Use the requested or context-established destination; ask only when unresolved database ambiguity materially changes where content is written.
- If the destination is a database URL, fetch it first and identify the correct `data_source_id` before creating pages.
- Prefer updating an existing page when the new content is incremental and the original page is still the canonical source.

### 3) Extract and structure
- Extract facts, decisions, actions, and rationale from the conversation.
- For decisions, record alternatives, rationale, and outcomes.
- For how-tos/docs, capture steps, pre-reqs, links to assets/code, and edge cases.
- For FAQs, phrase as Q&A with concise answers and links to deeper docs.
- Remove conversational filler; keep only information future readers need.
- If the source text is messy, build the clean page first, then preserve raw notes only in a small appendix or source section.

### 4) Create/update in Notion
- Use `Notion:notion-create-pages` with the correct `data_source_id`; set properties (title, tags, owner, status, dates, relations).
- Use templates in `reference/` to structure content (section headers, checklists).
- If updating an existing page, fetch then edit via `Notion:notion-update-page`.
- When updating content, anchor edits on exact old strings from `notion-fetch`; do not guess snippets.
- If the page lives outside a database, only the `title` property is allowed.

### 5) Link and surface
- Add relations/backlinks to hub pages, related specs/docs, and teams.
- Add a short summary/changelog for future readers.
- If follow-up tasks exist, create tasks in the relevant database and link them.

## Common Pitfalls

- Creating a new page when the existing page should have been updated
- Using a database URL where a `data_source_id` is required
- Writing long unstructured transcript dumps instead of reusable knowledge
- Forgetting to add relations/backlinks, which makes the page hard to rediscover
- Updating a page without fetching current content first

## Done Criteria

A capture is complete when:

- the page is in the right destination
- the title and key properties are filled
- the content is structured for reuse
- source context is preserved
- related pages or tasks are linked
- a future reader can understand the artifact without the original conversation

## References and examples
- `reference/` — database schemas and templates (e.g., `team-wiki-database.md`, `how-to-guide-database.md`, `faq-database.md`, `decision-log-database.md`, `documentation-database.md`, `learning-database.md`, `database-best-practices.md`).
- `examples/` — capture patterns in practice (e.g., `decision-capture.md`, `how-to-guide.md`, `conversation-to-faq.md`).
