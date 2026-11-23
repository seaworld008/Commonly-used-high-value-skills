# AI-Generated Code & Pre-Ship Application Security Checks

Distilled from the retired `security-auditor` checklist to supplement `security-review` when auditing AI-generated features, server actions, APIs, dependencies, and infrastructure diffs.

## Rapid Threat Model Mini-Template

```markdown
## Assets
- User data / PII:
- Credentials / tokens / signing keys:
- Money / credits / quota:
- Admin / cross-tenant capabilities:

## Actors & Trust Boundaries
- Anonymous / Authenticated member / Tenant admin / External webhook
- Browser -> API | API -> DB / RLS | Webhook -> Handler | CI -> Cloud

## Abuse Paths
- ...
```

## AI-Generated Code Failure Patterns

AI-generated code often compiles cleanly and passes happy-path tests while omitting server-side trust boundaries:

- **Client-trusted identity or tenant**: trusting `req.body.tenantId`, `userId`, or role claims instead of server session context (`where: { tenantId: req.body.tenantId }`).
- **UI-only gating**: hiding buttons or checks in client components while leaving server actions, GraphQL resolvers, or API routes unguarded.
- **Unsafe sinks & serialization**: `eval(`, `new Function(`, `dangerouslySetInnerHTML`, `child_process.exec`, `shell=True`, `pickle.loads`, `yaml.load(..., Loader=yaml.Loader)`, or interpolated SQL (`SELECT ... ${userInput}`).
- **Over-permissive CORS & cookies**: `Access-Control-Allow-Origin: *` paired with credentials, or session cookies missing `HttpOnly`, `Secure`, or bounded `SameSite`.
- **Silent exception swallowing**: broad `try/catch` blocks that skip authorization checks or continue after partial state writes.
- **Debug leaks**: `console.log(process.env...)`, stack traces, internal paths, or raw SQL returned to clients.

## Dependency, Supply-Chain & Infrastructure Review

- Verify lockfile diffs match declared package manifest updates and inspect newly added install scripts or typosquatting risk.
- Confirm container base images are pinned, Terraform/K8s diffs maintain least privilege, and CI secrets are unavailable to untrusted fork PRs.

## Regression Test Minimums

For every confirmed defect, verify a negative and positive check covering:
- Unauthorized user and cross-tenant principal denial.
- Invalid webhook signatures or replayed idempotency keys rejected.
- Untrusted HTML/file uploads sanitized or restricted by content and root path.
