# Commonly Used High-Value Skills

![Repository Banner](./.github/assets/repo-banner.svg)

[![简体中文](https://img.shields.io/badge/README-%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-1677ff)](./README.md)
[![English](https://img.shields.io/badge/README-English-111111)](./README.en.md)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Compatible-00b894)](./openclaw-skills/README.md)
[![Skills](https://img.shields.io/badge/Skills-309-7c3aed)](./skills/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

面向全球 AI 开发者与 Agent 工作流构建者的高价值 Skills 仓库，覆盖开发工程、DevOps、产品设计、运营、办公自动化、金融投资、AI 平台与安全治理等高频任务场景。当前共 **16 个分类 / 309 个技能**。

## 为什么值得收藏

- 一次收齐高频可复用 Skills，减少到处找 prompt、脚本和工作流的时间。
- 同时兼容 `Codex`、`Claude Code`、`Hermes Agent`、`OpenClaw` 等多种 AI 工具使用方式。
- 按场景分类组织，既适合日常检索，也适合二次扩展和团队沉淀。
- 很多技能不只是文档，还带 `scripts/`、`references/`、`assets/`，可以直接复用。
- 仓库已经具备发现新 Skill、同步上游更新、候选优选、质量校验和生成视图的自动化链路，适合持续运营而不是一次性收集。
- 现在支持用策略文件对白名单来源、黑名单来源、优先来源和基础门槛做统一治理，优选结果更稳定、更可控。
- 已提供 `scripts/sync_codex_skills.py`，可以把仓库中的最新技能一键同步到 `Codex`、`Claude Code` 等本机技能目录，减少手工拷贝和版本漂移。
- 除了功能覆盖，仓库也重视安全与可信度：既有来源追踪、候选筛选与安装前风险识别能力，也内置 `skill-vetter`、`skill-security-auditor`、`input-guard`、`link-checker` 等安全审查类技能。
- 现在还内置了许可证审计与月度死链巡检：`repo-validation` 会阻止缺失 license 元数据的外源技能进入主分支，`dead-links` 工作流会按月生成外链巡检报告。
- `Hermes Agent` 也被作为一等支持对象维护：可直接使用 `skills/` 分类目录，并且仓库已包含 `hermes-agent`、`native-mcp`、`hermes-graphify-gsd-*` 等 Hermes 生态专用技能。

## 适合谁

- AI 开发者、Agent 工作流构建者和自动化工具使用者
- 想把常见任务沉淀为 Skills 的个人或团队
- 正在使用 `Codex`、`Claude Code`、`Hermes Agent`、`OpenClaw` 等工具的工程师
- 想搭建一个自己的高价值技能库、提示库、Agent 工作流库的人

## 快速开始

### 我应该用哪个目录

| 使用场景 | 应使用的目录 |
|----------|---------------|
| 直接让 `Codex` / `Claude Code` / `Hermes Agent` / `Cursor` 等工具浏览仓库源码 | `skills/` |
| 安装到 `Codex` 本机技能目录 | 将 `skills/` 同步到 `~/.codex/skills` |
| 安装到 `Claude Code` 本机技能目录 | 将 `skills/` 同步到 `~/.claude/skills` 或项目内 `.claude/skills` |
| `OpenClaw` | `openclaw-skills/` |

### 方式一：直接发给 AI 工具的安装提示词（推荐）

如果你希望让 AI 工具直接帮你安装，优先发这段短提示词：

```
你现在是我的本地安装助手，请把这个仓库 https://github.com/seaworld008/Commonly-used-high-value-skills 里的 Skills 安装到当前 AI 工具中。
```

如果 AI 工具没有自动识别出来，再补一句即可：

```text
当前工具是 `<Codex / Claude Code / Hermes Agent / Cursor / OpenClaw>`，本地仓库路径是 `<你的本地仓库路径>`。
```

之所以可以这样简化，是因为仓库里已经包含给 AI 工具读取的安装规则与目录约定文档，通常不需要你手动把安装逻辑全部写进提示词里。

### 方式二：手动安装步骤

1. 克隆本仓库到本地并进入目录：

```bash
git clone https://github.com/seaworld008/Commonly-used-high-value-skills.git
cd Commonly-used-high-value-skills
```

2. 如果你使用 `Codex`，同步到本机 Codex skills 目录：

```bash
python3 scripts/sync_codex_skills.py --source-root ./skills --codex-root ~/.codex/skills
```

Windows PowerShell 示例：

```powershell
python scripts/sync_codex_skills.py --source-root ".\skills" --codex-root "$env:USERPROFILE\.codex\skills"
```

3. 如果你使用 `Claude Code`，同步到个人或项目级 skills 目录：

```bash
# 个人级，所有项目可用
python3 scripts/sync_codex_skills.py --source-root ./skills --codex-root ~/.claude/skills

# 项目级，只在当前项目可用
python3 scripts/sync_codex_skills.py --source-root ./skills --codex-root ./.claude/skills
```

Windows PowerShell 示例：

```powershell
python scripts/sync_codex_skills.py --source-root ".\skills" --codex-root "$env:USERPROFILE\.claude\skills"
```

这里的 `--codex-root` 是同步脚本沿用的参数名，实际含义是“目标技能目录”，也可以指向 `Claude Code` 的 skills 目录。

4. 如果你使用 `Hermes Agent`、`Cursor` 或其他能浏览源码目录的 AI coding assistant，优先把工具指向仓库内的 `skills/`；如果目标工具要求一层扁平技能目录，可以复用上面的同步命令，把 `--codex-root` 改成该工具自己的 skills 目录。

5. 如果你使用 `OpenClaw`，先生成扁平导出目录：

```bash
python3 scripts/export_openclaw_skills.py
```

然后把 `openclaw-skills/` 配置到 OpenClaw 的技能加载目录，不要把 OpenClaw 指向仓库根目录或 `skills/`。

6. 任选几个技能目录检查是否能正常读取，例如：
   - `skills/developer-engineering/codebase-onboarding`
   - `skills/security-and-reliability/skill-vetter`
   - `openclaw-skills/codebase-onboarding`

如果你希望按客户端直接看安装示例，可继续阅读：

- [按客户端安装示例](./docs/client-install-guides.md)
- [nlpm-audit 使用指南](./docs/nlpm-audit-usage.md)：说明安装到 `Codex` / `Claude Code` / `OpenClaw` 后如何自动触发、显式调用、生成 Markdown 审计报告和配置持续升级。

### 常见维护命令

如果你修改了仓库里的源码技能，推荐统一刷新生成视图：

```bash
python3 scripts/refresh_repo_views.py
```

如果你想在本地额外检查外源技能的许可证元数据与外链健康度，可以运行：

```bash
python3 scripts/audit_licenses.py
python3 scripts/check_dead_links.py --output docs/sources/reports/dead-links.json
```

首页 banner 的技能数量、分类数量和重点分类来自 `docs/catalog.json`，会在运行下面命令时自动同步刷新：

```bash
python3 scripts/build_catalog_json.py
```

如果你在本地 Codex skills 目录里看到 `invalid SKILL.md`、`missing YAML frontmatter`、`metadata` 类型错误等警告，可以运行：

```bash
python3 scripts/normalize_codex_skills.py ~/.codex/skills
```

Windows 示例：

```powershell
python scripts/normalize_codex_skills.py "C:\Users\admin\.codex\skills"
```

如果你想把仓库里的最新技能重新同步到本地 Codex 目录，可以运行：

```bash
python3 scripts/sync_codex_skills.py --source-root ./skills --codex-root ~/.codex/skills
```

## 分类快速跳转

| 分类 | 说明 | 文档跳转 | 目录 |
|------|------|----------|------|
| 开发工程 | 开发、测试、性能、代码审查、数据库与架构 | [跳转](#cat-developer-engineering) | [目录](./skills/developer-engineering/) |
| AI 工作流 | Agent 技能使用、规划、实现、评审、验证与发布闭环 | [跳转](#cat-ai-workflow) | [目录](./skills/ai-workflow/) |
| AI 平台与 Agent 开发 | ChatGPT Apps、Hermes、MCP、Figma、OpenAI Docs 与自主 Agent | [跳转](#cat-ai-agent-platform) | [目录](./skills/ai-agent-platform/) |
| 工程工作流自动化 | 浏览器自动化、GitHub、Notebook、Playwright、graphify/GSD | [跳转](#cat-workflow-automation) | [目录](./skills/engineering-workflow-automation/) |
| DevOps / SRE | 发布、监控、故障响应、CI/CD、环境管理 | [跳转](#cat-devops-sre) | [目录](./skills/devops-sre/) |
| 金融投资 | 金融数据、估值、风控、回测、投研写作 | [跳转](#cat-finance-investing) | [目录](./skills/finance-investing/) |
| 增长运营 | 小红书、社媒、内容、归因、竞品分析 | [跳转](#cat-growth-operations) | [目录](./skills/growth-operations-xiaohongshu/) |
| 办公与文档 | Word、Excel、PPT、PDF、会议纪要 | [跳转](#cat-office-white-collar) | [目录](./skills/office-white-collar/) |
| 项目管理与知识库集成 | Notion、Linear、Obsidian、飞书/Lark、规格到实施 | [跳转](#cat-knowledge-pm) | [目录](./skills/knowledge-and-pm-integrations/) |
| 通用运营 | 品牌、事实核查、内沟通、主题与天气 | [跳转](#cat-operations-general) | [目录](./skills/operations-general/) |
| 产品与设计 | 产品分析、设计系统、UX 研究、SaaS 脚手架 | [跳转](#cat-product-design) | [目录](./skills/product-design/) |
| 安全治理与稳定性 | Sentry、安全最佳实践、威胁建模、漏洞扫描 | [跳转](#cat-security-reliability) | [目录](./skills/security-and-reliability/) |
| 多模态内容 | 图像、语音、视频、截图、摘要、转写 | [跳转](#cat-multimodal-media) | [目录](./skills/multimodal-media/) |
| 部署平台 | Cloudflare、Netlify、Render、Vercel | [跳转](#cat-deployment-platforms) | [目录](./skills/deployment-platforms/) |
| 记忆与安全 | 长期记忆、输入防护、RAG、Runbook | [跳转](#cat-memory-safety) | [目录](./skills/openclaw-memory-and-safety/) |
| 任务理解与拆解 | 联网检索、复盘学习与任务理解补充能力 | [跳转](#cat-task-understanding) | [目录](./skills/task-understanding-decomposition/) |

## 从哪里开始最容易上手

如果你是第一次来到这个仓库，推荐从下面几类开始：

- 开发工程：`developer-engineering`
- AI 工作流：`ai-workflow`
- AI 平台与 Agent 开发：`ai-agent-platform`
- 工程工作流自动化：`engineering-workflow-automation`
- 金融投资：`finance-investing`
- 项目管理与知识库集成：`knowledge-and-pm-integrations`
- 多模态内容：`multimodal-media`
- 安全治理与稳定性：`security-and-reliability`

你也可以优先看这些代表性技能：

- `codebase-onboarding`：用于快速理解代码库结构、技术栈、关键模块和上手路径。
- `context-engineering`：用于设计上下文组织、提示结构和长任务信息管理方式。
- `agent-workflow-designer`：用于设计多步骤 Agent 工作流、角色分工和执行闭环。
- `gh-fix-ci`：用于定位 GitHub Actions 失败原因并修复 CI 流水线问题。
- `financial-data-collector`：用于收集股票、财报、市场和宏观金融数据。
- `notion-spec-to-implementation`：用于把 Notion 规格说明转化为可执行实现任务。
- `transcribe`：用于把音频或视频转写为文本，并整理说话人和时间信息。

## Hermes + graphify + GSD 使用说明

这组最新技能包现在包含 4 个相关技能，详细用法已放到对应分类 README 中，主 README 只保留入口：

- 全局非侵入式工作流：[`hermes-graphify-gsd-nonintrusive-workflow`](./skills/ai-agent-platform/README.md#hermes-graphify-gsd-global-workflow)
- 运行态排障与 operator：[`hermes-graphify-gsd-runtime-operator`](./skills/ai-agent-platform/README.md#hermes-graphify-gsd-runtime-operator)
- 项目接入工作流：[`hermes-graphify-gsd-project-integration`](./skills/engineering-workflow-automation/README.md#hermes-graphify-gsd-project-workflow)
- brownfield 启动流程：[`gsd-graphify-brownfield-bootstrap`](./skills/engineering-workflow-automation/README.md#gsd-graphify-brownfield-bootstrap)

## Hermes Agent 支持

这个仓库不只是“包含几个 Hermes 相关技能”，而是把 `Hermes Agent` 作为正式支持的消费端之一来维护：

- 源码浏览时统一使用 `skills/`；本机安装到 `Codex` / `Claude Code` 时同步到各自 skills 目录
- 已内置 [`hermes-agent`](./skills/ai-agent-platform/hermes-agent/) 技能，覆盖 CLI、gateway、profiles、memory、skills、MCP 与贡献开发说明
- 已内置 [`native-mcp`](./skills/ai-agent-platform/native-mcp/) 技能，方便 Hermes 连接外部 MCP server
- 已内置 `hermes-graphify-gsd-*` 系列技能，支持把 Hermes 与 graphify、GSD 组合成自动化开发工作流

如果你是 Hermes 用户，推荐从这些入口开始：

- [`skills/ai-agent-platform/hermes-agent`](./skills/ai-agent-platform/hermes-agent/)
- [`skills/ai-agent-platform/native-mcp`](./skills/ai-agent-platform/native-mcp/)
- [`skills/ai-agent-platform/README.md`](./skills/ai-agent-platform/README.md)
- [按客户端安装示例](./docs/client-install-guides.md)

## 如何参与共建

如果你希望把这个仓库一起做成更强的公共 Skills 基础设施：

- 阅读 [CONTRIBUTING.md](./CONTRIBUTING.md)
- 按 `skills/<分类>/<skill-name>/SKILL.md` 结构新增技能
- 修改后运行 `python3 scripts/refresh_repo_views.py`
- 提交 PR 时附上验证命令和适用场景

## 精选分类

- `developer-engineering`：开发、测试、性能、代码审查、数据库与架构
- `ai-workflow`：Agent 技能使用、规划、实现、评审、验证与发布闭环
- `ai-agent-platform`：ChatGPT Apps、Hermes、MCP、Figma、OpenAI Docs 与自主 Agent
- `engineering-workflow-automation`：浏览器自动化、GitHub、Notebook、Playwright、graphify/GSD
- `finance-investing`：金融数据、估值、风控、回测、投研写作
- `knowledge-and-pm-integrations`：Notion、Linear、Obsidian、飞书/Lark、规格到实施
- `multimodal-media`：图像、语音、视频、截图、摘要、转写
- `security-and-reliability`：Sentry、安全最佳实践、威胁建模、漏洞扫描

## 仓库定位

如果你想找的是：

- 可复用的 AI Skills 模板
- 面向真实工作的 Agent 工作流
- 多客户端兼容的 Skills 组织方式
- 一个可以持续扩展成“明星仓库”的 Skills 基础设施

这个仓库就是为这类目标准备的。

## 如果这个仓库对你有帮助

- 欢迎点一个 Star，让更多 AI 开发者更容易发现它
- 欢迎提 PR，把你自己的高价值技能沉淀进来
- 欢迎分享给使用 `Codex`、`Claude Code`、`Hermes Agent`、`OpenClaw` 的朋友或团队

## 仓库目标

- 沉淀高复用、可组合的技能模块（Skills）。
- 通过统一目录和文档结构，降低检索和使用成本。
- 让常见任务可以快速匹配到可执行的方法与模板。

## 多客户端兼容安装

这个仓库现在提供两套消费入口，用来兼容不同 AI 客户端的技能发现方式：

| 客户端 | 应使用的目录 | 原因 |
|--------|---------------|------|
| `Codex` / `Claude Code` 本机技能目录 | `~/.codex/skills` / `~/.claude/skills` / `.claude/skills` | 通过同步命令安装为一层技能目录，便于客户端发现 |
| `Hermes Agent` / `Cursor` / 其他按源码浏览的 coding assistants | `skills/` | 保留分类结构，便于检索、维护与编辑 |
| `OpenClaw` | `openclaw-skills/` | OpenClaw 需要扁平的一层技能目录，不能直接识别 `skills/<分类>/<skill>` |

### 给 AI 机器人看的规则

仓库根目录的 [AGENTS.md](./AGENTS.md) 明确约束如下：

- `OpenClaw` 安装时必须使用 `openclaw-skills/`
- `Codex`、`Claude Code` 本机安装时应同步到各自 skills 目录；源码浏览型工具可直接使用 `skills/`
- 不要把 `OpenClaw` 指向仓库根目录或 `skills/`
- `openclaw-skills/` 不手改，统一通过脚本生成

### OpenClaw 推荐接入方式

1. 克隆本仓库。
2. 生成或刷新 OpenClaw 兼容目录：

```bash
python3 scripts/export_openclaw_skills.py
```

3. 在 OpenClaw 配置里把克隆仓库的 `openclaw-skills/` 加到 `skills.load.extraDirs`。
4. 用下面命令确认是否已识别：

```bash
openclaw skills list
openclaw skills check
```

## 目录结构

```text
skills/
  developer-engineering/                # 开发工程
  ai-workflow/                          # AI 工作流（Agent Skills / 上下文工程 / 计划执行）
  ai-agent-platform/                    # AI 平台与 Agent 开发
  engineering-workflow-automation/      # 工程工作流自动化（GitHub/CI/测试）
  devops-sre/                           # DevOps / SRE
  finance-investing/                    # 金融投资与投研分析
  growth-operations-xiaohongshu/        # 增长运营（小红书/社媒）
  office-white-collar/                  # 办公与文档生产力
  knowledge-and-pm-integrations/        # 项目管理与知识库集成（Linear/Notion/Obsidian/飞书）
  operations-general/                   # 通用运营
  product-design/                       # 产品与设计
  security-and-reliability/             # 安全治理与稳定性
  multimodal-media/                     # 多模态内容（图像/语音/视频/转写）
  deployment-platforms/                 # 部署平台（Vercel/Netlify/Render/Cloudflare）
  openclaw-memory-and-safety/           # 记忆与安全
  task-understanding-decomposition/     # 任务理解与拆解
openclaw-skills/                        # 为 OpenClaw 生成的扁平兼容导出目录
```

## 使用方式

1. 按分类进入目标目录（如 `skills/developer-engineering/`）。
2. 打开对应技能的 `SKILL.md` 查看触发条件、操作流程和脚本说明。
3. 若技能下含 `scripts/`、`references/`、`assets/`，优先复用现成内容。

## 技能总览（按分类，16 类 / 309 技能）

<a id="cat-developer-engineering"></a>
### 1. 开发工程（developer-engineering，51）

- `agent-designer`：用于Agent、设计，支持开发、调试、评审和交付。
- `api-design-reviewer`：用于评审 API 设计的一致性、可用性、版本策略、错误语义、安全性和开发者体验。
- `api-test-suite-builder`：用于API、测试、套件、构建，支持开发、调试、评审和交付。
- `aws-solution-architect`：用于 AWS 云架构设计、服务选型、成本优化与 Well-Architected Framework 评估。
- `builder`：用于构建，支持开发、调试、评审和交付。
- `cli-demo-generator`：用于CLI、演示、生成，支持开发、调试、评审和交付。
- `code-review-excellence`：用于代码、评审、excellence，支持开发、调试、评审和交付。
- `codebase-inspection`：用于用 pygount 检查代码行数、语言构成、仓库规模和代码/注释比例。
- `codebase-onboarding`：用于代码库、onboarding，支持开发、调试、评审和交付。
- `database-designer`：用于数据库、设计，支持开发、调试、评审和交付。
- `database-schema-designer`：用于数据库、Schema、设计，支持开发、调试、评审和交付。
- `debugging-strategies`：用于调试、策略，支持开发、调试、评审和交付。
- `dependency-auditor`：用于dependency、审计，支持开发、调试、评审和交付。
- `docker-expert`：用于 Docker 容器化最佳实践、多阶段构建优化与 Docker Compose 编排。
- `frontend-design`：用于创建高质量、非模板化的前端页面、组件、仪表盘、海报和 Web UI。
- `gateway`：用于gateway，支持开发、调试、评审和交付。
- `git-worktree-manager`：用于Git、worktree、管理，支持开发、调试、评审和交付。
- `github-contributor`：用于GitHub、贡献，支持开发、调试、评审和交付。
- `graphify`：用于Graphify，支持开发、调试、评审和交付。
- `graphql-expert`：用于 GraphQL API 设计、Schema/Resolver 评审、查询优化和安全最佳实践。
- `i18n-expert`：用于i18n、expert，支持开发、调试、评审和交付。
- `kubernetes-specialist`：用于 Kubernetes 集群管理、Pod 调试、Helm Chart 设计、清单评审和部署优化。
- `mcp-builder`：用于MCP、构建，支持开发、调试、评审和交付。
- `mcp-server-builder`：用于MCP、服务器、构建，支持开发、调试、评审和交付。
- `migration-architect`：用于migration、架构，支持开发、调试、评审和交付。
- `monorepo-navigator`：用于Monorepo、导航，支持开发、调试、评审和交付。
- `neon-postgres`：用于 Neon Postgres 数据库连接、分支、迁移和运行维护。
- `neon-postgres-egress-optimizer`：诊断并降低 Neon / Postgres 数据出口流量与相关成本。
- `nextjs-app-router`：用于 Next.js App Router 项目开发、路由设计和服务端渲染实践。
- `parallel-debugging`：用于并行、调试，支持开发、调试、评审和交付。
- `performance-profiler`：用于性能、性能分析，支持开发、调试、评审和交付。
- `pr-review-expert`：用于PR、评审、expert，支持开发、调试、评审和交付。
- `promptfoo-evaluation`：用于promptfoo、评估，支持开发、调试、评审和交付。
- `python-performance`：用于 Python 性能分析、内存优化、热点路径调优和并发模式评审。
- `qa-expert`：用于质量保障、expert，支持开发、调试、评审和交付。
- `repomix-safe-mixer`：用于repomix、safe、mixer，支持开发、调试、评审和交付。
- `rust-engineer`：用于 Rust 代码开发、所有权和生命周期调试、异步模式选择和系统性能优化。
- `schema`：用于Schema，支持开发、调试、评审和交付。
- `skill-tester`：用于技能、tester，支持开发、调试、评审和交付。
- `supabase`：用于Supabase，支持开发、调试、评审和交付。
- `supabase-postgres`：用于 Supabase 平台开发与 PostgreSQL 最佳实践，包含 RLS、Edge Functions 和实。
- `supabase-postgres-best-practices`：用于编写、评审和优化 Supabase/Postgres 查询、Schema、索引和数据库配置。
- `systematic-debugging`：用于systematic、调试，支持开发、调试、评审和交付。
- `tailwind-design-system`：用于 Tailwind CSS 设计系统、主题 token、组件样式和响应式布局规范。
- `tech-debt-tracker`：用于tech、技术债、跟踪，支持开发、调试、评审和交付。
- `terraform-engineer`：用于 Terraform IaC 设计、模块评审、状态管理、Provider 升级和基础设施部署优化。
- `typescript-best-practices`：用于 TypeScript 类型安全设计、高级类型、API 边界、strict 迁移和反模式规避。
- `vercel-react-best-practices`：用于 Vercel/React 项目的架构、性能和部署最佳实践。
- `vercel-react-view-transitions`：用于在 React/Vercel 项目中实现和优化 View Transitions。
- `web-artifacts-builder`：用于构建复杂多组件 HTML/React 网页 artifacts，尤其适合需要状态、路由或 shadcn/ui 的场景。
- `webapp-testing`：用于使用 Playwright 测试本地 Web 应用、验证前端行为、截图和查看浏览器日志。

<a id="cat-ai-workflow"></a>
### 2. AI 工作流（ai-workflow，45）

- `agent-workflow-designer`：用于Agent、工作流、设计，支持任务规划、执行、评审和验证。
- `andrej-karpathy-skills`：用于应用 Andrej Karpathy 风格的 AI 学习、构建和研究实践。
- `api-and-interface-design`：用于API、interface、设计，支持任务规划、执行、评审和验证。
- `brainstorming`：用于brainstorming，支持任务规划、执行、评审和验证。
- `browser-testing-with-devtools`：用于通过浏览器 DevTools 测试、调试和验证前端行为。
- `ci-cd-and-automation`：用于CI、CD、自动化，支持任务规划、执行、评审和验证。
- `code-review-and-quality`：用于代码、评审、质量，支持任务规划、执行、评审和验证。
- `code-simplification`：用于代码、simplification，支持任务规划、执行、评审和验证。
- `context-engineering`：用于设计上下文工程策略、提示输入结构和长任务信息流。
- `debugging-and-error-recovery`：用于调试、错误、recovery，支持任务规划、执行、评审和验证。
- `deep-research`：用于执行深度研究、资料收集、来源核验和综合分析。
- `deprecation-and-migration`：用于deprecation、migration，支持任务规划、执行、评审和验证。
- `dispatching-parallel-agents`：用于拆分任务并调度多个 Agent 并行协作。
- `documentation-and-adrs`：用于documentation、adrs，支持任务规划、执行、评审和验证。
- `executing-plans`：用于按既定实现计划逐步执行任务，并在关键节点进行审查和完成验证。
- `find-skills`：用于搜索、比较并安装适合当前任务的技能，帮助 Agent 正确路由能力。
- `finishing-a-development-branch`：用于finishing、development、branch，支持任务规划、执行、评审和验证。
- `frontend-ui-engineering`：用于前端、UI、工程，支持任务规划、执行、评审和验证。
- `git-workflow-and-versioning`：用于Git、工作流、versioning，支持任务规划、执行、评审和验证。
- `idea-refine`：用于idea、refine，支持任务规划、执行、评审和验证。
- `incremental-implementation`：用于incremental、实现，支持任务规划、执行、评审和验证。
- `nexus`：用于nexus，支持任务规划、执行、评审和验证。
- `nlpm-audit`：审计 SKILL.md、AGENTS.md、CLAUDE.md、插件清单、hooks、commands 和提示词，检查安装一致性、质量评分、安全风险与版本漂移。
- `performance-optimization`：用于性能、优化，支持任务规划、执行、评审和验证。
- `planning-and-task-breakdown`：用于planning、任务、breakdown，支持任务规划、执行、评审和验证。
- `prompt-optimizer`：用于提示词、optimizer，支持任务规划、执行、评审和验证。
- `rally`：用于rally，支持任务规划、执行、评审和验证。
- `receiving-code-review`：用于receiving、代码、评审，支持任务规划、执行、评审和验证。
- `requesting-code-review`：用于在完成任务、实现重要功能或合并前请求代码审查并验证需求满足情况。
- `security-and-hardening`：用于安全、加固，支持任务规划、执行、评审和验证。
- `sherpa`：用于sherpa，支持任务规划、执行、评审和验证。
- `shipping-and-launch`：用于shipping、launch，支持任务规划、执行、评审和验证。
- `skill-creator`：用于技能、创建，支持任务规划、执行、评审和验证。
- `skill-reviewer`：用于技能、评审，支持任务规划、执行、评审和验证。
- `skills-search`：用于技能、搜索，支持任务规划、执行、评审和验证。
- `source-driven-development`：用于来源、驱动、development，支持任务规划、执行、评审和验证。
- `spec-driven-development`：用于spec、驱动、development，支持任务规划、执行、评审和验证。
- `subagent-driven-development`：用于subagent、驱动、development，支持任务规划、执行、评审和验证。
- `test-driven-development`：用于测试、驱动、development，支持任务规划、执行、评审和验证。
- `using-agent-skills`：用于选择、加载和正确使用 Agent Skills 完成任务。
- `using-git-worktrees`：用于使用 Git worktree 隔离并行开发和审查工作。
- `using-superpowers`：用于使用 Superpowers 工作流提升计划、执行和验证质量。
- `verification-before-completion`：用于verification、before、completion，支持任务规划、执行、评审和验证。
- `writing-plans`：用于writing、plans，支持任务规划、执行、评审和验证。
- `writing-skills`：用于writing、技能，支持任务规划、执行、评审和验证。

<a id="cat-ai-agent-platform"></a>
### 3. AI 平台与 Agent 开发（ai-agent-platform，16）

- `agent-hub`：用于管理 Agent 能力中心、技能发现、路由和协作工作流。
- `arena`：用于构建和运行 Agent 竞技场、评测对战和能力比较流程。
- `chatgpt-apps`：用于设计、构建和调试 ChatGPT Apps 与相关集成能力。
- `develop-web-game`：用于开发网页游戏原型、玩法循环、交互逻辑和前端实现。
- `figma`：用于处理 Figma 设计读取、解析、交付和实现协作。
- `figma-implement-design`：用于将 Figma 设计转化为可实现的前端界面和组件。
- `hermes-agent`：用于配置、扩展、调试和贡献 Hermes Agent，包括多 Agent、CLI 和网关工作流。
- `hermes-graphify-gsd-nonintrusive-workflow`：用于hermes、Graphify、gsd、nonintrusive、工作流，支持 Agent 平台编排、集成和运行管理。
- `hermes-graphify-gsd-runtime-operator`：用于hermes、Graphify、gsd、runtime、operator，支持 Agent 平台编排、集成和运行管理。
- `mcporter`：用于通过 mcporter CLI 列出、配置、鉴权和调用 MCP 服务器或工具。
- `native-mcp`：用于构建和调试原生 MCP 集成、服务器和工具调用流程。
- `openai-docs`：用于查阅和应用 OpenAI 官方文档、API 行为和集成指南。
- `oracle`：用于oracle，支持 Agent 平台编排、集成和运行管理。
- `proactive-agent`：用于让 Agent 主动规划、跟踪进展、暴露风险并提出下一步行动。
- `self-improving-agent`：用于构建具备记忆、反馈吸收和安全自我优化机制的持续改进型 Agent。
- `sigil`：用于sigil，支持 Agent 平台编排、集成和运行管理。

<a id="cat-workflow-automation"></a>
### 4. 工程工作流自动化（engineering-workflow-automation，16）

- `agent-browser`：用于让 Agent 操作真实浏览器，完成页面交互、截图录屏、脚本执行和端到端验证。
- `billing-automation`：用于构建订阅计费、自动开票、续费生命周期和催收管理流程。
- `changelog-automation`：用于基于提交、PR 和发布记录自动生成 Keep a Changelog 风格的变更日志。
- `gh-address-comments`：用于通过 gh CLI 处理当前分支的 GitHub PR Review 评论或 Issue 评论。
- `gh-fix-ci`：用于gh、修复、CI，支持工程协作、自动化验证和交付闭环。
- `github`：用于通过 GitHub CLI 自动化 Issue、PR、Review、CI 检查、标签和发布协作。
- `gsd-graphify-brownfield-bootstrap`：用于gsd、Graphify、brownfield、启动，支持工程协作、自动化验证和交付闭环。
- `guardian`：用于guardian，支持工程协作、自动化验证和交付闭环。
- `harvest`：用于harvest，支持工程协作、自动化验证和交付闭环。
- `hermes-graphify-gsd-project-integration`：用于hermes、Graphify、gsd、project、集成，支持工程协作、自动化验证和交付闭环。
- `jupyter-notebook`：用于Jupyter、Notebook，支持工程协作、自动化验证和交付闭环。
- `latch`：用于latch，支持工程协作、自动化验证和交付闭环。
- `playwright`：用于使用 Playwright 编写、运行和调试端到端测试。
- `playwright-pro`：用于高级 Playwright 测试、诊断、稳定性和浏览器自动化。
- `web-scraper`：用于网页抓取、结构化数据提取、爬取策略、选择器设计和反爬应对。
- `yeet`：用于yeet，支持工程协作、自动化验证和交付闭环。

<a id="cat-devops-sre"></a>
### 5. DevOps / SRE（devops-sre，15）

- `azure-kubernetes`：用于 Azure Kubernetes 集群管理、部署、排障和运维。
- `beacon`：用于beacon，支持部署、监控、排障和发布管理。
- `cc-devops-skills`：用于cc、DevOps、技能，支持部署、监控、排障和发布管理。
- `changelog-generator`：用于changelog、生成，支持部署、监控、排障和发布管理。
- `ci-cd-pipeline-builder`：用于CI、CD、流水线、构建，支持部署、监控、排障和发布管理。
- `cloudflare-troubleshooting`：用于Cloudflare、排障，支持部署、监控、排障和发布管理。
- `env-secrets-manager`：用于env、secrets、管理，支持部署、监控、排障和发布管理。
- `gear`：用于gear，支持部署、监控、排障和发布管理。
- `github-ops`：用于 GitHub 运维、仓库管理、PR/Issue 流程和自动化协作。
- `incident-commander`：用于事故响应中的分诊、角色分配、沟通协调、缓解跟踪和复盘。
- `observability-designer`：用于可观测性、设计，支持部署、监控、排障和发布管理。
- `release-manager`：用于发布、管理，支持部署、监控、排障和发布管理。
- `senior-architect`：用于高级、架构，支持部署、监控、排障和发布管理。
- `senior-devops`：用于高级、DevOps，支持部署、监控、排障和发布管理。
- `triage`：用于triage，支持部署、监控、排障和发布管理。

<a id="cat-finance-investing"></a>
### 6. 金融投资（finance-investing，16）

- `comps-valuation-analyst`：用于可比公司、估值、分析，支持投资研究、风险评估和报告生成。
- `earnings-call-analyzer`：用于摘要财报电话会、提取管理层语气变化、业绩指引措辞和投资者更新。
- `event-driven-tracker`：用于event、驱动、跟踪，支持投资研究、风险评估和报告生成。
- `factor-backtester`：用于factor、回测，支持投资研究、风险评估和报告生成。
- `financial-analyst`：用于金融、分析，支持投资研究、风险评估和报告生成。
- `financial-data-collector`：用于收集股票、财报、宏观和市场数据并生成分析输入。
- `helm`：用于helm，支持投资研究、风险评估和报告生成。
- `investment-memo-writer`：用于投资、memo、writer，支持投资研究、风险评估和报告生成。
- `ledger`：用于ledger，支持投资研究、风险评估和报告生成。
- `levy`：用于levy，支持投资研究、风险评估和报告生成。
- `macro-regime-monitor`：用于macro、regime、monitor，支持投资研究、风险评估和报告生成。
- `options-strategy-evaluator`：用于options、策略、评估，支持投资研究、风险评估和报告生成。
- `portfolio-risk-manager`：用于投资组合风险分析、仓位约束和风险报告生成。
- `saas-metrics-coach`：用于saas、metrics、教练，支持投资研究、风险评估和报告生成。
- `sec-filing-reviewer`：用于sec、申报文件、评审，支持投资研究、风险评估和报告生成。
- `stock-screener-builder`：用于stock、screener、构建，支持投资研究、风险评估和报告生成。

<a id="cat-growth-operations"></a>
### 7. 增长运营（growth-operations-xiaohongshu，16）

- `algorithmic-art`：用于algorithmic、art，支持内容、营销、渠道和数据分析。
- `app-store-optimization`：用于应用、store、优化，支持内容、营销、渠道和数据分析。
- `campaign-analytics`：用于活动、分析，支持内容、营销、渠道和数据分析。
- `compete`：用于compete，支持内容、营销、渠道和数据分析。
- `competitors-analysis`：Analyze competitor repositories with evidence-based approa。
- `content-creator`：用于内容、创建，支持内容、营销、渠道和数据分析。
- `growth`：用于增长，支持内容、营销、渠道和数据分析。
- `marketing-demand-acquisition`：用于营销、需求、acquisition，支持内容、营销、渠道和数据分析。
- `marketing-strategy-pmm`：用于营销、策略、PMM，支持内容、营销、渠道和数据分析。
- `prompt-engineer-toolkit`：用于提示词、工程、工具包，支持内容、营销、渠道和数据分析。
- `pulse`：用于pulse，支持内容、营销、渠道和数据分析。
- `seo-audit`：用于执行网站 SEO 审计、页面优化、技术检查和搜索增长建议。
- `social-media-analyzer`：用于社交、媒体、分析，支持内容、营销、渠道和数据分析。
- `tweetclaw-source-research`：用于tweetclaw、来源、研究，支持内容、营销、渠道和数据分析。
- `twitter-reader`：用于通过 URL 抓取 Twitter/X 帖子内容、作者、时间、图片和线程回复。
- `x-twitter-scraper`：用于抓取和分析 X/Twitter 公开内容、线程和增长信号。

<a id="cat-office-white-collar"></a>
### 8. 办公与文档（office-white-collar，20）

- `capture-screen`：用于捕获、screen，支持文档、表格、演示和资料整理。
- `doc`：用于读取、创建和编辑 `.docx` 文档，尤其适合需要格式和版面保真时。
- `doc-coauthoring`：用于文档、coauthoring，支持文档、表格、演示和资料整理。
- `docx`：用于创建、编辑和检查 Word `.docx` 文档。
- `excel-automation`：用于自动化 Excel 工作簿、公式、图表和数据处理。
- `gog`：用于跨 Gmail、Calendar、Drive、Docs 等 Google Workspace 工具执行办公自动化流程。
- `guizang-ppt-skill`：生成横向翻页网页 PPT（单 HTML 文件），含 WebGL 背景、章节幕封、数据大字报、图片网格等模板。
- `markdown-tools`：用于Markdown、tools，支持文档、表格、演示和资料整理。
- `meeting-minutes-taker`：用于会议、纪要、taker，支持文档、表格、演示和资料整理。
- `mermaid-tools`：用于mermaid、tools，支持文档、表格、演示和资料整理。
- `morph`：用于morph，支持文档、表格、演示和资料整理。
- `pdf`：用于pdf，支持文档、表格、演示和资料整理。
- `pdf-creator`：用于将 Markdown 转为支持中文字体和正式排版的 PDF 文档。
- `ppt-creator`：用于PPT、创建，支持文档、表格、演示和资料整理。
- `pptx`：用于创建、编辑和美化 PowerPoint 演示文稿。
- `prism`：用于prism，支持文档、表格、演示和资料整理。
- `spreadsheet`：用于处理电子表格数据、公式、清洗和分析。
- `stage`：用于stage，支持文档、表格、演示和资料整理。
- `transcript-fixer`：用于转录稿、fixer，支持文档、表格、演示和资料整理。
- `xlsx`：用于XLSX，支持文档、表格、演示和资料整理。

<a id="cat-knowledge-pm"></a>
### 9. 项目管理与知识库集成（knowledge-and-pm-integrations，36）

- `arxiv`：用于按关键词、作者、分类或编号检索 arXiv 论文。
- `grove`：用于grove，支持知识管理、项目同步和平台集成。
- `lark-approval`：用于查询、处理和发起飞书原生审批，区分审批待办与普通飞书任务。
- `lark-attendance`：用于查询飞书考勤记录、核对打卡缺失、整理异常考勤并生成可追溯说明。
- `lark-base`：用于操作飞书 Base 数据表、记录、字段和自动化数据流程。
- `lark-calendar`：用于查询、创建和管理飞书日历事件与日程安排。
- `lark-contact`：用于按姓名或邮箱解析飞书 open_id，并反查成员姓名、部门、邮箱和个人状态。
- `lark-doc`：用于读取、编辑和生成飞书云文档内容。
- `lark-drive`：用于搜索、读取和管理飞书云空间文件与权限。
- `lark-event`：用于lark、event，支持知识管理、项目同步和平台集成。
- `lark-im`：用于发送、读取和处理飞书即时消息与群聊交互。
- `lark-mail`：飞书邮箱：Use when user mentions 起草邮件、写邮件、草稿、发送/回复/转发邮件、查阅邮件、看邮。
- `lark-markdown`：飞书 Markdown：查看、创建、上传、编辑和比较 Markdown 文件。
- `lark-minutes`：飞书妙记：搜索妙记、查看妙记基础信息、下载/上传音视频、读取或编辑妙记的产物内容、改标题、替换说话人/关键词。
- `lark-okr`：飞书 OKR：管理目标与关键结果。
- `lark-openapi-explorer`：飞书/Lark 原生 OpenAPI 探索：从官方文档库中挖掘未经 CLI 封装的原生 OpenAPI 接口。
- `lark-shared`：用于lark、shared，支持知识管理、项目同步和平台集成。
- `lark-sheets`：用于读取、编辑和分析飞书电子表格数据。
- `lark-skill-maker`：用于把飞书 API 操作封装为可复用技能、流程模板和多步自动化。
- `lark-slides`：飞书幻灯片：创建和编辑幻灯片。
- `lark-task`：用于创建、查询和更新飞书任务及待办事项。
- `lark-vc`：飞书视频会议：搜索历史会议记录、查询会议纪要（总结/待办/章节/逐字稿）、查询参会人快照。
- `lark-vc-agent`：飞书视频会议会中能力：用于让应用机器人真实加入或离开正在进行的会议，并读取当前身份可见的会中事件，如参会人加入/离开。
- `lark-whiteboard`：用于查询、导出和编辑飞书云文档中的画板内容和节点结构。
- `lark-wiki`：飞书知识库：管理知识空间、空间成员和文档节点。
- `lark-workflow-meeting-summary`：用于汇总指定时间范围内的飞书会议纪要，并生成结构化会议报告或周报。
- `lark-workflow-standup-report`：日程待办摘要：编排 calendar +agenda 和 task +get-my-tasks，生成指定日期的日程与。
- `linear`：用于管理 Linear issue、项目、状态流转和工程协作。
- `llm-wiki`：用于构建、查询和维护 Karpathy 风格的互联 Markdown LLM 知识库。
- `lore`：用于lore，支持知识管理、项目同步和平台集成。
- `notion-knowledge-capture`：用于把对话、决策和笔记沉淀到 Notion。
- `notion-meeting-intelligence`：用于基于 Notion 上下文准备会议材料。
- `notion-research-documentation`：用于整合 Notion 信息并生成研究文档。
- `notion-spec-to-implementation`：用于将 Notion 规格文档转化为可执行实现计划。
- `obsidian`：用于读取、搜索、创建和编辑 Obsidian 知识库笔记，并维护 Markdown 结构和链接关系。
- `tome`：用于tome，支持知识管理、项目同步和平台集成。

<a id="cat-operations-general"></a>
### 10. 通用运营（operations-general，14）

- `brand-guidelines`：用于在文档、页面或视觉产物中应用 Anthropic 风格的品牌色、字体和视觉规范。
- `confidence-check`：用于结构化自检答案、验证假设、识别不确定性并降低幻觉风险。
- `crest`：用于crest，支持信息整理、沟通和执行管理。
- `dawn`：用于dawn，支持信息整理、沟通和执行管理。
- `docs-cleaner`：用于合并冗余文档、减少文档膨胀，并在保留有效内容的前提下整理知识库。
- `fact-checker`：用于事实、checker，支持信息整理、沟通和执行管理。
- `hearth`：用于hearth，支持信息整理、沟通和执行管理。
- `internal-comms`：用于撰写状态报告、领导层更新、FAQ、事故通报和项目进展等内部沟通材料。
- `interview-system-designer`：用于interview、系统、设计，支持信息整理、沟通和执行管理。
- `slack-gif-creator`：用于Slack、gif、创建，支持信息整理、沟通和执行管理。
- `supermemory`：用于长期记忆管理、偏好捕获、矛盾检测和项目状态跟踪。
- `teams-channel-post-writer`：用于teams、channel、post、writer，支持信息整理、沟通和执行管理。
- `theme-factory`：用于为幻灯片、文档、报告和网页应用预设主题或生成新的颜色字体系统。
- `weather`：用于免 API Key 查询当前天气、预报、恶劣天气和旅行天气信息。

<a id="cat-product-design"></a>
### 11. 产品与设计（product-design，14）

- `agile-product-owner`：用于agile、产品、负责人，支持产品研究、策略、界面和交付协作。
- `canvas-design`：用于画布、设计，支持产品研究、策略、界面和交付协作。
- `competitive-teardown`：用于竞品、teardown，支持产品研究、策略、界面和交付协作。
- `landing-page-generator`：用于落地页、page、生成，支持产品研究、策略、界面和交付协作。
- `product-analysis`：Multi-path parallel product analysis with cross-model test。
- `product-manager-toolkit`：用于产品、管理、工具包，支持产品研究、策略、界面和交付协作。
- `product-strategist`：用于产品、strategist，支持产品研究、策略、界面和交付协作。
- `researcher`：用于研究，支持产品研究、策略、界面和交付协作。
- `saas-scaffolder`：用于saas、scaffolder，支持产品研究、策略、界面和交付协作。
- `trace`：用于trace，支持产品研究、策略、界面和交付协作。
- `ui-design-system`：用于UI、设计、系统，支持产品研究、策略、界面和交付协作。
- `ui-ux-pro-max`：用于UI、UX、pro、max，支持产品研究、策略、界面和交付协作。
- `ux-researcher-designer`：用于UX、研究、设计，支持产品研究、策略、界面和交付协作。
- `voice`：用于voice，支持产品研究、策略、界面和交付协作。

<a id="cat-security-reliability"></a>
### 12. 安全治理与稳定性（security-and-reliability，21）

- `breach`：用于breach，支持安全扫描、审计、加固和风险治理。
- `cloak`：用于cloak，支持安全扫描、审计、加固和风险治理。
- `codeql-security-scanner`：用于通过 CodeQL 执行语义代码扫描、安全查询、自定义规则、SARIF 报告和 GitHub Code Scan。
- `comply`：用于comply，支持安全扫描、审计、加固和风险治理。
- `gha-security-review`：用于gha、安全、评审，支持安全扫描、审计、加固和风险治理。
- `grype-syft-sbom-scanner`：用于基于 SBOM 扫描容器、文件系统和软件包漏洞。
- `information-security-manager-iso27001`：用于information、安全、管理、iso27001，支持安全扫描、审计、加固和风险治理。
- `link-checker`：用于检测 URL 可达性、失效链接、跳转链路、可疑域名和文档链接健康度。
- `osv-scanner`：用于通过 OSV 数据库检查开源依赖、锁文件和 SBOM 漏洞。
- `security-auditor`：用于安全、审计，支持安全扫描、审计、加固和风险治理。
- `security-best-practices`：用于按语言或框架检查安全最佳实践，生成安全审查报告和 secure-by-default 建议。
- `security-ownership-map`：用于分析代码责任分布、敏感模块归属和人员风险。
- `security-pen-testing`：用于安全、pen、测试，支持安全扫描、审计、加固和风险治理。
- `security-review`：用于安全、评审，支持安全扫描、审计、加固和风险治理。
- `security-threat-model`：用于基于代码库或架构梳理资产、信任边界、攻击者能力、滥用路径和缓解措施。
- `semgrep-appsec-scanner`：用于 Semgrep SAST、规则编写、供应链和密钥扫描流程。
- `sentry`：用于查看线上异常、错误事件和服务健康信息。
- `skill-security-auditor`：用于技能、安全、审计，支持安全扫描、审计、加固和风险治理。
- `skill-vetter`：用于安装外部技能前审计指令、脚本、权限、依赖和来源风险。
- `trivy-vulnerability-scanner`：用于通过 Trivy 扫描仓库、容器镜像、文件系统、rootfs、SBOM、Kubernetes、IaC、密钥、许可。
- `vuls-linux-cve-scanner`：用于通过 Vuls 对 Linux、FreeBSD、容器、WordPress、库和网络设备执行 Agentless。

<a id="cat-multimodal-media"></a>
### 13. 多模态内容（multimodal-media，10）

- `clay`：用于clay，支持内容生成、编辑、分析和交付。
- `gpt-image2`：让 Codex 通过本地配置的 gpt-image-2 兼容画图服务生成图片，支持提示词、参考图、比例、清晰度和本地保存。
- `imagegen`：用于生成、编辑和迭代图像内容与视觉素材。
- `screenshot`：用于截图、屏幕捕获、视觉核查和界面证据收集。
- `sketch`：用于sketch，支持内容生成、编辑、分析和交付。
- `sora`：用于构思、生成和评审 Sora 视频或视频提示词。
- `speech`：用于语音，支持内容生成、编辑、分析和交付。
- `summarize`：用于忠实摘要网页、文档、邮件、转录稿或长文本，并提炼重点和后续行动。
- `tone`：用于tone，支持内容生成、编辑、分析和交付。
- `transcribe`：用于将音频或视频中的语音转写为文本，并可结合说话人分离和已知说话人提示。

<a id="cat-deployment-platforms"></a>
### 14. 部署平台（deployment-platforms，7）

- `cloudflare-deploy`：用于将应用部署到 Cloudflare 并处理相关发布流程。
- `netlify-deploy`：用于将网站或应用部署到 Netlify 并获取预览或生产链接。
- `pipe`：用于pipe，支持部署发布、配置、预览和故障处理。
- `render-deploy`：用于将服务或应用部署到 Render 并处理运行配置。
- `scaffold`：用于scaffold，支持部署发布、配置、预览和故障处理。
- `shard`：用于shard，支持部署发布、配置、预览和故障处理。
- `vercel-deploy`：用于将应用或网站部署到 Vercel，创建预览部署或生产发布链接。

<a id="cat-memory-safety"></a>
### 15. 记忆与安全（openclaw-memory-and-safety，7）

- `cast`：用于cast，支持记忆管理、安全防护和运行治理。
- `honcho`：用于管理 Agent 记忆、运行状态、协作上下文和安全边界。
- `input-guard`：用于输入安全检查、提示注入防护和高风险请求拦截。
- `omen`：用于omen，支持记忆管理、安全防护和运行治理。
- `rag-architect`：用于设计 RAG 架构、检索策略、索引和评估流程。
- `runbook-generator`：用于runbook、生成，支持记忆管理、安全防护和运行治理。
- `warden`：用于warden，支持记忆管理、安全防护和运行治理。

<a id="cat-task-understanding"></a>
### 16. 任务理解与拆解（task-understanding-decomposition，5）

- `lens`：用于lens，支持检索、拆解、反思和决策。
- `reflect-learn`：用于reflect、learn，支持检索、拆解、反思和决策。
- `ripple`：用于ripple，支持检索、拆解、反思和决策。
- `scout`：用于scout，支持检索、拆解、反思和决策。
- `tavily-search`：用于实时联网检索最新事实、来源证据、新闻市场信息和 Tavily 检索结果。

## 下一轮建议补充方向

以下方向适合作为下一批扩充候选；本轮已完成每类 3 个精选技能的补充，因此不再列已经落地的旧候选。

- 从 `VoltAgent/awesome-claude-skills` 中筛选行业类、数据类、科学研究类技能。
- 从 `kodustech/awesome-agent-skills` 中筛选命令开发、仓库治理和跨客户端兼容技能。
- 从官方平台文档中沉淀更细的部署、安全、办公自动化和多模态技能。
- 对功能重叠的技能增加使用频次、质量评分和最近同步时间后再做替换。

本轮详细筛选和替换判断见：[技能精选与升级报告](./docs/sources/reports/skill-curation-2026-04-25.md)。

## 快速检索命令

```bash
# 列出所有技能定义文件
rg --files skills | rg "SKILL.md$"

# 按关键词查找技能
rg -n "prompt|security|pdf|deploy" skills/**/SKILL.md
```

## 维护建议

- 新增技能时保持 `skills/<分类>/<skill-name>/SKILL.md` 结构。
- OpenClaw 兼容目录通过 `python3 scripts/export_openclaw_skills.py` 生成，不直接手工维护 `openclaw-skills/`。
- 若将候选技能正式落地，请同步更新正式分类列表、来源映射和总数统计。
- 每个技能应提供清晰触发条件、步骤、边界和验证方式。
- 优先复用 `scripts/` 与 `references/`，减少重复实现。
- 版本新鲜度校验建议采用“离线快照 + 本地比对”，避免逐个技能联网探测触发风控：

```bash
# 1) 快速生成 snapshot 模板（最小示例）
python3 scripts/skill_snapshot_template.py generate --output /tmp/clawhub_skills_snapshot.json

# 2) 用本仓库当前技能一键生成 snapshot（推荐）
python3 scripts/skill_snapshot_template.py generate --output /tmp/clawhub_skills_snapshot.json --from-local

# 3) 校验 snapshot 结构是否合法
python3 scripts/skill_snapshot_template.py validate --snapshot /tmp/clawhub_skills_snapshot.json

# 4) 再做离线新鲜度比对
python3 scripts/audit_skill_freshness.py --snapshot /tmp/clawhub_skills_snapshot.json
```

## 许可证

本仓库整体采用 [MIT License](./LICENSE)。其中外部导入的技能会保留各自上游许可证信息；新增外源技能必须通过 `scripts/audit_licenses.py` 校验。若高质量候选没有明确许可证，自动精选流程会生成原创 `in-house` MIT 重写版本并合入，但不会复制未知授权的上游正文。

---

本仓库维护中文与英文两份 README，面向全球开发者协作。文档更新应保持目录结构、技能数量、安装说明和自动化校验结果一致。
