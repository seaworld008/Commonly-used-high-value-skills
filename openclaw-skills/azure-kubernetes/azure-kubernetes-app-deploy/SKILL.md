---
name: azure-kubernetes-app-deploy
description: 'Use when deploying an existing web application or API to an already-running Azure Kubernetes Service cluster. Detects the framework, generates a Dockerfile and Kubernetes manifests, validates against AKS Deployment Safeguards, and deploys with verification. WHEN: deploy app to AKS, deploy to existing AKS cluster, containerize app for Kubernetes, generate K8s manifests for Azure, set up CI/CD for AKS, my AKS deployment is failing safeguard checks, I have a Django/Express/Spring Boot app to run on AKS. DO NOT USE FOR: creating or provisioning an AKS cluster (use azure-kubernetes), assessing migration to AKS Automatic (use azure-kubernetes-automatic-readiness), or deploying to non-AKS targets like Web Apps, Container Apps, or Functions.'
license: MIT
metadata:
  author: Microsoft
  version: "1.0.0"
tags: '[azure, kubernetes, deployment, aks]'
quality: 2
---

# Deploy to AKS

**Use when:** deploying a web app/API to AKS; containerizing for Kubernetes; generating manifests; AKS CI/CD; DS001–DS013 failures.

**Not for:** provisioning clusters (`azure-kubernetes`), AKS Automatic readiness (`azure-kubernetes-automatic-readiness`), non-AKS targets.

## Workflow

Requires: existing AKS cluster, `az login`, `kubectl` configured. Follow `phases/quick-deploy.md`. On failure: `references/rollback.md`.

## References

- [detection.md](./references/detection.md) — framework/port/health detection
- [safeguards.md](./references/safeguards.md) — DS001-DS013 checklist
- [workload-identity.md](./references/workload-identity.md) — Workload Identity setup
- [rollback.md](./references/rollback.md) — recovery procedures
- [base-images.md](./references/base-images.md) — base image policy and `<LATEST_STABLE_*>` resolution

## Knowledge Packs

Load `knowledge-packs/frameworks/<framework>.md` per detected framework. Available: `spring-boot`, `express`, `nextjs`, `fastapi`, `django`, `nestjs`, `aspnet-core`, `go`, `flask`

## Templates

`templates/` (dockerfiles/, k8s/, github-actions/, mermaid/).

<!-- LOCAL-QUALITY-SUPPLEMENT:START -->
## Usage Notes

Treat the app-deploy workflow as a controlled production change. Confirm the
target subscription, cluster context, namespace, image registry, and rollback
point before generating or applying manifests.

## Common Pattern

```text
1. Detect the application framework, port, health endpoint, and build command.
2. Generate the smallest applicable Dockerfile and Kubernetes manifests.
3. Validate the manifests and Deployment Safeguards before changing the cluster.
4. Apply to a non-production namespace or staged environment first.
5. Verify rollout status, probes, logs, service routing, and workload identity.
6. Stop and follow references/rollback.md when verification fails.
```

## Boundaries

- Never invent registry, cluster, subscription, namespace, or secret values.
- Do not replace a working deployment strategy without showing the proposed
  manifest diff and obtaining the user's authorization.
- Keep generated credentials out of Docker build arguments, manifests, logs,
  and command history.
- Prefer immutable image digests for production rollouts.
- This supplement adds repository quality and safety guidance; the upstream
  Microsoft workflow and templates remain authoritative.
<!-- LOCAL-QUALITY-SUPPLEMENT:END -->
