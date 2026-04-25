# Kubernetes Manifest Scaffolding Reference

Purpose: Scaffold raw Kubernetes manifests (Deployment, Service, Ingress, ConfigMap, Secret) and kustomize overlays for a workload that does not yet need full Helm packaging. Covers label conventions, namespace layout, resource requests/limits defaults, and probe wiring so the workload is admission-safe on first apply.

## Scope Boundary

- **Scaffold `k8s`**: raw manifest authoring and kustomize overlay layout (Deployment/Service/Ingress/ConfigMap/Secret, labels, namespace, requests/limits, probes).
- **Scaffold `helm`**: reusable, versioned chart packaging. If the workload must ship to 3+ environments or multiple tenants, escalate from `k8s` to `helm`.
- **Scaffold `terraform`**: cluster-level provisioning (EKS / GKE / AKS control plane, node groups, IRSA). Manifests live in `k8s`; the cluster that runs them lives in `terraform`.
- **Pipe (elsewhere)**: CI/CD wiring — `kubectl apply -k`, `kustomize build`, ArgoCD / Flux sync. `k8s` produces the manifests; `Pipe` wires the rollout.
- **Gateway (elsewhere)**: public API contract, versioning, breaking-change review. Ingress *routing* lives in `k8s`; API *rules* (auth, rate limit, schema) live in `Gateway`.

If the request is "package this workload for reuse" → `helm`. If it is "ship this single workload to one cluster" → `k8s`.

## Workload Shape (minimum set)

| Resource | Required? | Notes |
|----------|-----------|-------|
| `Namespace` | ✓ | One namespace per team or per bounded context; never deploy to `default`. |
| `Deployment` | ✓ | `replicas: 2` minimum for anything fronted by a Service; single-replica only for non-HA jobs. |
| `Service` | ✓ | `ClusterIP` by default; `LoadBalancer` only when ingress controller is absent. |
| `Ingress` | conditional | Required when HTTP(S) is exposed outside the cluster. |
| `ConfigMap` | conditional | Non-sensitive config. One CM per concern; avoid the "god CM". |
| `Secret` | conditional | Prefer `ExternalSecrets` / CSI driver over raw `Secret` objects. |
| `PodDisruptionBudget` | ✓ for HA | `minAvailable: 1` minimum for multi-replica workloads. |
| `HorizontalPodAutoscaler` | conditional | Only after resource requests are realistic (see defaults below). |

## Label & Annotation Convention

Use the recommended Kubernetes labels — they are free, queryable, and required by many tools (ArgoCD, Prometheus operator).

```yaml
metadata:
  labels:
    app.kubernetes.io/name: payments-api
    app.kubernetes.io/instance: payments-api-prod
    app.kubernetes.io/version: "1.24.3"
    app.kubernetes.io/component: api
    app.kubernetes.io/part-of: payments
    app.kubernetes.io/managed-by: kustomize
```

Selector labels (`Deployment.spec.selector.matchLabels`) must be a stable subset — never include `version` or `instance` in selectors, they break rolling updates.

## Resource Requests / Limits Defaults

Never ship without requests. Unrequested pods land in `BestEffort` QoS and are evicted first.

| Workload type | requests.cpu | requests.memory | limits.cpu | limits.memory |
|---------------|--------------|-----------------|------------|---------------|
| Small API | `100m` | `128Mi` | `500m` | `256Mi` |
| Standard API | `250m` | `512Mi` | `1000m` | `1Gi` |
| Batch / worker | `500m` | `1Gi` | *(no limit)* | `2Gi` |
| Sidecar (log/proxy) | `50m` | `64Mi` | `200m` | `128Mi` |

Prefer omitting `limits.cpu` (CPU throttling hurts latency more than it helps); always set `limits.memory` to prevent noisy-neighbor OOM cascade.

## Probes

Liveness and readiness are not optional. Startup probe is required for slow-booting apps (>10s).

```yaml
readinessProbe:
  httpGet: { path: /healthz, port: 8080 }
  periodSeconds: 5
  failureThreshold: 3
livenessProbe:
  httpGet: { path: /livez, port: 8080 }
  periodSeconds: 15
  failureThreshold: 3
  initialDelaySeconds: 30
startupProbe:
  httpGet: { path: /healthz, port: 8080 }
  periodSeconds: 5
  failureThreshold: 30  # allow 150s for JVM / cold-cache warmup
```

Never point liveness at `/` or any path that touches downstream dependencies — liveness failure restarts the pod and cascades an outage through the whole tier.

## Kustomize Overlay Layout

```
k8s/
  base/
    kustomization.yaml
    namespace.yaml
    deployment.yaml
    service.yaml
    configmap.yaml
  overlays/
    dev/
      kustomization.yaml     # patches replicas=1, lower requests
      config-patch.yaml
    staging/
      kustomization.yaml
    prod/
      kustomization.yaml     # patches replicas, HPA, PDB, prod image tag
      hpa.yaml
      pdb.yaml
```

Use `kustomization.yaml` `images:` to pin tags per overlay. Use `configMapGenerator` / `secretGenerator` to avoid drift from hand-edited YAML.

## Secret Handling

Raw `Secret` objects are base64, not encrypted. Three acceptable paths:

1. **External Secrets Operator** (ESO) → pulls from AWS Secrets Manager / GCP Secret Manager / Vault.
2. **Secrets Store CSI Driver** → mounts secrets as files, no K8s `Secret` object at all.
3. **Sealed Secrets** (Bitnami) → when the repo must be the source of truth and no secret manager exists.

Never commit a `Secret` with real data, even in `dev/`. Commit a placeholder and let ESO / CSI hydrate.

## Anti-Patterns

- Deploying to `default` namespace — collides with cluster tooling and breaks RBAC granularity.
- `latest` image tag — Kubernetes will not pull-refresh a running pod, and rollback becomes impossible.
- Missing `resources.requests` — evicted first under pressure, kills HPA accuracy.
- `readinessProbe` pointing at a path that exercises the database — startup storms and thundering-herd restarts.
- Single-replica `Deployment` behind a `Service` with no PDB — rolling node drain = full outage.
- One monolithic `ConfigMap` shared across unrelated workloads — changing one key restarts every consumer.
- Including `version` label in `selector.matchLabels` — makes rolling updates orphan the old ReplicaSet.
- Baking environment config into the image — breaks the 12-factor boundary and forces a rebuild per env.
- Setting `limits.cpu` aggressively on latency-sensitive APIs — CPU throttling shows up as p99 spikes.
- Using `hostNetwork: true` or `hostPath` volumes without a documented reason — breaks admission policies and portability.

## Handoff

When the `k8s` manifests are ready:

- **To Pipe**: the `kustomize build overlays/<env>` command, the image tag convention, and the promotion flow (dev → staging → prod). Pipe wires `kubectl apply` / ArgoCD sync / Flux Kustomization.
- **To Sentinel**: RBAC assumptions, `ServiceAccount` scope, `NetworkPolicy` posture (default-deny or not), and secret-handling path (ESO / CSI / Sealed Secrets).
- **To Beacon**: probe endpoints, Prometheus scrape annotations (`prometheus.io/scrape`, `prometheus.io/port`), and the metrics/log labels Beacon will key dashboards on.
- **To Canvas**: topology — namespaces, services, ingress routes — so Canvas can render the cluster view.
- **Upgrade path**: if the workload is about to be installed into a second cluster or handed to another team, re-scaffold as a Helm chart via `scaffold helm`.
