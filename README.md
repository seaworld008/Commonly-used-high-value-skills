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

- `agent-designer`：用于设计、拆分和评估多智能体协作系统。
- `api-design-reviewer`：用于审查接口设计、命名一致性、边界和可维护性。
- `api-test-suite-builder`：用于为接口服务生成自动化测试、覆盖异常和回归场景。
- `aws-solution-architect`：用于云架构设计、服务选型、成本优化和可靠性评估。
- `cli-demo-generator`：用于制作命令行演示流程、终端录制和交互示例。
- `code-review-excellence`：用于提升代码审查质量，发现缺陷并给出建设性反馈。
- `codebase-inspection`：用于统计代码规模、语言分布和注释比例，快速体检仓库。
- `codebase-onboarding`：用于快速理解陌生代码库结构、关键模块和上手路径。
- `database-designer`：用于数据库建模、索引规划、性能优化和迁移设计。
- `database-schema-designer`：用于根据需求设计表结构、字段关系、索引和种子数据。
- `debugging-strategies`：用于系统化定位问题、分析根因并制定修复路径。
- `dependency-auditor`：用于审计依赖版本、许可证风险和安全漏洞。
- `docker-expert`：用于容器化构建、镜像优化、多阶段构建和编排实践。
- `frontend-design`：用于设计和实现高质量前端界面，提升视觉与交互体验。
- `git-worktree-manager`：用于管理并行工作区，支持多分支隔离开发。
- `github-contributor`：用于规范开源贡献流程、议题选择、变更提交和协作沟通。
- `graphify`：用于把代码、文档和资料转成知识图谱并生成可视化报告。
- `graphql-expert`：用于图查询接口设计、模式治理、查询优化和安全审查。
- `i18n-expert`：用于国际化与本地化改造，处理多语言文案和格式适配。
- `kubernetes-specialist`：用于容器集群部署、服务编排、故障排查和包管理。
- `mcp-builder`：用于构建模型上下文协议工具，让模型安全调用外部服务。
- `mcp-server-builder`：用于设计和实现模型上下文协议服务端，封装数据和工具能力。
- `migration-architect`：用于规划低风险迁移、兼容验证、回滚策略和切换步骤。
- `monorepo-navigator`：用于浏览大型单仓库，分析包依赖和跨模块影响。
- `nextjs-app-router`：用于现代网页框架路由开发、服务端组件和表单动作实践。
- `parallel-debugging`：用于并行验证多个故障假设，加速复杂问题定位。
- `performance-profiler`：用于性能剖析、瓶颈定位、资源消耗分析和优化建议。
- `pr-review-expert`：用于系统化审查合并请求，评估影响面、风险和测试缺口。
- `promptfoo-evaluation`：用于配置提示词和模型输出评测，比较质量与稳定性。
- `python-performance`：用于脚本性能优化、内存分析、并发设计和热点定位。
- `qa-expert`：用于制定质量保障策略、测试计划、验收标准和回归流程。
- `repomix-safe-mixer`：用于安全打包仓库上下文，自动识别并排除敏感信息。
- `rust-engineer`：用于系统级编程、并发设计、错误处理和工程最佳实践。
- `skill-tester`：用于验证技能可用性、触发条件、输出质量和边界行为。
- `supabase-postgres`：用于后端数据库开发、权限策略、实时订阅和边缘函数实践。
- `systematic-debugging`：用于按证据推进调试，构建最小复现并确认根因。
- `tailwind-design-system`：用于搭建样式体系、组件规范、主题变量和视觉一致性。
- `tech-debt-tracker`：用于识别技术债、记录影响、排序治理并跟踪改善进度。
- `terraform-engineer`：用于基础设施即代码设计、模块化管理和状态治理。
- `typescript-best-practices`：用于类型安全设计、复杂类型建模和常见反模式避免。
- `web-artifacts-builder`：用于构建复杂网页制品、交互组件和可复用前端成果。
- `webapp-testing`：用于测试本地网页应用，验证交互、页面状态和回归问题。

<a id="cat-ai-workflow"></a>
### 2. AI 工作流（ai-workflow，40）

- `agent-workflow-designer`：用于设计智能体协作流程、角色分工和执行顺序。
- `api-and-interface-design`：用于设计稳定接口、模块边界和公共调用约定。
- `brainstorming`：用于需求澄清、方案发散、创意筛选和行动前思考。
- `browser-testing-with-devtools`：用于真实浏览器调试页面、检查元素、网络和控制台问题。
- `ci-cd-and-automation`：用于搭建持续集成与持续交付流程，自动化构建和发布。
- `code-review-and-quality`：用于多维度审查代码质量、正确性、风险和测试覆盖。
- `code-simplification`：用于在不改变行为的前提下简化代码结构和表达。
- `context-engineering`：用于优化智能体上下文、任务说明、资料组织和指令边界。
- `debugging-and-error-recovery`：用于构建系统化排错流程，恢复失败构建和异常行为。
- `deep-research`：用于深度研究主题、整理证据、引用来源并形成报告。
- `deprecation-and-migration`：用于下线旧能力、迁移用户路径并控制兼容风险。
- `dispatching-parallel-agents`：用于把独立任务分派给多个智能体并行推进。
- `documentation-and-adrs`：用于记录技术决策、架构说明、变更背景和文档规范。
- `executing-plans`：用于按既定实施计划执行任务，并在关键节点复核。
- `find-skills`：用于自动搜索并安装适合当前任务的技能。
- `finishing-a-development-branch`：用于开发完成后的收尾、验证、提交和合并准备。
- `frontend-ui-engineering`：用于构建面向用户的界面、组件、状态和响应式布局。
- `git-workflow-and-versioning`：用于规范分支、提交、版本、冲突处理和变更记录。
- `idea-refine`：用于把初步想法打磨成清晰目标、约束和可执行方案。
- `incremental-implementation`：用于把大任务拆成小步交付，逐步验证并降低风险。
- `performance-optimization`：用于分析性能瓶颈、制定优化方案并验证改善效果。
- `planning-and-task-breakdown`：用于把目标拆解为任务、依赖、里程碑和验收标准。
- `prompt-optimizer`：用于优化提示词结构、上下文、约束和输出稳定性。
- `receiving-code-review`：用于处理代码审查反馈，判断优先级并逐项修复。
- `requesting-code-review`：用于准备高质量代码审查请求，说明背景、风险和验证方式。
- `security-and-hardening`：用于加固代码、配置和运行环境，减少安全风险。
- `shipping-and-launch`：用于发布前检查、上线计划、回滚准备和交付沟通。
- `skill-creator`：用于创建新技能，定义触发条件、流程、边界和验证方法。
- `skill-reviewer`：用于审查技能质量、实用性、安全性和可维护性。
- `skills-search`：用于快速检索技能库，匹配当前任务所需能力。
- `source-driven-development`：用于从权威来源和现有代码出发推进实现。
- `spec-driven-development`：用于根据规格说明驱动开发、测试和验收。
- `subagent-driven-development`：用于组织多个子智能体协作开发、审查和整合结果。
- `test-driven-development`：用于按先写测试、再实现、再重构的节奏开发。
- `using-agent-skills`：用于指导智能体正确选择、组合和执行技能。
- `using-git-worktrees`：用于使用多个工作区并行处理不同任务。
- `using-superpowers`：用于调用增强型技能流程，提升任务执行质量。
- `verification-before-completion`：用于完成前复核结果、证据、测试和交付标准。
- `writing-plans`：用于编写清晰、可执行、可验证的实施计划。
- `writing-skills`：用于编写结构完整、触发清楚、可复用的技能文档。

<a id="cat-ai-agent-platform"></a>
### 3. AI 平台与 Agent 开发（ai-agent-platform，13）

- `agent-hub`：用于编排多个智能体并行尝试方案，比较结果并选择最佳分支。
- `chatgpt-apps`：用于构建、调试和发布聊天应用能力。
- `develop-web-game`：用于快速开发网页游戏、验证玩法并迭代体验。
- `figma`：用于读取设计稿上下文、提取视觉信息和资源。
- `figma-implement-design`：用于把设计稿高保真转化为可生产的前端代码。
- `hermes-agent`：用于配置和使用智能体运行时、资料、记忆和扩展能力。
- `hermes-graphify-gsd-nonintrusive-workflow`：用于全局非侵入式智能工作流，连接图谱分析和开发流程。
- `hermes-graphify-gsd-runtime-operator`：用于运行态排障、状态观察和智能体操作管理。
- `mcporter`：用于迁移和适配模型上下文协议工具与服务。
- `native-mcp`：用于配置原生模型上下文协议连接和工具调用。
- `openai-docs`：用于查询官方文档并据此实现相关能力。
- `proactive-agent`：用于让智能体更主动地规划、提醒、推进和协作。
- `self-improving-agent`：用于通过复盘、记忆和反馈持续优化智能体行为。

<a id="cat-workflow-automation"></a>
### 4. 工程工作流自动化（engineering-workflow-automation，10）

- `agent-browser`：用于用自然语言驱动真实浏览器完成操作和检查。
- `gh-address-comments`：用于处理代码托管平台评论、逐条回应并完成修复闭环。
- `gh-fix-ci`：用于诊断持续集成失败、定位原因并修复流水线问题。
- `github`：用于管理代码托管平台的议题、合并请求、分支和自动化流程。
- `gsd-graphify-brownfield-bootstrap`：用于为存量项目建立图谱化理解和任务推进基础。
- `hermes-graphify-gsd-project-integration`：用于把项目接入图谱化智能开发工作流。
- `jupyter-notebook`：用于创建、整理和维护交互式分析笔记本。
- `playwright`：用于浏览器自动化测试、页面检查和交互验证。
- `web-scraper`：用于抓取网页数据、结构化提取内容并处理反爬限制。
- `yeet`：用于一体化完成暂存、提交、推送和合并请求流程。

<a id="cat-devops-sre"></a>
### 5. DevOps / SRE（devops-sre，10）

- `changelog-generator`：用于根据提交和变更自动生成版本更新日志。
- `ci-cd-pipeline-builder`：用于设计持续集成和持续交付流水线。
- `cloudflare-troubleshooting`：用于排查云网络、边缘服务、缓存和访问异常。
- `env-secrets-manager`：用于管理环境变量、密钥、配置分层和泄露风险。
- `github-ops`：用于仓库运维、权限、自动化任务和协作流程管理。
- `incident-commander`：用于事故响应、分级、沟通、恢复和复盘。
- `observability-designer`：用于设计监控、日志、指标、告警和服务目标。
- `release-manager`：用于规划发布节奏、变更窗口、风险控制和回滚方案。
- `senior-architect`：用于架构评审、技术选型、扩展性和系统演进判断。
- `senior-devops`：用于综合运维、自动化、可靠性和交付体系建设。

<a id="cat-finance-investing"></a>
### 6. 金融投资（finance-investing，13）

- `comps-valuation-analyst`：用于可比公司估值、倍数分析和估值区间判断。
- `earnings-call-analyzer`：用于分析财报电话会、管理层表述、指引和风险信号。
- `event-driven-tracker`：用于跟踪财报、并购、回购、分红等市场事件。
- `factor-backtester`：用于回测因子策略、检验收益、换手和稳定性。
- `financial-analyst`：用于财务比率分析、估值、预算差异和预测。
- `financial-data-collector`：用于采集、清洗和校验公司财务与市场数据。
- `investment-memo-writer`：用于把研究结论整理成投资备忘录和决策材料。
- `macro-regime-monitor`：用于跟踪宏观环境、通胀、增长、流动性和风险偏好。
- `options-strategy-evaluator`：用于评估期权结构、盈亏场景、成本和风险。
- `portfolio-risk-manager`：用于分析组合风险、集中度、行业暴露和波动来源。
- `saas-metrics-coach`：用于分析订阅业务收入、留存、获客成本和健康度。
- `sec-filing-reviewer`：用于审阅上市公司披露文件，提取风险和关键变化。
- `stock-screener-builder`：用于构建选股条件、筛选股票池和生成研究清单。

<a id="cat-growth-operations"></a>
### 7. 增长运营（growth-operations-xiaohongshu，11）

- `algorithmic-art`：用于生成算法视觉作品、参数化图形和创意素材。
- `app-store-optimization`：用于应用商店关键词、标题、描述和转化优化。
- `campaign-analytics`：用于分析营销活动表现、归因、转化和投入产出。
- `competitors-analysis`：用于采集竞品信息、对比定位、功能和市场表现。
- `content-creator`：用于策划内容主题、撰写文案、脚本和发布计划。
- `marketing-demand-acquisition`：用于设计获客渠道、投放策略、线索转化和增长实验。
- `marketing-strategy-pmm`：用于市场定位、发布策略、竞争叙事和产品营销。
- `prompt-engineer-toolkit`：用于系统化设计、测试、版本化和优化提示词。
- `seo-audit`：用于网站搜索优化审计、页面建议和技术检查。
- `social-media-analyzer`：用于分析社媒数据、互动率、内容表现和趋势。
- `twitter-reader`：用于读取社交平台帖子内容并提炼关键信息。

<a id="cat-office-white-collar"></a>
### 8. 办公与文档（office-white-collar，16）

- `capture-screen`：用于在本机采集全屏、窗口或区域截图。
- `doc`：用于读取、创建和编辑文字处理文档。
- `doc-coauthoring`：用于协同撰写文档、审阅修改和统一结构。
- `docx`：用于处理文字处理文件的内容、样式和版式。
- `excel-automation`：用于自动化处理电子表格、公式、格式和批量任务。
- `gog`：用于自动化处理邮件、日历、网盘和在线文档办公流程。
- `markdown-tools`：用于转换、合并、清理和格式化标记文档。
- `meeting-minutes-taker`：用于把会议记录整理为结构化纪要、结论和行动项。
- `mermaid-tools`：用于提取、生成和渲染流程图与结构图。
- `pdf`：用于读取、拆分、合并和提取便携文档内容。
- `pdf-creator`：用于从文本或标记文档生成便携文档。
- `ppt-creator`：用于快速生成演示文稿结构、内容和讲稿。
- `pptx`：用于编辑演示文件、清理版式和调整幻灯片结构。
- `spreadsheet`：用于处理表格数据、分析结果和格式化工作簿。
- `transcript-fixer`：用于修正转录文本错误、统一术语和整理段落。
- `xlsx`：用于读取、编辑、分析和修复电子表格文件。

<a id="cat-knowledge-pm"></a>
### 9. 项目管理与知识库集成（knowledge-and-pm-integrations，8）

- `arxiv`：用于检索学术论文、提取摘要和整理研究线索。
- `linear`：用于管理项目任务、缺陷、迭代和团队协作流程。
- `llm-wiki`：用于维护模型知识库，沉淀资料、概念和项目上下文。
- `notion-knowledge-capture`：用于把讨论、决策和经验沉淀为知识库页面。
- `notion-meeting-intelligence`：用于基于知识库准备会议材料、议程和背景信息。
- `notion-research-documentation`：用于跨知识库页面研究并汇总成结构化文档。
- `notion-spec-to-implementation`：用于把规格文档转化为实施计划、任务和进度。
- `obsidian`：用于读取、搜索和创建本地知识库笔记。

<a id="cat-operations-general"></a>
### 10. 通用运营（operations-general，11）

- `brand-guidelines`：用于制定品牌颜色、字体、语气和视觉表达规范。
- `confidence-check`：用于结构化自我审查，识别假设、不确定性和幻觉风险。
- `docs-cleaner`：用于清理重复文档、合并有效内容并提升可读性。
- `fact-checker`：用于核查事实、寻找可靠来源并提出修正建议。
- `internal-comms`：用于撰写内部公告、说明、同步和变更沟通。
- `interview-system-designer`：用于设计招聘流程、面试题、评分标准和校准机制。
- `slack-gif-creator`：用于制作适合团队沟通工具使用的动态图片素材。
- `supermemory`：用于管理长期记忆、用户偏好、项目状态和矛盾信息。
- `teams-channel-post-writer`：用于撰写团队频道知识分享和功能介绍内容。
- `theme-factory`：用于为文档、页面和演示生成统一视觉主题。
- `weather`：用于查询天气、整理出行信息和辅助日程安排。

<a id="cat-product-design"></a>
### 11. 产品与设计（product-design，10）

- `agile-product-owner`：用于敏捷需求管理、用户故事、验收标准和迭代规划。
- `canvas-design`：用于创建商业画布、产品画布和视觉化方案。
- `competitive-teardown`：用于系统拆解竞品、价格、评价、招聘和流量信号。
- `landing-page-generator`：用于生成高转化落地页结构、内容和前端实现。
- `product-analysis`：用于多角度分析产品问题、机会、指标和改进方向。
- `product-manager-toolkit`：用于产品经理常用的优先级、访谈、需求和发现方法。
- `product-strategist`：用于产品战略、路线图、目标体系和团队扩展规划。
- `saas-scaffolder`：用于根据产品简报生成订阅软件项目脚手架。
- `ui-design-system`：用于设计界面组件体系、设计令牌和响应式规范。
- `ux-researcher-designer`：用于用户研究、旅程地图、可用性测试和体验设计。

<a id="cat-security-reliability"></a>
### 12. 安全治理与稳定性（security-and-reliability，7）

- `link-checker`：用于检查链接可达性、跳转链路和可疑域名风险。
- `security-best-practices`：用于按语言和框架检查安全最佳实践并提出改进。
- `security-ownership-map`：用于分析代码责任分布、敏感模块归属和人员风险。
- `security-threat-model`：用于识别资产、边界、攻击路径和缓解措施。
- `sentry`：用于查看线上异常、错误事件和服务健康信息。
- `skill-security-auditor`：用于安装前审计技能安全风险并给出处理建议。
- `skill-vetter`：用于检查第三方技能中的恶意指令、越权和泄露风险。

<a id="cat-multimodal-media"></a>
### 13. 多模态内容（multimodal-media，6）

- `imagegen`：用于生成、编辑、抠图和扩展图片内容。
- `screenshot`：用于采集桌面截图、窗口截图或指定区域截图。
- `sora`：用于生成、轮询、下载和管理视频内容。
- `speech`：用于把文本转换为语音旁白或批量音频。
- `summarize`：用于摘要网页、文档、邮件和长文本内容。
- `transcribe`：用于把音频或视频转写为文本并可区分说话人。

<a id="cat-deployment-platforms"></a>
### 14. 部署平台（deployment-platforms，4）

- `cloudflare-deploy`：用于部署网站和应用到边缘计算与静态托管平台。
- `netlify-deploy`：用于发布静态站点和前端项目到托管平台。
- `render-deploy`：用于分析项目并生成云托管部署配置。
- `vercel-deploy`：用于发布网页应用、预览环境和生产环境。

<a id="cat-memory-safety"></a>
### 15. 记忆与安全（openclaw-memory-and-safety，4）

- `honcho`：用于配置长期记忆、用户画像和多配置隔离。
- `input-guard`：用于扫描外部文本中的提示注入和不可信指令。
- `rag-architect`：用于设计检索增强生成系统、评估召回和回答质量。
- `runbook-generator`：用于根据代码库生成运维手册、排障步骤和响应流程。

<a id="cat-task-understanding"></a>
### 16. 任务理解与拆解（task-understanding-decomposition，2）

- `reflect-learn`：用于从对话、纠错和成功经验中提炼可复用学习。
- `tavily-search`：用于联网检索最新信息、补充来源证据和事实核查。

## 建议补充的高热度技能（候选）

以下技能是建议纳入下一批扩充的候选项，当前 **尚未** 在 `skills/` 目录中落地，因此 **不计入** 上方的 `16 类 / 207 技能` 统计。

如需继续扩充，建议下一批优先关注：

- `link-checker`（2.1K 下载）：建议归类到 `security-and-reliability`，用于链接安全检测、钓鱼链接识别与基础可达性检查。

### 工程工作流与协作（仍在候选）

- `github`（24.8K 下载）：建议归类到 `engineering-workflow-automation`，用于管理议题、合并请求和持续集成运行；可与 `gh-address-comments`、`gh-fix-ci`、`yeet` 形成互补。

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
