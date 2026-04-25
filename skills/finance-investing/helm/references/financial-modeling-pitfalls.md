Purpose: Use this reference when Helm models SaaS, growth, runway, or investment outcomes. It preserves the key modeling traps, 2025 benchmark ranges, and alert thresholds used in strategic simulation.

## Contents
- `FM-01..FM-10`
- SaaS benchmarks
- scenario design guidance
- Helm alert thresholds

# Financial Modeling Pitfalls & SaaS Benchmarks 2025

## Financial Modeling Anti-Patterns

| ID | Pitfall | Failure mode | Fix |
|---|---|---|---|
| `FM-01` | Underestimating churn | Retention assumptions are too optimistic | Model churn by segment and by voluntary/involuntary components |
| `FM-02` | Ignoring the J-curve | Payback and cash recovery are understated | Track CAC payback and monthly burn explicitly |
| `FM-03` | Ignoring step costs | Costs are modeled as linear when they jump at thresholds | Define infrastructure and headcount trigger points |
| `FM-04` | Hard-coded assumptions | Sensitivity analysis becomes impossible | Separate assumptions into parameter tables |
| `FM-05` | Generic template dependence | Business model-specific drivers disappear | Model with domain-specific drivers |
| `FM-06` | Flat expansion-rate logic | Expansion revenue is treated as a single percentage | Split seat growth, tier upgrades, and usage expansion |
| `FM-07` | GTM shift not reflected | Legacy assumptions remain after GTM changes | Rebuild conversion, CAC, and retention after GTM changes |
| `FM-08` | Single-scenario planning | Risk is hidden behind one narrative | Always build `3+` scenarios; use `1.8x` as a fundraising-rate reminder |
| `FM-09` | No actual-vs-plan review | Model quality never improves | Review monthly and version assumptions |
| `FM-10` | No cohort analysis | Generational behavior differences are hidden | Track cohort churn, LTV, and expansion |

## SaaS Benchmarks

### Core Metrics

| Metric | Benchmark | Interpretation |
|---|---|---|
| Rule of 40 | `50%+` top quartile | `<20%` is a warning |
| Burn Multiple | `<1.0x` at `$25-50M ARR` | `>2.0x` is a red flag |
| NRR | overall median `106%` (2026); segment: Enterprise ACV >$100K `118%`, Mid-Market `108%`, SMB `97%`; AI-native `132%`; top `120%+`; elite `130%+` | `<100%` means net shrink — apply segment context for SMB |
| Gross Margin | `70-80%` | SaaS baseline |
| CAC Payback | `12-18 months` | `>24 months` is weak |
| LTV:CAC | `3:1+` | below this suggests poor unit economics |
| Magic Number | `>0.75` | efficient sales and marketing spend |

### Churn Benchmarks

| Segment | Monthly churn | Annual churn |
|---|---|---|
| B2B SaaS overall | `0.3%-1.0%` | `3.5%-5%` |
| Enterprise | `<=1.0%` | `<=10%` |
| SMB | `3%-7%` | `30%-58%` |
| Usage-based / freemium | `5%-10%+` | `50%+` |
| B2C SaaS | `0.4%-1.0%` | `6%-8%` |

Additional churn split:

```text
Voluntary churn:    2.6%-3.3%
Involuntary churn:  0.8%-1.1%
```

## Scenario Design

| Scenario | Growth | Churn | Margin | Use |
|---|---|---|---|---|
| Bull | top-quartile | low-end benchmark | target `+5pt` | upside capacity planning |
| Base | current trajectory | current segment rate | current level | operating budget |
| Bear | roughly `50%` of current growth | benchmark upper bound | target `-10pt` | downside planning |
| Crisis | `0%` or negative | `2x` normal churn | major compression | survival planning |

### Assumption Management

1. Keep assumptions separate from formulas.
2. Tag each assumption by confidence.
3. Reconcile assumptions monthly against actuals.
4. Run `±20%` sensitivity on major assumptions.
5. Never ship only one scenario.

### Checklist

- Churn is segmented.
- Expansion is modeled by mechanism.
- Step-cost thresholds exist.
- CAC is channel-specific.
- Seasonality is represented if material.
- GTM assumptions match the current motion.

## Helm Alert Thresholds

| Signal | Threshold | Response |
|---|---|---|
| Churn | `>1.5x` segment benchmark upper bound | `RED` |
| Burn Multiple | `>2.0x` | `RED` |
| Rule of 40 | `<20%` | `YELLOW` |
| NRR | `<100%` | `RED` |
| CAC Payback | `>24 months` | `YELLOW` |

## Helm Integration

Use this with:

- `SIMULATE` for financial scenario construction
- `ST-1` / `ST-2` patterns when modeling MRR, runway, or cash flow
- `ROADMAP` when deciding pace, investment, or hiring capacity
- `FORESIGHT` when comparing model outputs against actual SaaS metrics
