# Finance Investing Category Design

**Date:** 2026-03-18

**Problem**

This repository already includes two finance-oriented skills, but they currently live under `skills/office-white-collar/`. That placement makes the financial toolkit hard to discover, mixes investment workflows with generic office productivity, and prevents the repository from presenting finance as a first-class scenario category.

The user wants a dedicated finance category plus at least ten additional finance skills. The new set should feel production-ready rather than placeholder-only, and it must stay compatible with both categorized AI-tool usage (`skills/`) and the generated flat OpenClaw export (`openclaw-skills/`).

**Goal**

Add a dedicated `skills/finance-investing/` source category, migrate the two existing finance skills into it, add ten new finance skills with substantial supporting material, update repository documentation, and regenerate the OpenClaw-compatible export without breaking the existing multi-client workflow.

**Recommended Architecture**

1. Create `skills/finance-investing/` as the canonical source category for finance and investing workflows.
2. Move these existing skills into the new category:
   - `financial-analyst`
   - `financial-data-collector`
3. Add ten new finance skills covering three practical lanes:
   - research and valuation
   - trading and portfolio management
   - investment communication and operating cadence
4. Keep skill names flat and client-friendly so `scripts/export_openclaw_skills.py` can continue exporting them directly into `openclaw-skills/<skill-name>/`.
5. Reuse a consistent skill shape for heavy-weight finance skills:
   - `SKILL.md`
   - `scripts/`
   - `assets/`
   - `references/`
6. Update `README.md` so the new category is visible in the categorized tree, skill overview, and total counts.

**Scope of New Skills**

The finance category will contain these twelve skills after the change:

- `financial-analyst`
- `financial-data-collector`
- `comps-valuation-analyst`
- `earnings-call-analyzer`
- `sec-filing-reviewer`
- `portfolio-risk-manager`
- `factor-backtester`
- `stock-screener-builder`
- `macro-regime-monitor`
- `options-strategy-evaluator`
- `event-driven-tracker`
- `investment-memo-writer`

**Design Choices**

**Category name**

Use `finance-investing` rather than `finance`. The longer name is still concise, is easy to understand in English, and naturally covers both corporate-finance analysis and public-market investing workflows.

**Migration strategy**

Move the two existing finance skills into the new category rather than duplicating them. This keeps the categorized source tree clean and avoids maintaining the same skill under multiple source categories. OpenClaw compatibility is preserved because the export is based on skill directory names, not category names.

**Weight of implementation**

Favor a "heavy skill" model. Every new skill should have a robust `SKILL.md` plus at least one of:

- runnable scripts
- reusable templates
- reference documentation
- sample input/output assets

This keeps the new category useful for real work and aligned with the stronger existing skills in the repository.

**Validation Plan**

- Verify the new category exists under `skills/`
- Verify the old finance skill directories are no longer under `office-white-collar/`
- Verify all finance skill directories contain `SKILL.md`
- Refresh `openclaw-skills/` with the exporter
- Verify the generated OpenClaw tree includes all finance skills as immediate children
- Spot-check exported frontmatter for several newly added finance skills
