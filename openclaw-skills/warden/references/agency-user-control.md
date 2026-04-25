# Agency Axis Audit Reference

Purpose: Standalone audit of the **A (Agency)** axis of V.A.I.R.E. — does the user remain in control at every step? This reference covers undo/redo, cancel/abort, destructive-action confirmation, exit affordances, consent granularity, opt-out visibility, and dark-pattern nudging. Run this when the `agency` subcommand is invoked or when a flow needs isolated user-control validation before a full `gate`.

## Scope Boundary

- **Warden `agency`**: scorecard-driven audit of *user control, consent, and reversibility* against the A axis of V.A.I.R.E. Outputs a 0-3 score, evidence, and remediation path. Does not fix.
- **Palette (elsewhere)**: implements usability-friction fixes (cognitive load, feedback, a11y) — receives Agency FAIL handoffs.
- **Prose (elsewhere)**: authors the voice of consent copy / confirmation microcopy — Agency audits only whether the affordance exists, not the wording.
- **Canon (elsewhere)**: standards compliance (WCAG, ISO 25010) — Agency overlaps with WCAG 2.2 SC 3.3.4/3.3.6 (error prevention) but scores against V.A.I.R.E., not WCAG gaps.
- **Echo (elsewhere)**: persona cognitive walkthrough — Agency checks affordance presence, Echo checks whether a specific persona notices or uses it.

If the question is "can the user refuse, reverse, or exit?" → `agency`. If it is "does the undo button feel clear?" → Palette. If it is "would Emi-san (mobile-novice) find the cancel?" → Echo.

## Core Checks

| # | Check | Score 2 baseline | Score 3 target |
|---|-------|------------------|----------------|
| A1 | Undo / Redo | Undo on last destructive action, within 5s | Multi-step undo, named history |
| A2 | Cancel / Abort | All long-running operations have a Cancel that actually aborts server-side work | Graceful partial results + resume option |
| A3 | Destructive confirmation | Confirm dialog for delete/disable/payment with explicit verb | Typed confirmation for irreversible, impact preview shown |
| A4 | Exit any flow | "Close" or back affordance present on every step of every modal/flow | Escape key works, flow state is preserved on re-entry |
| A5 | Consent granularity | Per-purpose consent (analytics / marketing / 3rd-party) — no all-or-nothing | Runtime re-consent prompt at new purpose use |
| A6 | Opt-out visibility | Opt-out path is ≤ 2 clicks and not visually de-emphasized vs opt-in | Opt-out is symmetric to opt-in (same weight, same path length) |
| A7 | No dark-pattern nudging | No confirmshaming, no pre-checked opt-ins, no forced continuity, no misdirection | Declining is the default visual weight; no emotional coercion copy |

## Audit Workflow

```
SCOPE     →  identify flow boundaries + every destructive or consent touchpoint
          →  tier as L0 (quick) / L1 (feature) / L2 (release gate)

AUDIT     →  walk each touchpoint against A1-A7
          →  record evidence (URL / screen / component path)
          →  flag dark-pattern symptoms against the 7-pattern catalog

SCORE     →  0 = missing · 1 = partial · 2 = sufficient · 3 = exemplary
          →  any confirmed dark pattern forces A7 = 0 → automatic FAIL

HANDOFF   →  PASS (A ≥ 2, no dark pattern) → return to `gate` or release
          →  FAIL → Palette (affordance) · Prose (copy) · Builder (confirm flow)
```

## Tiered Audit Depth

| Tier | Trigger | Touchpoints audited | Time-box |
|------|---------|---------------------|----------|
| L0 | Quick spot-check on one flow | 1 destructive + 1 consent touchpoint | ≤ 15 min |
| L1 | Feature-level audit | All destructive + all consent in the feature | ≤ 60 min |
| L2 | Release-gate A-axis audit | Every touchpoint across the release scope | ≤ 4 h |

When in doubt, pick L1 — L0 misses Roach Motels that live 3 steps deep; L2 is overkill unless the feature handles payment, data export, or account deletion.

## Dark-Pattern Quick Catalog

| Pattern | Agency impact | Evidence trigger |
|---------|---------------|------------------|
| Confirmshaming | Emotional coercion to decline | "No, I don't want to save money" |
| Roach Motel | Exit harder than entry | Signup 1 click, cancel 6 clicks (FTC $2.5B Amazon, Sep 2025) |
| Forced Continuity | Silent auto-renewal | No pre-charge notification, no one-click cancel |
| Misdirection | Visual weight steers to opt-in | Primary button = consent, tertiary text-link = decline |
| Privacy Zuckering | Consent without granularity | Single "Agree to all" button, no per-purpose toggle |
| Trick Questions | Double-negative / reversed checkboxes | "Uncheck to not not receive emails" |
| Hidden Costs | Charge appears post-consent | Fees revealed only on payment step |

Any confirmed pattern → **A = 0, automatic FAIL**. FTC continues enforcement via ROSCA / Section 5 post Click-to-Cancel vacatur (8 Jul 2025); EU DFA proposal scheduled Q4 2026 expands scope to addictive design.

## Consent-Granularity Rubric

A single "Accept all / Reject all" pair is not Score 2 — it is Score 1 even if a "Settings" link exists behind it.

| Level | Example | Score |
|-------|---------|-------|
| None  | Only "Accept" visible | 0 |
| Binary | "Accept all" + "Reject all" on same screen | 1 |
| Per-purpose | Separate toggles for analytics / marketing / 3rd-party | 2 |
| Runtime re-ask | New purpose triggers fresh prompt at use time | 3 |

## Reversibility Rubric

| Level | Example | Score |
|-------|---------|-------|
| None | Delete is immediate and permanent | 0 |
| Confirm-only | Dialog asks "are you sure?" but no undo | 1 |
| Undo window | Toast with Undo for 5-10s on last action | 2 |
| Multi-step history | Named undo stack or restore-from-trash ≥ 24h | 3 |

## Anti-Patterns

- ❌ Score A = 2 because "there is a cancel button" without verifying it actually aborts the backend job.
- ❌ Accept pre-checked marketing opt-ins as "user agreed" — this is Privacy Zuckering regardless of regional law.
- ❌ Approve a flow where "Skip" is a grey text link and "Continue with notifications" is a blue button — that's Misdirection.
- ❌ Give A = 3 because the confirm dialog exists; Score 3 requires *impact preview* (what will be deleted / how many records affected).
- ❌ Audit Agency without running through the exit path end-to-end at least once — Roach Motels hide in step 4, not step 1.
- ❌ Treat "long cancellation flow" as acceptable because of "retention UX" — asymmetric exit vs entry is the defining Roach Motel signal.
- ❌ Delegate copy rewrites yourself — Agency flags the violation; Prose owns the rewrite.

## Handoff / Next Steps

On **PASS** (A ≥ 2, no dark pattern confirmed):
- Return A-axis score and evidence to `gate` for scorecard aggregation.
- Note any Score-2 items that are one step from Score-3 as optional uplift.

On **FAIL** (A ≤ 1 or dark pattern confirmed):
- Route to **Palette** for control affordance and interaction fix (e.g., add real Cancel, expose Undo).
- Route to **Prose** for confirmation copy / opt-out wording rewrite.
- Route to **Builder** when the reversibility is absent at the data-model level (no soft-delete, no transaction boundary).
- Route to **Cloak** when the gap is consent-granularity / GDPR lawful basis.
- Block release until A ≥ 2 and no dark pattern remains.
- Log the pattern in the Warden journal (`.agents/warden.md`) for cross-project calibration.
