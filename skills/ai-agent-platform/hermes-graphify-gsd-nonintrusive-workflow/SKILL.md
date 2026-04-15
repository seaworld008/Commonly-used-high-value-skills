---
name: hermes-graphify-gsd-nonintrusive-workflow
description: 'Use when integrating Hermes Agent, graphify, and GSD into a local development workflow without modifying upstream repositories, especially when the user wants upgrade-safe wrappers, project-level workflow scripts, graph-aware planning, and a reusable setup that survives future upstream updates.'
version: "1.0.0"
author: Hermes Agent
source: "in-house"
source_url: "https://github.com/seaworld008/Commonly-used-high-value-skills"
tags: '["ai", "agent", "hermes", "graphify", "gsd", "workflow", "non-intrusive", "upgrade-safe"]'
created_at: "2026-04-15"
updated_at: "2026-04-15"
quality: 5
complexity: "intermediate"
license: MIT
related_repos: '["https://github.com/NousResearch/hermes-agent", "https://github.com/safishamsi/graphify", "https://github.com/gsd-build/get-shit-done"]'
---

# Hermes + graphify + GSD Non-Intrusive Workflow

## Overview

Use this skill to build an upgrade-safe local AI development workflow that combines:
- Hermes Agent for orchestration, memory, and execution
- graphify for codebase graph recall and low-cost refresh
- GSD for planning, phase management, and execution cadence

Core rule: do not modify upstream Hermes, graphify, or GSD repository code unless the user explicitly wants to contribute upstream. Prefer thin wrappers, project-local scripts, and repo documentation.

Important prerequisite:
- This skill assumes Hermes is already installed in an online-capable environment.
- If `hermes` is missing, stop and ask the user to install Hermes first.
- Do not auto-install Hermes from this skill.
- However, on first-time bootstrap, this skill should automatically install or upgrade the latest graphify and GSD, then configure them globally.

## When to Use

Use this skill when the user asks for any of these:
- "把 Hermes + graphify + GSD 接起来"
- non-intrusive integration
- upgrade-safe local AI coding workflow
- reusable project bootstrap for graph-aware planning
- wrappers around Hermes / graphify / GSD instead of patching upstream
- project-level workflow entrypoints like `ai-workflow.sh`

Do not use this skill when the user wants to directly change Hermes, graphify, or GSD upstream source behavior. In that case, work in the relevant upstream repo instead.

## Design Principles

1. Non-intrusive first
- Do not patch Hermes upstream repo for local workflow glue
- Do not patch installed graphify package for convenience
- Do not patch GSD installer/source just to fit one project

2. Depend on stable entrypoints
Prefer these interfaces:
- `hermes`
- `python -m graphify`
- `node <get-shit-done>/sdk/dist/cli.js`

3. Keep adaptation thin
Allowed adaptation layers:
- shell wrappers in `~/.local/bin/`
- repo-local scripts under `scripts/`
- docs in `README.md`, `AGENTS.md`, `docs/`
- local gitignored workflow state like `.planning/` and `graphify-out/`

4. Make upgrade cost local
If upstream changes, update wrappers/templates first. Avoid spreading compatibility logic across many repos.

## Recommended Architecture

### Layer 1 — upstream tools
- Hermes installation and config
- graphify Python package / CLI entrypoint
- GSD runtime and SDK installation

### First-time bootstrap policy
When this skill is used on a fresh machine:
1. Check `command -v hermes`
2. If Hermes is missing, stop and instruct the user to install Hermes manually first
3. If Hermes exists, automatically install or upgrade graphify and GSD to latest stable upstream entrypoints
4. Configure graphify globally for Hermes
5. Configure GSD globally for the target runtime, defaulting to Codex unless the user specifies another runtime

Recommended commands:

```bash
# graphify — latest package, then global Hermes integration
# prefer a Python that actually has pip available; Hermes venv python is a valid fallback
PY_BIN="${PYTHON_BIN:-$HOME/.hermes/hermes-agent/venv/bin/python3}"
[ -x "$PY_BIN" ] || PY_BIN="$(command -v python3)"
if "$PY_BIN" -c 'import sys; print(int(sys.prefix != sys.base_prefix))' 2>/dev/null | grep -q '^1$'; then
  "$PY_BIN" -m pip install -U graphifyy
else
  "$PY_BIN" -m pip install --user -U graphifyy
fi
~/.local/bin/graphify install --platform hermes || graphify install --platform hermes

# GSD — latest global runtime + SDK
npx -y get-shit-done-cc@latest --codex --global --sdk
```

Notes:
- graphify's current PyPI package name is `graphifyy`, while the CLI remains `graphify`
- graphify version warnings are global across installed platforms, not Hermes-only; if `graphify --help` still warns after updating Hermes, also check other installed platform copies such as `~/.claude/skills/graphify/.graphify_version` and rerun `graphify install --platform <platform>` there
- for GSD, `--codex --global --sdk` is the default global baseline for this workflow; choose another runtime only when the user explicitly wants it
- if a repo also needs local `.codex/` files, do a second repo-local install later during project integration

### Layer 2 — local wrappers
Create thin wrappers when needed:
- `~/.local/bin/graphify`
- `~/.local/bin/gsd-sdk`

Purpose:
- normalize invocation
- discover interpreters/paths
- avoid upstream edits

### Layer 3 — project integration
Per repo, add:
- `scripts/graphify-sync.sh`
- optional `scripts/ai-workflow.sh`
- `AGENTS.md` guidance
- `README.md` workflow section
- `.gitignore` entries for `.planning/` and `graphify-out/`

## Minimum Verification Checklist

Run these before claiming success:

```bash
command -v hermes
hermes --version

command -v graphify
graphify --help

command -v gsd-sdk
gsd-sdk --version

./scripts/graphify-sync.sh status
./scripts/graphify-sync.sh smart
```

For first-time bootstrap, also verify:
- `hermes` existed before any automation began
- graphify was installed or upgraded via the selected Python + pip flow
- graphify global Hermes integration was applied with `graphify install --platform hermes`
- if graphify still warns about an older skill version, inspect other installed platform targets (for example `~/.claude/skills/graphify/.graphify_version`) and update those too
- GSD global install was applied with `npx -y get-shit-done-cc@latest --codex --global --sdk`

Also verify:
- `.planning/` exists when planning context is expected
- `.codex/` exists if local GSD runtime is used
- `graphify-out/graph.json` and `graphify-out/GRAPH_REPORT.md` exist after graph build
- git hooks exist if graphify hook automation is expected

## Standard Project Operating Loop

1. `./scripts/graphify-sync.sh smart`
2. Read `graphify-out/GRAPH_REPORT.md`
3. Read `.planning/STATE.md` and `.planning/ROADMAP.md`
4. Use GSD phase / plan / execute workflow
5. Implement changes
6. Re-run `./scripts/graphify-sync.sh smart`
7. Update planning context if the phase meaning changed

Best division of labor:
- Hermes = orchestration and persistence
- graphify = architecture recall and code graph refresh
- GSD = planning cadence and execution structure

## Upgrade Contract

Always preserve these constraints:
- wrappers may change
- repo-local scripts may change
- project docs may change
- user-level installed platform copies of a skill may need resync across multiple runtimes
- upstream repos should remain untouched unless upstream contribution is the actual task

If something breaks after upstream updates, fix in this order:
1. wrapper path detection
2. wrapper invocation contract
3. project-local script assumptions
4. only then consider upstream changes

## Common Pitfalls

1. Treating one repo's path layout as universal
- make wrapper paths configurable with env vars where reasonable

2. Depending on one pip install mode everywhere
- virtualenv Python may reject `--user`
- system Python may need `--user`
- detect whether the chosen interpreter is in a venv, then choose `pip install -U ...` or `pip install --user -U ...` accordingly

3. Depending on graphify outputs that are no longer stable across versions
- current graphify versions reliably produce `graphify-out/graph.json` and `graphify-out/GRAPH_REPORT.md`
- do not require `manifest.json` unless you have verified that a specific version still emits it
- wrappers and sync scripts should treat manifest as optional

4. Misreading graphify version warnings as Hermes-only failures
- graphify scans multiple installed platform skill directories when checking installed skill versions
- an outdated `~/.claude/skills/graphify/.graphify_version` can trigger a warning even when `~/.hermes/skills/graphify/` is current
- if warning persists, update every installed graphify platform target you actually use

5. Mixing project-specific guidance into the generic skill body
- put reusable logic in this skill
- put project-specific facts in repo docs or AGENTS.md

## Files to Reuse

Load these bundled files when implementing:
- `templates/bootstrap-toolchain.sh`
- `templates/graphify-wrapper.sh`
- `templates/gsd-sdk-wrapper.sh`
- `templates/ai-workflow.sh`
- `references/first-install.md`
- `references/upgrade-contract.md`

## Execution Pattern

When using this skill:
1. Audit live tool availability first
2. If Hermes is missing, stop and instruct manual Hermes installation — do not auto-install it
3. If Hermes exists, automatically install or upgrade latest graphify and GSD globally
4. Add wrappers only if the native commands are missing or inconsistent after install
5. Add project-local scripts second
6. Verify the full loop with real commands
7. Document the contract so future upgrades stay safe
