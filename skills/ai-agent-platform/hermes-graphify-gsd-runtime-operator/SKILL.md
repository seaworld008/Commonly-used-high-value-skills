---
name: hermes-graphify-gsd-runtime-operator
description: 'Use when operating or debugging a repo-local Hermes + graphify + GSD autonomous runtime, especially when checking writer ownership, execution-surface eligibility, handoff/blocked state, stale cron or lease metadata, and whether the main project repo is still the only recommended writer surface.'
version: "1.2.0"
author: Hermes Agent
source: "in-house"
source_url: "https://github.com/seaworld008/Commonly-used-high-value-skills"
license: MIT
tags: '["ai", "agent", "hermes", "graphify", "gsd", "runtime", "operator", "diagnostics"]'
created_at: "2026-04-16"
updated_at: "2026-04-24"
quality: 5
complexity: "intermediate"
metadata:
  hermes:
    tags: [hermes, graphify, gsd, runtime, operator, auto-continue, writer-lease, diagnostics]
    companion_skills:
      - hermes-graphify-gsd-nonintrusive-workflow
      - hermes-graphify-gsd-project-integration
---

# Hermes + graphify + GSD Runtime Operator

## Overview

Use this skill to operate an already-integrated repo-local autonomous runtime.

This skill is for **observing, diagnosing, and correcting runtime state** after the workflow exists:
- who currently owns the writer lease
- whether the current repo is an eligible/recommended writer surface
- whether handoff or blocked state is active
- whether state/lease files are stale
- whether an old sandbox/worktree cron is still hijacking the writer role

## When to Use

Use when the user asks any of these:
- “现在是谁在写？”
- “为什么 auto-progress 还显示 running？”
- “sandbox 不是已经停了吗，为什么 lease 还在？”
- “这个 repo 还能不能当 writer？”
- “帮我把旧 sandbox writer 清掉”
- “检查 handoff / blocked / planning mirror / lease 是否一致”

Do not use this skill to bootstrap the workflow from scratch. Use the companion integration skills first.

## Core Operating Model

Preferred steady state:
- **main project repo = primary writer execution surface**
- extra worktrees are read-only analysis areas or temporary experiments unless explicitly promoted
- operator commands are the fact source, not intuition

## First Checks

Always start with the repo-local operator surface:

```bash
./scripts/ai-workflow.sh doctor
./scripts/ai-workflow.sh auto-execution-surface-show
./scripts/ai-workflow.sh auto-runner-show
./scripts/ai-workflow.sh auto-progress
./scripts/ai-workflow.sh auto-workflow-state-show
```

Also check the graphify runtime baseline when diagnosing graph or planning drift:

```bash
graphify --help | sed -n '1,40p'
python3 -m pip show graphifyy 2>/dev/null | sed -n '1,20p'
```

Expected baseline as of 2026-04-24:
- `graphifyy` should be `0.5.0` or newer
- required graph outputs are still `graphify-out/graph.json` and `graphify-out/GRAPH_REPORT.md`
- missing `manifest.json` is not a runtime failure
- transient `.graphify_chunk_*.json` files can indicate an interrupted Codex semantic extraction and should be treated as evidence, not immediately deleted

Interpretation:
- `execution_surface: ready` means the repo looks complete enough to participate
- `writer_eligible=yes` means the repo passes the execution-surface check
- `primary_root_match=yes` means the repo matches the configured primary root
- `writer_recommended=yes` means the repo is the intended writer surface

If `writer_recommended=no`, do not install cron or bind runtime metadata here.

## Runtime Triage Order

### 1. Check the current writer contract
Read:
- execution-surface status
- global runner state
- planning mirror
- effective state
- current lease

Use `auto-runner-show` and `auto-progress` before any mutation.

### 2. Distinguish live lock from stale metadata
A common trap is stale files saying `running` after the process is already gone.

Check both:
- operator views (`auto-runner-show`, `auto-progress`)
- actual lock/process reality

If needed, verify directly with shell tools such as:

```bash
ps -ef | grep -F 'hermes-auto-continue-trigger.sh' | grep -v grep
crontab -l
```

If lock/process reality and JSON state disagree, trust live process/lock facts first, then reconcile metadata.

### 3. Check both Hermes cron and system cron
Do not assume `hermes cron list --all` is enough.

Reality-tested rule:
- `hermes cron list --all` being empty does **not** prove the machine has no active scheduler entry
- also inspect system `crontab -l`

This matters when an old sandbox/worktree cron continues to trigger a stale writer.

### 4. Handle stale sandbox/worktree writers carefully
If observed writer metadata points at an unexpected worktree:
1. inspect the live PID / command line
2. inspect system cron entries and tags
3. remove the stale cron entry first
4. stop the stale process
5. only then reconcile state/lease metadata back to the intended main repo

Do not just edit JSON first and leave the old cron alive; it will reassert itself.

## Handoff and Blocked State

Use these commands:

```bash
./scripts/ai-workflow.sh auto-handoff-show
./scripts/ai-workflow.sh auto-handoff-set <reason> <detail> [requested_input] [resume_condition] [next_action]
./scripts/ai-workflow.sh auto-handoff-clear
./scripts/ai-workflow.sh auto-resume-if-ready
```

Interpretation:
- `blocked` = could not proceed right now (busy, refusal, conflict)
- `handoff` = intentionally waiting for human or external input

When handoff is active, prefer preserving the structured payload:
- `reason`
- `detail`
- `requested_input`
- `resume_condition`
- `next_action`

Do not clear handoff casually if the required input has not actually arrived.
Prefer machine-readable `resume_condition` probes when the runtime should recover automatically on the next cron/timer cycle.

## Planning Mirror

Use:

```bash
./scripts/ai-workflow.sh auto-workflow-state-show
```

Purpose:
- gives `.planning` / GSD a machine-readable mirror of runtime state
- should align with global state and effective state

If planning mirror says one thing and global runtime says another, note the divergence explicitly and reconcile only after checking the live process/lock situation.

## Common Failure Patterns

### Pattern 1: Empty Hermes cron, but writer still active
Cause:
- system crontab still contains an old runtime entry

Action:
- inspect `crontab -l`
- remove the stale cron tag
- stop the stale trigger process
- reconcile state/lease

### Pattern 2: State says running, but no visible process
Cause:
- stale metadata

Action:
- verify kernel/user-space lock reality
- if lock is actually free, rewrite state/lease to inactive with an operator reason

### Pattern 3: Sandbox still appears as writer after policy changed
Cause:
- historical cron or stale lease

Action:
- prove whether sandbox is still truly running
- if not, clear the stale metadata
- if yes, remove the cron/process first

### Pattern 4: Current repo passes execution-surface check but still should not write
Cause:
- it is not the configured primary root

Action:
- check `primary_root_match`
- only allow runtime binding / cron install on `writer_recommended=yes`

## Verification Checklist

Before claiming runtime/operator work is done, verify:

```bash
./scripts/ai-workflow.sh doctor
./scripts/ai-workflow.sh auto-execution-surface-show
./scripts/ai-workflow.sh auto-runner-show
./scripts/ai-workflow.sh auto-progress
hermes cron list --all
crontab -l
```

And make sure all of these are coherent:
- current repo shows `writer_recommended=yes` if it is meant to write
- `writer state` reflects reality
- global state file and effective state agree, or divergence is explicitly explained
- planning mirror is not silently stale
- no old sandbox/worktree cron remains active

## Common Mistakes

1. Treating operator JSON as more trustworthy than live process reality
- stale metadata is common; verify real processes and locks

2. Checking Hermes cron only
- system cron may still be active

3. Clearing lease/state before removing the stale scheduler source
- the next cron tick will recreate the bad state

4. Assuming a sandbox should stay canonical forever
- if the main project repo is now the writer surface, remove the stale sandbox runtime instead of working around it

5. Forgetting to re-check operator views after cleanup
- always rerun `auto-runner-show` and `auto-progress`

## Minimal Success Definition

A good operator outcome means:
- the intended main repo reports `writer_recommended=yes`
- stale sandbox/worktree writers are gone
- current writer state is accurate
- state/lease/planning mirror are coherent enough for the next development step
