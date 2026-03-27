---
name: comps-valuation-analyst
description: 'Use when valuing a public company with peer multiples, building comparable-company tables, or pressure-testing a valuation range with EV/EBITDA, P/E, and EV/Sales.'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["analyst", "comps", "finance", "valuation"]'
created_at: "2026-03-18"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
---

# Comps Valuation Analyst (可比公司估值分析师)

快速构建可比公司估值表（Peer Table），并能像资深股票研究助理一样解释估值区间，而非仅仅罗列枯燥的比率。本技能专注于从市场共识中提取公允价值，并通过多维度倍数（Multiples）交叉验证，为投资决策提供坚实的估值锚点。

## 安装与前提条件

```bash
# 确保已安装必要的金融分析库
pip install pandas numpy openbb
# 准备输入数据
cat assets/sample_comps_input.json
```

## 触发条件 / When to Use

- **公开市场相对估值**：需要为一家拟上市（IPO）或已上市公司的公允价值寻找市场参照。
- **同行对比表构建**：为投委会（IC）、投资备忘录（Memo）或财报发布会（Earnings Prep）准备详细的 Peer Table。
- **DCF 估值交叉验证**：利用市场倍数法（Market Approach）对现金流折现法（Income Approach）的结果进行“压力测试”。
- **估值区间框架设定**：根据乐观/中性/悲观三种情景，设定目标价（Target Price）的波动带。
- **并购（M&A）定价参考**：分析行业内近期交易的估值水平。

## 核心能力 / Core Capabilities

### 1. 同行组筛选与分类 (Peer Selection)
- **操作步骤**：
  1. 识别目标公司的业务构成（Business Segments）。
  2. 搜索相同子行业、类似市值（Market Cap）和相似增长率（Growth Rate）的公司。
  3. 剔除财务异常或正在进行重大重组的“干扰公司”。
- **最佳实践**：至少包含 5-8 家核心对标公司，并将它们分为“直接竞争对手”和“相关行业参照”两组。

### 2. 财务数据标准化 (Data Normalization)
- **操作步骤**：
  1. 统一报告货币（Currency）及会计准则（IFRS vs US GAAP）。
  2. 调整非经常性损益（Non-recurring Items），计算“Normalized EBITDA”和“Adjusted EPS”。
  3. 统一财务周期（LTM - Last Twelve Months vs NTM - Next Twelve Months）。
- **最佳实践**：特别注意负债结构对 EV (Enterprise Value) 的影响，确保净债务（Net Debt）计算口径一致。

### 3. 倍数选择与计算 (Multiple Calculation)
- **操作步骤**：
  1. 计算 EV/EBITDA（剔除资本结构差异）、P/E（衡量盈利能力）、EV/Sales（适用于高增长或亏损企业）。
  2. 运行 `scripts/calculate_comps.py` 自动化生成统计值。
  3. 识别并处理离群值（Outliers），如倍数过高或为负的情况。
- **最佳实践**：对于重资产行业，优先使用 EV/EBITDA；对于轻资产/软件行业，优先使用 P/S 或 P/FCF。

### 4. 估值溢价/折价分析 (Valuation Context)
- **操作步骤**：
  1. 分析目标公司相对于 Peer Median 的溢价/折价原因（如：品牌护城河、技术壁垒、治理风险）。
  2. 撰写专业论述：为什么该标的值得 15x 还是 12x 的倍数？
- **最佳实践**：结合 ROIC (资本回报率) 和 G (增长率) 的对比，证明溢价的合理性。

## 常用命令/模板 / Common Patterns

### 可比估值分析输入 JSON 模板 (Input Template)
```json
{
  "target_company": {
    "ticker": "TECH",
    "market_cap": 5000,
    "net_debt": 200,
    "ebitda_ltm": 400,
    "net_income_ltm": 150
  },
  "peers": [
    { "ticker": "PEER_A", "ev_ebitda": 12.5, "pe": 25.0, "growth": 0.15 },
    { "ticker": "PEER_B", "ev_ebitda": 10.2, "pe": 18.5, "growth": 0.08 },
    { "ticker": "PEER_C", "ev_ebitda": 14.0, "pe": 30.0, "growth": 0.20 }
  ]
}
```

### 估值结论摘要模板 (Executive Summary)
```markdown
### 📊 [目标公司] 估值摘要报告

**1. 市场参考值**: 行业中位 EV/EBITDA 为 **12.2x**，中位 P/E 为 **24.5x**。
**2. 目标价推演**:
   - 基于 EV/EBITDA (中位): **$145.00**
   - 基于 P/E (中位): **$138.50**
**3. 最终建议区间**: **$135 - $150** (给予 5% 的质量溢价)。
**4. 核心逻辑**: 目标公司 ROIC 显著高于同行（18% vs 12%），且自由现金流转化率更佳。
**5. 潜在风险**: 行业整体估值处于 5 年历史高位，存在下行风险。
```

## 进阶应用场景 / Advanced Use Cases

### 1. 动态估值瀑布图 (Valuation Football Field)
- 结合 DCF, Comps, Precedent Transactions 的多种估值方法，利用脚本自动生成“足球场图”，直观展示估值交集。

### 2. 情绪溢价实时监控
- 结合 `tavily-search` 抓取最新的卖方报告，分析市场情绪对特定倍数的影响力。

## 边界与限制 / Boundaries

- **周期性陷阱**：在行业周期顶点时，Comps 往往会给出过于乐观的估值。
- **负利润处理**：当 EBITDA 为负时，EV/EBITDA 失效，必须强制切换到 EV/Sales 或用户定义的非财务指标（如 EV/Active Users）。
- **流动性折价**：对于小市值或交易不活跃的公司，Comps 的结果可能需要额外施加 20-30% 的流动性折价（Illiquidity Discount）。
- **幸存者偏差**：同行组中仅包含目前存活良好的公司，忽略了已退市或破产的对标项。
- **会计政策差异**：非 GAAP 数据调整可能存在主观性，需在报告中显式说明调整逻辑。

## 最佳实践总结

1. **同口径对比**：确保所有 Peer 数据处于同一财报周期（Apple-to-Apple）。
2. **剔除异常值**：手动检查那些倍数 > 100x 或为负的对标项。
3. **重视中位数**：优先使用中位数（Median）而非平均值（Mean），以减少离群值的干扰。
4. **动态更新**：估值是动态的，每当重大宏观事件发生或 Peer 财报发布后，必须重新运行分析。
5. **记忆同步**：将估值区间和关键假设记录到 `MEMORY.md`。
6. **严谨的注释**：每一个标准化调整步骤（Normalization）都必须有详细的脚注说明。
