# 金融投资 / Finance Investing

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

覆盖金融数据、估值、风控、回测、投研写作和事件驱动分析的技能集合。

当前分类共 **12** 个技能。

## 推荐先看

- [comps-valuation-analyst](./comps-valuation-analyst/) - Use when valuing a public company with peer multiples, building comparable-company tables, or pressure-testing a valuation range with EV/EBITDA, P/E, and EV/Sales.
- [earnings-call-analyzer](./earnings-call-analyzer/) - Use when summarizing earnings calls, extracting management tone changes, surfacing guidance language, or turning transcript snippets into an actionable investor update.
- [event-driven-tracker](./event-driven-tracker/) - Use when tracking earnings, product launches, M&A, dividends, buybacks, unlocks, or other market-moving dates that need a prioritized event calendar.
- [factor-backtester](./factor-backtester/) - Use when testing factor signals, running long-short spread backtests, checking hit rate and turnover, or sanity-checking whether a ranking signal survives basic transaction cost assumptions.

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `comps-valuation-analyst` | Use when valuing a public company with peer multiples, building comparable-company tables, or pressure-testing a valuation range with EV/EBITDA, P/E, and EV/Sales. | [目录](./comps-valuation-analyst/) | [SKILL.md](./comps-valuation-analyst/SKILL.md) |
| `earnings-call-analyzer` | Use when summarizing earnings calls, extracting management tone changes, surfacing guidance language, or turning transcript snippets into an actionable investor update. | [目录](./earnings-call-analyzer/) | [SKILL.md](./earnings-call-analyzer/SKILL.md) |
| `event-driven-tracker` | Use when tracking earnings, product launches, M&A, dividends, buybacks, unlocks, or other market-moving dates that need a prioritized event calendar. | [目录](./event-driven-tracker/) | [SKILL.md](./event-driven-tracker/SKILL.md) |
| `factor-backtester` | Use when testing factor signals, running long-short spread backtests, checking hit rate and turnover, or sanity-checking whether a ranking signal survives basic transaction cost assumptions. | [目录](./factor-backtester/) | [SKILL.md](./factor-backtester/SKILL.md) |
| `financial-analyst` | Performs financial ratio analysis, DCF valuation, budget variance analysis, and rolling forecast construction for strategic decision-making | [目录](./financial-analyst/) | [SKILL.md](./financial-analyst/SKILL.md) |
| `financial-data-collector` | Use when collecting financial data for a US public company, assembling DCF inputs, pulling market and filing facts, or grounding downstream analysis in structured yfinance and SEC data. | [目录](./financial-data-collector/) | [SKILL.md](./financial-data-collector/SKILL.md) |
| `investment-memo-writer` | Use when turning research notes into an investment memo, writing a buy or sell thesis, or structuring catalysts, risks, and monitoring items for an IC-style document. | [目录](./investment-memo-writer/) | [SKILL.md](./investment-memo-writer/SKILL.md) |
| `macro-regime-monitor` | Use when tracking macro regime shifts, summarizing inflation, growth, spreads, and liquidity signals, or creating a house view before updating sector or asset-allocation calls. | [目录](./macro-regime-monitor/) | [SKILL.md](./macro-regime-monitor/SKILL.md) |
| `options-strategy-evaluator` | Use when evaluating an options structure, checking expiry payoff checkpoints, comparing premium outlay versus downside protection, or preparing a short strategy note for a trade review. | [目录](./options-strategy-evaluator/) | [SKILL.md](./options-strategy-evaluator/SKILL.md) |
| `portfolio-risk-manager` | Use when reviewing portfolio exposures, checking concentration and beta risk, summarizing sector or region tilts, or preparing a risk note before reallocating capital. | [目录](./portfolio-risk-manager/) | [SKILL.md](./portfolio-risk-manager/SKILL.md) |
| `sec-filing-reviewer` | Use when reviewing SEC filings, extracting material risk disclosures, scanning 10-K or 10-Q sections, or building a follow-up checklist from filing language. | [目录](./sec-filing-reviewer/) | [SKILL.md](./sec-filing-reviewer/SKILL.md) |
| `stock-screener-builder` | Use when building a stock screen, filtering a universe by valuation, growth, quality, or momentum rules, or creating a repeatable shortlist for deeper research. | [目录](./stock-screener-builder/) | [SKILL.md](./stock-screener-builder/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
