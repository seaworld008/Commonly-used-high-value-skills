---
name: stock-screener-builder
description: 'Use when building a stock screen, filtering a universe by valuation, growth, quality, or momentum rules, or creating a repeatable shortlist for deeper research.'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["builder", "finance", "screener", "stock"]'
created_at: "2026-03-18"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
---

# Stock Screener Builder (股票筛选器构建专家)

建立一个清晰的研究漏斗（Research Funnel），而不是对着成千上万的股票清单漫无目的地看。本技能旨在帮助投资者构建可重复的筛选逻辑，从全市场数千只标的中通过多维财务指标（估值、增长、质量、动量）快速筛选出具有潜力的“候选池”。

## 安装与前提条件

```bash
# 确保已安装金融数据接口与数据处理库
pip install pandas numpy openbb requests
# 下载筛选模板
npx clawhub install stock-screener-builder
```

## 触发条件 / When to Use

- **覆盖列表初筛 (Narrowing Coverage List)**：在进入深度调研前，先将几百个备选标的缩小到 10-20 个重点关注项。
- **投资想法生成 (Idea Generation)**：寻找符合特定策略（如：低估值且高分红、高增长且负债率低）的新机会。
- **质量-增长型筛选 (Quality-Growth Screens)**：锁定那些具有高 ROIC 且营收增速稳定的优质公司。
- **事件驱动候选池生成**：例如筛选出在未来 30 天内有除权、解锁或财报发布的特定标的。
- **行业对比初探**：分析全行业中表现最突出的“领头羊”和被低估的“落后者”。

## 核心能力 / Core Capabilities

### 1. 筛选漏斗设计 (Funnel Design)
- **操作步骤**：
  1. 定义“初选池”（Universe）：如标普 500、中证 800 或特定的行业（Semiconductor）。
  2. 设置“硬性门槛”（Hard Filters）：如市值 > 10 亿、日均成交量 > 100 万。
  3. 叠加“多维得分”（Scoring Rules）：将估值（P/E）、增长（Revenue Growth）、质量（ROE）按权重进行综合打分。
- **最佳实践**：不要一次设置过多过滤器，防止筛选结果为零。先放大范围，再通过排序（Ranking）精选。

### 2. 多维度指标过滤 (Multi-factor Filtering)
- **操作步骤**：
  1. 运行 `scripts/screen_stocks.py`。
  2. 配置以下核心维度：
     - **估值 (Valuation)**: P/E, P/S, EV/EBITDA, Dividend Yield.
     - **增长 (Growth)**: Revenue Growth (YoY), EPS Growth (CAGR).
     - **质量 (Quality)**: ROIC, Net Margin, Debt/Equity Ratio.
     - **动量 (Momentum)**: 52-week High/Low %, Relative Strength.
- **最佳实践**：对不同行业使用差异化的筛选逻辑（如：银行看 P/B 和不良率，科技看 P/S 和研发强度）。

### 3. 可重复性与版本管理 (Repeatability)
- **操作步骤**：
  1. 将筛选规则（Criteria）固化为 JSON 格式的配置文件。
  2. 定期（如每周一）执行脚本，观察结果列表的变动（即哪些新公司进入了视野，哪些被剔除了）。
- **最佳实践**：记录每一次筛选结果的快照，以便在月底进行复盘。

### 4. 结果结构化与后续联动 (Actionable Output)
- **操作步骤**：
  1. 将筛选后的 Shortlist 导出为 CSV 或 Notion 表格。
  2. 为每一个入选标的自动触发 `comps-valuation-analyst` 或 `sec-filing-reviewer` 技能进行深度背景调查。

## 常用命令/模板 / Common Patterns

### 股票筛选 JSON 配置文件模板 (Screener Config JSON)
```json
{
  "name": "GARP_Strategy_V1",
  "universe": "S&P 500",
  "filters": {
    "market_cap_min": 5000000000,
    "pe_ratio_max": 25.0,
    "peg_ratio_max": 1.2,
    "revenue_growth_min": 0.15,
    "roe_min": 0.18,
    "debt_to_equity_max": 0.5
  },
  "sort_by": "peg_ratio",
  "ascending": true,
  "limit": 20
}
```

### 筛选报告摘要模板 (Screener Report)
```markdown
### 🔎 股票筛选报告：[GARP_Strategy_V1]

**1. 筛选概述 (Execution Summary)**:
- **初选池**: 500 只 (S&P 500)
- **通过过滤器**: 18 只
- **平均分值**: 7.2/10

**2. 核心幸存标的 (Top Surviving Names)**:
| 代码 | 行业 | 市盈率 (P/E) | 营收增速 | ROE | 综合得分 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GOOGL** | Interactive Media | 22.5 | 15% | 25% | 8.8 |
| **META** | Interactive Media | 24.2 | 22% | 28% | 8.5 |
| **KLAC** | Semiconductors | 23.5 | 18% | 35% | 8.2 |

**3. 排除说明 (Why others failed)**:
- 35% 的标的因 `ROE < 18%` 被排除。
- 15% 的标的因 `PEG > 1.2` 被排除（估值过高）。

**4. 后续动作 (Next Steps)**:
- [ ] 调用 `earnings-call-analyzer` 分析 GOOGL 最新财报。
- [ ] 使用 `sec-filing-reviewer` 检查 KLAC 的地缘政治风险披露。
```

### 快速执行命令
```bash
# 运行预定义的筛选规则
python scripts/screen_stocks.py --config assets/garp_config.json --export output/screener_results.csv
```

## 进阶应用场景 / Advanced Use Cases

### 1. 动态监控仪表盘 (Dashboard)
- 结合 `cron` 技能，每天收盘后自动运行筛选器，如果出现符合“深度价值”（如：破净且现金充足）的新标的，立即通过 `question` 发送提醒给投资经理。

### 2. 情绪筛选器 (Sentiment Screener)
- 将财务指标与 `tavily-search` 抓取的新闻情绪得分结合。筛选出那些“基本面极佳但近期市场情绪极度悲观”（即：跌出价值）的错杀股。

## 边界与限制 / Boundaries

- **数据源一致性**：不同数据源（如 Yahoo Finance vs Bloomberg）对相同指标的定义可能不同，导致筛选结果差异。
- **幸存者偏差**：如果初选池本身包含偏差（如剔除了历史退市标的），筛选出的策略在回测时会虚高。
- **陷阱标的 (Value Traps)**：低 PE 可能是因为公司基本面即将崩溃，Agent 必须通过多重指标交叉验证以识别陷阱。
- **财务造假识别局限**：筛选器只看表面数字，无法识别财务报表中的欺诈行为。
- **过度拟合 (Over-filtering)**：过细的过滤器可能导致只选出那些过去表现极好的“个案”，而不具备普遍的策略指导意义。

## 最佳实践总结

1. **先宽后严**：第一层过滤应该尽量宽，防止核心标的被漏掉。
2. **重视现金流**：永远将 P/FCF 或 OCF 作为质量核实的关键维度。
3. **行业对齐**：对金融、地产、科技、消费应分别设计不同的筛选逻辑（Vertical Screens）。
4. **记忆同步**：将入选标的的理由和观察日期存入 `MEMORY.md`。
5. **动态阈值**：根据宏观象限（Regime）调整筛选门槛。例如：在高息环境下，调高对“资产负债率”的要求。
6. **逻辑自洽**：确保筛选器反映的是你的真实投资理念（Thesis），而非一堆随机数字的拼凑。
7. **引述来源**：所有筛选结果必须注明数据截止日期（Snapshot Date）。
