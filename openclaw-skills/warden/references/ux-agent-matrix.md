# UI/UX Agent Differentiation Matrix

Clear boundaries between Warden and other UI/UX-related agents.

---

## Agent Overview

| Agent | Primary Role | Phase | Code Generation |
|-------|-------------|-------|-----------------|
| **Warden** | Quality gate (V.A.I.R.E.) | Pre-release | ❌ Never |
| **Echo** | Persona simulation | Validation | ❌ Never |
| **Palette** | UX implementation | Implementation | ✅ Yes |
| **Vision** | Creative direction | Strategy | ❌ Never |
| **Muse** | Design tokens | Systematization | ✅ Yes (tokens) |
| **Flow** | Animation | Implementation | ✅ Yes (CSS/JS) |
| **Showcase** | Storybook | Documentation | ✅ Yes (stories) |
| **Researcher** | User research | Discovery | ❌ Never |
| **Forge** | Rapid prototyping | Exploration | ✅ Yes (prototype) |
| **Artisan** | Frontend production | Implementation | ✅ Yes |

---

## Responsibility Matrix

### What Each Agent DOES vs DOESN'T Do

| Capability | Warden | Echo | Palette | Vision | Muse | Researcher |
|------------|--------|------|---------|--------|------|------------|
| **Issue PASS/FAIL verdict** | ✅ Primary | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Score 0-3 per dimension** | ✅ Primary | Emotion only | ❌ | ❌ | ❌ | ❌ |
| **Detect dark patterns** | ✅ Primary | ✅ Flags | ❌ | ❌ | ❌ | ❌ |
| **Simulate user persona** | ❌ | ✅ Primary | ❌ | ❌ | ❌ | ✅ Creates |
| **Walk through as user** | ❌ | ✅ Primary | ❌ | ❌ | ❌ | ❌ |
| **Report friction points** | ❌ | ✅ Primary | ❌ | ❌ | ❌ | ❌ |
| **Fix usability issues** | ❌ | ❌ | ✅ Primary | ❌ | ❌ | ❌ |
| **Reduce cognitive load** | ❌ | ❌ | ✅ Primary | ❌ | ❌ | ❌ |
| **Implement a11y** | ❌ | ❌ | ✅ Primary | ❌ | ❌ | ❌ |
| **Define design direction** | ❌ | ❌ | ❌ | ✅ Primary | ❌ | ❌ |
| **Set visual strategy** | ❌ | ❌ | ❌ | ✅ Primary | ❌ | ❌ |
| **Manage design tokens** | ❌ | ❌ | ❌ | ❌ | ✅ Primary | ❌ |
| **Ensure visual consistency** | ❌ | ❌ | ❌ | ❌ | ✅ Primary | ❌ |
| **Design interviews** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Primary |
| **Create personas** | ❌ | Uses | ❌ | ❌ | ❌ | ✅ Primary |
| **Journey mapping** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Primary |

---

## Decision Flow: Which Agent to Use?

```
User has UI/UX need
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ What is the primary goal?                                    │
└─────────────────────────────────────────────────────────────┘
         │
    ┌────┴────┬────────┬────────┬────────┬────────┬──────────┐
    ▼         ▼        ▼        ▼        ▼        ▼          ▼
 Release   Validate   Fix    Define  Unify    Research   Animate
   gate    as user    UX    vision  tokens   users       UI
    │         │        │        │        │        │          │
    ▼         ▼        ▼        ▼        ▼        ▼          ▼
 WARDEN    ECHO    PALETTE  VISION   MUSE  RESEARCHER    FLOW
```

### Detailed Decision Tree

```
Q: "Is this ready to ship?"
└─▶ WARDEN (V.A.I.R.E. evaluation, PASS/FAIL)

Q: "What would a beginner user experience?"
└─▶ ECHO (persona walkthrough, emotion scores)

Q: "This form is confusing, fix it"
└─▶ PALETTE (UX implementation, cognitive load reduction)

Q: "What should our design look like?"
└─▶ VISION (creative direction, style guide)

Q: "Make colors/spacing consistent"
└─▶ MUSE (design token application)

Q: "Add hover animation"
└─▶ FLOW (CSS/JS animation implementation)

Q: "Document this component"
└─▶ SHOWCASE (Storybook story creation)

Q: "Who are our users?"
└─▶ RESEARCHER (persona creation, interviews)

Q: "Build a quick prototype"
└─▶ FORGE (rapid MVP, working prototype)

Q: "Implement this design in React"
└─▶ ARTISAN (production frontend code)
```

---

## Evaluation vs Implementation

| Aspect | Evaluation Agents | Implementation Agents |
|--------|-------------------|----------------------|
| **Agents** | Warden, Echo, Researcher | Palette, Muse, Flow, Artisan, Forge |
| **Output** | Reports, scores, recommendations | Code, designs, components |
| **Changes files?** | ❌ No | ✅ Yes |
| **Issues verdicts?** | ✅ Yes (Warden) / Reports (Echo) | ❌ No |
| **When to use** | Before decisions, before release | After decisions made |

---

## Collaboration Patterns

### Pattern 1: Pre-Release Quality Gate

```
Artisan/Builder implements feature
              │
              ▼
         ┌─────────┐
         │  Echo   │ ──▶ Persona walkthrough report
         └────┬────┘
              │
              ▼
         ┌─────────┐
         │ Warden  │ ──▶ V.A.I.R.E. scorecard + PASS/FAIL
         └────┬────┘
              │
      ┌───────┴───────┐
      ▼               ▼
    PASS            FAIL
      │               │
      ▼               ▼
   Launch         Palette fixes ──▶ Re-evaluate
```

### Pattern 2: Design System Flow

```
Vision defines direction
         │
         ▼
    ┌─────────┐
    │  Muse   │ ──▶ Design tokens defined
    └────┬────┘
         │
         ▼
    ┌─────────┐
    │ Palette │ ──▶ Tokens applied to components
    └────┬────┘
         │
         ▼
    ┌─────────┐
    │Showcase │ ──▶ Components documented
    └─────────┘
```

### Pattern 3: User-Centered Design

```
Researcher creates personas
         │
         ▼
    ┌─────────┐
    │  Echo   │ ──▶ Validates design with personas
    └────┬────┘
         │
    Friction found?
         │
    ┌────┴────┐
    ▼         ▼
   No        Yes
    │         │
    ▼         ▼
 Warden   Palette ──▶ Echo re-validates
```

---

## Handoff Matrix

### Who Hands Off to Whom

| From ↓ / To → | Warden | Echo | Palette | Vision | Muse | Researcher |
|---------------|--------|------|---------|--------|------|------------|
| **Warden** | - | ❌ | ✅ Fix request | ❌ | ❌ | ❌ |
| **Echo** | ✅ Findings | - | ✅ Friction fix | ❌ | ❌ | ❌ |
| **Palette** | ✅ Re-eval request | ❌ | - | ❌ | ❌ | ❌ |
| **Vision** | ❌ | ❌ | ✅ Direction | - | ✅ Tokens | ❌ |
| **Muse** | ❌ | ❌ | ✅ Tokens | ❌ | - | ❌ |
| **Researcher** | ❌ | ✅ Personas | ✅ Insights | ✅ Insights | ❌ | - |

### Handoff Triggers

| Scenario | Handoff |
|----------|---------|
| Warden FAIL on Agency/Value/Identity/Echo | → Palette |
| Warden FAIL on Resilience | → Builder |
| Echo finds dark pattern | → Warden (for verdict) |
| Echo finds friction | → Palette (for fix) |
| Researcher creates persona | → Echo (for validation) |
| Vision defines direction | → Muse (for tokens) |
| Muse defines tokens | → Palette (for application) |

---

## Scope Boundaries

### Warden Does NOT

| ❌ Does Not | Who Does |
|-------------|----------|
| Walk through as persona | Echo |
| Fix usability issues | Palette |
| Define visual direction | Vision |
| Create design tokens | Muse |
| Write animation code | Flow |
| Create Storybook stories | Showcase |
| Conduct user research | Researcher |
| Build prototypes | Forge |
| Write production code | Artisan/Builder |

### Echo Does NOT

| ❌ Does Not | Who Does |
|-------------|----------|
| Issue PASS/FAIL verdict | Warden |
| Score V.A.I.R.E. dimensions | Warden |
| Fix the issues found | Palette |
| Create personas (uses them) | Researcher |
| Define design direction | Vision |

### Palette Does NOT

| ❌ Does Not | Who Does |
|-------------|----------|
| Issue verdicts | Warden |
| Simulate user experience | Echo |
| Define design direction | Vision |
| Manage design system | Muse |
| Conduct research | Researcher |

---

## Quick Reference

### One-Line Descriptions

| Agent | One-liner |
|-------|-----------|
| **Warden** | "Is this ready to ship?" → PASS/FAIL |
| **Echo** | "What would [persona] feel?" → Emotion report |
| **Palette** | "Make this easier to use" → UX code |
| **Vision** | "What should it look like?" → Direction |
| **Muse** | "Make it consistent" → Tokens |
| **Flow** | "Make it move" → Animation |
| **Showcase** | "Document the component" → Storybook |
| **Researcher** | "Who are our users?" → Personas |
| **Forge** | "Build it fast" → Prototype |
| **Artisan** | "Build it right" → Production code |

### When to Use Multiple Agents

| Goal | Agent Chain |
|------|-------------|
| Full UX quality assurance | Echo → Warden → Palette (if FAIL) |
| Design system creation | Vision → Muse → Palette → Showcase |
| User-centered redesign | Researcher → Vision → Echo → Palette |
| Pre-release gate | Builder → Echo → Warden → Launch |
| Accessibility audit | Warden (R dimension) → Palette (fixes) |

---

## Anti-Pattern: Wrong Agent Selection

| User Says | Wrong Choice | Right Choice | Why |
|-----------|--------------|--------------|-----|
| "Review my UI" | Judge | Warden or Echo | Judge reviews code logic, not UX |
| "Make it pretty" | Palette | Vision + Muse | Palette fixes usability, not aesthetics |
| "Add dark mode" | Palette | Muse | Token-level concern, not component |
| "Test as new user" | Voyager | Echo | Voyager does E2E tests, Echo simulates personas |
| "Is this accessible?" | Sentinel | Warden (R) + Palette | Sentinel does security, not a11y |
