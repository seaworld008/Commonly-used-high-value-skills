---
name: options-strategy-evaluator
description: 'Use when evaluating an options structure, checking expiry payoff checkpoints, comparing premium outlay versus downside protection, or preparing a short strategy note for a trade review.'
---

# Options Strategy Evaluator

Map an options idea into a payoff shape before anyone confuses structure with edge.

## When to Use

- Covered call, spread, or hedge reviews
- Earnings-event structure planning
- Premium income trade checks
- Risk committee or PM trade notes

## Workflow

1. Define the option legs, premiums, and price checkpoints.
2. Run `scripts/evaluate_strategy.py`.
3. Review net premium and payoff checkpoints.
4. Add the missing real-world overlays: implied vol, liquidity, early assignment, and path risk.

## Tool

```bash
python scripts/evaluate_strategy.py assets/sample_options_strategy.json
```

## Benchmark Notes

- QuantConnect LEAN explicitly supports options workflows, which is the right benchmark for strategy realism.
- QuantLib remains a strong open-source reference for more rigorous derivatives modeling when you outgrow simple expiry-payoff checks.

## References

- `references/options-review-checklist.md`
