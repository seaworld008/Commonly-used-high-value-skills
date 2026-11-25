---
name: lark-skill-maker
description: 'Use when creating reusable skills around verified Lark CLI or OpenAPI operations, including scoped permissions and multi-step workflow contracts.'
zh_description: "用于把飞书 API 操作封装为可复用技能、流程模板和多步自动化。"
version: "1.0.8"
author: larksuite
source: "github:larksuite/cli"
source_url: "https://github.com/larksuite/cli/tree/7beffb086d7fa3c5b843d8affa7c089f49cfc65e/skills/lark-skill-maker"
license: MIT
tags: [feishu, lark, lark-cli, skills, agent-workflow]
created_at: "2026-05-19"
updated_at: "2026-11-25"
quality: 3
complexity: intermediate
metadata:
  requires:
    bins: ["lark-cli"]
---

# Skill Maker

基于 lark-cli 创建新 Skill。Skill = 一份 `SKILL.md`，教 AI 用 CLI 命令完成任务。

## CLI 核心能力

```bash
lark-cli <service> <resource> <method>          # 已注册 API
lark-cli <service> +<verb>                      # Shortcut（高级封装）
lark-cli api <METHOD> <path> [--data/--params]  # 任意飞书 OpenAPI
lark-cli schema <service.resource.method>       # 查参数定义
```

优先级：Shortcut > 已注册 API > `api` 裸调。

## 调研 API

```bash
# 1. 查看已有的 API 资源和 Shortcut
lark-cli <service> --help

# 2. 查参数定义
lark-cli schema <service.resource.method>

# 3. 未注册的 API，用 api 直接调用
lark-cli api GET /open-apis/vc/v1/rooms --params '{"page_size":"50"}'
lark-cli api POST /open-apis/vc/v1/rooms/search --data '{"query":"5F"}'
```

如果以上命令无法覆盖需求（CLI 没有对应的已注册 API 或 Shortcut），使用 [lark-openapi-explorer](../lark-openapi-explorer/SKILL.md) 从飞书官方文档库逐层挖掘原生 OpenAPI 接口，获取完整的方法、路径、参数和权限信息，再通过 `lark-cli api` 裸调完成任务。

通过以上流程确定需要哪些 API、参数和 scope。

## SKILL.md 模板

生成到用户指定的目标技能包，并遵循该宿主布局。在本仓库使用 `skills/<category>/lark-<name>/SKILL.md`，保留以下完整 frontmatter，另按仓库 provenance 规则登记已核实来源。其他宿主不强制采用本库目录。模板中的值须按新技能事实填写：

```markdown
---
name: lark-<name>
version: "1.0.0"
description: "<主要任务>。当用户需要<触发场景>时使用。"
zh_description: "<简明中文用途>"
author: "<实际作者>"
source: "<已核实来源或 in-house>"
source_url: "<来源链接；原创可为空>"
license: "<经审阅的适用许可证>"
tags: [lark, "<领域标签>"]
quality: 2
created_at: "<YYYY-MM-DD>"
updated_at: "<YYYY-MM-DD>"
metadata:
  requires:
    bins: ["lark-cli"]
---


# <标题>

> **前置条件：** 按目标包布局链接 `lark-shared`；同类别兄弟目录可用 `../lark-shared/SKILL.md`，跨类别时重新计算相对路径。

## 命令

\```bash
# 单步操作
lark-cli api POST /open-apis/xxx --data '{...}'

# 多步编排：说明步骤间数据传递
# Step 1: ...（记录返回的 xxx_id）
# Step 2: 使用 Step 1 的 xxx_id
\```

## 权限

| 操作 | 所需 scope |
|------|-----------|
| xxx | `scope:name` |
```

## 关键原则

- **description 决定触发** — 包含功能关键词 + "当用户需要...时使用"
- **认证** — 说明所需 scope，登录用 `lark-cli auth login --domain <name>`
- **安全** — 写入操作前确认用户意图，建议 `--dry-run` 预览
- **编排** — 说明数据传递、失败回滚、可并行步骤

<!-- LOCAL-CURATION-SUPPLEMENT:START -->
## 端到端构建示例 / End-to-End Skill Authoring Example

以下示例展示如何把「查询会议室空闲时段并创建日程」从 OpenAPI 调研一步步封装为可审计、带 `--dry-run` 门控的新飞书技能：

```bash
# 1. 查看 calendar 与 vc 服务已封装命令，优先复用 Shortcut
lark-cli calendar --help
lark-cli vc --help

# 2. 对裸调接口先查询字段与必填参数 Schema
lark-cli schema vc.v1.room.search
lark-cli schema calendar.v4.calendar_event.create

# 3. 串联只读检索 -> 用户确认 -> 带 --dry-run 预览的写入操作
# Step A (Read-Only): 按楼层搜索会议室并记录 room_id / open_chat_id
lark-cli api POST /open-apis/vc/v1/rooms/search \
  --data '{"keyword":"5F-A"}' --as user

# Step B (Preview / Confirmation): 创建日程前先校验时间区间与参与人 open_id，支持 --dry-run 预演
lark-cli calendar +create \
  --summary 'Architecture Review' \
  --start '2026-11-24T10:00:00+08:00' \
  --end '2026-11-24T11:00:00+08:00' \
  --attendee-ids 'ou_example_target' \
  --dry-run --as user
```

### 交付前本地检查清单

- 新技能写入仓库后，确认 frontmatter 含完整 `name`、`description`、`zh_description`、`version`、`tags`、`quality`、`source`。
- 在目标技能内明确标注所需的最小飞书 scope（例如 `calendar:calendar`、`vc:room:readonly`）以及失败码（如 `41050`、限流重试）的降级策略。
- 涉及外部数据源时，同步在 `docs/sources/` 登记来源与许可证，并运行 `python scripts/lint_skill_quality.py --strict` 与 `python scripts/check_skill_references.py` 验证引用可达性。
<!-- LOCAL-CURATION-SUPPLEMENT:END -->
