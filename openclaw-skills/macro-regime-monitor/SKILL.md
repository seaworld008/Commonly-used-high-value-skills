---
name: macro-regime-monitor
description: 'Use when tracking macro regime shifts, summarizing inflation, growth, spreads, and liquidity signals, or creating a house view before updating sector or asset-allocation calls.'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["finance", "macro", "monitor", "regime"]'
created_at: "2026-03-18"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
---

# Macro Regime Monitor (宏观周期监控器)

从宏观噪音中提取信号，识别当前的宏观范式（Macro Regime），为资产配置和行业轮动提供决策依据。本技能通过整合通胀、增长、利差和流动性等多维指标，帮助投资者判断市场正处于何种周期阶段，从而决定是“Risk-on”还是“Risk-off”。

## 安装与前提条件

```bash
# 确保已安装宏观数据抓取与分析库
pip install pandas numpy openbb requests
# 下载宏观分类脚本
npx clawhub install macro-regime-monitor
```

## 触发条件 / When to Use

- **每周宏观周报 (Weekly Macro Note)**：在周一开盘前，梳理上周所有宏观数据的变化及其对周期的影响。
- **资产配置会议 (Asset-allocation Meetings)**：在决定增配股票还是债权前，先确认宏观大环境。
- **风险模式切换 (Risk-on vs Risk-off Framing)**：当突发地缘政治冲突或重大利率决议时，快速评估环境切换风险。
- **跨资产仓位更新 (Cross-asset Positioning)**：根据宏观象限的变化，动态调整大宗商品、外汇及权益类资产的比例。
- **核心逻辑修正**：当通胀数据连续三个月超预期，触发“通胀粘性”范式确认。

## 核心能力 / Core Capabilities

### 1. 核心指标实时跟踪 (Key Indicators Tracking)
- **操作步骤**：
  1. 获取最新的 **增长 (Growth)** 数据：如 GDP, PMI (制造/服务), 零售销售。
  2. 获取最新的 **通胀 (Inflation)** 数据：如 CPI, PPI, PCE, 薪资增速。
  3. 获取最新的 **流动性 (Liquidity)** 数据：如 M2, 央行资产负债表变化, 逆回购（RRP）规模。
  4. 获取最新的 **利差 (Spreads)** 数据：如 10Y-2Y 收益率曲线倒挂程度, 信用违约掉期（CDS）。
- **最佳实践**：优先关注“二阶导数”（即增长是否在放缓，或通胀是否在加速）。

### 2. 宏观象限分类 (Regime Classification)
- **操作步骤**：
  1. 运行 `scripts/classify_regime.py`。
  2. 将当前环境映射到经典象限：
     - **金发姑娘 (Goldilocks)**: 增长高，通胀低。
     - **通货膨胀 (Reflation)**: 增长高，通胀高。
     - **滞胀 (Stagflation)**: 增长低，通胀高。
     - **衰退/通缩 (Recession)**: 增长低，通胀低。
- **最佳实践**：不仅给出标签，更要标注当前位置在象限中的偏移趋势。

### 3. 资产配置含义推导 (Allocation Implications)
- **操作步骤**：
  1. 基于当前的 Regime，自动匹配历史胜率最高的资产类别。
  2. 生成“战术性资产配置”（TAA）建议。
  3. 识别最受影响的行业板块（如：滞胀环境下通常利好能源和必需消费品）。
- **最佳实践**：提供“反转触发点”（Flip Points），例如：“如果 10Y 美债收益率突破 5.0%，则从成长股切换到防守型价值股”。

### 4. 情绪与头寸分析 (Sentiment & Positioning)
- **操作步骤**：
  1. 抓取 `Fear & Greed Index` 或 `AAII Sentiment Survey`。
  2. 分析 `Commitment of Traders (COT)` 报告，查看机构在大宗商品和外汇上的多空头寸分布。

## 常用命令/模板 / Common Patterns

### 宏观监控数据 JSON 模板 (Macro Indicators JSON)
```json
{
  "region": "US",
  "data_points": {
    "pmi_composite": 52.5,
    "cpi_yoy": 3.4,
    "fed_funds_rate": 5.25,
    "yield_curve_10y2y": -0.45,
    "m2_growth": 0.02
  },
  "trend": "Growth decelerating, Inflation sticky"
}
```

### 宏观范式报告模板 (Regime Scorecard)
```markdown
### 🌐 全球宏观范式报告 (2026-03-27)

**1. 当前宏观象限**: **滞胀早期 (Early Stagflation)**
- **得分情况**: 增长 [4.2/10], 通胀 [8.5/10], 流动性 [5.0/10]

**2. 核心变化 (What Changed)**:
- 过去两周内，PPI 增速超预期，导致通胀得分从 7.2 上升至 8.5。
- 制造业 PMI 跌入 50 荣枯线以下。

**3. 资产配置指引 (Strategic Moves)**:
- **超配 (Overweight)**: 黄金、能源、现金。
- **中性 (Neutral)**: 国债（等待收益率曲线进一步陡峭化）。
- **低配 (Underweight)**: 科技成长股、房地产。

**4. 关键观察哨 (Flip Points)**:
- 若下周非农数据低于 100k，确认衰退风险，资产配置将全面转向防守。
```

### 快速查询命令
```bash
# 获取并分类最新的宏观环境
python scripts/classify_regime.py --input assets/live_macro.json --plot_quadrant
```

## 进阶应用场景 / Advanced Use Cases

### 1. 跨国宏观联动分析
- 自动分析美、欧、中三大经济体的周期错位，寻找跨国利差套利（Carry Trade）或跨市场轮动的机会。

### 2. “历史复刻”模拟
- 将当前的宏观参数与历史上最相似的阶段（如 1970 年代石油危机或 2008 年金融危机）进行对比，生成“相似度报告”。

## 边界与限制 / Boundaries

- **数据滞后性**：宏观指标（如 GDP）通常是落后指标，存在“看后视镜开车”的风险。
- **央行干预的不可预测性**：突发的流动性支持（如贴现窗口开启）可能瞬间逆转宏观范式。
- **多变量复杂性**：单一的象限模型无法捕捉所有的复杂变量（如突发战争、技术突破）。
- **数据修订风险**：政府公布的数据经常在次月进行大幅修订。
- **黑盒模型风险**：分类脚本 `classify_regime.py` 的算法必须透明，严禁过度依赖不可解释的权重。

## 最佳实践总结

1. **结论先行，证据在后**：在报告头部直接给出 Regime 结论。
2. **重视流动性**：在低增长环境下，流动性的多寡往往决定了资产价格。
3. **区分“预期”与“现实”**：关注宏观数据相对于“市场共识预期”的偏差（Surprise Index）。
4. **记忆同步**：将每个月的 Regime 演变路径记录到 `MEMORY.md`。
5. **多周期校验**：同时观察月度（短期）、季度（中期）和年度（长期）的宏观趋势。
6. **动态权重**：根据当前的政策环境，调整增长和通胀在模型中的权重。
7. **引述来源**：所有数据点必须标注来源（如 Bloomberg, Fred, TradingEconomics）。
