---
name: internal-comms
description: 'A set of resources to help me write all kinds of internal communications, using the formats that my company likes to use. Claude should use this skill whenever asked to write some sort of internal communications (status reports, leadership updates, 3P updates, company newsletters, FAQs, incident reports, project updates, etc.).'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
license: Complete terms in LICENSE.txt
tags: '["comms", "internal", "productivity"]'
created_at: "2026-03-04"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
---

# Internal Communications Expert

内部沟通专家技能旨在帮助 Agent 以专业、得体、符合企业文化且极具影响力的格式编写各类内部通知。无论是向高层汇报进度、跨部门同步风险，还是在 Slack/Teams 中发布日常更新，本技能都能确保信息的清晰度与行动指向性。

## When to use this skill

当用户需要编写以下任何形式的内部沟通内容时，应优先激活本技能：

- **3P 更新 (Progress, Plans, Problems)**：团队每周/双周的标准同步格式。
- **公司简报 (Company Newsletters)**：面向全公司的月度或季度大事件汇总。
- **FAQ 响应 (FAQ Responses)**：针对新流程、新制度的常见问题解答。
- **状态报告 (Status Reports)**：项目关键里程碑、资源消耗及风险评估。
- **领导层更新 (Leadership Updates)**：高颗粒度、结果导向的极简汇报，供高层快速决策。
- **故障回顾报告 (Incident Reports / Post-mortems)**：针对线上事故的根因分析及后续补救。
- **项目同步 (Project Updates)**：特定职能组或跨职能任务组的日常对齐。

## How to use this skill

1. **识别沟通类型 (Identify Type)**：从用户请求中判断属于哪种模板。
2. **加载规范文件 (Load Guidelines)**：从 `examples/` 目录读取相应的参考：
    - `examples/3p-updates.md` - 适用于 Progress/Plans/Problems 团队同步。
    - `examples/company-newsletter.md` - 适用于全公司范围的公告。
    - `examples/faq-answers.md` - 适用于解答常见问题。
    - `examples/leadership-concise.md` - 适用于向 VP/CEO 汇报（极简风格）。
    - `examples/incident-report-template.md` - 适用于 SRE/研发事故复盘。
    - `examples/general-comms.md` - 适用于不匹配以上任何分类的一般沟通。
3. **遵循格式与语气指令 (Follow Tone/Format)**：根据文件中的说明，调整语气（如专业、鼓舞人心或严谨）。

## 触发条件 / When to Use

- **关键节点达成**：项目完成 50% 或完成部署。
- **预警信号出现**：项目可能延期，需要跨部门求助。
- **知识沉淀需求**：新员工入职，需要编写 FAQ。
- **组织变革通知**：部门重组或新流程上线。
- **定期复盘习惯**：周五下午的 3P 总结。

## 核心能力 / Core Capabilities

### 1. 受众敏感性分析 (Audience Sensitivity)
- **操作步骤**：
  1. 分析“谁是我的读者？”（高层、同级、初级员工）。
  2. 调整专业术语的密集度（高层少用缩写，研发多用具体参数）。
  3. 切换关注点（高层关注 ROI/风险，同级关注接口/依赖，初级关注执行步骤）。
- **最佳实践**：在初稿生成后，询问用户：“这封邮件是发给技术团队还是非技术管理层的？”

### 2. 事实提取与逻辑重构 (Fact Extraction)
- **操作步骤**：
  1. 调用 `memory_search` 提取过去一周的 `task_list` 完成情况。
  2. 过滤掉琐碎的琐事（Noise），保留对业务有影响的大事件（Impactful Events）。
  3. 按照“结论先行 -> 数据支持 -> 明确诉求”的逻辑重新排版。
- **最佳实践**：使用“三段论”：We Did X, The Result Was Y, Next We Will Do Z.

### 3. 敏感信息脱敏与风险规避 (Information Safety)
- **操作步骤**：
  1. 识别并标记文本中的敏感信息（如具体的合同金额、PII、尚未公开的战略）。
  2. 提供“公开版”和“内部版”两个版本的文案建议。
- **最佳实践**：遵循公司的数据安全白皮书，严禁在外部 Comms 中提及内部系统的未公开漏洞。

### 4. 行动导向设计 (Call-to-Action)
- **操作步骤**：
  1. 在结尾处清晰标注：Who needs to do What by When?
  2. 使用加粗字体突出具体的反馈截止时间。

## 常用命令/模板 / Common Patterns

### 3P 每周更新模板 (3P Weekly Template)
```markdown
### 🗓️ [团队名] 每周 3P 更新 (2026-03-27)

#### ✅ Progress (进展)
- **[项目 A]**: 已完成 V1.2 发布，灰度测试通过率 99.8%。
- **[人才招聘]**: 完成 3 轮面试，1 名后端专家已确认 Offer。

#### 📅 Plans (计划)
- **[核心重构]**: 下周启动数据库分表方案的压测。
- **[OKRs]**: 进行 Q2 OKR 的初稿评审。

#### ⚠️ Problems (风险/问题)
- **[资源瓶颈]**: 设计资源排期紧张，可能影响项目 B 的 UI 交付进度。
- **[外部依赖]**: 第三方支付网关 API 波动，正在寻求备选方案。

---
*Next Checkpoint: 下周二晨会*
```

### 极简领导层汇报示例 (Leadership Update)
```markdown
### [主题]：项目 X 进度快报

**当前状态**：🟢 正常
**核心指标**：本周活跃用户增长 15%。
**顶层决策点**：我们已通过技术方案评审，不需要额外预算，但需要法务部加速审批合约 Y。
```

## 进阶应用场景 / Advanced Use Cases

### 1. 自动化“坏消息”预警
- 当 Agent 检测到 `task_list` 中有多个任务延期超过 2 天时，自动调用 `internal-comms` 生成一份“项目延期预警邮件”草稿，并提出补救措施。

### 2. 跨时区团队同步
- 为在不同时区工作的同事生成“接力”说明文档，清晰标记目前的上下文和留待解决的问题。

## 边界与限制 / Boundaries

- **真实性责任**：Agent 只能基于它所能获取到的 `tasks` 或 `memory` 进行总结，无法代表人类的真实情感或主观判断。
- **文化差异风险**：不同公司的沟通风格（如硅谷风格 vs 传统德企）差异极大，建议在初次使用前让用户上传一份“样本文档”。
- **越权风险**：Agent 不得在未经授权的情况下，代用户直接发送涉及核心决策或人事变动的全局公告。
- **幻觉校对**：生成的百分比或日期必须由用户进行最终复核，以防大模型产生数字偏移。

## 最佳实践总结

1. **结构胜过文笔**：内部沟通的首要目标是提高信息获取效率。
2. **多用列表，少用长句**：让忙碌的同事能在一秒内扫视出核心观点。
3. **数据驱动**：尽可能在 Progress 中加入量化指标。
4. **保持客观**：在 Incident Report 中，只描述事实，不寻找“替罪羊”。
5. **记忆同步**：发送完成后，将核心沟通结论同步回 `MEMORY.md`。
