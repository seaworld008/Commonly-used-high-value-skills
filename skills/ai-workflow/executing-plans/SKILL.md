---
name: executing-plans
description: 'Use when executing an existing implementation plan, tracking dependencies, adapting outdated steps, and verifying acceptance checks.'
zh_description: "用于按既定实现计划逐步执行任务，并在关键节点进行审查和完成验证。"
version: "1.0.7"
author: "seaworld008"
source: "github:obra/superpowers"
source_url: "https://github.com/obra/superpowers/blob/main/skills/executing-plans/SKILL.md"
license: MIT
tags: '["plans", "execution", "workflow"]'
created_at: "2026-04-13"
updated_at: "2026-09-22"
quality: 3
complexity: "intermediate"
---

# Executing Plans

## Overview

Load plan, review critically, execute all tasks, report when complete.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

Use subagents only when supported, permitted, and useful for independent tasks. Otherwise execute the plan directly; no extra runtime setup is needed.

## The Process

### Step 1: Load and Review Plan
1. Inspect workspace ownership; reuse a clean task branch or isolate work if necessary
2. Read plan file
3. Review critically - identify any questions or concerns about the plan
4. Resolve routine concerns from repository evidence; ask about material unresolved decisions
5. If no concerns: Create todos for the plan items and proceed

### Step 2: Execute Tasks

For each task:
1. Mark as in_progress
2. Preserve the intended outcome; adapt obsolete implementation details from current evidence
3. Run verifications as specified
4. Mark as completed

### Step 3: Complete Development

After all tasks complete and verified:
- Inspect the requested delivery target and repository completion checks
- Use an available finishing workflow when its methods are needed
- Verify required checks and execute the delivery path already requested; ask only if it is unresolved

## When to Stop and Ask for Help

**STOP executing immediately when:**
- Required access or a consequential user decision is unavailable after investigation
- Plan has critical gaps preventing starting
- A material scope conflict cannot be resolved from current instructions or evidence
- Verification reveals an external blocker that cannot be repaired within the authorized scope

Investigate test failures and missing local dependencies first; repair routine blockers within scope. Ask for the specific missing input only when it is necessary.

## When to Revisit Earlier Steps

**Return to Review (Step 1) when:**
- Partner updates the plan based on your feedback
- Fundamental approach needs rethinking

**Don't force through blockers** - stop and ask.

## Remember
- Review plan critically first
- Follow acceptance criteria and update the plan when current evidence requires a change
- Don't skip verifications
- Reference skills when plan says to
- Stop when blocked, don't guess
- Never start implementation on main/master branch without explicit user consent
## Task Evidence Ledger

Track results against the actual work revision:

```text
Task: Implement retry policy
Input: Existing plan, current error contract, caller tests
Files: Client implementation and focused retry tests
Acceptance: Bounded attempts; cancellation propagates
Evidence: Test command, exit status, revision
Next: Integration check after the dependent caller changes
```

Reuse passing evidence while its relevant inputs are unchanged.
Invalidate the affected check when a dependency or implementation changes.
Keep failed checks visible until their causes are resolved.
A skipped external integration is not a passing integration test.

## Plan Drift and Recovery

Compare each step with current repository files before executing it.
When a command or file moved, update the plan from observed evidence.
Keep unfinished user tasks separate from newly discovered follow-up work.
For an unavailable dependency, complete independent tasks first.
Report the precise missing access or decision needed for blocked work.

## Completion Example

```text
Implemented: Tasks 1-4, with dependency order preserved.
Validated: Focused tests and required repository checks.
Delivery: PR created and merged when that was requested.
Unverified: External staging flow requires a configured environment.
```
