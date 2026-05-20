---
name: grype-syft-sbom-scanner
description: 'Use Syft to generate SBOMs and Grype to scan container images, filesystems, packages, archives, and SBOMs for vulnerabilities.'
version: "1.0.0"
author: seaworld008
source: "in-house"
source_url: ""
tags: '[security, sbom, vulnerability-scanning, grype, syft, container-security, supply-chain, cve]'
created_at: "2026-05-20"
updated_at: "2026-05-20"
quality: 4
complexity: advanced
---

# Grype + Syft SBOM Scanner

## Trigger / When to Use

Use this skill when the user wants SBOM-first vulnerability management, container image scanning, package inventory, or repeatable vulnerability scans using Anchore open-source tools Syft and Grype.

Good trigger phrases:
- "generate an SBOM and scan it"
- "scan this container with Grype"
- "compare vulnerabilities between two images"
- "produce CycloneDX or SPDX"
- "scan a directory or archive for CVEs"
- "make vulnerability results reproducible from SBOM"

## Core Capabilities

- Generate SBOMs from container images, directories, files, archives, and package metadata with Syft.
- Scan container images, directories, SBOMs, and individual package identifiers with Grype.
- Separate inventory generation from vulnerability matching for repeatable audits.
- Compare scan results over time as vulnerability databases change.
- Integrate SBOM and vulnerability outputs into CI/CD and release evidence.
- Support SPDX, CycloneDX, and Syft JSON workflows.

## Workflow

### 1. Pick the SBOM Strategy

Use one of these modes:
- Direct Grype scan for quick triage.
- Syft SBOM plus Grype scan for reproducibility.
- Stored SBOM scan for release, compliance, or incident response.

Prefer SBOM-first when the result will be attached to a release, shared with customers, or compared later.

### 2. Verify Tools

```bash
syft version
grype version
```

If missing, install from official Anchore channels. Pin versions in CI when release evidence matters.

### 3. Generate an SBOM

For a container image:

```bash
syft registry.example.com/app:1.2.3 -o cyclonedx-json=sbom.cdx.json
```

For a local source or filesystem directory:

```bash
syft dir:. -o spdx-json=sbom.spdx.json
```

For Syft JSON:

```bash
syft packages . -o syft-json=sbom.syft.json
```

### 4. Scan with Grype

Scan an image directly:

```bash
grype registry.example.com/app:1.2.3
```

Scan a directory:

```bash
grype dir:.
```

Scan an SBOM:

```bash
grype sbom:sbom.cdx.json
```

Fail on high-severity findings in CI:

```bash
grype registry.example.com/app:1.2.3 --fail-on high
```

### 5. Produce Reports

```bash
grype sbom:sbom.cdx.json -o json > grype-results.json
grype sbom:sbom.cdx.json -o sarif > grype-results.sarif
grype sbom:sbom.cdx.json -o table
```

Retain:
- SBOM file.
- Scanner version.
- Vulnerability DB update timestamp.
- Image digest or git commit.
- Grype output.

### 6. Triage Findings

For each finding, capture:
- Vulnerability ID.
- Package name, version, type, and location.
- Match type and confidence.
- Fixed version.
- Image layer or file path when available.
- Whether the package is runtime, build-only, or unused.

Prioritize runtime packages over build-only layers unless the build system is also in scope.

## Common Patterns

### Release Evidence Bundle

```text
release-security/
  image-digest.txt
  sbom.cdx.json
  grype-results.json
  grype-results.sarif
  scanner-versions.txt
  accepted-risk.md
```

### GitHub Actions Example

```yaml
name: sbom-vuln-scan
on: [pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Generate SBOM
        run: syft dir:. -o cyclonedx-json=sbom.cdx.json
      - name: Scan SBOM
        run: grype sbom:sbom.cdx.json --fail-on high
```

### Image Comparison

```bash
syft old-image:tag -o syft-json=old.sbom.json
syft new-image:tag -o syft-json=new.sbom.json
grype sbom:old.sbom.json -o json > old.vulns.json
grype sbom:new.sbom.json -o json > new.vulns.json
```

Summarize deltas by new, fixed, unchanged, and severity-changed vulnerabilities.

## Interpretation Rules

- An SBOM is an inventory, not a security verdict.
- A vulnerability match can depend on package metadata quality.
- Distro vendor advisories can disagree with NVD severity or fix status.
- Image scans should use immutable digests for release evidence.
- Re-scanning old SBOMs can show newly disclosed vulnerabilities without rebuilding artifacts.

## Boundaries

- Do not assume Grype and Trivy will produce identical results.
- Do not delete packages blindly from images without checking runtime dependencies.
- Do not publish SBOMs externally without approval; SBOMs reveal technology inventory.
- Do not treat a missing fixed version as an automatic blocker without risk analysis.
- Do not use SBOM-only results as proof that source code has no custom vulnerabilities.

## Reference Sources

- Anchore OSS docs: https://oss.anchore.com/docs/
- Grype scan targets: https://oss.anchore.com/docs/guides/vulnerability/scan-targets/
- Syft scan targets: https://oss.anchore.com/docs/guides/sbom/scan-targets/
