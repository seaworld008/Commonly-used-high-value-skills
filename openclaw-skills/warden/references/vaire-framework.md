# V.A.I.R.E. Framework Reference

Complete reference for the V.A.I.R.E. framework.

---

## Framework Overview

V.A.I.R.E. is a design language that defines experience quality across 5 dimensions.

```
        ┌─────────────────────────────────────────────────┐
        │                USER JOURNEY                      │
        │                                                  │
        │   Entry      Progress      Continuation   Exit   │
        │     │           │              │           │     │
        │     ▼           ▼              ▼           ▼     │
        │  ┌─────┐    ┌─────┐       ┌─────┐     ┌─────┐   │
        │  │  V  │───▶│  A  │──────▶│  I  │────▶│  E  │   │
        │  │alue │    │gency│       │dent │     │cho  │   │
        │  └─────┘    └─────┘       └─────┘     └─────┘   │
        │                                                  │
        │           ┌─────────────────────┐               │
        │           │    R e s i l i e n c e            │ │
        │           │    (Always present)               │ │
        │           └─────────────────────────────────────┘│
        └─────────────────────────────────────────────────┘
```

---

## Dimension 1: Value (Immediate Value Delivery)

### Definition

User understands "what they can do" and "what to do next" without confusion, reaching outcomes in minimum time.

### Temporal Position

**Entry** - Functions at the entry point of the experience.

### Core Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| Time-to-Value | Time to first value delivery | 30 seconds to few minutes |
| Activation Rate | First success experience rate | Industry average +20% |
| Task Success Rate | Task completion rate | 95%+ (critical flows) |
| Steps to Core Task | Steps to reach core task | ≤3 |

### Design Levers

| Lever | Description | Implementation |
|-------|-------------|----------------|
| **Time-to-Value Design** | Create "small success" in first 30 seconds to few minutes | Templates, demo data, guided tours |
| **Information Priority** | Main task front and center | Visual hierarchy, progressive disclosure |
| **Default Design** | Eliminate confusion | Recommended values, smart defaults |
| **Onboarding** | "Learn by doing" over explanations | Interactive tours |
| **Feedback** | Consistent action→response→result | Immediate UI response |
| **Perceived Speed** | Loading visibility | Skeleton screens, progressive display |

### Acceptance Criteria (Score 2)

- [ ] Entry to core task within 3 steps
- [ ] Primary button/next action is visually prioritized
- [ ] Empty state explains "what will happen/what to do next"
- [ ] Loading shows reason and progress

### Anti-Patterns

| Pattern | Description | Detection |
|---------|-------------|-----------|
| **Empty Landing** | Looks impressive but does nothing | Hero screen → nothing |
| **Choice Overload** | User bears burden of thinking | 5+ choices at same level |
| **Blind Failure** | Cause/next step unknown on failure | Dead end after error |

---

## Dimension 2: Agency (User Control & Autonomy)

### Definition

User can "choose", "decline", and "go back", not losing dignity in exchange for convenience.

### Temporal Position

**Progress** - Functions during progression.

### Core Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| Settings Reach Rate | Rate of reaching settings | Higher is better |
| Opt-out Rate | Notification OFF rate | Lower is better (high = design problem) |
| Undo Usage Rate | Undo/restore usage rate | Existence is important |
| Cancellation Ease | Cancellation completion rate | Equal ease to signup |

### Design Levers

| Lever | Description | Implementation |
|-------|-------------|----------------|
| **Consent Design** | Present purpose, benefit, alternative, revocation method | Clear consent flow |
| **Settings Center** | Adjustable notifications, privacy, personalization | Fine-grained control UI |
| **Reversibility** | Undo, drafts, restore, history, rollback | Operation history and undo stack |
| **Transparency** | Don't hide fees/conditions/limits/automation scope | Pre-disclosure |
| **Honest Choices** | Don't hide decline path | Equal visibility |
| **Easy Cancellation** | End as easily as start | Simple cancellation flow |

### Acceptance Criteria (Score 2)

- [ ] Important actions (delete/charge/publish) have preview and cancel path
- [ ] Permission requests (notification/location etc.) explain reason in context first
- [ ] Personalization/recommendations allow OFF/weak/strong choice (at least OFF)

### Anti-Patterns (Dark Patterns)

| Pattern | Description | Severity |
|---------|-------------|----------|
| **Confirmshaming** | Guilt-trip on decline | CRITICAL |
| **Roach Motel** | Easy to enter, hard to leave | CRITICAL |
| **Hidden Costs** | Fees revealed later | CRITICAL |
| **Trick Questions** | Confusing double negatives | HIGH |
| **Forced Continuity** | Hidden auto-renewal | HIGH |
| **Misdirection** | Visual manipulation of choice | HIGH |
| **Privacy Zuckering** | Data public by default | HIGH |

---

## Dimension 3: Identity (Self, Context, Belonging)

### Definition

Product fits as user's own tool rather than "someone's tool", giving continuity meaning.

### Temporal Position

**Continuation** - Functions during continued use.

### Core Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| Personalization Usage | Personalization usage rate | Exists and used |
| Retention | D1/D7/D30 retention | Industry benchmark +10% |
| Regret Rate | Regret rate (delete/report rate) | Lower is better |
| "My Tool" Sentiment | Do they say "my tool"? | Confirm in qualitative research |

### Design Levers

| Lever | Description | Implementation |
|-------|-------------|----------------|
| **Self-expression** | Profile, display name, icon, theme, sorting | Customization UI |
| **Context Adaptation** | Modes for beginner/expert, work/personal | Mode switching |
| **Language Personality** | Tone & manner, respect, distance, no shaming | Microcopy guide |
| **Community Design** | Participation barrier adjustment, anti-harassment, weak protection | Moderation |
| **Cultural Translation** | Understand memes without breaking them | Localization |

### Acceptance Criteria (Score 2)

- [ ] At least one setting where user can make it "their own"
- [ ] System messages don't attack user's character on failure
- [ ] Sharing/publishing defaults to private or has clear boundaries

### Anti-Patterns

| Pattern | Description | Detection |
|---------|-------------|-----------|
| **Forced Identity** | Real name required, excessive social integration forced | Required input fields |
| **Belonging Pressure** | Design makes not participating look like a loss | FOMO language |
| **Surface Culture** | Alienating with cringeworthy execution | Context-free memes |

---

## Dimension 4: Resilience (Recovery & Inclusion)

### Definition

User doesn't get stuck facing failure and uncertainty (connection, auth, input mistakes, errors, outages). System doesn't collapse under operation.

### Temporal Position

**Anytime** - Always functions (cross-cutting).

### Core Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| Crash-free Sessions | Crash-free session rate | 99.9%+ |
| Error Rate | Error occurrence rate | <5% common flows |
| Recovery Rate | Task completion rate after error | 90%+ |
| Support Classification | Support ticket classification (recovery path missing vs explanation missing) | Classify and improve |

### Design Levers

| Lever | Description | Implementation |
|-------|-------------|----------------|
| **State Design** | Clearly define loading/empty/error/offline/partial success | 5-state components |
| **Retry** | Retry, queue, backoff, resend | Auto-retry logic |
| **Data Protection** | Drafts, auto-save, idempotency | Local storage |
| **Observability** | Logs, traces, error IDs (connect to support) | Error ID display |
| **Accessibility** | Keyboard, contrast, screen reader, focus | WCAG AA |
| **Recovery UX** | Rescue for forgot password, device change, 2FA loss, billing trouble | Recovery flows |

### Acceptance Criteria (Score 2)

- [ ] Main flows have "connection failure branch" designed
- [ ] If dropped mid-input, can resume on return
- [ ] Errors show cause/impact/next step in human language
- [ ] Main operations completable by keyboard only

### Five States Checklist

| State | Required | Description |
|-------|----------|-------------|
| **loading** | ✅ | Processing. Show reason and progress |
| **empty** | ✅ | No data. Guide next action |
| **error** | ✅ | Failure. Show cause, impact, next step |
| **offline** | ✅ | Offline. Guide limitations and recovery |
| **success** | ✅ | Success. Confirm result, present next choices |

### Anti-Patterns

| Pattern | Description | Detection |
|---------|-------------|-----------|
| **Infinite Loading** | No distinction between complete/fail | 30+ second spinner |
| **Silent Error** | Error not displayed | console.log only |
| **State Loss** | Back erases data | Form → back → empty |
| **Double Execution** | Same operation causes double processing | Button spam = duplicates |

---

## Dimension 5: Echo (Aftermath & Endings)

### Definition

At the exit of the experience, user's mind and body feel "settled". Achievement is not exaggerated, leaving closure, safety, and freedom for next. This supports long-term trust and return visits.

### Temporal Position

**Exit** - Functions at the exit of the experience.

### Core Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| Session End Satisfaction | Satisfaction at session end | Lightweight survey |
| Return Rate | Next day/week return | Healthy return (watch for over-dependence) |
| Regret Proxies | Immediate uninstall, immediate cancel, consecutive undo | Lower is better |
| Complaint Rate | Complaint rate | Lower is better |

### Design Levers

| Lever | Description | Implementation |
|-------|-------------|----------------|
| **Ending Design** | completion → confirmation → next choices → permission to rest | Completion screen design |
| **Summary** | Crystallize what was achieved briefly | Receipt/record/history |
| **Atmosphere** | Don't over-explain, but don't confuse | Progressive disclosure |
| **Symbols** | Consistent language, motion, sound (don't overdo) | Sound design |
| **Stopping Point** | Breaks for infinite scroll and binge watching | "Are you still watching?" |
| **Reminder Ethics** | Don't motivate through guilt | Neutral notification copy |

### Acceptance Criteria (Score 2)

- [ ] Core task completion shows both "result confirmation" and "next action", both choosable
- [ ] No forced flow to next (push) after completion
- [ ] Notifications and reminders have frequency adjust/stop/snooze

### Anti-Patterns

| Pattern | Description | Detection |
|---------|-------------|-----------|
| **Over-celebration** | Exaggerate achievement to exhaustion | 🎉🎊🎁 spam |
| **Never-ending** | No stopping point | Infinite scroll, autoplay |
| **FOMO Pressure** | Pressure with "miss out/falling behind" | "Only X hours left!", "Everyone's doing it" |

---

## Cross-Cutting Concerns

### AI/Automation Requirements

When including AI features, add these evaluations:

| Dimension | AI-Specific Requirement |
|-----------|------------------------|
| **A** Agency | Adjustable automation ON/OFF, strength, scope |
| **A** Agency | Pre-execution consent, post-execution history and undo |
| **R** Resilience | Don't get stuck on mistakes, hallucinations, misreasoning |
| **V** Value | Instantly understand what AI will do |
| **E** Echo | User finishes satisfied, not dependent on AI suggestions |

### Always-On UI Requirements

When including notifications, widgets, voice UI:

| Requirement | Description |
|-------------|-------------|
| Interrupt Criteria | Urgency × Confidence × User state |
| Quiet Success | User doesn't get exhausted |
| Clear Stop | Snooze/stop is easy to find (Agency) |

### Trust-Critical Requirements

When including billing, cancellation, identity:

| Requirement | Description |
|-------------|-------------|
| Transparency | No hiding fees, conditions, renewal, cancellation method |
| Auth Recovery | Recovery when lost determines trust |
| Fraud Prevention Explanation | Friction requires explanation and rescue |

---

## Application Levels

| Level | Name | Applies To | Score Threshold |
|-------|------|---------|-----------------|
| **L0** | Minimum Viable VAIRE | All features | All dimensions ≥ 2 |
| **L1** | Standard | Main features (core flows) | All dimensions ≥ 2, 1+ at 3 |
| **L2** | Differentiation | Core experience, brand experience | Majority at 3 |

---

## Quick Reference Card

```
╔══════════════════════════════════════════════════════════════════╗
║                    V.A.I.R.E. QUICK REFERENCE                    ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  V = VALUE        | Can outcomes be reached in minimum time?     ║
║  A = AGENCY       | Can they choose, decline, go back?           ║
║  I = IDENTITY     | Does it become the user's own tool?          ║
║  R = RESILIENCE   | Does it not break, not block, allow recovery?║
║  E = ECHO         | Do they feel settled after completion?       ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  SCORE: 0=Not considered | 1=Partial | 2=Sufficient | 3=Exemplary║
║  PASS: All dimensions ≥ 2 | FAIL: Any dimension < 2              ║
╠══════════════════════════════════════════════════════════════════╣
║  NON-NEGOTIABLES:                                                ║
║  1. Location is known         6. Not just fast, but calming      ║
║  2. User has right to refuse  7. No deception (no dark patterns) ║
║  3. Can go back               8. Tolerates diversity             ║
║  4. Mistakes don't trap       9. Builds trust evidence           ║
║  5. Explanations are brief    10. Endings are designed           ║
╚══════════════════════════════════════════════════════════════════╝
```
