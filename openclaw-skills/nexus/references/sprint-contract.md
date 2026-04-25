# Sprint Contract Protocol

**Purpose:** Define completion criteria before execution begins, aligning Generator and Evaluators.
**Read when:** Evaluator Loop is enabled and you need to create or reference a Sprint Contract.

---

## Overview

A Sprint Contract is a pre-execution agreement between the Generator agent and Evaluator agents. It defines what "done" means before any code is written, preventing scope drift and enabling objective evaluation. Inspired by the Generator-Evaluator pattern where both parties agree on acceptance criteria upfront.

---

## Contract Format

```yaml
SPRINT_CONTRACT:
  ID: "SC-[task-slug]-[YYYYMMDD]"
  Goal: "[1-2 sentence description of the deliverable]"
  Scope:
    in_scope:
      - "[specific deliverable 1]"
      - "[specific deliverable 2]"
    out_of_scope:
      - "[explicitly excluded item 1]"
      - "[explicitly excluded item 2]"
  Acceptance_Criteria:
    functional:
      - id: "AC-F-001"
        criterion: "[what must work]"
        verification_method: "[test | E2E | manual | static-analysis]"
        evaluator: "[Radar | Voyager | Attest | ...]"
      - id: "AC-F-002"
        criterion: "[what must work]"
        verification_method: "[method]"
        evaluator: "[evaluator]"
    quality:
      - id: "AC-Q-001"
        criterion: "[quality requirement]"
        threshold: "[measurable threshold, e.g., coverage > 80%]"
        evaluator: "[Judge | Zen | Sentinel | ...]"
  Rubric_Ref: "[FEATURE_UI | FEATURE_BACKEND | BUG_FIX | SECURITY]"
  Generator: "[agent name]"
  Evaluators: ["agent1", "agent2", "..."]
  Max_Iterations: [1-5, default: 3]
  Context_Strategy: "[reset | continuous | hybrid]"
```

---

## Creation Timing

Sprint Contracts are created during **AUTORUN_FULL Phase 2: PREPARE**, after task classification and before chain selection.

### Applicability

| Task Type | Complexity | Evaluator Loop | Contract Required? |
|-----------|-----------|----------------|-------------------|
| FEATURE | MEDIUM+ | YES | **Required** |
| SECURITY | Any | YES | **Required** |
| BUG | COMPLEX | YES | Recommended |
| BUG | SIMPLE | NO | Skip |
| REFACTOR | COMPLEX | YES | Recommended |
| REFACTOR | SIMPLE | NO | Skip |
| DOCS | Any | NO | Skip |

**Rule:** If Evaluator Loop is enabled, a Sprint Contract is required. If Evaluator Loop is skipped, the contract is optional.

---

## Contract Creation Flow

```
Phase 1: PLAN (task classified)
  ↓
Phase 2: PREPARE
  ↓
  Evaluator Loop applicable? (check applicability table)
    ├─ NO → Skip contract, proceed to CHAIN_SELECT
    └─ YES
         ↓
       Nexus creates SPRINT_CONTRACT:
         1. Extract Goal from user request
         2. Define Scope (in/out) from task analysis
         3. Derive Acceptance_Criteria from requirements
         4. Select Rubric_Ref from task type
         5. Assign Generator and Evaluators from chain
         6. Set Max_Iterations (default: 3)
         ↓
       Contract stored in execution context
         ↓
       Phase 3: CHAIN_SELECT (contract informs chain)
```

---

## Contract in Handoff

When a Sprint Contract exists, include its reference in `NEXUS_HANDOFF`:

```
## NEXUS_HANDOFF
- Summary: [...]
- Contract_Ref: SC-login-feature-20260325
- Next: [...]
```

The Generator agent receives the contract as part of its spawn prompt context. Evaluator agents receive the contract to know what criteria to evaluate against.

---

## Contract Lifecycle

| State | Trigger | Action |
|-------|---------|--------|
| `DRAFT` | PREPARE phase begins | Nexus creates contract |
| `ACTIVE` | EXECUTE phase begins | Generator starts work |
| `EVALUATING` | Generator completes iteration | Evaluators score against contract |
| `REVISED` | Evaluator returns REVISE | Generator receives feedback, iterates |
| `FULFILLED` | All Evaluators ACCEPT | Contract complete, proceed to DELIVER |
| `TERMINATED` | Max iterations reached OR diminishing returns | Best result accepted, proceed to DELIVER |

---

## Best Practices

1. **Keep scope tight** — Contracts should cover one Sprint's work, not an entire epic
2. **Measurable criteria** — Every acceptance criterion must have a concrete verification method
3. **Evaluator alignment** — Each criterion maps to exactly one evaluator
4. **Reasonable iterations** — Default to 3; use 1 for simple tasks, 5 only for critical deliverables
5. **Out-of-scope is explicit** — Prevents Generator from gold-plating
