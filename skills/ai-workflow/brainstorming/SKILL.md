---
name: brainstorming
description: 'Use before creative product or engineering work when the user wants to design a feature, component, workflow, behavior change, or other solution whose goals, constraints, and tradeoffs need exploration before implementation.'
zh_description: "用于在实现前澄清创意型产品或工程需求，探索目标、约束、方案与取舍。"
version: "1.0.2"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["brainstorming", "planning", "workflow"]'
created_at: "2026-03-04"
updated_at: "2026-09-06"
quality: 3
complexity: "intermediate"
---

# Brainstorming Ideas Into Designs

## When to Use

Use this skill before:

- building a new feature
- changing behavior in a meaningful way
- creating a new component or workflow
- turning a rough idea into an implementation-ready design

## Usage

Use a short design discussion when consequential choices remain open.
If the user has already supplied a workable design and asked for implementation,
record the essential assumptions and proceed with the authorized work.
For small, reversible changes, a concise inline design is enough.

```text
inspect current context
-> identify decisions that affect the outcome
-> resolve consequential gaps
-> state the chosen approach and acceptance checks
-> implement when authorized
```

## Decision Boundaries

Ask for input when the answer changes the product goal, user experience,
public contract, data retention, or an irreversible action.
Use existing project patterns for routine implementation choices.
Continue independent research and preparation while a necessary answer is pending.
An explicit brainstorming-only request remains a discussion task.

## Practical Design Checklist

1. Read the relevant code, requirements, and previous decisions.
2. State the problem, intended user, and observable success criteria.
3. Identify only the uncertainties that materially affect the solution.
4. Compare alternatives when there is a real tradeoff; do not manufacture options.
5. Choose a small, coherent implementation and explain its main tradeoff.
6. Record an enduring design document only when future work needs it.
7. Continue into implementation if the user requested execution.

## Example

```text
Request: Add CSV export to the existing table.
Known: Current filters and columns define the exported data.
Decision: Reuse the existing authorized data-fetch path.
Check: Export filtered rows, escape CSV cells, preserve column order.
Clarify only if export scope or access requirements remain ambiguous.
```

## Handoff

Use a written plan when dependencies or scope need one.
Do not require a second plan or approval merely to invoke another skill.
Keep original user constraints and acceptance checks with the handoff.

## The Process

**Understanding the idea:**
- Check out the current project state first (files, docs, recent commits)
- Ask questions one at a time to refine the idea
- Prefer multiple choice questions when possible, but open-ended is fine too
- Ask concise questions only for unresolved material choices; group closely related gaps when useful
- Focus on understanding: purpose, constraints, success criteria

**Exploring approaches:**
- Propose 2-3 different approaches with trade-offs
- Present options conversationally with your recommendation and reasoning
- Lead with your recommended option and explain why

**Presenting the design:**
- Once you believe you understand what you're building, present the design
- Scale each section to its complexity: a few sentences if straightforward, up to 200-300 words if nuanced
- Invite corrections without blocking already authorized implementation
- Cover: architecture, components, data flow, error handling, testing
- Be ready to go back and clarify if something doesn't make sense

## After the Design

**Documentation:**
- For substantial designs, save the durable decisions to `docs/plans/YYYY-MM-DD-<topic>-design.md`
- Use elements-of-style:writing-clearly-and-concisely skill if available
- Include the design with the task changes when a commit is requested

**Implementation:**
- Continue the requested implementation once consequential decisions are resolved
- Use writing-plans when the task needs an enduring plan; avoid forced skill chains

## Key Principles

- **One question at a time** - Don't overwhelm with multiple questions
- **Multiple choice preferred** - Easier to answer than open-ended when possible
- **YAGNI** - Remove unnecessary features from designs
- **Explore alternatives** - Compare alternatives when they expose a real tradeoff
- **Incremental validation** - Confirm unresolved consequential choices; reuse existing authorization
- **Be flexible** - Go back and clarify when something doesn't make sense
