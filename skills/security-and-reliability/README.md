# 安全治理与稳定性 / Security and Reliability

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

覆盖 Sentry、安全最佳实践、威胁建模与安全所有权分析的技能集合。

当前分类共 **16** 个技能。

## 推荐先看

- [security-ownership-map](./security-ownership-map/) - Analyze git repositories to build a security ownership topology (people-to-file), compute bus factor and sensitive-code ownership, and export CSV/JSON for graph databases and visualization. Trigger only when the user explicitly wants a security-oriented ownership or bus-factor analysis grounded in git history (for example: orphaned sensitive code, security maintainers, CODEOWNERS reality checks for risk, sensitive hotspots, or ownership clusters). Do not trigger for general maintainer lists or non-security ownership questions.
- [sentry](./sentry/) - Use when the user asks to inspect Sentry issues or events, summarize recent production errors, or pull basic Sentry health data via the Sentry API; perform read-only queries with the bundled script and require `SENTRY_AUTH_TOKEN`.
- [breach](./breach/) - Red team engineering agent. Designs attack scenarios, builds threat models, applies MITRE ATT&CK/OWASP frameworks, runs Purple Team exercises, and performs AI/LLM red teaming. Use when adversarial security validation is needed.
- [cloak](./cloak/) - Privacy engineering and data governance agent. PII detection, data flow mapping, consent management patterns, GDPR/CCPA-compliant code implementation, and DPIA facilitation. Use when privacy-by-design implementation is needed.

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `breach` | Red team engineering agent. Designs attack scenarios, builds threat models, applies MITRE ATT&CK/OWASP frameworks, runs Purple Team exercises, and performs AI/LLM red teaming. Use when adversarial security validation is needed. | [目录](./breach/) | [SKILL.md](./breach/SKILL.md) |
| `cloak` | Privacy engineering and data governance agent. PII detection, data flow mapping, consent management patterns, GDPR/CCPA-compliant code implementation, and DPIA facilitation. Use when privacy-by-design implementation is needed. | [目录](./cloak/) | [SKILL.md](./cloak/SKILL.md) |
| `codeql-security-scanner` | Use CodeQL to run deep semantic code scanning, security query suites, custom queries, SARIF reporting, and GitHub code scanning integration. | [目录](./codeql-security-scanner/) | [SKILL.md](./codeql-security-scanner/SKILL.md) |
| `comply` | Regulatory compliance and audit agent. Maps business regulatory requirements (SOC2/PCI-DSS/HIPAA/ISO 27001), checks control implementations, designs audit trails, and implements Policy as Code. Use when compliance auditing is needed. | [目录](./comply/) | [SKILL.md](./comply/SKILL.md) |
| `grype-syft-sbom-scanner` | Use Syft to generate SBOMs and Grype to scan container images, filesystems, packages, archives, and SBOMs for vulnerabilities. | [目录](./grype-syft-sbom-scanner/) | [SKILL.md](./grype-syft-sbom-scanner/SKILL.md) |
| `link-checker` | 检测 URL 可达性与潜在风险，识别失效链接、跳转链路和可疑域名。 | [目录](./link-checker/) | [SKILL.md](./link-checker/SKILL.md) |
| `osv-scanner` | Use OSV-Scanner to detect known vulnerabilities in open-source dependencies from lockfiles, manifests, SBOMs, git history, and source trees. | [目录](./osv-scanner/) | [SKILL.md](./osv-scanner/SKILL.md) |
| `security-best-practices` | Perform language and framework specific security best-practice reviews and suggest improvements. Trigger only when the user explicitly requests security best practices guidance, a security review/report, or secure-by-default coding help. Trigger only for supported languages (python, javascript/typescript, go). Do not trigger for general code review, debugging, or non-security tasks. | [目录](./security-best-practices/) | [SKILL.md](./security-best-practices/SKILL.md) |
| `security-ownership-map` | Analyze git repositories to build a security ownership topology (people-to-file), compute bus factor and sensitive-code ownership, and export CSV/JSON for graph databases and visualization. Trigger only when the user explicitly wants a security-oriented ownership or bus-factor analysis grounded in git history (for example: orphaned sensitive code, security maintainers, CODEOWNERS reality checks for risk, sensitive hotspots, or ownership clusters). Do not trigger for general maintainer lists or non-security ownership questions. | [目录](./security-ownership-map/) | [SKILL.md](./security-ownership-map/SKILL.md) |
| `security-threat-model` | Repository-grounded threat modeling that enumerates trust boundaries, assets, attacker capabilities, abuse paths, and mitigations, and writes a concise Markdown threat model. Trigger only when the user explicitly asks to threat model a codebase or path, enumerate threats/abuse paths, or perform AppSec threat modeling. Do not trigger for general architecture summaries, code review, or non-security design work. | [目录](./security-threat-model/) | [SKILL.md](./security-threat-model/SKILL.md) |
| `semgrep-appsec-scanner` | Use Semgrep for application security scanning across source code, custom rules, secrets workflows, and Semgrep Supply Chain dependency analysis. | [目录](./semgrep-appsec-scanner/) | [SKILL.md](./semgrep-appsec-scanner/SKILL.md) |
| `sentry` | Use when the user asks to inspect Sentry issues or events, summarize recent production errors, or pull basic Sentry health data via the Sentry API; perform read-only queries with the bundled script and require `SENTRY_AUTH_TOKEN`. | [目录](./sentry/) | [SKILL.md](./sentry/SKILL.md) |
| `skill-security-auditor` | Audit AI agent skills for security risks before installation, with PASS/WARN/FAIL findings and remediation guidance. | [目录](./skill-security-auditor/) | [SKILL.md](./skill-security-auditor/SKILL.md) |
| `skill-vetter` | 在安装前审计技能安全性，识别恶意指令、越权行为与高风险配置。 | [目录](./skill-vetter/) | [SKILL.md](./skill-vetter/SKILL.md) |
| `trivy-vulnerability-scanner` | Use Trivy to scan repositories, container images, filesystems, root filesystems, SBOMs, Kubernetes resources, IaC, secrets, licenses, and OS package CVEs. | [目录](./trivy-vulnerability-scanner/) | [SKILL.md](./trivy-vulnerability-scanner/SKILL.md) |
| `vuls-linux-cve-scanner` | Use Vuls for agentless Linux, FreeBSD, container, WordPress, library, and network-device CVE scanning with NVD, OVAL, vendor advisory, and changelog sources. | [目录](./vuls-linux-cve-scanner/) | [SKILL.md](./vuls-linux-cve-scanner/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
