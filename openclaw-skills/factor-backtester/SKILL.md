---
name: factor-backtester
description: 'Use when testing factor signals, running long-short spread backtests, checking hit rate and turnover, or sanity-checking whether a ranking signal survives basic transaction cost assumptions.'
---

# Factor Backtester

Evaluate whether a factor has enough edge to deserve more work.

## When to Use

- Signal research
- Cross-sectional ranking tests
- PM review of quant ideas
- Research handoff before deeper infrastructure work

## Workflow

1. Prepare a period-by-period long return, short return, benchmark return, and turnover series.
2. Run `scripts/backtest_factor.py`.
3. Review cumulative return, benchmark comparison, hit rate, and turnover.
4. Reject signals that only work before costs or in tiny samples.

## Tool

```bash
python scripts/backtest_factor.py assets/sample_factor_data.json
```

## Benchmark Notes

- Qlib covers the full quant chain from data processing to backtesting and order execution, so this skill should be treated as a lightweight screening layer, not the final research engine.
- LEAN provides event-driven, production-grade backtesting and live-trading workflows; use that bar when deciding what “real usable” should mean.

## References

- `references/backtest-checklist.md`
