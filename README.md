# Commonly Used High-Value Skills

一个按场景组织的高价值 Skills 仓库，覆盖开发工程、DevOps、产品设计、运营、办公自动化与 AI 安全等常见高频任务。

## 仓库目标

- 沉淀高复用、可组合的技能模块（Skills）。
- 通过统一目录和文档结构，降低检索和使用成本。
- 让常见任务可以快速匹配到可执行的方法与模板。

## 目录结构

```text
skills/
  customized-solutions/               # 预留的定制化方案分类（当前为空）
  developer-engineering/              # 开发工程
  devops-sre/                         # DevOps / SRE
  growth-operations-xiaohongshu/      # 增长运营（小红书/社媒）
  office-white-collar/                # 办公与文档生产力
  openclaw-memory-and-safety/         # 记忆与安全
  operations-general/                 # 通用运营
  product-design/                     # 产品与设计
  task-understanding-decomposition/   # 任务理解与拆解
```

## 使用方式

1. 按分类进入目标目录（如 `skills/developer-engineering/`）。
2. 打开对应技能的 `SKILL.md` 查看触发条件、操作流程和脚本说明。
3. 若技能下含 `scripts/`、`references/`、`assets/`，优先复用现成内容。

## 技能总览（按分类）

### 1. 开发工程（developer-engineering，25）

- `agent-designer`：用于设计和评估多智能体系统架构。
- `api-design-reviewer`：用于审查 API 设计规范、可维护性与一致性。
- `api-test-suite-builder`：用于构建 API 自动化测试套件。
- `cli-demo-generator`：用于生成命令行工具演示与示例流程。
- `codebase-onboarding`：用于快速理解陌生代码库结构与关键模块。
- `database-designer`：用于数据库建模与表结构设计。
- `database-schema-designer`：用于设计或优化数据库 Schema。
- `dependency-auditor`：用于依赖审计、漏洞排查与许可证检查。
- `frontend-design`：用于前端界面设计实现与体验优化。
- `git-worktree-manager`：用于管理 Git Worktree 并行开发工作流。
- `github-contributor`：用于规范化 GitHub 贡献流程（Issue/PR/协作）。
- `i18n-expert`：用于国际化与本地化能力建设。
- `mcp-builder`：用于搭建 MCP 工具与集成能力。
- `mcp-server-builder`：用于构建和调试 MCP Server。
- `migration-architect`：用于制定数据或系统迁移方案。
- `monorepo-navigator`：用于在 Monorepo 中快速定位代码与依赖关系。
- `performance-profiler`：用于性能剖析、瓶颈定位与优化建议。
- `pr-review-expert`：用于提升 Pull Request 审查质量。
- `promptfoo-evaluation`：用于提示词/模型输出评测与对比。
- `qa-expert`：用于测试策略制定与质量保障。
- `repomix-safe-mixer`：用于安全打包与整理仓库上下文。
- `skill-tester`：用于技能可用性测试与效果验证。
- `tech-debt-tracker`：用于识别、记录和治理技术债。
- `web-artifacts-builder`：用于构建和管理前端制品。
- `webapp-testing`：用于 Web 应用自动化测试与回归验证。

### 2. DevOps / SRE（devops-sre，9）

- `changelog-generator`：用于自动生成版本变更日志。
- `ci-cd-pipeline-builder`：用于设计与搭建 CI/CD 流水线。
- `cloudflare-troubleshooting`：用于 Cloudflare 常见问题排查。
- `env-secrets-manager`：用于环境变量与密钥管理。
- `github-ops`：用于 GitHub 运维与仓库流程自动化。
- `incident-commander`：用于事故响应、升级与复盘流程。
- `observability-designer`：用于监控、告警和 SLO 体系设计。
- `release-manager`：用于发布节奏、版本流程与变更管控。
- `senior-devops`：用于综合 DevOps 工程实践与体系落地。

### 3. 增长运营（growth-operations-xiaohongshu，10）

- `algorithmic-art`：用于生成算法风格视觉内容与创意素材。
- `app-store-optimization`：用于应用商店优化（ASO）与关键词策略。
- `campaign-analytics`：用于活动归因分析与 ROI 评估。
- `competitors-analysis`：用于竞品信息采集与对标分析。
- `content-creator`：用于内容策划、脚本与发布节奏设计。
- `marketing-demand-acquisition`：用于获客漏斗与需求增长策略。
- `marketing-strategy-pmm`：用于市场定位、信息传达与 PMM 策略。
- `prompt-engineer-toolkit`：用于运营场景下的提示词工程实践。
- `social-media-analyzer`：用于社媒数据分析与趋势洞察。
- `twitter-reader`：用于读取、整理和提炼 Twitter 信息。

### 4. 办公与文档（office-white-collar，15）

- `capture-screen`：用于系统级截图与区域截图。
- `doc-coauthoring`：用于文档协同编辑与审阅流程。
- `docx`：用于 Word（.docx）文档创建、编辑与分析。
- `excel-automation`：用于 Excel 自动化处理与批量操作。
- `financial-analyst`：用于财务分析、预测与报告输出。
- `financial-data-collector`：用于财务数据抓取、清洗与校验。
- `markdown-tools`：用于 Markdown 转换、合并和内容处理。
- `meeting-minutes-taker`：用于会议纪要结构化整理。
- `mermaid-tools`：用于 Mermaid 图表提取、生成与渲染。
- `pdf`：用于 PDF 的读取、解析和内容处理。
- `pdf-creator`：用于从 Markdown/文本生成 PDF。
- `ppt-creator`：用于快速生成演示文稿内容。
- `pptx`：用于 PPTX 文件编辑、清理与结构操作。
- `transcript-fixer`：用于转录文本纠错、对比与修订。
- `xlsx`：用于电子表格分析、公式与格式处理。

### 5. 记忆与安全（openclaw-memory-and-safety，3）

- `input-guard`：用于检测外部文本中的提示注入风险。
- `rag-architect`：用于 RAG 系统架构设计与评估。
- `runbook-generator`：用于生成标准化运维 Runbook。

### 6. 通用运营（operations-general，8）

- `brand-guidelines`：用于品牌规范制定与统一表达。
- `docs-cleaner`：用于文档清洗、重构与降噪。
- `fact-checker`：用于信息事实核查与可信度评估。
- `internal-comms`：用于内部沟通文案与公告写作。
- `interview-system-designer`：用于面试流程、题库与评估体系设计。
- `slack-gif-creator`：用于制作 Slack 场景 GIF 素材。
- `teams-channel-post-writer`：用于撰写 Teams 频道发布文案。
- `theme-factory`：用于主题风格配置与视觉模板输出。

### 7. 产品与设计（product-design，9）

- `agile-product-owner`：用于敏捷需求管理与迭代推进。
- `canvas-design`：用于商业/产品画布设计与梳理。
- `competitive-teardown`：用于产品竞品拆解分析。
- `product-analysis`：用于产品诊断、问题分析与优化建议。
- `product-manager-toolkit`：用于产品经理常用方法与模板。
- `product-strategist`：用于产品战略规划与路线图设计。
- `saas-scaffolder`：用于 SaaS 产品方案脚手架与初始结构。
- `ui-design-system`：用于 UI 设计系统与 Design Token 规范。
- `ux-researcher-designer`：用于用户研究与体验设计方法。

### 8. 任务理解与拆解（task-understanding-decomposition，9）

- `agent-workflow-designer`：用于设计 Agent 协作流程与分工。
- `brainstorming`：用于在实现前进行需求澄清与方案发散。
- `deep-research`：用于深度研究、证据汇总与结论输出。
- `prompt-optimizer`：用于优化提示词结构与效果。
- `reflect-learn`：用于复盘总结并沉淀可复用经验。
- `skill-creator`：用于新技能创建、迭代与评测。
- `skill-reviewer`：用于技能质量评审与改进建议。
- `skills-search`：用于快速检索并匹配可用技能。
- `writing-plans`：用于编写可执行的实施计划。

## 快速检索命令

```bash
# 列出所有技能定义文件
rg --files skills | rg "SKILL.md$"

# 按关键词查找技能
rg -n "prompt|security|pdf|deploy" skills/**/SKILL.md
```

## 维护建议

- 新增技能时保持 `skills/<分类>/<skill-name>/SKILL.md` 结构。
- 每个技能应提供清晰触发条件、步骤、边界和验证方式。
- 优先复用 `scripts/` 与 `references/`，减少重复实现。

---

如果你希望，我可以在下一步继续补一版 `README.zh-CN.md`（面向中文）+ `README.en.md`（面向国际协作），并自动校验两份目录与技能数量一致。
