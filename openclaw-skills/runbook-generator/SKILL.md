---
name: runbook-generator
description: 'Write or review operational runbooks for deployment, rollback, incidents, recovery, and maintenance using concrete commands and verification evidence.'
zh_description: "用于基于仓库和平台证据编写安全、可演练、可验证的生产运维 Runbook。"
version: "2.0.1"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["generator", "runbook", "operations", "sre", "safety"]'
created_at: "2026-03-04"
updated_at: "2026-09-06"
quality: 5
complexity: "advanced"
---

# Runbook Generator

Create operator-ready procedures from evidence. Never invent commands, account
names, URLs, thresholds, rollback behavior, or escalation contacts.

## Required Inputs

Collect before writing:

- service and environment in scope
- repository configuration and deployment manifests
- current platform/provider documentation
- dependency and data-store topology
- observability links and known-good health signals
- change authority, approval boundary, and escalation owner
- recovery objectives when relevant: RTO, RPO, and maximum tolerated impact

If any production-critical input is unavailable, mark it `TBD — owner required`
instead of supplying a plausible value.

## Evidence Discovery

Inspect likely sources:

```bash
rg --files -g 'Dockerfile*' -g 'docker-compose*.yml' -g 'compose*.yaml'
rg --files -g '.github/workflows/*.yml' -g 'terraform/**' -g 'k8s/**'
rg --files -g 'vercel.json' -g 'fly.toml' -g 'render.yaml'
rg -n "DATABASE_URL|migrate|rollback|health|readiness|liveness" .
```

Read the actual scripts and provider configuration before quoting a command.
Confirm current CLI syntax against official documentation when the platform may
have changed.

## Safety Classification

Classify every step:

| Class | Meaning | Required handling |
|---|---|---|
| Read-only | Observes state | Safe to rehearse with non-secret fixtures |
| Reversible | Changes state with a proven undo | State precondition and rollback |
| Destructive | Deletes, truncates, resets, rotates, or revokes | Explicit approval and backup evidence |
| Irreversible | Cannot restore exact prior state | Separate break-glass procedure |

Never present destructive database reset, force push, bucket deletion, secret
revocation, or irreversible migration as a routine rollback.

In particular, commands such as `prisma migrate reset`, `DROP`, `TRUNCATE`,
`kubectl delete`, `terraform destroy`, and `git push --force` require a
destructive-operation warning and must not appear as the default production
path.

## Runbook Structure

Use this structure:

```markdown
# <Procedure name>

## Scope and owner
- Service:
- Environments:
- Primary owner:
- Escalation:
- Last rehearsed:

## Preconditions
- Required access:
- Change ticket or incident:
- Backup / restore evidence:
- Maintenance window:
- Known-good version:

## Stop conditions
- Abort when:
- Escalate when:

## Procedure
### Step 1 — <read-only preflight>
Command:
Expected evidence:
Failure action:

## Verification
- User-visible signal:
- Service health:
- Data integrity:
- Error and saturation signals:

## Rollback or recovery
- Trigger:
- Application rollback:
- Data recovery:
- Verification:

## Evidence record
- Operator:
- Start/end time:
- Commands executed:
- Links to logs, deploys, backups, and incident:
```

## Procedure Rules

For every mutating step:

1. State the precondition.
2. Show the smallest scoped command.
3. Describe expected output without fabricating exact IDs.
4. Define a stop condition.
5. Define the verification signal.
6. Define the recovery action.

Prefer commands that expose a plan or preview:

```bash
terraform plan -out=tfplan
kubectl diff -f k8s/
helm diff upgrade <release> <chart>
```

Do not hide failures with `|| true`, broad exception handling, or unbounded
retry loops.

## Database Changes

Treat application rollback and data rollback as separate operations.

- Confirm whether the migration is backward compatible.
- Prefer expand/migrate/contract for schema changes.
- Record backup timestamp and tested restore procedure.
- Do not assume down migrations are safe.
- Use a restore into an isolated environment to prove backup usability.
- Define reconciliation for writes that occurred after the backup.

If a migration is irreversible, say so and define forward recovery.

## Incident Runbooks

Start with containment and evidence preservation:

1. Confirm impact from at least two independent signals.
2. Declare severity using the organization's actual policy.
3. Freeze unrelated changes.
4. Capture timestamps, deploy versions, and relevant telemetry.
5. Apply the least invasive mitigation.
6. Verify recovery from the user's perspective.
7. Preserve a timeline for follow-up analysis.

Avoid commands that destroy forensic evidence before it is captured.

## Validation and Rehearsal

Validate runbooks outside production:

- lint every command and configuration fragment
- run read-only preflights against staging
- rehearse rollback or restore with representative data
- verify permissions using the operator role, not an admin shortcut
- ask a second operator to follow the runbook without oral guidance
- record ambiguities and update the document

A runbook is not production-ready until its highest-risk recovery path has been
rehearsed or explicitly marked untested.

## Freshness

Link each operational assumption to its source file or official document.
Re-review when any of these change:

- deployment workflow or infrastructure code
- schema or migration tooling
- provider CLI/API version
- alert thresholds or dashboards
- service ownership or escalation policy
- authentication and secret-management flow

## Output Contract

Return:

- runbook path or complete Markdown
- evidence inspected
- unresolved `TBD` items and owners
- destructive or irreversible steps
- rehearsal status
- next review trigger

Do not claim a runbook is safe merely because commands are syntactically
valid. Safety requires scoped authority, recoverability, and observed
verification.
