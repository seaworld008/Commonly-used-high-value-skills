---
name: gsd-graphify-brownfield-bootstrap
description: 'Bootstrap GSD + graphify for an existing brownfield repo when the project needs a single canonical workflow for local runtime setup, graph refresh, and manually seeded .planning/ context without depending on interactive GSD init.'
version: "2.0.0"
author: Hermes Agent
source: "in-house"
source_url: "https://github.com/seaworld008/Commonly-used-high-value-skills"
tags: '["automation", "workflow", "gsd", "graphify", "brownfield", "planning", "architecture", "codex"]'
created_at: "2026-04-16"
updated_at: "2026-04-16"
quality: 5
complexity: "intermediate"
license: MIT
metadata:
  hermes:
    tags: [gsd, graphify, brownfield, codex, planning, architecture, workflow]
    canonical_replacement_for:
      - brownfield-gsd-graphify-bootstrap
---

# GSD + graphify Brownfield Bootstrap

Use this skill when an existing repo needs one canonical brownfield bootstrap flow for:
- local GSD runtime wiring
- graphify context + smart refresh
- manually seeded `.planning/` context
- current-state / docs / entrypoint convergence

This skill now replaces the older duplicate `brownfield-gsd-graphify-bootstrap` so the brownfield story stays single-track.

## When to Use

Use this skill when the user asks to:
- add GSD + graphify to an existing repo
- bootstrap brownfield planning without trusting `gsd-sdk init`
- standardize one reusable brownfield onboarding flow for teammates
- converge README / docs / AGENTS around the repo's current architecture before major refactors

Do not use this skill for greenfield repos or for upstream Hermes / graphify / GSD development.

## Outcome

A successful bootstrap usually leaves the repo with:
1. local Codex runtime files in `./.codex/`
2. `scripts/graphify-sync.sh` for cheap graph refresh
3. graphify outputs in `graphify-out/`
4. manually seeded `.planning/` brownfield baseline
5. workflow guidance in `AGENTS.md`, `README.md`, and docs
6. an initial current-state / entrypoint / roadmap baseline that future agents can extend

## Standard Install Story

Prefer the same baseline as the main Hermes + graphify + GSD workflow skills:

```bash
command -v hermes
hermes --version

PY_BIN="${PYTHON_BIN:-$HOME/.hermes/hermes-agent/venv/bin/python3}"
[ -x "$PY_BIN" ] || PY_BIN="$(command -v python3)"
if "$PY_BIN" -c 'import sys; print(int(sys.prefix != sys.base_prefix))' 2>/dev/null | grep -q '^1$'; then
  "$PY_BIN" -m pip install -U graphifyy
else
  "$PY_BIN" -m pip install --user -U graphifyy
fi
~/.local/bin/graphify install --platform hermes || graphify install --platform hermes
npx -y get-shit-done-cc@latest --codex --global --sdk
```

Why this is now the default:
- it matches the teammate-shareable non-intrusive workflow
- it reduces drift between brownfield bootstrap and project-integration skills
- it avoids forcing every user to clone and build GSD from source just to get started

## Source Install Is a Fallback, Not the Default

Only prefer a source checkout of GSD when one of these is true:
- you are debugging or contributing to GSD itself
- the upstream package entrypoint is temporarily broken
- you need to inspect installer behavior before trusting it in a sensitive environment

Fallback example:

```bash
git clone https://github.com/gsd-build/get-shit-done /data/ai-coding/get-shit-done
node /data/ai-coding/get-shit-done/bin/install.js --codex --local
cd /data/ai-coding/get-shit-done/sdk
npm install
npm run build
npm install -g .
```

Keep this explicitly labeled as fallback so teammates are not forced into a heavier path.

## Brownfield Bootstrap Steps

### 1. Install local Codex runtime in the target repo

From the target project root:

```bash
npx -y get-shit-done-cc@latest --codex --local
```

If that entrypoint is unavailable, use the source-install fallback above.

Verify:

```bash
find ./.codex -maxdepth 3 -type f | sort | sed -n '1,120p'
```

### 2. Confirm graphify outputs and add smart refresh

Required outputs are:
- `graphify-out/graph.json`
- `graphify-out/GRAPH_REPORT.md`

Important rule:
- do **not** require `graphify-out/manifest.json`
- newer graphify versions may not emit it
- treat manifest as optional diagnostic output only

The repo-local `scripts/graphify-sync.sh` should support:
- `status`
- `smart`
- `force`
- `serve`

Recommended `smart` behavior:
- if graph outputs are missing, run `graphify update .`
- if code files changed, run code-only rebuild via `graphify.watch._rebuild_code(Path('.'))`
- if only docs/media changed, skip automatic rebuild and print manual full-refresh guidance

### 3. Add or verify repo docs and workflow contract

Update or create:
- `AGENTS.md`
- `README.md`
- `docs/current-state.md`
- `docs/index.md`
- `docs/entrypoints.md`
- optional `docs/gsd-graphify-workflow.md`

Converge them around current facts:
- authoritative frontend and backend entrypoints
- current mainline architecture path
- what is legacy / experimental / archived
- the standard GSD + graphify operating loop

### 4. Manually seed `.planning/` when interactive init is not trustworthy

If the repo is complex, credentials are missing, or the current architecture already has a mature analysis baseline, do **not** block on `gsd-sdk init`.

Create:

```text
.planning/
  PROJECT.md
  REQUIREMENTS.md
  ROADMAP.md
  STATE.md
  config.json
  codebase/CODEBASE-MAP.md
  research/ITERATION-LOOP.md
```

Source material should come from real repo facts:
- `graphify-out/GRAPH_REPORT.md`
- current README / docs / AGENTS
- codebase inspection results
- current architectural conclusions

Practical `config.json` defaults:
- `mode: yolo`
- `discuss_mode: assumptions`
- `planning.commit_docs: false`
- keep destructive / external-service confirmations enabled

### 5. Optional cleanup of legacy entrypoints

For repos with multiple old entrypoints or migration leftovers:
- document authoritative entrypoints first
- archive low-risk legacy entrypoints before deleting anything
- do not start by deleting the most ambiguous historical mainline files

This keeps the brownfield migration reversible while the new workflow settles in.

## Recommended Phase 0

A good first brownfield phase is usually:
- `00-01` planning bootstrap
- `00-02` docs/current-state alignment
- `00-03` workflow verification

Only after that should the repo move into larger cleanup or architecture-convergence phases.

## Verification Checklist

Run and inspect these before claiming success:

```bash
find ./.codex -maxdepth 3 -type f | sort | sed -n '1,120p'
gsd-sdk --version
gsd-sdk --help
./scripts/graphify-sync.sh status
./scripts/graphify-sync.sh smart
find .planning -maxdepth 3 -type f | sort
```

Also verify:
- `graphify-out/GRAPH_REPORT.md` exists
- `graphify-out/graph.json` exists
- README / docs / AGENTS agree on current facts
- `.planning/ROADMAP.md` and `.planning/STATE.md` point at the same active phase
- if legacy entrypoints were archived, their replacements are clearly documented

## Common Pitfalls

1. Treating source-install as the default teammate path
- prefer the standard upstream entrypoints first

2. Requiring `manifest.json`
- manifest is optional in current graphify versions

3. Letting `gsd-sdk init` invent a roadmap for a complex repo with weak context
- manually seed `.planning/` when needed

4. Updating scripts but not README / docs / AGENTS
- brownfield repos need documentation convergence, not only tool installation

5. Deleting historical entrypoints before documenting the current mainline
- convergence first, destructive cleanup second

## Standard Operating Loop After Bootstrap

1. `./scripts/graphify-sync.sh smart`
2. Read `graphify-out/GRAPH_REPORT.md`
3. Read `.planning/STATE.md` and `.planning/ROADMAP.md`
4. Use GSD phase / plan / execute workflow
5. Implement or clean up
6. Re-run `./scripts/graphify-sync.sh smart`
7. Update planning/docs if the phase meaning changed

## Canonical Skill Note

This is the only brownfield bootstrap skill that should remain in the shared workflow set.
If you find references to `brownfield-gsd-graphify-bootstrap`, update them to this skill and remove the duplicate.
