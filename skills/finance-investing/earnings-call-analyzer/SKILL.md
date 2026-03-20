---
name: earnings-call-analyzer
description: 'Use when summarizing earnings calls, extracting management tone changes, surfacing guidance language, or turning transcript snippets into an actionable investor update.'
---

# Earnings Call Analyzer

Turn structured earnings-call text into a fast investor readout with tone, guidance, capital-allocation, and risk signals.

## When to Use

- Post-earnings wrap-ups
- PM or IC notes
- Variant-perception checks against prior quarter messaging
- Management credibility tracking

## Workflow

1. Split transcript text into prepared remarks and Q&A segments.
2. Run `scripts/analyze_earnings_call.py`.
3. Review positive, caution, guidance, and capex signal counts.
4. Write what changed from last quarter, not just what was said.

## Tool

```bash
python scripts/analyze_earnings_call.py assets/sample_earnings_call.json
```

## Benchmark Notes

- FinGPT and FinRobot both emphasize finance-specific language understanding, so transcript analysis should focus on guidance and risk language rather than generic sentiment only.
- OpenBB-style analyst workflows work best when transcript output is concise enough to plug into a broader research stack.

## References

- `references/transcript-signals.md`
