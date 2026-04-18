# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A curated library of 188 AI Agent Skills (SKILL.md files) organized into 15 categories, supporting automated discovery, quality-gated ingestion, and upstream synchronization. Compatible with Codex, Claude Code, Cursor, and OpenClaw.

## Directory Layout

```
skills/<category>/<skill>/SKILL.md     ← Canonical source (never generated)
openclaw-skills/<skill>/SKILL.md       ← Auto-generated flat export (never hand-edit)
skills/*/README.md                     ← Auto-generated (never hand-edit)
docs/catalog.json                      ← Auto-generated (never hand-edit)
docs/TAGS-INDEX.md                     ← Auto-generated (never hand-edit)
docs/sources/*.skills.json             ← Provenance mapping, one file per source
scripts/                               ← Python automation pipeline
tests/                                 ← unittest test suite
```

## Key Rules

- **Never manually edit** `openclaw-skills/`, `skills/*/README.md`, `docs/catalog.json`, or `docs/TAGS-INDEX.md`.
- Every `SKILL.md` must have complete YAML frontmatter (name, description, version, tags, quality, source).
- Minimum commit bar: quality ≥ 2, content ≥ 50 lines.
- Every skill must have a provenance entry in `docs/sources/*.skills.json`.

## Common Commands

### Full pipeline (run after any skill change)
```bash
python scripts/enrich_frontmatter.py && \
python scripts/bootstrap_in_house_sources.py --write-json docs/sources/in-house.skills.json && \
python scripts/refresh_repo_views.py && \
python scripts/generate_tags_index.py && \
python scripts/build_catalog_json.py && \
python scripts/lint_skill_quality.py --min-lines 50 && \
python -m unittest discover tests -v
```

### Quality lint only
```bash
python scripts/lint_skill_quality.py --min-lines 50
```

### Run tests (all)
```bash
python -m unittest discover tests -v
```

### Run a single test
```bash
python -m unittest tests.test_export_openclaw_skills -v
```

### Refresh generated views only
```bash
python scripts/refresh_repo_views.py
```

### Sync a new skill's provenance after placing SKILL.md
```bash
python scripts/ingest_skill.py --dir skills/<category>/<skill-name> --source "<source_url>"
```

### Check upstream for available updates
```bash
python scripts/sync_upstream.py --check-only
```

### Sync Codex local skills from repo
```bash
python scripts/sync_codex_skills.py --source-root skills/ --codex-root ~/.codex/skills
```

## Skill Frontmatter Schema

```yaml
---
name: skill-name
description: "One-line description"
version: "1.0.0"
author: seaworld008
source: in-house   # in-house | skills.sh | clawhub | github:<owner>/<repo> | community
source_url: ""
tags: [tag1, tag2, tag3]
created_at: "YYYY-MM-DD"
updated_at: "YYYY-MM-DD"
quality: 4         # 1–5
complexity: intermediate   # beginner | intermediate | advanced
---
```

## Quality Ratings

| Rating | Min Lines | Bar |
|--------|-----------|-----|
| 5 | ≥200 | Comprehensive, multiple code examples, edge cases, anti-patterns |
| 4 | ≥100 | Solid coverage with code examples and practical templates |
| 3 | ≥80 | Basic coverage with at least one code block |
| 2 | ≥50 | Minimal viable, needs expansion |
| 1 | <50 | Stub — do not commit |

## CI Checks

GitHub Actions (`repo-validation.yml`) runs on push/PR to `main`:
1. `lint_skill_quality.py --min-lines 50`
2. `refresh_repo_views.py`
3. `generate_tags_index.py`
4. `build_catalog_json.py`
5. unittest suite (7 test modules)
6. `git diff --exit-code` — fails if generated files are stale

Always run the full pipeline locally before pushing to avoid CI failures on stale generated files.

## Adding a New Skill

1. Create `skills/<category>/<skill-name>/SKILL.md` with complete frontmatter and ≥ 50 lines.
2. Run `python scripts/ingest_skill.py --dir skills/<category>/<skill-name> --source "<url>"`.
3. Run the full pipeline (above).
4. Commit all changes including generated files.

## 15 Skill Categories

`developer-engineering`, `devops-sre`, `finance-investing`, `growth-operations-xiaohongshu`, `product-design`, `security-and-reliability`, `ai-agent-platform`, `engineering-workflow-automation`, `operations-general`, `task-understanding-decomposition`, `deployment-platforms`, `office-white-collar`, `multimodal-media`, `knowledge-and-pm-integrations`, `openclaw-memory-and-safety`

When placing a skill in a category, match the primary function. If uncertain, use `operations-general`.
