# Commonly Used High-Value Skills

![Repository Banner](./.github/assets/repo-banner.svg)

[![简体中文](https://img.shields.io/badge/README-%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-1677ff)](./README.md)
[![English](https://img.shields.io/badge/README-English-111111)](./README.en.md)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Compatible-00b894)](./openclaw-skills/README.md)
[![Skills](https://img.shields.io/badge/Skills-139-7c3aed)](./skills/)

A high-value skills repository for AI developers, organized by real work scenarios such as developer engineering, DevOps, automation, finance, design, knowledge workflows, and reliability.

This repository currently contains **15 categories / 139 skills**.

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
- refresh `openclaw-skills/` with `python3 scripts/export_openclaw_skills.py`
- include verification steps in your PR

## If This Repo Helps You

- give it a Star
- share it with AI developers and agent workflow builders
- contribute skills that are truly reusable

## Chinese Main README

The full primary documentation is in Chinese:

- [Open Chinese README](./README.md)
