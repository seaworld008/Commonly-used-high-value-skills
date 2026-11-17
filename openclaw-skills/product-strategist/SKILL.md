---
name: product-strategist
description: 'Strategic product leadership toolkit for Head of Product including OKR cascade generation, market analysis, vision setting, and team scaling. Use for strategic planning, goal alignment, competitive analysis, and organizational design.'
zh_description: "制定产品愿景、目标、市场分析和团队发展策略。"
version: "1.0.2"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["design", "product", "strategist"]'
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 5
complexity: "intermediate"
---

# Product Strategist

Strategic toolkit for Head of Product to drive vision, alignment, and organizational excellence.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Core Capabilities](#core-capabilities)
- [Workflow: Strategic Planning Session](#workflow-strategic-planning-session)
- [OKR Cascade Generator](#okr-cascade-generator)
  - [Usage](#usage)
  - [Configuration Options](#configuration-options)
  - [Input/Output Examples](#inputoutput-examples)
- [Reference Documents](#reference-documents)

---

## Quick Start

### Generate OKRs for Your Team

```bash
# Growth strategy with default teams
python scripts/okr_cascade_generator.py growth

# Retention strategy with custom teams
python scripts/okr_cascade_generator.py retention --teams "Engineering,Design,Data"

# Revenue strategy with 40% product contribution
python scripts/okr_cascade_generator.py revenue --contribution 0.4

# Export a draft for per-KR review
python scripts/okr_cascade_generator.py growth --json > okrs.json
```

---

## Core Capabilities

| Capability | Description | Tool |
|------------|-------------|------|
| **OKR Cascade** | Generate aligned OKRs from company to team level | `okr_cascade_generator.py` |
| **Alignment Scoring** | Measure vertical and horizontal alignment | Built into generator |
| **Strategy Templates** | 5 pre-built strategy types | Growth, Retention, Revenue, Innovation, Operational |
| **Team Configuration** | Customize for your org structure | `--teams` flag |

---

## Workflow: Strategic Planning Session

A step-by-step guide for running a quarterly strategic planning session.

### Step 1: Define Strategic Focus

Choose the primary strategy type based on company priorities:

| Strategy | When to Use |
|----------|-------------|
| **Growth** | Scaling user base, market expansion |
| **Retention** | Reducing churn, improving LTV |
| **Revenue** | Increasing ARPU, new monetization |
| **Innovation** | Market differentiation, new capabilities |
| **Operational** | Improving efficiency, scaling operations |

See `references/strategy_types.md` for detailed guidance on each strategy.

### Step 2: Gather Input Metrics

Collect current state metrics to inform OKR targets:

```bash
# Example metrics JSON
{
  "current": 100000,      # Current MAU
  "target": 150000,       # Target MAU
  "current_nps": 40,      # Current NPS
  "target_nps": 60        # Target NPS
}
```

### Step 3: Configure Team Structure

Define the teams that will receive cascaded OKRs:

```bash
# Default teams
python scripts/okr_cascade_generator.py growth

# Custom teams for your organization
python scripts/okr_cascade_generator.py growth --teams "Core,Platform,Mobile,AI"
```

### Step 4: Generate OKR Cascade

Run the generator to create aligned OKRs:

```bash
python scripts/okr_cascade_generator.py growth --contribution 0.3
```

### Step 5: Review Alignment Scores

Check the alignment scores in the output:

| Score | Target | Action |
|-------|--------|--------|
| Vertical Alignment | >90% | Ensure all objectives link to parent |
| Horizontal Alignment | >75% | Check for team coordination |
| Coverage | >80% | Validate all company OKRs are addressed |
| Balance | >80% | Redistribute if one team is overloaded |
| **Overall** | **>80%** | Good alignment; <60% needs restructuring |

### Step 6: Refine and Validate

Before finalizing:

- [ ] Review generated objectives with stakeholders
- [ ] Adjust team assignments based on capacity
- [ ] Verify each KR's unit, baseline, target, direction and owner. Allocate contributions only for additive increments.
- [ ] Ensure no conflicting objectives across teams
- [ ] Set up tracking cadence (bi-weekly check-ins)

### Step 7: Export and Track

Export a draft, reconcile its metrics with the reviewed targets, and import the reviewed copy into your tracking system:

```bash
# Draft JSON for review before import
python scripts/okr_cascade_generator.py growth --json > q1_okrs.json
```

---

## OKR Cascade Generator

Automatically cascades company OKRs down to product and team levels with alignment tracking.

### Usage

```bash
python scripts/okr_cascade_generator.py [strategy] [options]
```

**Strategies:**
- `growth` - User acquisition and market expansion
- `retention` - Customer value and churn reduction
- `revenue` - Revenue growth and monetization
- `innovation` - Product differentiation and leadership
- `operational` - Efficiency and organizational excellence

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `--teams`, `-t` | Comma-separated team names | Growth,Platform,Mobile,Data |
| `--contribution`, `-c` | Product contribution to company OKRs (0-1) | 0.3 (30%) |
| `--json`, `-j` | Output as JSON instead of dashboard | False |
| `--metrics`, `-m` | Metrics as JSON string | Sample metrics |

**Examples:**

```bash
# Custom teams
python scripts/okr_cascade_generator.py retention \
  --teams "Engineering,Design,Data,Growth"

# Higher product contribution
python scripts/okr_cascade_generator.py revenue --contribution 0.4

# Full customization
python scripts/okr_cascade_generator.py innovation \
  --teams "Core,Platform,ML" \
  --contribution 0.5 \
  --json
```

### Input/Output Examples

#### Example 1: Review a growth cascade

```bash
python scripts/okr_cascade_generator.py growth
```

Use the generated IDs and parent links to draft the hierarchy. The script reuses one metric across company KRs and scales the end target for product KRs. Review each number before using the draft for planning.

The following review uses the example growth data in `references/examples/sample_growth_okrs.json`:

| Company KR | Unit | Baseline | Target | Direction |
|---|---|---:|---:|---|
| Monthly active users | users | 100,000 | 150,000 | increase |
| Month-over-month growth | % per month | 8 | 15 | increase |
| Expansion into new markets | markets | 0 | 3 | increase |

For the 50,000 additional MAU, a 30% product contribution would be 15,000 additional users if attribution is additive and users are counted once. Link the product KR to CO-1-KR1 and assign team contributions only where their populations can be distinguished. Measure rates with their own denominators. Mark a missing baseline, target or unit as pending.

#### Example 2: JSON Output

**Command:**
```bash
python scripts/okr_cascade_generator.py retention --json
```

Inspect the retention JSON's `company`, `product` and `teams` entries. Follow each `contributes_to` link and compare the child's unit, baseline and direction with the parent. Replace reused growth counts with verified retention rates before reporting them.

See `references/examples/sample_growth_okrs.json` for a complete example.

---

## Reference Documents

| Document | Description |
|----------|-------------|
| `references/okr_framework.md` | OKR methodology, writing guidelines, alignment scoring |
| `references/strategy_types.md` | Detailed breakdown of all 5 strategy types with examples |
| `references/examples/sample_growth_okrs.json` | Worked growth cascade with separate targets for each KR |

---

## Best Practices

### OKR Cascade

- Limit to 3-5 objectives per level
- Each objective should have 3-5 key results
- Key results must be measurable with current and target values
- Validate parent-child relationships before finalizing

### Alignment Scoring

- Target >80% overall alignment
- Investigate any score below 60%
- Balance scores ensure no team is overloaded
- Horizontal alignment prevents conflicting goals

### Team Configuration

- Configure teams to match your actual org structure
- Adjust contribution percentages based on team size
- Platform/Infrastructure teams often support all objectives
- Specialized teams (ML, Data) may only support relevant objectives

---

## Quick Reference

```bash
# Common commands
python scripts/okr_cascade_generator.py growth               # Default growth
python scripts/okr_cascade_generator.py retention            # Retention focus
python scripts/okr_cascade_generator.py revenue -c 0.4       # 40% contribution
python scripts/okr_cascade_generator.py growth --json        # JSON export
python scripts/okr_cascade_generator.py growth -t "A,B,C"    # Custom teams
```
