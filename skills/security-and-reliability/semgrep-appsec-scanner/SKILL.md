---
name: semgrep-appsec-scanner
description: 'Use Semgrep for application security scanning across source code, custom rules, secrets workflows, and Semgrep Supply Chain dependency analysis.'
version: "1.0.0"
author: seaworld008
source: "in-house"
source_url: ""
tags: '[security, sast, semgrep, code-scanning, supply-chain, secrets, ci, appsec]'
created_at: "2026-05-20"
updated_at: "2026-05-20"
quality: 4
complexity: advanced
---

# Semgrep AppSec Scanner

## Trigger / When to Use

Use this skill when the user asks for source-code vulnerability scanning, secure coding rule enforcement, custom SAST checks, secret scanning workflow design, or Semgrep Supply Chain dependency analysis.

Good trigger phrases:
- "scan this code with Semgrep"
- "find injection bugs"
- "add SAST to CI"
- "write a Semgrep rule"
- "scan dependencies with Semgrep Supply Chain"
- "triage Semgrep findings"

## Core Capabilities

- Run SAST checks across many common programming languages.
- Use community and organization rules from the Semgrep registry.
- Author custom rules for project-specific insecure patterns.
- Triage findings with file, line, rule ID, and dataflow context.
- Integrate scans into pull requests and CI.
- Combine SAST with supply-chain and secrets workflows when the Semgrep plan supports them.

## Workflow

### 1. Identify Languages and Frameworks

Before scanning, inspect the repo:

```bash
rg --files | sed -n '1,120p'
```

Classify:
- Primary languages.
- Web frameworks.
- Package managers and lockfiles.
- Generated directories to exclude.
- Test fixtures that may intentionally contain insecure samples.

### 2. Verify Semgrep

```bash
semgrep --version
```

If missing, recommend official installation. For one-off local scans, a package manager or containerized Semgrep run is usually enough.

### 3. Run Baseline SAST

```bash
semgrep scan --config auto
```

For stricter security-focused scans:

```bash
semgrep scan --config p/security-audit
semgrep scan --config p/owasp-top-ten
```

For JSON output:

```bash
semgrep scan --config auto --json --output semgrep-results.json
```

For SARIF:

```bash
semgrep scan --config auto --sarif --output semgrep-results.sarif
```

### 4. Triage Findings

For each finding, record:
- Rule ID.
- File and line.
- Vulnerability class.
- Source and sink, if dataflow is available.
- User-controlled input evidence.
- Exploit preconditions.
- Suggested fix and regression test.

Prioritize:
1. Injection, deserialization, auth bypass, SSRF, path traversal, and unsafe crypto.
2. Findings in production paths over tests or examples.
3. Framework-specific high-confidence rules.
4. Repeated patterns that deserve custom guardrails.

### 5. Write Custom Rules When Needed

Use custom rules when the project has a known unsafe wrapper or banned API:

```yaml
rules:
  - id: no-dangerous-shell
    message: Avoid shell=True with interpolated input.
    severity: ERROR
    languages: [python]
    patterns:
      - pattern: subprocess.run($CMD, shell=True, ...)
```

Validate the rule with positive and negative examples before adding it to CI.

### 6. Remediate

For code fixes:
- Prefer framework-native safe APIs.
- Add tests for the vulnerable path.
- Avoid broad sanitizers that hide root causes.
- Keep suppressions narrow and justified.

For dependency findings:
- Prefer package-manager native updates.
- Check whether the vulnerable dependency is reachable.
- Treat supply-chain results as complementary to OSV, Grype, Trivy, or Snyk scans.

## Common Patterns

### Pull Request CI

```yaml
name: semgrep
on: [pull_request]
jobs:
  semgrep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Semgrep scan
        run: semgrep scan --config auto --error
```

### Project Rule Directory

```text
.semgrep/
  rules/
    no-dangerous-shell.yml
    no-raw-sql-wrapper.yml
  tests/
    no-dangerous-shell.py
```

### Finding Report Template

```markdown
## Semgrep Finding

- Rule:
- Severity:
- Location:
- User input source:
- Sensitive sink:
- Exploit path:
- Fix:
- Test:
- Suppression status:
```

## Interpretation Rules

- Semgrep is strongest when rules match the language and framework accurately.
- Do not report test fixtures, docs, or intentionally vulnerable examples unless they can ship.
- A finding without a feasible data path may be a hardening recommendation rather than a vulnerability.
- Use custom rules for local conventions; do not force generic rules to carry all policy.
- Keep false-positive feedback in rule tests so the signal improves over time.

## Boundaries

- Do not upload private code to a hosted service without approval.
- Do not suppress a rule across the entire repo unless the pattern is demonstrably irrelevant.
- Do not claim SAST coverage means dependency or runtime security is complete.
- Do not auto-fix security code without running tests around the behavior.
- Do not scan vendored dependencies as first-party code unless the user asks.

## Reference Sources

- Semgrep docs: https://semgrep.dev/docs/
- Running rules: https://semgrep.dev/docs/running-rules/
- Semgrep Supply Chain overview: https://semgrep.dev/docs/semgrep-supply-chain/overview/
