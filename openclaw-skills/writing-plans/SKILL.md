---
name: writing-plans
description: 'Write a practical implementation plan when multi-step work needs task boundaries, dependencies, and acceptance checks.'
zh_description: "编写包含任务依赖、修改范围和验收方法的实现计划。"
version: "1.0.2"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["planning", "plans", "workflow", "writing"]'
created_at: "2026-03-04"
updated_at: "2026-09-22"
quality: 4
complexity: "intermediate"
---

# Writing Plans

## Overview

Write comprehensive implementation plans for an engineer who needs the relevant repository context. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Describe the constraints and interfaces that matter; rely on the implementer's judgment for routine coding details.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** Reuse the current task workspace; isolate it when existing changes or parallel work require that.

**Save plans to:** `docs/plans/YYYY-MM-DD-<feature-name>.md`

## Bite-Sized Task Granularity

**Use coherent, independently verifiable tasks; the following test cycle is useful for behavior changes:**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Use the project's existing format, or this portable header:**

```markdown
# [Feature Name] Implementation Plan

> **Execution:** Follow the task dependencies and acceptance checks using the current host.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

## Task Structure

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

**Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## Remember
- Exact file paths always
- Describe interfaces, behavior, and acceptance criteria; include code only to resolve ambiguity
- Exact commands with expected output
- Name relevant skills only when their methods are needed and available
- DRY, YAGNI, TDD, frequent commits

## Execution Handoff

Continue implementation when the user already requested it.
For a plan-only request, deliver the plan and its unresolved decisions.
Keep execution in the current task unless the user requests another session.
Use delegation only when permitted by the host and useful for independent work.
A missing subagent tool does not prevent direct sequential execution.

Include the following information with any handoff:

- The plan path and current task status.
- The exact repository branch and ownership of existing changes.
- Dependencies that must finish before the next task starts.
- Completed checks and the revision they cover.
- Missing access or decisions that materially block work.
- The requested delivery target: local patch, PR, merge, or release.

## Adapting Existing Plans

Read unfinished tasks before replacing or extending a plan.
Keep completed evidence and unresolved work visible.
Update obsolete commands from the repository's current configuration.
Record why an acceptance criterion changed; do not silently weaken it.
When a check fails, investigate before adding workarounds or more tests.
Tests are appropriate for behavior changes and meaningful regressions.
A reversible prose edit usually needs review rather than a new test suite.

## Worked Handoff Example

```text
Task: Add filtered CSV export.
Done: Filter and column-order behavior covered by focused tests.
Next: Connect the existing table action to the export service.
Dependency: Reuse the approved data-access path.
Evidence: Focused tests passed on the recorded commit.
Delivery: User requested a PR and merge after required CI passes.
```
