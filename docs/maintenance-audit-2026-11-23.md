# 2026-11-23 全量技能维护与组合演进报告

本次维护从 `origin/main`（`a7c12c2f`）在独立演进分支 `codex/portfolio-evolution-20261123` 上完成全仓巡检、浏览器基础能力升级、重叠技能合并与退役、质量与触发描述精细化优化，以及 5 项高价值技能的策展入库，最终规范技能规模由 `294` 演进为 `295` 项（16 个分类；92 项自研 `in-house`，203 项含外部 provenance v2 追踪条目的生态/本地覆写技能；其中活跃已验证外源追踪条目 201 项）。

## 组合优化与精简

- **合并与退役 4 项重叠技能**（均已登记至 [组合策略](sources/portfolio-policy.json) 永久退役清单及 [组合决策台账](sources/portfolio-decisions-2026-08.json) 19 条决策，并把独有高价值域知识迁入保留主技能）：
  - `database-schema-designer` → 并入 `database-designer`（保留 Drizzle/Prisma 选型对比、Alembic 零停机迁移模式与 PostgreSQL RLS 策略片段至 `references/orm-and-rls-patterns.md`）。
  - `security-auditor` → 并入 `security-review`（迁入 AI 生成代码专项高风险模式核查表至 `references/ai-generated-code-checks.md`）。
  - `git-worktree-manager` → 并入 `using-git-worktrees`（迁入并行 Agent 工作区依赖与环境变量隔离规范至 `references/parallel-env-isolation.md`）。
  - `competitive-teardown` → 并入 `compete`（迁入公开定价页/评价站/招聘信号取证矩阵至 `reference/public-evidence-collection.md`）。
- **清理通用模板并补强领域内容**：
  - 从 23 个达标技能中移除冗余 `<!-- LOCAL-QUALITY-SUPPLEMENT:START -->` 模板，同时保留 9 个依赖该块维持分档行高或回归契约的技能；同步更新 `tests/test_weekly_curation_guardrails.py` 中对 `obsidian` 不再包含通用补充块的约束。
  - 为审计队列中的 `theme-factory`（新增 `references/theme-selection-matrix.md`）与 `find-skills`（新增 `references/catalog-query-recipes.md`）补充领域速查资产；为 `lark-contact`、`lark-skill-maker` 补充真实端到端消歧与 OpenAPI 脚手架示例；修正 `firebase-security-rules-auditor` 与 `linkedin-growth` 标题层级；精炼 15 个过短或偏泛的技能触发描述并校准 12 个技能 `quality` 分档。
  - 更新 `scripts/lint_skill_quality.py` 以原生识别中文常见章节标题（`适用场景`、`工作流`、`核心概念`、`参考` 等）与单数 `## Example` / `## Common Patterns`，并补充单元测试 `tests/test_lint_skill_quality.py`。
  - 组合平均分由基线 `94.2`（2 条 `review`）提升至 **`95.0`**（`295/295 keep`，`review` 队列清零，退役词回流 `0`）。

## 精选新增 5 项高价值技能

1. `claude-api`（`skills/ai-agent-platform/claude-api`，来源 `anthropics/skills`，`Apache-2.0`）：提供 Anthropic 多语言官方 SDK、Tool Runner、Prompt Caching、Refusal Fallbacks 与 Managed Agents 权威开发指南；将触发描述收敛至 240 字符以内仅限 Claude/Anthropic 场景，并将 14 节速查表拆分至 `references/api-quick-reference.md`（入口 `SKILL.md` 保持 `<= 500` 行，组合评分 `100`）。
2. `accessibility-engineering`（`skills/ai-workflow/accessibility-engineering`，来源 `addyosmani/agent-skills`，`MIT`）：提供 WCAG 2.2 AA 无障碍审计、键盘/读屏验证流程、打包的 `references/accessibility-checklist.md` 及可执行 `scripts/audit-a11y.sh`（`0755`）（组合评分 `100`）。
3. `cloudflare-agents-sdk`（`skills/deployment-platforms/cloudflare-agents-sdk`，来源 `cloudflare/skills/skills/agents-sdk`，`Apache-2.0`）：覆盖 Durable Objects SQLite 状态、`@callable` RPC、AgentWorkflow、MCP 集成与流式会话，并与 `cloudflare-deploy` / `cloudflare-troubleshooting` 明确职责边界（组合评分 `100`）。
4. `review-animations`（`skills/product-design/review-animations`，来源 `emilkowalski/skills`，`MIT`）：提供高标准 UI 动效工程审查清单与 [STANDARDS.md](../skills/product-design/review-animations/STANDARDS.md)，移除仅限特定宿主的 `disable-model-invocation` 与无问题停顿规则（组合评分 `95`）。
5. `ab-test-design`（`skills/product-design/ab-test-design`，来源 `Trystan-SA/product-engineer-skills`，`MIT`）：提供假设撰写、主/护栏指标设计、防闪烁特性开关实施及可执行 `scripts/sample_size.py` 样本量与整周周期计算器（组合评分 `92`）。

## 上游同步、基础能力与外链修复

- **浏览器基础能力**：运行 `check_browser_foundations.py` 完成对 `agent-browser`、`chrome-devtools-mcp`、`playwright-mcp`（升级跟踪 `v0.0.86`）与 Modern Web Guidance 的核查，更新 [browser-foundations.json](sources/browser-foundations.json)、`playwright/SKILL.md` 与 [浏览器基础能力维护](browser-foundation-maintenance.md)；复检 7/7 全部 `current`（`Browser foundations: complete`）。
- **Hermes 稳定镜像与监控来源**：将 `hermes-agent` 同步至官方 `v0.23.3`（`caafe5389ae585ef77387a962aee05b1bcf17029`，更新 `hermes-open-gsd-workflow` 依赖锁及 `tests/test_official_hermes_artifact_set.py` 固定版本测试）；按提交逐一审阅并保留 6 项路径变更 `monitor_review` 技能的本地策展（`ci-cd-and-automation`、`code-review-and-quality`、`spec-driven-development`、`using-agent-skills`、`linkedin`、`terraform-engineer`），并推进 `addyosmani/agent-skills` 已审监控检查点至 `8c99fa36d90068c82d547f7c12a9d67a3e95f4ee`。
- **死链清理**：将 `honcho/SKILL.md` 的 `source_url` 固定为有效提交链接；在 `scripts/check_dead_links.py` 增加对 `figma.com/design/EXAMPLEKEY` 占位示例、`api.semanticscholar.org/graph/v1/` 文档前缀及裸 `arxiv.org/{abs,pdf}/` 前缀的识别与 `os.devnull` 跨平台兼容。全仓 500 个唯一外链探测 **`dead: 0/500`**。

## 外部限制与已验证边界

- **外部仓库限制（未自动替换）**：`sync_upstream.py` 检查中 21 个 `openai/skills` 来源因上游 `LICENSE.txt` 在 Apache-2.0 末尾附加了微软版权声明且上游仓库标记向 `openai/plugins` 迁移而返回 `unavailable`（无法通过自动严格 SPDX 匹配），已按规则保留仓库内既有已审版本。
- **验证范围与性质**：本次验证均为本地静态门禁、脚本冒烟与自动化单元/集成测试（在 WSL Linux Python `3.12.3` + Node `v22.23.5` 下运行），**不构成真实在线 LLM 模型端到端评测或生产环境运行证明**：
  - 全量门禁流水线：`python scripts/validate_repository.py --refresh` 退出码 `0` — `audit_skill_instructions`（295 技能、4,462 文件、`0 findings`）、`lint_skill_quality --min-lines 50 --strict`（`298 PASS, 0 WARN, 0 FAIL`）、`audit_skill_portfolio --check-policy`（均分 `95.0`，`295 keep`、`0` 退役违规）、`audit_licenses`（307 映射条目、`MISSING: 0`、`DISALLOWED SPDX: 0`）、`validate_skill_sources`、`reconcile_artifact_inventory --offline --check-clean`、`check_source_coverage --min-percent 100`、`check_skill_references`（含 `--include-exports`，0 缺失）、`check_readme_sync`、`check_merge_conflicts` 全部通过。
  - 全量测试集：`pytest -q tests` **`3827 passed, 5 skipped, 5 warnings, 397 subtests passed`**；Node 安装器校验（`node --check bin/install-skills.js`、`--help`、`list-targets`）、`npm pack --dry-run --silent`（`common-high-value-skills-6.2.0.tgz`）、`node --test`（`65/65 pass`）、`generate_repo_health_report.py` 与 `evaluate_repo_health.py`（`PASS` 6/6）、新增脚本冒烟（`bash -n audit-a11y.sh`、`sample_size.py`）均通过。
  - 演进分支提交记录（`codex/portfolio-evolution-20261123`）：`4d7056af`（浏览器/Hermes/上游与死链）、`7d027dfa`（组合合并精简与质量提升）、`c698e8f4`（5 项新技能策展入库），以及本次视图刷新与维护报告发布准备提交。
