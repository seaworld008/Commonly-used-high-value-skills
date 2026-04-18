# Commonly Used High-Value Skills

![Repository Banner](./.github/assets/repo-banner.svg)

[![简体中文](https://img.shields.io/badge/README-%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-1677ff)](./README.md)
[![English](https://img.shields.io/badge/README-English-111111)](./README.en.md)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Compatible-00b894)](./openclaw-skills/README.md)
[![Skills](https://img.shields.io/badge/Skills-188-7c3aed)](./skills/)

A high-value skills repository for AI developers, organized by real work scenarios such as developer engineering, DevOps, automation, finance, design, knowledge workflows, and reliability.

This repository currently contains **15 categories / 188 skills**.

## Who This Is For

- AI developers using `Codex`, `Claude Code`, `Hermes Agent`, or similar coding assistants
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
- The repository now also includes license auditing and scheduled dead-link checks: `repo-validation` blocks external skills that are missing license metadata, while the monthly `dead-links` workflow produces a link health report instead of silently drifting.
- `Hermes Agent` is also treated as a first-class supported client: it uses the same categorized `skills/` tree and already has dedicated Hermes runtime, MCP, and Hermes + graphify + GSD workflow skills in the repository.

## Which Directory Should You Use

| Client | Directory |
|--------|-----------|
| `Codex` / `Claude Code` / `Hermes Agent` / source-browsing AI coding assistants | `skills/` |
| `OpenClaw` | `openclaw-skills/` |

## Quick Start

### Option 1: Give This Prompt to Your AI Tool (Recommended)

If you want your AI tool to install the skills for you, start with this short prompt:

```text
You are my local installation assistant. Please install the skills from this repository into the current AI tool: https://github.com/seaworld008/Commonly-used-high-value-skills
```

If the AI tool cannot infer enough context, add one more line:

```text
The current tool is `<Codex / Claude Code / Hermes Agent / Cursor / OpenClaw>`, and the local repository path is `<your local repo path>`.
```

This works because the repository already includes AI-readable installation rules and directory conventions, so users usually do not need to spell out the full install workflow in the prompt.

### Option 2: Manual Setup

1. Clone the repository.
2. Choose the correct directory for your client:
   - `Codex` / `Claude Code` / `Hermes Agent` / `Cursor` / other source-browsing assistants: use `skills/`
   - `OpenClaw`: use `openclaw-skills/`
3. If you use OpenClaw, generate the flat export first:

```bash
python3 scripts/export_openclaw_skills.py
```

4. Point your AI tool to the correct directory.
5. Verify by opening a few known skills, for example:
   - `skills/developer-engineering/codebase-onboarding`
   - `skills/security-and-reliability/skill-vetter`
   - `openclaw-skills/codebase-onboarding`

### Common Maintenance Commands

If you change source skills in the repository, refresh generated views with:

```bash
python3 scripts/refresh_repo_views.py
```

If you also want to validate external skill license metadata and outbound link health locally, run:

```bash
python3 scripts/audit_licenses.py
python3 scripts/check_dead_links.py --output docs/sources/reports/dead-links.json
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

## Hermes Agent Support

This repository does not just happen to include a few Hermes-related skills. It explicitly supports `Hermes Agent` as one of the maintained consumption targets:

- installation layout matches `Codex` / `Claude Code`, using the categorized `skills/` tree
- it includes the dedicated [`hermes-agent`](./skills/ai-agent-platform/hermes-agent/) skill covering CLI usage, gateway setup, profiles, memory, skills, MCP, and contributor guidance
- it includes [`native-mcp`](./skills/ai-agent-platform/native-mcp/) for Hermes MCP usage
- it includes the `hermes-graphify-gsd-*` workflow skills for graph-aware and autonomous development loops

Recommended starting points for Hermes users:

- [`skills/ai-agent-platform/hermes-agent`](./skills/ai-agent-platform/hermes-agent/)
- [`skills/ai-agent-platform/native-mcp`](./skills/ai-agent-platform/native-mcp/)
- [`skills/ai-agent-platform/README.md`](./skills/ai-agent-platform/README.md)

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
