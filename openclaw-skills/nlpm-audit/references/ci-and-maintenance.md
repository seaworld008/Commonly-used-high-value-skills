# NL Artifact CI And Maintenance

Use this reference when turning the audit into a repeatable maintenance process.

## Recommended Gates

| Gate | Blocking? | Why |
|---|---|---|
| Manifest references missing files | yes | installed artifacts can silently disappear |
| Disk artifact not reachable from manifest/catalog | yes for publishable packages | users cannot invoke it |
| Invalid frontmatter or config syntax | yes | loaders may ignore the file |
| Hook references absent script | yes | hook does not run |
| Hook uses suspicious executable pattern | yes for Critical/High | supply-chain risk |
| Version drift | yes before release | published metadata lies |
| Score below target | advisory by default | scoring contains judgment |
| Vocabulary drift | advisory unless opted in | premature enforcement hurts early projects |
| Plugin monorepo aggregate has high findings | yes | one nested plugin can be broken while the root looks clean |

For pull requests, limit subjective scoring to changed natural-language
artifacts. Repository-wide deterministic checks such as manifest reachability,
syntax, and version consistency should still run globally.

If a project opts into vocabulary enforcement, hard-fail only on deterministic
terms declared by its reviewed registry. Keep open-ended LLM clustering as an
advisory discovery signal because its output is not stable enough for a
required check.

## Pre-Commit Shape

```bash
#!/usr/bin/env bash
set -euo pipefail

python skills/ai-workflow/nlpm-audit/scripts/nl_artifact_check.py .
python scripts/lint_skill_quality.py --min-lines 50
python scripts/audit_licenses.py
```

## GitHub Actions Shape

```yaml
name: nl-artifact-check
on:
  pull_request:
    paths:
      - "skills/**"
      - "agents/**"
      - "commands/**"
      - ".claude-plugin/**"
      - ".codex-plugin/**"
      - "AGENTS.md"
      - "CLAUDE.md"
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python skills/ai-workflow/nlpm-audit/scripts/nl_artifact_check.py . --json
```

## Upstream NLPM Integration

Use upstream NLPM when maintainers want the original CLI/plugin behavior.

```bash
curl -fsSL -o ./nlpm-check https://raw.githubusercontent.com/xiaolai/nlpm/main/bin/nlpm-check
python3 ./nlpm-check .
```

For reproducible CI, pin to a reviewed commit:

```bash
curl -fsSL -o ./nlpm-check \
  https://raw.githubusercontent.com/xiaolai/nlpm/{reviewed-commit}/bin/nlpm-check
python3 ./nlpm-check .
```

For README badges, use upstream `nlpm-badge`:

```bash
curl -fsSL -o ./nlpm-badge https://raw.githubusercontent.com/xiaolai/nlpm/main/bin/nlpm-badge
python3 ./nlpm-check --json . | python3 ./nlpm-badge > nlpm-badge.json
```

Commit `nlpm-badge.json` only when the repository wants a public badge endpoint.

## Refresh Cadence

Monthly or before major release:

```bash
gh api repos/xiaolai/nlpm --jq '{license:.license.spdx_id,pushed_at,default_branch}'
gh api repos/xiaolai/nlpm/commits/main --jq '{sha:.sha,date:.commit.author.date,message:.commit.message}'
python scripts/sync_upstream.py --check-only --source github:xiaolai/nlpm
```

If upstream changed, review these files first:

- `README.md`
- `docs/for-authors.md`
- `RULES.md`
- `skills/nlpm/rules/SKILL.md`
- `skills/nlpm/scoring/SKILL.md`
- `skills/nlpm/testing/SKILL.md`
- `skills/nlpm/security/SKILL.md`
- `bin/nlpm-check`
- `templates/`
- `bin/nlpm-badge`
- `analysis/multi-tool-design-2026-05.md`
- `analysis/vocabulary-design-principles.md`

Promote changes into this skill when they are durable:

- new artifact categories;
- new deterministic checks;
- better CI patterns;
- clarified security false-positive filters;
- vocabulary-drift process changes;
- multi-plugin monorepo behavior;
- badge output or JSON contract changes;
- license or install changes.

Skip upstream details that are product-specific and likely to churn:

- auditor dashboard counts;
- daily case-study automation state;
- command implementation internals;
- temporary Antigravity advisory rules before the spec stabilizes.

## Last Curated Upstream Review

- Date: 2026-08-10
- Upstream: `xiaolai/nlpm`
- Commit reviewed: `06e14047e59a8446275dc1b2f082127fc3bc29de`
- License: ISC
- Durable changes absorbed: mention-versus-use and registry-declaration scoring
  exclusions, fenced-template example counting, deterministic vocabulary
  enforcement with advisory LLM clustering, changed-artifact PR scoring, and
  current Codex convention compatibility.

## Monitor-Only Sync

This curated skill should stay monitor-only in `docs/sources`. Upstream changes
should trigger review, not automatic replacement, because the upstream source is
a product repository while this file is a portable skill.

Expected behavior:

```bash
python scripts/sync_upstream.py --check-only --source github:xiaolai/nlpm
```

The command may report an update with `[monitor-only]`. That means: read the
upstream change, decide whether the curated skill should absorb it, and edit
manually.
