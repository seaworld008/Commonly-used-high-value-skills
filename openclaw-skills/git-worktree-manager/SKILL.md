---
name: git-worktree-manager
description: 'Create, inspect, and clean up Git worktrees for parallel development, with explicit ownership, environment handling, and port allocation.'
zh_description: "管理并行开发的 Git worktree、环境和端口分配。"
version: "1.0.2"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: ["development", "git", "manager", "worktree"]
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 4
complexity: "intermediate"
---

# Git Worktree Manager

**Tier:** POWERFUL  
**Category:** Engineering  
**Domain:** Parallel Development & Branch Isolation

## Overview

Use these manual templates to isolate branches, runtime configuration and local services across worktrees.

## Core Capabilities

- **Worktree lifecycle** — create, list, switch and clean up worktrees
- **Port allocation** — select unused ports for the services each worktree runs
- **Environment setup** — use project examples or managed test configuration
- **Docker Compose overrides** — adapt the port mapping for each stack
- **Conflict Prevention** — detect and warn about shared resources, database names, and API endpoints
- **Cleanup & Pruning** — safe removal with stale branch detection and uncommitted work warnings

## When to Use This Skill

- Running multiple Claude Code sessions on different features simultaneously
- Working on a hotfix while a feature branch has uncommitted work
- Reviewing a PR while continuing development on your branch
- Parallel CI/testing against multiple branches
- Monorepo development with isolated package changes

## Worktree Creation Workflow

### Step 1: Create Worktree

```bash
# Create worktree for a new feature branch
git worktree add ../project-feature-auth -b feature/auth

# Create worktree from an existing remote branch
git worktree add ../project-fix-123 origin/fix/issue-123

# Create worktree with tracking
git worktree add --track -b feature/new-api ../project-new-api origin/main
```

### Step 2: Environment Setup

Prepare runtime configuration only for a task that needs it.

1. Use the project's example configuration or inject scoped test credentials through its existing mechanism. Copy real credentials only when the user explicitly authorizes the files and destination.

2. If execution needs dependencies, use the project's package manager and locked install command within the worktree.

3. **For local services, check availability and allocate distinct ports.** Example assignments:
   ```
   Main worktree:     localhost:3000 (dev), :5432 (db), :6379 (redis)
   Worktree 1:        localhost:3010 (dev), :5442 (db), :6389 (redis)
   Worktree 2:        localhost:3020 (dev), :5452 (db), :6399 (redis)
   ```

### Step 3: Docker Compose Override

For Docker Compose projects, generate per-worktree override:

```yaml
# docker-compose.worktree.yml (example)
services:
  app:
    ports:
      - "3010:3000"
  db:
    ports:
      - "5442:5432"
  redis:
    ports:
      - "6389:6379"
```

Usage: `docker compose -f docker-compose.yml -f docker-compose.worktree.yml up`

### Step 4: Database Isolation

```bash
# Option A: Separate database per worktree
createdb myapp_feature_auth

# Option B: DATABASE_URL override
echo 'DATABASE_URL="postgresql://localhost:5442/myapp_wt1"' >> .env.local

# Option C: SQLite — file-based, automatic isolation
```

## Monorepo Optimization

Combine worktrees with sparse checkout for large repos:

```bash
git worktree add --no-checkout ../project-packages-only
cd ../project-packages-only
git sparse-checkout init --cone
git sparse-checkout set packages/shared packages/api
git checkout feature/api-refactor
```

## Claude Code Integration

When a project requests worktree-specific instructions, adapt this example:

```markdown
# Worktree: feature/auth
# Dev server port: 3010
# Created: 2026-03-01

## Scope
Focus on changes related to this branch only.

## Commands
- Dev: PORT=3010 npm run dev
- Test: npm test -- --related
- Lint: npm run lint
```

Run parallel sessions:
```bash
# Terminal 1: Main feature
cd ~/project && claude
# Terminal 2: Hotfix
cd ~/project-hotfix && claude
# Terminal 3: PR review
cd ~/project-pr-review && claude
```

## Common Pitfalls

1. **Dependencies** — Worktrees have separate working files. Prepare dependencies when the task needs execution.
2. **Port conflicts** — Two dev servers on :3000 = silent failures. Always allocate unique ports.
3. **Database migrations** — Migrations in one worktree affect all if sharing same DB. Isolate.
4. **Git hooks** — Live in `.git/hooks` (shared). Worktree-specific hooks need symlinks.
5. **IDE confusion** — VSCode may show wrong branch. Open as separate window.
6. **Stale worktrees** — Prune regularly: `git worktree prune`.

## Best Practices

1. Name worktrees by purpose: `project-auth`, `project-hotfix-123`, `project-pr-456`
2. Never create worktrees inside the main repo directory
3. Keep worktrees short-lived — merge and cleanup within days
4. Use an existing project setup script only after checking its inputs and actions. Otherwise use the applicable steps above.
5. One Claude Code instance per worktree — isolation is the point
6. Commit before switching — even WIP commits prevent lost work
