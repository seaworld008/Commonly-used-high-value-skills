# Security Hardening

Purpose: Secure GitHub Actions workflows against supply-chain compromise, privilege escalation, script injection, and secret exfiltration.

## Contents

- Threat model
- Permission model
- SHA pinning
- Safe scripting
- OIDC
- Supply-chain defenses
- Governance checklist

## Threat Model

| Threat | Typical failure | Primary defense |
|--------|------------------|-----------------|
| Supply-chain attack | compromised third-party action executes malicious code | full SHA pinning, allow-lists, automated updates |
| Script injection | untrusted event data interpolated into `run:` | pass untrusted values via `env:` and quote them |
| Secret exfiltration | secrets leaked to logs, artifacts, or outbound traffic | minimal secret scope, masking, egress monitoring |
| Privilege escalation | default or excessive workflow permissions | `permissions: {}` and job-level grants |
| Fork PR abuse | `pull_request_target` runs fork code with secrets | never checkout untrusted fork code in `pull_request_target` |

## Permission Model

Default to zero permissions at the workflow level, then grant the minimum required at job level.

```yaml
permissions: {}

jobs:
  test:
    permissions:
      contents: read
```

Common grants:

| Need | Permission |
|------|------------|
| Read repo contents | `contents: read` |
| Post PR comments or labels | `pull-requests: write` |
| Upload SARIF | `security-events: write` |
| Mint cloud identity via OIDC | `id-token: write` |

Never use `permissions: write-all`.

## SHA Pinning

- Pin every third-party action to a full commit SHA.
- Tags are mutable. SHAs are immutable.
- Update pins with Dependabot or Renovate.

```yaml
# Bad
- uses: actions/checkout@v4

# Good
- uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
```

If you inherit legacy config such as `aquasecurity/trivy-action@master`, treat it as technical debt and replace it with a full SHA pin before trusting the workflow.

## Safe Scripting

Treat PR titles, branch names, issue bodies, and commit messages as hostile input.

Bad:

```yaml
- run: echo "${{ github.event.pull_request.title }}"
```

Good:

```yaml
- env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  run: printf '%s\n' "$PR_TITLE"
```

Rules:

- never interpolate untrusted data directly inside shell code
- avoid `eval`
- quote variables
- mask secrets before any diagnostic logging

## OIDC Over Long-Lived Secrets

Prefer workload identity federation to stored cloud keys.

| Cloud | Common action | Notes |
|------|----------------|------|
| AWS | `aws-actions/configure-aws-credentials` | use `role-to-assume` and repository/branch trust conditions |
| GCP | `google-github-actions/auth` | constrain workload identity pool bindings |
| Azure | `azure/login` | scope federated credentials tightly |
| Vault | platform-specific OIDC login | bind claims to repo, ref, and environment |

Grant `id-token: write` only to jobs that actually mint cloud credentials.

## Supply-Chain Defenses

Recommended controls:

| Control | Example |
|---------|---------|
| Runner egress monitoring | `step-security/harden-runner@v2` |
| Build provenance | `actions/attest-build-provenance@v2` |
| SBOM generation | `anchore/sbom-action@v0` |
| SBOM attestation | `actions/attest-sbom@v1` |
| Secret scanning | `gitleaks/gitleaks-action@v2` |
| Scorecard | weekly OpenSSF Scorecard run |
| SARIF upload | `github/codeql-action/upload-sarif@v3` |

Real incidents to keep in mind:

- `tj-actions/changed-files` (`CVE-2025-30066`)
- `reviewdog/action-setup` (`CVE-2025-30154`)
- GhostAction secret-exfiltration campaign
- `pull_request_target` + unsanitized-input attacks such as the Nx incident

## Governance Checklist

- all third-party actions are SHA-pinned
- Dependabot or Renovate updates GitHub Actions dependencies
- workflow defaults to read-only or empty permissions
- no secrets are printed, echoed, or stored in artifacts
- `pull_request_target` never checks out untrusted fork code
- deploy jobs use environment protection and concurrency
- CODEOWNERS includes `.github/workflows/`
- org allow-list or approval policy exists for actions
- OIDC is preferred over long-lived cloud secrets
- Scorecard, secret scanning, and provenance are enabled where appropriate
