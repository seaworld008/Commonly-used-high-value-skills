---
name: investment-memo-writer
description: Use when turning research notes into an investment memo, writing a buy or sell thesis, or structuring catalysts, risks, and monitoring items for an IC-style document.
---

# Investment Memo Writer

Turn scattered research into a decision document that can survive committee scrutiny.

## When to Use

- IC memo drafting
- PM handoff
- Quarterly thesis refresh
- Long or short initiation notes

## Workflow

1. Gather recommendation, thesis points, catalysts, risks, and monitoring items.
2. Run `scripts/build_memo.py`.
3. Edit the generated markdown for nuance and evidence.
4. Add valuation, time horizon, and position-sizing context before circulation.

## Tool

```bash
python scripts/build_memo.py assets/sample_thesis.json
```

## Benchmark Notes

- FinRobot explicitly focuses on automated equity research reports, so memo quality should be judged by structure, evidence, and risk framing rather than length.
- The best workflows separate data gathering, analysis, and final narrative synthesis.

## References

- `references/memo-outline.md`

