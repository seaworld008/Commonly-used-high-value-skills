# Upgrade-safe contract

This workflow is intentionally non-intrusive.

Allowed to change:
- local wrappers in `~/.local/bin/`
- project-local scripts under `scripts/`
- project docs and AGENTS guidance
- local gitignored workflow state such as `.planning/` and `graphify-out/`

Not the default place to change:
- Hermes upstream repo code
- graphify upstream package code
- GSD upstream repo code

Preferred fix order after upstream changes:
1. fix wrapper path detection
2. fix wrapper invocation logic
3. fix project-local scripts
4. only then consider upstream changes if the user explicitly wants upstream contribution
