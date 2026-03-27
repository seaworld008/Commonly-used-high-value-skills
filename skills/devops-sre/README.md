# DevOps / SRE

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

面向发布、CI/CD、可观测性、故障响应和环境治理的技能集合。

当前分类共 **10** 个技能。

## 推荐先看

- [incident-commander](./incident-commander/) - Author: Claude Skills Team Version: 1.0.0 Last Updated: February 2026.
- [observability-designer](./observability-designer/) - Description: Design comprehensive observability strategies for production systems including SLI/SLO frameworks, alerting optimization, and dashboard generation.
- [cloudflare-troubleshooting](./cloudflare-troubleshooting/) - Investigate and resolve Cloudflare configuration issues using API-driven evidence gathering. Use when troubleshooting ERR_TOO_MANY_REDIRECTS, SSL errors, DNS issues, or any Cloudflare-related problems. Focus on systematic investigation using Cloudflare API to examine actual configuration rather than making assumptions.
- [release-manager](./release-manager/) - The Release Manager skill provides comprehensive tools and knowledge for managing software releases end-to-end. From parsing conventional commits to generating changelogs, determining version bumps, and orchestrating release processes, this skill ensures reliable, predictable, and well-documented software releases.

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `changelog-generator` | Parse conventional commits, determine semantic version bumps, and generate structured changelogs in Keep a Changelog format. Supports monorepo changelogs, GitHub Releases integration, and separates user-facing from developer changelogs. | [目录](./changelog-generator/) | [SKILL.md](./changelog-generator/SKILL.md) |
| `ci-cd-pipeline-builder` | Analyzes your project stack and generates production-ready CI/CD pipeline configurations for GitHub Actions, GitLab CI, and Bitbucket Pipelines. Handles matrix testing, caching strategies, deployment stages, environment promotion, and secret management — tailored to your actual tech stack. | [目录](./ci-cd-pipeline-builder/) | [SKILL.md](./ci-cd-pipeline-builder/SKILL.md) |
| `cloudflare-troubleshooting` | Investigate and resolve Cloudflare configuration issues using API-driven evidence gathering. Use when troubleshooting ERR_TOO_MANY_REDIRECTS, SSL errors, DNS issues, or any Cloudflare-related problems. Focus on systematic investigation using Cloudflare API to examine actual configuration rather than making assumptions. | [目录](./cloudflare-troubleshooting/) | [SKILL.md](./cloudflare-troubleshooting/SKILL.md) |
| `env-secrets-manager` | Complete environment and secrets management workflow: .env file lifecycle across dev/staging/prod, .env.example auto-generation, required-var validation, secret leak detection in git history, and credential rotation playbook. Integrates with HashiCorp Vault, AWS SSM, 1Password CLI, and Doppler. | [目录](./env-secrets-manager/) | [SKILL.md](./env-secrets-manager/SKILL.md) |
| `github-ops` | Provides comprehensive GitHub operations using gh CLI and GitHub API. Activates when working with pull requests, issues, repositories, workflows, or GitHub API operations including creating/viewing/merging PRs, managing issues, querying API endpoints, and handling GitHub workflows in enterprise or public GitHub environments. | [目录](./github-ops/) | [SKILL.md](./github-ops/SKILL.md) |
| `incident-commander` | Author: Claude Skills Team Version: 1.0.0 Last Updated: February 2026. | [目录](./incident-commander/) | [SKILL.md](./incident-commander/SKILL.md) |
| `observability-designer` | Description: Design comprehensive observability strategies for production systems including SLI/SLO frameworks, alerting optimization, and dashboard generation. | [目录](./observability-designer/) | [SKILL.md](./observability-designer/SKILL.md) |
| `release-manager` | The Release Manager skill provides comprehensive tools and knowledge for managing software releases end-to-end. From parsing conventional commits to generating changelogs, determining version bumps, and orchestrating release processes, this skill ensures reliable, predictable, and well-documented software releases. | [目录](./release-manager/) | [SKILL.md](./release-manager/SKILL.md) |
| `senior-architect` | 用于软件架构评审、技术选型决策和系统可扩展性分析。来源：alirezarezvani/claude-skills。 | [目录](./senior-architect/) | [SKILL.md](./senior-architect/SKILL.md) |
| `senior-devops` | Comprehensive DevOps skill for CI/CD, infrastructure automation, containerization, and cloud platforms (AWS, GCP, Azure). Includes pipeline setup, infrastructure as code, deployment automation, and monitoring. Use when setting up pipelines, deploying applications, managing infrastructure, implementing monitoring, or optimizing deployment processes. | [目录](./senior-devops/) | [SKILL.md](./senior-devops/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
