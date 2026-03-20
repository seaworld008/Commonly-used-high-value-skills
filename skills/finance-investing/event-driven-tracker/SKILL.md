---
name: event-driven-tracker
description: 'Use when tracking earnings, product launches, M&A, dividends, buybacks, unlocks, or other market-moving dates that need a prioritized event calendar.'
---

# Event Driven Tracker

Track catalysts before the market reminds you too late.

## When to Use

- Catalyst calendars
- Postion monitoring around earnings or M&A
- PM weekly prep
- Event-driven strategy notes

## Workflow

1. Normalize upcoming event dates and importance scores.
2. Run `scripts/track_events.py`.
3. Review priority events inside the next two weeks.
4. Add trade plan, monitoring owner, and decision rule outside the script.

## Tool

```bash
python scripts/track_events.py assets/sample_events.json
```

## Benchmark Notes

- Event-driven systems become useful when they are paired with structured data and fast follow-up workflows, not just a date list.
- OpenBB-like data stacks are helpful here because they consolidate corporate actions, earnings, and macro calendars in one place.

## References

- `references/event-catalog.md`
