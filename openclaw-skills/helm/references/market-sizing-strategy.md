# Market Sizing for Strategic Context — Helm

Purpose: Use this file when Helm needs to incorporate market size data into strategic simulation, market entry evaluation, portfolio allocation, or growth planning.

## Contents

- Market sizing in strategic context
- Consumption from Compete
- Strategic application of TAM/SAM/SOM
- Market entry decision framework
- Portfolio sizing
- Templates

## Market Sizing in Strategic Context

### Helm's Role vs Compete's Role

| Responsibility | Owner | Description |
|---|---|---|
| Market size estimation | **Compete** | Primary research, calculation, cross-verification |
| Strategic interpretation | **Helm** | Using market size for decisions, simulations, forecasts |

Helm does not estimate market size from scratch. Helm consumes market sizing data from Compete (via `COMPETE_TO_HELM` handoff) or from provided context, and applies it to strategic frameworks.

### When Helm Needs Market Sizing

| Strategic question | How market sizing helps |
|---|---|
| Should we enter this market? | SAM validates sufficient opportunity |
| How fast can we grow? | SOM vs SAM ratio reveals headroom |
| Should we invest or harvest? | TAM growth rate drives BCG quadrant |
| Which segment to prioritize? | Segment-level SAM comparison |
| Is acquisition justified? | Target's SAM + our SAM = combined opportunity |
| When do we hit diminishing returns? | SOM approaching SAM ceiling signals pivot need |

## Strategic Application of TAM/SAM/SOM

### Market Headroom Analysis

```markdown
## Market Headroom: [Product/Segment]

### Current Position
- Current revenue: $[X]
- Current market share (of SAM): [X]%
- SOM: $[X] ([X]% of SAM)
- SAM: $[X] ([X]% of TAM)
- TAM: $[X]

### Headroom Assessment
| Metric | Value | Implication |
|---|---|---|
| SOM / SAM ratio | [X]% | [< 10% = early, 10-30% = growing, > 30% = nearing ceiling] |
| SAM / TAM ratio | [X]% | [< 20% = niche, 20-50% = focused, > 50% = broad] |
| TAM CAGR | [X]% | [< 5% = mature, 5-15% = growing, > 15% = high-growth] |
| Years to SAM ceiling | [X] years | [at current growth rate] |

### Strategic Implication
- Growth headroom: [abundant / adequate / limited / exhausted]
- Recommended strategy: [penetrate / expand SAM / expand TAM / diversify]
```

### Market Size in Scenario Simulation

Integrate market sizing into Helm's 3-scenario model:

```text
Baseline scenario:
  Revenue = SOM × execution factor (0.8-1.0)

Optimistic scenario:
  Revenue = SOM × (1 + market expansion factor)
  where market expansion = SAM growth + share gain

Pessimistic scenario:
  Revenue = SOM × (1 - competitive erosion factor)
  where competitive erosion = new entrant impact + churn increase
```

## Market Entry Decision Framework

### Go/No-Go Inputs from Market Sizing

```markdown
## Market Entry Analysis: [Target Market]

### Market Attractiveness
| Factor | Score (1-5) | Weight | Weighted score |
|---|---|---|---|
| TAM size | | 15% | |
| TAM growth rate | | 20% | |
| SAM accessibility | | 20% | |
| Competitive intensity (inverse) | | 15% | |
| Margin potential | | 15% | |
| Strategic fit | | 15% | |
| **Total** | | 100% | **[X/5]** |

### Entry Threshold Rules
| Score | Decision |
|---|---|
| ≥ 4.0 | Strong go — prioritize entry |
| 3.0-3.9 | Conditional go — validate key assumptions |
| 2.0-2.9 | Weak — needs compelling strategic rationale beyond market size |
| < 2.0 | No go — insufficient opportunity |

### Simulation Integration
- Feed attractiveness score into Helm scenario simulation
- Model entry investment against SOM ramp-up timeline
- Include competitive response scenarios (from Compete wargaming if available)
```

## Portfolio Sizing

### Multi-Market Portfolio View

```markdown
## Portfolio Market Sizing

| Product / Segment | TAM | SAM | SOM | Current revenue | Headroom | Priority |
|---|---|---|---|---|---|---|
| [Product A] | $X | $X | $X | $X | [X]% | H/M/L |
| [Product B] | $X | $X | $X | $X | [X]% | H/M/L |
| [Product C] | $X | $X | $X | $X | [X]% | H/M/L |

### BCG Integration
- Stars: [products with high TAM growth + high share]
- Cash Cows: [products with low TAM growth + high share]
- Question Marks: [products with high TAM growth + low share]
- Dogs: [products with low TAM growth + low share]

### Resource Allocation Recommendation
| Product | BCG quadrant | Recommended investment | Market sizing rationale |
|---|---|---|---|
| [Product A] | [quadrant] | [invest/maintain/harvest/divest] | [TAM/SAM/SOM justification] |
```

## Templates

### Compete-to-Helm Market Sizing Handoff

Expected format when receiving market sizing from Compete:

```yaml
COMPETE_TO_HELM:
  market: "[market name]"
  tam: "$[X]"
  tam_cagr: "[X]%"
  sam: "$[X]"
  som: "$[X]"
  estimation_method: "[top-down / bottom-up / both]"
  cross_verification: "[aligned / divergent — details]"
  confidence: "[high / medium / low]"
  key_assumptions:
    - "[assumption 1]"
    - "[assumption 2]"
  competitive_context:
    market_structure: "[monopoly / oligopoly / fragmented]"
    top_3_share: "[X]%"
    our_position: "[leader / challenger / niche / entrant]"
```

If this handoff data is not available, Helm should request it via `HELM_REQUEST_COMPETE` or note the gap explicitly in assumptions.
