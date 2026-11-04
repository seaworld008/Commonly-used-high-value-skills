# 安全治理与稳定性 / Security and Reliability

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

覆盖 Sentry、安全最佳实践、威胁建模与安全所有权分析的技能集合。

当前分类共 **23** 个技能。

## 推荐先看

- [information-security-manager-iso27001](./information-security-manager-iso27001/) - 建立和审计 ISO 27001 信息安全管理体系及风险控制。
- [security-model](./security-model/) - 维护供安全审查工具读取的安全模型，核验信任边界、继承、可信版本和抑制规则。
- [security-ownership-map](./security-ownership-map/) - 用于基于 Git 历史分析安全所有权、敏感代码归属、bus factor、CODEOWNERS 现实差距和风险热点。
- [security-pen-testing](./security-pen-testing/) - 在授权范围内执行漏洞扫描、渗透测试和修复验证。

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `breach` | 开展授权红队演练或威胁建模时使用：攻击场景、AI 红队测试、紫队演练和防护验证。 | [目录](./breach/) | [SKILL.md](./breach/SKILL.md) |
| `cloak` | 系统涉及个人数据时使用：敏感信息识别、数据流梳理、同意管理、GDPR/CCPA 合规和隐私影响评估。 | [目录](./cloak/) | [SKILL.md](./cloak/SKILL.md) |
| `codeql-security-scanner` | 用于通过 CodeQL 执行语义代码扫描、安全查询和自定义规则，并输出 SARIF 接入 GitHub Code Scanning。 | [目录](./codeql-security-scanner/) | [SKILL.md](./codeql-security-scanner/SKILL.md) |
| `comply` | 核对法规与合规框架要求，整理控制证据和整改计划。 | [目录](./comply/) | [SKILL.md](./comply/SKILL.md) |
| `firebase-security-rules-auditor` | 审计 Firestore 与 Cloud Storage 安全规则，检查授权、字段校验、权限提升、资源滥用和模拟器测试覆盖。 | [目录](./firebase-security-rules-auditor/) | [SKILL.md](./firebase-security-rules-auditor/SKILL.md) |
| `gha-security-review` | 审查 GitHub Actions 触发器、注入、凭据和供应链风险。 | [目录](./gha-security-review/) | [SKILL.md](./gha-security-review/SKILL.md) |
| `grype-syft-sbom-scanner` | 用于通过 Syft 生成 SBOM，并用 Grype 扫描容器镜像、文件系统、软件包、归档和 SBOM 漏洞。 | [目录](./grype-syft-sbom-scanner/) | [SKILL.md](./grype-syft-sbom-scanner/SKILL.md) |
| `information-security-manager-iso27001` | 建立和审计 ISO 27001 信息安全管理体系及风险控制。 | [目录](./information-security-manager-iso27001/) | [SKILL.md](./information-security-manager-iso27001/SKILL.md) |
| `link-checker` | 检测 URL 可达性、失效链接、跳转链路、可疑域名和文档链接健康度。 | [目录](./link-checker/) | [SKILL.md](./link-checker/SKILL.md) |
| `osv-scanner` | 用于通过 OSV-Scanner 检查锁文件、清单、SBOM、Git 历史和源码树中的开源依赖漏洞。 | [目录](./osv-scanner/) | [SKILL.md](./osv-scanner/SKILL.md) |
| `security-audit` | 对代码库进行安全审计，聚焦可利用且有真实影响的漏洞，并生成可验证的发现、报告和结构化输出。 | [目录](./security-audit/) | [SKILL.md](./security-audit/SKILL.md) |
| `security-auditor` | 审查应用、接口、基础设施和依赖中的实际安全风险。 | [目录](./security-auditor/) | [SKILL.md](./security-auditor/SKILL.md) |
| `security-best-practices` | 用于按语言或框架检查安全最佳实践，生成安全审查报告和 secure-by-default 建议。 | [目录](./security-best-practices/) | [SKILL.md](./security-best-practices/SKILL.md) |
| `security-model` | 维护供安全审查工具读取的安全模型，核验信任边界、继承、可信版本和抑制规则。 | [目录](./security-model/) | [SKILL.md](./security-model/SKILL.md) |
| `security-ownership-map` | 用于基于 Git 历史分析安全所有权、敏感代码归属、bus factor、CODEOWNERS 现实差距和风险热点。 | [目录](./security-ownership-map/) | [SKILL.md](./security-ownership-map/SKILL.md) |
| `security-pen-testing` | 在授权范围内执行漏洞扫描、渗透测试和修复验证。 | [目录](./security-pen-testing/) | [SKILL.md](./security-pen-testing/SKILL.md) |
| `security-review` | 依据代码证据审查注入、认证、授权和加密漏洞。 | [目录](./security-review/) | [SKILL.md](./security-review/SKILL.md) |
| `security-threat-model` | 用于基于代码库或架构梳理资产、信任边界、攻击者能力、滥用路径和缓解措施。 | [目录](./security-threat-model/) | [SKILL.md](./security-threat-model/SKILL.md) |
| `semgrep-appsec-scanner` | 用于通过 Semgrep 执行应用安全 SAST、源码扫描、自定义规则、密钥流程和供应链依赖分析。 | [目录](./semgrep-appsec-scanner/) | [SKILL.md](./semgrep-appsec-scanner/SKILL.md) |
| `sentry` | 用于只读查询 Sentry issues、events 和服务健康数据，汇总线上错误并辅助生产问题排查。 | [目录](./sentry/) | [SKILL.md](./sentry/SKILL.md) |
| `skill-security-auditor` | 安装或更新外部技能前，静态扫描并人工审查指令、脚本、权限、依赖、来源和外传风险。 | [目录](./skill-security-auditor/) | [SKILL.md](./skill-security-auditor/SKILL.md) |
| `trivy-vulnerability-scanner` | 用于通过 Trivy 扫描仓库、镜像、文件系统、SBOM、Kubernetes 和 IaC 中的漏洞、错误配置、密钥与许可证问题。 | [目录](./trivy-vulnerability-scanner/) | [SKILL.md](./trivy-vulnerability-scanner/SKILL.md) |
| `vuls-linux-cve-scanner` | 用于通过 Vuls 对 Linux、FreeBSD、容器、WordPress、依赖库和网络设备执行无代理 CVE 扫描。 | [目录](./vuls-linux-cve-scanner/) | [SKILL.md](./vuls-linux-cve-scanner/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
