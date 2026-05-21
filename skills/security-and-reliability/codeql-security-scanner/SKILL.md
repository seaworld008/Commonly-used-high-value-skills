---
name: codeql-security-scanner
description: '用于通过 CodeQL 执行语义代码扫描、安全查询、自定义规则、SARIF 报告和 GitHub Code Scanning 集成。'
version: "1.0.0"
author: seaworld008
source: "in-house"
source_url: ""
tags: '[security, sast, codeql, code-scanning, github, sarif, custom-queries, appsec]'
created_at: "2026-05-20"
updated_at: "2026-05-20"
quality: 4
complexity: advanced
---

# CodeQL Security Scanner

## Trigger / When to Use

Use this skill when the user wants deep semantic code scanning, GitHub Advanced Security style analysis, custom CodeQL queries, SARIF output, or vulnerability investigation with CodeQL databases.

Good trigger phrases:
- "run CodeQL locally"
- "add CodeQL code scanning"
- "scan JavaScript for security issues"
- "write a CodeQL query"
- "upload SARIF to GitHub"
- "investigate a CodeQL alert"

## Core Capabilities

- Build CodeQL databases for supported languages.
- Run default and security-extended query suites.
- Produce SARIF reports for GitHub code scanning.
- Investigate dataflow-based vulnerabilities.
- Author and test custom queries for recurring insecure patterns.
- Integrate scans in GitHub Actions or local CI.

## Workflow

### 1. Identify Languages

Inspect the repository:

```bash
rg --files | sed -n '1,160p'
```

Determine:
- Primary language.
- Build command.
- Whether generated code should be excluded.
- Whether dependencies need to be installed before database creation.
- Whether multiple CodeQL databases are required for a polyglot repo.

### 2. Verify CodeQL CLI

```bash
codeql version
```

If missing, use official GitHub CodeQL CLI installation guidance. For GitHub-hosted workflows, prefer `github/codeql-action`.

### 3. Create a Database

For compiled languages, provide the real build command:

```bash
codeql database create codeql-db --language=java --command="mvn -DskipTests package"
```

For JavaScript or TypeScript:

```bash
codeql database create codeql-db --language=javascript-typescript
```

For Python:

```bash
codeql database create codeql-db --language=python
```

If database creation fails, fix dependency installation or build steps before analyzing.

### 4. Run Queries

Default query suite:

```bash
codeql database analyze codeql-db --format=sarif-latest --output=codeql.sarif
```

Security extended suite:

```bash
codeql database analyze codeql-db codeql/javascript-queries:codeql-suites/javascript-security-extended.qls --format=sarif-latest --output=codeql.sarif
```

Adapt the query pack path to the detected language and installed CodeQL pack layout.

### 5. Triage Alerts

For each alert:
- Query ID and suite.
- File and line.
- Source, sink, and path steps when available.
- User input control evidence.
- Exploitability in deployed configuration.
- Fix strategy and regression test.

Prioritize:
1. Dataflow alerts with realistic user-controlled input.
2. Authentication, authorization, injection, deserialization, SSRF, and path traversal.
3. Alerts in deployed services over test-only code.
4. Alerts recurring across many files.

### 6. Write or Run Custom Queries

Use custom queries when a project has its own framework wrappers:

```ql
/**
 * @name Example dangerous API use
 * @kind problem
 * @problem.severity warning
 * @security-severity 6.0
 * @id custom/dangerous-api
 */
import javascript

from CallExpr call
where call.getCalleeName() = "dangerousEval"
select call, "Avoid dangerousEval with untrusted input."
```

Keep custom queries versioned with tests where possible.

## Common Patterns

### GitHub Actions CodeQL

```yaml
name: codeql
on:
  pull_request:
  push:
    branches: [main]
jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: javascript-typescript
          queries: security-extended
      - uses: github/codeql-action/analyze@v3
```

### Local Investigation Checklist

```text
1. Reproduce the alert with CodeQL CLI.
2. Open path explanation and inspect each step.
3. Confirm source is user-controllable.
4. Confirm sink is security-sensitive.
5. Fix with framework-native safe API.
6. Add regression test.
7. Re-run the relevant query.
```

### Alert Report Template

```markdown
## CodeQL Alert

- Query:
- Severity:
- Location:
- Source:
- Sink:
- Path summary:
- Exploit condition:
- Fix:
- Test:
```

## Interpretation Rules

- CodeQL is strongest for semantic and dataflow problems, not package CVE inventory.
- Generated code and vendored code should usually be excluded from first-party triage.
- Build accuracy directly affects database quality for compiled languages.
- A path-problem alert deserves manual path validation before remediation.
- Custom query metadata matters for SARIF interpretation and alert severity.

## Boundaries

- Do not treat CodeQL as a replacement for dependency, container, host, or secret scanning.
- Do not upload SARIF from private code to an external system without approval.
- Do not silence alerts with broad query exclusions unless a rule is truly irrelevant.
- Do not patch code based only on a rule name; inspect the path and framework behavior.
- Do not ignore database creation warnings for compiled languages.

## Reference Sources

- CodeQL docs: https://codeql.github.com/docs/
- CodeQL queries: https://docs.github.com/en/code-security/reference/code-scanning/codeql/codeql-queries
- Writing CodeQL queries: https://codeql.github.com/docs/writing-codeql-queries/about-codeql-queries/
