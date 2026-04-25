# Rubric Evaluation System

**Purpose:** Structured rubric-based evaluation for Sprint Contract deliverables.
**Read when:** Evaluator Loop is active and you need scoring criteria for agent output.

---

## Overview

Rubrics replace subjective quality judgements with graduated, measurable criteria. Each deliverable is scored across weighted dimensions using a 4-level scale aligned with the Warden V.A.I.R.E. framework.

---

## Score Scale

| Score | Level | Description |
|-------|-------|-------------|
| 3 | Exemplary | Exceeds best practices; no improvements needed |
| 2 | Sufficient | Meets acceptance criteria; minor improvements possible |
| 1 | Partial | Gaps exist; revision needed before acceptance |
| 0 | Not considered | Serious issues; blocks acceptance |

**Decision mapping:**
- All dimensions >= 2 → `ACCEPT`
- Any dimension == 1 AND no dimension == 0 → `REVISE` (with targeted feedback)
- Any dimension == 0 → `BLOCK` (escalate to Nexus)

---

## Evaluation Dimensions

| Dimension | Weight Range | Default Evaluator | Description |
|-----------|-------------|-------------------|-------------|
| Correctness | 0.25 - 0.40 | Radar, Attest | Tests pass, requirements met, no regressions |
| Design Quality | 0.10 - 0.25 | Judge, Zen | Code structure, patterns, maintainability |
| Craft | 0.10 - 0.20 | Judge | Naming, formatting, idioms, documentation |
| Functionality | 0.15 - 0.25 | Voyager, Attest | Feature works as specified, edge cases handled |
| Security | 0.00 - 0.20 | Sentinel | No vulnerabilities, secure patterns used |
| UX Quality | 0.00 - 0.20 | Warden | V.A.I.R.E. compliance, accessibility, usability |

**Constraints:** Dimension weights MUST sum to 1.0 for any given rubric instance.

---

## Task-Type Templates

### FEATURE_UI

| Dimension | Weight | Evaluator |
|-----------|--------|-----------|
| Correctness | 0.25 | Radar |
| Functionality | 0.25 | Voyager, Attest |
| UX Quality | 0.20 | Warden |
| Design Quality | 0.15 | Judge |
| Craft | 0.15 | Judge |

### FEATURE_BACKEND

| Dimension | Weight | Evaluator |
|-----------|--------|-----------|
| Correctness | 0.35 | Radar, Attest |
| Design Quality | 0.25 | Judge, Zen |
| Functionality | 0.20 | Attest |
| Craft | 0.10 | Judge |
| Security | 0.10 | Sentinel |

### BUG_FIX

| Dimension | Weight | Evaluator |
|-----------|--------|-----------|
| Correctness | 0.40 | Radar |
| Functionality | 0.25 | Attest |
| Design Quality | 0.20 | Judge |
| Craft | 0.15 | Judge |

### SECURITY

| Dimension | Weight | Evaluator |
|-----------|--------|-----------|
| Security | 0.35 | Sentinel |
| Correctness | 0.30 | Radar |
| Design Quality | 0.20 | Judge |
| Craft | 0.15 | Judge |

---

## Evaluation Output Format

```yaml
RUBRIC_EVALUATION:
  Evaluator: "[agent name]"
  Contract_Ref: "[sprint contract ID]"
  Iteration: [N]
  Dimensions:
    - dimension: "Correctness"
      score: [0-3]
      evidence: "[specific findings]"
      recommendation: "[action if score < 2]"
    - dimension: "Design Quality"
      score: [0-3]
      evidence: "[specific findings]"
      recommendation: "[action if score < 2]"
  Weighted_Score: [0.00 - 3.00]
  Verdict: ACCEPT | REVISE | BLOCK
  Feedback: "[actionable summary for Generator]"
```

---

## UQS Conversion

Rubric scores (0-3 per dimension) convert to UQS (0-100) for long-term tracking:

```
UQS_equivalent = (weighted_rubric_score / 3.0) * 100
```

| Rubric Weighted | UQS Equivalent | UQS Band |
|-----------------|----------------|----------|
| 2.70 - 3.00 | 90 - 100 | Excellent |
| 2.40 - 2.69 | 80 - 89 | Good |
| 2.10 - 2.39 | 70 - 79 | Acceptable |
| 1.80 - 2.09 | 60 - 69 | Fair |
| < 1.80 | < 60 | Poor |

**Relationship:** Rubrics provide immediate, per-Sprint evaluation. UQS tracks long-term quality trends via PDCA (`references/quality-iteration.md`). Rubric results feed into UQS when quality iteration is triggered.

---

## Rubric Selection

Nexus selects the appropriate rubric template during PREPARE phase based on task classification:

```
Task Type == FEATURE AND has_ui_changes? → FEATURE_UI
Task Type == FEATURE AND backend_only?   → FEATURE_BACKEND
Task Type == BUG                         → BUG_FIX
Task Type == SECURITY                    → SECURITY
Other                                    → FEATURE_BACKEND (default)
```
