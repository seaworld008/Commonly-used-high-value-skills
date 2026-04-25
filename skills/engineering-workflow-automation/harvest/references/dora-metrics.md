# DORA 4-Key Metrics Deep-Dive Reference

Purpose: Structured deep-dive on the four DORA key metrics (Deployment Frequency, Lead Time for Changes, Change Failure Rate, Mean Time to Restore) plus their SPACE complement, anchored to the 2024-2025 DORA report benchmarks. Produces tier-classified delivery diagnostics with measurement-window and data-source caveats explicit.

## Scope Boundary

- **harvest `dora`**: focused 4-key metric report with tier classification, trend, and SPACE complement. Anchored to gh PR/release data plus deploy/incident sources.
- **harvest `weekly` / `monthly` (elsewhere)**: PR aggregation reports. Surface DORA throughput as one section but do not deep-dive tiers.
- **harvest `release` (elsewhere)**: changelog and release-note generation, not delivery-performance diagnostics.
- **harvest `retro` (elsewhere)**: narrative voice over a sprint window, not metric tier classification.
- **Pulse (elsewhere)**: dashboard implementation and KPI tracking. Harvest produces the metric report; Pulse owns the live dashboard.
- **Beacon (elsewhere)**: SLO/SLI and reliability engineering. Beacon owns MTTR-as-SLO; Harvest reports MTTR-as-DORA-input.
- **Launch (elsewhere)**: release planning and execution. Harvest reports deployment frequency; Launch owns the deploy cadence strategy.
- **Guardian (elsewhere)**: PR strategy and gatekeeping. Harvest reports change failure rate; Guardian owns the merge-gate policy.

## Workflow

```
SCOPE     →  confirm repo, window (28-90d typical), branch/env mapping
          →  identify deploy source (release tag / GHA workflow / external)

COLLECT   →  gh pr list --state merged + gh release list + workflow runs
          →  pull incident timestamps (rollback PRs, hotfix labels, external)
          →  per_page=100 + --paginate; cache deploy/incident lookups

COMPUTE   →  DF  = deploys / window
          →  LT  = merge_ts → deploy_ts (P50, P75, P90)
          →  CFR = failed_deploys / total_deploys
          →  MTTR= incident_start → resolved_ts (P50, P75)

CLASSIFY  →  map each metric to Elite / High / Medium / Low (2024-2025 thresholds)
          →  flag inconsistent tiering (e.g., Elite DF + Low CFR = brittle pipeline)

COMPLEMENT→  pair with SPACE: satisfaction, performance, activity, comm, efficiency
          →  add 7-archetype team profile (DORA 2025) where signals available

REPORT    →  tier table + trend + SPACE notes + AI-period caveat + next actions
```

## 2024-2025 Tier Thresholds

| Metric | Elite | High | Medium | Low |
|--------|-------|------|--------|-----|
| Deployment Frequency | On-demand (multiple/day) | 1/day - 1/week | 1/week - 1/month | < 1/month |
| Lead Time for Changes | < 1 hour | 1 day - 1 week | 1 week - 1 month | > 1 month |
| Change Failure Rate | 0-5% | 5-10% | 10-15% | > 15% |
| Mean Time to Restore | < 1 hour | < 1 day | 1 day - 1 week | > 1 week |

Notes:
- DORA 2025 deprecated the 4-tier cluster classification at the team level — these per-metric thresholds remain valid for individual metric framing, but team profiling should use the 7 archetypes.
- Failed deployment recovery time (a 5th key in DORA 2024) is reported separately when distinct from incident MTTR.

## Measurement Window Selection

| Window | Use when | Caveat |
|--------|----------|--------|
| 7 days | Pulse-check during incident response or sprint demo | High variance; not for tier classification |
| 28 days | Default reporting cadence | Smooths weekly noise, matches DORA survey baseline |
| 90 days | Quarterly review and tier classification | Stable signal; required for Elite/Low determination |
| 180 days+ | Trend and AI-adoption comparison | Note tooling/team changes that confound trend |

## SPACE Complement

| Dimension | DORA gap it fills | Harvest signal |
|-----------|-------------------|----------------|
| Satisfaction | DORA ignores burnout; Elite DF can mask exhaustion | Survey link; PR-after-hours ratio as proxy |
| Performance | DORA measures delivery, not outcome quality | Defect rate, revert rate, customer-reported issues |
| Activity | DORA aggregates; SPACE preserves individual contribution context | PR count + review count, never as ranking |
| Communication | DORA misses collaboration cost | Review comment volume, cross-team PR ratio |
| Efficiency | DORA misses flow interruption | Cycle time 4-phase breakdown (Pickup/Review/Merge) |

Use SPACE to prevent the "Velocity Trap" — Elite DORA scores with collapsing team health.

## gh + GitHub Insights Integration

| Metric | gh source | Insights complement |
|--------|-----------|---------------------|
| Deployment Frequency | `gh release list --limit 100` or `gh run list --workflow=deploy.yml` | Repository Insights → Deployments view |
| Lead Time | `gh pr list --state merged --json mergedAt` + deploy timestamp | Pulse aggregator with per-PR ledger |
| Change Failure Rate | Rollback PR labels (`revert`, `hotfix`) / failed deploy runs | Incidents log if external |
| MTTR | Incident-tracker integration (PagerDuty, Datadog) or label-based | Required external — gh alone insufficient |

For Lead Time, prefer "merge → deploy" over "first-commit → deploy" to avoid conflating coding time with delivery pipeline time.

## Anti-Patterns

- Using DORA in isolation without SPACE — leads to the "Velocity Trap" where teams optimize delivery speed at the cost of burnout, and Elite-tier scores hide collapsing team health.
- Classifying the team into 4-tier clusters (low/medium/high/elite) — DORA 2025 replaced these with 7 archetypes that incorporate human factors. Per-metric tier thresholds remain valid; team-level cluster classification does not.
- Mixing measurement windows — comparing this week's DF to last quarter's MTTR is meaningless. Always compute all four metrics on the same window.
- Counting deploys without a defined "deploy" event — if the team has no release tags or deploy workflow, manufactured DF numbers mislead. Either define the event or mark the metric as unavailable.
- Lead Time from first commit instead of merge — inflates the metric with coding time DORA does not target. Merge-to-deploy is the canonical definition.
- Comparing pre-AI and post-AI periods without flagging tooling adoption — DORA 2025 reports AI inflates individual PR counts (+98%) while org throughput drops 1.5% and stability drops 7.2%. Direct period comparison without this caveat is misleading.
- Reporting CFR with no incident definition — "failed deployment" must be operationalized (rollback PR, hotfix within 24h, post-deploy incident, etc.) or the metric is unauditable.
- Treating MTTR as an SLO — MTTR is a DORA delivery metric. SLO ownership belongs to Beacon. Harvest reports the number; Beacon designs the target.
- Tier-shopping by changing the window — switching to a 7-day window to claim Elite DF when the 90-day average is High is metric gaming. Always document the window.

## Handoff

- **To Pulse**: tier classification + 90-day trend payload for live KPI dashboard. Pulse owns ongoing tracking; Harvest owns the report.
- **To Beacon**: MTTR data and incident timestamps when the team has an SLO program. Beacon translates MTTR-as-DORA into MTTR-as-SLO with error budget context.
- **To Guardian**: Change Failure Rate breakdown by PR size and review depth when CFR > 10%. Guardian owns merge-gate policy adjustments.
- **To Launch**: Deployment Frequency trend and lead-time bottleneck phase when releases are clustered or delayed. Launch owns the cadence strategy.
- **To Triage**: when the data pipeline blocks tier classification (no deploy events, no incident log, gh rate-limited).
