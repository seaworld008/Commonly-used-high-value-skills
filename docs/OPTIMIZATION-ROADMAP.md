# 仓库优化路线图：打造全球最佳 Skills 收藏仓库

> 基于对当前仓库架构的深度审计和全球 Awesome List / Skills 平台最佳实践调研，提出以下优化路线图。

---

## 一、现状诊断

### 做得好的
- ✅ 双径分发架构（`skills/` 分类 + `openclaw-skills/` 扁平导出）适配多客户端
- ✅ 自动化工具链完备：17 个脚本覆盖刷新/导出/校验/溯源
- ✅ CI 双流水线（repo-validation + provenance-ci）
- ✅ 中英双语 README + AI Agent 指令（AGENTS.md）
- ✅ 溯源系统（provenance）有完整的 JSON 映射和检查脚本

### 关键差距

| 维度 | 现状 | 目标标准 | 差距等级 |
|------|------|---------|---------|
| **元数据完整性** | 仅 `name` + `description`，无 version/author/tags/source | 每个技能有完整的结构化元数据 | 🔴 严重 |
| **质量均匀度** | 20~700 行，26 个技能 <50 行（骨架级） | 每个技能 ≥80 行，有实战指导价值 | 🔴 严重 |
| **上游同步能力** | `check_upstream_github_updates.py` 仅检测，无自动同步 | 定期自动发现+创建 PR 同步 | 🟡 中等 |
| **搜索与发现** | 仅靠 README 列表浏览 | 标签索引 + 语义搜索 + 排行榜 | 🟡 中等 |
| **社区贡献机制** | 有 CONTRIBUTING.md 但无 PR 模板/Issue 模板 | 标准化贡献流程 + 质量门禁 | 🟡 中等 |
| **变更追踪** | 无 CHANGELOG | 自动生成变更日志 | 🟠 一般 |
| **许可证治理** | 未检查收录技能的 License | 自动 License 审计 | 🟠 一般 |

---

## 二、优化方案（按优先级排列）

### P0 — 基础质量提升（立即执行）

#### 2.1 扩展 SKILL.md Frontmatter Schema

当前只有 `name` + `description`，需要扩展为标准化 Schema：

```yaml
---
name: kubernetes-specialist
description: "用于 K8s 集群管理、部署编排、Pod 调试与 Helm Chart 设计。"
version: "1.0.0"
author: seaworld008              # 作者 GitHub ID
source: skills.sh                # 来源平台：in-house | skills.sh | clawhub | github
source_url: ""                   # 上游原始 URL（如有）
tags: [kubernetes, devops, container, helm]  # 跨分类的标签索引
created_at: "2026-03-27"
updated_at: "2026-03-27"
quality: 4                       # 质量评分 1-5（精选级 ≥4）
complexity: intermediate         # beginner | intermediate | advanced
---
```

**实施方式**：编写 `scripts/enrich_frontmatter.py`，自动为所有现有技能补充缺失字段（从目录结构推断 `tags`，从 `git log` 提取 `created_at`，默认 `quality: 3`）。

#### 2.2 补强骨架级技能

26 个技能不足 50 行，内容价值低，需要逐一充实：

| 行数 | 数量 | 示例 | 处理方式 |
|------|------|------|---------|
| <25 行 | 8 个 | `proactive-agent`(20), `gog`(20), `skill-vetter`(20) | 扩写到 ≥100 行或标记为 `stub` |
| 25-40 行 | 13 个 | 金融类 7 个均为 37 行 | 批量扩写，补充实战模板 |
| 40-50 行 | 5 个 | `figma`(42), `frontend-design`(42) | 中等优先级扩写 |

**实施方式**：编写 `scripts/lint_skill_quality.py`，CI 中强制检查 `SKILL.md` 最少行数（≥80）、必须包含的 Section（`## 触发条件` 或 `## When to Use`）、代码示例（至少 1 个代码块）。

#### 2.3 CI 增强：质量门禁

在 `repo-validation.yml` 中添加：

```yaml
- name: Lint skill quality
  run: python scripts/lint_skill_quality.py --min-lines 80 --require-sections "trigger,capabilities"

- name: Validate frontmatter schema  
  run: python scripts/validate_frontmatter.py --require "name,description,tags,version"

- name: Check dead links
  run: python scripts/check_dead_links.py --timeout 10
```

---

### P1 — 持续更新机制（核心竞争力）

#### 2.4 自动上游同步 GitHub Action

新建 `.github/workflows/upstream-sync.yml`，每周自动：

```yaml
name: Upstream Skill Sync
on:
  schedule:
    - cron: '0 2 * * 1'  # 每周一凌晨 2 点
  workflow_dispatch:       # 支持手动触发

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      
      # 1. 扫描全网热门来源
      - name: Discover new skills
        run: python scripts/discover_new_skills.py --sources skills.sh,clawhub,github --output docs/sources/reports/discovery.json
      
      # 2. 检查已收录技能的上游更新
      - name: Check upstream updates
        run: python scripts/check_upstream_github_updates.py --online --write-json docs/sources/reports/upstream-check.json
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      # 3. 生成同步 PR
      - name: Create sync PR if updates found
        run: python scripts/create_sync_pr.py --discovery docs/sources/reports/discovery.json --upstream docs/sources/reports/upstream-check.json
```

需要新建的脚本：
- `scripts/discover_new_skills.py` — 从 skills.sh API、ClawHub API、GitHub trending 自动发现新技能
- `scripts/create_sync_pr.py` — 将发现的更新打包成 PR，附带 diff 摘要

#### 2.5 外部来源的 upstream 映射

当前 `in-house.skills.json` 中所有技能的 `upstream.repo` 都是 `local-repo/in-house`。对于实际来自外部的技能，需要记录真实上游：

```json
{
  "video_name": "kubernetes-specialist",
  "status": "curated",
  "upstream": {
    "repo": "alirezarezvani/claude-skills",
    "path": "skills/kubernetes-specialist",
    "ref": "main",
    "last_synced_commit": "abc123...",
    "last_checked_at": "2026-03-27",
    "license": "MIT"
  }
}
```

这样 `check_upstream_github_updates.py --online` 才能真正检测到上游变更。

---

### P2 — 搜索与发现体验

#### 2.6 标签索引系统

基于 frontmatter 中的 `tags` 字段，自动生成 `docs/TAGS-INDEX.md`：

```markdown
## Tags Index

### kubernetes (5 skills)
- [kubernetes-specialist](skills/developer-engineering/kubernetes-specialist) ⭐4
- [docker-expert](skills/developer-engineering/docker-expert) ⭐4
- [senior-devops](skills/devops-sre/senior-devops) ⭐3
...

### react (3 skills)
...
```

**实施方式**：新建 `scripts/generate_tags_index.py`，在 `refresh_repo_views.py` 中调用，CI 检查一致性。

#### 2.7 技能排行榜

在 README 中增加 "精选推荐" 区域，基于 `quality` 评分自动生成：

```markdown
## ⭐ 精选推荐（Top 20）

| 排名 | 技能 | 分类 | 评分 | 标签 |
|------|------|------|------|------|
| 1 | prompt-engineer-toolkit | developer-engineering | ⭐⭐⭐⭐⭐ | prompt, ai |
| 2 | kubernetes-specialist | developer-engineering | ⭐⭐⭐⭐ | kubernetes, devops |
```

#### 2.8 技能目录 JSON API

自动生成 `docs/catalog.json`，提供机器可读的技能目录：

```json
{
  "version": "1.0.0",
  "total_skills": 163,
  "categories": [...],
  "skills": [
    {
      "name": "kubernetes-specialist",
      "category": "developer-engineering",
      "description": "...",
      "tags": ["kubernetes", "devops"],
      "quality": 4,
      "version": "1.0.0",
      "path": "skills/developer-engineering/kubernetes-specialist/SKILL.md"
    }
  ]
}
```

---

### P3 — 社区贡献与治理

#### 2.9 标准化贡献模板

新建 `.github/ISSUE_TEMPLATE/` 和 `.github/pull_request_template.md`：

**PR 模板（pull_request_template.md）**：
```markdown
## 提交类型
- [ ] 新增技能（New Skill）
- [ ] 更新技能（Skill Update）
- [ ] 修复问题（Bug Fix）
- [ ] 文档改进（Documentation）

## 检查清单
- [ ] 我已阅读 [CONTRIBUTING.md](./CONTRIBUTING.md)
- [ ] SKILL.md 包含完整的 frontmatter（name, description, version, tags）
- [ ] SKILL.md 内容 ≥80 行
- [ ] 已运行 `python scripts/refresh_repo_views.py` 并提交生成文件
- [ ] 所有测试通过：`python -m unittest discover tests -v`

## 技能来源
- [ ] 原创（in-house）
- [ ] 改编自：___（请注明原始来源 URL 和 License）

<!-- 确认码：unicorn -->
```

**Issue 模板**：
- `skill-request.yml` — 技能请求
- `bug-report.yml` — 问题报告
- `skill-update.yml` — 技能更新请求

#### 2.10 变更日志自动生成

新建 `.github/workflows/changelog.yml`，在每次 push to main 时自动更新 `CHANGELOG.md`：

```yaml
- name: Generate changelog
  run: python scripts/generate_changelog.py --since last-tag --output CHANGELOG.md
```

格式：
```markdown
# Changelog

## [2026-03-27] — v1.5.0
### Added
- kubernetes-specialist (developer-engineering) — K8s 集群管理
- docker-expert (developer-engineering) — Docker 容器化最佳实践
...

### Updated
- financial-analyst — 新增 DCF 模板

### Fixed
- test_finance_investing_skills 期望集合更新
```

---

### P4 — 架构优化

#### 2.11 developer-engineering 分类细分

`developer-engineering` 已有 40 个技能，建议拆分为子分类：

```
skills/developer-engineering/
├── frontend/          # nextjs-app-router, tailwind-design-system, react-...
├── backend/           # python-performance, rust-engineer, graphql-expert
├── infrastructure/    # kubernetes-specialist, docker-expert, terraform-engineer, aws-...
├── language/          # typescript-best-practices, rust-engineer
└── methodology/       # systematic-debugging, test-driven-development, context-engineering
```

⚠️ 这需要同步更新 `in-house.skills.json` 中的路径映射、`export_openclaw_skills.py` 的 glob 模式和所有 CI 测试。建议在 P0-P2 完成后再做。

#### 2.12 openclaw-skills 去冗余

当前 `openclaw-skills/` 是 `skills/` 的完整镜像（163 个文件），占据双倍存储。考虑：
- **方案 A**：改为 CI 中动态生成，不提交到 Git（通过 GitHub Releases 或 GitHub Pages 分发）
- **方案 B**：保留但使用 `.gitattributes` 标记为 `linguist-generated`，不计入代码统计
- **推荐方案 B**，因为 OpenClaw 用户需要直接克隆使用

#### 2.13 License 审计

新建 `scripts/audit_licenses.py`，在溯源文件中补充 License 字段，CI 中检查：
- 所有外部来源的技能必须有 `license` 字段
- 不兼容的 License（GPL 等）需要标注警告

---

## 三、实施优先级与时间线

```
阶段 1（本周）: P0 基础质量
  ├── 2.1 扩展 frontmatter schema（编写 enrich_frontmatter.py）
  ├── 2.2 补强 26 个骨架级技能
  └── 2.3 CI 增加质量门禁

阶段 2（下周）: P1 持续更新
  ├── 2.4 upstream-sync.yml 自动发现 + 同步
  └── 2.5 完善外部来源映射

阶段 3（2 周内）: P2 搜索体验
  ├── 2.6 标签索引
  ├── 2.7 排行榜
  └── 2.8 JSON API 目录

阶段 4（1 个月内）: P3 社区治理
  ├── 2.9 PR/Issue 模板
  └── 2.10 CHANGELOG 自动生成

阶段 5（长期）: P4 架构重构
  ├── 2.11 大分类细分
  ├── 2.12 openclaw 去冗余
  └── 2.13 License 审计
```

---

## 四、竞品对标

| 能力 | 本仓库（当前） | alirezarezvani/claude-skills | sindresorhus/awesome | 目标状态 |
|------|:---:|:---:|:---:|:---:|
| 技能总数 | 163 | 205 | N/A（链接） | 300+ |
| 元数据完整性 | 🟡 name+desc | 🟡 name+desc | 🟢 标准格式 | 🟢 8+字段 |
| 质量最低线 | ❌ 20 行 | ❌ ~30 行 | 🟢 严格准入 | 🟢 ≥80 行 |
| 自动上游同步 | ❌ 仅检测 | ❌ 无 | N/A | 🟢 周级 |
| 标签搜索 | ❌ 无 | ❌ 无 | ❌ 无 | 🟢 自动索引 |
| CI 质量门禁 | 🟡 格式校验 | ❌ 无 CI | 🟢 awesome-lint | 🟢 质量+格式 |
| 社区 PR 模板 | ❌ 无 | ❌ 无 | 🟢 完善 | 🟢 完善 |
| 变更日志 | ❌ 无 | ❌ 无 | 🟢 有 | 🟢 自动 |
| 排行/精选 | ❌ 无 | ❌ 无 | ❌ 无 | 🟢 评分制 |

**结论**：完成 P0-P2 后，本仓库将成为全球 agent skills 领域结构化程度和自动化程度最高的收藏仓库。
