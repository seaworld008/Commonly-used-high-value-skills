---
name: saas-scaffolder
description: 'Build a SaaS application or vertical slice from a validated brief, covering authentication, tenancy, persistence, billing, deployment, and acceptance checks.'
zh_description: "用于依据已验证产品需求搭建可演进的 SaaS 垂直切片，并覆盖鉴权、租户、计费、监控和验收。"
version: "2.0.1"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["design", "product", "saas", "scaffolder", "full-stack"]'
created_at: "2026-03-04"
updated_at: "2026-09-06"
quality: 5
complexity: "advanced"
---

# SaaS Scaffolder

Build one deployable vertical slice. Do not generate a large starter kit whose
authentication, billing, and data model have never worked together.

## Preconditions

Require:

- target user and primary paid outcome
- first end-to-end workflow
- tenant model: personal, workspace, organization, or hybrid
- billing unit and entitlement model
- data sensitivity and compliance constraints
- deployment environment and existing repository conventions

If the product brief is still ambiguous, refine it before scaffolding.

## Discover the Current Stack

For an existing repository, inspect before choosing dependencies:

```bash
rg --files -g 'package.json' -g 'pyproject.toml' -g 'go.mod'
rg --files -g '*lock*' -g 'Dockerfile*' -g '.github/workflows/*'
rg -n "auth|session|tenant|workspace|organization|stripe|billing|migration" .
```

Preserve the established package manager, framework, ORM, test runner, linting,
component library, and deployment target unless the user explicitly requests a
migration.

For a greenfield project, verify current stable versions and setup commands
against official documentation at implementation time. Do not hard-code
framework major versions or copy authentication middleware from old examples.

## Architecture Decisions

Record a short decision table:

| Concern | Decision | Evidence | Revisit trigger |
|---|---|---|---|
| Web/runtime |  | official docs / repository | unsupported runtime |
| Authentication |  | threat model and provider docs | identity model changes |
| Tenancy |  | product contract | shared workspace required |
| Database |  | access and consistency needs | scale or residency change |
| Billing |  | price and entitlement model | pricing migration |
| Jobs |  | latency and retry needs | synchronous path exceeds budget |
| Deployment |  | environment constraints | regional/compliance change |

Choose dependencies for the first workflow, not for hypothetical scale.

## Workflow: Required Vertical Slice

Implement the smallest slice that proves:

1. a user can sign in
2. the user can create or enter the correct tenant
3. authorization protects tenant-owned data
4. the primary resource can be created, viewed, and updated
5. entitlement checks gate the paid action
6. the workflow emits observable success and failure signals
7. tests exercise the public boundary
8. the slice deploys to a non-production environment

Do not claim “production-ready” until this slice works end to end.

## Authentication and Sessions

- Use the current official integration for the selected framework.
- Validate redirect and callback URLs by environment.
- Store secrets only in environment or secret management.
- Protect server-side actions independently from UI visibility.
- Rotate sessions or tokens after privilege changes.
- Define account deletion, recovery, and provider unlinking behavior.

Never infer authorization from a client-supplied role or tenant identifier.

## Tenancy and Authorization

Model tenant ownership explicitly:

```text
users
tenants
memberships(user_id, tenant_id, role)
resources(tenant_id, ...)
```

Every tenant-owned query and mutation must be scoped by trusted server-side
tenant context. Add negative tests proving that one tenant cannot read or
modify another tenant's records.

Use database row-level security only when its policies are tested as a primary
authorization boundary; do not assume enabling RLS makes access secure.

## Billing and Entitlements

Separate:

- provider customer/subscription state
- internal plan and entitlement state
- metered usage
- invoice/payment history

Treat webhooks as untrusted, duplicated, delayed, and out of order:

- verify signatures against the raw request body
- store provider event IDs for idempotency
- process asynchronously when appropriate
- reconcile periodically with provider state
- test cancellation, failed payment, upgrade, downgrade, and replay

Do not gate features only from client-visible price or plan names.

## Database and Migrations

- generate migrations from reviewed schema changes
- keep migrations deployable independently from application rollout
- prefer backward-compatible expand/migrate/contract changes
- provide seed data only for local/test environments
- never use reset or destructive migration commands in production instructions
- include indexes and uniqueness constraints that enforce product invariants

## Background Work

Use a job system only when work outlives the request or requires retry.
Define:

- idempotency key
- retry policy and maximum attempts
- timeout and cancellation
- dead-letter handling
- user-visible status
- trace/correlation identifier

## Observability

Add structured signals for:

- sign-in and authorization failures
- primary workflow latency and error rate
- webhook verification and processing
- job retries and dead letters
- database saturation and migration status

Exclude secrets, raw payment data, and sensitive user content from logs.

## Project Shape

Prefer a small, discoverable layout:

```text
app-or-src/
  routes-or-pages/
  domain/
  data/
  auth/
  billing/
  jobs/
tests/
  unit/
  integration/
  e2e/
docs/
  decisions/
```

Follow the repository's existing layout when present.

## Verification

Run the repository's real checks:

```bash
<package-manager> lint
<package-manager> typecheck
<package-manager> test
<package-manager> build
```

Add end-to-end coverage for:

- sign-up or sign-in
- tenant boundary denial
- primary resource happy path
- entitlement denied and allowed paths
- webhook replay
- deployment health endpoint

Use local provider emulators or signed fixtures when available. Never exercise
live billing or production mutations during routine verification.

## Delivery Contract

Return:

- implemented vertical slice
- architecture decision table
- environment variable template without secret values
- migrations and rollback/forward-recovery notes
- tests and exact validation results
- deployment instructions for a non-production environment
- known gaps, security assumptions, and next slice

Avoid placeholder integrations that compile but cannot complete the user
workflow.
