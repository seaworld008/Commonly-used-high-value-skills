# 2026-11-04 技能组合维护与 v6.0.0

基线为 `origin/main` 的 `ec74b6b`（v5.0.0 之后的 #148、#149 文档提交），从干净克隆维护，
分支 `codex/portfolio-maintenance-20261104`。用户本机仓库处于另一分支
`codex/skyai-public-navigation-skill`，本轮未触碰。

## 审计方法

- `audit_skill_portfolio.py --check-policy`：296 个入口，294 keep / 2 review，退役策略零违规。
- `audit_skill_instructions.py`：0 findings。
- `lint_skill_quality.py --strict`：298 PASS / 1 WARN（嵌套上游入口 `azure-kubernetes-app-deploy`，保持上游原样）。
- 人工按功能比对职责相近的入口：安全审查（7 个）、GitHub（`github` / `github-ops` / `gh-*`）、
  Playwright 与 Web 测试、worktree、数据库设计、代码审查、竞品分析、产品管理。
- 全仓检索 ClawHub 时代 in-house 包装的共性问题：自我安装命令、虚构的 `mcp_call(...)` 接口、
  未经请求写入 `MEMORY.md` 或 `cron`、伪装 UA 规避反爬。

评分只用于分流。退役仍按 `portfolio-policy.json` 的决定规则：没有唯一可执行资产、当前外部系统契约、
高风险领域护栏或可度量验收标准，且已有 canonical 覆盖同一用户意图。

## 退役（公开入口删除，主版本升级）

| 退役入口 | 替代入口 | 依据与迁移 |
|---|---|---|
| `skill-vetter` | `skill-security-auditor` | 单文件人工清单，与安装前技能审计意图完全重合，且自动扫描本就指向 auditor 的脚本。来源固定、权限与数据流地图、依赖审查和采纳记录模板迁入 `skill-security-auditor/references/manual-review.md`，入口新增 When to Use 与人工审查步骤。 |
| `github` | `github-ops` | 单文件 ClawHub 时代包装，只有通用 `gh` 命令，包含自我安装、`MEMORY.md` 持久化和一律二次确认的停顿。`github-ops` 已有五份参考；迁入 `gh` 认证复用、限流处理、告警分类、拆分 PR、CI 日志获取。 |

两项均写入 `portfolio-policy.json` 的 `retired_skills` 与 `canonical_groups`，不保留可发现别名；
in-house 来源记录由 bootstrap 移除，`README`、安装指南中的推荐入口改为替代技能。

## 保留（复核后不退役）

| 入口 | 保留依据 |
|---|---|
| `security-auditor` | 覆盖应用、接口、CI/基础设施与依赖的变更审计和严重度模型；与 `security-review`（代码 diff 缺陷）和 `security-audit`（可利用漏洞路径）在触发边界上不同。 |
| `git-worktree-manager` | 端口分配、环境文件和所有权清理，`using-git-worktrees` 只负责隔离工作区。 |
| `playwright-pro` | E2E 套件、flaky 诊断和框架迁移，区别于 `playwright` CLI 与 `webapp-testing`。 |
| `executing-plans` | 已在 2026-10-26 复核：计划执行、依赖顺序与证据账本的完整工作流。 |

## 优化

- `find-skills` 1.1.0：重写为“宿主技能 → 本仓库 catalog → 公开目录”的检索顺序和证据对比表；
  删除自我安装与自主安装、虚构 `mcp_call` 与评分；安装改为用户请求后执行，并先用
  `skill-security-auditor` 审查。
- `link-checker` 1.1.0：新增只读脚本 `scripts/check_links.py`（标准库、逐跳状态、HEAD→GET 回退、
  按主机限速、风险提示与分级、broken 时非零退出）；删除自我安装、伪装浏览器 UA、虚构接口和
  `MEMORY.md` 写入；明确被动检查与第三方信誉查询的数据外发边界。
- `figma` 1.1.0：改用 Figma MCP 实际工具名（`get_design_context`、`get_metadata`、
  `get_variable_defs`、`get_screenshot`、`get_code_connect_map`、`get_figjam`、`whoami`），
  增加 node-id 解析、截断处理、排查表与输出模板，并划清与 `figma-implement-design` 的边界。
- `github-ops` 1.1.0：删除某组织专用的 `NOJIRA` / `GR-1234` 标题约定（含两个参考文件），
  改为按目标仓库 CONTRIBUTING、模板和历史标题选择；补充合并前检查与上述迁移内容。
- `skill-security-auditor` 1.1.0：吸收 `skill-vetter` 的人工审查方法（本地 curation origin，
  上游检查点不变）。
- 10 个金融技能与 `frontend-design`：把“记忆同步到 `MEMORY.md` / 设置 cron”改为写入用户指定的
  记录文件，未请求时只在交付物中列出。patch 版本递增。

## 验证

- `python scripts/validate_repository.py --refresh`：完整流水线通过，820 项 pytest 与 236 subtests 通过；
  严格质量门槛零 WARN / FAIL，许可 missing/disallowed 为零，来源覆盖 100%，artifact inventory 干净。
- `check_links.py`：本地 HTTP 服务验证 301 跳转链、404、HEAD 405 回退 GET；`--list-only` 提取正确。
- 提交后重新运行生成器并 `git diff --exit-code` 证明幂等。

## 未完成与边界

- **上游同步未运行**（第二轮已补做，见下文）：本会话的 GitHub API 访问被代理拒绝（仓库未加入会话授权集），
  `sync_upstream.py --check-only` 和 reconcile 在线分类均无法执行。所有上游检查点保持原值，
  本轮不声称任何外部来源为最新；2026-10-26 记录的 59 个 monitor 待审条目仍待审。
- `skill-security-auditor` 的新参考文件以 `local-repo/curation` origin 手工登记，与 reconcile
  工具在线写入的结构一致；离线 `--check-clean` 通过。
- 没有运行真实 Figma MCP、GitHub 写操作、公开技能目录 CLI 或模型行为评测。

## 第二轮：上游同步、描述优化与 Neon 退役（同日）

第一轮 PR 的 `Repository Validation` 因 `refresh_queue = 4` 失败（4 个来源上游检查超过 30 天）。
第二轮在同一分支上补做上游同步检查，并继续优化与退役。

### 上游同步检查

`sync_upstream.py --check-only` 全量检查 163 个上游来源：44 equal、1 changed、88 monitor_review、
4 unavailable、26 expected_skipped。处理结果：

| 状态 | 技能 | 处理 |
|---|---|---|
| changed | `hermes-agent` | 按 replace 通道从 v0.22.5 升级到 v0.22.7（8 个文件，新增 `references/projects-and-folders.md`）。依赖它的 `hermes-open-gsd-workflow` 只把 Hermes 运行时问题路由给 `hermes-agent`，不依赖具体命令，经复核以 `--reviewed-dependent` 放行。上游拥有 mirror 的 `description`，同步后恢复上游原文。 |
| unavailable | `llm-wiki` | 上游把未改动的同一 blob 从 `skills/research/` 移到 `optional-skills/research/`（183b5dd），只更新 origin 路径。 |
| unavailable | `systematic-debugging` | 上游删除 `CREATION-LOG.md`、`test-academic.md`、`test-pressure-1..3.md`；`SKILL.md` 从未引用，本地同步删除并移出受管清单。 |
| unavailable | `honcho` | 上游 8112254 删除该技能，改由 Hermes 插件目录分发。仓库内没有其他技能覆盖 Honcho 记忆配置，不满足退役规则，按 `native-mcp` 先例转为固定在 7e53b3e 的归档快照（snapshot / archived）。 |
| unavailable | `neon-postgres-egress-optimizer` | 上游 neondatabase/agent-skills#172 退役该技能 ID，并入 `neon-postgres/references/egress-optimization.md`。本仓库同步退役（见下）。 |
| equal | 46 个来源 | 升级与路径修复后复查：46 equal、0 changed、0 unavailable、89 monitor_review；只对 `refresh_queue` 中过期的 4 个条目 `--record-check`，消除 `refresh_queue`（原因见第二轮验证）。 |

### 退役

| 退役入口 | 替代入口 | 依据与迁移 |
|---|---|---|
| `neon-postgres-egress-optimizer` | `neon-postgres` | 上游已退役并合并。对 `neon-postgres` 做三方合并（上游 ae9babb）：吸收 Egress Optimization 章节、热点读缓存说明、`@neon/auth` 包名、`neon-realtime` 路由，以及原样引入 `references/branching.md` 和 `references/egress-optimization.md`；保留本地的范围与授权边界、不自动安装策略和厂商中立的向量检索措辞。`branching.md` 中的 CLI 安装与登录步骤仅在用户请求配置时适用。 |

写入 `portfolio-policy.json` 的 `retired_skills` 与 `canonical_groups`；来源记录转为 `reference_only / archived / retired`。

### 描述优化

46 个技能的 `description` 只是名词罗列（多数为与 `zh_description` 相同的中文短句），没有触发条件，
自动选择不可靠。按运行手册“优先补 description、zh_description”的要求逐一阅读能力清单后重写：

- 29 个 simota 智能体（`beacon`、`builder`、`gateway`、`scout` 等）、4 个 Notion 技能、`linear`、`honcho`、`arxiv`：
  英文 `description` 改为 “Use when …” 触发式，`zh_description` 改为“……时使用”。
- 8 个安全扫描与观测技能（CodeQL、Trivy、Vuls、Semgrep、OSV、Grype/Syft、Sentry、安全所有权图）：同上，并修复
  `codeql-security-scanner`、`trivy-vulnerability-scanner`、`vuls-linux-cve-scanner` 被截断的 `zh_description`。
- `lark-workflow-standup-report`：修复被截断的 `zh_description`；其余飞书技能上游描述已含明确触发条件，保持原样。
- 各技能 patch 版本递增；外部来源只改仓库自有的 frontmatter，同步更新 `managed_files` 与本地 `content_sha256`，
  上游检查点（resolved/path commit、许可证）不变。`hermes-open-gsd-workflow` 的依赖锁随之更新。

组合审计平均分由 92.1 提升到 94.2。

### 本地环境说明

- Windows 系统级 `core.autocrlf=true` 会把检出文件转为 CRLF，使字节级摘要全部失配；本仓库已设置
  `core.autocrlf=false` 并重新检出。
- `provenance_v2.atomic_write_json` 等写入器依赖 POSIX 目录 fd，Windows 无法运行；完整流水线在 WSL Ubuntu 的
  独立克隆中执行，再把结果以补丁带回。

### 第二轮验证

- WSL Ubuntu 独立克隆中 `python scripts/validate_repository.py --refresh`：全部校验门禁通过；严格质量门槛 296 PASS / 0 WARN / 0 FAIL；
  来源、许可证、artifact inventory 与依赖锁校验通过；pytest 770 通过，其余 42 项均因该环境未安装 Node.js 而无法执行，由 CI 覆盖。
- `evaluate_repo_health.py`：Overall PASS，`refresh_queue` 0。
- 上游复查：46 equal、0 changed、0 unavailable、89 monitor_review、27 expected_skipped。
- 全局 `--record-check` 会推进 monitor 条目的已审许可证检查点，与仓库对已审检查点的固定测试冲突；因此只对
  `refresh_queue` 中与上游一致的 4 个条目（cc-devops-skills、security-audit、supabase、supabase-postgres-best-practices）记录检查。

### 仍待处理

- 89 个 default-branch 来源处于 monitor_review（上游有改动，需逐个人工三方复核），本轮未处理，保持原检查点。
- `hermes-agent` 的 `description` 由上游维护，仍缺少触发条件，需向上游反馈或接受现状。
