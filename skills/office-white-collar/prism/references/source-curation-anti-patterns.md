# Source Curation Anti-Patterns

Purpose: Prevent bad source sets from degrading NotebookLM outputs through overload, low quality, poor structure, or wrong notebook composition.

## Contents

- Source curation anti-patterns `SC-01..SC-07`
- Notebook composition anti-patterns `NC-01..NC-05`
- Format-specific source guidance
- Quick quality gates

## Source Curation Anti-Patterns

| ID | Anti-pattern | Symptom | Fix |
|----|--------------|---------|-----|
| `SC-01` | Source Overload | Output stays broad and shallow | Stay within `5-15` sources; prefer `2-5` for focus |
| `SC-02` | Quality Blindness | Inaccurate or weak claims | Run a pre-upload quality check |
| `SC-03` | Contradictory Sources by Accident | Output mixes incompatible claims | Resolve the conflict or use it intentionally for Debate/Critique |
| `SC-04` | Scan PDF Trap | Missing or broken extraction | OCR scanned PDFs first |
| `SC-05` | Paywall/Login Source | Source is inaccessible | Replace with public sources |
| `SC-06` | Language Mix | Output switches language unexpectedly | Unify source language or make multilingual intent explicit |
| `SC-07` | Stale Sources | Old facts appear as current | Prefer fresher sources for time-sensitive topics |

## Notebook Composition Anti-Patterns

| ID | Anti-pattern | Symptom | Fix |
|----|--------------|---------|-----|
| `NC-01` | Pattern Mismatch | Format and source structure fight each other | Match composition pattern to format |
| `NC-02` | No Role Assignment | Every source is treated equally | Give each source a clear role |
| `NC-03` | Depth-Breadth Confusion | Deep Dive turns superficial | Use `1-3` sources for deep analysis |
| `NC-04` | Missing Context Source | Key terms feel unexplained | Add one orientation or glossary source |
| `NC-05` | Unbalanced Perspectives | Debate/Critique feels one-sided | Balance evidence across viewpoints |

## Format-Specific Source Guidance

| Format | Recommended source shape |
|--------|--------------------------|
| `Audio Overview` | `2-5` focused sources with arguments, trade-offs, or strong narrative |
| `Video Overview` | Sources with visualizable concepts, data, or scene-worthy structure |
| `Slides` | Clear headings, bullets, and source data for charts |
| `Infographic` | Numeric, comparative, or ranking data |
| `Deep Research` | High-trust, high-depth, high-relevance sources |

## Quick Quality Gates

| Gate | Action |
|------|--------|
| Source count `15+` | Trim before proceeding |
| Source count `20+` | Treat as overload |
| Deep analysis with more than `3` sources | Reduce scope |
| Broad overview with fewer than `5` sources | Add breadth if needed |
| PDF is a scan | OCR first |
| URL needs login | Replace it |
| Mixed-language set | Unify language or declare multilingual intent |
