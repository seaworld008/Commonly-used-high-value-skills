# Automated Handoff Router Reference

Purpose: Route Guardian findings to the right specialist in the right order, with explicit blocking behavior.

## Contents

- Priority order
- Routing rules
- Multi-route orchestration
- Response handling
- AUTORUN behavior
- Analytics

## Priority Order

```yaml
routing_priority:
  1_security:
    target: Sentinel
    blocking: true
  2_coverage:
    target: Radar
    blocking: false
  3_noise:
    target: Zen
    blocking: false
  4_architecture:
    target: Atlas
    blocking: usually_false
  5_investigation:
    target: Scout
    blocking: context_dependent
```

## Routing Rules

| Route | Trigger | Blocking |
|-------|---------|----------|
| Zen | `noise_ratio > 0.30`, `formatting_files > 20`, `import_reorder_files > 10`, `whitespace_only_changes > 5` | no |
| Sentinel | `security_classification == CRITICAL`, `SENSITIVE` with auth changes, dangerous patterns, secret exposure risk | yes |
| Radar | `coverage_gap > 0.40`, hotspot `< 50%`, critical file with no tests, `regression_risk > 0.70` | no |
| Atlas | `cross_module_changes > 3`, new inter-module coupling, shared-core change | usually no |
| Scout | conflict ambiguity, unclear root cause, contradictory evidence | context-dependent |

Noise evaluation rule:
- auto-route if `1 HIGH` trigger or `2 MEDIUM` triggers fire

## Multi-Route Orchestration

Sequential requirements:
- `Sentinel` before all other routes when security is blocking
- `Scout` before commit strategy when root cause is unclear
- `Zen` before `Judge` when noise meaningfully distorts reviewability

Parallel routing is allowed only for non-blocking routes.

## Response Handling

When a downstream handoff returns:
- `Sentinel`: update blocking status and security classification
- `Zen`: recompute noise ratio and PR quality
- `Radar`: recompute coverage and regression risk
- `Atlas`: update structural risk and split recommendation
- `Scout`: update commit boundaries and conflict strategy

## AUTORUN Behavior

AUTORUN may:
- generate route recommendations
- emit non-blocking handoffs
- block and stop on security-critical or approval-gated cases

Pause when:
- two or more blocking routes compete
- a route would imply history rewrite or release-affecting PR restructuring

## Analytics

Target health metrics:
- auto-handoff rate `> 80%`
- successful resolution rate `> 95%`
- false positive rate `< 5%`

Canonical analytics heading:

```markdown
## Handoff Route Analytics

### Route Distribution
- Sentinel: 12%
- Radar: 28%
- Zen: 34%

### Manual Override Analysis
- 2 overrides this month
```
