---
name: portfolio-risk-manager
description: 'Use when reviewing portfolio exposures, checking concentration and beta risk, summarizing sector or region tilts, or preparing a risk note before reallocating capital.'
---

# Portfolio Risk Manager

Summarize the portfolio like a risk meeting would: concentration, exposure, beta, volatility, and where the portfolio is leaning too hard.

## When to Use

- Weekly PM review
- Pre-trade risk sanity check
- Investor letter prep
- Position sizing discussions

## Workflow

1. Normalize current holdings and weights.
2. Run `scripts/portfolio_risk.py`.
3. Check weighted beta, volatility proxy, and concentration.
4. Decide whether the risk is intentional or accidental.

## Tools

```bash
python scripts/portfolio_risk.py assets/sample_portfolio.json
python scripts/build_optimizer_inputs.py assets/sample_returns.json
```

Use the first command for descriptive risk review. Use the second when you want optimizer-ready expected returns, covariance, and simple seed weights without pulling in heavy portfolio libraries.

## Benchmark Notes

- PyPortfolioOpt sets the bar on portfolio construction methods, so this skill should feed optimization workflows rather than stop at descriptive metrics.
- Qlib and LEAN both treat risk modeling and backtesting as part of one pipeline; portfolio summaries should be comparable with strategy results.

## References

- `references/risk-metrics.md`
- `references/low-dependency-portfolio-workflow.md`
