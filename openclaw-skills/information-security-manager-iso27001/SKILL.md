---
name: information-security-manager-iso27001
description: 'Design or audit ISO 27001 ISMS controls, security risk treatment, and compliance evidence, including healthcare and medical-device contexts.'
zh_description: "建立和审计 ISO 27001 信息安全管理体系及风险控制。"
version: "1.0.3"
author: alirezarezvani
source: "github:alirezarezvani/claude-skills"
source_url: "https://github.com/alirezarezvani/claude-skills/blob/main/ra-qm-team/skills/information-security-manager-iso27001/SKILL.md"
license: MIT
tags: '["security", "iso27001", "isms", "compliance", "risk-assessment", "governance", "agent-skill"]'
created_at: "2026-06-01"
updated_at: "2026-11-17"
quality: 4
complexity: intermediate
---

# Information Security Manager - ISO 27001

Implement and manage Information Security Management Systems (ISMS) aligned with ISO 27001:2022 and healthcare regulatory requirements.

---

## Table of Contents

- [Trigger Phrases](#trigger-phrases)
- [Quick Start](#quick-start)
- [Tools](#tools)
- [Workflows](#workflows)
- [Reference Guides](#reference-guides)
- [Validation Checkpoints](#validation-checkpoints)

---

## Trigger Phrases

Use this skill when you hear:
- "implement ISO 27001"
- "ISMS implementation"
- "security risk assessment"
- "information security policy"
- "ISO 27001 certification"
- "security controls implementation"
- "incident response plan"
- "healthcare data security"
- "medical device cybersecurity"
- "security compliance audit"

---

## Quick Start

### Run Security Risk Assessment

```bash
python scripts/risk_assessment.py --scope "patient-data-system" --assets assets.csv --format json --output risk_register.json
```

### Check Compliance Status

```bash
python scripts/compliance_checker.py --standard iso27001 --controls-file controls.csv
```

### Generate Gap Analysis Report

```bash
python scripts/compliance_checker.py --standard iso27001 --controls-file controls.csv --gap-analysis --output gaps.md
```

---

## Tools

### risk_assessment.py

Offline catalog scenario analysis supporting ISO 27001 Clause 6.1.2 workshops. Requires a supplied asset inventory or explicit `--demo`. Scope is only a report label: the script does not discover assets, scan systems, or verify threats, vulnerabilities or evidence authenticity. Existing user authorization is sufficient to run the appropriate mode.

**Usage:**

```bash
# Supplied assets; candidate scenarios, with unknown control effectiveness
python scripts/risk_assessment.py --scope "cloud-infrastructure" --assets assets.csv --format json --output risks.json

# Explicit synthetic healthcare demo
python scripts/risk_assessment.py --scope "example-ehr" --demo --template healthcare --format json --output demo_risks.json

# Conditional estimates from supplied control attestations
python scripts/risk_assessment.py --scope "ehr-system" --assets assets.csv --template healthcare --control-evidence control_evidence.csv --format json --output risks.json
```

**Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--scope` | Yes | Scope label, not discovery or evidence of system access |
| `--template` | No | Assessment template: `general`, `healthcare`, `cloud` |
| `--assets` | One input mode | Nonempty asset CSV; mutually exclusive with `--demo` |
| `--demo` | One input mode | Explicitly generate synthetic sample assets, labeled in every output format |
| `--control-evidence` | No | Control attestation CSV for supplied assets; unavailable with demo |
| `--output` | No | Output file (default: stdout) |
| `--format` | No | Output format: `json`, `csv`, `markdown` |

**Input contracts and interpretation:**

Asset CSV requires unique nonempty `id`, nonempty `name`, and `classification` from `critical`, `high`, `medium`, `low`, `minimal`; `type` and `owner` are optional. Empty or invalid inventories fail without producing a report. Example input (illustrative data, not a discovered inventory):

```csv
id,name,type,owner,classification
DB01,Example database,Information,Example owner,critical
```

Control evidence is matched by `asset_id` and catalog `threat_id` (T01–T05 of the selected template), not the generated risk rank. Example attestation schema; substitute reviewed evidence and measured effectiveness before use:

```csv
asset_id,threat_id,status,effectiveness,evidence_ref,assessed_by,assessed_at
DB01,T01,verified,0.5,review-record-001,Example assessor,2026-01-15
```

- A control is `unknown` unless its row has `status=verified`, finite effectiveness in [0,1], a nonempty evidence reference and assessor, and a valid ISO date/time no later than today. Missing, incomplete or unverified rows produce `null` residual estimates, never a default 70% reduction. Unknown/duplicate asset-threat pairs fail to avoid applying evidence to the wrong scenario.
- Complete attestations are labeled `reported_verified`: the script checks input completeness, does not open evidence references, and cannot establish authenticity, measurement quality, freshness or applicability. Residual results are conditional estimates using `max(1, ceil(catalog_likelihood × (1 − effectiveness))) × classification_impact`.
- All JSON, CSV and Markdown outputs identify demo status, asset/control sources, the bundled scenario catalog and limitations. Threats and vulnerability candidates remain unverified even with real assets and control records. Scores use assumed catalog likelihoods and classification-derived impact; treatment deadlines are suggestions. This is not a formal completed assessment or certification decision.

### compliance_checker.py

Summarize the implementation statuses you supply for the bundled control catalog. Both standard options use the same local catalog. The report covers only the selected catalog controls. A full ISO assessment and certification decision require independent review.

**Usage:**

```bash
# List the bundled controls as unassessed until statuses are supplied
python scripts/compliance_checker.py --standard iso27001

# Gap analysis with recommendations
python scripts/compliance_checker.py --standard iso27001 --controls-file controls.csv --gap-analysis

# Check specific control domains
python scripts/compliance_checker.py --standard iso27001 --controls-file controls.csv --domains "people,technological"

# Export compliance report
python scripts/compliance_checker.py --standard iso27001 --controls-file controls.json --output compliance_report.md
```

**Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--standard` | Yes | `iso27001` or `iso27002` |
| `--controls-file` | No | CSV with `control_id` (or `id`) and `status`, or a `.json` mapping such as `{"A.5.1": "implemented"}` |
| `--gap-analysis` | No | Include remediation recommendations |
| `--domains` | No | Specific control domains to check |
| `--output` | No | Output file path |

**Interpreting the report**

- Supply `implemented`, `partial`, or `not_implemented` based on your control records. A missing control, blank field, or unrecognized value is `unknown`. With no input every control is unassessed.
- Assessment coverage is the count of controls with recognized statuses divided by all selected catalog controls. The catalog score uses the same denominator, with one point for implemented and half a point for partial. If no controls have been assessed, the JSON score is `null` and Markdown shows `Unassessed`.
- Findings and remediation cover high and critical priority controls explicitly reported as `not_implemented`. Collect evidence for unknown controls before drawing conclusions.

---

## Workflows

### Workflow 1: ISMS Implementation

**Step 1: Define Scope and Context**

Document organizational context and ISMS boundaries:
- Identify interested parties and requirements
- Define ISMS scope and boundaries
- Document internal/external issues

**Validation:** Scope statement reviewed and approved by management.

**Step 2: Conduct Risk Assessment**

```bash
python scripts/risk_assessment.py --scope "full-organization" --assets assets.csv --template general --format json --output initial_risks.json
```

- Supply an actual asset inventory with owners and classifications
- Use catalog candidates to guide threat and vulnerability review
- Validate applicability and likelihood/impact with local evidence
- Review treatment options; unknown controls have no residual estimate

**Validation:** Review critical asset coverage and assigned owners against the supplied inventory. Script output alone does not validate observed risks.

**Step 3: Select and Implement Controls**

Map risks to ISO 27002 controls:

```bash
python scripts/compliance_checker.py --standard iso27002 --controls-file controls.csv --gap-analysis --output control_gaps.md
```

Control categories:
- Organizational (policies, roles, responsibilities)
- People (screening, awareness, training)
- Physical (perimeters, equipment, media)
- Technological (access, crypto, network, application)

**Validation:** Statement of Applicability (SoA) documents all controls with justification.

**Step 4: Establish Monitoring**

Define security metrics:
- Incident count and severity trends
- Control effectiveness scores
- Training completion rates
- Audit findings closure rate

**Validation:** Dashboard shows real-time compliance status.

### Workflow 2: Security Risk Assessment

**Step 1: Asset Identification**

Create asset inventory:

| Asset Type | Examples | Classification |
|------------|----------|----------------|
| Information | Patient records, source code | Confidential |
| Software | EHR system, APIs | Critical |
| Hardware | Servers, medical devices | High |
| Services | Cloud hosting, backup | High |
| People | Admin accounts, developers | Varies |

**Validation:** All assets have assigned owners and classifications.

**Step 2: Threat Analysis**

Identify threats per asset category:

| Asset | Threats | Likelihood |
|-------|---------|------------|
| Patient data | Unauthorized access, breach | High |
| Medical devices | Malware, tampering | Medium |
| Cloud services | Misconfiguration, outage | Medium |
| Credentials | Phishing, brute force | High |

**Validation:** Threat model covers top-10 industry threats.

**Step 3: Vulnerability Assessment**

```bash
python scripts/risk_assessment.py --scope "network-infrastructure" --assets assets.csv --format json --output scenario_risks.json
```

Use the catalog to plan evidence collection; it does not perform a vulnerability scan. Document independently observed vulnerabilities:
- Technical (unpatched systems, weak configs)
- Process (missing procedures, gaps)
- People (lack of training, insider risk)

**Validation:** Map independently collected scan results to the register; catalog vulnerability candidates are unverified.

**Step 4: Risk Evaluation and Treatment**

Calculate risk: `Risk = Likelihood × Impact`

| Risk Level | Score | Treatment |
|------------|-------|-----------|
| Critical | 20-25 | Immediate action required |
| High | 15-19 | Treatment plan within 30 days |
| Medium | 10-14 | Treatment plan within 90 days |
| Low | 5-9 | Accept or monitor |
| Minimal | 1-4 | Accept |

**Validation:** All high/critical risks have approved treatment plans.

### Workflow 3: Incident Response

**Step 1: Detection and Reporting**

Incident categories:
- Security breach (unauthorized access)
- Malware infection
- Data leakage
- System compromise
- Policy violation

**Validation:** Incident logged within 15 minutes of detection.

**Step 2: Triage and Classification**

| Severity | Criteria | Response Time |
|----------|----------|---------------|
| Critical | Data breach, system down | Immediate |
| High | Active threat, significant risk | 1 hour |
| Medium | Contained threat, limited impact | 4 hours |
| Low | Minor violation, no impact | 24 hours |

**Validation:** Severity assigned and escalation triggered if needed.

**Step 3: Containment and Eradication**

Immediate actions:
1. Isolate affected systems
2. Preserve evidence
3. Block threat vectors
4. Remove malicious artifacts

**Validation:** Containment confirmed, no ongoing compromise.

**Step 4: Recovery and Lessons Learned**

Post-incident activities:
1. Restore systems from clean backups
2. Verify integrity before reconnection
3. Document timeline and actions
4. Conduct post-incident review
5. Update controls and procedures

**Validation:** Post-incident report completed within 5 business days.

---

## Reference Guides

### When to Use Each Reference

**references/iso27001-controls.md**
- Control selection for SoA
- Implementation guidance
- Evidence requirements
- Audit preparation

**references/risk-assessment-guide.md**
- Risk methodology selection
- Asset classification criteria
- Threat modeling approaches
- Risk calculation methods

**references/incident-response.md**
- Response procedures
- Escalation matrices
- Communication templates
- Recovery checklists

---

## Validation Checkpoints

### ISMS Implementation Validation

| Phase | Checkpoint | Evidence Required |
|-------|------------|-------------------|
| Scope | Scope approved | Signed scope document |
| Risk | Register complete | Risk register with owners |
| Controls | SoA approved | Statement of Applicability |
| Operation | Metrics active | Dashboard screenshots |
| Audit | Internal audit done | Audit report |

### Certification Readiness

Before Stage 1 audit:
- [ ] ISMS scope documented and approved
- [ ] Information security policy published
- [ ] Risk assessment completed
- [ ] Statement of Applicability finalized
- [ ] Internal audit conducted
- [ ] Management review completed
- [ ] Nonconformities addressed

Before Stage 2 audit:
- [ ] Controls implemented and operational
- [ ] Evidence of effectiveness available
- [ ] Staff trained and aware
- [ ] Incidents logged and managed
- [ ] Metrics collected for 3+ months

### Compliance Verification

Run periodic checks:

```bash
# Monthly compliance check
python scripts/compliance_checker.py --standard iso27001 --controls-file controls.csv --output monthly_$(date +%Y%m).md

# Quarterly gap analysis
python scripts/compliance_checker.py --standard iso27001 --controls-file controls.csv --gap-analysis --output quarterly_gaps.md
```

---

## Worked Example: Healthcare Risk Assessment

**Scenario:** Synthetic healthcare workshop, not a site assessment. Tables below are manually authored illustrative scenarios and treatment ideas, not exact CLI output or verified findings. Run with `--demo` to inspect the bundled catalog; use `--assets` for your supplied inventory.

### Step 1: Define Assets

```bash
python scripts/risk_assessment.py --scope "example-patient-data-system" --demo --template healthcare
```

**Illustrative synthetic inventory:**

| Asset ID | Asset | Type | Owner | Classification |
|----------|-------|------|-------|----------------|
| A001 | Patient database | Information | DBA Team | Critical |
| A002 | EHR application | Software | App Team | Critical |
| A003 | Database server | Hardware | Infra Team | High |
| A004 | Admin credentials | Access | Security | Critical |

### Step 2: Identify Risks

**Illustrative scenario register (unverified assumptions):**

| Risk ID | Asset | Threat | Vulnerability | L | I | Score |
|---------|-------|--------|---------------|---|---|-------|
| R001 | A001 | Data breach | Weak encryption | 3 | 5 | 15 |
| R002 | A002 | SQL injection | Input validation | 4 | 4 | 16 |
| R003 | A004 | Credential theft | No MFA | 4 | 5 | 20 |

### Step 3: Determine Treatment

| Risk | Treatment | Control | Timeline |
|------|-----------|---------|----------|
| R001 | Mitigate | Implement AES-256 encryption | 30 days |
| R002 | Mitigate | Add input validation, WAF | 14 days |
| R003 | Mitigate | Enforce MFA for all admins | 7 days |

### Step 4: Report Assessed Controls

If the control owners' records support these three statuses, save them as `implemented_controls.csv`.

```csv
control_id,status
A.8.24,implemented
A.8.5,implemented
A.8.26,partial
```

```bash
python scripts/compliance_checker.py --standard iso27001 --domains technological --controls-file implemented_controls.csv
```

With the bundled technological catalog, this example reports 2 implemented, 1 partial and 25 unknown. Assessment coverage is 3/28 (10.7%) and the catalog score is 2.5/28 (8.9%).
