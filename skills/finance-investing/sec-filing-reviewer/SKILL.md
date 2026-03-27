---
name: sec-filing-reviewer
description: 'Use when reviewing SEC filings, extracting material risk disclosures, scanning 10-K or 10-Q sections, or building a follow-up checklist from filing language.'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["filing", "finance", "reviewer", "sec"]'
created_at: "2026-03-18"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
---

# SEC Filing Reviewer (SEC 财报审计专家)

在数百页的冗长文件中，精准捕捉被隐藏的控制风险、流动性危机、法律纠纷及重大会计披露。本技能旨在帮助分析师从 10-K, 10-Q, 8-K 等 SEC 官方文件中提取关键变量，并识别出那些可能被市场忽视的“红旗”信号（Red Flags）。

## 安装与前提条件

```bash
# 确保已安装 EDGAR 数据处理库
pip install sec-edgar-downloader sec-parser beautifulsoup4
# 下载审计脚本
npx clawhub install sec-filing-reviewer
```

## 触发条件 / When to Use

- **定期财报审计 (10-K & 10-Q Reviews)**：每季度/年度对核心持仓或候选池中的公司进行深度合规性扫描。
- **突发事件扫描 (8-K Event Scans)**：当公司发布 8-K 公告时，快速判断该事件是否涉及 CEO 辞职、重大资产减值或法律诉讼。
- **盘前尽职调查 (Pre-earnings Diligence)**：在业绩电话会前，预先从最新提交的文件中寻找“蛛丝马迹”。
- **新标的分诊 (Red-flag Triage for New Positions)**：在正式建仓前，对陌生的公司进行一次全面的历史合规性背景调查。
- **内部人持股监控 (Form 4 & Proxy)**：追踪高管的买卖行为及薪酬方案是否与股东利益一致。

## 核心能力 / Core Capabilities

### 1. 关键章节自动提取 (Section Extraction)
- **操作步骤**：
  1. 使用 `sec-parser` 定位并提取核心章节：
     - **Item 1A (Risk Factors)**: 风险因素。
     - **Item 7 (MD&A)**: 管理层对经营状况的讨论与分析。
     - **Item 3 (Legal Proceedings)**: 法律诉讼详情。
     - **Item 9A (Controls and Procedures)**: 内部控制评价。
  2. 提取财务报表附注中的“表外融资”或“关联方交易”。
- **最佳实践**：重点对比本期与上期在 Item 1A (风险因素) 描述上的文字增减（Delta Analysis）。

### 2. 财务完整性与红旗信号扫描 (Red-flag Detection)
- **操作步骤**：
  1. 运行 `scripts/review_filing.py`。
  2. 扫描以下关键词与短语：`Going concern` (持续经营能力), `Material weakness` (重大缺陷), `Restatement` (重报), `Investigation` (调查), `Qualified opinion` (保留意见)。
  3. 统计审计费用（Audit Fees）的异常波动。
- **最佳实践**：如果 Item 9A 出现“Material weakness”，应立即调低其 ESG 和治理评分。

### 3. 流动性与资本支出分析 (Liquidity Analysis)
- **操作步骤**：
  1. 提取资产负债表中的“受限现金”（Restricted Cash）及“短期债务到期”情况。
  2. 分析 MD&A 中关于现金流来源及使用的具体描述。
- **最佳实践**：将文件的文本描述与财务模型中的 `DSO` (应收账款周转天数) 变动进行交叉验证。

### 4. 自动化跟进问题清单 (Follow-up Checklist)
- **操作步骤**：
  1. 基于文件的模糊陈述（如“某些不确定的法律影响”），生成 3-5 个具体的跟进问题。
  2. 将这些问题存入 `MEMORY.md`，供下次业绩电话会或投资者关系（IR）调研使用。

## 常用命令/模板 / Common Patterns

### 财报审计输入 JSON 模板 (Filing Sections JSON)
```json
{
  "cik": "0000320193",
  "filing_type": "10-K",
  "fiscal_year": 2025,
  "sections_to_scan": ["Risk Factors", "Legal", "MD&A"],
  "focus_keywords": ["Cybersecurity", "Litigation", "Inventory write-down"]
}
```

### 审计结论摘要模板 (Review Summary Note)
```markdown
### 🚩 SEC 文件审计报告：[TSLA] 10-Q (2026 Q1)

**1. 重大风险变更 (What's New in Risks)**:
- **新增项**: 明确提及了 X 地区的自动驾驶监管准入风险。
- **变更项**: 删除了关于“供应链已经常态化”的描述。

**2. 财务红旗信号 (Red Flags)**:
- **审计控制**: 🟢 无重大缺陷报告。
- **诉讼更新**: ⚠️ 发现一例涉及专利侵权的新增集体诉讼，金额未披露。
- **流动性**: 现金储备稳健，但存货积压较去年同期上升 15%。

**3. 管理层语气 (MD&A Tone)**:
- 针对资本开支的描述比上季度更显激进，重点强调 AI 算力投入。

**4. 建议跟进问题 (Investor Questions)**:
- 1) 存货积压是否主要来自 X 型号的排产过剩？
- 2) 新增诉讼的拨备计划是否已在当前利润表中体现？

**5. 最终评级**: **中性 (加强监控)**
```

### 快速执行命令
```bash
# 自动抓取并审计最新的 10-K 摘要
python scripts/review_filing.py --cik 320193 --type 10-K --report audit_report.md
```

## 进阶应用场景 / Advanced Use Cases

### 1. 跨公司“红旗”横向对比
- 自动对比同一行业（如：所有生物制药公司）在最新年报中关于“研发失败风险”的描述深度，识别出哪家公司披露最透明、哪家在“挤牙膏”。

### 2. 监管变动追踪
- 当 SEC 推出新规定（如：强制披露碳排放）后，Agent 自动扫描所有的 10-K，提取各家公司的合规成本预估。

## 边界与限制 / Boundaries

- **语言模糊性**：公司法律顾问会故意使用模糊词汇以降低法律风险，Agent 只能基于文本逻辑进行“推测”。
- **非 GAAP 数据偏见**：公司倾向于展示对其有利的非公认会计准则指标，必须始终回归到原始 GAAP 数据。
- **数据更新延迟**：虽然 SEC 提供 API，但数据录入系统到完全解析可能存在分钟级的延迟。
- **跨平台一致性**：8-K 的信息可能与之后补录的 10-Q 不完全一致。
- **阅读量限制**：对于包含 500+ 页附件的大型银行财报，Agent 处理全部文本的耗时会显著增加。

## 最佳实践总结

1. **锚定官方来源**：永远优先从 `sec.gov` 直接抓取，而非通过不可靠的第三方采集平台。
2. **区分“事实”与“评价”**：识别哪些是具体的数字，哪些是管理层的愿景（Prospective Statements）。
3. **关注变更 (The Deltas)**：相比于文件说了什么，上一期说了但这一期“没说”的内容往往更具风险。
4. **记忆同步**：将公司历年的法律纠纷进展存入 `MEMORY.md`。
5. **多维核实**：将 SEC 文件的描述与最新的空头研究报告（Short Sellers' Reports）进行对齐。
6. **关注“审计师变更”**：突然更换四大会计师事务所通常是极高风险信号。
7. **关注“内幕交易”**：结合 Form 4，看高管在财报提交前后的真实买卖动作。
