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

- **上游同步未运行**：本会话的 GitHub API 访问被代理拒绝（仓库未加入会话授权集），
  `sync_upstream.py --check-only` 和 reconcile 在线分类均无法执行。所有上游检查点保持原值，
  本轮不声称任何外部来源为最新；2026-10-26 记录的 59 个 monitor 待审条目仍待审。
- `skill-security-auditor` 的新参考文件以 `local-repo/curation` origin 手工登记，与 reconcile
  工具在线写入的结构一致；离线 `--check-clean` 通过。
- 没有运行真实 Figma MCP、GitHub 写操作、公开技能目录 CLI 或模型行为评测。
