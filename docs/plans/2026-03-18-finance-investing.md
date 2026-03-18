# Finance Investing Category Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a dedicated finance investing category, migrate existing finance skills into it, expand the repository with ten new finance skills, and keep the generated OpenClaw export working.

**Architecture:** Treat `skills/finance-investing/` as the new source-of-truth location for finance skills. Move the two existing finance skills from `skills/office-white-collar/`, create ten additional finance skill directories with substantial supporting content, update repository documentation, then regenerate `openclaw-skills/` from the categorized source tree.

**Tech Stack:** Markdown, Python 3 standard library, PowerShell, repository export script

---

### Task 1: Create the finance category scaffolding

**Files:**
- Create: `skills/finance-investing/`
- Modify: `docs/plans/2026-03-18-finance-investing-design.md`
- Modify: `docs/plans/2026-03-18-finance-investing.md`

**Step 1: Verify the current finance source locations**

Run: `Get-ChildItem skills\\office-white-collar | Select-Object Name`
Expected: shows `financial-analyst` and `financial-data-collector` under the old category

**Step 2: Create the new category path**

Run: `New-Item -ItemType Directory -Force skills\\finance-investing`
Expected: directory exists

**Step 3: Confirm the category is ready for skill migration**

Run: `Get-ChildItem skills | Select-Object Name`
Expected: includes `finance-investing`

### Task 2: Move the two existing finance skills

**Files:**
- Move: `skills/office-white-collar/financial-analyst` -> `skills/finance-investing/financial-analyst`
- Move: `skills/office-white-collar/financial-data-collector` -> `skills/finance-investing/financial-data-collector`

**Step 1: Move `financial-analyst`**

Run: `Move-Item skills\\office-white-collar\\financial-analyst skills\\finance-investing\\financial-analyst`
Expected: destination exists and source no longer exists

**Step 2: Move `financial-data-collector`**

Run: `Move-Item skills\\office-white-collar\\financial-data-collector skills\\finance-investing\\financial-data-collector`
Expected: destination exists and source no longer exists

**Step 3: Verify both moved cleanly**

Run: `Get-ChildItem skills\\finance-investing | Select-Object Name`
Expected: includes both migrated skills

### Task 3: Add ten new finance skills

**Files:**
- Create: `skills/finance-investing/comps-valuation-analyst/...`
- Create: `skills/finance-investing/earnings-call-analyzer/...`
- Create: `skills/finance-investing/sec-filing-reviewer/...`
- Create: `skills/finance-investing/portfolio-risk-manager/...`
- Create: `skills/finance-investing/factor-backtester/...`
- Create: `skills/finance-investing/stock-screener-builder/...`
- Create: `skills/finance-investing/macro-regime-monitor/...`
- Create: `skills/finance-investing/options-strategy-evaluator/...`
- Create: `skills/finance-investing/event-driven-tracker/...`
- Create: `skills/finance-investing/investment-memo-writer/...`

**Step 1: Define a consistent heavy-skill structure**

Each skill should have:

- `SKILL.md`
- `scripts/` when the workflow benefits from execution
- `references/` for methods, field definitions, and pitfalls
- `assets/` for templates or sample input/output

**Step 2: Write the skill content**

For each skill:

- use compliant frontmatter
- describe triggering conditions, constraints, workflow, tools, and outputs
- keep the content actionable and repository-consistent

**Step 3: Add runnable helpers where useful**

Prefer small Python scripts with standard library only for:

- valuation math
- risk metrics
- screening logic
- memo assembly
- event calendar normalization

**Step 4: Verify directory completeness**

Run: `Get-ChildItem skills\\finance-investing | Select-Object Name`
Expected: 12 finance skill directories are present

### Task 4: Update repository documentation

**Files:**
- Modify: `README.md`

**Step 1: Update top-level counts**

Adjust category and skill totals to reflect the new finance category and newly added skills.

**Step 2: Update the directory tree**

Add `finance-investing/` to the categorized layout.

**Step 3: Add a finance category overview**

Document the finance category in the categorized skill summary and remove the two migrated finance skills from the office category listing.

### Task 5: Refresh OpenClaw export

**Files:**
- Modify: `openclaw-skills/...` (generated)

**Step 1: Run the exporter**

Run: `python scripts/export_openclaw_skills.py`
Expected: `openclaw-skills/` is rebuilt successfully

**Step 2: Verify generated finance skills**

Run:

```powershell
Get-ChildItem openclaw-skills | Select-Object Name
```

Expected: includes all twelve finance skill names as flat child directories

**Step 3: Spot-check generated SKILL frontmatter**

Run:

```powershell
Get-Content openclaw-skills\\portfolio-risk-manager\\SKILL.md -TotalCount 20
Get-Content openclaw-skills\\investment-memo-writer\\SKILL.md -TotalCount 20
```

Expected: valid frontmatter with `name` and `description`

### Task 6: Run final verification

**Files:**
- Modify: repository working tree only

**Step 1: Verify source layout**

Run:

```powershell
Get-ChildItem skills\\finance-investing | Select-Object Name
Get-ChildItem skills\\office-white-collar | Select-Object Name
```

Expected: finance skills appear only in `finance-investing`

**Step 2: Verify exporter run**

Run: `python scripts/export_openclaw_skills.py`
Expected: exit code 0

**Step 3: Verify git diff sanity**

Run: `git status --short`
Expected: finance category additions, README update, generated OpenClaw export updates, no accidental unrelated edits
