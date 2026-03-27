---
name: event-driven-tracker
description: 'Use when tracking earnings, product launches, M&A, dividends, buybacks, unlocks, or other market-moving dates that need a prioritized event calendar.'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["driven", "event", "finance", "tracker"]'
created_at: "2026-03-18"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
---

# Event Driven Tracker (事件驱动跟踪器)

在市场“收割”你之前，先锁定关键的股价催化剂（Catalysts）。Event Driven Tracker 旨在帮助投资者从海量的日常公告中识别出真正具备“市场影响力”的大事件，并围绕这些时间点构建防御性或进攻性的交易计划。

## 安装与前提条件

```bash
# 确保已安装事件日历相关的库
pip install openbb pandas
# 准备事件数据
npx clawhub install event-driven-tracker
```

## 触发条件 / When to Use

- **股价催化剂日历 (Catalyst Calendars)**：需要为特定的投资组合建立未来 30 天的重大事件表。
- **关键仓位监控 (Position Monitoring)**：在财报发布、并购（M&A）审批或期权到期日前后的风险对冲。
- **PM 每周准备 (Weekly Prep)**：为基金经理提供下周可能导致波动（Volatility）的核心节点。
- **事件驱动策略研究 (Event-driven Strategy Notes)**：针对分拆（Spinoff）、私有化（LBO）、大股东减持（Unlocks）或纳指/标普调样进行专题跟踪。
- **宏观数据预警**：非农数据（NFP）、CPI 连续超预期后的政策节点捕捉。

## 核心能力 / Core Capabilities

### 1. 事件分类与优先级评估 (Event Prioritization)
- **操作步骤**：
  1. 识别事件类型：**软性事件**（如分析师日、新产品发布） vs **硬性事件**（如财报、特别股息、FDA 审批结果）。
  2. 根据历史波动率（Implied Volatility vs Realized Volatility）为事件打分 (Importance Score: 1-10)。
  3. 分配关键属性：公告日期、预期日期、确认日期。
- **最佳实践**：优先关注那些“结果非黑即白”（Binary Events）的事件，如法庭判决或重大合同签署。

### 2. 自动化监控与提醒 (Proactive Monitoring)
- **操作步骤**：
  1. 运行 `scripts/track_events.py`。
  2. 提取未来两周内的所有“高分”事件。
  3. 将事件同步至 Google Calendar 或 Slack 通道。
- **最佳实践**：在事件发生前 48 小时触发“准备检查清单”。

### 3. 交易计划关联 (Trade Plan Integration)
- **操作步骤**：
  1. 针对每个事件，关联“如果 A 发生，则执行 B”的逻辑（If-Then Scenarios）。
  2. 记录当前持仓的止损价和止盈位（Stop-loss / Take-profit）。
  3. 评估事件后的“情绪漂移”（Post-event Drift）。
- **最佳实践**：不仅记录“何时发生”，更要记录“如果结果不及预期，市场最可能的杀跌幅度是多少”。

### 4. 历史回测与归因分析 (Post-mortem)
- **操作步骤**：
  1. 记录事件前后的真实股价波动。
  2. 对比共识预期与真实数据。
  3. 为下一次类似事件优化“影响力得分”。

## 常用命令/模板 / Common Patterns

### 事件监控 JSON 模板 (Events JSON)
```json
{
  "ticker": "TSLA",
  "event_type": "Product Launch",
  "event_name": "Robotaxi Day",
  "date": "2026-08-08",
  "priority": "Critical",
  "implied_move": "±8.5%",
  "scenario_analysis": {
    "Bull": "Full FSD integration roadmap shared -> Target $280",
    "Bear": "Vague delay or regulatory hurdles -> Target $210"
  }
}
```

### 每周催化剂清单模板 (Weekly Catalyst List)
```markdown
### 🗓️ 本周核心催化剂 (2026-03-30 ~ 2026-04-03)

**1. [高优先级] NVDA GTC 大会 (周二)**:
- **预期**: 发布 B100 架构详情。
- **仓位风险**: 重仓持有中，建议买入 Puts 对冲潜在的“Sell the news”。

**2. [中优先级] PCE 物价指数发布 (周五)**:
- **预期**: 2.6% (YoY)。
- **市场含义**: 如果 > 2.8%，降息预期可能进一步推迟。

**3. [低优先级] AAPL 股息除权日 (周三)**:
- **操作**: 保持现状，无需额外动作。
```

### 快速查询示例
```bash
# 获取特定标的的未来事件
python scripts/track_events.py --ticker MSFT --range 30d
```

## 进阶应用场景 / Advanced Use Cases

### 1. 并购套利监控 (M&A Arbitrage)
- 监控某一并购案的所有监管审批节点（反垄断审查、股东大会投票、反向收购限期），实时计算“Deal Spread”（价差），并在价差异常收窄或扩大时报警。

### 2. 生物医药 FDA “开盲盒”
- 针对生物科技公司，跟踪 PDUFA 日期，并结合 `tavily-search` 抓取临床试验数据的专家讨论摘要。

## 边界与限制 / Boundaries

- **信息滞后风险**：部分事件（如突发性的股东减持或 CFO 辞职）无法预知，本技能仅能跟踪“已知”日历。
- **日期变动风险**：财报日期和产品发布日期经常发生“跳票”，需每日刷新 `npx github-ops` 类似的检查。
- **情绪误读**：即使事件结果是利好，如果已经被市场提前计价（Priced-in），股价仍可能下跌。
- **配额限制**：频繁抓取全球金融日历可能消耗较多 API Quota。
- **执行依赖**：本技能只提供“日历”和“建议”，不执行具体的买卖交易指令。

## 最佳实践总结

1. **专注影响力**：过滤掉那些对股价无实质影响的琐碎会议。
2. **提前布局**：在事件发生前一周完成仓位调整。
3. **多维同步**：事件日历应与 `portfolio-risk-manager` 技能打通。
4. **记录“意外”**：每次事件结果后的股价异常表现都要记入 `MEMORY.md`。
5. **来源可信度**：优先选择官网公告（Official IR）作为日期来源，而非第三方聚合网站。
6. **动态权重**：根据市场环境（牛市 vs 熊市）动态调整同一事件的影响力分值。
