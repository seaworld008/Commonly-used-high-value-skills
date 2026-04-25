# Supply Chain Attack Design Reference

Purpose: Model supply chain attack paths against the build and distribution pipeline, and validate that dependency ingestion, build-time execution, and artifact signing hold up against realistic adversary tradecraft. Output is a scenario set with provenance-verification gaps and remediation guidance — not live exploitation of third-party infrastructure.

## Scope Boundary

- **Breach `supply`**: adversary-path modeling across dependency ingestion, build-tool trust, artifact signing, and registry consumption. Includes SBOM analysis, SLSA provenance verification, in-toto attestation design, and registry-pinning review.
- **Sentinel (elsewhere)**: static scanning of manifests, lockfiles, secrets, and known-CVE matches in dependencies. Sentinel finds "what is vulnerable" — Breach models "how an adversary reaches it."
- **Probe (elsewhere)**: DAST / runtime vulnerability scans on deployed services that consume the compromised artifacts.
- **Vigil (elsewhere)**: authoring detection rules for anomalous install-time network egress, postinstall script patterns, and registry-resolution anomalies.
- **Comply (elsewhere)**: regulatory alignment (SLSA level attestations, SSDF, EU CRA, Executive Order 14028 SBOM mandate).
- **Shift (elsewhere)**: migration away from compromised or abandoned packages once scenarios land.

If the question is "could an attacker get code into our build?" → `supply`. If it is "does what's in our build have known CVEs?" → Sentinel.

## Attack Surface Map

```
DEVELOPER → REGISTRY → BUILD → ARTIFACT → DISTRIBUTION → CONSUMER
    │          │         │        │            │            │
    │          │         │        │            │            └─ registry-pinning, integrity
    │          │         │        │            └─ signing infra, release pipeline
    │          │         │        └─ SBOM/SLSA provenance, reproducibility
    │          │         └─ postinstall scripts, lifecycle hooks, compiler trust
    │          └─ typosquat / dependency confusion / namespace takeover
    └─ IDE plugin trust, local dev-env, stolen maintainer creds
```

Breach models adversary movement across these arrows, not just the nodes.

## Attack Patterns

| Pattern | Primary vector | Example indicator | Framework |
|---------|----------------|-------------------|-----------|
| Dependency confusion | Internal name resolvable on public registry | Registry-resolution log shows public vs private order | CWE-1357, SLSA L2 gap |
| Typosquatting | Cousin name (`reqeusts`, `lodahs`) installed by typo | Install event on unknown package with recent first-publish | OWASP A06 |
| Compromised maintainer | Legitimate package, new malicious version | Rapid version bump with no changelog / dist-tag shuffle | ATT&CK T1195.002 |
| Build-tool compromise (SolarWinds-style) | Injected into the build system itself | Binary / lockfile drift between branches | ATT&CK T1195.002, SLSA L3 gap |
| Malicious postinstall | `postinstall`, `preinstall`, `gyp` scripts | Egress to unknown host at install time | CWE-506 |
| Registry namespace takeover | Expired maintainer email re-registered | Publish from new email on dormant package | ATT&CK T1195.001 |
| Dependency of dependency (transitive) | Deep-tree compromise invisible to direct-dep review | Lockfile delta only in transitive leaves | SLSA L2-3 gap |
| Source-code-management backdoor | Protected-branch bypass / force-push to vendored dep | Unsigned commit in vendored subtree | SLSA source requirements |

## Workflow

```
SCOPE       → enumerate dependency ecosystems in use (npm / PyPI / Maven /
              Go / crates / NuGet / container base / VSCode extensions)
            → list internal registries and proxy caches
            → record SLSA level claimed vs observed; record signing posture

SBOM        → ingest CycloneDX or SPDX SBOM; bucket by ecosystem, direct vs
              transitive, version pinning, license
            → flag: unsigned, unpinned (^/~), recently-first-published,
              single-maintainer, domain-registration-expired contacts

MODEL       → map each attack pattern above to the environment
            → score: exploitability × blast radius × detection gap
            → mark which SLSA/in-toto control would have broken the chain

EXECUTE     → author scenario specs only; do NOT publish a real typosquat,
              do NOT push a real postinstall payload
            → draft table-top: "adversary publishes v2.3.1 of X — what
              alerts fire and when?"

REPORT      → findings with remediation, SLSA-level uplift recommendation,
              signing/attestation gaps, registry-pinning changes, provenance
              verification gate at CI
```

## SBOM Analysis (CycloneDX / SPDX)

- Prefer **CycloneDX** for security-first workflows (VEX support for known-exploitable triage); **SPDX** for license-first.
- Must include: `purl` coordinates, version, hash, supplier, dependency edges. Missing any of these downgrades the SBOM to unverifiable inventory.
- Re-generate on every build; an SBOM older than the artifact is a stale SBOM.
- VEX attachments mark which CVEs are unreachable — use before paging on them.
- Diff SBOMs between releases to detect unexpected transitive churn.

## SLSA Provenance and In-Toto Attestation

| SLSA Level | Expectation | Breach test |
|------------|-------------|-------------|
| L1 | Provenance exists | Is any provenance generated at all? |
| L2 | Hosted build, authenticated provenance | Can a developer forge provenance from a local build? |
| L3 | Non-forgeable, isolated build | Can a compromised build step inject into a sibling step? |
| L4 | Hermetic + reproducible | Does a second build produce byte-identical output? |

In-toto attestation shape to look for: `predicateType` (`slsa-provenance`, `vuln-scan`, `test-results`), signed by a build identity tied to Sigstore / Fulcio / offline key — not a shared long-lived secret.

Verification must happen at the **consumer** side (admission controller, CI gate, runtime policy), not at the publisher. Trusting your own publisher's claim is not provenance.

## Package-Registry Pinning

- Pin by **hash**, not version range. `^1.2.3` is a trust-on-first-use declaration; a hash pin is cryptographic.
- Use a **private proxy** (Artifactory, Nexus, Verdaccio, Sonatype) in front of public registries; scope internal names to private-only resolution.
- Explicit namespace / scope for internal packages (`@corp/*`) — prevents public-registry resolution collision.
- Disable implicit install-time script execution where the ecosystem allows (`npm --ignore-scripts` for audit runs, Bazel hermetic rules).
- Freeze the allow-list; any new dependency is an explicit PR with maintainer-review required.

## Anti-Patterns

- Trusting SBOM without provenance — the SBOM can be forged as easily as the build output.
- Signing only the final artifact — a compromised intermediate step gets signed too.
- Running SBOM scans only at release — build-time compromises happen before release.
- Treating `lockfile-only` review as supply chain due diligence — lockfiles encode versions, not intent or author trust.
- Allowing `postinstall` network egress in CI — legitimate packages rarely need it; adversarial ones always do.
- Relying on "popular package = safe" heuristics — ClawHub (Q1 2026) confirmed 5 of 7 top-downloaded agent skills as malware.
- Ignoring VSCode / IDE plugin and agent-skill ecosystems as supply chain — they execute in developer context with full credential access.
- SLSA-level claims without verification — unverified provenance is marketing, not a control.
- Pinning only direct dependencies — transitives are 80%+ of the attack surface.
- Internal-package name collisions with public registries and no namespace scoping — classic dependency-confusion setup.

## Handoff / Next Steps

- To **Sentinel**: list of dependencies flagged by the scenario model for targeted CVE + secret scanning prioritization.
- To **Probe**: deployed surface receiving the suspect artifacts — for runtime vulnerability confirmation.
- To **Vigil**: indicators of compromise (install-time egress patterns, rapid-publish dist-tags, maintainer-email anomalies) for Sigma / OSQuery / EDR rule authoring.
- To **Comply**: SLSA-level gap report mapped to SSDF / EO 14028 / EU CRA obligations and SBOM-delivery requirements.
- To **Shift**: migration plan off abandoned, single-maintainer, or compromised packages; Strangler Fig decommission path for wide-blast-radius deps.
- To **Scribe**: final supply chain assessment with scenario set, SBOM diff, SLSA uplift plan.
- Journal novel supply chain IoCs and provenance-forgery attempts in `.agents/breach.md`.
