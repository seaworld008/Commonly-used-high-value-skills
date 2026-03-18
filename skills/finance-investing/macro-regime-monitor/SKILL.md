---
name: macro-regime-monitor
description: Use when tracking macro regime shifts, summarizing inflation, growth, spreads, and liquidity signals, or creating a house view before updating sector or asset-allocation calls.
---

# Macro Regime Monitor

Reduce macro noise into a regime call that can actually inform positioning.

## When to Use

- Weekly macro note
- Asset-allocation meetings
- Risk-on versus risk-off framing
- Cross-asset positioning updates

## Workflow

1. Update the latest inflation, growth, spreads, and liquidity readings.
2. Run `scripts/classify_regime.py`.
3. Review the scorecard and current regime.
4. Add watch items that could flip the call.

## Tool

```bash
python scripts/classify_regime.py assets/sample_macro_data.json
```

## Benchmark Notes

- OpenBB and similar platforms show the value of pulling macro and market data into one normalized interface.
- Good macro workflows stay explicit about which indicators changed the call, instead of hiding everything behind a black-box label.

## References

- `references/regime-framework.md`

