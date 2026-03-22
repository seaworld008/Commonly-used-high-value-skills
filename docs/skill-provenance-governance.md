# Skill Provenance Governance (持续净化方案)

> 目标：让仓库长期可持续“收藏 + 同步 + 优化”全网优质 skills，同时可追溯来源、可自动检查、可定期更新。

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
- `docs/sources/provenance.config.json`：统一配置（阈值/输出路径）

## 3) 状态模型（status）

- `verified_in_repo`：已验证并已纳入仓库
- `verified_not_in_repo`：已验证存在，但暂未纳入仓库
- `in_house`：本仓库原创技能
- `not_a_skill`：概念/平台/工具，不是技能 slug
- `unverified_slug`：候选项，尚未验证 slug

## 4) 标准工作流（每次收藏）

1. 新建或更新来源 JSON（`docs/sources/*.skills.json`）。
2. 统一执行（推荐）：
   ```bash
   python3 scripts/provenance_pipeline.py --mode all --config docs/sources/provenance.config.json
   ```
3. 如需分步排障，再按下方脚本逐步执行。
   ```bash
   python3 scripts/validate_skill_sources.py
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
   python3 scripts/check_source_coverage.py --min-percent 95
   ```
8. PR 中必须包含：
   - 来源 JSON 变更
   - 验证命令与结果
   - 是否为原创（`in_house`）或外部来源

## 5) 定期更新策略（建议）

- 建议在 CI/cron 中每周自动跑：
  - `python3 scripts/bootstrap_in_house_sources.py --write-json docs/sources/in-house.skills.json`
  - `python3 scripts/validate_skill_sources.py`
  - `python3 scripts/check_source_coverage.py --min-percent 95`
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

## 6) 业界最佳实践对齐（可选增强）

- **Provenance/SBOM 思路**：把 skill 来源当作“内容供应链”管理，保留来源、版本、更新时间和验证记录。
- **OpenSSF 思路**：持续自动化校验（结构、来源、可追溯性），减少手工失误。
- **Renovate 思路**：定期扫描并自动发起更新 PR（未来可加脚本化 diff/同步流程）。

## 7) 最小落地清单

- [x] 建立来源 JSON 约定
- [x] 建立通用校验脚本
- [x] 增加来源索引
- [x] 增加定期巡检 CI（GitHub Actions）
- [x] 增加批量更新队列脚本
- [x] 增加批量更新提案脚本（dry-run）
- [ ] 增加自动更新提案脚本（可选）
- [x] 增加 upstream 更新检测脚本
- [x] 增加来源覆盖率门禁


## 8) 阶段收敛（告一段落）

建议以以下最小节奏稳定运行：

1. 日常开发：仅维护 `skills/` 与 `docs/sources/*.skills.json`。
2. 提交前：运行一次 `python3 scripts/provenance_pipeline.py --mode quick --config docs/sources/provenance.config.json`。
3. CI：运行单元测试 + `--mode all` 全流程。
4. 周期巡检：看 `refresh-queue` 与 `upstream-check`，按优先级处理。

如果没有新增来源或上游变更，可不做额外动作，保持系统稳定。
