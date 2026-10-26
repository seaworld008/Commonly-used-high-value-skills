# 2026-10-26 质量优先技能维护

基线为 `937497ffde6a53232c8e24662733e7d7d64fc4e5`，从干净的 `main`
执行 fetch、`pull --ff-only` 后维护。未发现用户未提交改动；旧的失效 detached
worktree 记录保持不变。分支为 `codex/portfolio-maintenance-20261026`。

## 组合决策

初始组合审计覆盖 294 个公共入口：285 keep、9 review，平均分 91.7，退役策略
零违规。评分只用于分流，不因行数、单文件或 description 的启发式提示自动删除。

| 待审入口 | 保留依据 |
|---|---|
| `agent-browser` | 真实 CLI、快照引用及浏览器信任边界，并有命令和上游参考文件。 |
| `firebase-security-rules-auditor` | 规则评分、越权路径、租户隔离及 emulator 负向验收标准。 |
| `lark-skill-maker` | CLI schema、scope、OpenAPI 和多步数据传递的外部系统契约。 |
| `obsidian` | vault 路径、frontmatter、wikilink 与定点编辑契约。 |
| `lark-doc` | Docx/Wiki 路由、身份和授权，以及完整按需参考文件。 |
| `llm-wiki` | 不可变原始资料、来源漂移、知识结构和 lint 标准。 |
| `executing-plans` | 计划执行、依赖顺序、漂移恢复和证据账本；属于完整工作流。 |
| `hermes-open-gsd-workflow` | 不同 runtime 状态根的隔离、失败归属及组合依赖锁。 |
| `writing-plans` | 任务边界、接口依赖、验收和续接证据；属于完整工作流。 |

另行发现并合并 `self-improving-agent` → `reflect-learn`。旧入口只有一个
`SKILL.md`，没有唯一脚本、可用外部 API 契约、领域高风险规则或可执行验收资产；
其中的 `memory_search`、`mcp_call`、系统提示词修改和 cron 调用未定义真实宿主契约。
canonical 已有信号检测、状态管理、指标、模板和 schema。删除入口前，已将有用的
观察/归因、单变量对照、基线与回归检查、回滚及漂移复核方法迁入
`reflect-learn/references/controlled-improvement.md`，并加入按需入口和宿主授权边界。

永久策略新增该退役名称及 canonical 分组；旧视频来源记录改为 retired/archived，
不保留可发现别名。`agent-hub` 与 `gh-address-comments` 的引用改到 canonical。
这使公共入口数从 294 降至 293；未来正式发布须按公开入口删除的规则提高主版本，
本轮不发布新版本，也不修改全局技能安装。

## 正文与流水线修正

- `agent-workflow-designer`：移除固定模型家族、省费百分比和每次调用费用的无测量保证，
  改为当前可用模型、官方价格、同一输入集质量及每个完成任务的实测成本契约。
- `gh-address-comments`：用实际的分页 GraphQL `reviewThreads` 查询替换无效的
  `reviews[].comments[].state` 示例，区分 thread 解决状态和 review 状态；对 PR #143
  的只读查询已验证 schema 和分页结构，不声称已发送评论。
- `security-review`：吸收 Sentry 对实际指南路由的修正，移除不存在的 Go/Rust/Java、
  Kubernetes/Terraform/CI/cloud 参考路径；补充 frontend/modern-threats 与可用
  Django、GitHub Actions 技能的可选路由，保留缺失专用技能时的具体 fallback。
- `neon-postgres`：补充 paid/prepaid gateway 边界、`enabled: true` 模型筛选、
  RRF 的 NULL embedding 排除和可更换 embedding provider 的条件；用 recall、
  nDCG@10/MRR、p95 延迟、token 成本和 fallback rate 明确检索评测。
- `test_pr4_upstream_decisions.py`：monitor 检查点从旧 SHA 常量改为核对最近成功的
  commit-aware 审阅记录及同提交许可证据。冻结快照的固定 SHA 断言保持不变。

## 已审来源

| 来源 | 已审提交 | 决策 |
|---|---|---|
| `getsentry/skills` | `d12f250460ffd961f549dbebf7eeb0cf4afd4c2e` | 审阅 18 提交/14 文件的净差异；更新既有安全审查路由，推进两个受管入口检查点；不为新上游入口扩充组合。 |
| `neondatabase/agent-skills` | `ccca3334a7542d3133134cc6926f2fafc6edeb1f` | 审阅 5 提交/14 文件；补充检索和模型访问方法，推进两个入口检查点；未引入 SDK 或执行云端操作。 |
| `obra/superpowers` | `2ce8aa15d05bd57213e6f746f953aafb7ded7a8b` | 审阅 2 提交/64 文件的净差异；三个 writing-skills 来源移到 references，保留本地目标路径和链接；11 个入口推进检查点，保留已有宿主适配，不复制强制委派或未测 token 节省数字。 |
| `xiaolai/nlpm` | `6ed91c366892febca10605a952e0a57fcbac7cc0` | 392 提交的净差异为 35 个 auditor 报告、统计及记录文件；不改本地方法正文，记录已审检查点。 |
| `NousResearch/hermes-agent` 稳定版 | `bf0203a794a07aac3ff764972ab9087baa4e4f4e`（`v0.22.5`） | 核验 MIT 不可变许可及全部受管文件；同步脚本更新 9 个既有文件，涉及 PM、CLI、Windows 测试、桌面插件与 MCP sampling 兼容。其余默认分支来源未随之推进。 |

Sentry、Neon 的不可变许可证据均为 Apache-2.0；原有 OWASP CC BY-SA 参考许可
和所有既有本地补充均保留。检查点推进表示完成指定受管范围的比较与取舍，不代表
本地文件与上游逐字相同，也不代表上游所有插件功能已导入。

Hermes 保留本地 frontmatter，版本从 `2.0.22` 提高到 `2.0.23`；这不是上游
技能版本 `3.2.0`。22 个受管普通文件（18 references、3 templates 和入口）均保留。
薄路由的运行时/状态根契约没有变化；按其正文的精确摘要完成兼容审阅后，由同步脚本
刷新组合依赖锁。稳定版、path commit 和 canonical 摘要的原有强断言已更新到本次
核验值，没有放宽镜像清单、许可或文件模式要求。

## 最终验证与来源状态

按用户指定顺序完成 frontmatter、in-house 来源、视图、标签、catalog、README、
严格质量、组合策略、许可、全部 unit tests、冲突标记、来源、视频映射、实时健康、
Python 编译、Node 安装器和打包检查；另外完成完整 `validate_repository.py --refresh`。
最终结果为 692 项 pytest、65 项 bundled security Node 测试通过，299 个技能 Python
文件编译通过；严格质量 296 PASS / 0 WARN / 0 FAIL（含嵌套入口），来源覆盖
293/293，许可 missing/disallowed 为零，健康评估 PASS。没有手工编辑生成物。

新增参考文件需先进入 Git 索引才能满足现有清单测试；前期该门禁失败后已补齐。
所有旧 SHA 断言和生成视图漂移修复后，最终完整流水线通过。提交后再次执行生成阶段
并要求 `git diff --exit-code`，远端验证由附带 PR 的最新 head 检查单独提供。

## 上游扫描完成与合并阻塞

完整检查正常结束，覆盖 161 个条目，未被超时或中断。初始结果为 59 equal、
1 auto changed、74 monitor review、1 unavailable、26 expected skipped，零 rollback。
唯一 unavailable 是 writing-skills 的三个旧上游路径；修正后，Obra 范围的在线完整
文件/许可检查通过，并记录已审检查点。初始失败事实保留，不能将原报告描述成绿色。

把已审 checkpoint、Hermes 自动应用和路径修复的范围证据与初始扫描逐项对齐后：
59 个一致、16 个 monitor 已审、1 个自动更新已应用、59 个 monitor 仍待审、
26 个按策略跳过，未解决的 unavailable 为零。明细及不可变比较 URL 见
[机器可读审计](maintenance-audit-2026-10-26.json)。本次没有新的 API 限流、仓库不可达
或缺少许可阻塞；按策略跳过不代表已核验其最新上游。

| 未完成 commit-aware 兼容性审阅的来源 | 条目数 |
|---|---:|
| `simota/agent-skills` | 30 |
| `alirezarezvani/claude-skills` | 8 |
| `NousResearch/hermes-agent` 默认分支 | 6 |
| `wshobson/agents` | 4 |
| `Jeffallan/claude-skills` | 2 |
| `Linked-API/linkedin-skills` | 2 |
| `prisma/skills` | 2 |
| `Graphify-Labs/graphify` | 1 |
| `Xquik-dev/x-twitter-scraper` | 1 |
| `firebase/agent-skills` | 1 |
| `mattpocock/skills` | 1 |
| `microsoft/azure-skills` | 1 |

这 59 个条目的正文差异没有获得完整语义/兼容性结论，因此检查点保持原值。
Simota compare API 返回的 300 项文件列表已达上限，不能把它当作完整审阅证据；
逐文件扫描结果另有完整记录。刷新规划器按日期给出的零过期项，也不能解释为零差异。
按照本轮用户指令，有 monitor 差异未能可靠解决时不合并：**本轮 PR 保持草稿，
main 和正式发布保持在原基线。** 这不是本地测试失败或新许可缺失。

任何未解决的来源、许可或 monitor 语义审阅问题都保留证据并阻止本轮合并；不把
静态健康 PASS 等同于全部来源最新。健康报告的 dead-link 输入为已有报告，本次没有
另行运行全量 URL 探测。没有运行真实云服务、Hermes 客户端或独立模型行为评测。
