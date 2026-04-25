# Cast Collaboration Formats

Purpose: Preserve the exact handoff anchors and the minimum payload each collaboration pattern requires.

## Contents

1. Pattern overview
2. Researcher pattern
3. Trace pattern
4. Voice pattern
5. Spark pattern
6. Retain pattern
7. Nexus integration
8. General handoff rules

## Pattern Overview

| Pattern | Flow | Use when |
|---|---|---|
| `A` | Researcher -> Cast -> Echo | Research findings become testing personas |
| `B` | Trace -> Cast | Behavioral data updates personas |
| `C` | Voice -> Cast | Feedback data enriches personas |
| `D` | Cast -> Spark | Personas inform feature ideation |
| `E` | Cast -> Retain | Personas inform retention strategy |

## Pattern A: Researcher -> Cast -> Echo

### Inbound anchor

`## CAST_HANDOFF: Research Integration`

Minimum fields:

- `Source`
- `Findings`
- `User Segments Identified`
- `Goals Discovered`
- `Pain Points Discovered`
- `Behavioral Insights`
- `Recommended Persona Updates`

### Outbound anchor

`## ECHO_HANDOFF: Updated Personas Ready`

Minimum fields:

- `Source`
- `Persona Summary`
- `Recommended Validation Flows`
- `Files`

## Pattern B: Trace -> Cast

### Inbound anchor

`## CAST_HANDOFF: Behavioral Data`

Minimum fields:

- `Source`
- `Behavioral Clusters`
- `Drift Signals`
- `Raw Metrics`

## Pattern C: Voice -> Cast

### Inbound anchor

`## CAST_HANDOFF: Feedback Integration`

Minimum fields:

- `Source`
- `Segment Insights`
- `Feedback-to-Persona Mapping`
- `Emerging Segments`

## Pattern D: Cast -> Spark

### Outbound anchor

`## SPARK_HANDOFF: Personas for Feature Ideation`

Minimum fields:

- `Source`
- `Persona Summaries (Feature-Focused)`
- `Cross-Persona Opportunities`
- `Files`

## Pattern E: Cast -> Retain

### Outbound anchor

`## RETAIN_HANDOFF: Personas for Retention Strategy`

Minimum fields:

- `Source`
- `Persona Profiles (Retention-Focused)`
- `Cross-Persona Retention Matrix`
- `Files`

## Nexus Integration

### AUTORUN step completion

Return `_STEP_COMPLETE:` with:

- `Mode`
- `Personas processed`
- `Registry updated`
- `Confidence notes`
- `Next`

### Hub handoff

Use the exact anchor:

`## NEXUS_HANDOFF`

Required fields:

- `Step`
- `Agent`
- `Summary`
- `Key Findings`
- `Artifacts`
- `Risks`
- `Open Questions`
- `Confirmations`
- `Suggested Next`
- `Next Action`

## General Handoff Rules

- Keep payloads small and evidence-first.
- Preserve exact anchors.
- Do not drop confidence or file references.
- When a persona changed, state what changed and why.
- When uncertainty remains, say so explicitly instead of implying certainty.
