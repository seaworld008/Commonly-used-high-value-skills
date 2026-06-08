# Repository Agent Instructions

This repository is the world's most comprehensive curated collection of high-quality AI Agent Skills. It supports automated skill discovery, quality-gated ingestion, and upstream synchronization.

## Architecture Overview

```
skills/<category>/<skill>/SKILL.md    ← Canonical categorized source (AI clients read from here)
openclaw-skills/<skill>/SKILL.md      ← Auto-generated flat export for OpenClaw
docs/sources/in-house.skills.json     ← Provenance mapping (every skill tracked)
docs/catalog.json                     ← Machine-readable full catalog
docs/TAGS-INDEX.md                    ← Cross-category tag-based index
.github/assets/repo-banner.svg        ← Auto-generated README banner from docs/catalog.json
```

## Installation Root By Client

- `OpenClaw`: use `openclaw-skills/` (flat layout)
- `Codex`, `Claude Code`, `Cursor`, and similar: use `skills/` (categorized layout)

## Golden Rules

1. **Never manually edit** `openclaw-skills/`, `skills/*/README.md`, `docs/catalog.json`, `docs/TAGS-INDEX.md`, or `.github/assets/repo-banner.svg` — they are auto-generated.
2. **Always run the full pipeline** after any skill change (see §Pipeline below).
3. **Every skill must have complete frontmatter** (name, description, version, tags, quality, source).
4. **Every copied external skill must have an explicit permissive license** (`license: MIT`, `Apache-2.0`, etc.). If the upstream repository has no detectable license but the candidate is high quality, auto-create an original `in-house` rewrite instead of copying upstream text.
5. **Every skill must pass quality lint** (`python scripts/lint_skill_quality.py --min-lines 50`).
6. **Source provenance must be tracked** — every skill has an entry in `docs/sources/*.skills.json`.
7. **Keep bilingual READMEs synchronized** — when updating `README.md`, update `README.en.md` in the same change and run `python scripts/check_readme_sync.py`.
8. **Keep all public counts generated from one source of truth** — skill totals in README badges/text, `docs/catalog.json`, and `.github/assets/repo-banner.svg` must match the actual `skills/*/*/SKILL.md` tree. Run `python scripts/refresh_repo_views.py`, `python scripts/build_catalog_json.py`, and `python scripts/check_readme_sync.py`; never hand-edit counts or banner numbers.
9. **Prefer authenticated GitHub access for automation** — before running discovery or upstream sync, verify `gh auth status`. If `GITHUB_TOKEN` / `GH_TOKEN` are unset, repository automation should fall back to the locally authenticated `gh` token instead of running unauthenticated searches that cause `401` or premature rate limiting.
10. **Treat warning sources differently** — distinguish between actionable repository regressions (quality lint, missing frontmatter, generated diff drift) and external-state noise (GitHub API rate limits, exploratory `404` upstream paths, temporary DNS failures). Fix the former in the same run; report the latter with enough detail to retry or repair provenance later.
11. **Prefer staged pull requests for recurring maintenance** — if the run includes both a focused additive change (for example a new skill) and a broad upstream sync, split them into separate `codex/` branches and PRs so review and rollback stay manageable.

---

## Automated Operations (SOP for AI Agents)

### Recurring Run Preflight (每周例行前置检查)

Run this before Operation 1/2/3:

```bash
git fetch origin --prune
gh auth status
git status --short --branch
```

Interpretation:

- If `gh auth status` fails, fix GitHub authentication before discovery/sync work.
- If the worktree is dirty, either stop or isolate the maintenance work on a fresh `codex/` branch after understanding the existing changes.
- If network or DNS is down, do not trust `0 updates found` as a complete freshness result; record it as a partial check and retry once connectivity is restored.

### Operation 1: Discover & Add New Skills (全网搜集优秀技能)

**Trigger**: User says "add best skills", "find new skills", "搜集优秀技能", "增加一些好的skills" or similar.

**Procedure**:

```
Step 1: DISCOVER — Search all platforms for candidate skills
  ├── Run: python scripts/discover_new_skills.py --output docs/sources/reports/discovery.json
  │   (Uses `GITHUB_TOKEN` / `GH_TOKEN` when present, otherwise should reuse local `gh` authentication)
  ├── Additionally search manually via:
  │   ├── npx skills find "<keyword>"          (skills.sh)
  │   ├── clawhub search "<keyword>"           (ClawHub)
  │   ├── web_search for GitHub trending repos with SKILL.md
  │   └── Check watched repos: alirezarezvani/claude-skills, opera/superpowers
  └── Collect: skill name, source URL, description, quality indicators

Step 2: EVALUATE — Score and filter candidates
  ├── Dedup against existing skills: compare with skills/*/*/SKILL.md directory names
  ├── Quality criteria (must meet ALL):
  │   ├── Content depth: original SKILL.md ≥ 50 lines (or you will expand it)
  │   ├── Practical value: contains actionable guidance, not just descriptions
  │   ├── Non-overlapping: does not duplicate an existing skill's coverage
  │   └── Well-scoped: focused on one domain, not a vague meta-skill
  ├── License criteria for external skills (must meet ALL):
  │   ├── Check upstream repo license via `gh api repos/<owner>/<repo> --jq .license`
  │   ├── Accept only permissive licenses allowed by `scripts/audit_licenses.py`
  │   ├── Record the accepted license in `SKILL.md` frontmatter
  │   └── If license is missing/unknown and the candidate is high quality, auto-generate an original `in-house` MIT rewrite; never copy unlicensed upstream text
  └── Assign recommended category from the 16 existing categories (see §Categories)

Step 3: INGEST — Download and add to repository
  ├── For each approved skill:
  │   ├── Download SKILL.md from source (GitHub raw URL, skills.sh, etc.)
  │   ├── Verify license before writing files; for missing/unknown license metadata, write only an original in-house rewrite
  │   ├── If content < 80 lines, expand with professional content to ≥ 100 lines
  │   ├── Ensure these sections exist: Trigger/When to Use, Core Capabilities, Common Patterns (with code blocks), Boundaries
  │   ├── Place in: skills/<category>/<skill-name>/SKILL.md
  │   └── If skill has auxiliary files (templates, configs), include them
  └── Run: python scripts/ingest_skill.py --dir skills/<category>/<skill-name> --source "<source_url>"
       (This auto-enriches frontmatter and updates provenance mapping)

Step 4: PIPELINE — Run full refresh and validation
  ├── python scripts/enrich_frontmatter.py
  ├── python scripts/bootstrap_in_house_sources.py --write-json docs/sources/in-house.skills.json
  ├── python scripts/refresh_repo_views.py
  ├── python scripts/generate_tags_index.py
  ├── python scripts/build_catalog_json.py
  ├── python scripts/check_readme_sync.py
  ├── python scripts/lint_skill_quality.py --min-lines 50
  ├── python scripts/audit_licenses.py
  ├── python -m unittest discover tests -v
  └── git diff --exit-code  (verify generated files are committed)

Step 5: COMMIT & PUSH
  ├── git add -A
  ├── git commit -m "feat: add N new skills from <sources>"
  ├── git push
  └── Prefer a focused PR if the run also includes bulk upstream sync changes
```

### Operation 2: Check & Update Existing Skills (检查并更新现有技能)

**Trigger**: User says "check for updates", "update skills", "检查更新", "同步最新" or similar.

**Procedure**:

```
Step 1: CHECK UPSTREAM — Scan for updated skills
  ├── Run: python scripts/sync_upstream.py --check-only
  │   (Reads docs/sources/in-house.skills.json, checks upstream repos for new commits, and should reuse local `gh` auth if env tokens are absent)
  └── Output: list of skills with available updates and their diffs

Step 2: APPLY UPDATES
  ├── Run: python scripts/sync_upstream.py --apply
  │   (Downloads latest SKILL.md from upstream, replaces local, updates metadata)
  ├── For each updated skill:
  │   ├── Preserve local frontmatter enrichments (tags, quality, etc.)
  │   ├── Update: updated_at, version (bump patch)
  │   ├── Verify content quality after merge
  │   └── If upstream becomes too thin for repository standards, add a local quality supplement instead of reverting the upstream body wholesale
  └── If conflicts exist, prefer upstream content but keep local frontmatter

Step 3: QUALITY CHECK
  ├── python scripts/lint_skill_quality.py --min-lines 50
  ├── Fix WARN/FAIL items caused by repository quality policy in the same branch
  └── Record external-state blockers separately (e.g. raw-path `404`, GitHub API `403 rate limit exceeded`)

Step 4: PIPELINE — Same as Operation 1, Step 4

Step 5: COMMIT & PUSH
  ├── git add -A
  ├── git commit -m "chore: sync upstream updates for N skills"
  └── git push
```

### Operation 3: Combined — Discover + Update (搜集新技能并更新旧技能)

**Trigger**: User says "add new and update existing", "全面更新", "搜集新的并更新旧的" or similar.

**Procedure**: Execute Operation 2 first (update existing), then Operation 1 (add new). This ensures the baseline is current before adding new skills.

**Preferred PR strategy**:

- PR 1: small, focused additions or warning fixes
- PR 2: bulk upstream sync
- Merge only after each PR has passed the local full pipeline cleanly

---

## Categories (16 total)

| Category Directory | Description | Example Skills |
|---|---|---|
| `developer-engineering` | Programming languages, frameworks, dev tools | kubernetes-specialist, nextjs-app-router, rust-engineer |
| `ai-workflow` | Agent workflows, planning, context engineering, review, verification | context-engineering, agent-workflow-designer, test-driven-development |
| `ai-agent-platform` | Agent platforms, orchestration, MCP, memory systems | agent-hub, hermes-agent, self-improving-agent |
| `engineering-workflow-automation` | Git workflows, CI/CD automation, browser testing, code generation | yeet, gh-fix-ci, playwright |
| `devops-sre` | Infrastructure, CI/CD, monitoring, reliability | senior-devops, senior-architect |
| `finance-investing` | Financial analysis, trading, portfolio management | financial-analyst, saas-metrics-coach |
| `growth-operations-xiaohongshu` | Marketing, SEO, social media, growth | seo-audit, campaign-manager |
| `office-white-collar` | Document processing, spreadsheets, presentations, office workflows | spreadsheet, pptx, docx |
| `knowledge-and-pm-integrations` | Knowledge bases and project-management integrations | notion-spec-to-implementation, linear, obsidian |
| `operations-general` | Productivity, search, communication, utilities | confidence-check, fact-checker |
| `product-design` | UX/UI, product management, design systems | figma, ux-researcher-designer |
| `security-and-reliability` | Security auditing, compliance, threat modeling | security-best-practices, skill-security-auditor |
| `multimodal-media` | Images, speech, video, screenshots, summaries, transcription | imagegen, sora, transcribe |
| `deployment-platforms` | Platform-specific deployment guides | cloudflare-workers, vercel |
| `openclaw-memory-and-safety` | Memory, input guards, RAG, runbooks | honcho, input-guard, rag-architect |
| `task-understanding-decomposition` | Task understanding support, live search, reflection | tavily-search, reflect-learn |

**Category selection rules**:
- Match primary function, not secondary use case
- If a skill spans two categories, choose the one with fewer skills to balance distribution
- If uncertain, use `operations-general` as default

---

## Frontmatter Schema (Required)

Every `SKILL.md` must have this frontmatter:

```yaml
---
name: skill-name                    # Must match directory name
description: "One-line description" # Quoted if contains special chars
version: "1.0.0"                    # Semver
author: seaworld008                 # Contributor GitHub ID
source: in-house                    # in-house | skills.sh | clawhub | github:<owner>/<repo> | community
source_url: ""                      # Original URL if from external source
license: MIT                        # Required for every external source; omit only for in-house
tags: [tag1, tag2, tag3]            # Cross-category searchable tags
created_at: "2026-03-27"            # YYYY-MM-DD
updated_at: "2026-03-27"            # YYYY-MM-DD
quality: 4                          # 1-5 (1=stub, 3=acceptable, 5=best-in-class)
complexity: intermediate            # beginner | intermediate | advanced
---
```

## Quality Standards

| Rating | Lines | Requirements |
|--------|-------|-------------|
| 5 (Best) | ≥200 | Comprehensive guide with multiple code examples, edge cases, anti-patterns |
| 4 (Good) | ≥100 | Solid coverage with code examples and practical templates |
| 3 (OK) | ≥80 | Basic coverage with at least 1 code block |
| 2 (Thin) | ≥50 | Minimal viable content, needs expansion |
| 1 (Stub) | <50 | Placeholder only — should not be committed |

**Minimum for commit**: quality ≥ 2, lines ≥ 50

---

## Script Reference

| Script | Purpose | When to Run |
|--------|---------|-------------|
| `discover_new_skills.py` | Search GitHub/skills.sh/ClawHub for new skills | Operation 1, Step 1 |
| `ingest_skill.py` | Register a new skill's provenance and enrich metadata | Operation 1, Step 3 |
| `sync_upstream.py` | Check and apply upstream updates | Operation 2 |
| `enrich_frontmatter.py` | Auto-fill missing frontmatter fields | After any skill addition |
| `bootstrap_in_house_sources.py` | Regenerate provenance mapping | After any skill addition |
| `refresh_repo_views.py` | Regenerate category READMEs + openclaw export | After any change |
| `generate_tags_index.py` | Regenerate docs/TAGS-INDEX.md | After any change |
| `build_catalog_json.py` | Regenerate docs/catalog.json and README banner | After any change |
| `generate_repo_banner.py` | Regenerate .github/assets/repo-banner.svg from docs/catalog.json | Usually via build_catalog_json.py |
| `check_readme_sync.py` | Verify Chinese and English READMEs match the skill tree | After README or skill list changes |
| `lint_skill_quality.py` | Quality gate check | Before commit |
| `audit_licenses.py` | License gate for external skills | Before commit |
| `generate_changelog.py` | Auto-generate CHANGELOG.md | Before release |

### One-liner: Full Pipeline

```bash
python scripts/enrich_frontmatter.py && \
python scripts/bootstrap_in_house_sources.py --write-json docs/sources/in-house.skills.json && \
python scripts/refresh_repo_views.py && \
python scripts/generate_tags_index.py && \
python scripts/build_catalog_json.py && \
python scripts/check_readme_sync.py && \
python scripts/lint_skill_quality.py --min-lines 50 && \
python scripts/audit_licenses.py && \
python -m unittest discover tests -v
```

Windows (PowerShell):
```powershell
python scripts/enrich_frontmatter.py; python scripts/bootstrap_in_house_sources.py --write-json docs/sources/in-house.skills.json; python scripts/refresh_repo_views.py; python scripts/generate_tags_index.py; python scripts/build_catalog_json.py; python scripts/check_readme_sync.py; python scripts/lint_skill_quality.py --min-lines 50; python scripts/audit_licenses.py; python -m unittest discover tests -v
```
