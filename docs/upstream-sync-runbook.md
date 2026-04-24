# Upstream Sync Runbook

This repository supports two levels of automated upstream refresh.

## Sync Everything

Use this for routine maintenance when upstream repositories may have changed:

```bash
python scripts/sync_all_upstream_skills.py --apply --run-pipeline
```

This command refreshes:

- `addyosmani/agent-skills` through its bundle-aware importer
- every other external skill listed in `docs/sources/*.skills.json`
- generated repository views, OpenClaw export, tag index, catalog, quality lint, and tests

To also install the refreshed skills into local Codex:

```bash
python scripts/sync_all_upstream_skills.py --apply --run-pipeline --sync-codex-root ~/.codex/skills
```

## Check Everything Without Writing

```bash
python scripts/sync_all_upstream_skills.py
```

## Sync One Source

For non-addyosmani sources, use exact provenance-backed sync:

```bash
python scripts/sync_upstream.py --check-only --source github:obra/superpowers
python scripts/sync_upstream.py --apply --source github:obra/superpowers
```

For `addyosmani/agent-skills`, use its dedicated importer because it also preserves commands, personas, hooks, docs, and references:

```bash
python scripts/sync_addyosmani_agent_skills.py --apply --run-pipeline
```

## What Makes A Skill Auto-Upgradeable

An external skill is auto-upgradeable when its source mapping contains:

```json
{
  "repo_skill": "skills/<category>/<skill>/SKILL.md",
  "upstream": {
    "repo": "owner/repo",
    "path": "path/in/upstream/SKILL.md",
    "ref": "main"
  }
}
```

The generic sync reads those exact paths from `docs/sources/*.skills.json`, fetches upstream content, keeps local enriched frontmatter, replaces the body, updates timestamps, and syncs same-directory auxiliary files when available.
