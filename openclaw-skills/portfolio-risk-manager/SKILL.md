---
name: portfolio-risk-manager
description: 'Use when reviewing portfolio exposures, checking concentration and beta risk, summarizing sector or region tilts, or preparing a risk note before reallocating capital.'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["finance", "manager", "portfolio", "risk"]'
created_at: "2026-03-18"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
---

# Portfolio Risk Manager (投资组合风险管理器)

像专业的风险会议（Risk Meeting）一样汇总投资组合：分析集中度（Concentration）、敞口（Exposure）、贝塔（Beta）、波动率（Volatility），识别组合在哪些领域过度倾斜。本技能旨在将杂乱的持仓清单转化为具有前瞻性的风险视图，辅助投资经理在调仓前进行全方位的“健康体检”。

## 安装与前提条件

```bash
# 确保已安装投资组合分析与统计库
pip install pandas numpy pyportfolioopt scipy
# 准备持仓数据
npx clawhub install portfolio-risk-manager
```

## 触发条件 / When to Use

- **每周 PM 评审 (Weekly PM Review)**：在每周一开盘前，对整个组合的风险暴露进行全量扫描。
- **调仓前风险核查 (Pre-trade Sanity Check)**：在大幅增加某个标的或行业的权重前，评估其对组合整体风险的影响。
- **致投资者信准备 (Investor Letter Prep)**：需要向投资者清晰地说明目前持仓的风险属性（如：低 Beta、高分红、区域倾斜）。
- **仓位规模讨论 (Position Sizing)**：根据波动率逆向计算每个标的应占的最优权重。
- **极端行情复盘**：当市场发生剧烈波动时，快速计算组合的 VaR（在职风险值）并制定防御方案。

## 核心能力 / Core Capabilities

### 1. 集中度与多维敞口分析 (Exposure Analysis)
- **操作步骤**：
  1. 统计前 10 大持仓的权重（Top 10 Weight）。
  2. 按 **行业 (Sector)**、**地区 (Region)**、**市值 (Market Cap)** 及 **风格 (Style)** 进行穿透式汇总。
  3. 识别“非意图敞口”（Accidental Exposure），即由于多个标的同属一个子行业而导致的隐性集中风险。
- **最佳实践**：单一标的权重通常不应超过 10%，单一行业敞口不应超过 25%，除非该策略是高集中度的特定风格。

### 2. 系统性与特有风险测算 (Beta & Volatility)
- **操作步骤**：
  1. 运行 `scripts/portfolio_risk.py`。
  2. 计算加权贝塔（Weighted Beta）：评估组合对大盘波动的敏感度。
  3. 拆解风险来源：区分 **系统性风险 (Systematic Risk)** 和 **特有风险 (Idiosyncratic Risk)**。
  4. 计算 **跟踪误差 (Tracking Error)**：衡量组合相对于基准的偏离程度。
- **最佳实践**：在熊市环境下，重点关注 Beta 的漂移情况。

### 3. 相关性矩阵与多元化分析 (Correlation Analysis)
- **操作步骤**：
  1. 计算所有持仓之间的相关性矩阵（Correlation Matrix）。
  2. 识别“假多元化”：表面上买了 20 只股票，但如果它们的相关系数都在 0.8 以上，实质上是一个高风险头寸。
- **最佳实践**：通过寻找相关性低于 0.3 的资产来优化夏普比率。

### 4. 压力测试与情景模拟 (Stress Testing)
- **操作步骤**：
  1. 模拟极端情景：如“利率上升 100bp”、“纳斯达克回调 10%”、“原油价格翻倍”。
  2. 预估组合在这些情景下的最大跌幅。
  3. 输出“VaR (Value at Risk)”报告。

## 常用命令/模板 / Common Patterns

### 投资组合 JSON 模板 (Portfolio JSON)
```json
{
  "portfolio_name": "Growth_Strategy_2026",
  "base_currency": "USD",
  "holdings": [
    { "ticker": "NVDA", "weight": 0.12, "beta": 1.65, "sector": "Semiconductors" },
    { "ticker": "MSFT", "weight": 0.10, "beta": 1.15, "sector": "Software" },
    { "ticker": "JPM", "weight": 0.08, "beta": 0.95, "sector": "Finance" }
  ],
  "benchmark": "S&P 500"
}
```

### 风险总结摘要模板 (Risk Summary Note)
```markdown
### 🛡️ 投资组合风险周报：[Growth_Strategy]

**1. 核心风险指标 (Core Metrics)**:
- **总贝塔 (Total Beta)**: 1.25 (中等激进，偏向进攻型)
- **集中度 (Concentration)**: 前 5 大持仓占比 45% (**偏高**)
- **波动率 (Volatility Proxy)**: 18.5% (高于基准的 14.2%)

**2. 敞口倾斜 (Sector Tilts)**:
- **超配 (Overweight)**: 科技 (+12%), 半导体 (+8%)
- **低配 (Underweight)**: 医疗 (-5%), 能源 (-10%)

**3. 关键预警 (Risk Alerts)**:
- [NVDA] 权重已达 12%，触发 10% 警戒线。建议减持至 8%。
- [MSFT] 与 [NVDA] 相关系数上升至 0.85，组合在 AI 硬件与软件上的风险高度耦合。

**4. 压力测试 (Scenario Results)**:
- **利率上升 50bp**: 组合预期净值下降 -4.2%。
- **科技股回调 10%**: 组合预期净值下降 -12.5%。

**5. 最终决策方案**:
> [Action] 卖出 4% NVDA，买入标普 500 低波动 ETF 以降低 Beta 到 1.1。
```

### 快速风险评估命令
```bash
# 运行描述性风险分析
python scripts/portfolio_risk.py --input assets/my_holdings.json --benchmark spy

# 构建优化器输入数据（协方差矩阵等）
python scripts/build_optimizer_inputs.py --returns assets/historical_returns.json
```

## 进阶应用场景 / Advanced Use Cases

### 1. 自动化调仓建议 (Auto-Rebalance)
- 当某一标的的权重因涨跌偏离预设比例 2% 以上时，Agent 自动调用 `portfolio-risk-manager` 计算“最小换手”下的调仓方案。

### 2. “风险因子”穿透监控
- 不仅看行业，更要看底层风险因子（如：汇率敏感度、大宗商品价格敏感度）。例如：分析组合中有多少收入来自海外，从而识别汇率波动的潜在风险。

## 边界与限制 / Boundaries

- **数据质量**：Beta 和相关性是基于历史数据计算的（Backward-looking），不能保证未来。
- **极端事件 (Tail Risk)**：正态分布假设无法准确预测“黑天鹅”事件的杀伤力。
- **执行滑点**：大宗交易的真实冲击成本（Price Impact）未包含在初步的风险评估中。
- **衍生品复杂性**：本技能主要处理权益类现货，对于复杂的期权或掉期头寸的 Delta/Gamma 风险需配合 `options-strategy-evaluator`。
- **静态 vs 动态**：风险管理是动态过程，本报告仅代表“当前时刻”的快照。

## 最佳实践总结

1. **意图第一**：明确哪些风险是“故意的”（如为了博取超额收益而主动重仓某个行业），哪些是“意外的”。
2. **重视 Beta 漂移**：随着股价上涨，强势股的权重会自然增加，导致 Beta 悄悄上升。
3. **小而美的持仓**：不要为了多元化而买入自己不熟悉的标的。
4. **记忆同步**：将每一次重大的风险调整决策记入 `MEMORY.md`。
5. **分级监控**：设置“黄灯”预警线（减速）和“红灯”强制线（强制平仓）。
6. **关注流动性**：在计算持仓占比时，也要核对自己的持仓量占该股日均交易量的比例。
7. **数据来源核实**：所有 Beta 数据必须标注时间窗口（如：基于 5 年月度数据 vs 1 年日度数据）。
