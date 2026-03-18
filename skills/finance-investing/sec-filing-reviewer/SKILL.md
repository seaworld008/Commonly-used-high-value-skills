---
name: sec-filing-reviewer
description: Use when reviewing SEC filings, extracting material risk disclosures, scanning 10-K or 10-Q sections, or building a follow-up checklist from filing language.
---

# SEC Filing Reviewer

Use structured section text to flag control, liquidity, legal, and disclosure risks before they get buried in a long filing read.

## When to Use

- 10-K and 10-Q reviews
- 8-K event scans
- Pre-earnings diligence
- Red-flag triage for new positions

## Workflow

1. Pull or paste the relevant sections.
2. Run `scripts/review_filing.py`.
3. Review risk flags and follow-up questions.
4. Escalate anything involving controls, going-concern language, restatements, or investigations.

## Tool

```bash
python scripts/review_filing.py assets/sample_filing_sections.json
```

## Benchmark Notes

- SEC official APIs expose disclosure and XBRL data, so filing workflows should anchor to official SEC sources whenever possible.
- Tools like `sec-edgar-downloader` and `sec-parser` show the value of separating retrieval from semantic review; keep those steps distinct.

## References

- `references/sec-sources.md`

