# GitHub Actions Templates

> **Note:** For advanced GHA workflow design (trigger strategy, security hardening, performance optimization, PR automation, Reusable/Composite design, monorepo CI, self-hosted runners), see the **Pipe** agent (`pipe/SKILL.md`).

CI/CD workflow templates, composite actions, reusable workflows, OIDC authentication, and security scanning.

---

## CI Workflow (Lint, Test, Build)

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
# ...
```

---

## Matrix Testing (Node Versions, OS)

```yaml
# .github/workflows/test-matrix.yml
name: Test Matrix

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
# ...
```

---

## CD Workflow (Deploy)

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deploy environment'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
# ...
```

---

## Release Workflow (Semantic Release)

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    branches: [main]

permissions:
  contents: write
  issues: write
  pull-requests: write

jobs:
  release:
    runs-on: ubuntu-latest
# ...
```

---

## Dependabot Configuration

```yaml
# .github/dependabot.yml
version: 2
updates:
  # npm dependencies
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 10
    groups:
      dev-dependencies:
        dependency-type: "development"
        patterns:
          - "*"
# ...
```

---

## Composite Action (DRY Setup)

```yaml
# .github/actions/setup-node-pnpm/action.yml
name: 'Setup Node + pnpm'
description: 'Common setup for Node.js projects with pnpm'

inputs:
  node-version:
    description: 'Node.js version'
    default: '20'
  install-deps:
    description: 'Run pnpm install'
    default: 'true'

runs:
  using: 'composite'
  steps:
# ...
```

Usage in workflows:
```yaml
- uses: ./.github/actions/setup-node-pnpm
  with:
    node-version: '20'
```

---

## Reusable Workflow

```yaml
# .github/workflows/ci-reusable.yml
name: Reusable CI

on:
  workflow_call:
    inputs:
      node-version:
        type: string
        default: '20'
      run-e2e:
        type: boolean
        default: false
    secrets:
      NPM_TOKEN:
        required: false
# ...
```

---

## OIDC Authentication (Passwordless)

```yaml
# AWS without secrets
permissions:
  id-token: write
  contents: read

steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::123456789:role/github-actions
      aws-region: ap-northeast-1

# GCP without secrets
  - uses: google-github-actions/auth@v2
    with:
      workload_identity_provider: 'projects/123/locations/global/workloadIdentityPools/github/providers/github'
# ...
```

---

## Security Scanning in CI

```yaml
# Gitleaks (secret detection)
- uses: gitleaks/gitleaks-action@v2
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

# Trivy (vulnerability scan)
- uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
    severity: 'CRITICAL,HIGH'
```

---

## Renovate Configuration (Dependabot Alternative)

```json
// renovate.json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"],
  "schedule": ["before 6am on monday"],
  "timezone": "Asia/Tokyo",
  "labels": ["dependencies"],
  "packageRules": [
    {
      "matchUpdateTypes": ["minor", "patch"],
      "automerge": true
    },
    {
      "matchPackagePatterns": ["eslint", "prettier", "typescript"],
      "groupName": "linting"
// ...
```
