---
name: tavily-search
description: '提供实时联网检索能力，帮助 Agent 获取最新资讯、数据与来源证据。'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["planning", "search", "tavily", "workflow"]'
created_at: "2026-03-15"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
---

# Tavily Web Search

当任务依赖 **最新信息**（新闻、市场数据、动态变化文档）时，必须优先使用本技能。Tavily Search 专为 AI Agent 设计，相比传统的 Google Search，它能直接返回结构化良好的摘要和高度相关的网页正文片段，显著减少了 Agent 解析无关 HTML 的 Token 开销。

## 安装

```bash
npx clawhub@latest install tavily-search
```

## 典型用途

- **查询最新事件与权威来源**：获取过去 24 小时内发生的科技大事件或政策变动。
- **交叉验证事实，降低信息滞后风险**：当 Agent 内置知识库（LLM Knowledge Cut-off）与现实发生冲突时。
- **为结论补充可追溯链接**：在生成研报、周报时，自动添加 `Sources` 引用，增强可信度。
- **深度研究 (Deep Research)**：递归执行多层搜索，从宏观概览深入到微观细节。
- **特定领域检索**：如寻找某个开源库的最新的 API 使用示例，或对比不同 SaaS 产品的实时价格。

## 触发条件 / When to Use

- **时间敏感性 (Recency)**：用户询问“今天/昨天/这周”发生的事。
- **存在知识盲区**：当用户提到的术语、公司或事件不在 Agent 训练数据中时。
- **需要事实核查 (Fact-Checking)**：对一个可疑的论点进行多方求证。
- **文档缺失补全**：需要查看某个在线产品的最新官方文档，而本地没有该文档的镜像。
- **竞品分析与对比**：需要获取竞争对手最新的官网描述、定价页面或用户评价。

## 核心能力 / Core Capabilities

### 1. 结构化结果获取 (Structured Results)
- **操作步骤**：
  1. 调用 `tavily_search` 接口。
  2. 使用 `search_depth: "advanced"` 以获取更深层的抓取。
  3. 设置 `max_results: 5`（对于简单概览）或 `max_results: 10`（对于深度研报）。
- **最佳实践**：在 Prompt 中明确要求 Agent 同时关注 `title`, `url` 和 `content` 字段。

### 2. 精准内容提取 (Clean Content Extraction)
- **操作步骤**：
  1. 通过 `include_raw_content: false` 排除不必要的网页源代码，仅保留清洗后的正文。
  2. 利用 Tavily 的 `answer` 功能获取搜索引擎自动生成的初步简答。
- **最佳实践**：如果需要更原始的数据进行二次加工，可配合 `web_fetch` 针对性抓取特定 URL。

### 3. 多样化媒体检索 (Multimodal Search)
- **操作步骤**：
  1. 在搜索参数中开启 `include_images: true`。
  2. 获取图片 URL、宽度、高度及描述。
- **最佳实践**：在生成图文并茂的 PPT 或文章时，使用此功能自动配图。

### 4. 来源归因与引文生成 (Citation Generation)
- **操作步骤**：
  1. 收集所有搜索到的 `url`。
  2. 在生成的文本中，使用 `[^1]`, `[^2]` 格式进行上标。
  3. 在文末生成 `References` 列表。

## 常用命令/模板 / Common Patterns

### 深度研究搜索模板 (Deep Research Template)
```markdown
### 搜索目标 (Search Target)
[描述：查找 NVIDIA 2025 Q4 财报的核心指标及分析师预期]

### 搜索策略 (Search Strategy)
1. **宏观搜索**: 使用词组 `NVIDIA 2025 Q4 earnings report official PDF`.
2. **分析师视角**: 使用词组 `NVIDIA earnings analysis 2025 Goldman Sachs Morgan Stanley`.
3. **市场反应**: 使用词组 `NVDA stock price reaction Q4 2025 post-market`.

### 约束条件 (Constraints)
- 只采集发布日期在 2025 年 1 月之后的信息。
- 优先选择 `.gov`, `.edu` 或知名财经媒体（如 Bloomberg, Reuters）。

### 预期产出 (Desired Output)
- 汇总表：营收、净利、毛利率、同比增长。
- 分析师观点对比。
- 原文来源链接。
```

### 多语言搜索示例
```javascript
// 示例：同时在中文和英文互联网搜索同一技术趋势
mcp_call({
  name: 'tavily_search',
  arguments: {
    query: "DeepSeek-V3 architecture analysis",
    search_depth: "advanced",
    include_answer: true
  }
});
```

## 进阶应用场景 / Advanced Use Cases

### 1. 自动化每日简报
- 配置一个 `cron` 任务，每天早上 8 点调用 `tavily-search` 抓取特定关键词的新闻，利用 `summarize` 技能生成摘要，并通过 `notion` 或 `slack` 发送给用户。

### 2. 招投标情报分析
- 输入某个项目的招标编号，Agent 自动搜索全网相关的招标公告、变更说明及历史中标结果，为用户提供竞争分析报告。

## 边界与限制 / Boundaries

- **API 配额限制 (API Quota)**：Tavily 的免费额度有限（通常每月 1000 次），在高频循环中使用时需注意熔断保护。
- **幻觉风险 (Hallucination)**：虽然来源是真实的，但如果搜索引擎抓取到了虚假新闻，Agent 仍可能产生误导。必须进行多源对比。
- **隐私保护 (Privacy)**：严禁将包含用户个人隐私、商业机密或 API Keys 的搜索词发送到外部搜索引擎。
- **付费墙限制 (Paywall)**：Tavily 无法突破 WSJ, Bloomberg 等网站的付费墙订阅。
- **结果偏见 (Algorithm Bias)**：搜索结果受算法排名影响，可能存在一定的立场偏见。

## 最佳实践总结

1. **精准 Query**：不要只输入一个词，要输入一个具体的问题或完整的短语。
2. **多源验证**：关键事实至少需要两个独立来源的印证。
3. **深度优先**：对于复杂问题，第一遍搜索出的结果应作为第二遍更精确搜索的线索。
4. **清理噪音**：使用 `include_domains` 或 `exclude_domains` 过滤掉不靠谱的博客或广告网站。
5. **记忆同步**：搜索到的重要信息应同步到 `MEMORY.md`，避免重复搜索同一个固定事实。
