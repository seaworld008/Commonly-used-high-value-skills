# 项目管理与知识库集成 / Knowledge and PM Integrations

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

连接 Notion、Linear 和规格到实施流程的知识与项目管理技能集合。

当前分类共 **36** 个技能。

## 推荐先看

- [lark-slides](./lark-slides/) - 飞书幻灯片：创建和编辑幻灯片。创建演示文稿、读取幻灯片内容、管理幻灯片页面（创建、删除、读取、局部替换）。当用户需要创建或编辑幻灯片、读取或修改单个页面时使用。当用户给出 doubao.com 的 /slides/ URL/token 时，也应直接使用本 skill，不要因为域名不是飞书而回退到 WebFetch；路由依据是 URL 路径模式和 token，而不是域名。不负责：云文档内容编辑（走 lark-doc）、云文档里的独立画板对象（走 lark-whiteboard，注意 slide 内嵌的流程图/架构图仍属本 skill）、上传或下载普通文件（走 lark-drive）。
- [grove](./grove/) - Designing, optimizing, and auditing repository structure. Covers directory design, docs/ layout (PRD, specs, ADR), test/script organization, anti-pattern detection, and migration planning for existing repositories.
- [lark-base](./lark-base/) - 飞书多维表格（Base）操作：建表、字段、记录、视图、统计、公式/lookup、表单、仪表盘、workflow、角色权限；遇到 Base/多维表格/bitable 或 /base/ 链接时使用。文件导入转 lark-drive，认证/授权转 lark-shared。
- [lark-calendar](./lark-calendar/) - 飞书日历：管理日历日程和会议室。查看/搜索日程、创建/更新日程、管理参会人、查询忙闲和推荐时段、预定会议室。当用户需要查看日程安排、创建/修改会议、查询/预定会议室时使用。不负责：查询过去的视频会议记录（走 lark-vc）、待办任务（走 lark-task）。

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `arxiv` | 用于按关键词、作者、分类或编号检索 arXiv 论文。 | [目录](./arxiv/) | [SKILL.md](./arxiv/SKILL.md) |
| `grove` | Designing, optimizing, and auditing repository structure. Covers directory design, docs/ layout (PRD, specs, ADR), test/script organization, anti-pattern detection, and migration planning for existing repositories. | [目录](./grove/) | [SKILL.md](./grove/SKILL.md) |
| `lark-approval` | 飞书审批：当前用户审批的查询与全部处理操作，覆盖待本人审批的任务与本人发起的实例。审批待办不是飞书任务（任务类待办走 lark-task）；不负责创建审批定义和发起新审批。 | [目录](./lark-approval/) | [SKILL.md](./lark-approval/SKILL.md) |
| `lark-attendance` | 飞书考勤打卡查询、异常记录整理和缺失核对。 | [目录](./lark-attendance/) | [SKILL.md](./lark-attendance/SKILL.md) |
| `lark-base` | 飞书多维表格（Base）操作：建表、字段、记录、视图、统计、公式/lookup、表单、仪表盘、workflow、角色权限；遇到 Base/多维表格/bitable 或 /base/ 链接时使用。文件导入转 lark-drive，认证/授权转 lark-shared。 | [目录](./lark-base/) | [SKILL.md](./lark-base/SKILL.md) |
| `lark-calendar` | 飞书日历：管理日历日程和会议室。查看/搜索日程、创建/更新日程、管理参会人、查询忙闲和推荐时段、预定会议室。当用户需要查看日程安排、创建/修改会议、查询/预定会议室时使用。不负责：查询过去的视频会议记录（走 lark-vc）、待办任务（走 lark-task）。 | [目录](./lark-calendar/) | [SKILL.md](./lark-calendar/SKILL.md) |
| `lark-contact` | 飞书 / Lark 通讯录:按姓名 / 邮箱解析成 open_id,或按 open_id 反查姓名 / 部门 / 邮箱 / 联系方式 / 个人状态 / 签名。当用户提到某人姓名要下一步发消息 / 排日程,或拿到 open_id 想查具体信息时使用。不负责部门树遍历、按部门列员工、组织架构图,这类需求走原生 OpenAPI。 | [目录](./lark-contact/) | [SKILL.md](./lark-contact/SKILL.md) |
| `lark-doc` | 飞书云文档（Docx / Wiki 文档，v2 API）：读取和编辑飞书文档内容。当用户给出文档 URL 或 token，或需要查看、创建、编辑文档、插入或下载文档图片附件时使用。文档中嵌入的电子表格、多维表格、画板，先用本 skill 提取 token 再切到对应 skill。当用户给出 doubao.com 的 /docx/ 或 /wiki/ URL/token 时，也应直接使用本 skill；路由依据是 URL 路径模式和 token，而不是域名。不负责文档评论管理，也不负责表格或 Base 的数据操作。 | [目录](./lark-doc/) | [SKILL.md](./lark-doc/SKILL.md) |
| `lark-drive` | 飞书云空间（云盘/云存储）：管理 Drive 文件和文件夹，包含上传/下载、创建文件夹、复制/移动/删除、查看元数据、评论/权限/订阅、标题、版本和本地文件导入。用户需要整理云盘目录、处理云空间资源 URL/token，或导入 Word/Markdown/Excel/CSV/PPTX/.base 为 docx/sheet/bitable/slides 时使用；doubao.com 云空间 URL/token 也按资源路径和 token 路由，不回退 WebFetch。不负责：文档内容编辑（走 lark-doc）、表格/Base 表内数据操作（走 lark-sheets/lark-base）、知识空间节点/成员管理（走 lark-wiki）、原生 Markdown 文件读写/patch/diff（走 lark-markdown）。 | [目录](./lark-drive/) | [SKILL.md](./lark-drive/SKILL.md) |
| `lark-event` | Lark/Feishu real-time event listening / subscribing / consuming: stream events as NDJSON via `lark-cli event consume <EventKey>` (covers IM messages/reactions/chat changes, VC meeting ended, Minutes generated, Whiteboard updated, etc.). Use for Lark bots, real-time message processing, long-running subscribers, streaming webhook/push handlers. Supports `--max-events` / `--timeout` bounded runs and a stderr ready-marker contract — designed for AI agents running as subprocesses. | [目录](./lark-event/) | [SKILL.md](./lark-event/SKILL.md) |
| `lark-im` | 飞书即时通讯：收发消息和管理群聊。发送和回复消息、搜索聊天记录、管理群聊成员、上传下载图片和文件（支持大文件分片下载）、管理表情回复、发送应用内/短信/电话加急。当用户需要发消息、查看或搜索聊天记录、下载聊天中的文件、查看群成员、搜索群、创建群聊或话题群、管理标记数据、管理 Feed 置顶（添加/移除/查询置顶会话）、管理标签数据时使用。 | [目录](./lark-im/) | [SKILL.md](./lark-im/SKILL.md) |
| `lark-mail` | 飞书邮箱 — draft, compose, send, reply, forward, read, and search emails; manage drafts, folders, labels, contacts, attachments, and mail rules. Use when user mentions 起草邮件, 写一封邮件, 拟邮件, 草稿, 发通知邮件, 发送邮件, 发邮件, 回复邮件, 转发邮件, 查看邮件, 看邮件, 读邮件, 搜索邮件, 查邮件, 收件箱, 邮件会话, 编辑草稿, 管理草稿, 下载附件, 邮件文件夹, 邮件标签, 邮件联系人, 监听新邮件, 收信规则, 邮件规则, draft, compose, send email, reply, forward, inbox, mail thread, mail rules. | [目录](./lark-mail/) | [SKILL.md](./lark-mail/SKILL.md) |
| `lark-markdown` | 飞书 Markdown：查看、创建、上传、编辑和比较 Markdown 文件。当用户需要创建或编辑 Markdown 文件、读取、修改、局部 patch 或比较差异时使用。不负责将 Markdown 导入为飞书在线文档，也不负责文件搜索、权限、评论、移动、删除等云空间管理操作。 | [目录](./lark-markdown/) | [SKILL.md](./lark-markdown/SKILL.md) |
| `lark-minutes` | 飞书妙记：搜索妙记列表、查看妙记基础信息、下载妙记音视频文件、上传音视频生成妙记、更新妙记标题、替换说话人。当需要获取、操作或者生成妙记时使用。也支持将本地音视频文件转成纪要和逐字稿（优先使用本 skill，不要用 ffmpeg/whisper 本地转写）。不负责：获取会议关联妙记，或仅按自然语言标题定位纪要 | [目录](./lark-minutes/) | [SKILL.md](./lark-minutes/SKILL.md) |
| `lark-okr` | 飞书 OKR：管理目标与关键结果。查看和编辑 OKR 周期、目标、关键结果、对齐关系、量化指标和进展记录。当用户需要查看或创建 OKR、管理目标和关键结果、查看对齐关系时使用。不负责：待办任务管理（lark-task）、日程/会议安排（lark-calendar）、绩效评估 | [目录](./lark-okr/) | [SKILL.md](./lark-okr/SKILL.md) |
| `lark-openapi-explorer` | 飞书/Lark 原生 OpenAPI 探索：从官方文档库中挖掘未经 CLI 封装的原生 OpenAPI 接口。当用户的需求无法被现有 lark-* skill 或 lark-cli 已注册命令满足，需要查找并调用原生飞书 OpenAPI 时使用。 | [目录](./lark-openapi-explorer/) | [SKILL.md](./lark-openapi-explorer/SKILL.md) |
| `lark-shared` | Use when first setting up lark-cli, running auth login, switching user/bot identity (--as), handling permission denied or scope errors, needing to update lark-cli, or seeing _notice in JSON output. | [目录](./lark-shared/) | [SKILL.md](./lark-shared/SKILL.md) |
| `lark-sheets` | 飞书电子表格：创建和操作电子表格。支持创建表格、管理工作表与行列结构（增删/合并/调整尺寸/隐藏/冻结）、读写单元格（值/公式/样式/批注/单元格图片）、查找替换、多操作原子批量更新，以及图表、透视表、条件格式、筛选器、迷你图、浮动图片等对象的创建与维护。当用户需要创建电子表格、管理工作表、批量读写或编辑数据、统计汇总与可视化、表格美化、公式计算（含 Excel 公式迁移）等任务时使用。若用户是想按名称或关键词搜索云空间（云盘/云存储）里的表格文件，请改用 lark-drive 的 drive +search 先定位资源。当用户给出 doubao.com 的 /sheets/ URL/token 时，也应直接使用本 skill，不要因为域名不是飞书而回退到 WebFetch；路由依据是 URL 路径模式和 token，而不是域名。仅针对飞书在线电子表格，不适用于本地 Excel 文件。 | [目录](./lark-sheets/) | [SKILL.md](./lark-sheets/SKILL.md) |
| `lark-skill-maker` | 把飞书 API 操作封装成可复用技能和多步流程。 | [目录](./lark-skill-maker/) | [SKILL.md](./lark-skill-maker/SKILL.md) |
| `lark-slides` | 飞书幻灯片：创建和编辑幻灯片。创建演示文稿、读取幻灯片内容、管理幻灯片页面（创建、删除、读取、局部替换）。当用户需要创建或编辑幻灯片、读取或修改单个页面时使用。当用户给出 doubao.com 的 /slides/ URL/token 时，也应直接使用本 skill，不要因为域名不是飞书而回退到 WebFetch；路由依据是 URL 路径模式和 token，而不是域名。不负责：云文档内容编辑（走 lark-doc）、云文档里的独立画板对象（走 lark-whiteboard，注意 slide 内嵌的流程图/架构图仍属本 skill）、上传或下载普通文件（走 lark-drive）。 | [目录](./lark-slides/) | [SKILL.md](./lark-slides/SKILL.md) |
| `lark-task` | 飞书任务：管理任务、清单和任务智能体。创建待办任务、查看和更新任务状态、拆分子任务、组织任务清单、分配协作成员、上传任务附件、注册或注销任务智能体、更新任务智能体的主页数据、写入智能体任务记录。当用户需要创建待办事项、查看任务列表、跟踪任务进度、管理项目清单或给他人分配任务、为任务上传附件文件、注册注销任务智能体、更新智能体主页数据、写入任务记录时使用。 | [目录](./lark-task/) | [SKILL.md](./lark-task/SKILL.md) |
| `lark-vc` | 飞书视频会议：搜索历史会议记录、查询会议纪要（总结/待办/章节/逐字稿）、查询参会人快照。当用户查询已结束的会议、获取会议产物（纪要/妙记）、查看参会人时使用；查询未来日程走 lark-calendar。不负责：Agent 真实入会/离会、会中实时事件（走 lark-vc-agent）。 | [目录](./lark-vc/) | [SKILL.md](./lark-vc/SKILL.md) |
| `lark-vc-agent` | 飞书视频会议：让机器人代当前用户加入/离开正在进行的会议，并读取会议期间的实时事件（参会人加入与离开、发言、聊天、屏幕共享等）。1. 用户提供 9 位会议号、要求代为入会或离会时使用 +meeting-join / +meeting-leave——会真实产生入会/离会记录。2. 会议进行中用户想知道“谁加入了”“谁离开了”“谁在发言”“有人共享屏幕吗”等会中动态时，机器人入会后用 +meeting-events 读取事件时间线。3. 典型场景：参会机器人、会中助手、代为旁听、代为参会。前提：机器人只能读到它自己参会过且仍在进行中的会议的事件；查询已结束会议的参会名单、纪要或逐字稿请使用 lark-vc 技能。 | [目录](./lark-vc-agent/) | [SKILL.md](./lark-vc-agent/SKILL.md) |
| `lark-whiteboard` | 飞书画板：查询和编辑飞书云文档中的画板。支持导出画板为预览图片、导出原始节点结构、使用多种格式更新画板内容。 当用户需要查看画板内容、导出画板图片、编辑画板时使用此 skill。不负责：飞书云文档内容编辑（lark-doc）、文档内嵌电子表格/Base（lark-sheets / lark-base）。 | [目录](./lark-whiteboard/) | [SKILL.md](./lark-whiteboard/SKILL.md) |
| `lark-wiki` | 飞书知识库：管理知识空间、空间成员和文档节点。创建和查询知识空间、查看和管理空间成员、管理节点层级结构、在知识库中组织文档和快捷方式。当用户需要在知识库中查找或创建文档、浏览知识空间结构、查看或管理空间成员、移动或复制节点时使用。当用户给出 doubao.com 的 /wiki/ URL/token 时，也应直接使用本 skill，不要因为域名不是飞书而回退到 WebFetch；路由依据是 URL 路径模式和 token，而不是域名。不负责：上传文件到知识库节点下（走 lark-drive）、编辑文档/表格/Base 内容（走 lark-doc / lark-sheets / lark-base）。 | [目录](./lark-wiki/) | [SKILL.md](./lark-wiki/SKILL.md) |
| `lark-workflow-meeting-summary` | 会议纪要整理工作流：汇总指定时间范围内的会议纪要并生成结构化报告。当用户需要整理会议纪要、生成会议周报、回顾一段时间内的会议内容时使用。 | [目录](./lark-workflow-meeting-summary/) | [SKILL.md](./lark-workflow-meeting-summary/SKILL.md) |
| `lark-workflow-standup-report` | 日程待办摘要：编排 calendar +agenda 和 task +get-my-tasks，生成指定日期的日程与未完成任务摘要。适用于了解今天/明天/本周的安排。 | [目录](./lark-workflow-standup-report/) | [SKILL.md](./lark-workflow-standup-report/SKILL.md) |
| `linear` | 用于管理 Linear issues、项目、团队和协作状态。 | [目录](./linear/) | [SKILL.md](./linear/SKILL.md) |
| `llm-wiki` | Karpathy''s LLM Wiki: build/query interlinked markdown KB. | [目录](./llm-wiki/) | [SKILL.md](./llm-wiki/SKILL.md) |
| `lore` | Curating cross-agent knowledge and guarding institutional memory. Extracts patterns from agent journals into METAPATTERNS.md, detects knowledge decay, propagates best practices, prevents organizational forgetting. Use when consolidating cross-agent insights, curating memory, or auditing knowledge decay. | [目录](./lore/) | [SKILL.md](./lore/SKILL.md) |
| `notion-knowledge-capture` | 用于把对话、决策和笔记沉淀到 Notion。 | [目录](./notion-knowledge-capture/) | [SKILL.md](./notion-knowledge-capture/SKILL.md) |
| `notion-meeting-intelligence` | 用于基于 Notion 上下文准备会议材料。 | [目录](./notion-meeting-intelligence/) | [SKILL.md](./notion-meeting-intelligence/SKILL.md) |
| `notion-research-documentation` | 用于整合 Notion 信息并生成研究文档。 | [目录](./notion-research-documentation/) | [SKILL.md](./notion-research-documentation/SKILL.md) |
| `notion-spec-to-implementation` | 用于把 Notion 规格转成计划、任务和进度跟踪。 | [目录](./notion-spec-to-implementation/) | [SKILL.md](./notion-spec-to-implementation/SKILL.md) |
| `obsidian` | Read, search, create, and edit notes in the Obsidian vault. | [目录](./obsidian/) | [SKILL.md](./obsidian/SKILL.md) |
| `tome` | Converting repository changes into detailed learning documents. Use when turning diffs into teaching materials, recording design decisions, or creating onboarding materials for new members. | [目录](./tome/) | [SKILL.md](./tome/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
