# Changelog / 更新日志

All notable changes to this repository are documented here.
本文件记录仓库的重要变更；版本号遵循 [Semantic Versioning](https://semver.org/)。

## [Unreleased]

### Removed / 移除

- 删除 `open-gsd-core-migration` 兼容技能以及旧 Hermes + Graphify + GSD 组合技能的 alias、tombstone 和 migration 路由；当前 portfolio 仅保留不可路由的名称 denylist，防止这些无用技能被自动重新引入。
  Removed the `open-gsd-core-migration` compatibility skill and all alias, tombstone, and migration routes for the legacy Hermes + Graphify + GSD composites; only a non-routing name denylist remains to prevent automated reintroduction.

## [2.0.0] - 2026-08-20

Revision range / 变更范围：`v1.2.0..HEAD`

### Highlights / 核心亮点

- 将来源治理升级为 provenance v2，统一管理完整 artifact set、依赖锁、许可证 lineage 与安全删除边界。
  Upgraded source governance to provenance v2 with complete artifact sets, dependency locks, license lineage, and safe deletion boundaries.
- 以官方完整产物替代 Hermes、Graphify 与旧 GSD 拼装快照，同时保留薄路由和可回滚迁移能力。
  Replaced stitched Hermes, Graphify, and legacy GSD snapshots with complete official artifacts while retaining thin routing and rollback-aware migration.
- 引入 installer v2、受管 bundle、旧技能清理和跨安装根冲突审计，并为仓库启用多语言 CodeQL 扫描。
  Added installer v2, governed bundles, retired-skill pruning, cross-root conflict auditing, and multi-language CodeQL scanning.

### Added / 新增

- 新增 provenance v2 数据模型：
  - `kind` 支持 `mirror`、`overlay`、`composite`、`bundle`、`snapshot`、`in_house` 和 `reference_only`；
  - `origins[]` 锁定仓库、路径、许可证、跟踪通道、解析 commit 与内容哈希；
  - `artifacts[]` 支持任意 source-to-target 文件或目录映射；
  - `managed_files[]` 记录受管文件、digest、mode 与安全删除所有权；
  - `composition.depends_on[]` 及依赖锁可在上游依赖推进时级联标记 composite stale。
  Added provenance v2 primitives for explicit source kinds, immutable origin checkpoints, arbitrary artifact mappings, owned managed files, and dependency-aware composite staleness.
- 新增 crash-safe artifact-set 同步引擎，支持正文、references、templates、scripts、二进制资产、文件 mode、跨目录映射、仓库 inventory 与移动/重命名识别；写入采用暂存校验和原子替换。
  Added crash-safe artifact-set synchronization for bodies, references, templates, scripts, binary assets, file modes, cross-directory mappings, repository inventories, and move/rename detection.
- 完整镜像 Hermes Agent `v2026.8.18`：`SKILL.md`、18 个官方 references 和 3 个官方 templates。
  Mirrored the complete Hermes Agent `v2026.8.18` skill artifact set, including 18 official references and 3 official templates.
- 完整收录 Graphify `v0.9.47` 官方 Codex skill 与 8 个 references。
  Added the official Graphify `v0.9.47` Codex skill and all 8 references.
- 注册 Open GSD Core `v1.11.0` 为显式安装的受管 bundle，记录 71 skills、34 agents、71 commands、共享 runtime、npm digest、release commit 与 SLSA provenance。
  Registered Open GSD Core `v1.11.0` as an explicit managed bundle with 71 skills, 34 agents, 71 commands, shared runtime, npm digests, release checkpoints, and SLSA provenance.
- 注册 Open GSD Pi `v1.16.0` 为可选、默认不安装的 bundle；其 `.gsd/` 状态与 Core 的 `.planning/` 状态严格隔离。
  Registered Open GSD Pi `v1.16.0` as an optional, non-default bundle with `.gsd/` state isolated from Core's `.planning/` state.
- 新增薄路由 `hermes-open-gsd-workflow`，只负责选择 Hermes、Graphify、GSD Core 或可选 GSD Pi，不再复制上游版本、安装命令或运行态状态机。
  Added the thin `hermes-open-gsd-workflow` router without duplicating upstream versions, installation commands, or runtime state machines.
- 新增 `open-gsd-core-migration`，集中处理旧安装检测、哈希备份、迁移验证、归档与回滚。
  Added `open-gsd-core-migration` for legacy-install detection, hash-backed backup, migration validation, archival, and rollback.
- installer v2 新增：
  - 受管安装 manifest 与文件所有权/digest/mode 记录；
  - `--bundle gsd-core` 显式 bundle 安装入口；
  - `--prune-retired`，仅直接删除未经修改且有所有权证明的旧文件；
  - `audit-conflicts --roots ... --json`，审计跨根同名但内容不同的技能；
  - 真正零写入的 `--dry-run`。
  Installer v2 now provides managed manifests, explicit bundle installation, ownership-safe retirement pruning, cross-root conflict auditing, and a truly zero-write dry run.
- 新增 portfolio decision ledger，为每个候选记录 `keep`、`merge`、`snapshot` 或 `retire`，以及替代项、独有资产、外部契约、许可证与本机清理动作。
  Added a portfolio decision ledger covering keep, merge, snapshot, and retire decisions with replacement, unique-asset, contract, license, and cleanup evidence.
- 新增 GitHub CodeQL workflow，覆盖 Actions、JavaScript/TypeScript 与 Python，并将代码扫描结果接入 PR 安全检查。
  Added GitHub CodeQL analysis for Actions, JavaScript/TypeScript, and Python, integrated with pull-request security checks.

### Changed / 变更

- 对全部受管来源执行真实上游复核，而不是沿用“映射存在即已覆盖”的假绿：
  - 同步当前 Simota 内容并跟随 `lore` 新路径；
  - 将仍有独有价值的归档技能转换为固定、带许可证的 snapshots；
  - 同步完整 Lark artifact sets；
  - 复核 Hermes、NLPM、Addy Osmani、Superpowers、LinkedIn、X/Twitter 等来源的 commit range 与吸收/保留理由。
  Re-audited the full governed portfolio, including Simota path changes and snapshots, complete Lark artifact sets, and reviewed commit ranges across Hermes, NLPM, Addy Osmani, Superpowers, LinkedIn, X/Twitter, and other sources.
- 稳定 release 与 immutable fixed ref 可在策略门禁后同步；默认分支、canary 与 composite 只进入 monitor/review，不再自动替换 canonical 内容。
  Stable releases and immutable refs may sync after policy gates; default branches, canaries, and composites are monitor/review only.
- `sync_upstream.py --check-only` 现在严格零写入；需要持久化检查时间时必须显式使用 `--record-check`。报告计数满足总量恒等式，未预期 `unavailable` 会失败而不再被视作“最新”。
  `sync_upstream.py --check-only` is now strictly read-only, check recording is explicit, report totals are internally consistent, and unexpected unavailable sources fail closed.
- 分类 README、双语主 README、catalog、标签索引、OpenClaw 导出和 banner 均从 canonical metadata 生成，不再维护组合技能的硬编码版本与安装说明。
  Category READMEs, bilingual top-level READMEs, catalog, tag index, OpenClaw export, and banner are generated from canonical metadata without hard-coded composite versions.
- 自 `v1.2.0` 以来的多轮已验证上游同步与技能组合整理统一纳入本次 major release，包括安全、可观测性、React Native、LinkedIn 和工作流类技能的新增或归类调整。
  Consolidated all verified upstream sync waves since `v1.2.0`, including additions and category refinements across security, observability, React Native, LinkedIn, and workflow skills.

### Removed / 移除

- 正式退役以下 4 个被完整替代的拼装技能，并保留永久 tombstone/alias 防止重新发现：
  - `hermes-graphify-gsd-nonintrusive-workflow`
  - `hermes-graphify-gsd-runtime-operator`
  - `hermes-graphify-gsd-project-integration`
  - `gsd-graphify-brownfield-bootstrap`
  Retired four fully superseded stitched workflows and added permanent tombstones/aliases to prevent rediscovery.
- 删除旧组合层重复的 writer lease、task board、cron、handoff、安装脚本和运行态状态机；独有迁移能力已并入 `open-gsd-core-migration`。
  Removed duplicated leases, task boards, cron jobs, handoffs, installers, and runtime state machines after preserving unique migration behavior.
- 删除 Graphify 中不完整且已漂移的 Python package/runtime 快照，仅保留官方 Codex artifact set。
  Removed the incomplete, drifted Graphify Python/runtime snapshot and retained only the official Codex artifact set.

### Fixed / 修复

- 修复外部技能被错误登记为 `in_house`、frontmatter 与 mapping 来源语义反向冲突、`source_url` 漂移及外部许可证错误豁免。
  Fixed external skills misclassified as in-house, reversed source semantics, drifting source URLs, and invalid license exemptions.
- 修复测试和 `--check-only` 污染真实 mapping 的问题，并加入 v1-to-v2 迁移、依赖级联 stale、上游移动/删除、sidecar-only 变化、二进制资产与安全删除回归测试。
  Prevented tests and read-only checks from mutating real mappings and added regression coverage for migration, dependency drift, upstream moves/deletions, sidecar-only changes, binary assets, and safe deletion.
- 修复 artifact 写入期间的 symlink/hardlink、inode 替换、临时文件 pinning 与 executable mode 保留问题。
  Hardened staged artifact writes against symlink/hardlink and inode replacement attacks while preserving executable modes.
- Repository Validation 显式安装测试所需依赖，避免 CI 因缺失 schema validator 在 collection 阶段失败。
  Repository Validation now installs required test dependencies so schema validation cannot fail during collection because of a missing package.

### Security / 安全

- GSD bundle 安装不再直接执行 npm package spec：installer 会在隔离临时目录下载固定版本，核验 pack metadata、文件路径、size、integrity、shasum 与 SHA-256，只执行验证后的本地 tarball，并在成功或失败后清理临时资产。
  GSD bundle installation now downloads the pinned package into an isolated directory, verifies metadata and cryptographic digests, executes only the verified local tarball, and always removes temporary artifacts.
- 受管清理遵循“有所有权且未修改才直接删除”：用户修改或无所有权证明的文件会先归档并移出活动发现路径。
  Managed cleanup deletes only owned, unchanged files; modified or unowned files are archived before leaving active discovery paths.
- 许可证审计升级为 lineage-aware 门禁，外部 artifact set 的许可证 checkpoint 与不可变 commit 一并记录。
  License auditing is now lineage-aware and records external artifact-set license checkpoints at immutable commits.
- 故意脆弱的依赖审计教学样本改用非 manifest 扩展名，避免 Dependabot 将测试夹具误判为仓库运行依赖。
  Intentionally vulnerable dependency-auditor fixtures now use non-manifest file names so Dependabot does not treat teaching samples as repository runtime dependencies.

### Compatibility and migration / 兼容与迁移

- 普通技能安装不会隐式安装任何 GSD bundle；GSD Core 必须显式请求，GSD Pi 保持可选且默认不安装。
  Normal skill installation never installs GSD bundles implicitly; Core requires an explicit request and Pi remains optional and disabled by default.
- 旧组合技能名称仅作为退休别名用于迁移诊断，不再作为活动技能执行。
  Legacy composite names remain only as retired aliases for migration diagnostics.
- 本次 major release 不要求安装 Hermes runtime，也不改变外部 Graphify CLI；仓库只治理其官方 skill artifacts。
  This major release does not require Hermes runtime installation or modify an external Graphify CLI; it governs only their official skill artifacts.

## [2026-03-27]

### Added
- `agent-hub` (ai-agent-platform) — agent-hub
- `aws-solution-architect` (developer-engineering) — aws-solution-architect
- `context-engineering` (developer-engineering) — context-engineering
- `docker-expert` (developer-engineering) — docker-expert
- `graphql-expert` (developer-engineering) — graphql-expert
- `kubernetes-specialist` (developer-engineering) — kubernetes-specialist
- `nextjs-app-router` (developer-engineering) — nextjs-app-router
- `python-performance` (developer-engineering) — python-performance
- `rust-engineer` (developer-engineering) — rust-engineer
- `supabase-postgres` (developer-engineering) — supabase-postgres
- `systematic-debugging` (developer-engineering) — systematic-debugging
- `tailwind-design-system` (developer-engineering) — tailwind-design-system
- `terraform-engineer` (developer-engineering) — terraform-engineer
- `test-driven-development` (developer-engineering) — test-driven-development
- `typescript-best-practices` (developer-engineering) — typescript-best-practices
- `senior-architect` (devops-sre) — senior-architect
- `web-scraper` (engineering-workflow-automation) — web-scraper
- `saas-metrics-coach` (finance-investing) — saas-metrics-coach
- `seo-audit` (growth-operations-xiaohongshu) — seo-audit
- `confidence-check` (operations-general) — confidence-check
- `supermemory` (operations-general) — supermemory
- `landing-page-generator` (product-design) — landing-page-generator
- `skill-security-auditor` (security-and-reliability) — skill-security-auditor
- `subagent-driven-development` (task-understanding-decomposition) — subagent-driven-development

### Changed
- add optimization roadmap for world-class skills repository
- add 24 high-value skills from top GitHub repos and skills.sh

### Fixed
- run refresh_repo_views, fix test expectations, normalize YAML frontmatter

[2.0.0]: https://github.com/seaworld008/Commonly-used-high-value-skills/compare/v1.2.0...v2.0.0
