---
name: spec-driven-development
description: 'Specify new features or substantial behavior changes when goals, boundaries, and acceptance criteria need agreement before implementation.'
zh_description: "把需求转成明确的功能边界、契约和验收标准。"
version: "1.0.6"
author: addyosmani
source: "github:addyosmani/agent-skills"
source_url: "https://github.com/addyosmani/agent-skills/blob/main/skills/spec-driven-development/SKILL.md"
license: MIT
tags: ["agent", "ai", "engineering", "spec-driven-development", "workflow"]
created_at: "2026-07-27"
updated_at: "2026-11-17"
quality: 5
complexity: advanced
upstream_slug: spec-driven-development
---

# Spec-Driven Development

## Overview

Use a specification to settle goals, boundaries and acceptance criteria that materially affect implementation. Reuse an existing specification or plan when it already settles them.

## When to Use

- A new feature has unresolved behavior, interfaces or acceptance criteria.
- A proposed architectural change needs agreement about scope or tradeoffs.
- With sufficient requirements and authorization, continue at the first unfinished phase.

## Workflow

Use the phases needed for the task. Phase 0 applies when one request bundles independently testable capabilities. Reuse prior decisions and seek review when an unresolved choice affects scope or acceptance.

```
SPECIFY ──→ PLAN ──→ TASKS ──→ IMPLEMENT
```

### Phase 0: Scope Check

Most requests describe one capability. If this one does, skip this phase and go straight to Specify — Phase 0 exists for the exception, not the rule, and it puts no hierarchy on single-capability features.

**Detection.** Decompose before specifying when a single requirement bundles several independently testable capabilities:

- The requirement names distinct capabilities with their own consumers or data (e.g. identity, billing, notifications, reporting)
- Acceptance criteria cluster into groups that could ship and be verified separately
- One capability could be cut or replaced without rewriting the others' requirements

**Propose a capability map before writing any spec.** Small and reviewable — a module table plus a build order, not a project plan:

```markdown
# Capability Map: [Initiative Name]

| Module id | Responsibility | Depends on |
|---|---|---|
| identity | Accounts, sessions, SSO | — |
| billing | Plans, invoices, payments | identity |
| notifications | Email and webhook fan-out | identity |
| reporting | Usage dashboards | billing, notifications |

Build order: identity → billing, notifications → reporting
```

- **Stable module ids.** Kebab-case, chosen once, never renamed mid-initiative. Specs, plans, and downstream commands select work by these ids instead of guessing which spec is active.
- **Dependency direction, no cycles.** Arrows point one way. If two modules each need the other, they are one module.
- **Interfaces live at the boundary.** The map records that `billing` depends on `identity`; the contract between them belongs in the provider module's spec (see `api-and-interface-design` for designing it).

Review unresolved module boundaries, dependency direction and build order with the user. Reuse an agreed capability map.

**Then recurse per module.** Run Specify → Plan → Tasks → Implement for each module in dependency order. Each module gets its own spec, scoped to that module's objective, boundaries, and success criteria. Save the approved map at the project root and each module's spec alongside it, named by module id (`SPEC-identity.md`, `SPEC-billing.md`) — the map, not filename guessing, is the index of what exists.

### Phase 1: Specify

Start from the stated objective, project evidence and agreed requirements. Clarify remaining decisions that change what will be delivered.

**Surface assumptions immediately.** Before writing any spec content, list what you're assuming:

```
ASSUMPTIONS I'M MAKING:
1. This is a web application (not native mobile)
2. Authentication uses session-based cookies (not JWT)
3. The database is PostgreSQL (based on existing Prisma schema)
4. We're targeting modern browsers only (no IE11)
→ Correct me now or I'll proceed with these.
```

Don't silently fill in ambiguous requirements. The spec's entire purpose is to surface misunderstandings *before* code gets written — assumptions are the most dangerous form of misunderstanding.

**Write a spec document covering these six core areas:**

1. **Objective** — What are we building and why? Who is the user? What does success look like?

2. **Commands** — Full executable commands with flags, not just tool names.
   ```
   Build: npm run build
   Test: npm test -- --coverage
   Lint: npm run lint -- --fix
   Dev: npm run dev
   ```

3. **Project Structure** — Where source code lives, where tests go, where docs belong.
   ```
   src/           → Application source code
   src/components → React components
   src/lib        → Shared utilities
   tests/         → Unit and integration tests
   e2e/           → End-to-end tests
   docs/          → Documentation
   ```

4. **Code Style** — One real code snippet showing your style beats three paragraphs describing it. Include naming conventions, formatting rules, and examples of good output.

5. **Testing Strategy** — What framework, where tests live, coverage expectations, which test levels for which concerns.

6. **Boundaries** — Three-tier system:
   - **Always do:** Run tests before commits, follow naming conventions, validate inputs
   - **Ask first:** Database schema changes, adding dependencies, changing CI config
   - **Never do:** Commit secrets, edit vendor directories, remove failing tests without approval

**Spec template:**

```markdown
# Spec: [Project/Feature Name] — V[N]

## Objective
[What we're building and why. User stories or acceptance criteria.]

## Tech Stack
[Framework, language, key dependencies with versions]

## Commands
[Build, test, lint, dev — full commands]

## Project Structure
[Directory layout with descriptions]

## Code Style
[Example snippet + key conventions]

## Testing Strategy
[Framework, test locations, coverage requirements, test levels]

## Boundaries
- Always: [...]
- Ask first: [...]
- Never: [...]

## Success Criteria
[How we'll know this is done — specific, testable conditions]

## Open Questions
[Anything unresolved that needs human input]
```

**Reframe instructions as success criteria.** When receiving vague requirements, translate them into concrete conditions:

```
REQUIREMENT: "Make the dashboard faster"

REFRAMED SUCCESS CRITERIA:
- Dashboard LCP < 2.5s on 4G connection
- Initial data load completes in < 500ms
- No layout shift during load (CLS < 0.1)
→ Are these the right targets?
```

This lets you loop, retry, and problem-solve toward a clear goal rather than guessing what "faster" means.

### Phase 2: Plan

With the validated spec, generate a technical implementation plan:

1. Identify the major components and their dependencies
2. Determine the implementation order (what must be built first)
3. Note risks and mitigation strategies
4. Identify what can be built in parallel vs. what must be sequential
5. Define verification checkpoints between phases

> Follow `planning-and-task-breakdown` for the dependency-graph mapping and vertical-slicing mechanics behind these steps; it is the canonical source. The bullets above are a lightweight summary; if they ever diverge, `planning-and-task-breakdown` takes precedence.
>
> **Handoff:** Reuse the existing plan and tracker at their project- or user-selected locations. If a separate plan is requested and no location is specified, `tasks/plan.md` is an example. `/build` is an optional host command. Check its configured inputs before using it.

The plan should be reviewable: the human should be able to read it and say "yes, that's the right approach" or "no, change X."

### Phase 3: Tasks

Break the plan into discrete, implementable tasks:

- Each task should be completable in a single focused session
- Each task has explicit acceptance criteria
- Each task includes a verification step (test, build, manual check)
- Tasks are ordered by dependency, not by perceived importance
- No task should require changing more than ~5 files

> Follow `planning-and-task-breakdown` for the full task-sizing and dependency-ordering mechanics; it is the canonical source. The template below is a lightweight inline form; if they ever diverge, `planning-and-task-breakdown` takes precedence.

**Task template:**
```markdown
- [ ] Task: [Description]
  - Acceptance: [What must be true when done]
  - Verify: [How to confirm — test command, build, manual check]
  - Files: [Which files will be touched]
```

### Phase 4: Implement

Follow the plan's dependency order. Use `incremental-implementation`, `test-driven-development` and `context-engineering` where their methods apply. Load the spec sections and files needed for the current task.

## Keeping the Spec Alive

### External Specification Tools

This workflow is format-agnostic. If a project already uses OpenSpec or
another specification system, keep that system's artifact format and storage
conventions instead of creating a duplicate `SPEC.md`. This skill owns
clarification, content and resolution of open decisions. The external tool defines how the
approved specification is represented.

The spec is a living document, not a one-time artifact:

- **Update when decisions change** — If you discover the data model needs to change, update the spec first, then implement.
- **Update when scope changes** — Features added or cut should be reflected in the spec.
- **Version the spec** — Include it alongside code when the requested delivery includes a commit.
- **Reference the spec in PRs** — Link back to the spec section that each PR implements.

## Spec Evolution

Give each spec an explicit version and capture deferred ideas under Out of Scope. Keep new ideas out of the active implementation unless the user changes its scope.
For a change to a shipped feature, write a small delta beside the original spec: objective, current behavior, new behavior, acceptance criteria, and changed boundaries. Link the existing spec and inherit unchanged constraints.
Use the repository's actual planning commands; host-specific commands are not portable requirements. Resolve routine choices from evidence and use authorization already present in the conversation.
After delivery, update the original spec to describe the shipped system and mark the delta implemented. Preserve the reasons for earlier decisions.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "This is simple" | Check whether the request already provides testable acceptance criteria. |
| "I'll write the spec after I code it" | That's documentation, not specification. The spec's value is in forcing clarity *before* code. |
| "The spec will slow us down" | A 15-minute spec prevents hours of rework. Waterfall in 15 minutes beats debugging in 15 hours. |
| "Requirements will change anyway" | That's why the spec is a living document. An outdated spec is still better than no spec. |
| "The user knows what they want" | Even clear requests have implicit assumptions. The spec surfaces those assumptions. |
| "It's one big feature; splitting it is overhead" | If acceptance criteria cluster into independently testable groups, a monolithic spec forces every downstream task to reason over the whole contract. A ten-line capability map is the cheap alternative. |
| "I'll decompose during planning" | Planning slices tasks within a spec. By then the oversized artifact already exists — module boundaries and dependency direction must be decided before the spec is written, not after. |

## Red Flags

- Starting to write code without any written requirements
- Asking "should I just start building?" before clarifying what "done" means
- Implementing features not mentioned in any spec or task list
- Making architectural decisions without documenting them
- Starting implementation while material acceptance criteria are unresolved
- One spec whose requirements span several independently testable capabilities
- Module boundaries or build order decided implicitly during implementation because no capability map was approved up front

## Verification

Before proceeding to implementation, confirm:

- [ ] The spec covers all six core areas
- [ ] Required decisions are settled by the request, an existing approved spec or focused review
- [ ] Success criteria are specific and testable
- [ ] Boundaries (Always/Ask First/Never) are defined
- [ ] The spec is available at the requested handoff location
- [ ] For bundled capabilities, module IDs, dependencies and build order are settled
- [ ] Every module spec traces to a module id in the approved map
