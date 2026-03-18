# Finance Skill Benchmark Notes

**Date:** 2026-03-18

This note captures the external benchmark set used to judge whether the new finance category is merely present or actually useful.

## Benchmark Set

- OpenBB: broad financial data platform for analysts, quants, and AI agents
- FinGPT: finance-specific LLM stack
- FinRobot: agent workflow for financial analysis
- Microsoft Qlib: quant research and production pipeline
- QuantConnect LEAN: professional-grade event-driven backtesting and live trading
- PyPortfolioOpt: modular portfolio optimization toolkit
- SEC official EDGAR APIs: official filings and XBRL data access

## What These Projects Do Better Than the Current Draft

### 1. Data access breadth

OpenBB sets a high bar by acting as a data integration layer rather than a single-purpose script set. The practical lesson for this repository is that `financial-data-collector`, `stock-screener-builder`, `macro-regime-monitor`, and `event-driven-tracker` should move toward explicit provider abstraction and official-source references.

### 2. Research-to-execution continuity

Qlib and LEAN both connect idea generation, backtesting, and execution more tightly than the current draft. The practical lesson is that `factor-backtester` and `portfolio-risk-manager` should surface turnover, cost assumptions, drawdown, and concentration instead of stopping at a single return series or exposure table.

### 3. Portfolio construction depth

PyPortfolioOpt provides classical efficient frontier, Black-Litterman, and HRP workflows. The practical lesson is that `portfolio-risk-manager` should eventually grow beyond descriptive metrics into optimizer-ready outputs.

### 4. Finance-native language workflows

FinGPT and FinRobot show that good finance agents blend data gathering, domain language understanding, and report generation. The practical lesson is that `earnings-call-analyzer`, `sec-filing-reviewer`, and `investment-memo-writer` should favor structured outputs that downstream agents or analysts can chain together.

### 5. Official-source grounding

The SEC APIs and related filing download libraries show that filing workflows should prefer official filing and XBRL data instead of secondary summaries wherever possible.

## Immediate Repository Changes Guided by These Benchmarks

- Add benchmark notes directly into each new finance `SKILL.md`
- Upgrade `factor-backtester` to include turnover-aware cost adjustment and drawdown
- Upgrade `portfolio-risk-manager` to include concentration metrics
- Keep SEC references anchored to official SEC APIs
- Treat the current finance scripts as lightweight building blocks, not as a replacement for full quant platforms

