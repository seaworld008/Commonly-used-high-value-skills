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

- `latest_release`：可在许可证、签名/制品和 inventory 门禁通过后自动同步。
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

检查上游时，`--check-only` 保证零写入；只有明确需要记录检查时间时才使用 `--record-check`：

```bash
python scripts/sync_upstream.py --check-only
python scripts/sync_upstream.py --check-only --record-check
```

## 6) 定期更新策略（建议）

- 建议在 CI/cron 中每周自动跑：
  - `python3 scripts/bootstrap_in_house_sources.py --write-json docs/sources/in-house.skills.json`
  - `python3 scripts/validate_skill_sources.py`
  - `python3 scripts/check_source_coverage.py --min-percent 100`
  - `python3 scripts/skills_refresh_planner.py --stale-days 30 --write-json docs/sources/reports/refresh-queue.json`
  - `python3 scripts/build_skills_catalog.py --write-json docs/sources/reports/catalog.json`
  - `python3 scripts/generate_sources_index.py --write-json docs/sources/index.json`
  - `python3 scripts/check_upstream_github_updates.py --write-json docs/sources/reports/upstream-check.json`
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


## 9) 阶段收敛（告一段落）

建议以以下最小节奏稳定运行：

1. 日常开发：仅维护 `skills/` 与 `docs/sources/*.skills.json`。
2. 提交前：运行一次 `python3 scripts/provenance_pipeline.py --mode quick --config docs/sources/provenance.config.json`。
3. CI：运行单元测试 + `--mode all` 全流程。
4. 周期巡检：看 `refresh-queue` 与 `upstream-check`，按优先级处理。

如果没有新增来源或上游变更，可不做额外动作，保持系统稳定。
