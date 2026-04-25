# Persona Governance and Organizational Readiness

Purpose: Define lifecycle governance, update cadence, retirement rules, and organizational rollout practices for Cast-managed personas.

## Contents

1. Lifecycle phases
2. Update triggers
3. Retirement rules
4. Organizational readiness
5. Living document principles

## Lifecycle Governance

### Five Phases

| Phase | Goal | Typical output |
|---|---|---|
| Planning | Define purpose, scope, stakeholders, data sources | Persona plan |
| Conception | Collect data and draft proto-personas | Proto-personas |
| Maturation | Validate and promote to active use | `draft -> active` |
| Adulthood | Use, update, evolve, measure impact | Active persona portfolio |
| Retirement | Archive or replace obsolete personas | `active -> archived` |

### Maturation Gate

- Promote to `active` at `confidence > 0.60`.

## Update Triggers

| Trigger | Urgency | Example |
|---|---|---|
| Major market change | `P0` | regulation or disruptive competitor event |
| User-base shift | `P1` | new enterprise segment or sharp demographic shift |
| Behavior drift | `P2` | new usage pattern or funnel divergence |
| New release | `P2` | major feature shifts user behavior |
| Feedback accumulation | `P3` | recurring support/NPS pattern changes |
| Scheduled review | `P3` | quarterly review cycle |

### Suggested Cadence

- Monthly: freshness check, drift scan, decay application
- Quarterly: full review, coverage review, anti-persona review
- Yearly: large-scale revalidation, clustering rerun, retirement review

## Retirement Rules

### Triggers

| Trigger | Threshold / condition | Action |
|---|---|---|
| Segment disappearance | segment falls below `5%` | Archive quickly |
| Segment merge | no meaningful behavioral difference remains | Merge personas |
| Long-term unused | unused in decisions for `6 months` | Review for retirement |
| Confidence collapse | confidence below `0.30` | Revalidate or retire |
| Source loss | major evidence source disappears | Replace source or retire |
| Strategy shift | market or segment is no longer targeted | Archive |

### Retirement Process

1. Identify the retirement candidate.
2. Assess downstream dependency.
3. Obtain stakeholder approval.
4. Define successor or replacement if needed.
5. Move to archive and update registry metadata.

## Organizational Readiness

Evaluate readiness across:

- leadership support
- process integration
- data infrastructure
- team skill
- user-centered culture

### Rollout Roadmap

| Phase | Goal | Duration |
|---|---|---|
| Seed | awareness | `1-2` months |
| Grow | pilot adoption | `2-3` months |
| Scale | standardization | `3-6` months |
| Optimize | automation and measurement | `6-12` months |

## Living Document Principles

| Principle | Meaning |
|---|---|
| Easy to edit | difficult formats do not stay updated |
| Easy to access | personas must live where teams already work |
| Low update cost | attribute-level changes should be cheap |
| Visible history | everyone must see what changed and when |
| Stable but flexible | Core Identity stays fixed; peripheral details evolve |

Preferred formats:

- Markdown
- wiki / shared documentation
- structured YAML plus human-readable view

Avoid:

- static PDF as the only source
- hard-to-edit design files as the only source
- image-only persona assets
