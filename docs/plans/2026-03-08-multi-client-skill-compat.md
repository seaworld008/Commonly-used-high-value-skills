# Multi-Client Skill Compatibility Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make this repository installable across Codex, Claude-style assistants, and OpenClaw without changing the existing categorized skill source tree.

**Architecture:** Keep `skills/` as the canonical categorized source tree, add a generated flat `openclaw-skills/` export for OpenClaw discovery, and add root-level agent instructions so AI assistants choose the correct install path automatically.

**Tech Stack:** Markdown, Python 3 standard library, `unittest`

---

### Task 1: Add export test coverage

**Files:**
- Create: `tests/test_export_openclaw_skills.py`

**Step 1: Write the failing test**

Cover these cases:

- export flattens `skills/<category>/<skill>` into `openclaw-skills/<skill>`
- exported skill copies supporting files
- missing frontmatter is synthesized with `name` and `description`
- existing extra frontmatter blocks are preserved

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_export_openclaw_skills -v`
Expected: FAIL because exporter module does not exist yet

**Step 3: Write minimal implementation**

Create exporter functions used by the test.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_export_openclaw_skills -v`
Expected: PASS

### Task 2: Implement OpenClaw export script

**Files:**
- Create: `scripts/export_openclaw_skills.py`

**Step 1: Implement source scanning**

Source pattern:

- `skills/<category>/<skill>/SKILL.md`

Output pattern:

- `openclaw-skills/<skill>/SKILL.md`

**Step 2: Implement frontmatter normalization**

- Preserve existing `name` / `description` when possible
- Synthesize missing values from folder name and body text
- Preserve non-`name`/`description` frontmatter blocks

**Step 3: Implement recursive copy**

- Copy supporting files and subdirectories
- Rewrite only `SKILL.md`
- Remove stale output before regeneration

**Step 4: Add CLI entrypoint**

Run:

```bash
python3 scripts/export_openclaw_skills.py
```

Expected:

- export completes without error
- `openclaw-skills/` is refreshed

### Task 3: Add repository-level installation guidance

**Files:**
- Modify: `README.md`
- Create: `AGENTS.md`

**Step 1: Update README**

Add:

- compatibility explanation
- install matrix by client
- OpenClaw usage path
- export refresh command

**Step 2: Add root AGENTS.md**

Tell AI assistants:

- use `skills/` for Codex/Claude-style workflows
- use `openclaw-skills/` for OpenClaw installs
- do not point OpenClaw at repo root or `skills/`

### Task 4: Generate compatibility export and verify

**Files:**
- Create: `openclaw-skills/...` (generated)

**Step 1: Run exporter**

Run: `python3 scripts/export_openclaw_skills.py`

Expected:

- `openclaw-skills/` contains one directory per skill

**Step 2: Verify OpenClaw-compatible shape**

Run:

```bash
find openclaw-skills -mindepth 1 -maxdepth 1 -type d | wc -l
find openclaw-skills -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l
```

Expected:

- both counts match total exported skills

**Step 3: Verify tests**

Run:

```bash
python3 -m unittest tests.test_export_openclaw_skills -v
```

Expected:

- PASS
