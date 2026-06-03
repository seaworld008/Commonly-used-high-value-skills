---
name: osv-scanner
description: '用于通过 OSV-Scanner 检查锁文件、清单、SBOM、Git 历史和源码树中的开源依赖漏洞。'
version: "1.0.0"
author: seaworld008
source: "in-house"
source_url: ""
tags: '[security, dependency-scanning, cve, osv, sca, sbom, lockfiles, supply-chain]'
created_at: "2026-05-20"
updated_at: "2026-05-20"
quality: 4
complexity: intermediate
---

# OSV-Scanner

## Trigger / When to Use

Use this skill when the user wants a fast open-source dependency vulnerability scan based on the OSV database, especially for projects with lockfiles, package manifests, SBOMs, or git repositories.

Good trigger phrases:
- "scan dependencies with OSV"
- "check package-lock or go.sum for CVEs"
- "find vulnerable open-source packages"
- "scan this SBOM against OSV"
- "add OSV scanning to CI"

## Core Capabilities

- Scan source directories and automatically discover lockfiles, SBOMs, and git metadata.
- Scan specific package manifests or lockfiles.
- Scan SPDX or CycloneDX SBOMs.
- Report vulnerabilities from the OSV database across language ecosystems.
- Work well as a lightweight SCA gate in CI.
- Provide actionable package names, versions, vulnerability IDs, and fixed versions when available.

## Workflow

### 1. Confirm Scope

Determine whether the user wants to scan:
- The current repository.
- A single manifest or lockfile.
- An SBOM file.
- A monorepo with multiple package roots.
- Git history or checked-out code only.

Prefer scanning lockfiles when present because they represent resolved dependency versions.

### 2. Verify Installation

```bash
osv-scanner --version
```

If it is missing, recommend the official OSV-Scanner installation method for the user's platform.

### 3. Run Source Scan

Use source scanning for normal repositories:

```bash
osv-scanner scan source .
```

Scan a specific lockfile or manifest:

```bash
osv-scanner scan source --lockfile package-lock.json .
```

Scan an SBOM:

```bash
osv-scanner scan source -L sbom.spdx.json .
```

### 4. Capture JSON Output

Use JSON when the result needs to feed automation:

```bash
osv-scanner scan source --format json --output osv-results.json .
```

If the installed version does not support a flag exactly as written, run `osv-scanner --help` and adapt to the installed CLI syntax.

### 5. Triage Results

For each finding, record:
- Package name and ecosystem.
- Vulnerable version.
- Introduced and fixed version ranges.
- Vulnerability aliases such as CVE or GHSA.
- Whether the package is direct or transitive.
- Owning package manager and lockfile path.

Prioritize:
1. Direct dependencies with fixed versions.
2. Transitive vulnerabilities reachable through active runtime paths.
3. Vulnerabilities with public exploit references.
4. Dependencies used in production builds over dev-only packages.

### 6. Remediation Strategy

Use the package manager native workflow first:

```bash
npm audit fix
go get module@example.com@patched-version
pip-compile --upgrade-package package-name
cargo update -p package-name
bundle update package-name
```

When no fixed version exists:
- Check whether the vulnerable feature is used.
- Consider temporary dependency replacement.
- Add a short-lived ignore entry with reason and review date.
- Open an upstream issue if the package is still maintained.

## Common Patterns

### GitHub Actions Gate

```yaml
name: osv-scanner
on: [pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install OSV-Scanner
        run: go install github.com/google/osv-scanner/v2/cmd/osv-scanner@latest
      - name: Scan dependencies
        run: osv-scanner scan source .
```

### Monorepo Scan Checklist

```text
1. List package roots and lockfiles.
2. Scan from repository root.
3. Re-run targeted scans for high-risk services.
4. Deduplicate repeated findings by package/version/vulnerability ID.
5. Assign owners based on package root.
```

### Finding Template

```markdown
## OSV Finding

- Package:
- Ecosystem:
- Current version:
- Fixed version:
- Vulnerability:
- Direct/transitive:
- Lockfile:
- Recommended action:
- Risk owner:
```

## Interpretation Rules

- Lockfile findings are usually more reliable than manifest-only findings.
- Development-only dependencies may still matter if they run in CI, build scripts, or release automation.
- A vulnerable transitive dependency should be fixed through the top-level package when possible.
- Do not delete lockfiles to reduce findings; that lowers reproducibility.
- Compare OSV findings with another scanner when results affect a release block.

## Boundaries

- OSV-Scanner is not a full SAST tool.
- It does not prove runtime exploitability.
- It should not be the only scanner for container images or Linux host packages.
- Do not publish private dependency inventories without approval.
- Do not blanket-ignore entire ecosystems or package managers.

## Reference Sources

- OSV-Scanner docs: https://google.github.io/osv-scanner/
- Source scanning: https://google.github.io/osv-scanner/usage/scan-source
