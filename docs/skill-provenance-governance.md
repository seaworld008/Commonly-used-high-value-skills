# Skill Provenance Governance (持续净化方案)

> 目标：让仓库长期可持续“收藏 + 同步 + 优化”全网优质 skills，同时可追溯来源、可自动检查、可定期更新。

每周精选、替换/剔除判断、外部阻塞源分类和自动化模型要求见 [Skill Curation and Automation Runbook](./skill-curation-and-automation-runbook.md)。

## 1) 基本原则

1. **每个外部来源都要有机器可读记录**（JSON 映射）。
2. **先记录来源，再复制/改造技能**。
3. **每次更新都保留证据**（验证时间、验证方式、结果）。
4. **本仓库原创技能与外部引入技能区分管理**。
5. **自动化使用统一入口**，避免脚本链条分散。
6. **报告类生成物默认不入库**（可复现，减少仓库噪音）。

## 2) 推荐目录约定

- `skills/<category>/<skill>/`：唯一事实来源（canonical skill source）
- `openclaw-skills/`：自动导出（禁止手改）
- `docs/sources/*.skills.json`：来源映射（一个来源一份）
- `docs/sources/*.bundle.json`：由官方安装器管理、不可平铺为普通技能的 bundle
- `docs/sources/templates/skills-source.template.json`：来源模板
- `docs/sources/reports/` 与 `docs/sources/index.json`：流水线生成物（默认不提交）
- `scripts/validate_skill_sources.py`：来源映射校验器（通用）
- `scripts/bootstrap_in_house_sources.py`：为本仓库全部技能生成 in_house 来源映射
- `scripts/check_source_coverage.py`：覆盖率门禁（防止来源映射遗漏）
- `scripts/skills_refresh_planner.py`：批量生成“待更新队列”（优先级排序）
- `scripts/build_skills_catalog.py`：聚合所有来源映射并检测 slug 冲突
- `scripts/generate_sources_index.py`：生成全局来源索引（全局状态/覆盖率）
- `scripts/skills_bulk_update_stub.py`：从 refresh queue 自动生成批量更新执行计划（安全 dry-run）
- `scripts/check_upstream_github_updates.py`：检查 GitHub upstream 是否有更新（支持 offline/online 模式）
- `scripts/provenance_pipeline.py`：统一执行入口（一条命令跑完整流程）
- `scripts/migrate_provenance_v2.py`：来源映射 v1→v2 迁移与显式受管哈希刷新
- `scripts/reconcile_artifact_inventory.py`：逐文件判定外部 exact artifact 与本地 curation overlay
- `scripts/artifact_set_sync.py`：受管 artifact-set 的事务式暂存、替换、回滚与安全删除
- `scripts/github_artifact_provider.py`：按不可变 commit 读取 GitHub tree/blob 与移动候选
- `scripts/provenance_v2.schema.json`：provenance v2 的机器可读契约
- `docs/sources/provenance.config.json`：统一配置（阈值/输出路径）

## 3) Provenance v2 模型

`status` 保留给旧消费者读取；新的治理与同步逻辑以 v2 字段为准：

- `kind`：`mirror`、`overlay`、`composite`、`bundle`、`snapshot`、`in_house` 或 `reference_only`
- `origins[]`：每个来源的仓库、路径、许可证、同步模式、artifact 映射与不可变 checkpoint
- `artifacts[]`：显式声明任意上游 `source` 到仓库 `target` 的文件映射
- `managed_files[]`：记录受管路径、SHA-256 和 owner；未来清理只能作用于这些边界
- `composition.depends_on[]`：组合技能的机器可读依赖
- `composition.dependency_lock`：依赖内容哈希；依赖推进后组合技能必须进入复核

所有活动 mapping 默认必须是 `schema_version: 2`。只有兼容旧 fixture 或迁移排障时才允许显式使用 `validate_skill_sources.py --allow-v1`。

`managed_files` 不是“当前目录文件列表”的同义词，而是覆盖、更新和删除授权。每条记录同时锁定 `sha256` 与 Git 可移植模式 `100644`/`100755`；仅执行位变化也属于必须复核或受管修复的状态变化。可进入的文件必须有下列已核实来源之一：

- 在锁定 commit 上与上游 blob 字节完全一致的 external artifact；
- 已证明基于该固定来源、保留许可并记录改动的 `overlay` 改编；其外部 owner 表示派生来源，必须保持 `monitor`，不能自动覆盖本地字节；
- 明确归属于 `local-repo/curation`、永不被外部 origin 覆盖的本地原创文件。

`managed_files.sha256` 锁定实际本地交付；它不证明与上游原样相同。上游 blob、摘要、模式与本地改编关系应另外保留在 artifact 证据中。只有逐字节复核后的文件才能称为 external exact；本地摘要刷新不能替代来源或许可证据。

首次治理或历史目录补录时先只读盘点，再显式写入：

```bash
python scripts/reconcile_artifact_inventory.py \
  --output /tmp/artifact-inventory.json
python scripts/reconcile_artifact_inventory.py \
  --write --output /tmp/artifact-inventory-write.json
python scripts/reconcile_artifact_inventory.py \
  --offline --output /tmp/artifact-inventory-idempotence.json
python scripts/reconcile_artifact_inventory.py \
  --offline --check-clean --quiet
```

只要出现 `unavailable`、所有权冲突、受管哈希漂移、symlink 或扫描错误，写入必须停止；不能通过刷新 digest 消除用户修改证据。

迁移默认只读：

```bash
python scripts/migrate_provenance_v2.py
python scripts/migrate_provenance_v2.py --write
```

归一化后的受管哈希只能显式刷新；该命令不会扩张 artifact 清单，也不会掩盖缺失文件：

```bash
python scripts/migrate_provenance_v2.py --refresh-managed-digests --write
```

### Release channel 策略

- `latest_release`：canonical skill 只有在解析后的不可变 commit 上通过
  许可证与 artifact inventory 门禁后才可自动同步；包签名、SLSA 与制品
  完整性属于 bundle-specific tooling，不能由普通 skill sync 冒充。
- `fixed_ref`：只有不可变 ref 才可自动同步。
- `default_branch`、`canary`：一律 `monitor`，进入人工复核，不能自动覆盖 canonical 内容。
- `local`：仅允许 `local-only`。
- `snapshot`、已归档来源：不再跟随活动分支；保留许可证、最后 checkpoint 和退役理由。

## 4) 兼容状态模型（status）

- `verified_in_repo`：已验证并已纳入仓库
- `verified_not_in_repo`：已验证存在，但暂未纳入仓库
- `in_house`：本仓库原创技能
- `not_a_skill`：概念/平台/工具，不是技能 slug
- `unverified_slug`：候选项，尚未验证 slug

## 5) 标准工作流（每次收藏）

1. 新建或更新来源 JSON（`docs/sources/*.skills.json`）。
2. 统一执行（推荐）：
   ```bash
   python3 scripts/provenance_pipeline.py --mode all --config docs/sources/provenance.config.json
   ```
3. 如需分步排障，再按下方脚本逐步执行。
   ```bash
   python3 scripts/validate_skill_sources.py
   python3 scripts/audit_licenses.py
   ```
4. 如果引入了新 skill 源文件，刷新导出：
   ```bash
   python3 scripts/refresh_repo_views.py
   ```
5. 生成批量更新候选清单（推荐）：
   ```bash
   python3 scripts/skills_refresh_planner.py --stale-days 30 --write-json docs/sources/reports/refresh-queue.json
   ```
6. 生成批量执行计划（推荐）：
   ```bash
   python3 scripts/skills_bulk_update_stub.py --queue docs/sources/reports/refresh-queue.json --write-plan docs/sources/reports/bulk-update-plan.md
   ```
7. 执行覆盖率门禁：
   ```bash
   python3 scripts/check_source_coverage.py --min-percent 100
   ```
8. PR 中必须包含：
   - 来源 JSON 变更
   - 验证命令与结果
   - 是否为原创（`in_house`）或外部来源

检查上游时，普通 `--check-only` 不修改 canonical skill 或 provenance
mapping。显式 `--report-json` 会写报告，显式 `--record-check` 会更新
mapping 的检查 checkpoint：

```bash
python scripts/sync_upstream.py --check-only
python scripts/sync_upstream.py --check-only --record-check
python scripts/sync_upstream.py --check-only \
  --report-json /tmp/upstream-report.json
```

机器报告采用三态：

- `complete`（退出码 `0`）：检查可信完成；可能包含可自动吸收的 `changed` 或显式 `expected_skipped`。
- `degraded`（退出码 `2`）：存在 `monitor_review` 或上游 rollback，必须人工处理。
- `failed`（退出码 `1`）：存在未预期 unavailable、空输入、记录失败或事务失败，禁止声称“全部最新”。

报告必须满足：

```text
total = equal + changed + monitor_review + unavailable + rollback + expected_skipped
```

artifact apply 只覆盖所选 external origin 已有且 digest 未被用户修改的受管目标。其他 origin 的文件受到保护；上游删除只会 prune manifest 授权且当前 hash 仍匹配的文件。技能目录和 mapping 使用两阶段事务，mapping 未成功提交时必须恢复原 artifact set。

跨 mapping/skill 的写入使用仓库私有状态目录 `.hvs-transactions/` 保存崩溃恢复 journal。该目录已被 Git 忽略；固定 `batch.lock` 可以长期存在。不要手工删除 `pending/` 或其中的原始文件：下一次受管写操作会在取得全局锁后自动判定完成或回滚，无法安全判定时会保留 recovery 路径并失败关闭。`--check-only`、`--dry-run` 和 inventory 只读检查既不会创建事务状态，也不会恢复或删除已有 journal；若只读路径发现待恢复事务，应先运行相应的受管写操作完成恢复。

## 6) 定期更新策略（建议）

- 建议在 CI/cron 中每周自动跑：
  - `python3 scripts/bootstrap_in_house_sources.py --write-json docs/sources/in-house.skills.json`
  - `python3 scripts/validate_skill_sources.py`
  - `python3 scripts/check_source_coverage.py --min-percent 100`
  - `python3 scripts/skills_refresh_planner.py --stale-days 30 --write-json docs/sources/reports/refresh-queue.json`
  - `python3 scripts/build_skills_catalog.py --write-json docs/sources/reports/catalog.json`
  - `python3 scripts/generate_sources_index.py --write-json docs/sources/index.json`
  - `python3 scripts/check_upstream_github_updates.py --online --write-json docs/sources/reports/upstream-check.json`

不带 `--online` 的检查只用于确定性 inventory/CI 结构验证，永远不能
返回 `complete`；有效离线盘点为 `degraded`，空输入、inventory 错误或
unavailable 仍必须是 `failed`。它不能作为“当前上游已是最新”的新鲜度
证据。
- 通过 refresh queue 的 `priority` 字段批量处理最紧急条目。
- 通过 catalog 的 `conflicts` 字段快速发现跨来源 slug 冲突。
- 通过 sources index 快速查看全局覆盖率与状态分布。

- 每周/每两周运行一次“来源巡检”：
  - 检查 `unverified_slug` 是否可升级
  - 检查 `verified_not_in_repo` 是否值得纳入
  - 检查已收录技能 upstream 是否有重大更新
- 对高价值技能增加维护优先级（核心工作流、易过期技能、依赖外部 API 的技能）。

## 7) 业界最佳实践对齐（可选增强）

- **Provenance/SBOM 思路**：把 skill 来源当作“内容供应链”管理，保留来源、版本、更新时间和验证记录。
- **OpenSSF 思路**：持续自动化校验（结构、来源、可追溯性），减少手工失误。
- **Renovate 思路**：定期扫描并自动发起更新 PR（未来可加脚本化 diff/同步流程）。

## 8) 最小落地清单

- [x] 建立来源 JSON 约定
- [x] 建立通用校验脚本
- [x] 增加来源索引
- [x] 增加定期巡检 CI（GitHub Actions）
- [x] 增加批量更新队列脚本
- [x] 增加批量更新提案脚本（dry-run）
- [ ] 增加自动更新提案脚本（可选）
- [x] 增加 upstream 更新检测脚本
- [x] 增加来源覆盖率门禁
- [x] provenance v2 来源、artifact、许可证与依赖 DAG 门禁
- [x] `--check-only` 零写入与显式 `--record-check`
- [x] artifact-set 全文件同步、二进制安全与安全 prune
- [x] external/local overlay 唯一所有权与历史 sidecar 全量纳管
- [x] 周期任务 `complete/degraded/failed` 三态与守恒报告


## 9) 阶段收敛（告一段落）

建议以以下最小节奏稳定运行：

1. 日常开发：仅维护 `skills/` 与 `docs/sources/*.skills.json`。
2. 提交前：运行一次 `python3 scripts/provenance_pipeline.py --mode quick --config docs/sources/provenance.config.json`。
3. CI：运行单元测试 + `--mode all` 全流程。
4. 周期巡检：看 `refresh-queue` 与 `upstream-check`，按优先级处理。

如果没有新增来源或上游变更，可不做额外动作，保持系统稳定。
