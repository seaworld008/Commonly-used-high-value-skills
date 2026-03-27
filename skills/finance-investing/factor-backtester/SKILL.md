---
name: factor-backtester
description: 'Use when testing factor signals, running long-short spread backtests, checking hit rate and turnover, or sanity-checking whether a ranking signal survives basic transaction cost assumptions.'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["backtester", "factor", "finance"]'
created_at: "2026-03-18"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
---

# Factor Backtester (因子回测器)

在投入重金之前，先验证你的因子（Factor）是否真的具备“阿尔法”收益。本技能旨在提供一个轻量级的因子筛选层，帮助量化研究员和投资经理快速验证信号的有效性，并识别那些仅在“理想实验室”中存在的伪因子。

## 安装与前提条件

```bash
# 确保已安装量化回测与数学统计库
pip install pandas numpy matplotlib scipy pyfolio
# 准备回测数据
npx clawhub install factor-backtester
```

## 触发条件 / When to Use

- **新信号研发 (Signal Research)**：验证一个新的财务指标（如：研发投入强度）是否具备长期选股能力。
- **横截面排名测试 (Cross-sectional Ranking Tests)**：对比不同因子在全市场范围内的预测力。
- **投资经理思路验证 (PM Idea Review)**：将宏观直觉转化为可量化的因子回测。
- **深度工程前的筛选 (Lightweight Screening)**：在大规模分布式回测之前，先进行快速的“可行性扫描”。
- **因子失效诊断**：当某个传统因子（如：估值因子）近期表现不佳时，进行历史回看以判断其是否已经永久失效。

## 核心能力 / Core Capabilities

### 1. 信号准备与预处理 (Signal Prep)
- **操作步骤**：
  1. 准备分周期的长端收益（Long Return）、短端收益（Short Return）及基准收益（Benchmark Return）。
  2. 进行数据的去极值处理（Winsorization）和标准化（Z-score）。
  3. 处理缺失值，并标记“可交易性”过滤器（如：剔除停牌、ST 或新股）。
- **最佳实践**：始终保留至少 5-10 年的历史跨度，以覆盖完整的经济周期。

### 2. 核心指标计算 (Metrics Calculation)
- **操作步骤**：
  1. 运行 `scripts/backtest_factor.py`。
  2. 计算 **IC/IR (Information Coefficient)**：衡量预测值与实际收益的相关性。
  3. 计算 **夏普比率 (Sharpe Ratio)**、**最大回撤 (Max Drawdown)** 以及 **胜率 (Hit Rate)**。
  4. 分析 **换手率 (Turnover)** 对最终收益的侵蚀。
- **最佳实践**：除了看总收益，更要看分年度、分行业的收益稳定性。

### 3. 多空对冲模拟 (Long-Short Simulation)
- **操作步骤**：
  1. 模拟多空对冲（Long-Short Spread）策略，观察因子的纯净阿尔法。
  2. 识别因子的“行业暴露”：该收益是真的来自因子，还是仅仅因为重仓了某个行业？
- **最佳实践**：在计算收益时，显式扣除双边 0.1% - 0.3% 的交易成本（Transaction Costs）。

### 4. 稳健性与压力测试 (Robustness Check)
- **操作步骤**：
  1. 在不同市场环境下（牛市、熊市、震荡市）进行分段回测。
  2. 改变回测起点或调仓周期（如：从周频改为月频），观察信号是否依然存活。
- **最佳实践**：如果一个小变化导致收益巨幅波动，该因子大概率存在“过拟合”风险。

## 常用命令/模板 / Common Patterns

### 回测输入数据 JSON 模板 (Backtest Data JSON)
```json
{
  "factor_name": "OperatingProfitMargin",
  "periods": [
    { "date": "2025-01-31", "long_ret": 0.05, "short_ret": 0.02, "bench_ret": 0.03, "turnover": 0.12 },
    { "date": "2025-02-28", "long_ret": -0.01, "short_ret": -0.04, "bench_ret": -0.02, "turnover": 0.08 }
  ],
  "transaction_cost": 0.0015
}
```

### 回测报告摘要模板 (Backtest Summary)
```markdown
### 📊 [因子名] 回测报告摘要

**1. 核心表现 (Performance)**:
- **年化收益**: [XX%]
- **夏普比率**: [1.85] (显著性阈值: > 1.5)
- **最大回撤**: [-8.2%]

**2. 统计显著性 (Significance)**:
- **平均 IC**: [0.045]
- **IC IR**: [0.65]

**3. 换手与成本分析 (Cost Analysis)**:
- **月均换手率**: [25%]
- **预估成本侵蚀**: [年化约 4.5%]
- **净收益**: [依然为正，具备实盘价值]

**4. 最终结论 (Verdict)**:
> [✓] 建议进入深度研究阶段
> [!] 信号较弱，仅可作为次要辅助
> [X] 严重过拟合或成本无法覆盖收益，拒绝
```

### 快速回测执行示例
```bash
# 针对特定数据文件运行回测脚本并输出 PDF 报告
python scripts/backtest_factor.py --input assets/factor_alpha_v1.json --plot --save report.pdf
```

## 进阶应用场景 / Advanced Use Cases

### 1. 因子相关性矩阵构建
- 自动计算新因子与现有“全家桶因子”（如：Size, Value, Momentum）的相关性，确保新信号带来的不是重复的信息（Collinearity）。

### 2. 自动参数寻优
- 利用 `factor-backtester` 自动遍历不同的参数组合（如：3 个月均值 vs 6 个月均值），并绘制参数热力图。

## 边界与限制 / Boundaries

- **生存者偏差 (Survivorship Bias)**：如果数据集中不包含那些已经退市或破产的公司，回测结果会虚高。
- **未来函数 (Look-ahead Bias)**：严禁在 T 时刻使用 T+1 时刻才公布的数据（如：用 4 月份公布的年报去回测 1 月份的交易）。
- **成交量与冲击成本**：小市值因子的回测往往忽略了在大额交易时的股价冲击（Price Impact），导致实盘无法成交。
- **过度拟合 (Overfitting)**：在海量因子中强行寻找规律，可能会找到由于偶然性产生的收益曲线。
- **数据回补延迟**：财报公布日不等于财报数据录入数据库的日期。

## 最佳实践总结

1. **简单至上**：逻辑简单、可解释性强的因子往往比复杂的黑盒因子更稳健。
2. **扣除成本**：永远不要相信未扣除手续费和滑点的收益曲线。
3. **样本外验证 (Out-of-sample)**：将数据分为两半，一半用于训练，另一半用于验证。
4. **记忆同步**：将回测的关键指标及失败原因记入 `MEMORY.md`，防止重复开发。
5. **重视换手率**：换手率超过 60% 的月频策略在当前的 A 股或美股环境下很难盈利。
6. **多市场验证**：一个好的因子应该在不同的市场（如 A 股和美股）同时具备一定的解释力。
