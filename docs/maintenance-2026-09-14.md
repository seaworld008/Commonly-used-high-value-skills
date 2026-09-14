# 2026-09-14 技能组合维护记录

## 组合决策

- 从 `main`/`origin/main` 的 `3fc422b` 开始，工作树无预存用户改动。
- 保持 284 个规范技能、36 个永久退休墓碑；组合审计为 271 keep / 13 review，墓碑违规 0。没有新增、退役或合并技能，也没有安装客户端或运行时。
- 13 个 review 项均有外部契约、本地质量补充或完整工作流理由，本轮不因数量或单文件深度删除。

## 已吸收更新

- Hermes Agent 稳定发布从 `v2026.8.31` 更新到 `v2026.9.11`（release `939e45c91d751fadd94dcd1b873ac3cb44846213`，path `248ff2d3e8bfc3ac4b7dfa5c5bbb95865dde75a7`）。仅 3 个受管文件有正文变化：Electron 插件根目录/能力开关说明、Windows 环境清理模块路径，以及对应 provenance、OpenClaw 导出和依赖锁；MIT 许可校验通过。
- Addy Osmani monitor-only 提交 `48cb1168aeaaa70dfc2bbf709eddfa2a8ed8129a..be4e44a9fbc5e8df0beaefadbb28bd22ee61cc39` 已提交级复核。把可迁移的会话恢复边界、告警 runbook 维护、外部规格工具格式边界原创整合到 `context-engineering`、`observability-and-instrumentation`、`spec-driven-development`；其余为触发描述或已覆盖的措辞变化。

## Monitor-only 审阅

完整来源检查为 149 项：31 equal、1 stable update、92 monitor review、25 expected-skipped、0 unavailable/rollback。已记录以下精确 checkpoint；未将非受管运行时代码、报告、插件目录或大批量内部实现覆盖进 canonical 技能：

| 来源 | 审阅提交范围 | 决定 |
|---|---|---|
| Graphify-Labs/graphify | `c9f99018..fe663890`（v0.9.55→v0.9.61） | Codex 入口字节一致；新内容是运行时、依赖、CI 和包修复，保留当前 artifact mirror |
| NousResearch/hermes-agent | `693641aa..ee445299` | stable mirror 单独升级；其余 6 个 monitor 技能未见需替换的受管正文 |
| cloudflare/security-audit-skill | `8bac4200..d24bc269` | 新增攻击类别/参考与 validator 制品需独立 artifact 迁移，本轮不覆盖现有本地策展 |
| firebase/agent-skills | `a0b4e143..28caac2d` | 插件目录与 Firestore 变体超出当前映射，不替换本地规则审计技能 |
| larksuite/cli | `7fd6ef3c..39aaf9fc` | 主要为 CLI 内部实现与测试；未发现可安全批量覆盖的受管入口 |
| microsoft/azure-skills | `49e1542b..9d46511c` | 插件目录、hooks 与新增 Azure 技能超出当前映射，保留现状 |
| simota/agent-skills | `9f7d77ad..bd5d9cd6` | 归档、模板、公共骨架与编排资产变化，不导入数量型候选 |
| wshobson/agents | `a30778f8..4236bb91` | 工具、插件治理和仓库元数据变化，未改变当前受管正文契约 |
| xiaolai/nlpm | `eb6b088f..289f1e29` | 仅 auditor 报告、日志和仪表盘变化，保留 `nlpm-audit` 正文 |

## 验证边界

- `validate_repository.py --refresh`：最终通过；质量 287 PASS / 0 WARN / 0 FAIL，完整 pytest 603 passed，来源覆盖 284/284，许可证 155 external OK、0 missing/disallowed，README/冲突/源映射检查通过。
- OpenClaw 视频映射、Python 编译、Node installer syntax/help/targets、`npm pack --dry-run`、repo health evaluation、`git diff --check` 与生成器幂等检查通过。
- 这些是静态、来源、仓库和 CI 类证据；不代表生产运行、在线迁移、数据库性能、模型成功率或真实设备验收。

## 后续组合调整

- 维护者随后决定移除低采用度的 YYLO 专用技能集合：`ledger-tasks-yylo`、`workflow-yylo`、`wiki-yylo`、`artifact-yylo`。已删除 canonical 正文、OpenClaw 导出与 provenance 映射，并将四个名称加入永久退休墓碑；其余组合保持不变。
