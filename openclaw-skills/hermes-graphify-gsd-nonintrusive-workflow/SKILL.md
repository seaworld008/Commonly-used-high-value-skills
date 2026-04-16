---
name: hermes-graphify-gsd-nonintrusive-workflow
description: 'Use when integrating Hermes Agent, graphify, and GSD into a local development workflow without modifying upstream repositories, especially when the user wants upgrade-safe wrappers, project-level workflow scripts, graph-aware planning, and a reusable setup that survives future upstream updates.'
version: "1.4.0"
author: Hermes Agent
source: "in-house"
source_url: "https://github.com/seaworld008/Commonly-used-high-value-skills"
tags: '["ai", "agent", "hermes", "graphify", "gsd", "workflow", "non-intrusive", "upgrade-safe"]'
created_at: "2026-04-16"
updated_at: "2026-04-16"
quality: 5
complexity: "intermediate"
license: MIT
metadata:
  hermes:
    tags: [hermes, graphify, gsd, workflow, non-intrusive, upgrade-safe, wrappers, planning]
    github_repos:
      - https://github.com/NousResearch/hermes-agent
      - https://github.com/safishamsi/graphify
      - https://github.com/gsd-build/get-shit-done
---

# Hermes + graphify + GSD Non-Intrusive Workflow

## Overview

Use this skill to build an upgrade-safe local AI development workflow that combines:
- Hermes Agent for orchestration, memory, and execution
- graphify for codebase graph recall and low-cost refresh
- GSD for planning, phase management, and execution cadence

If the repo already has this workflow and the task is now about **runtime diagnosis, writer ownership, stale cron/state/lease cleanup, or handoff/operator recovery**, switch to `hermes-graphify-gsd-runtime-operator`.

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

### Optional Layer 4 — autonomous continuation loop
When the user wants the repo to keep advancing with minimal manual prompting, add a repo-local auto-continue layer:
- lightweight Git hooks for event triggers (`post-commit`, optionally `post-merge`)
- a periodic reconciler (`cron` or systemd timer) that re-checks progress every N minutes
- a single-runner lock to prevent concurrent agent executions
- a project-level completion sentinel written only after full verification succeeds
- evidence docs that record the final verification command and output

Recommended responsibilities:
- **hook**: only enqueue or trigger; keep it lightweight
- **cron/timer**: watchdog + periodic reconciliation; restart the runner if needed
- **runner**: read planning/graph context, continue work, update docs, run focused verification, and only attempt final completion when the project is actually done
- **per-trigger loop**: let one trigger run multiple internal passes before giving up, so the workflow does not stop after one small task when more scoped work remains
- **completion gate**: a dedicated script that runs the full verification command and writes the sentinel/evidence only on success

Recommended repo-local files:
- `scripts/hermes-auto-continue-config.sh`
- `scripts/hermes-auto-continue-status.sh`
- `scripts/hermes-auto-continue-trigger.sh`
- `scripts/hermes-auto-continue-checkpoint.sh` (manual no-commit checkpoint trigger)
- `scripts/hermes-auto-continue-summary.sh` (generate the last-run summary artifact)
- `scripts/hermes-auto-continue-task-board-init.sh`
- `scripts/hermes-auto-continue-task-board-status.sh`
- `scripts/hermes-auto-continue-task-board-update.sh`
- `scripts/hermes-auto-continue-task-board-complete-if-ready.sh`
- `scripts/hermes-auto-continue-task-board-sync-docs.sh`
- `scripts/hermes-auto-continue-mark-complete.sh`
- `scripts/install-hermes-auto-continue-cron.sh`
- `.husky/post-commit`
- optional `.husky/post-merge`

Recommended optional relay artifacts:
- `.planning/auto-continue-last-summary.md`
- `.planning/task-board.json`
- optional explicit delivery env vars such as:
  - `HERMES_AUTO_CONTINUE_NOTIFY_DELIVER`
  - `HERMES_AUTO_CONTINUE_NOTIFY_SCHEDULE`
- recommended runtime tuning env vars such as:
  - `HERMES_AUTO_CONTINUE_MAX_PASSES_PER_TRIGGER`
  - `HERMES_AUTO_CONTINUE_PASS_IDLE_SECONDS`
  - `HERMES_AUTO_CONTINUE_CRON_SCHEDULE`

### Reality-tested runtime contract
When this workflow grows into an autonomous repo-local runtime, prefer these additional constraints by default:
- **main project repo = primary writer execution surface**
- do not assume a separate sandbox/worktree should be the canonical writer
- treat extra worktrees as read-only analysis or temporary experiments unless they are rebuilt into a complete project environment and explicitly promoted

Recommended operator contract:
- maintain a project-level writer lease, state file, handoff file, and planning mirror under a shared state dir
- expose a repo-local doctor/operator surface such as:
  - `./scripts/ai-workflow.sh doctor`
  - `./scripts/ai-workflow.sh auto-status`
  - `./scripts/ai-workflow.sh auto-progress`
  - `./scripts/ai-workflow.sh auto-runner-show`
  - `./scripts/ai-workflow.sh auto-execution-surface-show`
  - `./scripts/ai-workflow.sh auto-workflow-state-show`
  - `./scripts/ai-workflow.sh auto-handoff-show`
- the bundled `templates/ai-workflow.sh` in this skill now exposes those subcommands and delegates to the repo-local auto-continue scripts
- use the operator commands as the primary fact source before assuming the runtime is healthy

Recommended execution-surface guard for any repo allowed to write:
- require at least:
  - `package.json`
  - `pnpm-lock.yaml`
  - `src-tauri/` or the repo's real backend root
  - `.planning/STATE.md`
  - executable `scripts/graphify-sync.sh`
- `doctor`, `trigger`, and cron/timer install paths should all refuse to proceed on an incomplete execution surface
- if temporary experiments must bypass the guard, require an explicit override env var and treat it as an exception path, not the normal workflow

Recommended writer-surface contract:
- define a **primary root** for the project
- compute and expose:
  - `writer_eligible`
  - `primary_root_match`
  - `writer_recommended`
- only allow runtime-binding commands or cron installation on `writer_recommended=yes`

Core rule:
- **Do not stop because one small task or one local checklist is done.**
- Stop only when a project-level completion sentinel exists and still matches the current HEAD/worktree state.

Recommended machine-readable planning contract:
- keep human-readable docs (`PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`)
- also keep a machine-readable task board at `.planning/task-board.json`
- the autonomous runner should prefer:
  1. `in_progress` task
  2. highest-priority executable `todo`
  3. documented fallback to `REQUIREMENTS.md` / `ROADMAP.md` only when the board is missing or stale
- expose task-board operator commands for:
  - initialization
  - current/next task inspection
  - claiming the next task
  - status transitions (`todo`, `in_progress`, `blocked`, `done`, `dropped`)
  - appending notes and acceptance evidence
  - `complete-if-ready` evaluation before marking a task done
  - syncing the machine task board back into managed sections of `STATE.md` and `ROADMAP.md`
- every task should ideally include:
  - `id`
  - `title`
  - `status`
  - `priority`
  - `depends_on`
  - `acceptance`
  - `artifacts`
  - `blocked_by`
  - `last_updated`
- a strong default is: tasks should become `done` only through a lightweight completion gate that checks dependencies, acceptance evidence, and artifact existence

Trigger semantics note:
- The default repo-local auto-continue loop described here is **code-event driven + periodic reconciliation**, not chat-turn driven.
- Typical immediate triggers are: `post-commit`, optional `post-merge`, explicit manual checkpoint scripts, and periodic `cron`/timer reconciliation.
- A strong default is: one trigger may run **multiple internal passes** until completion is reached, a structured handoff becomes active, or the pass budget is exhausted.
- A normal assistant reply ending does **not** automatically create a new trigger event unless your wrapper explicitly does so.
- If the user expects "回复一停就继续跑", add a lightweight non-commit checkpoint trigger (for example `scripts/hermes-auto-continue-checkpoint.sh`) at agreed milestone boundaries rather than assuming message completion will fire hooks.
- If the user also expects autonomous run summaries to return to chat, do **not** assume the local shell knows the current conversation origin. Repo-local scripts run without current-chat delivery context, so reliable auto-delivery requires an **explicit target** (for example `discord:chat_id`, `telegram:chat_id:thread_id`, or another concrete deliver string).
- A practical pattern is: write `.planning/auto-continue-last-summary.md` after each run, then create a one-shot Hermes cron notification job only when an explicit deliver target is configured.
- Hermes cron runs in fresh sessions, so the trigger prompt itself should be self-contained and explicitly tell the runner which local files to read first (`GRAPH_REPORT.md`, `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, and runtime summary/mirror files when present).
- If a machine-readable task board exists, the trigger prompt should explicitly tell the runner to use that board as the canonical next-task selector and to update it after each meaningful step.

## Project-Level Completion Gate

For autonomous continuation loops, use a **completion sentinel** instead of guessing from partial task lists.

Recommended design:
1. The normal runner keeps going by default.
2. When the agent believes the whole scoped project is finished, it runs a dedicated completion script.
3. That script executes the repo's **full verification command**.
4. Only if verification succeeds and the worktree is clean does it write:
   - a sentinel file such as `.planning/auto-continue-complete.json`
   - an evidence doc such as `docs/auto-continue-completion-evidence.md`
5. Status checks should return `COMPLETE` only when:
   - sentinel exists
   - sentinel says `complete`
   - sentinel HEAD matches current HEAD
   - worktree is clean

This avoids the common failure mode where automation stops after a subtask, a phase checklist, or a focused test subset passes.

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
- if the repo uses an autonomous writer runtime, `doctor` / `auto-progress` / `auto-runner-show` all report the same primary writer facts
- if the repo uses a primary-root contract, `auto-execution-surface-show` reports `writer_recommended=yes` only for the intended main repo

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

6. Stopping on partial completion
- do not treat a single phase checklist, one small task, or a focused test subset as project completion
- require a project-level completion sentinel written by a dedicated verification script
- prefer **default continue, not default stop**

7. Letting hooks do long-running work
- hooks should stay lightweight and should not run long autonomous sessions inline
- use hooks to enqueue/trigger and let a runner or cron/timer do the heavy work

8. Missing concurrency control in auto-continue loops
- use a single-runner lock (`flock` or equivalent)
- if you want queue semantics, prefer one running + one pending over unbounded backlog
- periodic reconciliation should recover from stale locks or crashed runners

9. Letting stale cron/state/lease metadata redefine the writer by accident
- `hermes cron list --all` being empty does **not** prove there is no system cron entry
- check system `crontab -l` when the observed writer and the intended writer disagree
- if a stale sandbox/worktree cron is still running, remove the cron entry first, then clear or correct state/lease metadata so operator output returns to the main repo
- if state says `running` but kernel locks are already free, treat it as stale metadata and reconcile it explicitly instead of trusting the stale file forever

10. Using one generic cron tag for every repo
- cron install/uninstall should be keyed by project, not by one shared tag string
- otherwise one repo's install step can silently overwrite another repo's autonomous loop

## Files to Reuse

Load these bundled files when implementing:
- `templates/bootstrap-toolchain.sh`
- `templates/graphify-wrapper.sh`
- `templates/gsd-sdk-wrapper.sh`
- `templates/ai-workflow.sh`
- `templates/hermes-auto-continue-config.sh`
- `templates/hermes-auto-continue-status.sh`
- `templates/hermes-auto-continue-trigger.sh`
- `templates/hermes-auto-continue-checkpoint.sh`
- `templates/hermes-auto-continue-summary.sh`
- `templates/hermes-auto-continue-task-board-init.sh`
- `templates/hermes-auto-continue-task-board-status.sh`
- `templates/hermes-auto-continue-task-board-update.sh`
- `templates/hermes-auto-continue-task-board-complete-if-ready.sh`
- `templates/hermes-auto-continue-task-board-sync-docs.sh`
- `templates/hermes-auto-continue-mark-complete.sh`
- `templates/install-hermes-auto-continue-cron.sh`
- `templates/husky-post-commit-auto-continue.sh`
- `templates/husky-post-merge-auto-continue.sh`
- `references/first-install.md`
- `references/upgrade-contract.md`
- `references/auto-continue-best-practices.md`
- `references/ai-workflow-auto-continue-snippet.md`

## Execution Pattern

When using this skill:
1. Audit live tool availability first
2. If Hermes is missing, stop and instruct manual Hermes installation — do not auto-install it
3. If Hermes exists, automatically install or upgrade latest graphify and GSD globally
4. Add wrappers only if the native commands are missing or inconsistent after install
5. Add project-local scripts second
6. If the user wants autonomous continuation, add the repo-local auto-continue layer with hook + cron/timer + lock + completion gate
7. Verify the full loop with real commands
8. Document the contract so future upgrades stay safe
9. For auto-continue setups, explicitly verify that partial completion does **not** stop the loop and that only the completion sentinel can stop it
10. Verify that the bundled `ai-workflow.sh` surface, auto-continue scripts, and operator docs all expose the same command names before packaging the workflow for teammates
11. Verify that Hermes runner failures become explicit blocked/operator state instead of being silently treated as ordinary incomplete runs
