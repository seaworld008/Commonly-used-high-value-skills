---
name: investment-memo-writer
description: 'Use when turning research notes into an investment memo, writing a buy or sell thesis, or structuring catalysts, risks, and monitoring items for an IC-style document.'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["finance", "investment", "memo", "writer"]'
created_at: "2026-03-18"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
---

# Investment Memo Writer (投资备忘录撰写师)

将零散的研究笔记转化为能够承受投资委员会（IC）审视的决策文档。本技能专注于将事实、逻辑与前瞻性判断有机融合，生成一份包含投资论据（Thesis）、催化剂（Catalysts）、风险（Risks）及估值（Valuation）的专业投资备忘录。

## 安装与前提条件

```bash
# 确保已安装文档处理库
pip install markdown docx
# 下载备忘录模板
npx clawhub install investment-memo-writer
```

## 触发条件 / When to Use

- **正式投资建议 (IC Memo Drafting)**：在决定开仓前，为投资委员会或基金经理提交正式的买入/卖出申请。
- **投研交接 (PM Handoff)**：研究员将覆盖标的移交给交易员或投资经理时。
- **季度策略复盘 (Quarterly Thesis Refresh)**：当核心逻辑发生变化时，更新原有标的的投资假设。
- **多空深度报告 (Long/Short Initiation Notes)**：首次覆盖某一行业或个股时的深度论述。
- **尽职调查汇总 (DD Summary)**：在完成一系列专家访谈和案头研究后，汇总核心发现。

## 核心能力 / Core Capabilities

### 1. 结构化论点梳理 (Thesis Structuring)
- **操作步骤**：
  1. 收集推荐结论（买入/卖出/持有）及目标价。
  2. 提取核心投资逻辑点：为什么市场错了？我们的差异化认知是什么？
  3. 定义投资时间线（Time Horizon）。
- **最佳实践**：采用“核心三点论”，确保每个论点都有独立的数据支撑。

### 2. 催化剂与里程碑设定 (Catalyst & Milestone Identification)
- **操作步骤**：
  1. 识别未来 6-12 个月内的关键驱动因素。
  2. 区分硬催化剂（如财报、临床试验、合并投票）和软催化剂（如产品口碑、行业情绪转向）。
- **最佳实践**：明确标出“监控项”（Monitoring Items），即什么情况发生意味着催化剂失效。

### 3. 多场景估值与安全边际 (Scenario Analysis & Margin of Safety)
- **操作步骤**：
  1. 输入 Bull (乐观), Base (基准), Bear (悲观) 三种情景下的财务假设。
  2. 计算每种情景下的预期回报（Expected Return）。
  3. 分析当前价格下的“风险收益比”（Risk-Reward Ratio）。
- **最佳实践**：强调在 Bear Case 下的下行空间（Downside），这是委员会最关心的点。

### 4. 风险评估与对冲建议 (Risk Assessment)
- **操作步骤**：
  1. 识别核心风险：执行风险、监管风险、宏观风险。
  2. 分析因子暴露：该笔投资是否会增加组合在“价值”或“科技”因子上的过度暴露。
  3. 提出对冲建议（如：买入行业 ETF 的 Puts）。

## 常用命令/模板 / Common Patterns

### 投资备忘录输入 JSON 模板 (Memo Input JSON)
```json
{
  "ticker": "AMZN",
  "recommendation": "BUY",
  "target_price": 245.0,
  "horizon": "12-18 Months",
  "thesis": [
    "AWS growth re-acceleration driven by AI workload migration",
    "Advertising margins improving with high incremental EBITDA",
    "Logistics optimization reducing per-package delivery cost"
  ],
  "catalysts": [
    "Q3 Cloud Revenue guidance beat",
    "Prime Day record sales volume",
    "Capex efficiency metrics showing lower intensity"
  ],
  "risks": [
    "Regulatory pressure on cloud dominance",
    "Consumer spend softening in EU/NA markets"
  ]
}
```

### 备忘录核心段落模板 (Executive Summary Segment)
```markdown
### 📝 投资摘要：[AMZN] - 买入建议

**1. 核心投资逻辑 (The Thesis)**:
- 市场低估了 AWS 在生成式 AI 领域的长尾效应，随着资本支出（Capex）转化为收入，利润率有望在明年 Q1 见底回升。

**2. 为什么市场错了 (Variant Perception)**:
- 我们认为市场过度关注了短期的折旧压力，而忽略了云计算业务在垂直行业（如医疗、金融）的渗透率上限。

**3. 估值推演 (Valuation Ranges)**:
- **Base Case**: $210 (15x EV/EBITDA FY26) - **回报 +25%**。
- **Bear Case**: $165 (12x EV/EBITDA FY26) - **风险 -5%**。

**4. 关键监控项 (Key to Monitor)**:
- AWS 月度账单增长率是否维持在 12% 以上。
```

### 快速生成文档命令
```bash
# 基于 JSON 模板生成 Markdown 格式的初步草案
python scripts/build_memo.py --input assets/amzn_v1.json --output draft_memo.md
```

## 进阶应用场景 / Advanced Use Cases

### 1. 自动化“打脸”复盘系统
- 当标的股价跌破 Bear Case 目标价时，Agent 自动调用 `investment-memo-writer` 提取当初的 Thesis，并与当前的 `news-feed` 对比，分析是“逻辑受损”还是“市场超跌”。

### 2. 跨标的对比备忘录
- 在同一行业内，针对 A、B 两家公司生成一份“对比投资备忘录”，分析为什么在这个时间点买 A 而不是买 B。

## 边界与限制 / Boundaries

- **数据依赖性**：Memo 的质量完全取决于输入的数据质量。Agent 无法识别财务造假或未公开的黑天鹅。
- **主观判断**：估值溢价和情景权重是投资者的主观判断，Agent 的建议仅供参考。
- **合规性风险**：在发布外部报告前，必须经过合规合规人员的人工审核，Agent 生成的内容不构成法律意义上的投资建议。
- **篇幅平衡**：过长的 Memo 会降低阅读率，Agent 必须学会在详尽与精炼之间取舍。

## 最佳实践总结

1. **结论先行**：第一段必须明确买卖方向和核心回报预期。
2. **证据导向**：每一个论点后必须跟着一个数据或一个事实来源。
3. **重视风险**：花 30% 的篇幅讨论风险，能显著增加 Memo 的可信度。
4. **视觉辅助**：文字描述复杂的逻辑关系时，调用 `mermaid-tools` 技能插入流程图。
5. **记忆同步**：将 Memo 中的 Key Monitoring Items 存入 `MEMORY.md` 并在 `cron` 中设定自动刷新任务。
6. **分级修订**：先由 Agent 生成草稿（Draft），再由人类研究员填入“软信息”进行最终修饰（Polishing）。
