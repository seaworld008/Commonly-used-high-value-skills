---
name: security-auditor
description: 'Security audit workflow for AI-generated application code, APIs, infrastructure changes, dependencies, secrets, auth flows, and pull requests before they ship.'
version: "1.0.0"
author: seaworld008
source: in-house
source_url: ""
license: MIT
tags: '[security, appsec, ai-generated-code, code-review, owasp, secrets, dependency-audit, threat-modeling]'
created_at: "2026-06-03"
updated_at: "2026-06-03"
quality: 4
complexity: advanced
---

# Security Auditor

Use this skill to audit AI-generated code and human-written changes before they are merged or deployed. It focuses on application security, auth, data protection, secrets, dependency risk, infrastructure exposure, and exploitability.

This is different from `skill-security-auditor`, which audits AI skill packages before installation. Use `security-auditor` for product code and repository changes.

## When to Use

- Reviewing AI-generated code for security flaws.
- Auditing pull requests that touch authentication, authorization, payments, user data, file upload, webhooks, secrets, infrastructure, or dependencies.
- Checking generated APIs, database queries, server actions, middleware, background jobs, or CI workflows.
- Validating that frontend changes do not expose privileged data or trust client-only checks.
- Investigating a suspected vulnerability or insecure pattern.
- Hardening code before release.
- Creating security regression tests for a fixed issue.

## Skip When

- The target is an AI skill package rather than application code. Use `skill-security-auditor`.
- The user requests a full formal penetration test, legal compliance certification, or production exploit attempt without authorization.
- The task is pure style review with no security relevance.

## Core Capabilities

1. Threat-model a change by assets, actors, trust boundaries, and abuse paths.
2. Review code for OWASP-style issues and framework-specific security mistakes.
3. Check authn/authz correctness beyond happy-path role checks.
4. Detect secret leakage, unsafe logging, and sensitive data exposure.
5. Review dependency and supply-chain risk.
6. Inspect infrastructure and CI changes for privilege escalation or exposure.
7. Produce actionable findings with severity, evidence, exploit path, and fix.
8. Recommend tests that prevent recurrence.

## Audit Sequence

Use this sequence for repository changes:

```text
1. Identify changed files and security-sensitive surfaces.
2. Map trust boundaries and protected assets.
3. Review input validation, auth, data access, side effects, and error paths.
4. Scan for secrets and dangerous APIs.
5. Check dependencies, CI, and infrastructure exposure.
6. Confirm mitigations with tests or concrete reasoning.
7. Report only actionable findings with severity and evidence.
```

## Threat Model Mini-Template

```markdown
## Assets
- User data:
- Credentials/tokens:
- Money or quota:
- Admin capabilities:

## Actors
- Anonymous:
- Authenticated user:
- Tenant member:
- Admin:
- External service:

## Trust Boundaries
- Browser to API:
- API to database:
- Webhook provider to app:
- CI to cloud:

## Abuse Cases
- ...
```

## High-Risk Surfaces

- Login, registration, password reset, MFA, SSO, sessions, cookies, and refresh tokens.
- Authorization middleware, RBAC, ABAC, tenant scoping, row-level security, and admin routes.
- File upload, image processing, archive extraction, document parsing, and media metadata.
- Webhooks, callbacks, OAuth redirects, and third-party integrations.
- Payment, billing, coupons, credits, usage limits, and subscription state.
- Search, filters, raw SQL, ORM query builders, GraphQL resolvers, and NoSQL queries.
- Server-side rendering, server actions, template rendering, markdown rendering, and HTML sanitization.
- Background jobs, queues, cron tasks, retries, idempotency, and event handlers.
- CI/CD workflows, deployment scripts, cloud roles, Kubernetes manifests, and Terraform.

## Code Review Checks

- Input validation happens at the server trust boundary.
- Client-side validation is treated only as UX, never as authorization.
- Authorization checks use server-known identity and tenant context.
- Database queries cannot cross tenant boundaries.
- Direct object references are scoped to the current principal.
- Secrets are read from secret stores and never logged.
- Errors do not reveal tokens, stack traces, SQL, internal paths, or PII.
- Passwords and tokens are hashed or stored using approved primitives.
- Session cookies use `HttpOnly`, `Secure`, appropriate `SameSite`, and bounded lifetime.
- CORS is explicit and does not allow credentials for arbitrary origins.
- File uploads validate type, size, extension, content, storage path, and serving mode.
- Webhooks verify signatures and timestamps before side effects.
- Mutating endpoints have CSRF protection where cookie auth is used.
- Rate limits protect login, password reset, OTP, invite, and expensive operations.
- Audit logs capture sensitive administrative changes.

## Dangerous Patterns

```text
eval(
new Function(
dangerouslySetInnerHTML
innerHTML =
child_process.exec
shell=True
pickle.loads
yaml.load(..., Loader=yaml.Loader)
SELECT ... ${userInput}
where: { tenantId: req.body.tenantId }
Access-Control-Allow-Origin: *
console.log(process.env
```

Treat these as prompts to inspect context. They are not automatically vulnerabilities, but they deserve evidence-based review.

## Dependency and Supply-Chain Checks

- Lockfile changes match package manifest changes.
- New dependencies are necessary, maintained, and license-compatible.
- Install scripts are not introduced without review.
- Package names are checked for typosquatting.
- Dependency audit results are triaged by exploitability, not just count.
- Container base images are pinned and scanned.
- CI actions are pinned by SHA where risk warrants.
- Generated code does not vendor unknown binaries.

## Infrastructure Checks

- Cloud roles use least privilege.
- Public buckets, databases, dashboards, queues, and admin panels are intentional.
- Security groups and ingress rules are narrowed.
- Kubernetes service accounts are scoped.
- Secrets are not placed in ConfigMaps, logs, artifacts, or build args.
- Terraform plans do not widen access unexpectedly.
- CI tokens are not available to untrusted fork pull requests.
- Production deploys require protected branch or environment controls.

## Severity Model

- Critical: unauthenticated or low-privilege path to data breach, remote code execution, credential theft, payment abuse, or full tenant escape.
- High: authenticated but realistic path to privilege escalation, sensitive data exposure, stored XSS, SSRF to sensitive network, or destructive action.
- Medium: constrained vulnerability requiring unusual preconditions or limited data impact.
- Low: defense-in-depth issue, missing hardening, weak diagnostics, or minor information leak.

## Finding Format

```markdown
## Findings
- [High] path/to/file.ts:42 - Missing tenant scope in project lookup.
  Evidence: The query uses `projectId` from params but does not constrain by `tenantId`.
  Impact: Any authenticated user who guesses an id can read another tenant's project.
  Fix: Add tenant scope from server session and add a regression test for cross-tenant access.
```

## Verification Commands

Use the repo's existing tools first. Common examples:

```bash
npm audit --audit-level=high
pnpm audit --prod
pip-audit
semgrep scan --config p/owasp-top-ten
gitleaks detect --no-git
trivy fs .
```

Do not invent a clean result. If a tool is unavailable or noisy, report that clearly.

## Security Regression Tests

For every confirmed vulnerability, recommend at least one test:

- Unauthorized user is denied.
- Wrong tenant is denied.
- Invalid signature is rejected.
- Malicious payload is escaped or sanitized.
- Dangerous file type is rejected.
- Duplicate webhook does not double-charge or double-apply state.
- Rate limit triggers after threshold.

## Anti-Patterns

- Treating AI-generated code as safe because it compiles.
- Reporting generic "use HTTPS" findings without repository evidence.
- Trusting frontend role checks.
- Fixing auth by hiding UI controls while API remains open.
- Logging whole request bodies.
- Adding broad try/catch that hides security failures.
- Dismissing dependency issues without checking reachability.
- Running exploit attempts against systems without authorization.

## Boundaries

This skill provides security review guidance, not legal certification. Stay within authorized local code, test systems, or user-approved targets. Do not exfiltrate secrets, exploit production systems, or provide offensive persistence instructions.
