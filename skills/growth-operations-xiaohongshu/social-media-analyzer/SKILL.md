---
name: social-media-analyzer
description: 'Analyze social campaign engagement, ROI, audience behavior, and platform comparisons from supplied or retrieved performance data.'
zh_description: "分析社交媒体互动、受众、活动收益和跨平台表现。"
version: "1.0.2"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["analyzer", "growth", "marketing", "media", "social"]'
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 5
complexity: "intermediate"
triggers:
---

# Social Media Analyzer

Campaign performance analysis with engagement metrics, ROI calculations, and platform benchmarks.

---

## Table of Contents

- [Analysis Workflow](#analysis-workflow)
- [Engagement Metrics](#engagement-metrics)
- [ROI Calculation](#roi-calculation)
- [Platform Benchmarks](#platform-benchmarks)
- [Tools](#tools)
- [Examples](#examples)

---

## Analysis Workflow

Analyze social media campaign performance:

1. Validate input data completeness (reach > 0, dates valid)
2. Calculate engagement metrics per post
3. Aggregate campaign-level metrics
4. Calculate cost metrics when spend is provided; calculate actual ROI/ROAS only with attributable value/revenue
5. Compare against platform benchmarks
6. Identify top and bottom performers
7. Generate recommendations
8. **Validation:** Engagement rate < 100%, ROI matches spend data

### Input Requirements

| Field | Required | Description |
|-------|----------|-------------|
| platform | Yes | instagram, facebook, twitter, linkedin, tiktok |
| posts[] | Yes | Array of post data |
| posts[].likes | Yes | Like/reaction count |
| posts[].comments | Yes | Comment count |
| posts[].reach | Yes | Unique users reached |
| posts[].impressions | No | Total views |
| posts[].shares | No | Share/retweet count |
| posts[].saves | No | Save/bookmark count |
| posts[].clicks | No | Link clicks |
| total_spend | No | Ad spend (for ROI) |

### Data Validation Checks

Before analysis, verify:

- [ ] Reach > 0 for all posts (avoid division by zero)
- [ ] Engagement counts are non-negative
- [ ] Date range is valid (start < end)
- [ ] Platform is recognized
- [ ] Spend > 0 if ROI requested

---

## Engagement Metrics

### Engagement Rate Calculation

```
Engagement Rate = (Likes + Comments + Shares + Saves) / Reach × 100
```

### Metric Definitions

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| Engagement Rate | Engagements / Reach × 100 | Audience interaction level |
| CTR | Clicks / Impressions × 100 | Content click appeal |
| Reach Rate | Reach / Followers × 100 | Content distribution |
| Virality Rate | Shares / Impressions × 100 | Share-worthiness |
| Save Rate | Saves / Reach × 100 | Content value |

### Performance Categories

| Rating | Engagement Rate | Action |
|--------|-----------------|--------|
| Excellent | > 6% | Scale and replicate |
| Good | 3-6% | Optimize and expand |
| Average | 1-3% | Test improvements |
| Poor | < 1% | Analyze and pivot |

---

## ROI Calculation

Separate observed costs from scenario value:

1. Sum engagements and compute CPE/CPC from actual spend.
2. The bundled calculator assigns a fixed illustrative $2.50 to every engagement. Its `estimated_value` and `roi_percentage` are scenario outputs, not attributed revenue or realized ROI.
3. Actual ROAS requires attributable revenue / ad spend; actual ROI additionally needs the agreed value/cost basis. If revenue is missing, list it as missing and do not recommend budget expansion from simulated returns.

### ROI Formulas

| Metric | Formula |
|--------|---------|
| Cost Per Engagement (CPE) | Total Spend / Total Engagements |
| Cost Per Click (CPC) | Total Spend / Total Clicks |
| Cost Per Thousand (CPM) | (Spend / Impressions) × 1000 |
| Return on Ad Spend (ROAS) | Revenue / Ad Spend |

### Engagement Value Assumption

The current implementation uses total engagements × $2.50 regardless of action type. It does not accept a valuation input. Show this fixed assumption beside any scenario output; if the task needs different assumptions, calculate and label them separately. Do not apply the script's ROI-based scaling recommendations without actual revenue evidence.

---

## Platform Benchmarks

### Engagement Rate by Platform

| Platform | Average | Good | Excellent |
|----------|---------|------|-----------|
| Instagram | 1.22% | 3-6% | >6% |
| Facebook | 0.07% | 0.5-1% | >1% |
| Twitter/X | 0.05% | 0.1-0.5% | >0.5% |
| LinkedIn | 2.0% | 3-5% | >5% |
| TikTok | 5.96% | 8-15% | >15% |

### CTR by Platform

| Platform | Average | Good | Excellent |
|----------|---------|------|-----------|
| Instagram | 0.22% | 0.5-1% | >1% |
| Facebook | 0.90% | 1.5-2.5% | >2.5% |
| LinkedIn | 0.44% | 1-2% | >2% |
| TikTok | 0.30% | 0.5-1% | >1% |

### CPC by Platform

| Platform | Average | Good |
|----------|---------|------|
| Facebook | $0.97 | <$0.50 |
| Instagram | $1.20 | <$0.70 |
| LinkedIn | $5.26 | <$3.00 |
| TikTok | $1.00 | <$0.50 |

See `references/platform-benchmarks.md` for complete benchmark data.

---

## Tools

### Calculate Metrics and Analyze Performance

Both scripts expose Python classes and have no CLI entry. From the skill directory:

```bash
python3 -c 'import sys,json; from pathlib import Path; sys.path.insert(0,"scripts"); from calculate_metrics import SocialMediaMetricsCalculator; from analyze_performance import PerformanceAnalyzer; d=json.loads(Path("assets/sample_input.json").read_text()); r=SocialMediaMetricsCalculator(d).analyze_all(); a=PerformanceAnalyzer(r["campaign_metrics"],r["roi_metrics"]); print(json.dumps({**r,"insights":a.generate_insights()},indent=2))'
```

The current campaign aggregate counts likes + comments + shares, while per-post rates also include saves. Keep these definitions explicit; their rates are not directly interchangeable. The calculator returns campaign metrics, scenario ROI and top posts; the analyzer consumes the calculated campaign and ROI objects for benchmark comparisons and insights. Review any recommendation against the scenario limitation above before including it in the report.

---

## Examples

### Sample Input

See `assets/sample_input.json`:

```json
{
  "platform": "instagram",
  "total_spend": 500,
  "posts": [
    {
      "post_id": "post_001",
      "content_type": "image",
      "likes": 342,
      "comments": 28,
      "shares": 15,
      "saves": 45,
      "reach": 5200,
      "impressions": 8500,
      "clicks": 120
    }
  ]
}
```

### Sample Output

Current output excerpt for the complete `assets/sample_input.json` (the historical `assets/expected_output.json` differs from current implementation):

```json
{
  "campaign_metrics": {
    "total_engagements": 1374,
    "avg_engagement_rate": 7.549450549450549,
    "ctr": 1.55
  },
  "roi_metrics": {
    "total_spend": 500.0,
    "cost_per_engagement": 0.36,
    "roi_percentage": 587.0
  },
  "insights": {
    "overall_health": "excellent",
    "benchmark_comparison": {
      "engagement_status": "excellent",
      "engagement_benchmark": "1.22%",
      "engagement_actual": "7.55%"
    }
  }
}
```

### Interpretation

The sample campaign shows:
- **Campaign engagement rate 7.55%** vs built-in 1.22% benchmark = Excellent (about 6.2x)
- **CTR 1.55%** vs 0.22% benchmark = Excellent (7x above average)
- **Scenario ROI 587%** uses an assumed engagement value; it does not establish realized return on $500 spend.
- **Recommendation:** Test successful creative elements; verify attributed revenue and conversion quality before deciding whether to increase spend.

---

## Reference Documentation

### Platform Benchmarks

`references/platform-benchmarks.md` contains:

- Engagement rate benchmarks by platform and industry
- CTR benchmarks for organic and paid content
- Cost benchmarks (CPC, CPM, CPE)
- Content type performance by platform
- Optimal posting times and frequency
- ROI calculation formulas
