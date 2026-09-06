---
name: monorepo-navigator
description: 'Inspect or improve Turborepo, Nx, pnpm, or Lerna monorepos: package boundaries, dependency graphs, selective tests, caching, and migrations.'
zh_description: "分析多包仓库的依赖、构建、缓存和变更影响。"
version: "1.0.1"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["development", "monorepo", "navigator"]'
created_at: "2026-03-04"
updated_at: "2026-09-06"
quality: 5
complexity: "intermediate"
---

# Monorepo Navigator

**Tier:** POWERFUL  
**Category:** Engineering  
**Domain:** Monorepo Architecture / Build Systems  

---

## Overview

Navigate, manage, and optimize monorepos. Covers Turborepo, Nx, pnpm workspaces, and Lerna. Enables cross-package impact analysis, selective builds/tests on affected packages only, remote caching, dependency graph visualization, and structured migrations from multi-repo to monorepo. Includes Claude Code configuration for workspace-aware development.

---

## Core Capabilities

- **Cross-package impact analysis** — determine which apps break when a shared package changes
- **Selective commands** — run tests/builds only for affected packages (not everything)
- **Dependency graph** — visualize package relationships as Mermaid diagrams
- **Build optimization** — remote caching, incremental builds, parallel execution
- **Migration** — step-by-step multi-repo → monorepo with zero history loss
- **Publishing** — changesets for versioning, pre-release channels, npm publish workflows
- **Claude Code config** — workspace-aware CLAUDE.md with per-package instructions

---

## When to Use

Use when:
- Multiple packages/apps share code (UI components, utils, types, API clients)
- Build times are slow because everything rebuilds when anything changes
- Migrating from multiple repos to a single repo
- Need to publish packages to npm with coordinated versioning
- Teams work across multiple packages and need unified tooling

Skip when:
- Single-app project with no shared packages
- Team/project boundaries are completely isolated (polyrepo is fine)
- Shared code is minimal and copy-paste overhead is acceptable

---

## Tool Selection

| Tool | Best For | Key Feature |
|---|---|---|
| **Turborepo** | JS/TS monorepos, simple pipeline config | Best-in-class remote caching, minimal config |
| **Nx** | Large enterprises, plugin ecosystem | Project graph, code generation, affected commands |
| **pnpm workspaces** | Workspace protocol, disk efficiency | `workspace:*` for local package refs |
| **Lerna** | npm publishing, versioning | Batch publishing, conventional commits |
| **Changesets** | Modern versioning (preferred over Lerna) | Changelog generation, pre-release channels |

Most modern setups: **pnpm workspaces + Turborepo + Changesets**

---

## Turborepo

### turbo.json pipeline config

```json
{
  "$schema": "https://turbo.build/schema.json",
  "globalEnv": ["NODE_ENV", "DATABASE_URL"],
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],    // build deps first (topological order)
      "outputs": [".next/**", "dist/**", "build/**"],
      "env": ["NEXT_PUBLIC_API_URL"]
    },
    "test": {
      "dependsOn": ["^build"],    // need built deps to test
      "outputs": ["coverage/**"],
      "cache": true
    },
    "lint": {
      "outputs": [],
      "cache": true
    },
    "dev": {
      "cache": false,             // never cache dev servers
      "persistent": true          // long-running process
    },
    "type-check": {
      "dependsOn": ["^build"],
      "outputs": []
    }
  }
}
```

### Key commands

```bash
# Build everything (respects dependency order)
turbo run build

# Build only affected packages (requires --filter)
turbo run build --filter=...[HEAD^1]   # changed since last commit
turbo run build --filter=...[main]     # changed vs main branch

# Test only affected
turbo run test --filter=...[HEAD^1]

# Run for a specific app and all its dependencies
turbo run build --filter=@myorg/web...

# Run for a specific package only (no dependencies)
turbo run build --filter=@myorg/ui

# Dry-run — see what would run without executing
turbo run build --dry-run

# Enable remote caching (Vercel Remote Cache)
turbo login
turbo link
```

### Remote caching setup

```bash
# .turbo/config.json (auto-created by turbo link)
{
  "teamid": "team_xxxx",
  "apiurl": "https://vercel.com"
}

# Self-hosted cache server (open-source alternative)
# Run ducktape/turborepo-remote-cache or Turborepo's official server
TURBO_API=http://your-cache-server.internal \
TURBO_TOKEN=your-token \
TURBO_TEAM=your-team \
turbo run build
```

---

## Nx

### Project graph and affected commands

```bash
# Install
npx create-nx-workspace@latest my-monorepo

# Visualize the project graph (opens browser)
nx graph

# Show affected packages for the current branch
nx affected:graph

# Run only affected tests
nx affected --target=test

# Run only affected builds
nx affected --target=build

# Run affected with base/head (for CI)
nx affected --target=test --base=main --head=HEAD
```

### nx.json configuration

```json
{
  "$schema": "./node_modules/nx/schemas/nx-schema.json",
  "targetDefaults": {
    "build": {
      "dependsOn": ["^build"],
      "cache": true
    },
    "test": {
      "cache": true,
      "inputs": ["default", "^production"]
    }
  },
  "namedInputs": {
    "default":    ["{projectRoot}/**/*", "sharedGlobals"],
    "production": ["default", "!{projectRoot}/**/*.spec.ts", "!{projectRoot}/jest.config.*"],
    "sharedGlobals": []
  },
  "parallel": 4,
  "cacheDirectory": "/tmp/nx-cache"
}
```

---

## pnpm Workspaces

### pnpm-workspace.yaml

```yaml
packages:
  - 'apps/*'
  - 'packages/*'
  - 'tools/*'
```

### workspace:* protocol for local packages

```json
// apps/web/package.json
{
  "name": "@myorg/web",
  "dependencies": {
    "@myorg/ui":     "workspace:*",   // always use local version
    "@myorg/utils":  "workspace:^",   // local, but respect semver on publish
    "@myorg/types":  "workspace:~"
  }
}
```

### Useful pnpm workspace commands

```bash
# Install all packages across workspace
pnpm install

# Run script in a specific package
pnpm --filter @myorg/web dev

# Run script in all packages
pnpm --filter "*" build

# Run script in a package and all its dependencies
pnpm --filter @myorg/web... build

# Add a dependency to a specific package
pnpm --filter @myorg/web add react

# Add a shared dev dependency to root
pnpm add -D typescript -w

# List workspace packages
pnpm ls --depth -1 -r
```

---

## Cross-Package Impact Analysis

When a shared package changes, determine what's affected before you ship.

```bash
# Using Turborepo — show affected packages
turbo run build --filter=...[HEAD^1] --dry-run 2>&1 | grep "Tasks to run"

# Using Nx
nx affected:apps --base=main --head=HEAD    # which apps are affected
nx affected:libs --base=main --head=HEAD    # which libs are affected

# Manual analysis with pnpm
# Find all packages that depend on @myorg/utils:
grep -r '"@myorg/utils"' packages/*/package.json apps/*/package.json

# Using jq for structured output
for pkg in packages/*/package.json apps/*/package.json; do
  name=$(jq -r '.name' "$pkg")
  if jq -e '.dependencies["@myorg/utils"] // .devDependencies["@myorg/utils"]' "$pkg" > /dev/null 2>&1; then
    echo "$name depends on @myorg/utils"
  fi
done
```

---

## Dependency Graph Visualization

Read [the detailed procedure and examples](EXTENDED.md#section-3) when working on this part of the task.

## Claude Code Configuration (Workspace-Aware CLAUDE.md)

Read [the detailed procedure and examples](EXTENDED.md#section-1) when working on this part of the task.

## Migration: Multi-Repo → Monorepo

```bash
# Step 1: Create monorepo scaffold
mkdir my-monorepo && cd my-monorepo
pnpm init
echo "packages:\n  - 'apps/*'\n  - 'packages/*'" > pnpm-workspace.yaml

# Step 2: Move repos with git history preserved
mkdir -p apps packages

# For each existing repo:
git clone https://github.com/myorg/web-app
cd web-app
git filter-repo --to-subdirectory-filter apps/web  # rewrites history into subdir
cd ..
git remote add web-app ./web-app
git fetch web-app --tags
git merge web-app/main --allow-unrelated-histories

# Step 3: Update package names to scoped
# In each package.json, change "name": "web" to "name": "@myorg/web"

# Step 4: Replace cross-repo npm deps with workspace:*
# apps/web/package.json: "@myorg/ui": "1.2.3" → "@myorg/ui": "workspace:*"

# Step 5: Add shared configs to root
cp apps/web/.eslintrc.js .eslintrc.base.js
# Update each package's config to extend root:
# { "extends": ["../../.eslintrc.base.js"] }

# Step 6: Add Turborepo
pnpm add -D turbo -w
# Create turbo.json (see above)

# Step 7: Unified CI (see CI section below)
# Step 8: Test everything
turbo run build test lint
```

---

## CI Patterns

### GitHub Actions — Affected Only

Read [the detailed procedure and examples](EXTENDED.md#section-2) when working on this part of the task.

### GitLab CI — Parallel Stages

```yaml
# .gitlab-ci.yml
stages: [install, build, test, publish]

variables:
  PNPM_CACHE_FOLDER: .pnpm-store

cache:
  key: pnpm-$CI_COMMIT_REF_SLUG
  paths: [.pnpm-store/, .turbo/]

install:
  stage: install
  script:
    - pnpm install --frozen-lockfile
  artifacts:
    paths: [node_modules/, packages/*/node_modules/, apps/*/node_modules/]
    expire_in: 1h

build:affected:
  stage: build
  needs: [install]
  script:
    - turbo run build --filter=...[origin/main]
  artifacts:
    paths: [apps/*/dist/, apps/*/.next/, packages/*/dist/]

test:affected:
  stage: test
  needs: [build:affected]
  script:
    - turbo run test --filter=...[origin/main]
  coverage: '/Statements\s*:\s*(\d+\.?\d*)%/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: "**/coverage/cobertura-coverage.xml"
```

---

## Publishing with Changesets

```bash
# Install changesets
pnpm add -D @changesets/cli -w
pnpm changeset init

# After making changes, create a changeset
pnpm changeset
# Interactive: select packages, choose semver bump, write changelog entry

# In CI — version packages + update changelogs
pnpm changeset version

# Publish all changed packages
pnpm changeset publish

# Pre-release channel (for alpha/beta)
pnpm changeset pre enter beta
pnpm changeset
pnpm changeset version   # produces 1.2.0-beta.0
pnpm changeset publish --tag beta
pnpm changeset pre exit  # back to stable releases
```

### Automated publish workflow (GitHub Actions)

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    branches: [main]

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v3
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          registry-url: https://registry.npmjs.org

      - run: pnpm install --frozen-lockfile

      - name: Create Release PR or Publish
        uses: changesets/action@v1
        with:
          publish: pnpm changeset publish
          version: pnpm changeset version
          commit: "chore: release packages"
          title: "chore: release packages"
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

---

## Common Pitfalls

| Pitfall | Fix |
|---|---|
| Running `turbo run build` without `--filter` on every PR | Always use `--filter=...[origin/main]` in CI |
| `workspace:*` refs cause publish failures | Use `pnpm changeset publish` — it replaces `workspace:*` with real versions automatically |
| All packages rebuild when unrelated file changes | Tune `inputs` in turbo.json to exclude docs, config files from cache keys |
| Shared tsconfig causes one package to break all type-checks | Use `extends` properly — each package extends root but overrides `rootDir` / `outDir` |
| git history lost during migration | Use `git filter-repo --to-subdirectory-filter` before merging — never move files manually |
| Remote cache not working in CI | Check TURBO_TOKEN and TURBO_TEAM env vars; verify with `turbo run build --summarize` |
| CLAUDE.md too generic — Claude modifies wrong package | Add explicit "When working on X, only touch files in apps/X" rules per package CLAUDE.md |

---

## Best Practices

1. **Root CLAUDE.md defines the map** — document every package, its purpose, and dependency rules
2. **Per-package CLAUDE.md defines the rules** — what's allowed, what's forbidden, testing commands
3. **Always scope commands with --filter** — running everything on every change defeats the purpose
4. **Remote cache is not optional** — without it, monorepo CI is slower than multi-repo CI
5. **Changesets over manual versioning** — never hand-edit package.json versions in a monorepo
6. **Shared configs in root, extended in packages** — tsconfig.base.json, .eslintrc.base.js, jest.base.config.js
7. **Impact analysis before merging shared package changes** — run affected check, communicate blast radius
8. **Keep packages/types as pure TypeScript** — no runtime code, no dependencies, fast to build and type-check
