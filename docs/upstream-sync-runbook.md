# Upstream Sync Runbook

This repository supports two levels of automated upstream refresh.

For the full weekly curation workflow, including portfolio audit, external
blocker triage, replacement decisions, and automation model settings, see
[Skill Curation and Automation Runbook](./skill-curation-and-automation-runbook.md).

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

## Handling Noisy Or Retired Upstreams

Do not treat every upstream fetch failure as a repository regression.

- ClawHub SSL EOF, TLS handshake timeouts, and transient `IncompleteRead` errors are external noise. Retry briefly, record source health, and avoid marking the run as fully fresh if discovery was partial.
- Old GitHub raw-path `404` responses usually mean the provenance path is stale. First repair the exact upstream path from `source_url` or the GitHub API.
- If the upstream skill has genuinely disappeared but the local skill remains valuable, keep the local version and mark the mapping as archived or local-only instead of repeatedly failing future sync runs.
- License gaps are not noise. Missing or unknown license metadata must be fixed, or the skill must become an original in-house rewrite before copying any upstream text.

Example archived mapping:

```json
{
  "upstream": {
    "sync_mode": "archived",
    "archived_at": "2026-06-29"
  }
}
```

Example local-only mapping:

```json
{
  "upstream": {
    "sync_mode": "local-only"
  }
}
```
