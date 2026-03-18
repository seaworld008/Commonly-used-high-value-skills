---
name: comps-valuation-analyst
description: Use when valuing a public company with peer multiples, building comparable-company tables, or pressure-testing a valuation range with EV/EBITDA, P/E, and EV/Sales.
---

# Comps Valuation Analyst

Build a comparable-company valuation quickly, then explain the range like an equity research associate instead of dumping ratios without context.

## When to Use

- Relative valuation for a listed company
- Peer table construction for IC, memo, or earnings prep
- Cross-checking a DCF with market-based multiples
- Framing bull/base/bear valuation bands

## Workflow

1. Confirm the subject company, peer set, currency, and reporting basis.
2. Normalize EBITDA, EPS, revenue, net debt, and share count.
3. Run `scripts/calculate_comps.py` on the JSON input.
4. Explain which multiple deserves the most weight and why.
5. Call out where the peer set is distorted by growth, cyclicality, or capital structure.

## Tool

```bash
python scripts/calculate_comps.py assets/sample_comps_input.json
```

## Output

- Implied price range by multiple
- Peer median statistics
- Subject-versus-peer comparison summary

## Benchmark Notes

- OpenBB emphasizes broad public-market data access for analysts and quants, so peer-data completeness matters.
- FinRobot highlights valuation plus risk assessment in the same workflow, so always pair the multiple range with key caveats.
- PyPortfolioOpt is not a comps tool, but its modularity principle is worth copying: keep inputs explicit and swappable.

## References

- `references/comps-methodology.md`

