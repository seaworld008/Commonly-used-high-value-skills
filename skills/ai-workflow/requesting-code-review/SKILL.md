---
name: requesting-code-review
description: 'Use when completing tasks, implementing major features, or before merging to verify work meets requirements'
zh_description: "用于在完成任务、实现重要功能或合并前请求代码审查并验证需求满足情况。"
version: "1.0.3"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["code-review", "workflow", "quality-gate"]'
created_at: "2026-04-13"
updated_at: "2026-06-29"
quality: 4
complexity: "intermediate"
---

# Requesting Code Review

Dispatch a code reviewer subagent to catch issues before they cascade. The reviewer gets precisely crafted context for evaluation — never your session's history. This keeps the reviewer focused on the work product, not your thought process, and preserves your own context for continued work.

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

**1. Get git SHAs:**
```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or origin/main
HEAD_SHA=$(git rev-parse HEAD)
```

**2. Dispatch code reviewer subagent:**

Dispatch a `general-purpose` subagent, filling the template at [code-reviewer.md](code-reviewer.md)

**Placeholders:**
- `{DESCRIPTION}` - Brief summary of what you built
- `{PLAN_OR_REQUIREMENTS}` - What it should do
- `{BASE_SHA}` - Starting commit
- `{HEAD_SHA}` - Ending commit

**3. Act on feedback:**
- Fix Critical issues immediately
- Fix Important issues before proceeding
- Note Minor issues for later
- Push back if reviewer is wrong (with reasoning)

## Example

```
[Just completed Task 2: Add verification function]

You: Let me request code review before proceeding.

BASE_SHA=$(git log --oneline | grep "Task 1" | head -1 | awk '{print $1}')
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

## Integration with Workflows

**Subagent-Driven Development:**
- Review after EACH task
- Catch issues before they compound
- Fix before moving to next task

**Executing Plans:**
- Review after each task or at natural checkpoints
- Get feedback, apply, continue

**Ad-Hoc Development:**
- Review before merge
- Review when stuck

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

<!-- LOCAL-CURATION-SUPPLEMENT:START -->
## Review Request Checklist

A strong review request includes:

- The user-facing requirement or plan being validated.
- The exact diff range, branch, or commit pair under review.
- The areas where risk is highest: data loss, auth, concurrency, migrations, billing, security, or UX regressions.
- The tests already run and any tests intentionally skipped.
- The expected behavior in edge cases, not just the happy path.
- Any files or generated artifacts reviewers should ignore.

## Good vs Weak Requests

Weak:

```text
Please review my changes.
```

Better:

```text
Review the checkout retry changes from BASE..HEAD. Focus on idempotency,
double-charge prevention, webhook replay behavior, and missing tests.
I ran the unit suite and one manual Stripe test; migration rollback is not covered.
```

## Follow-up Rules

- Fix critical and important findings before moving to the next task.
- If a finding is rejected, document the technical reason and supporting evidence.
- Re-run the relevant tests after changes, not only the full suite.
- Keep review conversations tied to code and requirements, not preferences.
<!-- LOCAL-CURATION-SUPPLEMENT:END -->
