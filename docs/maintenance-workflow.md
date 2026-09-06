# 技能维护工作流

本文件供维护任务按需读取；日常约定见 [AGENTS.md](../AGENTS.md)。

## 前置检查

```bash
git status --short --branch
git worktree list
git fetch origin --prune
gh auth status
```

先确认已有改动的归属。干净的 main 可以 `git pull --ff-only`，再建 `codex/` 分支；有改动时在独立 worktree 工作。GitHub 自动化优先使用 `GITHUB_TOKEN` / `GH_TOKEN`，缺省复用已认证的 `gh`，不要输出令牌。

## 更新现有技能

```bash
python scripts/sync_upstream.py --check-only
```

该命令只读；需要记录检查时间时显式用 `--record-check`。
审阅 `artifact_changed`、`monitor_review`、`expected_skipped`、`unavailable`：

- 已审阅的稳定版本或固定引用：使用 `sync_upstream.py --apply` 更新其管理的文件。
- 默认分支、canary、策展版本：查看上次检查点到当前提交的差异，吸收适用变更并记录理由；不自动覆盖本地正文。
- snapshot / local-only：保留有效授权快照；上游消失不等于用户授权删除。
- 网络或来源路径失败：记录源、错误和重试结果；不能把未检查成功的来源计入“最新”。

保留本地 frontmatter、领域补充和辅助文件；修改内容时提高 patch 版本并更新日期。新增引用也要纳入 artifact inventory。来源变化需刷新并检查 provenance v2，不能用摘要刷新掩盖未经审阅的替换。

```bash
python scripts/refresh_repo_views.py
python scripts/migrate_provenance_v2.py --write --refresh-managed-digests
python scripts/reconcile_artifact_inventory.py --offline --check-clean --quiet
```

## 发现与收录

仅在请求增加技能时执行发现；一次全面优化不意味着扩充数量。

```bash
python scripts/discover_new_skills.py --output docs/sources/reports/discovery.json
```

按实际需求补充 skills.sh、ClawHub 和公开代码库检索。与现有技能按功能去重，核对上游许可。复制仅允许 `audit_licenses.py` 接受的宽松许可；缺少许可但方法有价值时原创 in-house 重写，不复制文本。

分类匹配主要功能；现有分类和数量从 `docs/catalog.json` 读取。优先复用已有入口，避免同一任务需要多个职责重叠的路由技能。

```bash
python scripts/ingest_skill.py --dir skills/<category>/<skill-name> --source '<source-url>'
```

## 技能内容约定

```yaml
---
name: example-skill
description: "Review API compatibility when changing public endpoints or schemas."
zh_description: "审查公共接口和数据结构变更的兼容性。"
version: "1.0.0"
author: seaworld008
source: in-house
source_url: ""
license: MIT
tags: [api, compatibility, review]
created_at: "YYYY-MM-DD"
updated_at: "YYYY-MM-DD"
quality: 3
complexity: intermediate
---
```

描述写任务与触发边界，正文写执行方法和验收；不要把整套流程挤进 description。保留 Trigger/When to Use、能力或步骤、可用示例、边界。基础门槛是 50 行，质量 3/4/5 的入口分档为 80/100/200 行；这些是仓库检查门槛，不代表模型能力评分。长示例和查阅表按需放入技能自带引用，避免逐行填充或重复通用规范。

## 完整流水线

在项目 Python 环境安装 `pyyaml pytest jsonschema`；使用一个顺序执行、失败即停的跨平台入口：

```bash
python scripts/validate_repository.py --refresh
```

不带 `--refresh` 时只执行校验。刷新阶段依次运行 frontmatter、in-house 来源、仓库视图、标签和 catalog 生成；校验阶段覆盖指令、质量、组合策略、许可、来源、覆盖率、README、冲突标记和完整 pytest。脚本不会提交、推送、安装技能或修改用户配置。

修改安装器时另外执行 `npm test`；修改 GitHub Actions 时检查所有 YAML 和 `actionlint`（可用时）。CI 保留独立来源检查与 CodeQL。流水线全部通过才进入提交。

## PR 与交付

1. 审查文件清单和 diff，仅暂存这次修改与对应生成物。禁止对含用户改动的工作区盲目 `git add -A`。
2. 提交后重跑刷新并执行 `git diff --exit-code`，证明生成器幂等；`git diff --check` 仅证明空白格式。
3. 推送分支，PR 说明具体问题、改变后的行为、证据与限制。若同时增加技能和大批同步，拆分 PR。
4. 检查最新 PR head 的检查项、审阅反馈和 mergeability，修复有效问题。已经获得合并授权时继续合并 main。
5. fetch 后核对合并 SHA 与 main，等待该 SHA 的 CI，并确认本地工作区干净。

变更历史使用 `python scripts/generate_changelog.py --preserve-history`；只允许更新唯一 Unreleased 内的标记块，保留已整理历史。
模型延迟、成本和任务成功率需要独立运行的评测；静态指令检查与仓库测试不能代替这些结果。
