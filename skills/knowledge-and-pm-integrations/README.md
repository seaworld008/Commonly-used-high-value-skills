# 项目管理与知识库集成 / Knowledge and PM Integrations

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

连接 Notion、Linear 和规格到实施流程的知识与项目管理技能集合。

当前分类共 **36** 个技能。

## 推荐先看

- [lark-slides](./lark-slides/) - 飞书幻灯片创建、页面读取、局部编辑和演示稿管理。
- [grove](./grove/) - Repository structure design, optimization, and audit. Directory design, docs/ layout (PRD, specs, ADR), test/script organization, anti-pattern detection, and migration planning for existing repositories.
- [lark-base](./lark-base/) - 当需要用 lark-cli 操作飞书多维表格（Base）时调用：搜索 Base、建表、字段管理、记录读写、记录分享链接、视图配置、历史查询，以及角色/表单/仪表盘管理/工作流；也适用于把旧的 +table / +field / +record 写法改成当前命令写法。涉及字段设计、公式字段、查找引用、跨表计算、行级派生指标、数据分析需求时也必须使用本 skill。
- [lark-calendar](./lark-calendar/) - 飞书日历、日程、参会人、忙闲状态和会议室管理。

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `arxiv` | 用于按关键词、作者、分类或编号检索 arXiv 论文。 | [目录](./arxiv/) | [SKILL.md](./arxiv/SKILL.md) |
| `grove` | Repository structure design, optimization, and audit. Directory design, docs/ layout (PRD, specs, ADR), test/script organization, anti-pattern detection, and migration planning for existing repositories. | [目录](./grove/) | [SKILL.md](./grove/SKILL.md) |
| `lark-approval` | 飞书审批 API：审批实例、审批任务管理。 | [目录](./lark-approval/) | [SKILL.md](./lark-approval/SKILL.md) |
| `lark-attendance` | 飞书考勤打卡查询、异常记录整理和缺失核对。 | [目录](./lark-attendance/) | [SKILL.md](./lark-attendance/SKILL.md) |
| `lark-base` | 当需要用 lark-cli 操作飞书多维表格（Base）时调用：搜索 Base、建表、字段管理、记录读写、记录分享链接、视图配置、历史查询，以及角色/表单/仪表盘管理/工作流；也适用于把旧的 +table / +field / +record 写法改成当前命令写法。涉及字段设计、公式字段、查找引用、跨表计算、行级派生指标、数据分析需求时也必须使用本 skill。 | [目录](./lark-base/) | [SKILL.md](./lark-base/SKILL.md) |
| `lark-calendar` | 飞书日历、日程、参会人、忙闲状态和会议室管理。 | [目录](./lark-calendar/) | [SKILL.md](./lark-calendar/SKILL.md) |
| `lark-contact` | 飞书通讯录人员查询、身份解析和联系信息检索。 | [目录](./lark-contact/) | [SKILL.md](./lark-contact/SKILL.md) |
| `lark-doc` | 飞书云文档 / Docx / 知识库 Wiki 文档（v2）：创建、打开、读取、获取、查看、总结、整理、改写、翻译、审阅和编辑飞书文档内容。当用户给出飞书文档 URL/token，或说查看/读取/打开某个文档、提取文档内容、总结文档、生成/创建文档、追加/替换/删除/移动内容、调整排版、插入或下载文档图片/附件/素材/画板缩略图时使用。文档内容中出现嵌入电子表格、多维表格、需要将重要信息可视化为画板（含 SVG 画板）、引用或同步块时，也先用本 skill 读取和提取 token，再切到对应 skill 下钻。使用本 skill 时，docs +create、docs +fetch、docs +update 必须携带 --api-version v2；默认使用 DocxXML，也支持 Markdown。当用户给出 doubao.com 的 /docx/ 或 /wiki/ URL/token 时，也应直接使用本 skill，不要因为域名不是飞书而回退到 WebFetch；路由依据是 URL 路径模式和 token，而不是域名。 | [目录](./lark-doc/) | [SKILL.md](./lark-doc/SKILL.md) |
| `lark-drive` | 飞书云空间（云盘/云存储）：管理云空间（云盘/云存储）中的文件和文件夹。上传和下载文件、创建文件夹、复制/移动/删除文件、查看文件元数据、管理文档评论、管理文档权限、订阅用户评论变更事件、修改文件标题（docx、sheet、bitable、file、folder、wiki）；也负责把本地 Word/Markdown/Excel/CSV/PPTX 以及 Base 快照（.base）导入为飞书在线云文档（docx、sheet、bitable、slides）。当用户需要上传或下载文件、整理云空间（云盘/云存储）目录、查看文件详情、管理评论、管理文档权限、修改文件标题、订阅用户评论变更事件，或要把本地文件导入成新版文档、电子表格、多维表格/Base/幻灯片 时使用。\\"云空间\\"、\\"云盘\\"和\\"云存储\\"是同一概念，用户说\\"云盘\\"、\\"云存储\\"、\\"网盘\\"、\\"我的空间\\"时均路由到本 skill。当用户给出 doubao.com 的云空间资源 URL/token，或明确提到豆包里的 file/folder/docx/sheet/bitable/wiki 资源时，也应直接使用本 skill，不要因为域名不是飞书而回退到 WebFetch；路由依据是资源类型、URL 路径模式和 token，而不是域名。 | [目录](./lark-drive/) | [SKILL.md](./lark-drive/SKILL.md) |
| `lark-event` | Lark/Feishu real-time event listening / subscribing / consuming: stream events as NDJSON via `lark-cli event consume <EventKey>` (covers IM messages/reactions/chat changes, VC meeting ended, Minutes generated, etc.). Use for Lark bots, real-time message processing, long-running subscribers, streaming webhook/push handlers. Supports `--max-events` / `--timeout` bounded runs and a stderr ready-marker contract — designed for AI agents running as subprocesses. | [目录](./lark-event/) | [SKILL.md](./lark-event/SKILL.md) |
| `lark-im` | 飞书即时通讯：收发消息和管理群聊。发送和回复消息、搜索聊天记录、管理群聊成员、上传下载图片和文件（支持大文件分片下载）、管理表情回复、发送应用内/短信/电话加急。当用户需要发消息、查看或搜索聊天记录、下载聊天中的文件、查看群成员、搜索群、创建群聊或话题群、管理标记数据时使用。 | [目录](./lark-im/) | [SKILL.md](./lark-im/SKILL.md) |
| `lark-mail` | 飞书邮箱 — draft, compose, send, reply, forward, read, and search emails; manage drafts, folders, labels, contacts, attachments, and mail rules. Use when user mentions 起草邮件, 写一封邮件, 拟邮件, 草稿, 发通知邮件, 发送邮件, 发邮件, 回复邮件, 转发邮件, 查看邮件, 看邮件, 读邮件, 搜索邮件, 查邮件, 收件箱, 邮件会话, 编辑草稿, 管理草稿, 下载附件, 邮件文件夹, 邮件标签, 邮件联系人, 监听新邮件, 收信规则, 邮件规则, draft, compose, send email, reply, forward, inbox, mail thread, mail rules. | [目录](./lark-mail/) | [SKILL.md](./lark-mail/SKILL.md) |
| `lark-markdown` | 飞书 Markdown：查看、创建、上传、编辑和比较 Markdown 文件。当用户需要创建或编辑 Markdown 文件、读取、修改、局部 patch 或比较差异时使用。 | [目录](./lark-markdown/) | [SKILL.md](./lark-markdown/SKILL.md) |
| `lark-minutes` | 飞书妙记：妙记相关基本功能。1.查询妙记列表（按关键词/所有者/参与者/时间范围）；2.获取妙记基础信息（标题、封面、时长 等）；3.下载妙记音视频文件；4.获取妙记相关 AI 产物（总结、待办、章节）；5.上传音视频生成妙记，也支持将本地音视频文件转成纪要、逐字稿、文字稿、撰写文字等产物；6.更新妙记标题（重命名妙记）；7.替换妙记逐字稿中的说话人。遇到这类请求时，应优先使用本 skill。飞书妙记 URL 格式: http(s)://<host>/minutes/<minute-token> | [目录](./lark-minutes/) | [SKILL.md](./lark-minutes/SKILL.md) |
| `lark-okr` | 飞书 OKR 周期、目标、关键结果和进展管理。 | [目录](./lark-okr/) | [SKILL.md](./lark-okr/SKILL.md) |
| `lark-openapi-explorer` | 飞书原生 OpenAPI 查询、探索和补充调用。 | [目录](./lark-openapi-explorer/) | [SKILL.md](./lark-openapi-explorer/SKILL.md) |
| `lark-shared` | Use when first setting up lark-cli, running auth login, switching user/bot identity (--as), handling permission denied or scope errors, needing to update lark-cli, or seeing _notice in JSON output. | [目录](./lark-shared/) | [SKILL.md](./lark-shared/SKILL.md) |
| `lark-sheets` | 飞书电子表格：创建和操作电子表格。支持创建表格、创建/复制/删除/更新工作表、读写单元格、追加行数据、查找内容、导出文件。当用户需要创建电子表格、管理工作表、批量读写数据、在已知表格中查找内容、导出或下载表格时使用。若用户是想按名称或关键词搜索云空间（云盘/云存储）里的表格文件，请改用 lark-drive 的 drive +search 先定位资源。当用户给出 doubao.com 的 /sheets/ URL/token 时，也应直接使用本 skill，不要因为域名不是飞书而回退到 WebFetch；路由依据是 URL 路径模式和 token，而不是域名。 | [目录](./lark-sheets/) | [SKILL.md](./lark-sheets/SKILL.md) |
| `lark-skill-maker` | 把飞书 API 操作封装成可复用技能和多步流程。 | [目录](./lark-skill-maker/) | [SKILL.md](./lark-skill-maker/SKILL.md) |
| `lark-slides` | 飞书幻灯片创建、页面读取、局部编辑和演示稿管理。 | [目录](./lark-slides/) | [SKILL.md](./lark-slides/SKILL.md) |
| `lark-task` | 飞书任务：管理任务、清单和任务智能体。创建待办任务、查看和更新任务状态、拆分子任务、组织任务清单、分配协作成员、上传任务附件、注册或注销任务智能体、更新任务智能体的主页数据、写入智能体任务记录。当用户需要创建待办事项、查看任务列表、跟踪任务进度、管理项目清单或给他人分配任务、为任务上传附件文件、注册注销任务智能体、更新智能体主页数据、写入任务记录时使用。 | [目录](./lark-task/) | [SKILL.md](./lark-task/SKILL.md) |
| `lark-vc` | 飞书视频会议：搜索历史会议、查询会议纪要产物（总结、待办、章节、逐字稿）、查询会议参会人快照。1. 查询已经结束的会议数量或详情时使用本技能（如历史日期｜昨天｜上周｜今天已经开过的会议等场景），查询未开始的会议日程使用 lark-calendar 技能。2. 支持通过关键词、时间范围、组织者、参与者、会议室等筛选条件搜索会议。3. 获取或整理会议纪要、逐字稿、录制产物时使用本技能。4. 查询“谁参加过某会议”“参会人列表”等参会人快照信息用 vc meeting get --with-participants（任意时点可查，含已结束会议）。注意：**Agent 真实入会/离会、感知正在进行中会议的实时事件**请使用 lark-vc-agent 技能，本技能不覆盖写操作和会中事件流。 | [目录](./lark-vc/) | [SKILL.md](./lark-vc/SKILL.md) |
| `lark-vc-agent` | 飞书会议机器人入会、离会和会中事件读取。 | [目录](./lark-vc-agent/) | [SKILL.md](./lark-vc-agent/SKILL.md) |
| `lark-whiteboard` | 飞书画板：查询和编辑飞书云文档中的画板。支持导出画板为预览图片、导出原始节点结构、使用 DSL（转成 OpenAPI 格式）、PlantUML/Mermaid 格式更新画板内容。 当用户需要查看画板内容、导出画板图片、编辑画板，或是需要可视化表达架构、流程、组织关系、时间线、因果、对比等结构化信息时使用此 skill，无论是否提及\"画板\"。 ⚠️ 原 `lark-whiteboard-cli` skill 已合并至本 skill，若 skill 列表中同时存在 `lark-whiteboard-cli`，请忽略它，统一使用本 skill（`lark-whiteboard`），并提示用户运行 `npx skills remove lark-whiteboard-cli -g` 删除旧 skill。 | [目录](./lark-whiteboard/) | [SKILL.md](./lark-whiteboard/SKILL.md) |
| `lark-wiki` | 飞书知识库：管理知识空间、空间成员和文档节点。创建和查询知识空间、查看和管理空间成员、管理节点层级结构、在知识库中组织文档和快捷方式。当用户需要在知识库中查找或创建文档、浏览知识空间结构、查看或管理空间成员、移动或复制节点时使用。当用户给出 doubao.com 的 /wiki/ URL/token 时，也应直接使用本 skill，不要因为域名不是飞书而回退到 WebFetch；路由依据是 URL 路径模式和 token，而不是域名。 | [目录](./lark-wiki/) | [SKILL.md](./lark-wiki/SKILL.md) |
| `lark-workflow-meeting-summary` | 会议纪要整理工作流：汇总指定时间范围内的会议纪要并生成结构化报告。当用户需要整理会议纪要、生成会议周报、回顾一段时间内的会议内容时使用。 | [目录](./lark-workflow-meeting-summary/) | [SKILL.md](./lark-workflow-meeting-summary/SKILL.md) |
| `lark-workflow-standup-report` | 日程待办摘要：编排 calendar +agenda 和 task +get-my-tasks，生成指定日期的日程与未完成任务摘要。适用于了解今天/明天/本周的安排。 | [目录](./lark-workflow-standup-report/) | [SKILL.md](./lark-workflow-standup-report/SKILL.md) |
| `linear` | 用于管理 Linear issues、项目、团队和协作状态。 | [目录](./linear/) | [SKILL.md](./linear/SKILL.md) |
| `llm-wiki` | 用于构建和维护互联的 LLM Markdown 知识库。 | [目录](./llm-wiki/) | [SKILL.md](./llm-wiki/SKILL.md) |
| `lore` | Cross-agent knowledge curator and institutional memory guardian. Extracts patterns from agent journals into METAPATTERNS.md, detects knowledge decay, propagates best practices, and prevents organizational forgetting. | [目录](./lore/) | [SKILL.md](./lore/SKILL.md) |
| `notion-knowledge-capture` | 用于把对话、决策和笔记沉淀到 Notion。 | [目录](./notion-knowledge-capture/) | [SKILL.md](./notion-knowledge-capture/SKILL.md) |
| `notion-meeting-intelligence` | 用于基于 Notion 上下文准备会议材料。 | [目录](./notion-meeting-intelligence/) | [SKILL.md](./notion-meeting-intelligence/SKILL.md) |
| `notion-research-documentation` | 用于整合 Notion 信息并生成研究文档。 | [目录](./notion-research-documentation/) | [SKILL.md](./notion-research-documentation/SKILL.md) |
| `notion-spec-to-implementation` | 用于把 Notion 规格转成计划、任务和进度跟踪。 | [目录](./notion-spec-to-implementation/) | [SKILL.md](./notion-spec-to-implementation/SKILL.md) |
| `obsidian` | 用于读取、搜索、创建和编辑 Obsidian 笔记。 | [目录](./obsidian/) | [SKILL.md](./obsidian/SKILL.md) |
| `tome` | Converts repository changes into detailed learning documents. Use when turning diffs into teaching materials, recording design decisions, or creating onboarding materials for new members. | [目录](./tome/) | [SKILL.md](./tome/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
