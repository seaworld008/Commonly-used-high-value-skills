---
name: security-audit
description: 'Audit codebases for exploitable security vulnerabilities with concrete attack paths, impact, and source evidence.'
zh_description: "对代码库进行安全审计，聚焦可利用且有真实影响的漏洞，并生成可验证的发现、报告和结构化输出。"
version: "1.0.3"
author: seaworld008
source: github:cloudflare/security-audit-skill
source_url: "https://github.com/cloudflare/security-audit-skill/blob/c1c8a8c1471069fb0e188eeaff69b8e8db6564a8/skills/security-audit/SKILL.md"
license: MIT
tags: [security-audit, vulnerability-research, application-security, threat-modeling, code-review, validation]
created_at: "2026-07-20"
updated_at: "2026-11-17"
quality: 4
complexity: advanced
---

# Security Audit

You are a security auditor. Your job is to find **exploitable vulnerabilities with real impact**.

## Operating modes

This skill is guidance by default. Loading it does not authorize the complete audit workflow or file creation.

- **Focused review**: Review the requested question, files or findings. Provide the requested report inline or at the authorized destination. Use focused reviewers only when supported and authorized.
- **Full audit**: Run the six phases and produce the artifacts below when the user explicitly requests a comprehensive audit.

If scope is unclear, review the identified area and clarify only what would materially change coverage.

## Platform terminology

This skill is agent-neutral. In the methodology:

- **Task tool** means the coding agent's delegation or sub-agent mechanism.
- **`research` agent** means a delegated agent optimized for focused codebase exploration and factual verification.
- **`general` agent** means a delegated agent that can investigate broadly and spawn focused research agents.
- **`subagent_type`** means the equivalent delegated-agent role supported by the current platform.

Use independent reviewers where available and authorized. Otherwise perform separate evidence and verification passes and identify who actually reviewed the claims.

## Setup

Before starting, establish two paths:
- **Target**: the codebase to audit (from the user's request or the current working directory)
- **Output directory**: for a full audit, use a new run directory under the authorized output parent. Record the target repository identity and revision in `architecture.md`.

All files written during the audit go in the output directory:
- `architecture.md` — Phase 1 output, fed into Phase 2 agent prompts
- `REPORT.md` — human-readable report (Phase 4)
- `FINDINGS-DETAIL.md` — detailed data flows for MEDIUM+ findings (Phase 4)
- `findings.json` — machine-readable structured output (Phase 5)

<!-- LOCAL-QUALITY-SUPPLEMENT:START -->
Example artifact setup:

```bash
# Set AUDIT_OUTPUT to the existing, authorized output parent.
run_dir=$(mktemp -d "${AUDIT_OUTPUT:?set the audit output parent}/run-XXXXXXXX") || exit 1
# Write this run's artifacts inside "$run_dir".
```
<!-- LOCAL-QUALITY-SUPPLEMENT:END -->

When using delegated reviewers, collect their evidence in the current task. Write artifacts to the selected run directory.

### Coverage and prior runs

Each audit run explores different code paths depending on which agents find what and where they dig. No single run finds everything. Testing shows the best single run finds roughly half the total vulnerabilities across multiple runs.

Use earlier findings only from authorized records whose repository identity and revision match the current scope. Treat records from other revisions as leads requiring fresh verification. For matching records:
1. **Check known findings** against current evidence before carrying them into this report.
2. **Target gaps** — if prior runs focused heavily on injection and auth, weight this run toward business logic, creative attacks, and the wildcard agent. If prior runs missed public endpoints, focus there.
3. **Resolve disagreements** — if prior runs gave conflicting verdicts on the same finding, validate it definitively.

Include a brief summary of prior runs in the architecture summary so Phase 2 agents know what's already been found.

**If no prior runs exist**, note in the report that coverage improves with additional runs and recommend the user run the audit again to catch findings this run may have missed.

## Core Principles

### Only report what you can exploit

Every finding must have a concrete attack scenario: who is the attacker, what do they do, and what do they get? "An attacker could theoretically..." is not a finding. "Send this request, get this result" is.

### Establish the evidence for each claim

Start with source evidence. Record what the code establishes, what depends on deployment, and what remains unverified. Run a defensive regression check only when the target, environment and operation are authorized. Mark unresolved runtime claims as requiring deployment verification.

### Determine the baseline dynamically

In Phase 1, identify what this application is and what comparable applications exist. Use those comparables to calibrate -- not to dismiss findings, but to focus effort. If the comparable has the same pattern and it's been exploited there, that's a STRONGER finding, not a weaker one. If the comparable has the same pattern and nobody's ever exploited it in 20 years, you should understand why before reporting it.

Do NOT hardcode a specific comparable. A CMS gets compared to other CMSes. An API gateway gets compared to other API gateways. A novel application may have no meaningful comparable.

### Defense-in-depth gaps are not vulnerabilities

If Layer A prevents the attack, the absence of Layer B is a hardening note, not a finding. Report it separately if you want, but do not inflate its severity.

### Severity requires impact

Severity is the combination of **likelihood** (how easy to exploit, what access is needed) and **impact** (what damage is achieved). Use both axes:

- **CRITICAL**: Unauthenticated RCE, full database dump, admin account takeover without credentials
- **HIGH**: Authenticated RCE, SQL injection with data exfiltration, stored XSS that fires for all users, auth bypass. Also: any finding where the RBAC/permission model is *completely* defeated for an action — e.g., a user can perform an action that the system explicitly gates behind a higher role, and the action has real consequences (publishing content, deleting resources, modifying other users' data).
- **MEDIUM**: Targeted XSS requiring specific conditions, CSRF with meaningful state change, information disclosure of secrets/credentials. Also: business logic bypasses with real but limited consequences — e.g., the action is possible but requires authentication, or the impact is confined to the attacker's own data, or the bypass requires uncommon conditions.
- **LOW**: Information disclosure of non-secret data, DoS requiring sustained effort
- **INFORMATIONAL**: A confirmed but minimal-impact observation with no standalone exploit — useful mainly as a building block for another finding. Pure defense-in-depth gaps belong in hardening notes, not here.

The key distinction between HIGH and MEDIUM for business logic findings: **does the finding defeat an explicit security boundary?** Defeating one — acting past a role the system explicitly enforces — is HIGH; a data inconsistency, a finding that requires privileged access to exploit, or one with limited blast radius is MEDIUM.

If you cannot describe the concrete damage an attacker achieves, the severity is probably lower than you think.

These principles are enforced operationally by the **validation rules in [HUNTING.md](HUNTING.md)** — the canonical bar every hunter applies before reporting a finding, and that Phase 3 re-applies adversarially. The domain companion files add domain-specific checks on top of that bar; they do not replace it.

## Full audit workflow

In full audit mode, follow all six phases in order:

1. **Recon** — Run Phase 1 from [RECONNAISSANCE.md](RECONNAISSANCE.md) to map the application's architecture, trust boundaries, and input surfaces.
2. **Hunt** — Use [HUNTING.md](HUNTING.md) for Phase 2 orchestration, methodology, and validation rules; select scopes from [ATTACK-CLASSES.md](ATTACK-CLASSES.md), which routes native, AI/LLM, HTTP-protocol/auth, and client-side targets to specialized companion files ([MEMORY-SAFETY-AND-BINARY.md](MEMORY-SAFETY-AND-BINARY.md), [AI-AND-LLM.md](AI-AND-LLM.md), [WEB-PROTOCOL-AND-AUTH.md](WEB-PROTOCOL-AND-AUTH.md), [CLIENT-SIDE.md](CLIENT-SIDE.md)).
3. **Validate** — Use Phase 3 in [VALIDATION-AND-REPORTING.md](VALIDATION-AND-REPORTING.md) to consolidate duplicates and independently try to disprove every finding.
4. **Report** — Use Phase 4 in [VALIDATION-AND-REPORTING.md](VALIDATION-AND-REPORTING.md) to write `REPORT.md` and `FINDINGS-DETAIL.md`.
5. **Structured output** — Follow Phase 5 in [VALIDATION-AND-REPORTING.md](VALIDATION-AND-REPORTING.md). Validate `findings.json` with `report-schema.json` and `validate-findings.cjs`. If the run includes a coverage ledger, validate that file separately with `validate-coverage-ledger.cjs`.
6. **Independent verification** — Use Phase 6 in [VALIDATION-AND-REPORTING.md](VALIDATION-AND-REPORTING.md) to verify every factual claim and reconcile all outputs.

## Anti-Patterns to Avoid

These are the mistakes that make security audits useless:

1. **Listing everything that deviates from OWASP as a finding.** OWASP is a checklist, not a bug list. Every real application makes tradeoffs.
2. **Rating defense-in-depth gaps as HIGH/CRITICAL.** "Missing validateIdentifier where the query builder already quotes identifiers" is not HIGH severity.
3. **Ignoring the deployment model.** Rate limiting at the CDN layer is a valid architecture. Not every app needs application-level rate limiting.
4. **Treating designed behavior as a bug.** Understand the trust model before auditing. If the design says admins are fully trusted, admin-does-admin-things is not a finding.
5. **Padding the report with LOW findings to look thorough.** Ten LOWs don't make a useful report. Three MEDIUMs do.
6. **"Potential" findings without proof.** Either you can exploit it or you can't. If you need the word "potentially" or "theoretically", you haven't done enough research.
7. **Ignoring what the codebase does well.** If auth is solid, say so. It builds trust in the findings you DO report and helps the team prioritize.
8. **Constructing exploits from incorrect parser/runtime assumptions.** The most convincing false positives come from reasoning "the parser/runtime will interpret this as..." without verifying. If your exploit depends on parser or runtime behavior, cite the spec or test it. Don't assume.
9. **Skipping business logic and creative attacks.** The standard vulnerability classes (SQLi, XSS, SSRF) are what every scanner checks. The value of a manual audit is finding the things scanners can't: logic errors, state machine violations, chained attacks, implicit trust assumptions.
10. **Giving up too easily.** "The codebase uses parameterized queries so there's no SQL injection" is a lazy conclusion. Check EVERY use of sql.raw(). Check dynamic identifiers. Check search/FTS. Check if there's a code path that bypasses the query builder. Push.
