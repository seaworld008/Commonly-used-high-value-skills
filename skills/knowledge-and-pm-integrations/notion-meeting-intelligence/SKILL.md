---
name: notion-meeting-intelligence
description: 'Prepare meeting materials with Notion context and Codex research; use when gathering context, drafting agendas/pre-reads, and tailoring materials to attendees.'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["intelligence", "meeting", "notion"]'
created_at: "2026-03-04"
updated_at: "2026-03-20"
quality: 3
complexity: "intermediate"
metadata: 
short-description: Prep meetings with Notion context and tailored agendas
---

# Meeting Intelligence

Prep meetings by pulling Notion context, tailoring agendas/pre-reads, and enriching with Codex research.

## When to Use

Use this skill when the user needs to:

- prepare an agenda before a meeting
- gather previous context from Notion for attendees
- draft a pre-read, briefing, or decision memo for a meeting
- consolidate open questions, blockers, and decision points into one page

Use a different skill when:

- the meeting already happened and you need to capture outcomes into knowledge pages → use `notion-knowledge-capture`
- the primary task is deep research documentation instead of meeting prep → use `notion-research-documentation`

## Quick start
1) Confirm meeting goal, attendees, date/time, and decisions needed.
2) Gather context: search with `Notion:notion-search`, then fetch with `Notion:notion-fetch` (prior notes, specs, OKRs, decisions).
3) Pick the right template via `reference/template-selection-guide.md` (status, decision, planning, retro, 1:1, brainstorming).
4) Draft agenda/pre-read in Notion with `Notion:notion-create-pages`, embedding source links and owner/timeboxes.
5) Enrich with Codex research (industry insights, benchmarks, risks) and update the page with `Notion:notion-update-page` as plans change.

## Usage

Typical output should include:

- objective and desired decisions
- attendee-aware agenda with timeboxes
- linked source pages
- explicit prep asks
- risks, open questions, and owners

Minimal create flow:

```text
search relevant meeting context
-> fetch prior notes/specs
-> choose template
-> create or update the prep page
-> link follow-up tasks
```

## Workflow

### 0) If any MCP call fails because Notion MCP is not connected, pause and set it up:
1. Add the Notion MCP:
   - `codex mcp add notion --url https://mcp.notion.com/mcp`
2. Enable remote MCP client:
   - Set `[features].rmcp_client = true` in `config.toml` **or** run `codex --enable rmcp_client`
3. Log in with OAuth:
   - `codex mcp login notion`

After successful login, the user will have to restart codex. You should finish your answer and tell them so when they try again they can continue with Step 1.

### 1) Gather inputs
- Ask for objective, desired outcomes/decisions, attendees, duration, date/time, and prior materials.
- Search Notion for relevant docs, past notes, specs, and action items (`Notion:notion-search`), then fetch key pages (`Notion:notion-fetch`).
- Capture blockers/risks and open questions up front.
- If there are many possible source pages, prioritize the most recent meeting notes, current specs, and pages linked to active projects.

### 2) Choose format
- Status/update → status template.
- Decision/approval → decision template.
- Planning (sprint/project) → planning template.
- Retro/feedback → retrospective template.
- 1:1 → one-on-one template.
- Ideation → brainstorming template.
- Use `reference/template-selection-guide.md` to confirm.

### 3) Build the agenda/pre-read
- Start from the chosen template in `reference/` and adapt sections (context, goals, agenda, owner/time per item, decisions, risks, prep asks).
- Include links to pulled Notion pages and any required pre-reading.
- Assign owners for each agenda item; call out timeboxes and expected outputs.
- Tailor depth to the audience: exec review should be short and decision-heavy; working sessions can include more context and task detail.

### 4) Enrich with research
- Add concise Codex research where helpful: market/industry facts, benchmarks, risks, best practices.
- Keep claims cited with source links; separate fact from opinion.
- Avoid stuffing the page with broad research that will not change meeting decisions.

### 5) Finalize and share
- Add next steps and owners for follow-ups.
- If tasks arise, create/link tasks in the relevant Notion database.
- Update the page via `Notion:notion-update-page` when details change; keep a brief changelog if multiple edits.

## Common Pitfalls

- agendas with no explicit decision points
- too many context links and not enough synthesis
- not tailoring the material to attendees
- missing owner/timebox fields, which weakens execution
- mixing speculative research with confirmed internal context

## Done Criteria

Meeting prep is complete when:

- the page states the objective clearly
- attendees and meeting date are captured if relevant
- each agenda item has an owner or facilitator
- source context is linked
- prep asks and expected decisions are explicit
- follow-up tasks can be created from the page without extra interpretation

## Example Commands

```text
Notion:notion-search -> find prior notes and specs
Notion:notion-fetch -> read the most relevant pages
Notion:notion-create-pages -> create the agenda or pre-read
Notion:notion-update-page -> refine as the meeting plan changes
```

## References and examples
- `reference/` — template picker and meeting templates (e.g., `template-selection-guide.md`, `status-update-template.md`, `decision-meeting-template.md`, `sprint-planning-template.md`, `one-on-one-template.md`, `retrospective-template.md`, `brainstorming-template.md`).
- `examples/` — end-to-end meeting preps (e.g., `executive-review.md`, `project-decision.md`, `sprint-planning.md`, `customer-meeting.md`).
