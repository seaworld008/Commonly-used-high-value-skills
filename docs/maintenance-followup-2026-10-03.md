# 2026-10-03 发布前补充审阅

接续 [9 月 30 日全仓审计](maintenance-audit-2026-09-30.md)，不改写其历史统计和当时哈希。本报告和 JSON 中的哈希对应本轮修改后的文件。

实时观测时间：`2026-10-03T19:20:12Z`。153 个跟踪条目：85 个没有新变更，43 个需要策展，0 个不可用，25 个按原政策冻结。对 43 个候选比较固定旧/新提交的完整声明文件及新增普通资源，再逐项决定；不把本地差异全部覆盖为上游正文。

本轮处理统计：`{"updated": 8, "unchanged_artifacts": 31, "retained_after_review": 4}`；另修复飞书图表检查的两个 PR 反馈。新增性能优化模式参考保留许可证，修复同目录链接；公共入口仍为 287 个。

| 技能 | 决策 | 依据与处理 |
|---|---|---|
| `api-and-interface-design` | updated | Adopt the executable catch/rethrow fix (throw e), preserving the idempotency design. |
| `browser-testing-with-devtools` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `ci-cd-and-automation` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `code-review-and-quality` | updated | Adopt a bounded mutation-test experiment only in an authorized isolated copy; omit the unbundled constraint-driven-development dependency. |
| `code-simplification` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `context-engineering` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `debugging-and-error-recovery` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `deprecation-and-migration` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `documentation-and-adrs` | updated | Add Proposed to the ADR status lifecycle; preserve local templates. |
| `doubt-driven-development` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `frontend-ui-engineering` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `git-workflow-and-versioning` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `idea-refine` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `incremental-implementation` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `interview-me` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `observability-and-instrumentation` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `performance-optimization` | updated | Move worked examples into the new bundled optimization-patterns reference; repair relative checklist links and preserve local guidance. |
| `planning-and-task-breakdown` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `security-and-hardening` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `shipping-and-launch` | updated | Remove nonexistent Prisma rollback command; require a project-verified command or runbook. |
| `source-driven-development` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `spec-driven-development` | retained_after_review | Retain the local authorization-aware flow; reject a new forced turn/approval gate that conflicts with repository and current-user authorization. |
| `test-driven-development` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `using-agent-skills` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `firebase-security-rules-auditor` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `graphify` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `prisma-client-api` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `prisma-upgrade-v7` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `llm-wiki` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `honcho` | updated | Document the Honcho plugin-catalog installation route only for an explicitly requested installation and supported local CLI; loading the skill never installs it. |
| `codebase-inspection` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `arxiv` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `obsidian` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `mcporter` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `azure-kubernetes` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `kubernetes-specialist` | retained_after_review | Retain functional guidance and local attribution; upstream changes only add company advertising metadata and footer. |
| `neon-postgres` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `neon-postgres-egress-optimizer` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `supabase` | updated | Adopt the upstream changelog entry for scoped PAT guidance; retain local restricted auth and execution policy. |
| `supabase-postgres-best-practices` | unchanged_artifacts | Declared artifact bytes and modes are unchanged between the pinned commits; retain local overlay and advance the reviewed checkpoint only. |
| `terraform-engineer` | retained_after_review | Retain functional guidance and local attribution; upstream changes only add company advertising metadata and footer. |
| `x-twitter-scraper` | updated | Adopt no credentialed redirects, 2xx-only success, no secrets in process arguments and untrusted error isolation; retain local REST execution/MCP planning-only restrictions. |
| `nlpm-audit` | retained_after_review | Retain the portable local audit rather than replacing it with a product README: manifest verification, client-specific evaluation and advisory scoring already have explicit local boundaries. |

## PR #129 回归

图表检查默认只读取明确可见网格表，支持旧响应中带完整网格维度的表；显式指定非网格表会明确拒绝，显式隐藏网格仍可读取。共享图表读取路径对超时、无效 JSON 最多重试一次，不重试权限失败、缺少 CLI 或写命令。回归通过 mock/离线执行验证，没有读取真实飞书账户。

上游证据采集运行：`37147614811`；完整逐项提交、Git blob 和修改前后 SHA-256 见 [JSON](maintenance-followup-2026-10-03.json)。原审计是历史记录，不把最新检查点推进称为逐字镜像；冻结的 25 项不声称最新。测试命令和最终提交的通过情况以 PR / 精确合并 SHA 的 CI 为准；没有真实模型、live SaaS 或生产验收。
