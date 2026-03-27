---
name: options-strategy-evaluator
description: 'Use when evaluating an options structure, checking expiry payoff checkpoints, comparing premium outlay versus downside protection, or preparing a short strategy note for a trade review.'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["evaluator", "finance", "options", "strategy"]'
created_at: "2026-03-18"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
---

# Options Strategy Evaluator (期权策略评估器)

将期权投资想法转化为可视化的盈亏平衡点（Payoff Shape）和风险指标。本技能旨在帮助交易员和风险经理在开仓前深入理解期权结构的收益风险比，避免将复杂的“结构”误认为真实的“阿尔法”优势。

## 安装与前提条件

```bash
# 确保已安装期权定价与数值计算库
pip install numpy pandas scipy pyvol
# 准备策略参数
npx clawhub install options-strategy-evaluator
```

## 触发条件 / When to Use

- **备兑开仓与价差评审 (Covered Call, Spread Review)**：在构建卖出期权赚取权利金（Income Trade）前进行安全性核查。
- **对冲策略规划 (Hedging Strategy)**：针对现有持仓，计算保护性买权（Protective Put）或领口策略（Collar）的最优行权价。
- **业绩期波动率交易 (Earnings-event Planning)**：针对财报季的剧烈波动，评估跨式（Straddle）或宽跨式（Strangle）策略。
- **权利金收入与现金流管理 (Premium Income Checks)**：分析 Cash-Secured Puts 或 Iron Condors 的预期胜率与盈亏比。
- **风险委员会汇报 (Risk Committee Notes)**：为投资组合中的复杂期权结构提供直观的压力测试报告。

## 核心能力 / Core Capabilities

### 1. 策略结构定义与定价 (Leg Definition)
- **操作步骤**：
  1. 定义期权腿（Legs）：类型（Call/Put）、方向（Long/Short）、行权价（Strike）、到期日（Expiry）。
  2. 获取当前隐含波动率（Implied Volatility）和标的资产价格（Underlying Price）。
  3. 利用 Black-Scholes 或二叉树模型进行期权公允价值测算。
- **最佳实践**：明确区分欧式期权与美式期权（美式期权需考虑提前行权风险）。

### 2. 盈亏平衡与 Payoff 分析 (Payoff Analysis)
- **操作步骤**：
  1. 运行 `scripts/evaluate_strategy.py`。
  2. 生成到期盈亏曲线图（Static Payoff）。
  3. 计算关键价格节点：最大盈利点、最大亏损点、上下行盈亏平衡点（Breakeven Points）。
- **最佳实践**：除了看“到期盈亏”，更要看“当前时刻盈亏”（T+0 Curve），理解波动率对中间价格的影响。

### 3. 希腊字母 (The Greeks) 风险敞口分析
- **操作步骤**：
  1. 计算 **Delta (方向性敞口)**：股价变动 1 美元，期权价格变动多少？
  2. 计算 **Gamma (曲率/风险加速度)**：股价波动剧烈时，Delta 的变化率。
  3. 计算 **Theta (时间损耗)**：持有期权每天亏损多少权利金？
  4. 计算 **Vega (波动率敏感度)**：当 IV 上升 1% 时，头寸价值的变动。
- **最佳实践**：在 Iron Condor 等中性策略中，严格监控 Vega 和 Gamma 的极端风险。

### 4. 真实世界因子覆盖 (Real-world Overlays)
- **操作步骤**：
  1. 评估 **流动性 (Liquidity)**：分析 Bid-Ask Spread 是否过宽。
  2. 模拟 **路径风险 (Path Risk)**：如果股价在到期前大幅波动，是否会触发提前行权（Early Assignment）。
  3. 计算 **预期胜率 (Probability of Profit)**：基于当前 IV 推导盈亏平衡概率。

## 常用命令/模板 / Common Patterns

### 期权策略输入 JSON 模板 (Options JSON)
```json
{
  "ticker": "AAPL",
  "strategy": "Bull Call Spread",
  "underlying_price": 190.50,
  "iv": 0.28,
  "legs": [
    { "type": "Call", "strike": 195, "expiry": "2026-05-15", "side": "Long", "qty": 10, "premium": 4.5 },
    { "type": "Call", "strike": 205, "expiry": "2026-05-15", "side": "Short", "qty": 10, "premium": 1.2 }
  ]
}
```

### 期权策略评审摘要模板 (Strategy Review)
```markdown
### 📝 期权策略评估：[SPY] Iron Condor

**1. 策略概览 (Overview)**:
- **最大盈利**: $2,500 (权利金净收入)
- **最大亏损**: $7,500 (风险敞口)
- **盈亏比**: 1:3

**2. 核心风险指标 (The Greeks)**:
- **Delta**: [Neutral] - 处于市场中性状态。
- **Theta**: [+$85/day] - 每天赚取 85 美元时间价值。
- **Vega**: [-150] - 波动率上升将对头寸不利。

**3. 盈亏平衡点 (Breakeven)**:
- 下行平衡: $485.5
- 上行平衡: $515.5

**4. 胜率分析 (POB)**:
- 基于当前 IV 22%，到期获利概率为 **68%**。

**5. 风险提醒 (Critical Warnings)**:
- **流动性差**: 该行权价成交量极低，平仓可能面临较大滑点。
- **IV 溢价**: 目前 IV 高于历史分位数 80%，适合卖出而非买入。
```

### 快速评估命令
```bash
# 运行策略评估脚本并输出可视化图表
python scripts/evaluate_strategy.py --input assets/spread_a.json --plot --show_greeks
```

## 进阶应用场景 / Advanced Use Cases

### 1. 动态对冲 (Delta Hedging) 自动化
- Agent 定期监控期权组合的 Delta 敞口。当 Delta 偏移超过预设阈值时，自动调用 `options-strategy-evaluator` 生成对冲方案（如买卖标的股票或调整期权腿）。

### 2. 波动率曲面 (Vol Surface) 偏离分析
- 分析不同行权价（Skew）或不同到期日（Term Structure）的 IV 异常。

## 边界与限制 / Boundaries

- **波动率假设**：所有的定价模型都建立在“正态分布”或特定的“随机过程”假设上，无法完全预测市场的“肥尾风险”。
- **极端滑点**：在市场崩溃（Flash Crash）时，Bid-Ask Spread 可能迅速扩大，导致预设的止损或平仓指令失效。
- **多资产关联**：本技能默认评估单标的策略，对于复杂的跨品种套利（Cross-asset Arb）支持有限。
- **计算开销**：对于大规模、包含数百条腿的复杂期权账簿（Book），实时计算所有希腊字母可能存在延迟。
- **非连续交易**：隔夜跳空（Gap Opening）是期权买方的福音，也是卖方的噩梦，模型无法精准量化这种风险。

## 最佳实践总结

1. **先看希腊字母，再看利润**：永远确保风险敞口在可承受范围内。
2. **重视 Vega 风险**：大多数散户期权玩家死于 IV Crush 而非股价方向。
3. **分阶段减仓**：在利润达到 50% 或时间价值损耗 80% 时考虑获利了结。
4. **记忆同步**：将历史上的成功和失败策略记录到 `MEMORY.md`。
5. **保守的胜率预估**：不要只看期权计算器，要结合当前的宏观环境（Regime）。
6. **流动性门禁**：交易前必须检查 Open Interest (持仓量) 和 Volume (成交量)。
7. **备选方案 (Plan B)**：如果股价突破盈亏平衡点，是直接止损、展期（Roll over）还是转化为其他结构？
