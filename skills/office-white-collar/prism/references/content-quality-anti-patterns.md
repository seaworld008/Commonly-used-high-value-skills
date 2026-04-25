# AI Content Quality Anti-Patterns

Purpose: Catch hallucination, attribution, repetition, weak endings, and consistency failures before Prism recommends a prompt as ready.

## Contents

- Hallucination anti-patterns `HQ-01..HQ-07`
- Common content failures `CQ-01..CQ-05`
- Format-specific quality pitfalls
- Consistency rules

## Hallucination Anti-Patterns

| ID | Anti-pattern | Symptom | Fix |
|----|--------------|---------|-----|
| `HQ-01` | Unchecked Fabrication | Facts or claims are not traceable to the source | Cross-check all claims |
| `HQ-02` | Confidence Blindness | Fluent output sounds right but is wrong | Require explicit source grounding |
| `HQ-03` | Source Scope Creep | The model adds outside knowledge | Constrain to provided sources |
| `HQ-04` | Statistical Hallucination | Unsupported percentages or numbers appear | Require sourced numbers only |
| `HQ-05` | Attribution Confusion | Claims are credited to the wrong source | Label sources clearly |
| `HQ-06` | Interpolation Illusion | Gaps are filled with invented causal logic | Mark gaps as unknown |
| `HQ-07` | Recency Fabrication | Old sources are framed as current facts | State source dates explicitly |

## Common Content Failures

| ID | Failure | Symptom | Fix |
|----|---------|---------|-----|
| `CQ-01` | AI-sounding prose | Generic, overpolished, pattern-heavy output | Tighten tone and negative constraints |
| `CQ-02` | Redundancy | Same point appears repeatedly | Tighten focus and trim scope |
| `CQ-03` | Context breaks | Tone or depth changes across the piece | Use stronger structural guidance |
| `CQ-04` | Flat expression | Everything sounds equally important | Mix evidence, story, comparison, and emphasis intentionally |
| `CQ-05` | Weak ending | No meaningful summary or CTA | Require a closing synthesis or next action |

## Format-Specific Quality Pitfalls

| Format | Pitfall | Guardrail |
|--------|---------|-----------|
| `Audio` | Same point repeated `3+` times | Reduce scope and add stronger focus |
| `Audio` | One speaker dominates `80%+` | Ask for better balance |
| `Video` | Visuals do not support the spoken message | Re-state the visual role explicitly |
| `Slides` | Text walls or unlabeled charts | Enforce one message per slide and explicit chart labels |
| `Infographic` | Source or statistic is not attributed | Require visible attribution |

## Consistency Rules

- Keep the tone stable from opening to close.
- Keep depth consistent across sections unless a deliberate sequence is specified.
- Keep the same core message across Audio, Video, and Slides when they belong to the same content funnel.
- Preserve brand voice when the user or source implies one.

## Quick Quality Gates

| Gate | Action |
|------|--------|
| Unsupported number detected | Flag hallucination risk immediately |
| Attribution is unclear | Add attribution requirements before another round |
| Repetition `3+` times | Narrow focus and shorten duration |
| Ending has no next step | Add summary or CTA |
| Weighted score `< 4.0` | Iterate if another round is justified |
