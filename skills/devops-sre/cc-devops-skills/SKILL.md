---
name: cc-devops-skills
description: 'SRE, DevOps, Kubernetes, CI/CD, PromQL, Terraform, Docker, and incident operations playbook for building reliable delivery and operations workflows.'
zh_description: "用于cc、DevOps、技能，支持部署、监控、排障和发布管理。"
version: "1.0.0"
author: seaworld008
source: github:akin-ozer/cc-devops-skills
source_url: "https://github.com/akin-ozer/cc-devops-skills"
license: Apache-2.0
tags: '[sre, devops, kubernetes, cicd, promql, terraform, docker, observability, incident-response]'
created_at: "2026-06-03"
updated_at: "2026-06-03"
quality: 4
complexity: advanced
---

# CC DevOps Skills

Use this skill when working on infrastructure, delivery pipelines, Kubernetes operations, observability, PromQL, incident response, Terraform, Docker, shell automation, and reliability engineering. It provides a unified SRE/DevOps operating model rather than a single vendor-specific command set.

The skill is inspired by the Apache-2.0 `cc-devops-skills` repository, but this version is self-contained for this curated skill catalog.

## When to Use

- Designing, reviewing, or fixing CI/CD pipelines.
- Creating or validating Kubernetes manifests, Helm values, Kustomize overlays, or deployment workflows.
- Debugging pods, services, ingress, DNS, network policy, probes, autoscaling, or rollout issues.
- Writing PromQL queries, alert rules, recording rules, SLO dashboards, or runbooks.
- Building Dockerfiles, Compose stacks, image hardening, or multi-stage builds.
- Reviewing Terraform, Terragrunt, Ansible, or infrastructure-as-code changes.
- Handling incidents, postmortems, operational readiness, release safety, and rollback planning.
- Improving reliability, deployment frequency, recovery time, observability, and operational toil.

## Skip When

- The task is pure application logic without deployment, runtime, reliability, or operational impact.
- The user asks for business strategy, product design, or frontend-only polish.
- A cloud-provider-specific skill already covers the whole task more precisely, such as a deep Azure Kubernetes operation.

## Core Capabilities

1. Translate product and engineering needs into reliable delivery systems.
2. Build CI/CD workflows with clear stages, caching, artifact flow, gates, and rollback paths.
3. Design Kubernetes resources with probes, requests, limits, disruption budgets, security context, and deployment strategy.
4. Debug live clusters using repeatable evidence gathering.
5. Write PromQL that respects labels, cardinality, windows, and alert semantics.
6. Review infrastructure-as-code for drift, blast radius, secrets, and lifecycle risk.
7. Harden containers and supply-chain paths.
8. Produce incident runbooks and postmortem-ready timelines.

## Operating Principles

- Automate the path, but make the failure mode visible.
- Prefer declarative infrastructure and reproducible builds.
- Treat secrets as toxic data: never print, commit, or echo them.
- Every alert needs an owner, severity, symptom, impact, and action.
- Every deployment needs a rollback or forward-fix decision point.
- Production changes should be observable before they are trusted.
- CI should fail early on cheap checks and reserve expensive checks for later gates.
- Kubernetes readiness is not the same as liveness; do not use one probe for both.
- PromQL queries must be tested against expected label sets and time windows.

## CI/CD Workflow

Use this pipeline shape unless the repo already has a stronger local convention:

```yaml
stages:
  - lint
  - unit-test
  - build
  - security-scan
  - integration-test
  - package
  - deploy-staging
  - smoke-test
  - promote-production
```

For each stage, define:

- Inputs and outputs.
- Cache keys and invalidation rules.
- Required secrets and their scope.
- Failure ownership.
- Timeout.
- Retry policy.
- Artifact retention.
- Required status checks before merge.

## CI/CD Review Checklist

- Build is deterministic and does not depend on local developer state.
- Lockfiles are respected.
- Tests run in the same major runtime version used in production.
- Secrets are read from the platform secret store, not committed files.
- Deployment jobs require protected environments or approvals when needed.
- The pipeline uploads test results, coverage, logs, and build artifacts.
- Rollbacks are documented and tested.
- Concurrency controls prevent two production deploys racing.
- Scheduled jobs and branch filters cannot deploy unreviewed code.
- Container images are pinned by digest for production where feasible.

## Kubernetes Readiness Checklist

- `resources.requests` and `resources.limits` are set with realistic values.
- `readinessProbe` checks whether the pod can receive traffic.
- `livenessProbe` checks whether the process should be restarted.
- `startupProbe` protects slow boot paths.
- `PodDisruptionBudget` exists for replicated workloads.
- Deployment strategy is compatible with state and traffic behavior.
- `securityContext` drops unnecessary privileges.
- Service account permissions are least privilege.
- ConfigMaps and Secrets are mounted or injected intentionally.
- Ingress, service, and pod selectors match.
- HPA metrics are stable and not based on noisy low-volume signals.
- NetworkPolicy does not block required DNS, egress, or service traffic.

## Kubernetes Debug Flow

Use a read-only evidence path first:

```bash
kubectl get deploy,rs,pod,svc,ingress -n <namespace> -o wide
kubectl describe pod <pod> -n <namespace>
kubectl logs <pod> -n <namespace> --previous
kubectl get events -n <namespace> --sort-by=.lastTimestamp
kubectl rollout status deploy/<name> -n <namespace>
```

Then isolate by layer:

- Scheduling: pending pods, taints, node pressure, quotas.
- Image: pull errors, registry auth, platform mismatch.
- Config: missing env vars, invalid secret keys, wrong mount paths.
- Runtime: crash loops, OOMKilled, failed probes, dependency timeouts.
- Network: service selector, endpoints, DNS, ingress, TLS, network policy.
- Capacity: CPU throttling, memory pressure, queue depth, saturation.

## PromQL Patterns

Use rate windows that match scrape interval and user impact.

```promql
sum by (service) (
  rate(http_requests_total{status=~"5.."}[5m])
)
/
sum by (service) (
  rate(http_requests_total[5m])
)
```

For SLO burn alerts, prefer multi-window checks:

```promql
(
  job:slo_errors_per_request:ratio_rate5m > 14.4 * 0.001
and
  job:slo_errors_per_request:ratio_rate1h > 14.4 * 0.001
)
or
(
  job:slo_errors_per_request:ratio_rate30m > 6 * 0.001
and
  job:slo_errors_per_request:ratio_rate6h > 6 * 0.001
)
```

## PromQL Review Checklist

- Query uses `rate()` or `increase()` for counters.
- Aggregation keeps only labels needed for routing or diagnosis.
- Regex matchers do not explode cardinality.
- Alert window is long enough for the scrape interval.
- Alert has `for:` where short spikes should not page.
- Dashboard query and alert query agree on units.
- Recording rules name the unit and aggregation.
- Missing metrics are handled when absence itself is meaningful.

## Terraform and IaC Checks

- Pin provider versions.
- Keep state backend remote, locked, and encrypted.
- Review plan output for destructive actions before apply.
- Use modules for repeated infrastructure, not for single-use complexity.
- Keep secrets out of variables files and state where possible.
- Add lifecycle rules only with a clear reason.
- Detect drift before assuming code matches production.
- Prefer small, reviewable plans over giant mixed changes.

## Incident Response Flow

```text
1. Declare incident and assign roles.
2. Define user impact and start timeline.
3. Stabilize: rollback, disable feature, scale, or shed load.
4. Gather evidence without destroying state.
5. Communicate status on a fixed cadence.
6. Resolve or mitigate.
7. Capture follow-up actions with owners and dates.
```

## Anti-Patterns

- Paging on symptoms nobody can act on.
- Using CPU percentage alone as a service health signal.
- Deploying without smoke tests or rollback instructions.
- Running production migrations as an unobserved CI side effect.
- Giving CI broad cloud credentials across all branches.
- Using `latest` image tags in production.
- Adding Kubernetes liveness probes that restart slow but healthy apps.
- Writing PromQL with unbounded high-cardinality labels.

## Output Format

For reviews:

```markdown
## Findings
- Severity:
- Evidence:
- Impact:
- Fix:

## Validation
- Commands:
- Expected result:
```

For implementation:

```markdown
## Plan
- Delivery path:
- Rollback:
- Observability:
- Security:
```

## Boundaries

Do not run destructive cloud or cluster operations without explicit user approval. Prefer read-only inspection first. Never print or persist secrets.
