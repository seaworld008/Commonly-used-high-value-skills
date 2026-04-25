# Engineering Metrics Pitfalls

Purpose: Use this reference when Harvest reports include DORA, SPACE, throughput, burnout, or AI-productivity commentary.

## Contents

- DORA pitfalls
- SPACE limits
- Vanity metrics
- Actionable flow metrics
- Harvest reporting guardrails

## DORA Pitfalls

| ID | Pitfall | Guardrail |
|----|---------|-----------|
| `EM-01` | Lagging-indicator dependence | Pair with leading indicators such as cycle time and review wait |
| `EM-02` | Chasing "Elite" as a status badge | Use benchmarks as context, not as the target itself |
| `EM-03` | Deployment frequency without quality balance | Always pair with failure rate and recovery time |
| `EM-04` | Speed without value | Tie flow metrics to business or user outcomes |
| `EM-05` | Cross-team comparison | Focus on intra-team trend, not leaderboard behavior |
| `EM-06` | Ambiguous failure definition | Define rollback, hotfix, and incident criteria explicitly |

## SPACE Limits

- Do not use `Activity` alone as a performance proxy.
- Cover at least `3` dimensions if you reference SPACE.
- Treat SPACE as a checklist, not a single composite score.

## Vanity Metrics To Avoid

| ID | Metric | Why it is unsafe |
|----|--------|------------------|
| `VM-01` | Commit count | Easy to inflate |
| `VM-02` | LOC as productivity | Penalizes refactoring and varies by language |
| `VM-03` | PR count | Encourages artificial fragmentation |
| `VM-04` | Hours worked | Long hours can become negative productivity |
| `VM-05` | Approval rate alone | Can hide rubber-stamping |
| `VM-06` | Bug fixes closed | More fixes do not mean better quality |
| `VM-07` | Story points | Unstable across teams |

## Actionable Metrics

| Metric | Suggested target or warning |
|--------|-----------------------------|
| Cycle time | Median `24-48h` |
| Review response time | Median `< 4h` |
| Flow efficiency | `< 60%` suggests a bottleneck |
| Night/weekend commits | `> 10%` triggers burnout warning |
| Individual PR concentration | One person `> 40%` of team flow triggers imbalance warning |

## Harvest Guardrails

- Never report LOC as a direct productivity score.
- Add context for every key number: previous period, target, or trend.
- Avoid team-vs-team ranking unless the user explicitly asks and understands the limitation.
- If AI-tool productivity is discussed, note that self-report and measured throughput can diverge.
