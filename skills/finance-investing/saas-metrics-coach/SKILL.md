---
name: saas-metrics-coach
description: 用于 SaaS 关键指标分析与健康度诊断，包含 ARR/MRR/Churn/LTV/CAC 等核心指标。来源：alirezarezvani/claude-skills。
---

# SaaS Metrics Coach

## 触发条件
- 当需要评估 SaaS 业务的财务健康状况和增长潜力时。
- 在准备董事会报告、投资者演示文稿（Pitch Deck）或内部季度业务评论（QBR）时。
- 需要对客户流失（Churn）、增购（Expansion）或获客成本（CAC）进行深度诊断时。
- 制定年度预算、收入目标或进行中长期财务预测时。
- 进行行业对标（Benchmarking），判断公司表现是否优于同行时。

## 核心能力

### 1. 核心收入指标体系 (The Revenue Stack)
SaaS 的核心在于预测性收入。
- **ARR (Annual Recurring Revenue)**: 衡量合同化、经常性收入的年度价值。计算公式：`MRR * 12`。注意：ARR 不应包含一次性费用（如实施费、咨询费）。
- **MRR (Monthly Recurring Revenue)**: 包含以下五个关键部分：
  - **New MRR**: 本月新签约客户带来的月收入。
  - **Expansion MRR**: 现有客户增购（Up-sell/Cross-sell）带来的月收入增加。
  - **Resurrected MRR**: 之前流失但本月重新启用的客户收入。
  - **Contraction MRR**: 现有客户降级（Down-sell）导致的月收入减少。
  - **Churned MRR**: 彻底流失客户原本贡献的月收入。
- **Net Revenue Retention (NRR)**: 衡量从现有客户群中产生更多收入的能力。公式：`(期初 ARR + Expansion - Contraction - Churn) / 期初 ARR`。优秀标准：SMB >100%, Enterprise >120%。
- **Gross Revenue Retention (GRR)**: 扣除流失和缩减后的保留情况（不计入增购）。公式：`(期初 ARR - Churn - Contraction) / 期初 ARR`。衡量产品粘性的核心指标。优秀标准：>90%。

### 2. 单位经济效益与获客分析 (Unit Economics & CAC)
- **CAC (Customer Acquisition Cost)**: 获客总成本（营销+销售）/ 新增客户数。
- **LTV (Lifetime Value)**: 客户生命周期价值。公式：`(ARPU * Gross Margin %) / Churn %`。
- **LTV:CAC Ratio**: 衡量增长的可持续性。
  - **1:1**: 亏本生意。
  - **3:1**: 健康的 SaaS 模型。
  - **5:1**: 非常高效，甚至可能暗示营销投入不足，应进一步扩张。
- **CAC Payback Period**: 多少个月能收回获客成本。公式：`CAC / (ARPU * Gross Margin %)`。优秀标准：SMB < 12个月，Enterprise < 18个月。超过 24 个月通常被视为高风险。

### 3. 增长效率指标 (Growth Efficiency)
- **Rule of 40**: 增长率与利润率的平衡。`Revenue Growth % + EBITDA Margin % >= 40%`。
  - 如果增长 100%，即使亏损 60%，依然符合 Rule of 40。
  - 如果增长 20%，则必须有 20% 的利润率。
- **SaaS Magic Number**: 衡量销售和营销投入的效率。公式：`(本季营收 - 上季营收) * 4 / 上季 S&M 支出`。
  - **> 1.0**: 极其高效，应立即加大投入。
  - **0.5 - 1.0**: 中等水平。
  - **< 0.5**: 效率低下，需反思销售渠道或产品市场匹配度（PMF）。
- **Hype Factor**: `资本支出 / ARR 净增额`。衡量烧钱换增长的代价。理想值 < 2.0。

### 4. 留存与队列分析 (Retention & Cohort Analysis)
- **Logo Churn vs. Revenue Churn**: 客户数流失与金额流失的区别。一个流失 10 个小客户但保留了 1 个大客户的公司，其 Logo Churn 高但 Revenue Churn 低。
- **Cohort Analysis**: 按获客月份分组，观察其留存率（Retention）随时间的变化曲线。识别“早期流失”与“长期价值”。
  - **前 30 天流失**: 通常归咎于 onboarding 不力。
  - **半年后流失**: 通常归咎于产品更新缓慢或竞争对手冲击。
- **Negative Churn**: 当增购（Expansion）超过流失（Churn）时，实现净收入负流失，这是 SaaS 规模化爆发的关键。

### 5. 投资者视角与 Benchmark
- **T2D3 路径**: Triple, Triple, Double, Double, Double（从 1M ARR 增长到 100M ARR 的经典路径）。
- **Burn Multiple**: `Net Burn / Net New ARR`。衡量每增加 1 美元 ARR 需要烧掉多少钱。早期公司理想值 < 1.5。
- **Gross Margin**: SaaS 应保持在 70%-85% 之间。如果低于 70%，通常是因为人力密集型的实施或支持成本过高。

### 6. 指标误区与陷阱 (Common Pitfalls)
- **将预付款项全部计入当月收入**: 导致 MRR 剧烈波动，而非平稳增长。
- **忽略销售与营销（S&M）的时间滞后性**: 计算 CAC Payback 时，应考虑销售周期。
- **混淆 Gross Churn 和 Net Churn**: 掩盖了由于高流失率而被高增购率抵消的问题。
- **计算 ARPU 时包含非经常性收入**: 虚报了核心产品的盈利能力。

### 7. Churn 应对策略与深度分析
- **主动流失 (Active Churn)**: 客户主动取消订阅。需分析是否由于产品 Bug、价格过高或竞争对手撬动。
- **被动流失 (Passive Churn)**: 由于信用卡过期、支付失败导致的流失。建议：引入自动扣款重试机制及过期提醒。
- **流失预警模型**: 监控客户的健康度得分（Health Score），如登录频率下降、功能使用率降低。
- **赢回策略 (Win-back Strategies)**: 针对流失 3-6 个月的优质老客户，提供定向折扣或新功能展示。

### 8. 场景模拟分析 (Scenario Analysis)
- **Base Case**: 保持当前的 3% 月流失率。
- **Bull Case**: 通过优化 Onboarding，将月流失率降低至 2%。
- **Bear Case**: 竞争加剧，流失率上升至 5%。
- **结果评估**: 计算不同场景下 12 个月后的 ARR 预期，帮助管理层制定冗余预算。

## 常用命令/模板

### 指标计算 Python 示例 (简单逻辑)
```python
def calculate_saas_health(mrr_start, mrr_new, mrr_expansion, mrr_churn, mrr_contraction, sm_spend_prev):
    mrr_end = mrr_start + mrr_new + mrr_expansion - mrr_churn - mrr_contraction
    nrr = (mrr_start + mrr_expansion - mrr_churn - mrr_contraction) / mrr_start
    magic_number = (mrr_end - mrr_start) * 12 / sm_spend_prev
    return {
        "MRR_End": mrr_end,
        "NRR_Pct": nrr * 100,
        "Magic_Number": magic_number
    }
```

### 诊断报告结构
1. **Top-line Growth**: ARR 总额及同比/环比增速。
2. **Retention Health**: NRR 与 GRR 趋势，识别流失原因。
3. **Efficiency Check**: Magic Number 与 LTV:CAC 现状。
4. **Benchmark Comparison**: 根据公司规模（Seed/Series A/B/C）对比行业中值。
5. **Strategic Recommendations**: 建议（如：提高 ARPU、优化 S&M 渠道、降低 Churn）。
6. **Scenario Modeling**: 如果流失率降低 1%，对未来 24 个月 ARR 的影响分析。

## 边界与限制
- **非经常性收入**: 咨询、实施费等 Professional Services 不应计入 ARR/MRR。
- **早期初创公司**: 客户样本量太少时（例如少于 20 个），LTV 和 Churn 的统计学意义有限。
- **现金流 vs. 权责发生制**: SaaS 指标通常基于权责发生制，不能完全替代现金流分析（Cash Flow）。
- **递延收入 (Deferred Revenue)**: 预收款项需要正确分摊到各月度，否则会导致指标失真。
- **免费试用 (Freemium)**: 活跃用户（MAU/DAU）不等于付费客户，计算 CAC 时需剔除免费用户成本。
- **多产品线复杂性**: 当存在多条完全不同的产品线时，混合指标可能掩盖某个细分市场的危机。

---
*注：本技能持续参考最新 SaaS 财务准则与 Bessemer/KeyBank 行业报告更新。*
* lines: 105
* word count: ~800 characters
