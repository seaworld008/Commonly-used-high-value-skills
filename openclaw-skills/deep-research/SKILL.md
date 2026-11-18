---
name: deep-research
description: 'Produce source-backed research reports, literature reviews, or technical and market briefs when evidence tracking and a defined report format matter.'
zh_description: "用于执行深度研究、资料收集、来源核验和综合分析。"
version: "1.0.2"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: ["deep", "planning", "research", "workflow"]
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 5
complexity: "intermediate"
---

# Deep Research

Create high-fidelity research reports with strict format control, evidence mapping, and multi-pass synthesis.

## Quick Start

1. Clarify the report spec and format contract
2. Build a research plan and query set
3. Collect evidence with available research/search and original-page reading tools
4. Triage sources and build an evidence table
5. Draft from the evidence table; add independent comparisons only for concrete gaps
6. Merge relevant verified findings, enforce format compliance, verify citations
7. Present draft for human review and iterate

## Core Workflow

Copy this checklist and track progress:

```
Deep Research Progress:
- [ ] Step 1: Intake and format contract
- [ ] Step 2: Research plan and query set
- [ ] Step 3: Evidence collection (available retrieval operations)
- [ ] Step 4: Source triage and evidence table
- [ ] Step 5: Outline and section map
- [ ] Step 6: Evidence-based draft; optional independent comparison
- [ ] Step 7: Evidence-filtered merge and format compliance
- [ ] Step 8: Evidence and citation verification
- [ ] Step 9: Present draft for human review and iterate
```

### Step 1: Intake and Format Contract

Establish the report requirements before any research:

- Confirm audience, purpose, scope, time range, and geography
- Lock output format: Markdown, DOCX, slides, or user-provided template
- Capture required sections and exact formatting rules
- Confirm citation style (footnotes, inline, numbered, APA, etc.)
- Confirm length targets per section
- Ask for any existing style guide or sample report

Create a concise report spec file:

```
Report Spec:
- Audience:
- Purpose:
- Scope:
- Time Range:
- Geography:
- Required Sections:
- Section Formatting Rules:
- Citation Style:
- Output Format:
- Length Targets:
- Tone:
- Must-Include Sources:
- Must-Exclude Topics:
```

If a user provides a template or an example report, treat it as a hard constraint and mirror the structure.

### Step 2: Research Plan and Query Set

Define the research strategy before calling tools:

- Break the main question into 3-7 subquestions
- Define key entities, keywords, and synonyms
- Identify primary sources vs secondary sources
- Define disqualifiers (outdated, low quality, opinion-only)
- Assemble a query set per section

Use [references/research_plan_checklist.md](references/research_plan_checklist.md) for guidance.

### Step 3: Evidence Collection (Available Research Tools)

Discover the host's research, search, and page-reading operations and bind their actual schemas. Use available tools to collect evidence and verify original sources; a tool named `deepresearch` is not required.

- Run additional targeted searches where coverage is uncertain
- Vary query phrasing to reduce blind spots
- Preserve raw tool output in files for traceability

**File structure (recommended):**
```
<output_dir>/research/<topic-name>/
  deepresearch_pass1.md
  deepresearch_pass2.md
  deepresearch_pass3.md
```

Without an automated research tool, use search plus original-page verification to build the same evidence table. Only when all retrieval is unavailable, use user-provided sources and state the coverage limit. Save raw outputs only within authorized output or temporary locations.

### Step 4: Source Triage and Evidence Table

Normalize and score sources before drafting:

- De-duplicate sources across passes
- Score sources using [references/source_quality_rubric.md](references/source_quality_rubric.md)
- Build an evidence table mapping claims to sources

Evidence table minimum columns:

- Source ID
- Title
- Publisher
- Date
- URL or reference
- Quality tier (A/B/C)
- Notes

### Step 5: Outline and Section Map

Create an outline that enforces the format contract:

- Use the template in [references/research_report_template.md](references/research_report_template.md)
- Produce a section map with required elements per section
- Confirm ordering and headings match the report spec

### Step 6: Evidence-Based Drafting

Produce one draft from the evidence table, respecting coverage, conflicts, and the user's length limit. Add targeted research or independent drafts only for material blind spots, disputed conclusions, or an explicitly requested comparison.

#### Optional Strategy: Independent Drafts

When delegation is available and authorized, bind the host's actual delegation schema. Each independent reviewer or drafter should:

- Load the report spec, outline, and evidence table
- Review or draft the assigned scope; use complete drafts only when whole-report comparison is useful
- Enforce formatting rules and citation style

**Conceptual pattern (not executable host calls):**
```
available_delegate(verified evidence, assigned scope, output contract) -> optional draft
```

**Write drafts to files, not conversation context:**
```
<output_dir>/intermediate/<topic-name>/version1.md
<output_dir>/intermediate/<topic-name>/version2.md
<output_dir>/intermediate/<topic-name>/version3.md
```

### Step 7: Evidence-Filtered Merge and Format Compliance

If multiple drafts exist, merge findings by relevance and evidence:

- Keep verified unique findings that serve the research question
- Consolidate duplicates at the detail level allowed by the user's scope and length
- Exclude unsupported or out-of-scope material; record reasons for significant exclusions
- Ensure every claim in the merged draft has a cited source
- Enforce the exact section order, headings, and formatting
- Re-run formatting rules from [references/formatting_rules.md](references/formatting_rules.md)

### Step 8: Evidence and Citation Verification

Verify traceability:

- Every numeric claim has at least one source
- Every recommendation references supporting evidence
- No orphan claims without citations
- Dates and time ranges are consistent
- Conflicts are explicitly called out with both sources

Use [references/completeness_review_checklist.md](references/completeness_review_checklist.md).

### Step 9: Present Draft for Human Review and Iterate

Present the draft as a reviewable version:

- Emphasize that format compliance and factual accuracy need human review
- Accept edits to format, structure, and scope
- If the user provides another AI output, cross-compare claims against sources and merge relevant verified findings

## Output Requirements

- Match the requested language and tone
- Preserve technical terms in English
- Respect the report spec and formatting rules
- Include a references section or bibliography

## Reference Files

| File | When to Load |
| --- | --- |
| [research_report_template.md](references/research_report_template.md) | Build outline and draft structure |
| [formatting_rules.md](references/formatting_rules.md) | Enforce section formatting and citation rules |
| [source_quality_rubric.md](references/source_quality_rubric.md) | Score and triage sources |
| [research_plan_checklist.md](references/research_plan_checklist.md) | Build research plan and query set |
| [completeness_review_checklist.md](references/completeness_review_checklist.md) | Review for coverage, citations, and compliance |

## Anti-Patterns

- Drafting without checking evidence coverage and material conflicts
- Generating multiple full drafts without a concrete uncertainty or comparison need
- Ignoring the format contract or user template
- Claims without citations or evidence table mapping
- Mixing conflicting dates without calling out discrepancies
- Copying external AI output without verification
- Deleting intermediate drafts or raw research outputs
