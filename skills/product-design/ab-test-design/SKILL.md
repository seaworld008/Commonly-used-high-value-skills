---
name: ab-test-design
description: 'Use when designing an A/B or split test, defining hypothesis, primary metric, guardrails, randomization unit, MDE, sample size and duration via scripts/sample_size.py, and implementing flicker-free feature-flag rollout.'
zh_description: "用于设计严谨的 A/B 实验方案，明确假设、单一主指标、护栏指标、随机化单元、使用脚本测算样本量与周期及无闪烁特性开关落地。"
version: "1.0.0"
author: "Trystan Sarrade"
source: "https://github.com/Trystan-SA/product-engineer-skills"
source_url: "https://github.com/Trystan-SA/product-engineer-skills/tree/main/skills/ab-test-design"
license: MIT
tags: [ab-testing, experimentation, product-engineering, feature-flags, analytics]
created_at: "2026-11-23"
updated_at: "2026-11-23"
quality: 4
complexity: intermediate
---

# A/B Test Design

## When to Use

- Designing an A/B or split test before implementation: hypothesis, primary metric, guardrails, randomization unit, minimum detectable effect (MDE), sample size, and runtime budget.
- Deciding whether a change actually warrants an experiment versus shipping a bug fix or behind-flag qualitative validation.
- Implementing deterministic variant assignment, server/bootstrap evaluation without UI flicker, and exposure logging behind feature-flag platforms (GrowthBook, LaunchDarkly, Statsig, PostHog, Optimizely, Unleash, or in-house flags).


An A/B test is a measuring instrument. Designed badly, it gives a confident answer to the wrong question, or no answer after six weeks of traffic. This skill writes the experiment spec before any code, checks that the test is feasible, and implements it so the data can be trusted.

## Phase 1: Write the hypothesis

> Because <evidence>, we believe that <change> for <eligible users> will <increase or decrease> <primary metric> by at least <MDE>.

Evidence comes from `brief.md`, `flow-audit.md` or `adoption-plan.md` in the feature folder (`docs/product/<feature-slug>/`), from research, or from data. Test one idea per experiment: if the variant changes copy, layout and pricing at once, a win can't tell you which change worked. Bundling is fine when you only need the decision and not the learning — say so explicitly.

## Phase 2: Decide whether to test at all

An experiment fits when the change is reversible, the outcome is genuinely uncertain, and there's enough traffic. Don't run one when:

- **It's a fix.** Ship bug fixes, accessibility fixes and repaired flows directly.
- **Traffic is too low.** If Phase 4 asks for more than about 6–8 weeks, the test won't conclude. Alternatives: test a bigger change (larger MDE), choose a more sensitive metric closer to the change, widen the eligible population, or ship behind a flag and compare before and after with qualitative feedback — while saying clearly that this is weaker evidence.
- **The decision is already made.** A test nobody will act on is waste.

## Phase 3: Choose metrics and the unit

- **Primary metric** — exactly one, chosen now. It must move if the hypothesis is true, be measurable per randomization unit, and matter to the business: the value moment beats clicks on the button you changed.
- **Guardrails** — 2 to 4 metrics that must not get worse: error rate, latency, support contacts, revenue, unsubscribes, a later step of the funnel.
- **Secondary metrics** — for learning only, never to declare a winner.
- **Randomization unit** — the user for signed-in products (stable across devices); the **account or organization** when users collaborate, otherwise teammates see different versions and contaminate each other; an anonymous ID for signed-out flows (accept some cross-device noise).
- **Eligibility and exposure** — only users who can reach the change are enrolled, and they're counted from the moment they actually see it. Users who never reach the changed screen dilute the effect.

## Phase 4: Size it

Run the bundled calculator, in the `scripts/` folder next to this file:

```bash
# Conversion metric: 12% baseline, detect a +10% relative lift, 3,000 eligible users a day
python3 scripts/sample_size.py --baseline 0.12 --mde 0.10 --daily-users 3000

# Continuous metric: standard deviation 40, detect +3 units
python3 scripts/sample_size.py --std 40 --mde-abs 3 --daily-users 3000
```

It prints users per variant, the total, and the duration rounded up to whole weeks, because weekdays and weekends behave differently and a test should never stop mid-week. Defaults: α = 0.05 two-sided, 80 % power. With more than two variants it applies a Bonferroni correction; each extra variant costs traffic, so prefer two.

Sanity check by hand for conversions: n per variant ≈ 16 · p(1 − p) / δ², where δ is the absolute difference.

The MDE is a business decision, not a statistical one: the smallest lift worth shipping and maintaining. If the answer is "any lift", no test will ever be big enough.

## Phase 5: Implement

1. **Use the project's flag tool** (GrowthBook, LaunchDarkly, Statsig, PostHog, Optimizely, Unleash, Flagsmith, ConfigCat, Vercel Flags or an in-house system) and its experiment features — assignment and exposure logging — rather than random numbers in app code.
2. **Assign deterministically** by the randomization unit, so a user sees the same variant on every visit and device.
3. **Fall back to control** when the flag service fails or times out.
4. **No flicker.** Evaluate flags on the server or bootstrap them before first render. Showing control and then switching to the variant biases the result and degrades the experience.
5. **Log exposure** when the variant renders for an eligible user. Many SDKs log on evaluation, so evaluate at the point of exposure, not at app start.
6. **QA both variants** by forcing each one through the tool's overrides, and check that tracking fires in both (`instrument-feature`).
7. **Keep the variant easy to delete**: one flag check at a boundary, not conditions scattered through the code.

## Phase 6: Pre-register the analysis

Write these down now, before any data arrives:

- The fixed duration and sample size, and the commitment not to stop early because results look good. Peeking pushes the false-positive rate far above 5 %. If the tool supports sequential testing, use its rules instead and say so.
- The decision rule: ship if the primary metric improves significantly and no guardrail degrades beyond its threshold; otherwise keep control or iterate.
- The segments you'll look at — two or three at most, chosen in advance. Patterns found in other segments are hypotheses for the next test.

## Output

Write `experiment.md` to the feature folder: hypothesis, metrics, unit, eligibility, sample size and duration (with the calculator command), implementation notes (flag key, variants, exposure point), and the pre-registered analysis plan. Summarize: duration, MDE, and anything that makes the test risky. Archive the experiment spec beside code review notes so post-test readout evaluates against pre-registered hypotheses and guardrails.
## Worked Example & Pre-Launch Checklist

Example sizing run for a checkout onboarding funnel with 12% baseline conversion, +10% relative lift target (`12.00% -> 13.20%`), and 3,000 eligible daily users:

```bash
python3 scripts/sample_size.py --baseline 0.12 --mde 0.10 --daily-users 3000
# Effect to detect:  12.00% -> 13.20% (+1.20 pp, +10.0% relative)
# Alpha / power:     0.05 two-sided / 80%
# Users per variant: 12,001
# Total users:       24,002 (2 variants)
# Duration:          9 days of traffic -> run 14 days (2 full weeks)
```

Before enabling traffic allocation:

- **One primary metric + bounded guardrails:** Verify latency, error rate, and core funnel completion guardrails have alert thresholds defined before launch.
- **No flicker & deterministic bucketing:** Evaluate the flag before first paint (SSR/edge/bootstrap) keyed on user ID or organization ID so returning users never switch cohorts.
- **Exposure logging at point of visibility:** Log exposure only when the eligible user enters the changed surface, not globally on app startup.
- **Zero-peeking lock:** Record exact end date from `scripts/sample_size.py` upfront and keep variants isolated behind one boundary flag for fast cleanup after readout.

### Randomization & Rollout Decision Guide

| Product Context | Randomization Unit | Primary Guardrails | When to Abort / Iterate |
|---|---|---|---|
| Self-serve signup / solo flow | Signed-in user ID | Error rate, latency, step completion | Any guardrail crosses alert threshold |
| Multi-user workspace / team | Organization / tenant ID | Cross-seat errors, invite completion | Contamination across teammates |
| Logged-out landing / checkout | Anonymous device ID + server handoff | Bounce rate, payment failures | Flag flicker before first paint |
| Multi-variant test (3+ arms) | User or org (Bonferroni-adjusted) | All core metrics + runtime <= 6 weeks | Predicted duration > 8 weeks (increase MDE or revert to 2 arms) |
