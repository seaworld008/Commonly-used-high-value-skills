---
name: stock-screener-builder
description: Use when building a stock screen, filtering a universe by valuation, growth, quality, or momentum rules, or creating a repeatable shortlist for deeper research.
---

# Stock Screener Builder

Create a clear research funnel instead of manually eyeballing a huge universe.

## When to Use

- Narrowing a coverage list
- Idea generation
- Quality-growth or value screens
- Event-driven candidate generation

## Workflow

1. Define a small set of filters that actually reflect the strategy.
2. Run `scripts/screen_stocks.py`.
3. Review the surviving names and why they passed.
4. Avoid adding so many filters that the screen just confirms prior bias.

## Tool

```bash
python scripts/screen_stocks.py assets/sample_universe.json
```

## Benchmark Notes

- OpenBB’s strength is standardized access to many data vendors; real screeners need a data abstraction layer, not hard-coded single-provider assumptions.
- FinRobot-style downstream analysis works better when the screener output is structured and small enough for follow-up valuation work.

## References

- `references/screener-design.md`

