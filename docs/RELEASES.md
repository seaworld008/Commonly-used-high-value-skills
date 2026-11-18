# 版本动态

[简体中文](./RELEASES.md) · [English](./RELEASES.en.md)

本文件汇总各版本的主要变化。每个版本的完整说明见 [`docs/releases/`](./releases/)，逐条变更见 [CHANGELOG.md](../CHANGELOG.md)，发布包与校验文件见 [GitHub Releases](https://github.com/seaworld008/Commonly-used-high-value-skills/releases)。

## 最新版本

**v6.2.0 全量审查与浏览器持续进化（2026-11-18）**：合并 v6.1.0 的 293 项技能全量审查、来源与许可修复成果，更新 agent-browser 0.43.0、DevTools 与 Playwright 指引；新增每次全仓维护与周一定时流程的基础能力优先检测、待适配跟踪和验证后基线推进。[发布说明](./releases/v6.2.0.md)。

从旧版本升级时，可用 `--prune-retired` 清理已退役的技能：只删除由本安装器安装且未改动过的副本，其余一律归档保留。

```bash
npx github:seaworld008/Commonly-used-high-value-skills install --target codex --prune-retired --dry-run
```

## 近期版本

- [v6.1.0](./releases/v6.1.0.md)（2026-11-17）：已合并进 v6.2.0；历史审查记录保留。

- [v6.0.0](./releases/v6.0.0.md)（2026-11-04）：精简三个重复入口，保留 293 个技能，更新触发描述、工具发现及上游检查。

- [v5.0.0](./releases/v5.0.0.md)（2026-10-27）：完成全量策展，新增 `shadcn`、`security-model`、`remotion-video`；`self-improving-agent` 迁移为 `reflect-learn`。
- [v4.3.0](./releases/v4.3.0.md)（2026-10-24）：更新 4 个精选技能，升级行为改动与文字微调的验证流程。
- [v4.1.0](./releases/v4.1.0.md)（2026-10-16）：更新工程方法、飞书任务与图表、AKS 就绪检查和 Neon 检索指南，修复 macOS 离线 HTML 报告更新。
- [v4.0.0](./releases/v4.0.0.md)（2026-10-12）：修复 CodeQL 发现，新增“零开放 Code Scanning 告警”发布门禁，用更安全的离线 HTML 渲染器替换旧可执行文件。
- [v3.3.0](./releases/v3.3.0.md)（2026-10-12）：新增 Go 性能分析、基准测试与可观测性，架构深化、HTML 报告、动画拓扑面板和 Azure 诊断。
- [v3.2.0](./releases/v3.2.0.md)（2026-10-04）：新增 `grill-me` 计划压力测试，完成全量来源维护。

更早的版本见 [CHANGELOG.md](../CHANGELOG.md)。
