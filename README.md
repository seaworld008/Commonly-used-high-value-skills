# Commonly Used High-Value Skills

![Repository Banner](./.github/assets/repo-banner.svg)

[![简体中文](https://img.shields.io/badge/README-%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-1677ff)](./README.md)
[![English](https://img.shields.io/badge/README-English-111111)](./README.en.md)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Compatible-00b894)](./openclaw-skills/README.md)
[![Skills](https://img.shields.io/badge/Skills-207-7c3aed)](./skills/)

面向中文 AI 开发者的高价值 Skills 仓库，覆盖开发工程、DevOps、产品设计、运营、办公自动化、金融投资、AI 平台与安全治理等高频任务场景。当前共 **16 个分类 / 207 个技能**。

## 为什么值得收藏

- 一次收齐高频可复用 Skills，减少到处找 prompt、脚本和工作流的时间。
- 同时兼容 `Codex`、`Claude Code`、`Hermes Agent`、`OpenClaw` 等多种 AI 工具使用方式。
- 按场景分类组织，既适合日常检索，也适合二次扩展和团队沉淀。
- 很多技能不只是文档，还带 `scripts/`、`references/`、`assets/`，可以直接复用。
- 仓库已经具备发现新 Skill、同步上游更新、候选优选、质量校验和生成视图的自动化链路，适合持续运营而不是一次性收集。
- 现在支持用策略文件对白名单来源、黑名单来源、优先来源和基础门槛做统一治理，优选结果更稳定、更可控。
- 已提供 `scripts/sync_codex_skills.py`，可以把仓库中的最新技能一键同步到本地 `Codex` 技能目录，减少手工拷贝和版本漂移。
- 除了功能覆盖，仓库也重视安全与可信度：既有来源追踪、候选筛选与安装前风险识别能力，也内置 `skill-vetter`、`skill-security-auditor`、`input-guard`、`link-checker` 等安全审查类技能。
- 现在还内置了许可证审计与月度死链巡检：`repo-validation` 会阻止缺失 license 元数据的外源技能进入主分支，`dead-links` 工作流会按月生成外链巡检报告。
- `Hermes Agent` 也被作为一等支持对象维护：可直接使用 `skills/` 分类目录，并且仓库已包含 `hermes-agent`、`native-mcp`、`hermes-graphify-gsd-*` 等 Hermes 生态专用技能。

## 适合谁

- 中文 AI 开发者和自动化工作流使用者
- 想把常见任务沉淀为 Skills 的个人或团队
- 正在使用 `Codex`、`Claude Code`、`Hermes Agent`、`OpenClaw` 等工具的工程师
- 想搭建一个自己的高价值技能库、提示库、Agent 工作流库的人

## 快速开始

### 我应该用哪个目录

| 使用场景 | 应使用的目录 |
|----------|---------------|
| `Codex` / `Claude Code` / `Hermes Agent` / 按源码浏览的 AI coding assistants | `skills/` |
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

1. 克隆本仓库到本地。
2. 判断你当前使用的是哪类工具：
   - 如果是 `Codex` / `Claude Code` / `Hermes Agent` / `Cursor` / 其他源码浏览型 AI coding assistant，直接使用 `skills/`
   - 如果是 `OpenClaw`，使用 `openclaw-skills/`
3. 如果你使用 `OpenClaw`，先生成扁平导出目录：

```bash
python3 scripts/export_openclaw_skills.py
```

4. 把对应目录配置到你的 AI 工具里：
   - `Codex` / `Claude Code` / `Hermes Agent` / `Cursor`：配置 `skills/`
   - `OpenClaw`：配置 `openclaw-skills/`
5. 任选几个技能目录检查是否能正常读取，例如：
   - `skills/developer-engineering/codebase-onboarding`
   - `skills/security-and-reliability/skill-vetter`
   - `openclaw-skills/codebase-onboarding`

如果你希望按客户端直接看安装示例，可继续阅读：

- [按客户端安装示例](./docs/client-install-guides.md)

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

如果你想把仓库里的最新技能同步到本地 Codex 目录，可以运行：

```powershell
python scripts/sync_codex_skills.py --source-root "E:\AI-codex\003-Commonly-used-high-value-skills\skills" --codex-root "C:\Users\admin\.codex\skills"
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
| 项目管理与知识库集成 | Notion、Linear、Obsidian、规格到实施 | [跳转](#cat-knowledge-pm) | [目录](./skills/knowledge-and-pm-integrations/) |
| 通用运营 | 品牌、事实核查、内沟通、主题与天气 | [跳转](#cat-operations-general) | [目录](./skills/operations-general/) |
| 产品与设计 | 产品分析、设计系统、UX 研究、SaaS 脚手架 | [跳转](#cat-product-design) | [目录](./skills/product-design/) |
| 安全治理与稳定性 | Sentry、安全最佳实践、威胁建模、所有权分析 | [跳转](#cat-security-reliability) | [目录](./skills/security-and-reliability/) |
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

- `codebase-onboarding`
- `context-engineering`
- `agent-workflow-designer`
- `gh-fix-ci`
- `financial-data-collector`
- `notion-spec-to-implementation`
- `transcribe`

## Hermes + graphify + GSD 使用说明

这组最新技能包现在包含 4 个相关技能，详细用法已放到对应分类 README 中，主 README 只保留入口：

- 全局非侵入式工作流：[`hermes-graphify-gsd-nonintrusive-workflow`](./skills/ai-agent-platform/README.md#hermes-graphify-gsd-global-workflow)
- 运行态排障与 operator：[`hermes-graphify-gsd-runtime-operator`](./skills/ai-agent-platform/README.md#hermes-graphify-gsd-runtime-operator)
- 项目接入工作流：[`hermes-graphify-gsd-project-integration`](./skills/engineering-workflow-automation/README.md#hermes-graphify-gsd-project-workflow)
- brownfield 启动流程：[`gsd-graphify-brownfield-bootstrap`](./skills/engineering-workflow-automation/README.md#gsd-graphify-brownfield-bootstrap)

## Hermes Agent 支持

这个仓库不只是“包含几个 Hermes 相关技能”，而是把 `Hermes Agent` 作为正式支持的消费端之一来维护：

- 安装目录与 `Codex` / `Claude Code` 一致，统一使用 `skills/`
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
- `knowledge-and-pm-integrations`：Notion、Linear、Obsidian、规格到实施
- `multimodal-media`：图像、语音、视频、截图、摘要、转写
- `security-and-reliability`：Sentry、安全最佳实践、威胁建模、所有权分析

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
| `Codex` / `Claude Code` / `Hermes Agent` / 其他按源码浏览的 coding assistants | `skills/` | 保留分类结构，便于检索、维护与编辑 |
| `OpenClaw` | `openclaw-skills/` | OpenClaw 需要扁平的一层技能目录，不能直接识别 `skills/<分类>/<skill>` |

### 给 AI 机器人看的规则

仓库根目录新增了 [AGENTS.md](/Volumes/soft/13-openclaw%20安装部署/5-Commonly-used-high-value-skills/Commonly-used-high-value-skills/AGENTS.md)，明确约束如下：

- `OpenClaw` 安装时必须使用 `openclaw-skills/`
- `Codex`、`Claude Code`、`Hermes Agent` 等按原方式使用 `skills/`
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
  knowledge-and-pm-integrations/        # 项目管理与知识库集成（Linear/Notion/Obsidian）
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

## 技能总览（按分类，16 类 / 207 技能）

<a id="cat-developer-engineering"></a>
### 1. 开发工程（developer-engineering，42）

- `agent-designer`：Tags: AI agents, architecture, system design, orchestration, multi-agent systems.
- `api-design-reviewer`：Maintainer: Claude Skills Team.
- `api-test-suite-builder`：Scans API route definitions across frameworks (Next.js App Router, Express, FastAPI, Django REST) and auto-generates comprehensive test suites...
- `aws-solution-architect`：用于 AWS 云架构设计、服务选型、成本优化与 Well-Architected Framework 评估。来源：alirezarezvani/claude-skills。
- `cli-demo-generator`：This skill should be used when users want to create animated CLI demos, terminal recordings, or command-line demonstration GIFs. It supports both...
- `code-review-excellence`：Master effective code review practices to provide constructive feedback, catch bugs early, and foster knowledge sharing while maintaining team...
- `codebase-inspection`：Inspect and analyze codebases using pygount for LOC counting, language breakdown, and code-vs-comment ratios. Use when asked to check lines of code...
- `codebase-onboarding`：Analyze a codebase and generate comprehensive onboarding documentation tailored to your audience. Produces architecture overviews, key file maps...
- `database-designer`：A comprehensive database design skill that provides expert-level analysis, optimization, and migration capabilities for modern database systems. This...
- `database-schema-designer`：Design relational database schemas from requirements and generate migrations, TypeScript/Python types, seed data, RLS policies, and indexes. Handles...
- `debugging-strategies`：Master systematic debugging techniques, profiling tools, and root cause analysis to efficiently track down bugs across any codebase or technology...
- `dependency-auditor`：> Skill Type: POWERFUL > Category: Engineering > Domain: Dependency Management & Security.
- `docker-expert`：用于 Docker 容器化最佳实践、多阶段构建优化与 Docker Compose 编排。来源：skills.sh 8.7K installs。
- `frontend-design`：Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages...
- `git-worktree-manager`：The Git Worktree Manager skill provides systematic management of Git worktrees for parallel development workflows. It handles worktree creation with...
- `github-contributor`：Strategic guide for becoming an effective GitHub contributor. Covers opportunity discovery, project selection, high-quality PR creation, and...
- `graphify`：any input (code, docs, papers, images, video/audio) -> knowledge graph -> clustered communities -> HTML + JSON + audit report
- `graphql-expert`：用于 GraphQL API 设计、查询优化、Schema 管理和安全最佳实践。仓库整理版，吸收社区高频最佳实践。
- `i18n-expert`：This skill should be used when setting up, auditing, or enforcing internationalization/localization in UI codebases (React/TS, i18next or similar...
- `kubernetes-specialist`：用于 Kubernetes 集群管理、部署编排、Pod 调试与 Helm Chart 设计。来源：skills.sh 5K+ installs。
- `mcp-builder`：Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools...
- `mcp-server-builder`：Design and implement Model Context Protocol (MCP) servers that expose any REST API, database, or service as structured tools for Claude and other...
- `migration-architect`：Purpose: Zero-downtime migration planning, compatibility validation, and rollback strategy generation.
- `monorepo-navigator`：Navigate, manage, and optimize monorepos. Covers Turborepo, Nx, pnpm workspaces, and Lerna. Enables cross-package impact analysis, selective...
- `nextjs-app-router`：用于 Next.js App Router 模式开发，包含 RSC、Server Actions 和路由最佳实践。来源：skills.sh 10.2K installs。
- `parallel-debugging`：Debug complex issues using competing hypotheses with parallel investigation, evidence collection, and root cause arbitration. Use this skill when...
- `performance-profiler`：Systematic performance profiling for Node.js, Python, and Go applications. Identifies CPU, memory, and I/O bottlenecks; generates flamegraphs...
- `pr-review-expert`：Structured, systematic code review for GitHub PRs and GitLab MRs. Goes beyond style nits — this skill performs blast radius analysis, security...
- `promptfoo-evaluation`：Configures and runs LLM evaluation using Promptfoo framework. Use when setting up prompt testing, creating evaluation configs (promptfooconfig.yaml)...
- `python-performance`：用于 Python 性能优化、内存分析和并发编程最佳实践。来源：skills.sh 12.8K installs。
- `qa-expert`：This skill should be used when establishing comprehensive QA testing processes for any software project. Use when creating test strategies, writing...
- `repomix-safe-mixer`：Safely package codebases with repomix by automatically detecting and removing hardcoded credentials before packing. Use when packaging code for...
- `rust-engineer`：用于 Rust 语言开发最佳实践、异步编程和系统级编程指导。来源：skills.sh 1.5K+ installs。
- `skill-tester`：Name: skill-tester Tier: POWERFUL Category: Engineering Quality Assurance Dependencies: None (Python Standard Library Only) Author: Claude Skills...
- `supabase-postgres`：用于 Supabase 平台开发与 PostgreSQL 最佳实践，包含 RLS、Edge Functions 和实时订阅。来源：supabase 官方 52.5K installs。
- `systematic-debugging`：Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
- `tailwind-design-system`：用于 Tailwind CSS 设计系统搭建、组件库开发与主题定制。来源：skills.sh 24.7K installs。
- `tech-debt-tracker`：Tier: POWERFUL 🔥 Category: Engineering Process Automation Expertise: Code Quality, Technical Debt Management, Software Engineering.
- `terraform-engineer`：用于 Terraform 基础设施即代码（IaC）设计、模块化管理和状态管理。来源：HashiCorp 官方 + skills.sh。
- `typescript-best-practices`：用于 TypeScript 高级类型编程、类型安全设计和常见反模式避免。仓库整理版，吸收社区高频最佳实践。
- `web-artifacts-builder`：Suite of tools for creating elaborate, multi-component claude.ai HTML artifacts using modern frontend web technologies (React, Tailwind CSS...
- `webapp-testing`：Toolkit for interacting with and testing local web applications using Playwright. Supports verifying frontend functionality, debugging UI behavior...

<a id="cat-ai-workflow"></a>
### 2. AI 工作流（ai-workflow，40）

- `agent-workflow-designer`：Design production-grade multi-agent orchestration systems. Covers five core patterns (sequential pipeline, parallel fan-out/fan-in, hierarchical...
- `api-and-interface-design`：Guides stable API and interface design. Use when designing APIs, module boundaries, or any public interface. Use when creating REST or GraphQL...
- `brainstorming`：You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user...
- `browser-testing-with-devtools`：Tests in real browsers. Use when building or debugging anything that runs in a browser. Use when you need to inspect the DOM, capture console errors...
- `ci-cd-and-automation`：Automates CI/CD pipeline setup. Use when setting up or modifying build and deployment pipelines. Use when you need to automate quality gates...
- `code-review-and-quality`：Conducts multi-axis code review. Use before merging any change. Use when reviewing code written by yourself, another agent, or a human. Use when you...
- `code-simplification`：Simplifies code for clarity. Use when refactoring code for clarity without changing behavior. Use when code works but is harder to read, maintain, or...
- `context-engineering`：Optimizes agent context setup. Use when starting a new session, when agent output quality degrades, when switching between tasks, or when you need to...
- `debugging-and-error-recovery`：Guides systematic root-cause debugging. Use when tests fail, builds break, behavior doesn''t match expectations, or you encounter any unexpected...
- `deep-research`：Generate format-controlled research reports with evidence tracking, citations, and iterative review. This skill should be used when users request a...
- `deprecation-and-migration`：Manages deprecation and migration. Use when removing old systems, APIs, or features. Use when migrating users from one implementation to another. Use...
- `dispatching-parallel-agents`：Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies
- `documentation-and-adrs`：Records decisions and documentation. Use when making architectural decisions, changing public APIs, shipping features, or when you need to record...
- `executing-plans`：Use when you have a written implementation plan to execute in a separate session with review checkpoints
- `find-skills`：让 Agent 自动搜索并安装合适技能，解决不知道该用哪个技能的问题。
- `finishing-a-development-branch`：Use when implementation is complete, all tests pass, and you need to decide how to integrate the work - guides completion of development work by...
- `frontend-ui-engineering`：Builds production-quality UIs. Use when building or modifying user-facing interfaces. Use when creating components, implementing layouts, managing...
- `git-workflow-and-versioning`：Structures git workflow practices. Use when making any code change. Use when committing, branching, resolving conflicts, or when you need to organize...
- `idea-refine`：Refines ideas iteratively. Refine ideas through structured divergent and convergent thinking. Use \"idea-refine\" or \"ideate\" to trigger.
- `incremental-implementation`：Delivers changes incrementally. Use when implementing any feature or change that touches more than one file. Use when you''re about to write a large...
- `performance-optimization`：Optimizes application performance. Use when performance requirements exist, when you suspect performance regressions, or when Core Web Vitals or load...
- `planning-and-task-breakdown`：Breaks work into ordered tasks. Use when you have a spec or clear requirements and need to break work into implementable tasks. Use when a task feels...
- `prompt-optimizer`：Transform vague prompts into precise, well-structured specifications using EARS (Easy Approach to Requirements Syntax) methodology. This skill should...
- `receiving-code-review`：Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - requires...
- `requesting-code-review`：Use when completing tasks, implementing major features, or before merging to verify work meets requirements
- `security-and-hardening`：Hardens code against vulnerabilities. Use when handling user input, authentication, data storage, or external integrations. Use when building any...
- `shipping-and-launch`：Prepares production launches. Use when preparing to deploy to production. Use when you need a pre-launch checklist, when setting up monitoring, when...
- `skill-creator`：Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, update or...
- `skill-reviewer`：Reviews and improves Claude Code skills against official best practices. Supports three modes - self-review (validate your own skills), external...
- `skills-search`：This skill should be used when users want to search, discover, install, or manage Claude Code skills from the CCPM registry. Triggers include...
- `source-driven-development`：Grounds every implementation decision in official documentation. Use when you want authoritative, source-cited code free from outdated patterns. Use...
- `spec-driven-development`：Creates specs before coding. Use when starting a new project, feature, or significant change and no specification exists yet. Use when requirements...
- `subagent-driven-development`：Use when executing implementation plans with independent tasks in the current session
- `test-driven-development`：Drives development with tests. Use when implementing any logic, fixing any bug, or changing any behavior. Use when you need to prove that code works...
- `using-agent-skills`：Discovers and invokes agent skills. Use when starting a session or when you need to discover which skill applies to the current task. This is the...
- `using-git-worktrees`：Use when starting feature work that needs isolation from current workspace or before executing implementation plans - creates isolated git worktrees...
- `using-superpowers`：Use when starting any conversation - establishes how to find and use skills, requiring Skill tool invocation before ANY response including clarifying...
- `verification-before-completion`：Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and...
- `writing-plans`：Use when you have a spec or requirements for a multi-step task, before touching code
- `writing-skills`：Use when creating new skills, editing existing skills, or verifying skills work before deployment

<a id="cat-ai-agent-platform"></a>
### 3. AI 平台与 Agent 开发（ai-agent-platform，13）

- `agent-hub`：Multi-agent collaboration plugin that spawns N parallel subagents competing on the same task via git worktree isolation. Agents work independently...
- `chatgpt-apps`：Build, scaffold, refactor, and troubleshoot ChatGPT Apps SDK applications that combine an MCP server and widget UI. Use when Codex needs to design...
- `develop-web-game`：Use when Codex is building or iterating on a web game (HTML/JS) and needs a reliable development + testing loop: implement small changes, run a...
- `figma`：Use the Figma MCP server to fetch design context, screenshots, variables, and assets from Figma, and to translate Figma nodes into production code...
- `figma-implement-design`：Translate Figma nodes into production-ready code with 1:1 visual fidelity using the Figma MCP workflow (design context, screenshots, assets, and...
- `hermes-agent`：Complete guide to using and extending Hermes Agent — CLI usage, setup, configuration, spawning additional agents, gateway platforms, skills, voice...
- `hermes-graphify-gsd-nonintrusive-workflow`：Use when integrating Hermes Agent, graphify, and GSD into a local development workflow without modifying upstream repositories, especially when the...
- `hermes-graphify-gsd-runtime-operator`：Use when operating or debugging a repo-local Hermes + graphify + GSD autonomous runtime, especially when checking writer ownership, execution-surface...
- `mcporter`：Use the mcporter CLI to list, configure, auth, and call MCP servers/tools directly (HTTP or stdio), including ad-hoc servers, config edits, and...
- `native-mcp`：Built-in MCP (Model Context Protocol) client that connects to external MCP servers, discovers their tools, and registers them as native Hermes Agent...
- `openai-docs`：Use when the user asks how to build with OpenAI products or APIs and needs up-to-date official documentation with citations (for example: Codex...
- `proactive-agent`：增强 Agent 的主动规划与自我迭代能力，从被动执行升级为主动协作。
- `self-improving-agent`：带记忆与自我优化机制的 Agent 技能，能在迭代中持续改进行为。

<a id="cat-workflow-automation"></a>
### 4. 工程工作流自动化（engineering-workflow-automation，10）

- `agent-browser`：为 Agent 提供真实浏览器自动化能力，支持语义定位、表单交互、截图录屏、脚本执行与会话管理。
- `gh-address-comments`：Help address review/issue comments on the open GitHub PR for the current branch using gh CLI; verify gh auth first and prompt the user to...
- `gh-fix-ci`：Use when a user asks to debug or fix failing GitHub PR checks that run in GitHub Actions; use `gh` to inspect checks and logs, summarize failure...
- `github`：通过 GitHub CLI 自动化 Issue、PR、Review 与 CI 检查，适合工程协作闭环。
- `gsd-graphify-brownfield-bootstrap`：Bootstrap GSD + graphify for an existing brownfield repo when the project needs a single canonical workflow for local runtime setup, graph refresh...
- `hermes-graphify-gsd-project-integration`：Use when integrating Hermes Agent, graphify, and GSD into a specific repository, especially for adding project-local graph refresh scripts, AGENTS.md...
- `jupyter-notebook`：Use when the user asks to create, scaffold, or edit Jupyter notebooks (`.ipynb`) for experiments, explorations, or tutorials; prefer the bundled...
- `playwright`：Use when the task requires automating a real browser from the terminal (navigation, form filling, snapshots, screenshots, data extraction, UI-flow...
- `web-scraper`：用于网页数据抓取、结构化提取和反爬策略应对。仓库整理版，吸收社区高频最佳实践。
- `yeet`：Use only when the user explicitly asks to stage, commit, push, and open a GitHub pull request in one flow using the GitHub CLI (`gh`).

<a id="cat-devops-sre"></a>
### 5. DevOps / SRE（devops-sre，10）

- `changelog-generator`：Parse conventional commits, determine semantic version bumps, and generate structured changelogs in Keep a Changelog format. Supports monorepo...
- `ci-cd-pipeline-builder`：Analyzes your project stack and generates production-ready CI/CD pipeline configurations for GitHub Actions, GitLab CI, and Bitbucket Pipelines...
- `cloudflare-troubleshooting`：Investigate and resolve Cloudflare configuration issues using API-driven evidence gathering. Use when troubleshooting ERR_TOO_MANY_REDIRECTS, SSL...
- `env-secrets-manager`：Complete environment and secrets management workflow: .env file lifecycle across dev/staging/prod, .env.example auto-generation, required-var...
- `github-ops`：Provides comprehensive GitHub operations using gh CLI and GitHub API. Activates when working with pull requests, issues, repositories, workflows, or...
- `incident-commander`：Author: Claude Skills Team Version: 1.0.0 Last Updated: February 2026.
- `observability-designer`：Description: Design comprehensive observability strategies for production systems including SLI/SLO frameworks, alerting optimization, and dashboard...
- `release-manager`：The Release Manager skill provides comprehensive tools and knowledge for managing software releases end-to-end. From parsing conventional commits to...
- `senior-architect`：This skill should be used when the user asks to \"design system architecture\", \"evaluate microservices vs monolith\", \"create architecture...
- `senior-devops`：Comprehensive DevOps skill for CI/CD, infrastructure automation, containerization, and cloud platforms (AWS, GCP, Azure). Includes pipeline setup...

<a id="cat-finance-investing"></a>
### 6. 金融投资（finance-investing，13）

- `comps-valuation-analyst`：Use when valuing a public company with peer multiples, building comparable-company tables, or pressure-testing a valuation range with EV/EBITDA, P/E...
- `earnings-call-analyzer`：Use when summarizing earnings calls, extracting management tone changes, surfacing guidance language, or turning transcript snippets into an...
- `event-driven-tracker`：Use when tracking earnings, product launches, M&A, dividends, buybacks, unlocks, or other market-moving dates that need a prioritized event calendar.
- `factor-backtester`：Use when testing factor signals, running long-short spread backtests, checking hit rate and turnover, or sanity-checking whether a ranking signal...
- `financial-analyst`：Performs financial ratio analysis, DCF valuation, budget variance analysis, and rolling forecast construction for strategic decision-making
- `financial-data-collector`：Use when collecting financial data for a US public company, assembling DCF inputs, pulling market and filing facts, or grounding downstream analysis...
- `investment-memo-writer`：Use when turning research notes into an investment memo, writing a buy or sell thesis, or structuring catalysts, risks, and monitoring items for an...
- `macro-regime-monitor`：Use when tracking macro regime shifts, summarizing inflation, growth, spreads, and liquidity signals, or creating a house view before updating sector...
- `options-strategy-evaluator`：Use when evaluating an options structure, checking expiry payoff checkpoints, comparing premium outlay versus downside protection, or preparing a...
- `portfolio-risk-manager`：Use when reviewing portfolio exposures, checking concentration and beta risk, summarizing sector or region tilts, or preparing a risk note before...
- `saas-metrics-coach`：SaaS financial health advisor. Use when a user shares revenue or customer numbers, or mentions ARR, MRR, churn, LTV, CAC, NRR, or asks how their SaaS...
- `sec-filing-reviewer`：Use when reviewing SEC filings, extracting material risk disclosures, scanning 10-K or 10-Q sections, or building a follow-up checklist from filing...
- `stock-screener-builder`：Use when building a stock screen, filtering a universe by valuation, growth, quality, or momentum rules, or creating a repeatable shortlist for...

<a id="cat-growth-operations"></a>
### 7. 增长运营（growth-operations-xiaohongshu，11）

- `algorithmic-art`：Creating algorithmic art using p5.js with seeded randomness and interactive parameter exploration. Use this when users request creating art using...
- `app-store-optimization`：App Store Optimization toolkit for researching keywords, optimizing metadata, and tracking mobile app performance on Apple App Store and Google Play...
- `campaign-analytics`：Analyzes campaign performance with multi-touch attribution, funnel conversion, and ROI calculation for marketing optimization
- `competitors-analysis`：Analyze competitor repositories with evidence-based approach. Use when tracking competitors, creating competitor profiles, or generating competitive...
- `content-creator`：Create SEO-optimized marketing content with consistent brand voice. Includes brand voice analyzer, SEO optimizer, content frameworks, and social...
- `marketing-demand-acquisition`：Multi-channel demand generation, paid media optimization, SEO strategy, and partnership programs for Series A+ startups
- `marketing-strategy-pmm`：Product marketing skill for positioning, GTM strategy, competitive intelligence, and product launches. Covers April Dunford positioning, ICP...
- `prompt-engineer-toolkit`：Systematic prompt engineering from first principles. Build, test, version, and optimize prompts for any LLM task. Covers technique selection, a...
- `seo-audit`：用于网站 SEO 全面审计、On-page 优化建议和技术 SEO 检查清单生成。仓库整理版，吸收社区高频最佳实践。
- `social-media-analyzer`：Social media campaign analysis and performance tracking. Calculates engagement rates, ROI, and benchmarks across platforms. Use for analyzing social...
- `twitter-reader`：Fetch Twitter/X post content by URL using jina.ai API to bypass JavaScript restrictions. Use when Claude needs to retrieve tweet content including...

<a id="cat-office-white-collar"></a>
### 8. 办公与文档（office-white-collar，16）

- `capture-screen`：Programmatic screenshot capture on macOS. Find window IDs with Swift CGWindowListCopyWindowInfo, control application windows via AppleScript (zoom...
- `doc`：Use when the task involves reading, creating, or editing `.docx` documents, especially when formatting or layout fidelity matters; prefer...
- `doc-coauthoring`：Guide users through a structured workflow for co-authoring documentation. Use when user wants to write documentation, proposals, technical specs...
- `docx`：Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx files). Triggers include: any mention of ''Word...
- `excel-automation`：Create, parse, and control Excel files on macOS. Professional formatting with openpyxl, complex xlsm parsing with stdlib zipfile+xml for investment...
- `gog`：Google Workspace 自动化技能，统一处理 Gmail、Calendar、Drive 与 Docs 等办公流程。
- `markdown-tools`：Converts documents to markdown with multi-tool orchestration for best quality. Supports Quick Mode (fast, single tool) and Heavy Mode (best quality...
- `meeting-minutes-taker`：Transforms raw meeting transcripts into high-fidelity, structured meeting minutes with iterative review for completeness. This skill should be used...
- `mermaid-tools`：Extracts Mermaid diagrams from markdown files and generates high-quality PNG images using bundled scripts. Activates when working with Mermaid...
- `pdf`：Use this skill whenever the user wants to do anything with PDF files. This includes reading or extracting text/tables from PDFs, combining or merging...
- `pdf-creator`：Create PDF documents from markdown with proper Chinese font support using weasyprint. This skill should be used when converting markdown to PDF...
- `ppt-creator`：Create professional slide decks from topics or documents. Generates structured content with data-driven charts, speaker notes, and complete PPTX...
- `pptx`：Use this skill any time a .pptx file is involved in any way — as input, output, or both. This includes: creating slide decks, pitch decks, or...
- `spreadsheet`：Use when tasks involve creating, editing, analyzing, or formatting spreadsheets (`.xlsx`, `.csv`, `.tsv`) using Python (`openpyxl`, `pandas`)...
- `transcript-fixer`：Corrects speech-to-text transcription errors in meeting notes, lectures, and interviews using dictionary rules and AI. Learns patterns to build...
- `xlsx`：Use this skill any time a spreadsheet file is the primary input or output. This means any task where the user wants to: open, read, edit, or fix an...

<a id="cat-knowledge-pm"></a>
### 9. 项目管理与知识库集成（knowledge-and-pm-integrations，8）

- `arxiv`：Search and retrieve academic papers from arXiv using their free REST API. No API key needed. Search by keyword, author, category, or ID. Combine with...
- `linear`：Manage Linear issues, projects, and teams via the GraphQL API. Create, update, search, and organize issues. Uses API key auth (no OAuth needed). All...
- `llm-wiki`：Path to the LLM Wiki knowledge base directory
- `notion-knowledge-capture`：Capture conversations and decisions into structured Notion pages; use when turning chats/notes into wiki entries, how-tos, decisions, or FAQs with...
- `notion-meeting-intelligence`：Prepare meeting materials with Notion context and Codex research; use when gathering context, drafting agendas/pre-reads, and tailoring materials to...
- `notion-research-documentation`：Research across Notion and synthesize into structured documentation; use when gathering info from multiple Notion sources to produce briefs...
- `notion-spec-to-implementation`：Turn Notion specs into implementation plans, tasks, and progress tracking; use when implementing PRDs/feature specs and creating Notion plans + tasks...
- `obsidian`：Read, search, and create notes in the Obsidian vault.

<a id="cat-operations-general"></a>
### 10. 通用运营（operations-general，11）

- `brand-guidelines`：Applies Anthropic''s official brand colors and typography to any sort of artifact that may benefit from having Anthropic''s look-and-feel. Use it...
- `confidence-check`：用于结构化自我审查，验证假设、识别不确定性和减少幻觉输出。仓库整理版，吸收社区高频最佳实践。
- `docs-cleaner`：Consolidates redundant documentation while preserving all valuable content. This skill should be used when users want to clean up documentation...
- `fact-checker`：Verifies factual claims in documents using web search and official sources, then proposes corrections with user confirmation. Use when the user asks...
- `internal-comms`：A set of resources to help me write all kinds of internal communications, using the formats that my company likes to use. Claude should use this...
- `interview-system-designer`：This skill should be used when the user asks to "design interview processes", "create hiring pipelines", "calibrate interview loops", "generate...
- `slack-gif-creator`：Knowledge and utilities for creating animated GIFs optimized for Slack. Provides constraints, validation tools, and animation concepts. Use when...
- `supermemory`：用于长期记忆管理、偏好捕获、矛盾检测和项目状态跟踪。来源：supermemoryai/supermemory。
- `teams-channel-post-writer`：Creates educational Teams channel posts for internal knowledge sharing about Claude Code features, tools, and best practices. Applies when writing...
- `theme-factory`：Toolkit for styling artifacts with a theme. These artifacts can be slides, docs, reportings, HTML landing pages, etc. There are 10 pre-set themes...
- `weather`：免 API Key 的天气查询技能，支持多数据源与自然语言请求。

<a id="cat-product-design"></a>
### 11. 产品与设计（product-design，10）

- `agile-product-owner`：Agile product ownership for backlog management and sprint execution. Covers user story writing, acceptance criteria, sprint planning, and velocity...
- `canvas-design`：Create beautiful visual art in .png and .pdf documents using design philosophy. You should use this skill when the user asks to create a poster...
- `competitive-teardown`：Run a structured competitive analysis on any product or company. Synthesizes data from pricing pages, app store reviews, job postings, SEO signals...
- `landing-page-generator`：Generates high-converting landing pages as complete Next.js/React (TSX) components with Tailwind CSS. Creates hero sections, feature grids, pricing...
- `product-analysis`：Multi-path parallel product analysis with cross-model test-time compute scaling. Spawns parallel agents (Claude Code agent teams + Codex CLI) to...
- `product-manager-toolkit`：Comprehensive toolkit for product managers including RICE prioritization, customer interview analysis, PRD templates, discovery frameworks, and...
- `product-strategist`：Strategic product leadership toolkit for Head of Product including OKR cascade generation, market analysis, vision setting, and team scaling. Use for...
- `saas-scaffolder`：Generate complete, production-ready SaaS projects from a product brief. Outputs a fully wired Next.js App Router project with authentication...
- `ui-design-system`：UI design system toolkit for Senior UI Designer including design token generation, component documentation, responsive design calculations, and...
- `ux-researcher-designer`：UX research and design toolkit for Senior UX Designer/Researcher including data-driven persona generation, journey mapping, usability testing...

<a id="cat-security-reliability"></a>
### 12. 安全治理与稳定性（security-and-reliability，7）

- `link-checker`：检测 URL 可达性与潜在风险，识别失效链接、跳转链路和可疑域名。
- `security-best-practices`：Perform language and framework specific security best-practice reviews and suggest improvements. Trigger only when the user explicitly requests...
- `security-ownership-map`：Analyze git repositories to build a security ownership topology (people-to-file), compute bus factor and sensitive-code ownership, and export...
- `security-threat-model`：Repository-grounded threat modeling that enumerates trust boundaries, assets, attacker capabilities, abuse paths, and mitigations, and writes a...
- `sentry`：Use when the user asks to inspect Sentry issues or events, summarize recent production errors, or pull basic Sentry health data via the Sentry API...
- `skill-security-auditor`：Audit AI agent skills for security risks before installation, with PASS/WARN/FAIL findings and remediation guidance.
- `skill-vetter`：在安装前审计技能安全性，识别恶意指令、越权行为与高风险配置。

<a id="cat-multimodal-media"></a>
### 13. 多模态内容（multimodal-media，6）

- `imagegen`：Use when the user asks to generate or edit images via the OpenAI Image API (for example: generate image, edit/inpaint/mask, background removal or...
- `screenshot`：Use when the user explicitly asks for a desktop or system screenshot (full screen, specific app or window, or a pixel region), or when tool-specific...
- `sora`：Use when the user asks to generate, remix, poll, list, download, or delete Sora videos via OpenAI\u2019s video API using the bundled CLI...
- `speech`：Use when the user asks for text-to-speech narration or voiceover, accessibility reads, audio prompts, or batch speech generation via the OpenAI Audio...
- `summarize`：对网页、文档、邮件与长文本进行快速摘要，提炼核心信息。
- `transcribe`：Transcribe audio files to text with optional diarization and known-speaker hints. Use when a user asks to transcribe speech from audio/video, extract...

<a id="cat-deployment-platforms"></a>
### 14. 部署平台（deployment-platforms，4）

- `cloudflare-deploy`：Deploy applications and infrastructure to Cloudflare using Workers, Pages, and related platform services. Use when the user asks to deploy, host...
- `netlify-deploy`：Deploy web projects to Netlify using the Netlify CLI (`npx netlify`). Use when the user asks to deploy, host, publish, or link a site/repo on...
- `render-deploy`：Deploy applications to Render by analyzing codebases, generating render.yaml Blueprints, and providing Dashboard deeplinks. Use when the user wants...
- `vercel-deploy`：Deploy applications and websites to Vercel. Use when the user requests deployment actions like "deploy my app", "deploy and give me the link", "push...

<a id="cat-memory-safety"></a>
### 15. 记忆与安全（openclaw-memory-and-safety，4）

- `honcho`：Configure and use Honcho memory with Hermes -- cross-session user modeling, multi-profile peer isolation, observation config, dialectic reasoning...
- `input-guard`：Scan untrusted external text (web pages, tweets, search results, API responses) for prompt injection attacks. Returns severity levels and alerts on...
- `rag-architect`：The RAG (Retrieval-Augmented Generation) Architect skill provides comprehensive tools and knowledge for designing, implementing, and optimizing...
- `runbook-generator`：Analyze a codebase and generate production-grade operational runbooks. Detects your stack (CI/CD, database, hosting, containers), then produces...

<a id="cat-task-understanding"></a>
### 16. 任务理解与拆解（task-understanding-decomposition，2）

- `reflect-learn`：Self-improvement through conversation analysis. Extracts learnings from corrections and success patterns, proposes updates to agent files or creates...
- `tavily-search`：提供实时联网检索能力，帮助 Agent 获取最新资讯、数据与来源证据。

## 建议补充的高热度技能（候选）

以下技能是建议纳入下一批扩充的候选项，当前 **尚未** 在 `skills/` 目录中落地，因此 **不计入** 上方的 `16 类 / 207 技能` 统计。

如需继续扩充，建议下一批优先关注：

- `link-checker`（2.1K 下载）：建议归类到 `security-and-reliability`，用于 URL 安全检测、钓鱼链接识别与基础可达性检查。

### 工程工作流与协作（仍在候选）

- `github`（24.8K 下载）：建议归类到 `engineering-workflow-automation`，用于通过 GitHub CLI 管理 Issues、PRs 和 CI 运行；可与 `gh-address-comments`、`gh-fix-ci`、`yeet` 形成互补。

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
- 若将候选技能正式落地，请同步把对应条目从“建议补充的高热度技能（候选）”迁移到正式分类列表，并更新总数统计。
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

---

如果你希望，我可以在下一步继续补一版 `README.zh-CN.md`（面向中文）+ `README.en.md`（面向国际协作），并自动校验两份目录与技能数量一致。
