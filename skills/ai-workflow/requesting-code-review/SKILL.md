---
name: requesting-code-review
description: 'Use when completing tasks, implementing major features, or before merging to verify work meets requirements'
zh_description: "用于在完成任务、实现重要功能或合并前请求代码审查并验证需求满足情况。"
version: "1.0.7"
author: "seaworld008"
source: "github:obra/superpowers"
source_url: "https://skills.sh/obra/superpowers/requesting-code-review"
license: MIT
tags: ["code-review", "workflow", "quality-gate"]
created_at: "2026-04-13"
updated_at: "2026-11-17"
quality: 4
complexity: "intermediate"
---

# Requesting Code Review

Use an independent code reviewer when delegation is supported and authorized; otherwise review locally with the same checklist and state the independence limit. The reviewer gets precisely crafted context for evaluation — never your session's history.

**Core principle:** Review early, review often.

## When to Request Review

**Mandatory:**
- After each task in subagent-driven development
- After completing major feature
- Before merge to main

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing complex bug

## How to Request

**1. Establish the actual review target:**

Inspect the current implementation before choosing a commit range:

```bash
git status --short
git diff
git diff --staged
git ls-files --others --exclude-standard
```

Use the task's known base, not an assumed `HEAD~1`. For fully committed work, identify the intended starting and ending SHAs:
```bash
BASE_SHA='REPLACE_WITH_VERIFIED_TASK_BASE_SHA'
HEAD_SHA=$(git rev-parse HEAD)
```

For uncommitted implementation, the review target is the current snapshot: relevant committed changes plus staged, unstaged, and task-owned untracked files. Include their actual diffs and contents without unrelated user changes or secrets. Do not make a commit just to request review.

**2. Request review using available host capabilities:**

If delegation is supported and permitted, discover the host's actual schema and pass the template at [code-reviewer.md](code-reviewer.md). Otherwise apply that template locally. For snapshot review, replace the template's commit-range-only Git section with the exact review files, staged/unstaged diffs, and relevant untracked contents established above; SHA placeholders alone do not describe uncommitted work.

The review is read-only: do not move HEAD or alter the working tree. If tools need a different checkout, use an authorized temporary copy or isolated checkout and preserve the current one.

**Placeholders:**
- `{DESCRIPTION}` - Brief summary of what you built
- `{PLAN_OR_REQUIREMENTS}` - What it should do
- `{BASE_SHA}` - Starting commit
- `{HEAD_SHA}` - Ending commit
- Review target - Verified commit range or current snapshot manifest and supplied diffs/contents; explicitly state exclusions

**3. Act on feedback:**
- Fix Critical issues immediately
- Fix Important issues before proceeding
- Note Minor issues for later
- Push back if reviewer is wrong (with reasoning)

## Example

```
[Just completed Task 2: Add verification function]

You: Let me request code review before proceeding.

BASE_SHA=$(git log --oneline | grep "Task 1" | head -1 | cut -d' ' -f1)
HEAD_SHA=$(git rev-parse HEAD)

[Dispatch code reviewer subagent]
  DESCRIPTION: Added verifyIndex() and repairIndex() with 4 issue types
  PLAN_OR_REQUIREMENTS: Task 2 from docs/superpowers/plans/deployment-plan.md
  BASE_SHA: a7981ec
  HEAD_SHA: 3df7661

[Subagent returns]:
  Strengths: Clean architecture, real tests
  Issues:
    Important: Missing progress indicators
    Minor: Magic number (100) for reporting interval
  Assessment: Ready to proceed

You: [Fix progress indicators]
[Continue to Task 3]
```

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "The host has no delegation, so review cannot run" | Review locally with the same requirements and checklist, and state that it was not independent. When delegation is supported and authorized, prefer an independent reviewer. |
| "The reviewer needs my whole session history to understand the change" | Hand it precisely crafted context, never your session's history. That keeps the reviewer on the work product, not your thought process. |

## Red Flags

**Never:**
- Skip review because "it's simple"
- Ignore Critical issues
- Proceed with unfixed Important issues
- Argue with valid technical feedback

**If reviewer wrong:**
- Push back with technical reasoning
- Show code/tests that prove it works
- Request clarification

See template at: [code-reviewer.md](code-reviewer.md)
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

- Prefer the upstream workflow for Requesting Code Review; this section only adds local quality
  guardrails.
- Do not invent project facts when required files, vaults, services, or tools are
  unavailable.
- Stop and ask for clarification when the next action could overwrite user work,
  expose private data, or change production state.
<!-- LOCAL-QUALITY-SUPPLEMENT:END -->
