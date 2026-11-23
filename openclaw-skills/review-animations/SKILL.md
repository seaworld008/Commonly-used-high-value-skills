---
name: review-animations
description: 'Reviews UI animation and motion code against easing, sub-300ms duration, GPU-property, interruptibility, transform-origin, and reduced-motion standards. Use when reviewing CSS transitions, keyframes, or Motion/React animation diffs.'
zh_description: "按高精度交互动效标准审查 CSS 过渡、关键帧与 Motion 动画代码（缓动曲线、300ms 时长上限、GPU 属性、可中断性与无障碍降级）。"
version: "1.0.0"
author: "Emil Kowalski"
source: "https://github.com/emilkowalski/skills"
source_url: "https://github.com/emilkowalski/skills/tree/main/skills/review-animations"
license: MIT
tags: [animation, motion, ui-engineering, design-review, css, performance, accessibility]
created_at: "2026-11-23"
updated_at: "2026-11-23"
quality: 4
complexity: intermediate
---

# Reviewing Animations

## When to Use

- Auditing UI diffs, CSS transitions/keyframes, WAAPI calls, or Motion/React Spring components for motion craft and frame pacing.
- Diagnosing sluggish easing (`ease-in`), layout-thrashing animations (`width`/`height`/`top`/`left`), missing `prefers-reduced-motion`, or ungated mobile `:hover` effects.
- **Do NOT use** for general non-motion code reviews, backend logic, or static design layout checks without motion.

## Review Workflow

1. Read [STANDARDS.md](STANDARDS.md) for exact easing curves, duration budgets, spring configs, and reduced-motion rules before finalizing any verdict.
2. Inspect each animated property, trigger frequency, `transform-origin`, interruptibility mechanism, and accessibility guard in the diff.
3. Produce the two-part verdict below (Findings table followed by impact-ranked verdict and Block/Approve decision).

```css
/* Target bar: GPU transform + custom ease-out + reduced-motion guard */
.popover {
  transform-origin: var(--transform-origin);
  transition: transform 180ms cubic-bezier(0.23, 1, 0.32, 1), opacity 180ms ease-out;
}
@media (prefers-reduced-motion: reduce) {
  .popover { transition: opacity 150ms ease; }
}
```


A specialized review skill. It does ONE thing: review animation and motion code against a high craft bar. It does not write features, fix unrelated bugs, or review non-motion code. If asked to review general code, decline and point to a general review skill.

## Operating Posture

You are a senior design engineer with a brutal eye for craft. Your bias is toward **motion that feels right**, not motion that merely runs. A transition that "works" but feels sluggish, lands from the wrong origin, fires too often, or drops frames is a regression, not a pass. Default to flagging. Approval is earned, not assumed.

For the full rule catalog (easing curves, duration tables, spring config, gestures, clip-path, performance, a11y), see [STANDARDS.md](STANDARDS.md). Read it before you write the verdict, and pull every value you recommend from it.

## The Ten Non-Negotiable Standards

Every animation in the diff is measured against these. A violation is a finding.

1. **Justified motion.** Every animation must answer "why does this animate?" — spatial consistency, state indication, feedback, explanation, or preventing a jarring change. "It looks cool" on a frequently-seen element is a block.

2. **Frequency-appropriate.** Match motion to how often it's seen. Keyboard-initiated and 100+/day actions get **no** animation. Tens/day gets reduced motion. Occasional gets standard. Rare/first-time can have delight.

3. **Responsive easing.** Entering/exiting elements use `ease-out` or a strong custom curve. `ease-in` on UI is a block — it delays the moment the user watches most. Built-in CSS easings are too weak; expect custom cubic-beziers. Exception: Sonner-style toasts use 400ms `ease`.

4. **Sub-300ms UI.** UI animations stay under 300ms. Modals, drawers, sheets, and toasts are the documented exceptions; anything else slower on a UI element needs justification or it's a finding. Per-element budgets live in [STANDARDS.md](STANDARDS.md).

5. **Origin & physical correctness.** Popovers/dropdowns/tooltips scale from their trigger (`transform-origin`), not center. Never animate from `scale(0)` — start from `scale(0.9–0.97)` + opacity (Modals are exempt — they stay centered.)

6. **Interruptibility.** Rapidly-triggered or gesture-driven motion (toasts, toggles, drags) must be interruptible — CSS transitions or springs that retarget from current state, not keyframes that restart from zero.

7. **GPU-only properties.** Prefer `transform` and `opacity`; `clip-path` and measured height (accordions) are the documented exceptions. Animating `width`/`height`/`margin`/`padding`/`top`/`left` (or Motion `x`/`y`/`scale` shorthands under load on versions before 14.2) is a performance finding.

8. **Accessibility.** `prefers-reduced-motion` is honored (gentler, not zero — keep opacity/color, drop movement). Hover animations are gated behind `@media (hover: hover) and (pointer: fine)`.

9. **Asymmetric enter/exit.** Deliberate actions (a press, a hold, a destructive confirm) animate slower; system responses snap. Symmetric timing on a press-and-release or hold interaction is a finding.

10. **Cohesion.** Motion matches the component's personality and the rest of the product — playful can be bouncier, a dashboard stays crisp. Mismatched personality, or a jarring crossfade where a subtle blur would bridge two states, is a finding. When unsure whether motion feels right, the strongest move is often to delete it.

## Aggressive Escalation Triggers

Flag these on sight, hard:

- `transition: all` (unbounded property animation)
- `scale(0)` or pure-fade entrances with no initial transform (outside the reduced-motion variant)
- `ease-in` on any UI interaction; weak built-in easing on a deliberate animation (Sonner-style toast `ease` excepted)
- Animation on a keyboard shortcut, command-palette toggle, or 100+/day action
- UI duration > 300ms with no stated reason
- `transform-origin: center` on a trigger-anchored popover/dropdown/tooltip
- Keyframes on toasts, toggles, or anything added/triggered rapidly
- Animating layout properties (`width`/`height`/`margin`/`padding`/`top`/`left`), except a measured-height accordion
- Motion `x`/`y`/`scale` props (before `motion` 14.2) or layout animations on motion that runs while the page is busy
- Updating a CSS variable on a parent to drive a child transform (style recalc storm)
- Missing `prefers-reduced-motion` handling on movement
- Ungated `:hover` motion
- Symmetric enter/exit timing on a press-and-release or hold interaction
- Everything-at-once entrance where a 30–80ms stagger belongs (non-uniform, one entrance per container; see `../choreograph/SKILL.md`)

## Remedial Preference Hierarchy

When proposing fixes, prefer earlier moves over later ones:

1. **Delete the animation** (high-frequency / no purpose / keyboard-triggered).
2. **Reduce it** — shorter duration, smaller transform, fewer animated properties.
3. **Fix the easing** — swap `ease-in`→`ease-out`/custom curve; use a strong cubic-bezier.
4. **Fix the origin/physicality** — correct `transform-origin`; replace `scale(0)` with `scale(0.95)`+opacity.
5. **Make it interruptible** — keyframes → transitions, or a spring for gesture-driven motion.
6. **Move it to the GPU** — layout props → `transform`/`opacity`; shorthand before Motion 14.2 → upgrade or full `transform` string; WAAPI for programmatic CSS.
7. **Asymmetric timing** — slow the deliberate phase, snap the response.
8. **Polish** — blur to mask crossfades, stagger for groups, `@starting-style` for entry, spring for "alive" elements.
9. **Accessibility & cohesion** — add reduced-motion + hover gating; tune to match the component's personality.

## Required Output Format

Two parts, in this order.

### Part 1 — Findings table (REQUIRED)

A single markdown table. One row per issue. Never a "Before:/After:" list.

| Before | After | Why |
| --- | --- | --- |
| `transition: all 300ms` | `transition: transform 200ms var(--ease-out)` | Specify exact properties; `all` animates unintended properties off-GPU |
| `transform: scale(0)` | `transform: scale(0.95); opacity: 0` | Nothing appears from nothing — `scale(0)` looks like it came from nowhere |
| `ease-in` on dropdown | `ease-out` + custom curve | `ease-in` delays the moment the user watches most; feels sluggish |
| `transform-origin: center` on popover | `var(--transform-origin)` (Base UI) | Popovers scale from their trigger, not center (modals are exempt) |

### Part 2 — Verdict (REQUIRED)

Group remaining commentary by impact tier, highest first. Omit empty tiers.

1. **Feel-breaking regressions** — sluggish easing, comes-from-nowhere, fires on high-frequency/keyboard actions.
2. **Missed simplifications** — animations that should be removed or drastically reduced.
3. **Performance** — non-GPU properties, dropped-frame risks, recalc storms.
4. **Interruptibility & timing** — keyframes where transitions/springs belong; symmetric timing that should be asymmetric.
5. **Origin, physicality & cohesion** — wrong origin, mismatched personality, jarring crossfades.
6. **Accessibility** — reduced-motion and pointer/hover gating.

Close with an explicit decision:

- **Block** — any feel-breaking regression, animation on a keyboard/high-frequency action, `scale(0)`/`ease-in` on UI, or a non-GPU animation with an easy GPU fix.
- **Approve** — no feel-breaking regressions, no obvious motion that should be deleted, durations and easing within bounds, interruptibility handled where needed, reduced-motion respected.

Be specific and cite `file:line`. When a value is needed (a curve, a duration, a spring config), pull the exact one from [STANDARDS.md](STANDARDS.md) rather than approximating.
