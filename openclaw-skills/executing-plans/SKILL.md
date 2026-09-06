---
name: executing-plans
description: Use when you have a written implementation plan to execute in a separate session with review checkpoints
zh_description: "用于按既定实现计划逐步执行任务，并在关键节点进行审查和完成验证。"
version: "1.0.6"
author: "seaworld008"
source: "github:obra/superpowers"
source_url: "https://github.com/obra/superpowers/blob/main/skills/executing-plans/SKILL.md"
license: MIT
tags: '["plans", "execution", "workflow"]'
created_at: "2026-04-13"
updated_at: "2026-09-06"
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
- Announce: "I'm using the finishing-a-development-branch skill to complete this work."
- **REQUIRED SUB-SKILL:** Use superpowers:finishing-a-development-branch
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
<!-- LOCAL-QUALITY-SUPPLEMENT:START -->
## Usage Notes

This supplement is maintained by the repository sync pipeline. It keeps the
imported upstream skill usable inside this curated collection when the upstream
source is intentionally concise.

## Common Patterns

```text
1. Confirm that the user's task matches the skill trigger.
2. Read the relevant project files or user-provided context before acting.
3. Choose the smallest reversible action that advances the task.
4. Run the verification command or manual check that proves the result.
5. Report the outcome, evidence, and any remaining risk.
```

## Boundaries

- Prefer the upstream workflow for Executing Plans; this section only adds local quality
  guardrails.
- Do not invent project facts when required files, vaults, services, or tools are
  unavailable.
- Stop and ask for clarification when the next action could overwrite user work,
  expose private data, or change production state.
<!-- LOCAL-QUALITY-SUPPLEMENT:END -->
