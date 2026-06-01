# 安全治理与稳定性 / Security and Reliability

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

覆盖 Sentry、安全最佳实践、威胁建模与安全所有权分析的技能集合。

当前分类共 **18** 个技能。

## 推荐先看

- [security-ownership-map](./security-ownership-map/) - 用于基于 Git 历史分析安全所有权、敏感代码归属、bus factor、CODEOWNERS 现实差距和风险热点。
- [sentry](./sentry/) - 用于只读查询 Sentry issues、events 和服务健康数据，汇总线上错误并辅助生产问题排查。
- [breach](./breach/) - Red team engineering agent. Designs attack scenarios, builds threat models, applies MITRE ATT&CK/OWASP frameworks, runs Purple Team exercises, and performs AI/LLM red teaming. Use when adversarial security validation is needed.
- [cloak](./cloak/) - Privacy engineering and data governance agent. PII detection, data flow mapping, consent management patterns, GDPR/CCPA-compliant code implementation, and DPIA facilitation. Use when privacy-by-design implementation is needed.

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `breach` | Red team engineering agent. Designs attack scenarios, builds threat models, applies MITRE ATT&CK/OWASP frameworks, runs Purple Team exercises, and performs AI/LLM red teaming. Use when adversarial security validation is needed. | [目录](./breach/) | [SKILL.md](./breach/SKILL.md) |
| `cloak` | Privacy engineering and data governance agent. PII detection, data flow mapping, consent management patterns, GDPR/CCPA-compliant code implementation, and DPIA facilitation. Use when privacy-by-design implementation is needed. | [目录](./cloak/) | [SKILL.md](./cloak/SKILL.md) |
| `codeql-security-scanner` | 用于通过 CodeQL 执行语义代码扫描、安全查询、自定义规则、SARIF 报告和 GitHub Code Scanning 集成。 | [目录](./codeql-security-scanner/) | [SKILL.md](./codeql-security-scanner/SKILL.md) |
| `comply` | Regulatory compliance and audit agent. Maps business regulatory requirements (SOC2/PCI-DSS/HIPAA/ISO 27001), checks control implementations, designs audit trails, and implements Policy as Code. Use when compliance auditing is needed. | [目录](./comply/) | [SKILL.md](./comply/SKILL.md) |
| `grype-syft-sbom-scanner` | 用于通过 Syft 生成 SBOM，并用 Grype 扫描容器镜像、文件系统、软件包、归档和 SBOM 漏洞。 | [目录](./grype-syft-sbom-scanner/) | [SKILL.md](./grype-syft-sbom-scanner/SKILL.md) |
| `information-security-manager-iso27001` | ISO 27001 ISMS implementation and cybersecurity governance for HealthTech and MedTech companies. Use for ISMS design, security risk assessment, control implementation, ISO 27001 certification, security audits, incident response, and compliance verification. Covers ISO 27001, ISO 27002, healthcare security, and medical device cybersecurity. | [目录](./information-security-manager-iso27001/) | [SKILL.md](./information-security-manager-iso27001/SKILL.md) |
| `link-checker` | 检测 URL 可达性与潜在风险，识别失效链接、跳转链路和可疑域名。 | [目录](./link-checker/) | [SKILL.md](./link-checker/SKILL.md) |
| `osv-scanner` | 用于通过 OSV-Scanner 检查锁文件、清单、SBOM、Git 历史和源码树中的开源依赖漏洞。 | [目录](./osv-scanner/) | [SKILL.md](./osv-scanner/SKILL.md) |
| `security-best-practices` | 用于按语言和框架执行安全最佳实践检查，生成安全审查报告并提出 secure-by-default 改进建议。 | [目录](./security-best-practices/) | [SKILL.md](./security-best-practices/SKILL.md) |
| `security-ownership-map` | 用于基于 Git 历史分析安全所有权、敏感代码归属、bus factor、CODEOWNERS 现实差距和风险热点。 | [目录](./security-ownership-map/) | [SKILL.md](./security-ownership-map/SKILL.md) |
| `security-pen-testing` | Use when the user asks to perform security audits, penetration testing, vulnerability scanning, OWASP Top 10 checks, or offensive security assessments. Covers static analysis, dependency scanning, secret detection, API security testing, and pen test report generation. | [目录](./security-pen-testing/) | [SKILL.md](./security-pen-testing/SKILL.md) |
| `security-threat-model` | 用于基于代码库枚举信任边界、资产、攻击者能力、滥用路径和缓解措施，并生成威胁模型。 | [目录](./security-threat-model/) | [SKILL.md](./security-threat-model/SKILL.md) |
| `semgrep-appsec-scanner` | 用于通过 Semgrep 执行应用安全 SAST、源码扫描、自定义规则、密钥流程和供应链依赖分析。 | [目录](./semgrep-appsec-scanner/) | [SKILL.md](./semgrep-appsec-scanner/SKILL.md) |
| `sentry` | 用于只读查询 Sentry issues、events 和服务健康数据，汇总线上错误并辅助生产问题排查。 | [目录](./sentry/) | [SKILL.md](./sentry/SKILL.md) |
| `skill-security-auditor` | Security audit and vulnerability scanner for AI agent skills before installation. Use when: (1) evaluating a skill from an untrusted source, (2) auditing a skill directory or git repo URL for malicious code, (3) pre-install security gate for Claude Code plugins, OpenClaw skills, or Codex skills, (4) scanning Python scripts for dangerous patterns like os.system, eval, subprocess, network exfiltration, (5) detecting prompt injection in SKILL.md files, (6) checking dependency supply chain risks, (7) verifying file system access stays within skill boundaries. Triggers: \"audit this skill\", \"is this skill safe\", \"scan skill for security\", \"check skill before install\", \"skill security check\", \"skill vulnerability scan\". | [目录](./skill-security-auditor/) | [SKILL.md](./skill-security-auditor/SKILL.md) |
| `skill-vetter` | 在安装前审计技能安全性，识别恶意指令、越权行为与高风险配置。 | [目录](./skill-vetter/) | [SKILL.md](./skill-vetter/SKILL.md) |
| `trivy-vulnerability-scanner` | 用于通过 Trivy 扫描仓库、容器镜像、文件系统、rootfs、SBOM、Kubernetes、IaC、密钥、许可证和系统 CVE。 | [目录](./trivy-vulnerability-scanner/) | [SKILL.md](./trivy-vulnerability-scanner/SKILL.md) |
| `vuls-linux-cve-scanner` | 用于通过 Vuls 对 Linux、FreeBSD、容器、WordPress、库和网络设备执行 Agentless CVE 扫描。 | [目录](./vuls-linux-cve-scanner/) | [SKILL.md](./vuls-linux-cve-scanner/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
