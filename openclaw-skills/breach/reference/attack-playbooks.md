# Attack Playbooks

**Purpose:** Structured attack playbooks for application, infrastructure, and supply chain domains.
**Read when:** Designing attack scenarios for non-AI systems.
**Scope:** Generic OWASP Top 10 (web/API/infrastructure). For AI/LLM attack frameworks (OWASP LLM Top 10, OWASP Agentic Top 10, MITRE ATLAS, NIST AI 100-2), see `ai-red-teaming.md`.

---

## OWASP Top 10 (2025) Attack Playbook

Use the [official 2025 categories](https://top10.owasp.org/2025/) rather than
mixing the 2021 IDs with 2025 names. Map findings by their demonstrated cause and
impact; a category label does not establish exploitability or authorize testing.

| Category | Focused assessment |
|---|---|
| A01 Broken Access Control | IDOR, forced browsing, horizontal/vertical privilege tests; authorized SSRF tests for internal services, metadata endpoints and URL reachability |
| A02 Security Misconfiguration | Default credentials, verbose errors, unnecessary services and effective configuration; compare applicable CIS guidance |
| A03 Software Supply Chain Failures | Known dependency CVEs, version/exposure verification, build provenance, CI permissions, artifact integrity and update paths |
| A04 Cryptographic Failures | TLS configuration, storage encryption, weak algorithms, key handling and secrets exposure |
| A05 Injection | Parameterized SQL/NoSQL, command and LDAP injection tests; trace controlled input to interpreters and templates |
| A06 Insecure Design | Business-logic abuse, missing rate limits and security properties not fixed by input validation alone |
| A07 Authentication Failures | Authorized credential/brute-force resistance tests, session lifecycle, account recovery, JWT boundaries and bypass paths |
| A08 Software or Data Integrity Failures | Unsafe deserialization, unsigned updates and CI/data-integrity assumptions |
| A09 Security Logging and Alerting Failures | Missing critical logs, log injection/tampering, monitoring coverage and actionable alert delivery |
| A10 Mishandling of Exceptional Conditions | Fail-open error paths, exceptional inputs and resource-exhaustion behavior |

## OWASP API Security Top 10 Attack Playbook

| # | Risk | Attack Technique |
|---|------|------------------|
| API1 | Broken Object Level Authorization | Manipulate object IDs to access other users' data |
| API2 | Broken Authentication | Token manipulation, credential stuffing, session abuse |
| API3 | Broken Object Property Level Authorization | Mass assignment, excessive data exposure |
| API4 | Unrestricted Resource Consumption | Rate limit bypass, resource exhaustion |
| API5 | Broken Function Level Authorization | Access admin endpoints as regular user |
| API6 | Unrestricted Access to Sensitive Business Flows | Automate business-critical operations (purchase, booking) |
| API7 | Server Side Request Forgery | Force API to make requests to internal resources |
| API8 | Security Misconfiguration | CORS misconfiguration, verbose errors, debug endpoints |
| API9 | Improper Inventory Management | Access undocumented/shadow APIs |
| API10 | Unsafe Consumption of APIs | Exploit trust in third-party API responses |

---

## Infrastructure Attack Patterns

### MITRE ATT&CK — Key Techniques by Tactic

| Tactic | Priority Techniques | Test Focus |
|--------|-------------------|------------|
| Initial Access | T1190 Exploit Public-Facing App, T1133 External Remote Services | Exposed services, VPN, admin panels |
| Execution | T1059 Command/Script Interpreter, T1203 Exploitation for Client Execution | Shell access, script injection |
| Persistence | T1078 Valid Accounts, T1053 Scheduled Tasks | Credential reuse, backdoor placement |
| Privilege Escalation | T1068 Exploitation, T1548 Abuse Elevation Control | Kernel exploits, sudo misconfig |
| Defense Evasion | T1070 Indicator Removal, T1027 Obfuscation | Log tampering, encoded payloads |
| Credential Access | T1110 Brute Force, T1003 OS Credential Dumping | Password spraying, hash extraction |
| Lateral Movement | T1021 Remote Services, T1080 Taint Shared Content | SSH pivoting, shared drive abuse |
| Exfiltration | T1041 Over C2 Channel, T1048 Over Alternative Protocol | DNS tunneling, steganography |

### Cloud-Specific Attack Patterns

| Target | Attack | Test |
|--------|--------|------|
| IAM | Over-permissioned roles, role chaining | Enumerate permissions, test escalation paths |
| Storage | Public buckets, misconfigured ACLs | Access testing without credentials |
| Metadata | IMDS exploitation (169.254.169.254) | SSRF to metadata service |
| Serverless | Function injection, event poisoning | Test event source manipulation |
| Containers | Container escape, image tampering | Privileged container testing, registry security |

---

## Supply Chain Attack Patterns

| Vector | Attack | Test Approach |
|--------|--------|---------------|
| Dependencies | Typosquatting, dependency confusion, malicious packages | Verify package sources, test private registry isolation |
| Build Pipeline | CI/CD injection, secret leakage, unsigned artifacts | Audit pipeline config, test secret exposure |
| Source Code | Commit signing bypass, branch protection circumvention | Test branch protection rules, verify signing |
| Distribution | Compromised update channels, unsigned releases | Verify update integrity, test rollback |

---

## Purple Team Exercise Template

```markdown
## Purple Team Exercise: [Exercise Name]

### Objective
[What security control or detection capability is being validated]

### Scenario
- **Threat Actor Profile:** [Nation-state / Criminal / Insider / Opportunistic]
- **ATT&CK Techniques:** [T-IDs]
- **Target:** [System/component]

### Red Team Actions
| Step | Action | ATT&CK ID | Expected Blue Detection |
|------|--------|-----------|------------------------|
| 1 | [Red action] | [T-ID] | [What blue should see] |
| 2 | [Red action] | [T-ID] | [What blue should see] |

### Blue Team Validation
| Detection Rule | Triggered? | Time to Detect | SIEM Query |
|---------------|-----------|----------------|------------|
| [Rule name] | Yes/No | [Duration] | [Query] |

### Results
- Detection rate: [X/Y actions detected]
- Mean time to detect: [Duration]
- Gaps identified: [List]

### Improvements
- [New detection rules to add]
- [SIEM queries to tune]
- [Playbook updates needed]
```
