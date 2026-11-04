# 版本动态

[简体中文](./RELEASES.md) · [English](./RELEASES.en.md)

本文件汇总各版本的主要变化。每个版本的完整说明见 [`docs/releases/`](./releases/)，逐条变更见 [CHANGELOG.md](../CHANGELOG.md)，发布包与校验文件见 [GitHub Releases](https://github.com/seaworld008/Commonly-used-high-value-skills/releases)。

## 最新版本

**v6.0.0 技能组合精简（2026-11-04）**：退役三个重复入口（`skill-vetter` → `skill-security-auditor`，`github` → `github-ops`，`neon-postgres-egress-optimizer` → `neon-postgres`），按真实工具重写 `find-skills`、`link-checker`（新增只读检查脚本）和 `figma`，并移除默认写入 `MEMORY.md`／定时任务的指令；同时为 46 个技能补齐带触发条件的描述，完成全量上游同步检查并升级 Hermes Agent 至 v0.22.7。当前 293 个技能 / 16 个分类。[发布说明](./releases/v6.0.0.md)。

从旧版本升级时，可用 `--prune-retired` 清理已退役的技能：只删除由本安装器安装且未改动过的副本，其余一律归档保留。

```bash
npx github:seaworld008/Commonly-used-high-value-skills install --target codex --prune-retired --dry-run
```

## 近期版本

- [v5.0.0](./releases/v5.0.0.md)（2026-10-27）：完成全量策展，新增 `shadcn`、`security-model`、`remotion-video`；`self-improving-agent` 迁移为 `reflect-learn`。
- [v4.3.0](./releases/v4.3.0.md)（2026-10-24）：更新 4 个精选技能，升级行为改动与文字微调的验证流程。
- [v4.1.0](./releases/v4.1.0.md)（2026-10-16）：更新工程方法、飞书任务与图表、AKS 就绪检查和 Neon 检索指南，修复 macOS 离线 HTML 报告更新。
- [v4.0.0](./releases/v4.0.0.md)（2026-10-12）：修复 CodeQL 发现，新增“零开放 Code Scanning 告警”发布门禁，用更安全的离线 HTML 渲染器替换旧可执行文件。
- [v3.3.0](./releases/v3.3.0.md)（2026-10-12）：新增 Go 性能分析、基准测试与可观测性，架构深化、HTML 报告、动画拓扑面板和 Azure 诊断。
- [v3.2.0](./releases/v3.2.0.md)（2026-10-04）：新增 `grill-me` 计划压力测试，完成全量来源维护。

更早的版本见 [CHANGELOG.md](../CHANGELOG.md)。
