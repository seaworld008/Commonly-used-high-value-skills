# Identity Axis Audit Reference

Purpose: Standalone audit of the **I (Identity)** axis of V.A.I.R.E. — does the product feel like *itself* and like the user's? This reference covers personality alignment, tone-of-voice adherence, visual identity fidelity, distinctiveness vs competitors, trust-signal presence, and icon/illustration style consistency. Run this when the `identity` subcommand is invoked or when brand-drift is suspected before a full `gate`.

## Scope Boundary

- **Warden `identity`**: scorecard-driven audit of *brand-voice consistency and distinctiveness* against the I axis of V.A.I.R.E. Outputs a 0-3 score, evidence, and remediation path. Does not write new copy, does not redesign.
- **Prose (elsewhere)**: authors the voice/tone itself (microcopy, voice-and-tone spec, error messages) — Identity audits adherence to the spec, not its creation.
- **Vision (elsewhere)**: creative direction and complete redesign when the brand itself is off — Identity flags drift, Vision re-authors.
- **Muse (elsewhere)**: design tokens (color / type / spacing) — Identity checks token *usage* in UI, Muse defines them.
- **Compete (elsewhere)**: competitor benchmarking and positioning maps — Identity checks distinctiveness using Compete output, does not re-run the competitor study.
- **Canon (elsewhere)**: standards compliance (WCAG contrast, ISO) — orthogonal to Identity.

If the question is "does this feel like us?" → `identity`. If it is "what should our voice be?" → Prose or Vision. If it is "are we differentiated from competitor X?" → Compete first, then `identity` to verify execution.

## Core Checks

| # | Check | Score 2 baseline | Score 3 target |
|---|-------|------------------|----------------|
| I1 | Personality alignment | Copy, imagery, and motion all land within the declared brand personality traits | Personality is recognizable from 1 screen without logo |
| I2 | Tone-of-voice adherence | Voice-and-tone spec is followed across success / error / empty / onboarding states | Tone adapts to context (celebratory / calming / urgent) within the same voice |
| I3 | Visual identity fidelity | Design tokens (color, type, spacing, radius) used — no ad-hoc values in audited scope | Distinctive visual signature (custom type / illustration / motion) present |
| I4 | Distinctiveness vs competitors | First viewport is not the generic SaaS grid (3-stat cards + 3-feature icons) | Brand is identifiable within 2 seconds without the wordmark |
| I5 | Trust-signal presence | Appropriate trust signals for the stage (security badges, pricing transparency, team, reviews) | Trust signals are native to the flow, not bolted-on footer clutter |
| I6 | Icon / illustration style consistency | All icons share a family (weight / corner / fill rule); illustrations share a system | Custom illustration system or distinctive icon family, no mixed stock |
| I7 | Personalization / "my tool" feeling | ≥ 1 meaningful personalization (name, workspace, saved view) surfaces without setup friction | Context-adaptive modes, saved preferences persist and are visible |

## Audit Workflow

```
SCOPE     →  collect brand guidelines (voice spec, token library, logo/illustration system)
          →  collect competitor refs from Compete (if distinctiveness is in scope)
          →  tier as L0 / L1 / L2

AUDIT     →  walk target screens against I1-I7
          →  pull evidence (screenshots, token usage diff, copy vs spec delta)
          →  run the 2-second test: hide the wordmark, can a stranger identify the brand?

SCORE     →  0 = missing · 1 = partial · 2 = sufficient · 3 = exemplary
          →  Generic SaaS grid on first viewport → I4 ≤ 1 (see design-litmus-check.md)

HANDOFF   →  PASS → return score to `gate`
          →  FAIL → Prose (copy) · Vision (direction) · Muse (tokens) · Palette (execution)
```

## Tiered Audit Depth

| Tier | Trigger | Surfaces audited | Time-box |
|------|---------|------------------|----------|
| L0 | Quick brand-drift spot-check | 1 hero + 2 inner screens | ≤ 15 min |
| L1 | Feature-level identity audit | Full feature, all states, primary + inverted themes | ≤ 60 min |
| L2 | Release-gate I-axis audit | Marketing + product + email + in-app + mobile + desktop | ≤ 4 h |

If the brand is pre-launch or mid-rebrand, escalate to **Vision** before running I-axis — auditing against a shifting target wastes cycles.

## Generic-SaaS Litmus (fast I4 check)

If the first viewport contains ≥ 2 of the following, **I4 is capped at 1**:

- 3–4 stat cards with big numbers and grey labels.
- 3–4 feature cards each with a thin-line icon, bold heading, 2-line description.
- A blue or purple gradient hero with a centered H1 and a white primary button.
- A screenshot of a dashboard floating at an angle with a drop shadow.
- A "Trusted by" logo strip using only greyed-out B2B logos.

This is the default failure mode of brand-less product UI. Score 3 requires at least one distinctive device (custom type, editorial layout, motion signature, proprietary illustration) that a competitor could not trivially clone.

## Voice-Adherence Sampling

Identity cannot be judged from a single screen. Minimum sample for I2:

| State | Example surface | What to check |
|-------|-----------------|---------------|
| Success | "Plan saved" toast | Tone matches declared voice trait (e.g., "warm" not "cheerful") |
| Error | "Payment failed" | No blame-the-user language; tone stays in-voice under stress |
| Empty | "No results yet" | Encouragement without condescension |
| Loading | Skeleton / spinner copy | Voice present in microcopy, not just emoji |
| Onboarding | First-run welcome | Sets the voice expectation within first 2 screens |

If ≥ 2 of these drift from the spec → I2 ≤ 1.

## Trust-Signal Appropriateness

Trust signals are Score 2 when *contextually placed*, Score 0 when stacked as security theater.

| Stage | Appropriate signal | Inappropriate signal |
|-------|-------------------|----------------------|
| Signup | "We don't share your email" inline | 12 security-badge logos in footer |
| Payment | PCI / Stripe badge near card field | Fake countdown urgency timer |
| Data export | "Your data is yours" with export affordance | Vague "trusted by thousands" with no count |
| Cancellation | Plain path + honest retention offer | Dark-pattern guilt-trip modal |

## Anti-Patterns

- ❌ Score I = 3 because the design system exists; Score 3 requires a *distinctive signature*, not just tidy tokens.
- ❌ Treat voice-spec presence as adherence — spot-check at least 5 states (success, error, empty, loading, offline).
- ❌ Accept mixed icon families ("we bought 2 icon packs") as Score 2 — this is Score 1.
- ❌ Give I4 = 2 because the logo is on every page — Identity is about distinctiveness *without* the logo.
- ❌ Audit Identity from desktop only — mobile compresses brand expression and exposes token-abuse faster.
- ❌ Write the replacement copy inside the Identity report — that is Prose's job; Identity only flags.
- ❌ Approve trust-signal bloat (badges, testimonials, counters all at once) as Score 3 — excess erodes trust; I5 = 2 is enough when contextually placed.

## Handoff / Next Steps

On **PASS** (I ≥ 2):
- Return I-axis score and evidence to `gate` for scorecard aggregation.
- Note weakest Score-2 item as optional uplift candidate.

On **FAIL** (I ≤ 1):
- Route to **Prose** when the gap is voice-and-tone / copy-vs-spec drift.
- Route to **Vision** when the gap is creative direction (brand itself feels wrong).
- Route to **Muse** when the gap is token-system abuse (hard-coded colors, ad-hoc spacing).
- Route to **Palette** when tokens exist but execution is inconsistent (component-level drift).
- Route to **Compete** when distinctiveness cannot be judged without competitor context.
- Block release until I ≥ 2.
- Log brand-drift patterns in `.agents/warden.md` for cross-project calibration.
