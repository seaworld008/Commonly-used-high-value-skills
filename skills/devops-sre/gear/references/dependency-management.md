# Dependency Management

Package manager reference, audit workflows, lockfile handling, version pinning strategies, and multi-language support.

---

## Package Manager Reference

| Task | npm | pnpm | yarn |
|------|-----|------|------|
| Install all | `npm install` | `pnpm install` | `yarn` |
| Install (CI) | `npm ci` | `pnpm install --frozen-lockfile` | `yarn --frozen-lockfile` |
| Add package | `npm install pkg` | `pnpm add pkg` | `yarn add pkg` |
| Add dev dep | `npm install -D pkg` | `pnpm add -D pkg` | `yarn add -D pkg` |
| Remove | `npm uninstall pkg` | `pnpm remove pkg` | `yarn remove pkg` |
| Update all | `npm update` | `pnpm update` | `yarn upgrade` |
| Update pkg | `npm update pkg` | `pnpm update pkg` | `yarn upgrade pkg` |
| Audit | `npm audit` | `pnpm audit` | `yarn audit` |
| Audit fix | `npm audit fix` | `pnpm audit --fix` | `yarn audit fix` |
| Outdated | `npm outdated` | `pnpm outdated` | `yarn outdated` |
| Dedupe | `npm dedupe` | `pnpm dedupe` | `yarn dedupe` |
| Why | `npm explain pkg` | `pnpm why pkg` | `yarn why pkg` |
| List | `npm list` | `pnpm list` | `yarn list` |
| Clean cache | `npm cache clean --force` | `pnpm store prune` | `yarn cache clean` |

---

## Audit Response Flow

```bash
# 1. Check vulnerabilities
pnpm audit

# 2. Check for safe updates
pnpm outdated

# 3. Update within semver range (safe)
pnpm update

# 4. If specific package has vulnerability
pnpm update vulnerable-package

# 5. If major version required (ask first)
pnpm add vulnerable-package@latest

# 6. If transitive dependency
pnpm add vulnerable-package --save-dev
# or use overrides in package.json:
# "pnpm": {
#   "overrides": {
#     "vulnerable-package": "^2.0.0"
#   }
# }
```

---

## Dependency Health Check

```bash
# Check for unused dependencies
npx depcheck

# Check for outdated dependencies
pnpm outdated

# Check bundle size impact
npx bundlephobia-cli package-name

# Check for duplicate dependencies
pnpm dedupe --check

# List direct dependencies
pnpm list --depth=0

# Find why a package is installed
pnpm why package-name

# Check peer dependency issues
pnpm install --strict-peer-dependencies
```

---

## Lockfile Conflict Resolution

```bash
# When lockfile conflicts occur:

# 1. Discard lockfile changes and regenerate
git checkout --theirs pnpm-lock.yaml  # or --ours
pnpm install

# 2. Or regenerate from scratch (last resort)
rm pnpm-lock.yaml
pnpm install

# 3. Verify build still works
pnpm build
pnpm test
```

---

## Version Pinning Strategies

```json
{
  "dependencies": {
    // Exact: Most stable, manual updates required
    "critical-lib": "2.0.0",

    // Patch: Auto-update patch versions (recommended for most)
    "stable-lib": "~2.0.0",

    // Minor: Auto-update minor versions
    "flexible-lib": "^2.0.0",

    // Range: Explicit range
    "legacy-lib": ">=1.0.0 <2.0.0"
  },

  // Override transitive dependencies
  "pnpm": {
    "overrides": {
      "vulnerable-package": "^2.0.0",
      "package>nested-vulnerable": "^1.5.0"
    }
  }
}
```

---

## Bun Runtime

```bash
# Install
curl -fsSL https://bun.sh/install | bash

# Basic commands (pnpm-like)
bun install              # Install dependencies
bun add <pkg>            # Add package
bun remove <pkg>         # Remove package
bun run <script>         # Run script
bun test                 # Run tests
bun build ./src/index.ts --outdir ./dist  # Bundle
```

```yaml
# GitHub Actions with Bun
- uses: oven-sh/setup-bun@v2
  with:
    bun-version: latest

- run: bun install --frozen-lockfile
- run: bun test
- run: bun run build
```

---

## Multi-Language Reference

| Task | Python (uv) | Go | Rust |
|------|-------------|-----|------|
| Install | `uv sync` | `go mod download` | `cargo fetch` |
| Add pkg | `uv add pkg` | `go get pkg` | `cargo add pkg` |
| Build | `uv run python -m build` | `go build ./...` | `cargo build --release` |
| Test | `uv run pytest` | `go test ./...` | `cargo test` |
| Lint | `uv run ruff check` | `golangci-lint run` | `cargo clippy` |
| Format | `uv run ruff format` | `gofmt -w .` | `cargo fmt` |
| Audit | `uv run pip-audit` | `govulncheck ./...` | `cargo audit` |
| Lock | `uv lock` | `go mod tidy` | `cargo generate-lockfile` |

```yaml
# Python CI with uv
- uses: astral-sh/setup-uv@v4
- run: uv sync --frozen
- run: uv run pytest

# Go CI
- uses: actions/setup-go@v5
  with:
    go-version: '1.22'
- run: go mod download
- run: go test ./...
```
