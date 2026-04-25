# Task Breakdown Framework

Purpose: Use this file during `MAP` to define hierarchy, size work, estimate effort, and stop decomposition at the right granularity.

## Contents

- Task hierarchy
- Epic input template
- T-shirt sizing
- Complexity factors
- Estimation formula
- Breakdown rules

## Task Hierarchy

| Level | Size | Description | Example |
| --- | --- | --- | --- |
| Epic | `1-5 days` | large feature or initiative | “Implement payment system” |
| Story | `2-8 hours` | user-facing slice | “Add checkout form” |
| Task | `30-120 min` | technical work unit | “Create PaymentForm component” |
| Atomic Step | `5-15 min` | single testable, committable action | “Define PaymentProps interface” |

## Epic Input Template

```markdown
## Epic: [Name]

**Goal**: [What we are trying to achieve]
**Success Criteria**: [How we know it is done]
**Constraints**: [Time, tech, scope limits]
**Out of Scope**: [What we are not doing]

**Initial Estimate**: [XS/S/M/L/XL]
**Risk Level**: [Low / Medium / High]
```

## T-Shirt Sizing

| Size | Minutes | Interpretation |
| --- | --- | --- |
| XS | `5-10` | trivial, clear path, no unknowns |
| S | `10-15` | simple and ready to execute |
| M | `15-30` | too large for an atomic step, split further |
| L | `30-60` | complex task, must be decomposed |
| XL | `60+` | always decompose immediately |

## Complexity Factors

| Factor | Multiplier | Meaning |
| --- | --- | --- |
| New technology | `1.5x` | first time using a library or API |
| Unclear requirements | `1.5x` | investigation still needed |
| External dependency | `2.0x` | approval, third party, or cross-team dependency |
| High risk | `1.5x` | could break existing functionality |
| Multiple files | `1.3x` | changes span several modules |

## Estimation Formula

```text
Actual Time = Base Estimate × Complexity Multiplier × Risk Buffer

Risk Buffer:
- Low: 1.0x
- Medium: 1.3x
- High: 1.5x
```

### Estimation Output

```markdown
### Time Estimate: [Step Name]

| Aspect | Value |
|--------|-------|
| Base Size | M (20 min) |
| Complexity | New API (1.5x) |
| Risk Level | Medium (1.3x) |
| Estimated | 39 min |

Over the 15-minute threshold -> split further.
```

## Breakdown Rules

1. Keep breaking work down until the current step is under `15 min`.
2. Every atomic step must be testable.
3. Every atomic step must be committable.
4. Identify the responsible agent for each step.
5. mark dependencies before execution starts.
6. Flag XL items immediately.
