---
name: notion-spec-to-implementation
description: 'Turn Notion specs into implementation plans, tasks, and progress tracking; use when implementing PRDs/feature specs and creating Notion plans + tasks from them.'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["implementation", "notion", "spec"]'
created_at: "2026-03-04"
updated_at: "2026-03-20"
quality: 3
complexity: "intermediate"
metadata:
short-description: 'Turn Notion specs into implementation plans, tasks, and progress tracking'
---

# Spec to Implementation

Convert a Notion spec into linked implementation plans, tasks, and ongoing status updates.

## When to Use

Use this skill when the user wants to:

- turn a Notion PRD or feature spec into an execution plan
- create linked implementation tasks from a spec
- keep spec, plan, and tasks synchronized over time
- move from product definition to engineering delivery inside Notion

Use a different skill when:

- the main task is documenting research or summaries → use `notion-research-documentation`
- the main task is capturing a meeting or decision artifact → use `notion-knowledge-capture`

## Quick start
1) Locate the spec with `Notion:notion-search`, then fetch it with `Notion:notion-fetch`.
2) Parse requirements and ambiguities using `reference/spec-parsing.md`.
3) Create a plan page with `Notion:notion-create-pages` (pick a template: quick vs. full).
4) Find the task database, confirm schema, then create tasks with `Notion:notion-create-pages`.
5) Link spec ↔ plan ↔ tasks; keep status current with `Notion:notion-update-page`.

## Usage

Typical artifact chain:

```text
spec page
-> implementation plan page
-> task database entries
-> recurring status updates
```

Default output should include:

- requirements summary
- assumptions and open questions
- phases or milestones
- concrete tasks with acceptance criteria
- relations between spec, plan, and task records

## Workflow

### 0) If any MCP call fails because Notion MCP is not connected, pause and set it up:
1. Add the Notion MCP:
   - `codex mcp add notion --url https://mcp.notion.com/mcp`
2. Enable remote MCP client:
   - Set `[features].rmcp_client = true` in `config.toml` **or** run `codex --enable rmcp_client`
3. Log in with OAuth:
   - `codex mcp login notion`

After successful login, the user will have to restart codex. You should finish your answer and tell them so when they try again they can continue with Step 1.

### 1) Locate and read the spec
- Search first (`Notion:notion-search`); if multiple hits, ask the user which to use.
- Fetch the page (`Notion:notion-fetch`) and scan for requirements, acceptance criteria, constraints, and priorities. See `reference/spec-parsing.md` for extraction patterns.
- Capture gaps/assumptions in a clarifications block before proceeding.
- Separate hard requirements from inferred implementation detail; do not silently invent acceptance criteria.

### 2) Choose plan depth
- Simple change → use `reference/quick-implementation-plan.md`.
- Multi-phase feature/migration → use `reference/standard-implementation-plan.md`.
- Create the plan via `Notion:notion-create-pages`, include: overview, linked spec, requirements summary, phases, dependencies/risks, and success criteria. Link back to the spec.

### 3) Create tasks
- Find the task database (`Notion:notion-search` → `Notion:notion-fetch` to confirm the data source and required properties). Patterns in `reference/task-creation.md`.
- Size tasks to 1–2 days. Use `reference/task-creation-template.md` for content (context, objective, acceptance criteria, dependencies, resources).
- Set properties: title/action verb, status, priority, relations to spec + plan, due date/story points/assignee if provided.
- Create pages with `Notion:notion-create-pages` using the database’s `data_source_id`.
- Prefer fewer, clearer tasks over copying the entire spec into every ticket.

### 4) Link artifacts
- Plan links to spec; tasks link to both plan and spec.
- Optionally update the spec with a short “Implementation” section pointing to the plan and tasks using `Notion:notion-update-page`.
- If the spec already has implementation links, update them instead of duplicating sections.

### 5) Track progress
- Use the cadence in `reference/progress-tracking.md`.
- Post updates with `reference/progress-update-template.md`; close phases with `reference/milestone-summary-template.md`.
- Keep checklists and status fields in plan/tasks in sync; note blockers and decisions.

## Common Pitfalls

- turning ambiguous ideas into tasks without calling out assumptions
- creating tasks before confirming the correct task database schema
- making tasks too large to track
- not linking spec, plan, and tasks, which breaks traceability
- updating task status but forgetting to update the plan summary

## Done Criteria

Spec-to-implementation is complete when:

- the source spec is identified and linked
- a plan page exists with phases and risks
- task records exist in the correct data source
- tasks have usable acceptance criteria
- spec, plan, and tasks link to each other
- progress can be reported without rereading the whole spec

## References and examples
- `reference/` — parsing patterns, plan/task templates, progress cadence (e.g., `spec-parsing.md`, `standard-implementation-plan.md`, `task-creation.md`, `progress-tracking.md`).
- `examples/` — end-to-end walkthroughs (e.g., `ui-component.md`, `api-feature.md`, `database-migration.md`).
