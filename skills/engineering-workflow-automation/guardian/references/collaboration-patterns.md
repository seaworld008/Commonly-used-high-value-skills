# Guardian Collaboration Patterns Reference

Purpose: Define Guardian's standard collaboration flows and keep every inbound and outbound handoff discoverable in one place.

## Contents

- Pattern catalog
- Orbit boundary
- Bidirectional handoff matrix

## Pattern Catalog

| Pattern | Flow | Use when | Guardian output |
|---------|------|----------|-----------------|
| A | `Plan -> Guardian -> Builder` | planning is complete and commit strategy is needed | branch name, commit structure, PR size forecast |
| B | `Builder -> Guardian -> Judge` | implementation is done and PR prep is needed | signal/noise breakdown, PR package, squash report |
| C | `Guardian <-> Zen` | `noise_ratio > 0.30` or cleanup is required | noise separation plan |
| D | `Guardian -> Canvas` | PR or dependency visualization helps review | diagrams or structure map |
| E | `Guardian <-> Scout` | merge-conflict or technical context is unclear | conflict-aware commit strategy |
| F | `Guardian <-> Judge` | dependency changes, AI-suspected code, or unfamiliar imports need validation | pre-commit quality gate |
| G | `Guardian <-> Atlas` | `3+` modules or new coupling are involved | architecture impact report |
| H | `Guardian -> Radar` | high-risk files or coverage gaps require test support | coverage-focused handoff |
| I | `Guardian -> Zen` | hotspot refactoring is safer before PR | cleanup recommendation |
| J | `Guardian -> [auto]` | routing conditions are met | prioritized handoff package |
| K | `Guardian -> predictions` | pre-review Judge/Zen issues should be anticipated | predictive quality report |

## Key Trigger Thresholds

- Pattern C: `noise_ratio > 0.30`
- Pattern F: dependency files changed, AI-suspected code `>10%`, unfamiliar imports, or substantial logic changes
- Pattern G: cross-module changes `3+`
- Pattern H: risk `> 65`, hotspot overlap, coverage gap, or regression history

## Orbit-Guardian Squash Boundary

Guardian handles non-loop squash analysis and PR-prep squash recommendations.

Orbit owns:
- loop-iteration squash execution
- autonomous loop rebase
- loop artifact isolation

Guardian owns:
- pairwise squash scoring
- commit grouping
- message synthesis
- attribution checks
- post-squash verification guidance

Rule:
- Guardian may review Orbit output
- Guardian must not re-squash Orbit loop commits structurally

## Bidirectional Handoff Matrix

### Input Partners

| Partner | Handoff token | Purpose |
|---------|---------------|---------|
| Plan | `PLAN_TO_GUARDIAN_HANDOFF` | convert plan into branch and commit strategy |
| Builder | `BUILDER_TO_GUARDIAN_HANDOFF` | prepare PR-ready structure from finished code |
| Judge | `JUDGE_TO_GUARDIAN_HANDOFF` | incorporate review findings |
| Judge | `JUDGE_TO_GUARDIAN_FEEDBACK` | calibrate prediction accuracy |
| Zen | `ZEN_TO_GUARDIAN_HANDOFF` | learn accepted or rejected cleanup patterns |
| Scout | `SCOUT_TO_GUARDIAN_HANDOFF` | add RCA and conflict context |
| Atlas | `ATLAS_TO_GUARDIAN_HANDOFF` | add architecture impact |
| Harvest | `HARVEST_TO_GUARDIAN_HANDOFF` | use historical PR/report feedback |
| Ripple | `RIPPLE_TO_GUARDIAN_HANDOFF` | incorporate blast-radius analysis |

### Output Partners

| Partner | Handoff token | Purpose |
|---------|---------------|---------|
| Builder | `GUARDIAN_TO_BUILDER_HANDOFF` | implement commit or branch structure |
| Judge | `GUARDIAN_TO_JUDGE_HANDOFF` | review-ready PR package |
| Canvas | `GUARDIAN_TO_CANVAS_HANDOFF` | visualize dependency or split structure |
| Sherpa | `GUARDIAN_TO_SHERPA_HANDOFF` | break down XXL or MEGA work |
| Sentinel | `GUARDIAN_TO_SENTINEL_HANDOFF` | blocking security review |
| Probe | `GUARDIAN_TO_PROBE_HANDOFF` | runtime security verification |
| Atlas | `GUARDIAN_TO_ATLAS_HANDOFF` | structural impact analysis |
| Radar | `GUARDIAN_TO_RADAR_HANDOFF` | coverage and regression mitigation |
| Zen | `GUARDIAN_TO_ZEN_HANDOFF` | noise cleanup or hotspot refactor |
| Ripple | `GUARDIAN_TO_RIPPLE_HANDOFF` | dedicated impact analysis |
| Harvest | reporting follow-up | use Harvest when release-note or historical report support is needed |

Include the squash report in `GUARDIAN_TO_JUDGE_HANDOFF` when squash analysis was performed.
