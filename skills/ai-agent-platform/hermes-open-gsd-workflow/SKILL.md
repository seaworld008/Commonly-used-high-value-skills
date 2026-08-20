---
name: hermes-open-gsd-workflow
description: 'Route a development task to the official Hermes Agent skill, Graphify Codex artifact set, Open GSD Core bundle, or optional GSD Pi bundle without duplicating their installers or state machines.'
zh_description: "在 Hermes Agent、Graphify、Open GSD Core 与可选 GSD Pi 之间做薄路由，不复制上游安装器和状态机。"
version: "1.0.1"
author: seaworld008
source: in-house
source_url: ""
tags: '[hermes, graphify, open-gsd, orchestration, routing]'
created_at: "2026-08-20"
updated_at: "2026-08-20"
quality: 4
complexity: intermediate
---

# Hermes and Open GSD Workflow Router

## Purpose

Use this skill as a thin decision layer. It chooses the maintained capability
that should own the work, then hands control to that capability.

It does not copy:

- upstream versions or installation commands;
- Graphify query syntax;
- GSD planning state machines;
- Hermes cron, lease, task-board, or handoff protocols;
- client-specific runtime files.

Those details belong to the official artifacts and managed bundle metadata.

## When to Use

Use this router when a request mentions two or more of these concerns:

- running or configuring Hermes Agent;
- building or querying a repository graph;
- onboarding or planning work in an existing repository;
- choosing between Open GSD Core and GSD Pi;
- deciding which component owns a failure.

For a task that clearly belongs to one component, invoke that component's
canonical skill directly.

## Routing Table

| Intent | Canonical owner | State boundary |
|---|---|---|
| Hermes runtime, providers, plugins, CLI, TUI, webhooks | `hermes-agent` | Hermes home and project context |
| Repository graph build, watch, query, hooks, export | `graphify` | Graphify's own database and config |
| Standard planning, brownfield onboarding, phase execution | Open GSD Core managed bundle | `.planning/` |
| Pi-native runtime explicitly requested by the user | Optional Open GSD Pi bundle | `.gsd/` |

## Decision Procedure

1. Identify the requested outcome, not merely the tools named by the user.
2. Check whether an existing repository already has `.planning/` or `.gsd/`.
3. Never treat both state roots as one project state machine.
4. Choose one planning runtime for the current operation.
5. Add Graphify only when graph evidence materially improves the task.
6. Add Hermes only when a Hermes execution surface is actually requested.

## Common Routes

Record the decision in a compact form when more than one component participates:

```yaml
planning_owner: open-gsd-core
state_root: .planning
evidence_provider: graphify
execution_surface: hermes
```

### Brownfield repository

Route to Open GSD Core and its official brownfield onboarding capability.
Graphify may supply current architecture evidence, but it does not create or
own the planning state.

Expected sequence:

1. inspect the repository and current state;
2. refresh or query Graphify when architecture evidence is needed;
3. run the Core onboarding workflow;
4. verify the generated `.planning/` artifacts;
5. continue with the selected Core phase workflow.

### Hermes-assisted implementation

Route runtime questions to `hermes-agent`, repository-structure questions to
`graphify`, and planning transitions to Open GSD Core.

Do not create a second lease, cron, task board, or handoff file to coordinate
them. The active runtime and planning bundle already define their own state.

### Optional GSD Pi request

GSD Pi is never selected by implication. It may be selected only when the user
explicitly requests the Pi bundle or a Pi-native workflow.

Before proceeding:

- confirm the optional bundle policy permits explicit installation;
- keep `.gsd/` isolated from Core's `.planning/`;
- do not copy Core planning state into Pi or vice versa;
- do not add Pi to the default canonical skill installation.

## Failure Ownership

Use the smallest owner that can explain the failure:

- provider, model, plugin, portal auth, or TUI failure: Hermes;
- stale graph, missing symbol, watcher, export, or query failure: Graphify;
- planning phase, onboarding, health, or resume failure: GSD Core;
- Pi plugin or `.gsd/` runtime failure: GSD Pi;

Do not diagnose a component by editing another component's state.

## Verification Contract

A routed workflow is complete only when:

- exactly one planning state root owns the operation;
- every installed bundle is selected explicitly and pinned by repository
  metadata;
- Graphify evidence is current enough for the decision being made;
- Hermes runtime state is checked through Hermes-native diagnostics;
- no retired composite skill is active in the client's discovery path;
- no duplicated wrapper state machine was introduced.

## Boundaries

- This skill never installs Hermes runtime.
- It never installs the optional GSD Pi bundle by default.
- It never upgrades a system Graphify CLI.
- It does not support retired composite skills or legacy installation layouts.
- It never rewrites upstream repositories to integrate the tools.
- It never claims that CI success proves a local runtime installation.
