# Quality Evaluation Framework

Purpose: Score NotebookLM outputs consistently, identify the highest-impact prompt change, and stop iteration before it becomes wasteful.

## Contents

- Universal five-axis rubric
- Format-specific red flags
- A/B testing method
- REFINE loop

## Universal Five-Axis Rubric

| Criterion | Weight | Score 5 | Score 3 | Score 1 |
|-----------|--------|---------|---------|---------|
| `Accuracy` | `30%` | Fully faithful to the source | Mostly accurate with minor gaps | Contains fabrication or major errors |
| `Audience Fit` | `25%` | Perfect fit for audience knowledge and goals | Mostly suitable | Wrong level or wrong context |
| `Engagement` | `20%` | Compelling throughout | Acceptable but plain | Audience would disengage |
| `Completeness` | `15%` | Covers all critical points | Covers the main points | Misses important material |
| `Actionability` | `10%` | Clear next step or takeaway | Some implied action | No clear takeaway |

### Total Score Interpretation

- `4.5-5.0`: Excellent, ready to use
- `3.5-4.4`: Good, minor tuning only
- `2.5-3.4`: Acceptable, prompt adjustment recommended
- `1.0-2.4`: Poor, reassess source quality and design

## Format-Specific Red Flags

| Format | Red flags |
|--------|-----------|
| `Audio Overview` | Same point repeated `3+` times, one speaker talks `80%+`, sudden topic jumps, weak ending, unsupported facts |
| `Video Overview` | Audio-visual mismatch, unreadable text, visuals switching too fast, style drift, too much information on screen |
| `Slide Deck` | Text wall, weak slide-to-slide logic, unlabeled charts, redundant slides, no conclusion or CTA |
| `Infographic` | Missing source attribution, overloaded color palette, unreadable text, weak visual hierarchy, unclear scan path |

## Common Quality Failures

| Problem | Likely cause | First fix |
|---------|--------------|-----------|
| Too shallow | Focus is too broad or source is too weak | Use `Focus Laser` and trim the scope |
| Unsupported claims | Source set is incomplete or prompt scope is too loose | Add source-only constraints |
| Tone mismatch | Tone instructions are vague | Use a more explicit `Tone Dial` |
| Structure drifts | No explicit blueprint | Add a `Structural Blueprint` |
| Wrong duration | No hard duration target | Add `Duration Target` and reduce scope |

## A/B Prompt Testing

Rules:

- Change only one variable at a time.
- Keep the same source set for both variants.
- Score both variants with the same rubric.
- Promote the winner and test the next variable.

### Variables to Test

| Variable | Example A | Example B |
|----------|-----------|-----------|
| Audience level | experts | beginners |
| Tone | formal | conversational |
| Focus | broad overview | deep on 2 topics |
| Structure | free-form | strict sequence |
| Duration | `10 min` | `20 min` |
| Negative space | none | explicit `Skip:` list |

### A/B Result Template

```markdown
## A/B Test Results

Source: [same source set]
Variable tested: [one variable only]

### Version A
Score: Accuracy [X] / Audience [X] / Engagement [X] / Completeness [X] / Actionability [X]
Total: [weighted score]
Notes: [observation]

### Version B
Score: Accuracy [X] / Audience [X] / Engagement [X] / Completeness [X] / Actionability [X]
Total: [weighted score]
Notes: [observation]

### Result
Winner: [A or B]
Reason: [why]
Next test: [next variable]
```

## REFINE Loop

| Condition | Action |
|-----------|--------|
| Score `< 3.5` | Reassess source quality or format fit before only rewriting the prompt |
| Score `>= 3.5` | Identify the top `2-3` gaps |
| Each new round | Change exactly one prompt variable |
| Score `>= 4.0` | Stop, output is good enough |
| `3 rounds` reached | Stop and decide whether the source is the blocker |
| No improvement after `3 rounds` | Review source quality first |

## Practical Evaluation Sequence

1. Score the output on the five axes.
2. Check format-specific red flags.
3. Identify the single biggest weakness.
4. Change one variable only.
5. Regenerate and compare.
6. Stop at `>= 4.0` or after `3 rounds`.

Remember: the goal is not perfection. The goal is a reliable, audience-fit result with a clear next step.
