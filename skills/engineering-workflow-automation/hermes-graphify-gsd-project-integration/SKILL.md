---
name: hermes-graphify-gsd-project-integration
description: 'Use when integrating Hermes Agent, graphify, and GSD into a specific repository, especially for adding project-local graph refresh scripts, AGENTS.md guidance, README workflow docs, gitignore entries, and a brownfield-friendly planning loop without modifying upstream tool repositories.'
version: "1.3.0"
author: Hermes Agent
source: "in-house"
source_url: "https://github.com/seaworld008/Commonly-used-high-value-skills"
tags: '["automation", "workflow", "hermes", "graphify", "gsd", "repo-integration", "planning", "brownfield"]'
created_at: "2026-04-16"
updated_at: "2026-04-16"
quality: 5
complexity: "intermediate"
license: MIT
metadata:
  hermes:
    tags: [hermes, graphify, gsd, repo-integration, planning, project-workflow, brownfield]
    companion_skill: hermes-graphify-gsd-nonintrusive-workflow
---

# Hermes + graphify + GSD Project Integration

## Overview

Use this skill to integrate Hermes, graphify, and GSD into one specific repository.

This is the repo-level companion to `hermes-graphify-gsd-nonintrusive-workflow`.
- The companion skill defines the upgrade-safe architecture and wrapper strategy
- This skill applies that strategy inside a project
- If the repo is already integrated and the current task is runtime diagnosis or writer/operator recovery, switch to `hermes-graphify-gsd-runtime-operator`

Observed repo-level outputs from this skill typically include:
- local GSD Codex runtime bootstrap (`.codex/`)
- graphify outputs (`graphify-out/`)
- workflow scripts and docs

`.planning/` may remain absent unless another bootstrap step is run deliberately.
- This skill is meant to run on machines where Hermes is already installed and network access is available.
- If `hermes` is missing, stop and ask the user to install Hermes first.
- Do not auto-install Hermes from this skill.
- Before repo-level integration, automatically install or upgrade the latest graphify and GSD globally.

## When to Use

Use this skill when the user asks to:
- add Hermes + graphify + GSD workflow to a repo
- bootstrap a brownfield repo for graph-aware planning
- add `graphify-sync.sh`, `ai-workflow.sh`, `.planning/`, or `.codex/` workflow guidance
- update repo docs so future agents understand the workflow
- standardize AGENTS.md / README / .gitignore for AI development

Do not use this skill for upstream tool development. Use the upstream repo directly for that.

## Expected Repo Outputs

A successful integration usually leaves the repo with:
- `scripts/graphify-sync.sh`
- optional `scripts/ai-workflow.sh`
- `AGENTS.md` workflow section
- `README.md` workflow section
- `.gitignore` entries for `.planning/` and `graphify-out/`
- existing or verified `.codex/`
- existing or refreshed `graphify-out/`

Important boundary:
- this skill does not guarantee automatic creation of `.planning/`
- if the repo needs a fresh or manual brownfield planning baseline, delegate that step to `gsd-graphify-brownfield-bootstrap`

## Reality-tested repo contract
For repos that also use autonomous continuation, prefer these repo-level defaults:
- the **main project repo** should be the primary writer execution surface
- do not default to a sandbox/worktree as the canonical writer just because it feels safer
- only promote an extra worktree into runtime if it is rebuilt into a complete project environment and explicitly becomes the primary root

At repo level, expose and verify:
- `./scripts/ai-workflow.sh doctor`
- `./scripts/ai-workflow.sh auto-progress`
- `./scripts/ai-workflow.sh auto-runner-show`
- `./scripts/ai-workflow.sh auto-execution-surface-show`

For any repo allowed to write, prefer an execution-surface guard requiring at least:
- `package.json`
- `pnpm-lock.yaml`
- `src-tauri/` or the repo's real backend root
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`
- executable `scripts/graphify-sync.sh`

If the repo adopts a primary-root writer contract, runtime-binding commands should only succeed when the current repo reports `writer_recommended=yes`.

## Standard Integration Steps

### 0. Ensure global toolchain first
Before touching the repo:
1. Check `command -v hermes`
2. If Hermes is missing, stop and ask for manual Hermes installation
3. If Hermes exists, automatically install or upgrade graphify globally:
   ```bash
   PY_BIN="${PYTHON_BIN:-$HOME/.hermes/hermes-agent/venv/bin/python3}"
   [ -x "$PY_BIN" ] || PY_BIN="$(command -v python3)"
   if "$PY_BIN" -c 'import sys; print(int(sys.prefix != sys.base_prefix))' 2>/dev/null | grep -q '^1$'; then
     "$PY_BIN" -m pip install -U graphifyy
   else
     "$PY_BIN" -m pip install --user -U graphifyy
   fi
   ~/.local/bin/graphify install --platform hermes || graphify install --platform hermes
   ```
4. Then automatically install or upgrade GSD globally:
   ```bash
   npx -y get-shit-done-cc@latest --codex --global --sdk
   ```
5. If graphify still warns about an older skill version after Hermes install, inspect other installed platform targets under the home directory (for example `claude`) and update them too:
   ```bash
   graphify install --platform claude
   graphify install --platform hermes
   ```
6. Only after the global toolchain is ready should repo integration begin

### 1. Audit the repo
Check for:
- `AGENTS.md`
- `README.md`
- `scripts/`
- `.planning/`
- `.codex/`
- `graphify-out/`
- git hook status

### 2. Add graph refresh script
Prefer a project-local `scripts/graphify-sync.sh`.

Required modes:
- `status`
- `smart`
- `force`
- `serve`

Behavior guidance:
- detect a Python interpreter that can import `graphify`
- use code-only rebuild for code changes when possible
- fallback to full `graphify update .` when outputs are missing
- treat `graphify-out/graph.json` and `graphify-out/GRAPH_REPORT.md` as the required outputs
- do not require `manifest.json`; newer graphify versions may not emit it
- skip automatic rebuild when only docs/media changed

### 3. Add optional unified repo entrypoint
If the repo benefits from a single entrypoint, add `scripts/ai-workflow.sh`.

Use it to:
- check tool availability
- show recommended reading order
- trigger graph sync
- print the repo's standard iteration loop
- expose operator/runtime diagnostics such as `auto-status`, `auto-progress`, `auto-runner-show`, `auto-execution-surface-show`, `auto-workflow-state-show`, and `auto-handoff-show`

If the user wants **autonomous continuation** rather than only repo integration:
- also add the repo-local auto-continue script family from the companion workflow skill
- make the trigger prompt self-contained because Hermes cron runs in fresh sessions
- prefer a multi-pass per-trigger loop so the runtime does not stop after one small task when more scoped work remains
- use a project-specific cron tag / schedule instead of one shared global tag string
- add or normalize a machine-readable task board such as `.planning/task-board.json`
- expose task-board operator commands so humans and agents can inspect next actionable work

### 4. Update AGENTS.md
Add or refine a workflow section covering:
- GSD local runtime location
- graphify output location
- required pre-read files like `graphify-out/GRAPH_REPORT.md`
- preferred post-change sync command
- treatment of `.planning/` and `graphify-out/` as local workflow artifacts

### 5. Update README.md
Add a concise workflow section for humans:
- what GSD is used for
- what graphify is used for
- which commands to run
- what docs to read next

### 6. Update .gitignore
Recommended defaults:
```gitignore
.planning/
graphify-out/
```

### 7. Verify end-to-end
Run real checks before claiming completion.

### 7. Planning bootstrap is a separate decision
If `.planning/` already exists, verify and reuse it.

If `.planning/` does not exist and the repo needs a real brownfield planning baseline:
- do not pretend this repo-integration skill alone fully solves planning bootstrap
- delegate to `gsd-graphify-brownfield-bootstrap`
- then return to this skill for workflow docs/script verification if needed

If `.planning/` exists but `REQUIREMENTS.md` is missing and the user wants autonomous continuation:
- add or normalize `REQUIREMENTS.md`
- make sure `ROADMAP.md` and `STATE.md` reference the same active scope
- ensure the runtime prompt can recover the next highest-priority unfinished requirement from those files

If the repo uses a machine-readable task board:
- prefer the board as the canonical next-task selector
- keep it aligned with `REQUIREMENTS.md`, `ROADMAP.md`, and `STATE.md`
- the runtime should continue `in_progress` tasks first, then choose the highest-priority executable `todo`
- expose operator commands for claim-next and task status transitions so humans can safely intervene without editing JSON by hand
- prefer a lightweight `complete-if-ready` gate before changing task status to `done`
- sync task board changes back into managed sections of `STATE.md` / `ROADMAP.md` so human-readable docs stay aligned with runtime truth

## Brownfield Guidance

For existing repos:
- do not force `gsd-sdk init` if credentials/model access are unavailable
- manually seed `.planning/` from repo facts if needed
- prefer graphify-first architecture recall before planning big refactors
- document the current state before trying to redesign the system

## Verification Checklist

Run as many of these as applicable:

```bash
command -v hermes
hermes --version
command -v graphify
graphify --help
command -v gsd-sdk
gsd-sdk --version
./scripts/graphify-sync.sh status
./scripts/graphify-sync.sh smart
./scripts/ai-workflow.sh doctor
./scripts/ai-workflow.sh context
find .planning -maxdepth 3 -type f | sort
find .codex -maxdepth 3 -type f | sort | sed -n '1,40p'
```

Also verify:
- Hermes was preinstalled rather than auto-installed by this skill
- graphify was globally installed and integrated for Hermes
- if graphify warns about an older skill version, any other installed platform targets were also updated as needed
- GSD was globally installed with `--sdk`
- git hooks exist if graphify hooks are part of the contract
- `graphify-out/GRAPH_REPORT.md` exists
- AGENTS.md and README.md mention the workflow clearly
- if the repo exposes autonomous runtime commands, `doctor` / `auto-progress` / `auto-runner-show` agree on the current writer facts
- if the repo uses a primary-root contract, `auto-execution-surface-show` reports `writer_recommended=yes` only on the intended main repo
- if the repo exposes autonomous continuation, one trigger is allowed to run multiple internal passes before yielding back to cron/timer

## Common Pitfalls

1. Overfitting the integration to one repo layout
- keep paths configurable where possible

2. Forgetting documentation
- future agents need AGENTS.md and README hints, not just scripts

3. Treating graphify semantic refresh and code refresh as the same thing
- use cheap code refresh by default
- reserve full rebuilds for when they are actually needed

4. Claiming integration is done without live verification
- always run the scripts you added

5. Assuming `graphify hook install` always works inside a git worktree
- in git worktrees, `.git` is often a file, not a directory
- `graphify hook install` may fail with `NotADirectoryError` on `.git/hooks`
- install hooks from the primary checkout, or treat hook installation as optional during isolated worktree testing

6. Misreading graphify version warnings as a failure of the current platform only
- graphify may scan multiple installed platform directories and warn if any of them are stale
- a stale Claude-side graphify install can keep warning even after Hermes-side install is current
- update all installed graphify platform targets you actually use before treating it as a broken Hermes integration

7. Leaving stale sandbox cron/state/lease artifacts active after moving back to main-repo single-writer mode
- check both `hermes cron list --all` and system `crontab -l`
- if observed writer metadata points at an unexpected worktree, inspect live PIDs and cron tags before assuming the runtime is healthy
- after removing a stale sandbox writer, reconcile state/lease files so `auto-runner-show` and `auto-progress` return to `inactive` or the real current writer

## Bundled Files

Load these when implementing repo integration:
- `templates/bootstrap-toolchain.sh`
- `templates/graphify-sync.sh`
- `templates/ai-workflow.sh`
- `templates/agents-section.md`
- `templates/readme-section.md`
- `references/first-install.md`
- `references/integration-checklist.md`

## Execution Pattern

When using this skill:
1. check Hermes prerequisite first
2. if Hermes is missing, stop and ask the user to install Hermes manually
3. if Hermes exists, install or upgrade latest graphify and GSD globally
4. inspect the repo
5. reuse existing workflow files if already present
6. add only the missing thin integration layer
7. verify with real commands
8. if the repo includes autonomous continuation, verify that `scripts/ai-workflow.sh` exposes the same auto-* operator commands documented by the companion skills
9. document the workflow for both agents and humans
