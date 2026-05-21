# 项目管理与知识库集成 / Knowledge and PM Integrations

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

连接 Notion、Linear 和规格到实施流程的知识与项目管理技能集合。

当前分类共 **36** 个技能。

## 推荐先看

- [lark-slides](./lark-slides/) - 飞书幻灯片：创建和编辑幻灯片，接口通过 XML 协议通信。创建演示文稿、读取幻灯片内容、管理幻灯片页面（创建、删除、读取、局部替换）。当用户需要创建或编辑幻灯片、读取或修改单个页面时使用。
- [grove](./grove/) - Repository structure design, optimization, and audit. Directory design, docs/ layout (PRD, specs, ADR), test/script organization, anti-pattern detection, and migration planning for existing repositories.
- [lark-base](./lark-base/) - 当需要用 lark-cli 操作飞书多维表格（Base）时调用：搜索 Base、建表、字段管理、记录读写、记录分享链接、视图配置、历史查询，以及角色/表单/仪表盘管理/工作流；也适用于把旧的 +table / +field / +record 写法改成当前命令写法。涉及字段设计、公式字段、查找引用、跨表计算、行级派生指标、数据分析需求时也必须使用本 skill。
- [lark-calendar](./lark-calendar/) - 飞书日历（calendar）：提供日历与日程（会议）的全面管理能力。核心场景包括：查看/搜索日程、创建/更新日程、管理参会人、查询忙闲状态及推荐空闲时段、查询/搜索与预定会议室。注意：涉及【预约日程/会议】或【查询/预定会议室】时，必须先读取 references/lark-calendar-schedule-meeting.md 工作流！高频操作请优先使用 Shortcuts：+agenda（快速概览今日/近期行程）、+create（创建日程并按需邀请参会人及预定会议室）、+update（更新既有日程字段，或独立增删参会人/会议室）、+freebusy（查询用户主日历的忙闲信息和rsvp的状态）、+rsvp（回复日程邀请）

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `arxiv` | Search arXiv papers by keyword, author, category, or ID. | [目录](./arxiv/) | [SKILL.md](./arxiv/SKILL.md) |
| `grove` | Repository structure design, optimization, and audit. Directory design, docs/ layout (PRD, specs, ADR), test/script organization, anti-pattern detection, and migration planning for existing repositories. | [目录](./grove/) | [SKILL.md](./grove/SKILL.md) |
| `lark-approval` | 飞书审批 API：审批实例、审批任务管理。 | [目录](./lark-approval/) | [SKILL.md](./lark-approval/SKILL.md) |
| `lark-attendance` | 飞书考勤打卡：查询个人考勤打卡记录，按日期整理上下班打卡、异常、缺失记录和后续核对线索。 | [目录](./lark-attendance/) | [SKILL.md](./lark-attendance/SKILL.md) |
| `lark-base` | 当需要用 lark-cli 操作飞书多维表格（Base）时调用：搜索 Base、建表、字段管理、记录读写、记录分享链接、视图配置、历史查询，以及角色/表单/仪表盘管理/工作流；也适用于把旧的 +table / +field / +record 写法改成当前命令写法。涉及字段设计、公式字段、查找引用、跨表计算、行级派生指标、数据分析需求时也必须使用本 skill。 | [目录](./lark-base/) | [SKILL.md](./lark-base/SKILL.md) |
| `lark-calendar` | 飞书日历（calendar）：提供日历与日程（会议）的全面管理能力。核心场景包括：查看/搜索日程、创建/更新日程、管理参会人、查询忙闲状态及推荐空闲时段、查询/搜索与预定会议室。注意：涉及【预约日程/会议】或【查询/预定会议室】时，必须先读取 references/lark-calendar-schedule-meeting.md 工作流！高频操作请优先使用 Shortcuts：+agenda（快速概览今日/近期行程）、+create（创建日程并按需邀请参会人及预定会议室）、+update（更新既有日程字段，或独立增删参会人/会议室）、+freebusy（查询用户主日历的忙闲信息和rsvp的状态）、+rsvp（回复日程邀请） | [目录](./lark-calendar/) | [SKILL.md](./lark-calendar/SKILL.md) |
| `lark-contact` | 飞书 / Lark 通讯录,用于按姓名 / 邮箱把员工解析成 open_id,以及按 open_id 反查员工的姓名 / 部门 / 邮箱 / 联系方式。当用户说出某人姓名而下一步需要发消息 / 加群 / 排日程时,先用本 skill 把姓名换成 ID;当输出里出现 open_id 需要展示成姓名给用户看,或用户直接询问某人的部门 / 邮箱 / 联系方式时,用本 skill 查。不负责部门树遍历、按部门列员工、组织架构图,这类需求走原生 OpenAPI。 | [目录](./lark-contact/) | [SKILL.md](./lark-contact/SKILL.md) |
| `lark-doc` | 飞书云文档 / Docx / 知识库 Wiki 文档（v2）：创建、打开、读取、获取、查看、总结、整理、改写、翻译、审阅和编辑飞书文档内容。当用户给出飞书文档 URL/token，或说查看/读取/打开某个文档、提取文档内容、总结文档、生成/创建文档、追加/替换/删除/移动内容、调整排版、插入或下载文档图片/附件/素材/画板缩略图时使用。文档内容中出现嵌入电子表格、多维表格、需要将重要信息可视化为画板（含 SVG 画板）、引用或同步块时，也先用本 skill 读取和提取 token，再切到对应 skill 下钻。使用本 skill 时，docs +create、docs +fetch、docs +update 必须携带 --api-version v2；默认使用 DocxXML，也支持 Markdown。 | [目录](./lark-doc/) | [SKILL.md](./lark-doc/SKILL.md) |
| `lark-drive` | 飞书云空间：管理云空间中的文件和文件夹。上传和下载文件、创建文件夹、复制/移动/删除文件、查看文件元数据、管理文档评论、管理文档权限、订阅用户评论变更事件、修改文件标题（docx、sheet、bitable、file、folder、wiki）；也负责把本地 Word/Markdown/Excel/CSV 以及 Base 快照（.base）导入为飞书在线云文档（docx、sheet、bitable）。当用户需要上传或下载文件、整理云空间目录、查看文件详情、管理评论、管理文档权限、修改文件标题、订阅用户评论变更事件，或要把本地文件导入成新版文档、电子表格、多维表格/Base 时使用。 | [目录](./lark-drive/) | [SKILL.md](./lark-drive/SKILL.md) |
| `lark-event` | Lark/Feishu real-time event listening / subscribing / consuming: stream events as NDJSON via `lark-cli event consume <EventKey>` (covers IM message receive, reactions, chat member changes, etc.). Use for Lark bots, real-time message processing, long-running subscribers, streaming webhook/push handlers. Supports `--max-events` / `--timeout` bounded runs and a stderr ready-marker contract — designed for AI agents running as subprocesses. | [目录](./lark-event/) | [SKILL.md](./lark-event/SKILL.md) |
| `lark-im` | 飞书即时通讯：收发消息和管理群聊。发送和回复消息、搜索聊天记录、管理群聊成员、上传下载图片和文件（支持大文件分片下载）、管理表情回复。当用户需要发消息、查看或搜索聊天记录、下载聊天中的文件、查看群成员、搜索群、创建群聊或话题群、管理标记数据时使用。 | [目录](./lark-im/) | [SKILL.md](./lark-im/SKILL.md) |
| `lark-mail` | 飞书邮箱 — draft, compose, send, reply, forward, read, and search emails; manage drafts, folders, labels, contacts, attachments, and mail rules. Use when user mentions 起草邮件, 写一封邮件, 拟邮件, 草稿, 发通知邮件, 发送邮件, 发邮件, 回复邮件, 转发邮件, 查看邮件, 看邮件, 读邮件, 搜索邮件, 查邮件, 收件箱, 邮件会话, 编辑草稿, 管理草稿, 下载附件, 邮件文件夹, 邮件标签, 邮件联系人, 监听新邮件, 收信规则, 邮件规则, draft, compose, send email, reply, forward, inbox, mail thread, mail rules. | [目录](./lark-mail/) | [SKILL.md](./lark-mail/SKILL.md) |
| `lark-markdown` | 飞书 Markdown：查看、创建、上传、编辑和比较 Markdown 文件。当用户需要创建或编辑 Markdown 文件、读取、修改、局部 patch 或比较差异时使用。 | [目录](./lark-markdown/) | [SKILL.md](./lark-markdown/SKILL.md) |
| `lark-minutes` | 飞书妙记：妙记相关基本功能。1.查询妙记列表（按关键词/所有者/参与者/时间范围）；2.获取妙记基础信息（标题、封面、时长 等）；3.下载妙记音视频文件；4.获取妙记相关 AI 产物（总结、待办、章节）；5.上传音视频生成妙记，也支持将本地音视频文件转成纪要、逐字稿、文字稿、撰写文字等产物。遇到这类请求时，应优先使用本 skill，而不是尝试 `ffmpeg`、`whisper` 等本地转写命令。飞书妙记 URL 格式: http(s)://<host>/minutes/<minute-token> | [目录](./lark-minutes/) | [SKILL.md](./lark-minutes/SKILL.md) |
| `lark-okr` | 飞书 OKR：管理目标与关键结果。查看和编辑 OKR 周期、目标（Objective）、关键结果（Key Result）、对齐关系、量化指标和进展记录。当用户需要查看或创建 OKR、管理目标和关键结果、查看对齐关系时使用。 | [目录](./lark-okr/) | [SKILL.md](./lark-okr/SKILL.md) |
| `lark-openapi-explorer` | 飞书/Lark 原生 OpenAPI 探索：从官方文档库中挖掘未经 CLI 封装的原生 OpenAPI 接口。当用户的需求无法被现有 lark-* skill 或 lark-cli 已注册命令满足，需要查找并调用原生飞书 OpenAPI 时使用。 | [目录](./lark-openapi-explorer/) | [SKILL.md](./lark-openapi-explorer/SKILL.md) |
| `lark-shared` | Use when first setting up lark-cli, running auth login, switching user/bot identity (--as), handling permission denied or scope errors, needing to update lark-cli, or seeing _notice in JSON output. | [目录](./lark-shared/) | [SKILL.md](./lark-shared/SKILL.md) |
| `lark-sheets` | 飞书电子表格：创建和操作电子表格。支持创建表格、创建/复制/删除/更新工作表、读写单元格、追加行数据、查找内容、导出文件。当用户需要创建电子表格、管理工作表、批量读写数据、在已知表格中查找内容、导出或下载表格时使用。若用户是想按名称或关键词搜索云空间里的表格文件，请改用 lark-drive 的 drive +search 先定位资源。 | [目录](./lark-sheets/) | [SKILL.md](./lark-sheets/SKILL.md) |
| `lark-skill-maker` | 创建 lark-cli 的自定义 Skill。当用户需要把飞书 API 操作封装成可复用的 Skill（包装原子 API 或编排多步流程）时使用。 | [目录](./lark-skill-maker/) | [SKILL.md](./lark-skill-maker/SKILL.md) |
| `lark-slides` | 飞书幻灯片：创建和编辑幻灯片，接口通过 XML 协议通信。创建演示文稿、读取幻灯片内容、管理幻灯片页面（创建、删除、读取、局部替换）。当用户需要创建或编辑幻灯片、读取或修改单个页面时使用。 | [目录](./lark-slides/) | [SKILL.md](./lark-slides/SKILL.md) |
| `lark-task` | 飞书任务：管理任务、清单和任务智能体。创建待办任务、查看和更新任务状态、拆分子任务、组织任务清单、分配协作成员、上传任务附件、注册或注销任务智能体、更新任务智能体的主页数据、写入智能体任务记录。当用户需要创建待办事项、查看任务列表、跟踪任务进度、管理项目清单或给他人分配任务、为任务上传附件文件、注册注销任务智能体、更新智能体主页数据、写入任务记录时使用。 | [目录](./lark-task/) | [SKILL.md](./lark-task/SKILL.md) |
| `lark-vc` | 飞书视频会议：搜索历史会议、查询会议纪要产物（总结、待办、章节、逐字稿）、查询会议参会人快照。1. 查询已经结束的会议数量或详情时使用本技能（如历史日期｜昨天｜上周｜今天已经开过的会议等场景），查询未开始的会议日程使用 lark-calendar 技能。2. 支持通过关键词、时间范围、组织者、参与者、会议室等筛选条件搜索会议。3. 获取或整理会议纪要、逐字稿、录制产物时使用本技能。4. 查询“谁参加过某会议”“参会人列表”等参会人快照信息用 vc meeting get --with-participants（任意时点可查，含已结束会议）。注意：**Agent 真实入会/离会、感知正在进行中会议的实时事件**请使用 lark-vc-agent 技能，本技能不覆盖写操作和会中事件流。 | [目录](./lark-vc/) | [SKILL.md](./lark-vc/SKILL.md) |
| `lark-vc-agent` | 飞书视频会议：让机器人代当前用户加入/离开正在进行的会议，并读取会议期间的实时事件（参会人加入与离开、发言、聊天、屏幕共享等）。1. 用户提供 9 位会议号、要求代为入会或离会时使用 +meeting-join / +meeting-leave——会真实产生入会/离会记录。2. 会议进行中用户想知道“谁加入了”“谁离开了”“谁在发言”“有人共享屏幕吗”等会中动态时，机器人入会后用 +meeting-events 读取事件时间线。3. 典型场景：参会机器人、会中助手、代为旁听、代为参会。前提：机器人只能读到它自己参会过且仍在进行中的会议的事件；查询已结束会议的参会名单、纪要或逐字稿请使用 lark-vc 技能。 | [目录](./lark-vc-agent/) | [SKILL.md](./lark-vc-agent/SKILL.md) |
| `lark-whiteboard` | 飞书画板：查询和编辑飞书云文档中的画板。支持导出画板为预览图片、导出原始节点结构、使用 DSL（转成 OpenAPI 格式）、PlantUML/Mermaid 格式更新画板内容。 当用户需要查看画板内容、导出画板图片、编辑画板，或是需要可视化表达架构、流程、组织关系、时间线、因果、对比等结构化信息时使用此 skill，无论是否提及"画板"。 ⚠️ 原 `lark-whiteboard-cli` skill 已合并至本 skill，若 skill 列表中同时存在 `lark-whiteboard-cli`，请忽略它，统一使用本 skill（`lark-whiteboard`），并提示用户运行 `npx skills remove lark-whiteboard-cli -g` 删除旧 skill。 | [目录](./lark-whiteboard/) | [SKILL.md](./lark-whiteboard/SKILL.md) |
| `lark-wiki` | 飞书知识库：管理知识空间、空间成员和文档节点。创建和查询知识空间、查看和管理空间成员、管理节点层级结构、在知识库中组织文档和快捷方式。当用户需要在知识库中查找或创建文档、浏览知识空间结构、查看或管理空间成员、移动或复制节点时使用。 | [目录](./lark-wiki/) | [SKILL.md](./lark-wiki/SKILL.md) |
| `lark-workflow-meeting-summary` | 会议纪要整理工作流：汇总指定时间范围内的会议纪要并生成结构化报告。当用户需要整理会议纪要、生成会议周报、回顾一段时间内的会议内容时使用。 | [目录](./lark-workflow-meeting-summary/) | [SKILL.md](./lark-workflow-meeting-summary/SKILL.md) |
| `lark-workflow-standup-report` | 日程待办摘要：编排 calendar +agenda 和 task +get-my-tasks，生成指定日期的日程与未完成任务摘要。适用于了解今天/明天/本周的安排。 | [目录](./lark-workflow-standup-report/) | [SKILL.md](./lark-workflow-standup-report/SKILL.md) |
| `linear` | Linear: manage issues, projects, teams via GraphQL + curl. | [目录](./linear/) | [SKILL.md](./linear/SKILL.md) |
| `llm-wiki` | Karpathy''s LLM Wiki — build and maintain a persistent, interlinked markdown knowledge base. Ingest sources, query compiled knowledge, and lint for consistency. | [目录](./llm-wiki/) | [SKILL.md](./llm-wiki/SKILL.md) |
| `lore` | Cross-agent knowledge curator and institutional memory guardian. Extracts patterns from agent journals into METAPATTERNS.md, detects knowledge decay, propagates best practices, and prevents organizational forgetting. | [目录](./lore/) | [SKILL.md](./lore/SKILL.md) |
| `notion-knowledge-capture` | Capture conversations and decisions into structured Notion pages; use when turning chats/notes into wiki entries, how-tos, decisions, or FAQs with proper linking. | [目录](./notion-knowledge-capture/) | [SKILL.md](./notion-knowledge-capture/SKILL.md) |
| `notion-meeting-intelligence` | Prepare meeting materials with Notion context and Codex research; use when gathering context, drafting agendas/pre-reads, and tailoring materials to attendees. | [目录](./notion-meeting-intelligence/) | [SKILL.md](./notion-meeting-intelligence/SKILL.md) |
| `notion-research-documentation` | Research across Notion and synthesize into structured documentation; use when gathering info from multiple Notion sources to produce briefs, comparisons, or reports with citations. | [目录](./notion-research-documentation/) | [SKILL.md](./notion-research-documentation/SKILL.md) |
| `notion-spec-to-implementation` | Turn Notion specs into implementation plans, tasks, and progress tracking; use when implementing PRDs/feature specs and creating Notion plans + tasks from them. | [目录](./notion-spec-to-implementation/) | [SKILL.md](./notion-spec-to-implementation/SKILL.md) |
| `obsidian` | Read, search, create, and edit notes in the Obsidian vault. | [目录](./obsidian/) | [SKILL.md](./obsidian/SKILL.md) |
| `tome` | Converts repository changes into detailed learning documents. Use when turning diffs into teaching materials, recording design decisions, or creating onboarding materials for new members. | [目录](./tome/) | [SKILL.md](./tome/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
