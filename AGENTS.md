# Repository Agent Instructions

This repository supports multiple AI clients, but they must not install skills from the same path.

## Installation Root By Client

- `OpenClaw`: use `openclaw-skills/`
- `Codex`, `Claude Code`, and similar coding assistants: use `skills/`

## Why

- `skills/` is the canonical categorized source tree:
  - `skills/<category>/<skill>/SKILL.md`
- OpenClaw does not reliably discover that categorized layout from the repo root or the `skills/` root.
- `openclaw-skills/` is the generated flat export for OpenClaw:
  - `openclaw-skills/<skill>/SKILL.md`

## Rules

- Do not point OpenClaw at the repository root.
- Do not point OpenClaw at `skills/`.
- Do not manually edit `openclaw-skills/`; regenerate it from source.
- When source skills change, refresh the OpenClaw export with:

```bash
python3 scripts/export_openclaw_skills.py
```

## Recommended Usage

### For OpenClaw

- Clone this repository.
- Configure OpenClaw to load from the cloned repo's `openclaw-skills/` directory, for example via `skills.load.extraDirs`.
- Verify with:

```bash
openclaw skills list
openclaw skills check
```

### For Codex / Claude Code

- Clone this repository.
- Read and use skills from the categorized `skills/` tree.
- Preserve category organization when creating or editing skills.
