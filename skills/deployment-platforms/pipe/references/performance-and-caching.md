# Performance and Caching

Purpose: Reduce CI latency and cost through cache design, efficient job graphs, bounded matrices, and disciplined artifact handling.

## Contents

- Cache strategy
- Job graph design
- Matrix strategy
- Artifacts and concurrency
- Runner cost
- Optimization checklist

## Cache Strategy

| Technique | Use it when | Key rules |
|-----------|-------------|-----------|
| built-in `setup-*` cache | language ecosystem supports it | prefer this first because it is simpler and less error-prone |
| `actions/cache` | you need custom paths or multiple cache layers | include OS and lockfile hash in the key |
| Docker layer cache | image builds dominate runtime | use `docker/build-push-action` with `type=gha` cache |
| framework cache | `.next/cache`, Turbo, Nx, uv, Go build cache | cache only the minimum useful directories |

Repository cache facts:

- total cache budget is `10 GB` per repository
- entries not accessed for `7 days` are evicted
- use restore keys for fallback

Good pattern:

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.pnpm-store
    key: pnpm-${{ runner.os }}-${{ hashFiles('**/pnpm-lock.yaml') }}
    restore-keys: |
      pnpm-${{ runner.os }}-
```

Rules:

- prefer built-in setup caches first
- key caches by OS and lockfile hash
- do not cache entire `node_modules` unless you have measured a need
- avoid duplicate caches such as `setup-node` cache plus an overlapping `actions/cache`

## Job Graph Design

| Pattern | Use it when | Avoid |
|---------|-------------|-------|
| Parallel independent jobs | lint, unit tests, static analysis are independent | serializing everything with `needs:` |
| Diamond graph | multiple checks feed one build or deploy | long linear chains |
| Conditional jobs | monorepo or environment-specific paths | giant workflow-level skip logic |

Prefer:

```yaml
lint ─┐
test ─┼─> build ─> deploy
scan ─┘
```

over:

```yaml
lint -> test -> build -> deploy
```

## Matrix Strategy

| Rule | Guidance |
|------|----------|
| `fail-fast: false` | use when each axis gives independent signal |
| `include` / `exclude` | trim impossible or low-value combinations |
| push vs PR coverage | keep pushes small, expand on PRs or nightly |
| explosion guard | redesign if matrix fan-out approaches `100+` jobs |

Dynamic matrices are appropriate when the changed package set or supported versions are computed at runtime.

## Artifacts And Concurrency

| Topic | Rule |
|-------|------|
| Artifacts v4 | artifact names are immutable |
| Artifact cap | max `500` artifacts per job |
| PR concurrency | use `cancel-in-progress: true` |
| Deploy concurrency | use `cancel-in-progress: false` to preserve queue order |

PR pattern:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

Deploy pattern:

```yaml
concurrency:
  group: deploy-production
  cancel-in-progress: false
```

## Runner Cost Guide

| Runner | Relative cost | Use it for |
|--------|---------------|------------|
| `ubuntu-latest` | baseline | default CI |
| Windows | `2x` | Windows-only checks |
| macOS | `10x` | Apple-platform validation |
| ARM | about `37%` cheaper than comparable x86 | compatible Linux workloads |

Illustrative GitHub-hosted pricing examples from the reference set:

- `ubuntu-latest`: `$0.008`
- `windows-latest`: `$0.016`
- `macos-latest`: `$0.08`
- `macos-latest-xlarge`: `$0.12`

## Optimization Checklist

- keep clones shallow unless history is required
- combine tiny steps that pay repeated setup costs
- use timeouts on long-running jobs
- shard tests only after measuring imbalance
- route monorepo work with path filters or affected-package tooling
- profile artifact upload/download before blaming test runtime
- use `act` or `workflow_dispatch` to validate expensive changes before broad rollout
