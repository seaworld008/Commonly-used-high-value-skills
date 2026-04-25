# Alerts & Anomaly Detection

## Alert Types

| Alert Type | Description | Use Case | Channels |
|------------|-------------|----------|----------|
| **Threshold** | Static upper/lower bounds | Revenue, error rate | PagerDuty, Slack |
| **Anomaly** | Statistical deviation from baseline | DAU, conversion | Slack #metrics |
| **Trend** | Significant directional change | NPS, session duration | Slack #growth |
| **Missing Data** | Expected events not received | Tracking gaps | PagerDuty |
| **SLA** | Service level violations | Latency, uptime | PagerDuty |

## Z-Score Based Anomaly Detection

```typescript
interface AnomalyConfig {
  metric: string;
  lookbackDays: number;
  sensitivity: 'low' | 'medium' | 'high';
  direction: 'both' | 'up' | 'down';
}

const sensitivityThresholds = {
  low: 3.0,    // 99.7% confidence
  medium: 2.5, // 98.8% confidence
  high: 2.0,   // 95.4% confidence
};

function detectAnomaly(
  currentValue: number,
  historicalValues: number[],
  config: AnomalyConfig
): { isAnomaly: boolean; zScore: number; direction: string } {
  const mean = historicalValues.reduce((a, b) => a + b, 0) / historicalValues.length;
  const stdDev = Math.sqrt(
    historicalValues.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / historicalValues.length
  );
  if (stdDev === 0) return { isAnomaly: false, zScore: 0, direction: 'none' };
  const zScore = (currentValue - mean) / stdDev;
  const threshold = sensitivityThresholds[config.sensitivity];
  const direction = zScore > 0 ? 'up' : 'down';
  let isAnomaly = false;
  if (config.direction === 'both') isAnomaly = Math.abs(zScore) > threshold;
  else if (config.direction === 'up') isAnomaly = zScore > threshold;
  else isAnomaly = zScore < -threshold;
  return { isAnomaly, zScore: Math.round(zScore * 100) / 100, direction };
}
```

## Alert Rule Engine

```typescript
interface AlertRule {
  name: string;
  metric: string;
  condition: 'above' | 'below' | 'anomaly' | 'missing';
  threshold?: number;
  cooldownMinutes: number;
  channels: ('slack' | 'pagerduty' | 'email')[];
  severity: 'critical' | 'warning' | 'info';
}

const defaultRules: AlertRule[] = [
  {
    name: 'Revenue Drop',
    metric: 'daily_revenue',
    condition: 'below',
    threshold: 0.7,
    cooldownMinutes: 60,
    channels: ['slack', 'pagerduty'],
    severity: 'critical',
  },
  {
    name: 'Conversion Anomaly',
    metric: 'signup_conversion_rate',
    condition: 'anomaly',
    cooldownMinutes: 120,
    channels: ['slack'],
    severity: 'warning',
  },
];
```

## Slack Alert Template

```json
{
  "blocks": [
    {
      "type": "header",
      "text": { "type": "plain_text", "text": "Alert: [ALERT_NAME]" }
    },
    {
      "type": "section",
      "fields": [
        { "type": "mrkdwn", "text": "*Metric:* [METRIC]" },
        { "type": "mrkdwn", "text": "*Current:* [VALUE]" },
        { "type": "mrkdwn", "text": "*Expected:* [BASELINE]" },
        { "type": "mrkdwn", "text": "*Change:* [DELTA]%" }
      ]
    }
  ]
}
```
