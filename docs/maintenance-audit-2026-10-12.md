# 2026-10-12 例行技能策展及发布治理复核

## 版本与基线

- 核查分支：`main`，基线 SHA：`3bb0fa394ed6dd00f83a2b28457d882665e22d79`（2026-10-12）。
- 最近正式发布：`v3.2.0`（2026-10-03）。
- `skills/<category>/<slug>/SKILL.md` 规范入口 **287** 个，分类 **16** 个；`openclaw-skills/<slug>/SKILL.md` 导出入口 287 个。另有 3 个嵌套 SKILL.md（`skill-tester` 示例和 AKS 子技能），不应误计入公开入口。
- 基线 main 的 Repository Validation、skills-provenance-ci、CodeQL 均为 success（Actions runs：38191276656、38191276680、38191276663）。
- PR #130（单格 A1 引用）仍开放，不并入本次维护，也不删除其分支。

## 本轮审阅决策

| 范围 | 结论 |
| --- | --- |
| 规范入口和导出入口 | 清单交叉核对，维持 287 个公开技能；不把嵌套示例误标成新技能。 |
| DevOps/SRE 的 12 个规范技能入口 | 已复核入口结构、版本、更新日期和任务定位；未找到足以支持直接淘汰或覆盖的证据。 |
| 上游来源与许可 | 沿用 2026-10-03 的逐项策展快照及现有 provenance/许可证 CI；本轮未逐个联网重新核对全部 153 个跟踪源，不把历史快照称为今日最新。 |
| 新增候选 | 目前没有经过功能去重、不可变版本核验和许可审计的明确高价值候选，不以凑数新增。 |
| 发布历史 | `v3.2.0` 已正式发布，但变更日志仍将其内容放在 Unreleased；补上对最新稳定 tag 的自动归档和防回归测试。 |

## 变更及边界

- 修正 `generate_changelog.py --since last-tag --preserve-history`：仅在最新版稳定 semver tag 尚无对应 release 章节、且 tag 自身的自动区块合法时，归档该已发布区块；已有历史原样保留，二次运行幂等。
- 补充真实临时 git 仓库的自动归档回归，覆盖历史保全、最新修复进入 Unreleased、一次归档与重跑幂等。
- 将历史 `v3.2.0` 自动区块归档到独立发布章节；当前 Unreleased 从 `v3.2.0..HEAD` 起，避免重复标注已发布变更。
- 未修改规范技能、受管来源元数据、自动生成导出文件或安装器，也未更改用户环境。
- 此次复核为仓库结构、已发布 CI 证据和抽样技能审阅，**不等价于**所有上游当日在线校验、真实模型行为评测或完整生产环境验收。新 PR 和合并后 main 的门禁结果应分别记录。

## 验证门禁

应在本 PR head 和最终合并 main SHA 上分别验证 Repository Validation、skills-provenance-ci、CodeQL；完整流水线须执行 `python scripts/validate_repository.py --refresh`，并检查 `git diff --exit-code` 生成幂等、Windows/Ubuntu Node 22/24 安装器测试及新归档回归。发布制品仍应从验证过的 main SHA 构建、下载复核摘要和 SHA256，再公开 Release。
