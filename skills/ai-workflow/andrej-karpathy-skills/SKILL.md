---
name: andrej-karpathy-skills
description: 'Karpathy-inspired coding discipline for AI agents: think before coding, keep changes simple, edit surgically, and define verifiable success criteria before implementation.'
version: "1.0.0"
author: seaworld008
source: github:swarmclawai/andrej-karpathy-skills
source_url: "https://github.com/swarmclawai/andrej-karpathy-skills/blob/main/skills/karpathy-guidelines/SKILL.md"
license: MIT
tags: '[coding-discipline, architecture, backend, refactoring, code-review, ai-workflow, verification]'
created_at: "2026-06-03"
updated_at: "2026-06-03"
quality: 4
complexity: intermediate
---

# Andrej Karpathy Skills

Use this skill to keep AI-assisted engineering grounded, simple, and verifiable. It is especially useful for backend, architecture, refactoring, debugging, migrations, and any task where an agent might overbuild, guess, or change unrelated code.

The core idea is simple: do not let the model drift. Make assumptions explicit, prefer minimal changes, touch only what the request requires, and verify with concrete checks before calling the work done.

## When to Use

- Writing backend code, API changes, migrations, data access logic, or architecture-sensitive code.
- Refactoring code where accidental behavior changes are risky.
- Debugging a production issue or a failing test.
- Reviewing AI-generated code for overengineering, hidden assumptions, or missing verification.
- Implementing a user request that is ambiguous, cross-cutting, or easy to over-scope.
- Making changes in an unfamiliar codebase.
- Working under constraints such as dirty git state, existing style, generated files, or ownership boundaries.
- Producing a plan before code or a concise review after code.

## Skip When

- The user explicitly asks for brainstorming without implementation.
- The task is pure content writing, design exploration, or research without code changes.
- A different skill with stricter domain procedure applies, such as a security audit, incident response, or regulated compliance workflow.

## Core Principles

1. Think before coding.
2. Simplicity first.
3. Surgical changes.
4. Goal-driven execution.
5. Verification before completion.
6. Respect the existing system.
7. Surface uncertainty early.
8. Prefer reversible, observable steps.

## Principle 1: Think Before Coding

Before implementation, establish what is known and what is assumed.

- Read the relevant files before changing them.
- Identify the exact behavior the user wants changed.
- Name any ambiguity that changes the implementation path.
- If there are multiple viable approaches, pick the smallest one that fits the repo.
- If an approach creates a new abstraction, justify why it reduces real complexity.
- If the task crosses module boundaries, map those boundaries first.
- If the codebase already has a local pattern, use it.

Do not silently guess when the guess would affect data integrity, security, public API behavior, billing, auth, or destructive operations.

## Principle 2: Simplicity First

Write the minimum code that fully solves the actual problem.

- Do not add configuration for cases the user did not ask for.
- Do not introduce a framework, service, queue, cache, or abstraction just because it may help later.
- Do not broaden a bug fix into a style rewrite.
- Do not add generic helpers for one call site unless the helper removes real complexity.
- Keep names direct and local.
- Prefer boring data structures and clear control flow.
- Make failure modes explicit, but do not handle impossible states with noisy code.

Ask this before committing to an approach:

```text
Can the same behavior be achieved with fewer concepts, fewer files, and less surface area?
```

If yes, simplify.

## Principle 3: Surgical Changes

Every changed line should trace to the request.

- Touch only the files required by the task.
- Keep unrelated formatting, naming, and comments intact.
- Remove only unused code made unused by your own change.
- Leave unrelated dead code alone unless the user asked for cleanup.
- Preserve generated files unless the repository pipeline regenerates them.
- Do not rewrite public APIs when an adapter or narrow fix is enough.
- In a dirty worktree, distinguish your changes from existing user changes.

Use this edit filter:

```text
If I had to explain this line in the PR, could I tie it directly to the requested outcome?
```

If not, do not change it.

## Principle 4: Goal-Driven Execution

Turn vague tasks into verifiable goals.

- "Fix login" becomes: reproduce failing login, identify cause, patch, run auth tests.
- "Add validation" becomes: define invalid cases, test them, implement, verify messages.
- "Improve architecture" becomes: name the current pain, change one boundary, prove behavior holds.
- "Clean up" becomes: list safe cleanup targets, remove only confirmed unused or duplicated assets.

For multi-step work, use a compact plan:

```markdown
1. Inspect current behavior -> verify with failing test or local reproduction.
2. Make minimal change -> verify targeted test passes.
3. Run broader checks -> verify no nearby regression.
```

## Principle 5: Verification Before Completion

Do not finish on intuition.

- Run the smallest relevant test first.
- Then run the broader suite required by the blast radius.
- For UI work, inspect the rendered result when feasible.
- For generated files, rerun the generator and confirm no unexpected drift.
- For migrations, inspect schema and rollback assumptions.
- For security-sensitive work, run static checks and manual review.
- If a check cannot run, say exactly why and what risk remains.

Good final status includes changed files, validation performed, and known residual risk.

## Backend Discipline

For backend and architecture work:

- Preserve request/response contracts unless the user asked to change them.
- Keep validation at trust boundaries.
- Keep database writes transactional where partial writes would corrupt state.
- Make idempotency explicit for retries, webhooks, jobs, and sync flows.
- Avoid hidden global state and time-dependent behavior in core logic.
- Separate pure decision logic from I/O when it makes tests easier.
- Prefer existing repository error handling and logging conventions.
- Avoid swallowing exceptions without traceable context.

## Architecture Discipline

Use architecture changes only when they reduce current pain.

- Add a module boundary when multiple call sites need the same behavior.
- Add an interface when there are multiple real implementations or a test boundary demands it.
- Add a service only if it owns a coherent workflow.
- Add a background job only if synchronous execution is genuinely unsafe or too slow.
- Add a cache only when there is measured or obvious repeated expensive work.
- Add a migration path for public or persisted contracts.

If the change cannot be validated in this turn, keep it smaller.

## Review Checklist

- Scope: Does the diff solve only the user request?
- Assumptions: Are assumptions named or encoded in tests?
- Simplicity: Is there speculative abstraction?
- Behavior: Are important edge cases covered?
- Data: Are writes safe, atomic, and idempotent where needed?
- Security: Are inputs validated and secrets protected?
- Compatibility: Are public contracts preserved or intentionally migrated?
- Observability: Are errors diagnosable without leaking sensitive data?
- Verification: Did relevant tests or checks run?

## Anti-Patterns

- Rewriting a working subsystem to fix a one-line bug.
- Adding a new dependency for a small utility.
- Changing formatting across a file while making a behavior fix.
- Returning "done" without running any verification.
- Hiding uncertainty behind confident prose.
- Creating TODOs instead of finishing the requested path.
- Making the code more configurable than the product needs.
- Updating generated files by hand.

## Output Format

For implementation planning:

```markdown
## Assumptions
- ...

## Minimal Approach
- ...

## Verification
- Targeted:
- Broader:
```

For code review:

```markdown
## Findings
- [Severity] file:line - issue and impact

## Verification Gaps
- ...
```

## Boundaries

This skill is a discipline layer, not a replacement for domain expertise. Pair it with security, testing, DevOps, database, or frontend skills when the task needs specialized checks.
