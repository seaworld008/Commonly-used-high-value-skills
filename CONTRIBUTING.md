# Contributing

Thanks for helping improve this repository.

This project is designed as a practical, high-value skills library for AI developers and multi-client agent workflows. Good contributions should improve reuse, clarity, and compatibility.

## What To Contribute

- new high-value skills
- improvements to existing `SKILL.md` files
- reusable `scripts/`, `references/`, and `assets/`
- better compatibility for `Codex`, `Claude Code`, and `OpenClaw`
- README and discoverability improvements

## Skill Structure

Use this layout:

```text
skills/<category>/<skill-name>/
  SKILL.md
  scripts/
  references/
  assets/
```

## Naming Rules

- use lowercase kebab-case for skill directories
- keep names specific and searchable
- prefer trigger-oriented descriptions in frontmatter
- avoid vague names like `helper-skill` or `useful-tool`

## Multi-Client Compatibility

- `skills/` is the source-of-truth tree
- `openclaw-skills/` is generated output
- `skills/*/README.md` is generated output
- do not hand-edit `openclaw-skills/`
- do not hand-edit generated category README files
- refresh generated views with:

```bash
python3 scripts/refresh_repo_views.py
```

## Before Opening a PR

Please verify:

- the skill lives in the correct category
- `SKILL.md` includes valid frontmatter
- any new scripts or helpers are documented
- generated views have been refreshed if source skills changed
- README counts and category descriptions stay accurate when relevant

## Recommended Verification

Examples:

```bash
python -m unittest tests.test_export_openclaw_skills -v
python -m unittest tests.test_finance_investing_skills -v
python -m unittest tests.test_generate_category_readmes -v
python -m unittest tests.test_refresh_repo_views -v
python3 scripts/refresh_repo_views.py
```

If your change adds a new script, include the exact command you used to test it.

## PR Quality Bar

A strong PR should clearly explain:

- what changed
- why it matters
- how it was verified
- whether it changes generated OpenClaw output

## Good First Contribution Ideas

- improve a weak skill description
- add sample assets for an existing skill
- add verification tests for a script-backed skill
- improve bilingual README and onboarding docs
- add a high-signal skill in an underdeveloped category
