# V.A.I.R.E. Evaluation Examples

Real evaluation examples with scoring rationale.

---

## Example 1: E-Commerce Checkout Flow

### Evaluation Context

```yaml
Target: Checkout flow (cart → payment → confirmation)
Level: L1 (Standard - core flow)
Scope: 4 screens, 1 modal
```

### Scorecard

| Dimension | Score | Evidence | Issues |
|-----------|-------|----------|--------|
| **V** Value | 3/3 | Purchase complete in 3 steps, main CTAs clear, skeleton display present | None |
| **A** Agency | 1/3 | "Cancel purchase" is hard to find, consent checkbox is pre-checked | Pre-checked consent, weak cancel path |
| **I** Identity | 2/3 | Can save addresses as "Home" or "Work", polite error messages | None |
| **R** Resilience | 2/3 | Payment failure shows reason, cart auto-saves | Offline state not designed |
| **E** Echo | 2/3 | Purchase complete screen shows order summary and next actions, link to email confirmation | None |

**Total**: 10/15
**Minimum**: Agency 1/3
**Verdict**: ❌ **FAIL**

### Blocking Issues

#### [BLOCK-001] Agency: Pre-checked consent checkbox

| Aspect | Detail |
|--------|--------|
| Location | `/checkout/payment.tsx:142` |
| Current State | "Receive marketing emails" is checked by default |
| Impact | Emails sent without user consent, GDPR violation risk |
| Remediation | Change default to unchecked |
| Owner | Builder |
| Priority | CRITICAL |

#### [BLOCK-002] Agency: Weak cancel path

| Aspect | Detail |
|--------|--------|
| Location | `/checkout/confirm.tsx:58-72` |
| Current State | "Complete purchase" button (blue, large), "Cancel" link (gray, small, bottom) |
| Impact | Users have difficulty finding how to cancel purchase |
| Remediation | Make cancel button equally visible |
| Owner | Palette |
| Priority | HIGH |

### Handoff

```markdown
## WARDEN_TO_PALETTE_HANDOFF

**Target**: Checkout flow
**Verdict**: ❌ FAIL (Agency: 1/3)

**Required Fixes**:
1. BLOCK-002: Improve cancel button visibility
   - Make "Cancel" same size button as "Complete purchase"
   - Change layout to side-by-side

**After Fix**: Request Warden re-evaluation
```

---

## Example 2: User Settings Page

### Evaluation Context

```yaml
Target: Settings page (profile, notifications, privacy)
Level: L1 (Standard)
Scope: 3 tabs, 15 settings
```

### Scorecard

| Dimension | Score | Evidence | Issues |
|-----------|-------|----------|--------|
| **V** Value | 2/3 | Settings grouped and easy to find | No search function (many settings) |
| **A** Agency | 3/3 | All settings have explanations, ON/OFF is clear, changes are instant with Undo | None |
| **I** Identity | 3/3 | Theme selection, notification frequency, language settings are comprehensive | None |
| **R** Resilience | 2/3 | Save failure shows toast, retry button available | Loading state missing in some areas |
| **E** Echo | 2/3 | "Settings saved" confirmation on change | None |

**Total**: 12/15
**Minimum**: Value, Resilience, Echo each 2/3
**Verdict**: ✅ **PASS**

### Notes

Good design overall. Agency (3/3) is particularly excellent. Optional improvements for future:

1. **Value**: Add search function if settings grow
2. **Resilience**: Add loading states to all components

---

## Example 3: AI Chat Interface

### Evaluation Context

```yaml
Target: AI chatbot interface
Level: L2 (Differentiation - core product experience)
Scope: Chat UI, response generation, conversation history
```

### Scorecard

| Dimension | Score | Evidence | Issues |
|-----------|-------|----------|--------|
| **V** Value | 3/3 | Immediate input available, sample questions provided, responses display progressively | None |
| **A** Agency | 1/3 | Unclear what AI is recording, conversation deletion not found | Lack of transparency, no delete path |
| **I** Identity | 2/3 | Can resume from chat history, tone settings (formal/casual) | None |
| **R** Resilience | 0/3 | Response generation failure shows only "An error occurred", no retry button | All states undesigned, insufficient error messages |
| **E** Echo | 1/3 | Unclear how to end conversation, long conversations continue forever | No breaks, no summary |

**Total**: 7/15
**Minimum**: Resilience 0/3
**Verdict**: ❌ **FAIL**

### Blocking Issues

#### [BLOCK-001] Resilience: No state design at all

| Aspect | Detail |
|--------|--------|
| Location | `/chat/ChatResponse.tsx` |
| Current State | Only 1 of 5 states (success) implemented out of loading/empty/error/offline/success |
| Impact | Users get stuck on error, doesn't work offline |
| Remediation | Design and implement all 5 states |
| Owner | Builder |
| Priority | CRITICAL |

#### [BLOCK-002] Agency: Lack of data transparency

| Aspect | Detail |
|--------|--------|
| Location | Entire Chat UI |
| Current State | No explanation of how AI uses conversations |
| Impact | Users don't understand what they're sharing |
| Remediation | Add privacy explanation and conversation delete function |
| Owner | Builder + Palette |
| Priority | CRITICAL |

#### [BLOCK-003] Echo: No ending design

| Aspect | Detail |
|--------|--------|
| Location | `/chat/ChatContainer.tsx` |
| Current State | Conversations continue indefinitely with no termination or breaks |
| Impact | Users can't feel "done", dependency risk |
| Remediation | Add conversation summary, session breaks, "That's enough for today" suggestions |
| Owner | Palette |
| Priority | HIGH |

---

## Example 4: Subscription Cancellation Flow

### Evaluation Context

```yaml
Target: Subscription cancellation (settings → cancel → confirm)
Level: L0 (Minimum Viable - must not be a dark pattern)
Scope: 2 screens, 1 modal
```

### Scorecard

| Dimension | Score | Evidence | Issues |
|-----------|-------|----------|--------|
| **V** Value | N/A | Value doesn't apply to cancellation flow | - |
| **A** Agency | 0/3 | "Cancel" is hidden deep in settings, "Are you sure you want to cancel?" guilts user | Roach Motel, Confirmshaming |
| **I** Identity | 1/3 | Cancellation reasons are provided as choices | Forced reason selection |
| **R** Resilience | 2/3 | Cancellation processing state displayed | None |
| **E** Echo | 0/3 | After cancellation: "We're sorry to see you go" "Please come back" long message | Guilt-tripping, bad ending |

**Total**: 3/15 (3 out of 12 excluding V)
**Minimum**: Agency 0/3, Echo 0/3
**Verdict**: ❌ **FAIL** (Dark Pattern Detected)

### Anti-Pattern Detection

| Pattern | Found | Location | Severity |
|---------|-------|----------|----------|
| **Confirmshaming** | ✅ | `/cancel/ConfirmModal.tsx` - "No, I'll lose my benefits" | CRITICAL |
| **Roach Motel** | ✅ | 1 click signup, 5 step cancellation | CRITICAL |
| **Hidden Costs** | ❌ | - | - |
| **Misdirection** | ✅ | "Don't cancel" button is large and blue, "Cancel" is small and gray | HIGH |

### Verdict Commentary

> This flow is a collection of dark patterns. Legal risk exists (GDPR, consumer protection laws), immediate correction required. Maintaining this design for business reasons is not permitted.

### Required Remediation

1. **Cancel path**: Place "Subscription Management" at settings top level
2. **Button design**: Make "Cancel" and "Continue" equally visible
3. **Copy fix**: "No, I'll lose my benefits" → "Don't cancel" (neutral expression)
4. **Completion screen**: Remove "We're sorry", simple "Cancellation complete. Thank you for using our service."

---

## Example 5: Password Reset Flow

### Evaluation Context

```yaml
Target: Password reset (forgot → email → reset → login)
Level: L1 (Standard - account recovery is critical)
Scope: 4 screens, 1 email
```

### Scorecard

| Dimension | Score | Evidence | Issues |
|-----------|-------|----------|--------|
| **V** Value | 3/3 | "Forgot password" clearly shown on login screen, email delivery explained | None |
| **A** Agency | 2/3 | Reset link expiration clearly stated, resend available | None |
| **I** Identity | N/A | Identity doesn't apply to password reset | - |
| **R** Resilience | 3/3 | Email not received instructions provided, check spam folder prompt, resend button available | None |
| **E** Echo | 2/3 | After reset: "Go to login page" and optional "Review security settings" | None |

**Total**: 10/15 (10 out of 12 excluding I)
**Minimum**: Agency, Echo each 2/3
**Verdict**: ✅ **PASS**

### Notes

Excellent Resilience design (3/3). Exemplary as a recovery flow from failure state (password reset).

---

## Score Calibration Reference

### Score 3 Examples (Exemplary)

| Dimension | What Score 3 Looks Like |
|-----------|------------------------|
| **V** Value | Notion: Template selection for immediate value, Figma's learn-by-doing onboarding |
| **A** Agency | iOS: Detailed privacy settings, clear App Tracking consent request |
| **I** Identity | Slack: Per-workspace personas, emoji reactions, custom status |
| **R** Resilience | Google Docs: Offline editing, auto-save, conflict resolution, version history |
| **E** Echo | Headspace: Calm session-end summary, doesn't force next |

### Score 1 Examples (Failing)

| Dimension | What Score 1 Looks Like |
|-----------|------------------------|
| **V** Value | Empty dashboard with only "Please complete setup first" |
| **A** Agency | Modal where only "Agree" is clickable |
| **I** Identity | "Input error: Invalid value" message |
| **R** Resilience | "An error occurred" (no details, no retry) |
| **E** Echo | "Thank you for your purchase! Recommended products for you:" (no rest option) |

---

## Common Evaluation Mistakes

### Mistake 1: Averaging Scores

❌ Wrong: "Total 10/15, average 2.0, so PASS"
✅ Correct: "Minimum score is Agency 1/3, so FAIL"

**Rule**: The minimum score determines release decision. Not the average.

### Mistake 2: Skipping Dimensions

❌ Wrong: "This is a backend feature, so Echo doesn't apply"
✅ Correct: "Every user-facing flow has an ending. What happens after the API call completes?"

**Rule**: Evaluate all 5 dimensions. "Not applicable" is rare.

### Mistake 3: Accepting Business Justification

❌ Wrong: "Marketing wants the pre-checked box, so it's OK"
✅ Correct: "Pre-checked consent is a dark pattern. FAIL regardless of business request."

**Rule**: Quality standards are not compromised by business requirements.

### Mistake 4: Conditional Approval

❌ Wrong: "PASS if they fix it before release"
✅ Correct: "FAIL. Fix it, then request re-evaluation."

**Rule**: Conditional approval doesn't exist. PASS or FAIL only.
