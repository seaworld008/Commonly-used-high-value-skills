# Commonly Used High-Value Skills

![Repository Banner](./.github/assets/repo-banner.svg)

[![简体中文](https://img.shields.io/badge/README-%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-1677ff)](./README.md)
[![English](https://img.shields.io/badge/README-English-111111)](./README.en.md)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Compatible-00b894)](./openclaw-skills/README.md)
[![Skills](https://img.shields.io/badge/Skills-163-7c3aed)](./skills/)

A high-value skills repository for AI developers, organized by real work scenarios such as developer engineering, DevOps, automation, finance, design, knowledge workflows, and reliability.

This repository currently contains **15 categories / 163 skills**.

## Who This Is For

- AI developers using `Codex`, `Claude Code`, or similar coding assistants
- Teams building reusable skill libraries for common workflows
- OpenClaw users who need a flat exported skill directory
- Builders who want a practical, extensible agent workflow repository instead of a loose prompt collection

## Why It Is Useful

- Skills are organized by scenario, not dumped into a single list
- Many skills include `scripts/`, `references/`, and `assets/`
- The repository supports both categorized source usage and flat OpenClaw export
- It is suitable both for daily usage and long-term team knowledge accumulation
- The repo now supports automated discovery, upstream sync, candidate ranking, quality checks, and generated view refreshes, so it can be maintained as a living skill system rather than a static dump
- Curation is policy-driven: trusted sources can be preferred, noisy sources can be denied, and minimum quality thresholds can be enforced in one place
- `scripts/sync_codex_skills.py` lets you sync the latest repository skills into a local Codex skill directory without manual copying
- The repository also emphasizes trust and safety through provenance tracking, curated source controls, and built-in security-review skills such as `skill-vetter`, `skill-security-auditor`, `input-guard`, and `link-checker`

## Which Directory Should You Use

| Client | Directory |
|--------|-----------|
| `Codex` / `Claude Code` / source-browsing AI coding assistants | `skills/` |
| `OpenClaw` | `openclaw-skills/` |

## Quick Start

1. Clone the repository.
2. If you use OpenClaw, generate the flat export:

```bash
python3 scripts/export_openclaw_skills.py
```

3. Point your AI tool to either `skills/` or `openclaw-skills/`, depending on the client.

If you change source skills in the repository, refresh generated views with:

```bash
python3 scripts/refresh_repo_views.py
```

If Codex shows local skill warnings such as `invalid SKILL.md`, `missing YAML frontmatter`, or broken `metadata`, you can normalize a local Codex skill tree with:

```bash
python3 scripts/normalize_codex_skills.py ~/.codex/skills
```

If you want to sync the latest repository skills into a local Codex skills directory, run:

```bash
python3 scripts/sync_codex_skills.py --source-root ./skills --codex-root ~/.codex/skills
```

## Quick Category Jump Table

| Category | What It Covers | Jump | Folder |
|----------|----------------|------|--------|
| Developer Engineering | Testing, review, performance, architecture, databases | [Jump](./README.md#cat-developer-engineering) | [Folder](./skills/developer-engineering/) |
| DevOps / SRE | Releases, observability, incidents, CI/CD, secrets | [Jump](./README.md#cat-devops-sre) | [Folder](./skills/devops-sre/) |
| Growth Operations | Xiaohongshu, social media, content, attribution, competitor work | [Jump](./README.md#cat-growth-operations) | [Folder](./skills/growth-operations-xiaohongshu/) |
| Finance Investing | Financial data, valuation, risk, backtesting, research writing | [Jump](./README.md#cat-finance-investing) | [Folder](./skills/finance-investing/) |
| Office and Documents | Word, Excel, PPT, PDF, meeting output | [Jump](./README.md#cat-office-white-collar) | [Folder](./skills/office-white-collar/) |
| Memory and Safety | Input guard, RAG, runbooks | [Jump](./README.md#cat-memory-safety) | [Folder](./skills/openclaw-memory-and-safety/) |
| General Operations | Brand, fact-checking, internal comms, themes, weather | [Jump](./README.md#cat-operations-general) | [Folder](./skills/operations-general/) |
| Product and Design | Product analysis, design systems, UX, SaaS scaffolding | [Jump](./README.md#cat-product-design) | [Folder](./skills/product-design/) |
| Task Understanding | Brainstorming, research, plans, skill search | [Jump](./README.md#cat-task-understanding) | [Folder](./skills/task-understanding-decomposition/) |
| AI Platform and Agents | ChatGPT Apps, Figma, OpenAI docs, proactive agents | [Jump](./README.md#cat-ai-agent-platform) | [Folder](./skills/ai-agent-platform/) |
| Workflow Automation | Browser automation, GitHub, notebooks, Playwright | [Jump](./README.md#cat-workflow-automation) | [Folder](./skills/engineering-workflow-automation/) |
| Knowledge and PM Integrations | Notion, Linear, spec-to-implementation | [Jump](./README.md#cat-knowledge-pm) | [Folder](./skills/knowledge-and-pm-integrations/) |
| Deployment Platforms | Cloudflare, Netlify, Render, Vercel | [Jump](./README.md#cat-deployment-platforms) | [Folder](./skills/deployment-platforms/) |
| Multimodal Media | Images, speech, video, screenshots, summaries, transcription | [Jump](./README.md#cat-multimodal-media) | [Folder](./skills/multimodal-media/) |
| Security and Reliability | Sentry, best practices, threat modeling, ownership | [Jump](./README.md#cat-security-reliability) | [Folder](./skills/security-and-reliability/) |

## Recommended Starting Categories

- `developer-engineering`
- `engineering-workflow-automation`
- `finance-investing`
- `knowledge-and-pm-integrations`
- `multimodal-media`
- `security-and-reliability`

## Representative Skills

- `codebase-onboarding`
- `gh-fix-ci`
- `financial-data-collector`
- `portfolio-risk-manager`
- `notion-spec-to-implementation`
- `transcribe`

## Contributing

If you want to help grow this repository:

- read [CONTRIBUTING.md](./CONTRIBUTING.md)
- add or improve skills under `skills/`
- refresh generated views with `python3 scripts/refresh_repo_views.py`
- include verification steps in your PR

## If This Repo Helps You

- give it a Star
- share it with AI developers and agent workflow builders
- contribute skills that are truly reusable

## Chinese Main README

The full primary documentation is in Chinese:

- [Open Chinese README](./README.md)
