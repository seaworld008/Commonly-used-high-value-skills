---
name: summarize
description: '对网页、文档、邮件与长文本进行快速摘要，提炼核心信息。'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["summarize"]'
created_at: "2026-03-15"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
---

# Summarize

用于信息过载场景下的快速理解与要点抽取。Summarize 技能通过强大的语义提取算法，能够将冗长的文档、复杂的网页或散乱的邮件链条一键浓缩为结构化、可阅读性极强的摘要报告。它不仅是阅读助手，更是辅助决策的知识过滤器。

## 安装

```bash
npx clawhub@latest install summarize
```

## 支持内容

- **网页与长文本**：支持通过 URL 抓取正文并去除广告噪音。
- **Office / PDF 文档**：支持 `.docx`, `.xlsx`, `.pptx` 以及各种排版的 PDF 文件。
- **邮件内容**：支持多轮往返邮件的逻辑梳理。
- **音视频字幕**：可结合 OCR（光学字符识别）或 `transcribe` 技能进行二次提炼。
- **代码库文档**：快速从 `README.md` 或源码注释中提取核心架构信息。

## 触发条件 / When to Use

- **快速预读 (Pre-reading)**：面对几十页的行业研报，先花 30 秒看一眼摘要决定是否精读。
- **会议要点归纳 (Meeting Minutes)**：基于转录的原始录音文字，自动生成待办事项（Action Items）。
- **竞争情报追踪**：每天抓取竞争对手的官宣稿件，快速汇总其产品迭代动向。
- **邮件回复辅助**：在长达 20 封的回复链条中，快速理清目前的最终共识是什么。
- **社交媒体情报提取**：从 Twitter、Reddit 或知乎的长贴中提取核心论点和用户情绪趋势。
- **法律/技术协议解读**：从枯燥的 EULA 或 API 说明中提取关键约束条件和资费变动。

## 核心能力 / Core Capabilities

### 1. 多层级分段摘要 (Multi-level Summarization)
- **操作步骤**：
  1. 调用 `read` 或 `web_fetch` 获取原文。
  2. 使用“分治法”（Map-Reduce）处理超长文本：先分段摘要，再进行全局融合。
  3. 提供 `TL;DR` (一句话简介)、`Key Points` (3-5 个核心点) 以及 `Deep Dive` (逻辑脉络梳理)。
- **最佳实践**：为不同身份的用户（如高管 vs 研发）定制不同视角的摘要模板。

### 2. 结构化实体提取 (Entity Extraction)
- **操作步骤**：
  1. 在摘要过程中，自动识别：人物 (Person)、机构 (Organization)、日期 (Date)、金额 (Money) 以及 技术术语 (Tech Stack)。
  2. 将这些实体以 JSON 或表格形式单独列出，方便导入数据库或 Notion。
- **最佳实践**：结合 `memory_search` 检查提取的实体是否已经在历史知识库中。

### 3. 意图与情感分析 (Sentiment & Intent)
- **操作步骤**：
  1. 判断文本的主观性倾向（褒义/贬义/中性）。
  2. 提取隐藏在文字背后的显式要求（如“请在周五前回信”）。
- **最佳实践**：在摘要头部用图标标出文档的“紧急程度”和“风险等级”。

### 4. 跨语言翻译与润色 (Cross-lingual Refining)
- **操作步骤**：
  1. 将外文资料直接翻译为目标语言（如中英互转）。
  2. 调整摘要的语气（正式/幽默/学术）。

## 常用命令/模板 / Common Patterns

### 行业研报摘要模板 (Report Summary Template)
```markdown
### 📄 文档概览
- **标题**: [输入标题]
- **来源**: [URL/文件名]
- **核心结论**: [一句话总结全文最具价值的洞察]

### 💡 核心要点 (Key Insights)
- **[要点 1]**: 描述详细的事实背景及数据支持。
- **[要点 2]**: 描述详细的事实背景及数据支持。
- **[要点 3]**: 描述详细的事实背景及数据支持。

### 📊 关键数据 (Metrics)
- **增长率**: [XX%]
- **市场规模**: [$XXX]
- **竞争对手**: [A, B, C]

### ✅ 待办建议 (Next Steps)
- [ ] 建议行动 A
- [ ] 建议行动 B

### 🚩 风险提示
- [潜在风险点 1]
```

### 快速摘要命令示例
```javascript
// 示例：对当前打开的网页进行深度摘要
mcp_call({
  name: 'summarize_content',
  arguments: {
    source_url: "https://techcrunch.com/article/123",
    detail_level: "advanced",
    focus: "technical_innovations"
  }
});
```

## 进阶应用场景 / Advanced Use Cases

### 1. 自动化每日情报墙
- 结合 `tavily-search` 技能，Agent 每天抓取 20 个相关网页。Summarize 技能将这 20 个网页融合成一张“情报大盘”，展示在用户的 Dashboard 上。

### 2. 播客/视频“跳着听”
- 从 Youtube 获取字幕，Summarize 技能自动标注视频的“高光时刻”时间戳，让用户只需观看关键的 3 分钟。

## 边界与限制 / Boundaries

- **幻觉风险 (Hallucination)**：对于高度专业化的文档（如前沿数学论文），Agent 可能理解错误导致摘要失准。
- **输入长度限制**：虽然支持长文本，但一次性向大模型发送超过 128k Token 的内容可能导致严重的性能下降或上下文截断。
- **格式解析失败**：加密的 PDF、纯图片的扫描件（未 OCR）或复杂的嵌套表格可能导致解析不完整。
- **隐私合规**：处理包含敏感个人信息（PII）的文档时，应先进行脱敏处理。
- **版权尊重**：摘要内容应遵循 Fair Use 原则，不应直接复制原文大段文字以规避侵权。

## 最佳实践总结

1. **先看目录**：对于大文档，先摘要其目录，由用户指定感兴趣的章节再进行深入摘要。
2. **事实核查**：在摘要中遇到具体数字时，Agent 应主动通过 `see_image` 或 `fact-checker` 技能进行二次验证。
3. **记忆化存储**：所有的摘要记录应存入 `MEMORY.md`，实现“读过即拥有”。
4. **视觉辅助**：利用 `mermaid-tools` 技能，将摘要中的逻辑关系转化为流程图。
5. **增量摘要**：对于每日更新的文档（如项目日志），只摘要相比昨天的“新增变动”。
