# Experience Axis Audit Reference

Purpose: Standalone audit of the **E (Experience)** axis of V.A.I.R.E. — does the emotional arc of the journey *feel* right? This reference covers onboarding joy, achievement signals, flow-state affordances, delight moments, friction-vs-meaning trade-offs, and the emotional arc across the journey including the ending. Run this when the `experience` subcommand is invoked or when emotional quality is the specific release concern.

## Scope Boundary

- **Warden `experience`**: scorecard-driven audit of *emotional quality* against the E axis of V.A.I.R.E. Outputs a 0-3 score, evidence, and remediation path. Does not author, does not animate.
- **Echo (elsewhere)**: persona cognitive walkthrough — Echo simulates "what would Persona X feel here?" turn-by-turn; `experience` judges whether the design *supports* the intended arc across personas.
- **Flow (elsewhere)**: motion and transition implementation — `experience` flags where delight/calm is missing; Flow builds it.
- **Palette (elsewhere)**: interaction quality and feedback — overlaps at the micro-level (feedback *is* an emotional signal); `experience` scores the whole arc, Palette fixes individual interactions.
- **Researcher / Canvas (elsewhere)**: journey mapping with emotion scores from real users — `experience` uses these as input when available, but can audit from design alone.
- **Prose (elsewhere)**: celebratory / calming copy — `experience` flags missing moments; Prose writes them.

If the question is "does the arc feel joyful / calm / settled?" → `experience`. If it is "where exactly does Kenji-san get frustrated?" → Echo. If it is "the celebration animation is janky" → Flow.

## Core Checks

| # | Check | Score 2 baseline | Score 3 target |
|---|-------|------------------|----------------|
| E1 | Onboarding joy | First-success moment is intentional, visible, and emotionally positive | Learn-by-doing, first outcome within 60s, a smile-worthy moment |
| E2 | Achievement signals | Meaningful milestones are acknowledged (not every click, but the real wins) | Achievement is proportional to effort, receipts are keepable / shareable |
| E3 | Flow-state affordances | Core work views reduce chrome, minimize interruption, honor keyboard | Dedicated focus mode, interruption budget enforced, context preserved |
| E4 | Delight moments | ≥ 1 delightful detail in the core flow (animation, copy, sound) that isn't purely functional | Delight is woven, not sprinkled — feels native, not decorative |
| E5 | Friction-vs-meaning | Friction is present only where it adds meaning (confirm destructive, slow down for care) | Friction is deliberate; nowhere is it present by neglect |
| E6 | Emotional arc | Entry / progress / exit each have a deliberate emotional intent | Arc resolves — user feels *settled*, not abandoned, at the end |
| E7 | Ending design | Completion is confirmed; next action is optional; notifications are stoppable | Natural break points, achievement receipt, no engagement-maximization traps |

## Audit Workflow

```
SCOPE     →  identify the primary emotional journey (onboarding / core task / exit)
          →  collect artifacts: flow, copy, motion, notification config, end-state
          →  tier as L0 (quick) / L1 (feature arc) / L2 (release arc)

AUDIT     →  walk the journey as-designed, noting the intended emotion at each step
          →  score each step against E1-E7
          →  mark friction points as "meaningful" / "neglectful" / "extractive"

SCORE     →  0 = missing · 1 = partial · 2 = sufficient · 3 = exemplary
          →  any engagement-maximization trap (infinite scroll pushing past natural
             stop, streak-guilt on exit, fake "you're leaving?" modals) → E7 = 0 → FAIL

HANDOFF   →  PASS → return score to `gate`
          →  FAIL → Echo (validate with persona) · Flow (motion) · Prose (arc copy) · Palette (feedback)
```

## Tiered Audit Depth

| Tier | Trigger | Arc audited | Time-box |
|------|---------|-------------|----------|
| L0 | Spot-check one micro-arc (e.g., onboarding only) | 1 arc, entry → first success | ≤ 15 min |
| L1 | Feature arc | Entry / progress / exit across one feature | ≤ 60 min |
| L2 | Release-gate E-axis audit | Full lifecycle: onboarding → core task → exit → re-entry | ≤ 4 h |

Pair with real emotion-score data from Researcher / Canvas Journey Maps when available. Design-only audits can score arc intent; only user data can score arc *delivery*.

## Friction Taxonomy (for E5)

| Kind | Verdict | Example |
|------|---------|---------|
| Meaningful | Score 2+ | Confirm before deleting a customer record with 500 invoices attached |
| Calming | Score 2+ | 2-step pause before sending a large payout (gives deliberate slowness) |
| Neglectful | Score 1 | 3 clicks to change a setting that could be inline — no design intent |
| Extractive | Score 0 (FAIL) | Confirmshaming on unsubscribe, guilt-trip on canceling a streak |

## Emotional Arc Test (fast E6 check)

Describe the intended emotion at three points in one sentence each:

- **Entry**: "The user should feel ___" (e.g., *oriented*, *welcomed*, *curious*).
- **Progress**: "The user should feel ___" (e.g., *competent*, *flowing*, *in-control*).
- **Exit**: "The user should feel ___" (e.g., *settled*, *accomplished*, *closed*).

If any of the three can't be answered crisply from the designed artifact → **E6 ≤ 1**. If the exit intention is "come back soon" phrased as a guilt trigger → **E7 = 0 → FAIL** (engagement-extraction pattern).

## Delight Calibration (for E4)

Delight is not frequency — it's weight and fit.

| Level | Example | Score |
|-------|---------|-------|
| None | No intentional delight in the core flow | 0 |
| Decorative | Generic confetti on every button press | 1 |
| Earned | Celebration proportional to the milestone (first invoice sent, workspace set up) | 2 |
| Native | Delight is woven into the brand voice and motion system; feels signature, not bolted-on | 3 |

## Ending-Design Checklist (for E7)

An ending is Score 2 only if all four of these hold:

- [ ] The completion state is visually distinct from the in-progress state (not just a grey "Done" text).
- [ ] The user has an explicit affordance to stop (close, log out, "I'm done for today").
- [ ] Any follow-up notification is opt-in, stoppable, and time-bounded (no perpetual streaks).
- [ ] The final screen leaves the user oriented — next session, saved progress, or a natural pause.

Score 3 adds: a keepable receipt (shareable summary, exportable record) and a natural break point the product honors (no dark-pattern interruption to prevent exit).

## Anti-Patterns

- ❌ Score E = 3 because of confetti on every click — delight inflation is noise, not Score 3.
- ❌ Treat "fast" as "joyful" — Value is speed, Experience is the *feel* of the speed.
- ❌ Ignore the ending because "shipping is the goal" — unresolved exits are the #1 E-axis gap.
- ❌ Approve engagement streaks / loss-framing as "retention UX" — these extract emotion, they don't give it.
- ❌ Score E without running the full arc end-to-end at least once — micro-level audits miss arc-level gaps.
- ❌ Add friction for "care" when the real cause is poor defaults — that's neglectful friction with a rationalization.
- ❌ Write the celebratory copy yourself — Experience flags the missing moment; Prose owns the words.
- ❌ Judge E from design alone when real emotion scores from Researcher/Canvas exist — use them.

## Handoff / Next Steps

On **PASS** (E ≥ 2):
- Return E-axis score and evidence to `gate` for scorecard aggregation.
- Flag any Score-2 item close to extractive friction for future watch.

On **FAIL** (E ≤ 1 or extractive pattern confirmed):
- Route to **Echo** to validate the arc gap with a persona cognitive walkthrough.
- Route to **Flow** when motion / transitions carry the missing emotional weight.
- Route to **Prose** for celebratory, calming, or arc-resolving copy.
- Route to **Palette** when micro-feedback (haptics, focus ring, success state) is the gap.
- Route to **Researcher** when the intended emotion at each arc point is undeclared — they own journey-map authoring.
- Block release until E ≥ 2 and no extractive pattern remains.
- Log arc patterns and friction taxonomy findings in `.agents/warden.md` for cross-project calibration.
