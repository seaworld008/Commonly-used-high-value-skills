# Revenue Analytics

## Core SaaS Metrics

| Metric | Formula | Target |
|--------|---------|--------|
| **MRR** | Sum of active subscriptions | > 5% MoM growth |
| **ARR** | MRR x 12 | Benchmark comparison |
| **ARPU** | MRR / Active paying users | Increasing trend |
| **LTV** | ARPU x Avg lifespan | LTV:CAC > 3:1 |
| **CAC** | Total spend / New customers | Decreasing trend |
| **Net Revenue Retention** | (MRR - Contraction - Churn + Expansion) / MRR | > 100% |

## MRR Movement Tracking

```typescript
interface MRRMovement {
  period: string;
  startMRR: number;
  newMRR: number;
  expansionMRR: number;
  contractionMRR: number;
  churnedMRR: number;
  reactivationMRR: number;
  endMRR: number;
}
```

## LTV Calculation Methods

### Simple: `ARPU / Churn Rate`
### Cohort-Based: Fit exponential decay curve to actual revenue data

## Churn Analysis SQL

```sql
SELECT cancellation_reason, COUNT(*) as count, SUM(mrr) as lost_mrr,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as pct
FROM cancellations
WHERE cancelled_at >= DATE_TRUNC(CURRENT_DATE, MONTH)
GROUP BY cancellation_reason ORDER BY lost_mrr DESC;
```

## At-Risk Account Scoring

Risk factors and weights:
- Usage decline (> 30% drop): +30 points
- Inactivity (> 14 days): +25 points
- Open support tickets (> 3): +20 points
- Low feature adoption (< 3 features): +15 points
- Low NPS (< 7): +10 points

Threshold: Score > 60 = At Risk
