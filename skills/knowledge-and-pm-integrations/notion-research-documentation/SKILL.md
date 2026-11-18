---
name: notion-research-documentation
description: 'Use when synthesizing several Notion pages into a cited brief, comparison, or recommendation report that links back to its source pages.'
zh_description: "需要汇总多个 Notion 页面并生成带引用的研究简报或对比报告时使用。"
version: "1.0.2"
author: "Notion Labs, Inc.; local curators"
source: "https://github.com/openai/skills"
source_url: "https://github.com/openai/skills/blob/49f948faa9258a0c61caceaf225e179651397431/skills/.curated/notion-research-documentation/SKILL.md"
license: "MIT"
tags: ["documentation", "notion", "research"]
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 3
complexity: "intermediate"
metadata:
short-description: Research Notion content and produce briefs/reports
---

# Research & Documentation

Pull relevant Notion pages, synthesize findings, and publish clear briefs or reports (with citations and links to sources).

## When to Use

Use this skill when the user wants to:

- collect information from multiple Notion pages and turn it into a brief
- compare options, projects, teams, or decisions using existing workspace context
- produce a report, summary, or recommendation document grounded in Notion sources
- preserve citations and source links while synthesizing content

Use a different skill when:

- the main output is a meeting agenda → use `notion-meeting-intelligence`
- the main job is storing a conversation or decision as a reusable page → use `notion-knowledge-capture`
- the main job is converting a spec into implementation artifacts → use `notion-spec-to-implementation`

## Quick start
1) Find sources with `Notion:notion-search` using targeted queries; confirm scope with the user.
2) Fetch pages via `Notion:notion-fetch`; note key sections and capture citations (`reference/citations.md`).
3) Choose output format (brief, summary, comparison, comprehensive report) using `reference/format-selection-guide.md`.
4) Draft in Notion with `Notion:notion-create-pages` using the matching template (quick, summary, comparison, comprehensive).
5) Link sources and add a references/citations section; update as new info arrives with `Notion:notion-update-page`.

## Usage

Default output sections:

- scope and question being answered
- key findings
- supporting evidence
- contradictions or gaps
- recommendation or next steps
- references

Minimal synthesis flow:

```text
search pages
-> fetch source content
-> extract evidence
-> synthesize findings
-> create report page
```

## Workflow

### 0) Discover the available Notion connection
Discover and use the host's available Notion connector; map the example tool names below to its supported operations. If unavailable, explain the missing capability and continue independent local drafting from supplied material. Do not claim to have fetched or published pages without a working connection.

Installation, configuration, and OAuth setup are separate user-requested tasks. For such a task, check the installed CLI help and host instructions before changing configuration; do not assume a specific feature flag or restart requirement.

Ask about source or destination only when ambiguity materially changes the result and cannot be resolved from the request or workspace context.

### 1) Gather sources
- Search first (`Notion:notion-search`); refine queries and select relevant sources from context. Ask only if unresolved source ambiguity materially changes the report.
- Fetch relevant pages (`Notion:notion-fetch`), skim for facts, metrics, claims, constraints, and dates.
- Track each source URL/ID for later citation; prefer direct quotes for critical facts.
- For database-backed sources, fetch the data source details first if the schema matters to the report.

### 2) Select the format
- Quick readout → quick brief.
- Single-topic dive → research summary.
- Option tradeoffs → comparison.
- Deep dive / exec-ready → comprehensive report.
- See `reference/format-selection-guide.md` for when to pick each.

### 3) Synthesize
- Outline before writing; group findings by themes/questions.
- Note evidence with source IDs; flag gaps or contradictions.
- Keep user goal in view (decision, summary, plan, recommendation).
- Distinguish clearly between sourced facts, inferred conclusions, and recommendations.

### 4) Create the doc
- Pick the matching template in `reference/` (brief, summary, comparison, comprehensive) and adapt it.
- Create the page with `Notion:notion-create-pages`; include title, summary, key findings, supporting evidence, and recommendations/next steps when relevant.
- Add citations inline and a references section; link back to source pages.

### 5) Finalize & handoff
- Add highlights, risks, and open questions.
- If the user needs follow-ups, create tasks or a checklist in the page; link any task database entries if applicable.
- Share a short changelog or status using `Notion:notion-update-page` when updating.

## Common Pitfalls

- treating search results as final evidence without fetching the full pages
- merging conflicting claims without flagging the contradiction
- writing a recommendation without separating it from the evidence
- losing page URLs and source IDs, which weakens traceability
- publishing a comparison without a clear evaluation frame

## Done Criteria

Research documentation is complete when:

- the scope is explicit
- the source set is clear and linked
- findings are grouped logically
- contradictions and unknowns are called out
- recommendations, if any, are grounded in cited material
- a reader can trace each key point back to source pages

## Example Commands

```text
Notion:notion-search -> locate candidate source pages
Notion:notion-fetch -> read the selected pages
Notion:notion-create-pages -> publish the brief or report
Notion:notion-update-page -> revise with new evidence or clarifications
```

## References and examples
- `reference/` — search tactics, format selection, templates, and citation rules (e.g., `advanced-search.md`, `format-selection-guide.md`, `research-summary-template.md`, `comparison-template.md`, `citations.md`).
- `examples/` — end-to-end walkthroughs (e.g., `competitor-analysis.md`, `technical-investigation.md`, `market-research.md`, `trip-planning.md`).
