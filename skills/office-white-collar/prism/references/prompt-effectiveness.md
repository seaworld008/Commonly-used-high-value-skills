# Prompt Effectiveness System (SPECTRUM)

Purpose: Track prompt outcomes, calibrate reusable prompt heuristics, and emit stable learning signals without overreacting to small samples.

## Contents

- RECORD schema
- EVALUATE thresholds
- CALIBRATE rules
- PROPAGATE format

## RECORD

Log these fields after each Prism task:

```yaml
Task: [task-id]
Format: [Audio Deep Dive | Audio Brief | Audio Critique | Audio Debate | Audio Lecture | Video Explainer | Video Brief | Slide Presenter | Slide Detailed | Infographic | Mind Map | Deep Research]
Audience_Type: [C-suite | PM | Senior Engineer | Junior Dev | Researcher | General Public | Student | Sales]
Source_Pattern: [Single Deep | Multi-Perspective | Hierarchical | Comparative | Chronological]
Source_Count: [number]
Prompt_Layers_Used:
  L1_audience: [yes/no]
  L2_focus: [yes/no]
  L3_tone: [yes/no]
Patterns_Applied:
  - pattern: [Audience Anchor | Negative Space | Focus Laser | Tone Dial | Duration Target | Structural Blueprint]
    effectiveness: [High/Medium/Low/Unknown]
Quality_Score:
  accuracy: [1-5]
  audience_fit: [1-5]
  engagement: [1-5]
  completeness: [1-5]
  actionability: [1-5]
  overall: [1.0-5.0]
Iterations_Required: [count]
Downstream_Handoff: [Morph/Growth/Canvas/Lore/None]
```

## EVALUATE

### Quality Trend Thresholds

| Average overall score | Interpretation | Action |
|-----------------------|----------------|--------|
| `> 4.2` | Excellent | Keep the pattern and reuse it |
| `3.5-4.2` | Good | Minor tuning only |
| `2.5-3.5` | Moderate | Review pattern selection and source advice |
| `< 2.5` | Low | Investigate root causes immediately |

### Format-Audience Fit Thresholds

| Fit score | Interpretation | Action |
|-----------|----------------|--------|
| `> 0.85` | Highly effective | Prefer this combination |
| `0.70-0.85` | Good | Keep using with situational tuning |
| `< 0.70` | Underperforming | Rework the template or audience guidance |

### Evaluation Triggers

- Quality score `< 3.0`
- User requests a major revision
- `3+ iterations` were required
- A new NotebookLM feature changes format behavior
- Quarterly review

## CALIBRATE

### Default Pattern Weights

| Format | Pattern weights |
|--------|-----------------|
| `Audio` | `Audience Anchor 0.95`, `Negative Space 0.90`, `Focus Laser 0.85`, `Tone Dial 0.85`, `Duration Target 0.80`, `Structural Blueprint 0.75` |
| `Video` | `Audience Anchor 0.90`, `Focus Laser 0.90`, `Tone Dial 0.80`, `Structural Blueprint 0.85`, `Duration Target 0.75`, `Negative Space 0.70` |
| `Slides` | `Structural Blueprint 0.95`, `Focus Laser 0.90`, `Audience Anchor 0.85`, `Negative Space 0.80`, `Tone Dial 0.70`, `Duration Target 0.65` |

### Calibration Rules

- Require `3+ tasks` before changing any pattern weight.
- Cap each adjustment at `±0.15` per calibration cycle.
- Apply `10% per quarter` decay toward defaults.
- User-explicit preferences always override calibrated defaults.

### Audience-Fit Defaults

| Audience | Best audio | Best video | Best slides |
|----------|------------|------------|-------------|
| `C-suite` | `Brief: Executive Summary` | `Explainer: Corporate` | `Presenter: Internal` |
| `Senior Engineer` | `Deep Dive: Technical` | `Explainer: Whiteboard` | `Detailed: Handout` |
| `General Public` | `Deep Dive: General` | `Brief: Casual` | `Presenter: TED-style` |
| `Student` | `Lecture: Tutorial` | `Explainer: Classroom` | `Detailed: Educational` |
| `Researcher` | `Critique: Research` | `Explainer: Academic` | `Detailed: Handout` |

### Source Pattern Defaults

| Source pattern | Best for | Notes |
|----------------|----------|-------|
| `Single Deep` | Lecture Mode, Deep Research | Strongest focus |
| `Multi-Perspective` | Debate, Critique | Strongest tension and contrast |
| `Hierarchical` | Lecture, Detailed Deck | Best for structured learning |
| `Comparative` | Infographic, Critique | Strong comparison scaffolding |
| `Chronological` | Deep Dive, Presenter | Good narrative flow |

## PROPAGATE

### Journal Entry

Record major findings in `.agents/prism.md`:

```markdown
## YYYY-MM-DD - SPECTRUM: [Format × Audience]

**Tasks assessed**: N
**Average quality**: X/5.0
**Key insight**: [description]
**Calibration adjustment**: [pattern/fit: old -> new]
**Apply when**: [future scenario]
**reusable**: true

<!-- EVOLUTION_SIGNAL
type: PATTERN
source: Prism
date: YYYY-MM-DD
summary: [prompt design insight]
affects: [Prism, Lore]
priority: MEDIUM
reusable: true
-->
```

### Quick SPECTRUM

Use this when there are fewer than `3` tasks:

```markdown
## Quick SPECTRUM

**Tasks**: 1 completed
**Quality**: 4.2/5.0
**Note**: [small-sample insight]
**Action**: No weight change (insufficient data)
```

Do not change weights from a single small task.
