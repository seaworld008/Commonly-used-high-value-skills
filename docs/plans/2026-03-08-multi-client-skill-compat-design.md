# Multi-Client Skill Compatibility Design

**Date:** 2026-03-08

**Problem**

This repository is optimized for human browsing and Codex/Claude-style usage with a categorized layout:

`skills/<category>/<skill>/SKILL.md`

OpenClaw does not discover that layout when pointed at the repository root or the `skills/` root. Its local scanner expects either:

- a single skill directory containing `SKILL.md`, or
- a flat skill root where immediate child directories each contain `SKILL.md`

As a result, users can clone this repo, "install" it, and still see zero recognized skills in OpenClaw.

**Goal**

Keep the current categorized source tree for Codex/Claude and human maintainers, while adding a deterministic OpenClaw-compatible export plus explicit installation guidance for different AI clients.

**Recommended Architecture**

1. Treat `skills/` as the source-of-truth tree.
2. Generate `openclaw-skills/<skill-name>/...` as a flat compatibility export for OpenClaw.
3. Add root-level instructions so AI assistants can choose the correct install path:
   - `OpenClaw` -> use `openclaw-skills/`
   - `Codex` / `Claude` / similar coding assistants -> use `skills/`
4. Normalize exported `SKILL.md` files for OpenClaw compatibility:
   - ensure frontmatter exists
   - ensure `name` and `description` are present
   - preserve any additional frontmatter blocks where possible
5. Document a single refresh command so the export can be regenerated after source changes.

**Tradeoffs Considered**

- Directly flattening the main `skills/` tree would improve OpenClaw compatibility but would destroy the current category-based organization.
- Relying on documentation alone would still leave OpenClaw users with a broken default path.
- Maintaining two manual trees would drift quickly and create review overhead.

The generated export is the lowest-risk option because it preserves the current authoring model while giving OpenClaw a layout it can actually discover.

**Validation Plan**

- Add automated tests for the export script.
- Verify the generated `openclaw-skills/` root contains immediate child skill directories.
- Verify exported skills receive usable frontmatter even when the source `SKILL.md` does not have it.
- Update README and root `AGENTS.md` so both humans and AI agents are directed to the correct installation root.
