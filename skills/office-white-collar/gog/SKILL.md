---
name: gog
description: 'Google Workspace 自动化技能，统一处理 Gmail、Calendar、Drive 与 Docs 等办公流程。'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["gog"]'
created_at: "2026-03-15"
updated_at: "2026-03-20"
quality: 4
complexity: "intermediate"
---

# GoG (Google 全家桶)

用于跨 Gmail、日历、Drive、Docs 的一站式办公自动化。GoG 技能将原本孤立的 Google 办公套件通过统一的 Agent 逻辑串联起来，实现真正的“全自动助理”体验。

## 安装

```bash
npx clawhub@latest install gog
```

## 支持能力

- **Gmail**：支持基于关键词、发件人或标签的邮件检索（`search_gmail_messages`），邮件草拟与直接发送（`send_gmail_message`），以及处理附件并存入 Drive。
- **Calendar**：支持读取用户日程（`list_calendar_events`），创建新日程（`create_google_calendar_event`），并能自动处理会议冲突建议。
- **Drive / Docs**：支持在指定目录下创建文件夹或文档（`create_google_drive_file`），并能基于模板自动填充内容（`update_google_docs_content`）。

## 触发条件 / When to Use

- **多任务跨屏流转**：例如“收到某人的邮件后，自动在日历上标记一个 follow-up，并将邮件里的 PDF 存到 Drive 的‘发票’文件夹”。
- **会议智能筹备**：需要根据参会人的可用时间（Free/Busy）自动寻找空档，并向所有人发送 Google Meet 邀请。
- **自动化文档生成**：从 Excel 或数据库（甚至是 Gmail 中的表单反馈）中提取数据，并生成排版美观的 Google Docs 报告或备忘录。
- **批量数据归档**：需要定期清理 Gmail 某标签下的邮件，并将其内容摘要导出为 Google Sheets 或 Docs 存档。
- **快速信息检索**：当用户记不清某个信息在哪（邮件、日历还是文档）时，Agent 可以进行跨平台的全局搜索。

## 核心能力 / Core Capabilities

### 1. 智能邮件分拣与响应 (Gmail Intelligence)
- **操作步骤**：
  1. 使用 `list_gmail_messages` 获取最近的邮件列表。
  2. 结合 LLM 分析邮件的优先级和紧急程度。
  3. 自动生成回复草稿或执行后续流程（如下载附件）。
- **最佳实践**：在进行大规模邮件扫描前，先指定 `q` (query) 参数，例如 `label:unread after:2025/01/01`，以减少 API 调用量和数据噪音。

### 2. 精准日程调度 (Calendar Precision)
- **操作步骤**：
  1. 调用 `list_calendar_events` 检查冲突。
  2. 若存在冲突，主动搜索下一个可用时间点。
  3. 执行 `create_google_calendar_event` 时，确保填写 `description` 和 `attendees`。
- **最佳实践**：为自动创建的任务设置特定的颜色标签（Color ID），方便在网页端一眼识别出是由 Agent 生成的任务。

### 3. 文档全生命周期管理 (Drive & Docs Mastery)
- **操作步骤**：
  1. 建立标准的文件夹目录结构。
  2. 动态生成文件名（如 `[YYYY-MM-DD]_Meeting_Summary`）。
  3. 使用 `mcp_call` 调用 `google_docs` 接口进行流式写入。
- **最佳实践**：处理大文件时，建议先分块处理。在 Drive 查找文件时，优先使用 `name contains 'keyword'` 过滤器。

### 4. 实时响应与监听 (Listener Support)
- **操作步骤**：
  1. 使用 `listen_gmail_reply` 持续关注特定发件人的动态。
  2. 触发后，Agent 自动唤醒并基于最新邮件内容更新 `MEMORY.md`。

## 常用命令/模板 / Common Patterns

### 复杂自动化工作流模板 (Workflow Template)
```markdown
### 目标描述
[例如：自动处理来自 HR 的面试安排邮件]

### 执行逻辑
1. **监听 (Listen)**：等待来自 `hr@example.com` 的邮件。
2. **分析 (Analyze)**：提取邮件中的面试候选人姓名、职位、面试官及意向时间。
3. **核对 (Check)**：使用 `gog:list_calendar_events` 核对面试官当天的日程。
4. **决策 (Decide)**：
   - 如果时间空闲：直接 `create_google_calendar_event` 并发送确认邮件。
   - 如果有冲突：向面试官发送 `question` 询问备选方案，或主动给 HR 回复“正在协商”。
5. **归档 (Archive)**：将候选人的简历 PDF 移动到 Drive 的 `Candidates/[Name]` 目录下。
```

### Gmail 全局搜索示例
```javascript
// 示例：查找包含“发票”且有附件的所有邮件
mcp_call({
  name: 'search_gmail_messages',
  arguments: {
    q: '发票 has:attachment'
  }
});
```

## 进阶应用场景 / Advanced Use Cases

### 1. 自动化项目进度跟踪
- Agent 每天定时检查 Drive 中某个共享文档的更新情况，并根据修改内容自动在 Calendar 中标记“进度评估”任务。

### 2. 差旅智能管家
- 自动从 Gmail 中提取机票和酒店订单信息，一键同步到 Calendar，并创建包含订单详情的 Docs 旅行手册。

## 边界与限制 / Boundaries

- **认证有效期**：Google OAuth Token 具有有效期，过期后需通过 `composio_connect_app` 或相关指令重新扫码授权。
- **存储配额**：Drive 存储空间受限，Agent 在上传大文件前需检查可用余额。
- **API 速率限制 (Rate Limiting)**：短时间内进行成百上千次的邮件搜索或日程创建可能触发 Google 的反爬或频控机制。
- **隐私保护原则**：Agent 只能读取用户授权的 Scope。除非明确要求，不得扫描用户的私密邮件内容或非工作相关的个人文件夹。
- **数据一致性**：在高并发操作（如多人协作编辑同一个 Doc）时，需防范内容覆盖冲突。

## 最佳实践总结

1. **精准过滤**：搜索时永远带上日期和标签（Label），减少无关数据的解析。
2. **两阶段提交**：对于删除邮件或修改核心日程的操作，始终先生成 `preview` 给用户，再执行真正的 `commit`。
3. **结构化存储**：不要将所有文件扔在根目录，建立按月、按项目分类的文件夹。
4. **错误处理**：考虑到网络波动，为所有的 Google API 调用增加 `retry` 逻辑。
5. **记忆同步**：重要的日历事项完成后，应同步到 `MEMORY.md` 供长期参考。
