# Evaluator Loop Pattern

**Purpose:** Generator-Evaluator separation for active quality assurance.
**Read when:** Task qualifies for Evaluator Loop and you need the evaluation orchestration pattern.

---

## Core Principle

> An agent must never evaluate its own output. (GAN-inspired separation)

The Generator produces deliverables; independent Evaluator agents assess them against the Sprint Contract. This separation eliminates self-assessment bias and catches issues that the Generator's context window cannot see.

---

## Loop Structure

```
Nexus → Agent(Generator) → _STEP_COMPLETE
                              ↓
Nexus → Agent(Evaluator-1, bg) + Agent(Evaluator-2, bg) → EVALUATION_FEEDBACK
                              ↓
Nexus → Aggregate feedback
         ├─ All ACCEPT     → DELIVER
         ├─ Any REVISE      → Agent(Generator, with feedback) → loop
         └─ Any BLOCK       → ESCALATE to user
```

---

## Evaluator Team

Evaluators are selected from existing specialist agents based on what they assess:

| Evaluator | Assessment Target | Method | Typical Tasks |
|-----------|------------------|--------|---------------|
| Judge | Code quality (static) | Code review, style, patterns | All code changes |
| Voyager | Functional behavior (dynamic) | Playwright E2E, active exploration | UI features |
| Warden | UX quality | V.A.I.R.E. criteria evaluation | UI features |
| Attest | Spec compliance | Acceptance criteria verification | Features, specs |
| Radar | Test coverage & correctness | Test execution, coverage measurement | All code changes |
| Sentinel | Security posture | Static security scan, vulnerability check | Security-sensitive |

**Evaluators operate read-only on the Generator's output.** They do not modify code — they provide structured feedback for the Generator to act on.

---

## Applicability

Not every task needs an Evaluator Loop. Apply based on task type and complexity:

| Task Type | Complexity | Evaluator Loop | Evaluators |
|-----------|-----------|----------------|------------|
| FEATURE (UI) | MEDIUM+ | **YES** | Voyager + Warden + Radar |
| FEATURE (Backend) | MEDIUM+ | **YES** | Judge + Radar + Attest |
| FEATURE (Full-stack) | MEDIUM+ | **YES** | Judge + Voyager + Radar + Attest |
| BUG | SIMPLE | NO | VERIFY suffices |
| BUG | COMPLEX | **YES** | Radar + Attest |
| SECURITY | Any | **YES** | Sentinel + Judge + Radar |
| REFACTOR | SIMPLE | NO | VERIFY suffices |
| REFACTOR | COMPLEX | **YES** | Judge + Radar |
| DOCS | Any | NO | VERIFY suffices |
| OPTIMIZE | MEDIUM+ | **YES** | Radar + Judge |

**Default:** When Evaluator Loop is disabled, Phase 6: VERIFY runs the traditional test-only verification.

---

## Loop Control

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| Max Iterations | 3 | 1-5 | Maximum evaluation-revision cycles |
| Termination: All ACCEPT | — | — | All Evaluators return ACCEPT verdict |
| Termination: Diminishing Returns | — | — | Weighted score improves < 0.2 between iterations |
| Termination: Max Reached | — | — | Max iterations exhausted; best result accepted |

---

## Evaluation Feedback Format

Each Evaluator returns structured feedback via `EVALUATION_FEEDBACK`:

```yaml
EVALUATION_FEEDBACK:
  Evaluator: "[agent name]"
  Contract_Ref: "[sprint contract ID]"
  Iteration: [N]
  Verdict: ACCEPT | REVISE | BLOCK
  Rubric_Scores:
    - dimension: "[dimension name]"
      score: [0-3]
      evidence: "[specific finding with file:line references]"
  Issues:
    - severity: CRITICAL | HIGH | MEDIUM | LOW
      description: "[what's wrong]"
      location: "[file:line or component]"
      suggestion: "[how to fix]"
  Summary: "[1-2 sentence overall assessment]"
```

---

## Feedback Aggregation

Nexus aggregates feedback from all Evaluators:

```
Collect all EVALUATION_FEEDBACK
  ↓
Determine aggregate verdict:
  - Any BLOCK → ESCALATE (present to user with context)
  - All ACCEPT → DELIVER
  - Any REVISE → Compile revision brief
  ↓
If REVISE:
  - Merge all REVISE issues into a single revision brief
  - Prioritize: CRITICAL > HIGH > MEDIUM > LOW
  - Remove duplicates across Evaluators
  - Pass revision brief to Generator for next iteration
```

### Revision Brief Format

```yaml
REVISION_BRIEF:
  Contract_Ref: "[sprint contract ID]"
  Iteration: [N → N+1]
  Issues_To_Address:
    - "[CRITICAL] description (from Evaluator)"
    - "[HIGH] description (from Evaluator)"
  Issues_Deferred:
    - "[LOW] description — deferred, does not block acceptance"
  Evaluator_Verdicts:
    Judge: REVISE | Radar: ACCEPT | Attest: REVISE
```

---

## Orchestration Pattern (Pattern H)

This pattern extends the existing orchestration patterns (A-G):

```
Nexus → Agent(Generator, foreground) → _STEP_COMPLETE
                                          ↓
Nexus → spawn Evaluators (parallel, background):
         Agent(Evaluator-1, bg) + Agent(Evaluator-2, bg) + ...
                                          ↓
         Wait for all Evaluators to complete
                                          ↓
Nexus → Aggregate EVALUATION_FEEDBACK
         ├─ All ACCEPT
         │    → proceed to DELIVER
         ├─ Any REVISE (iteration < max)
         │    → compile REVISION_BRIEF
         │    → Agent(Generator, foreground, with REVISION_BRIEF) → _STEP_COMPLETE
         │    → loop back to Evaluator spawn
         ├─ Any REVISE (iteration >= max)
         │    → accept best result, proceed to DELIVER with quality notes
         └─ Any BLOCK
              → ESCALATE to user (present BLOCK reasons)
              → await user decision: fix manually | override | abort
```

**Use when:** Task qualifies for Evaluator Loop per the applicability table above.

### Evaluator Spawn Template

#### Claude Code

```
Agent(
  name: "[evaluator]-eval-[task-slug]"
  description: "Evaluate [aspect] for [task]"
  run_in_background: true
  mode: bypassPermissions
  model: sonnet
  prompt: |
    あなたは [Evaluator] エージェントです。
    まず ~/.claude/skills/[evaluator]/SKILL.md を読み、その指示に従ってください。

    モード: EVALUATOR (コードを変更せず、評価のみ行ってください)

    Sprint Contract:
    [contract content]

    評価対象: [Generator's output summary and artifacts]

    以下のフォーマットで評価結果を出力してください:
    EVALUATION_FEEDBACK:
      Evaluator: [name]
      Contract_Ref: [contract ID]
      Iteration: [N]
      Verdict: ACCEPT | REVISE | BLOCK
      Rubric_Scores: [...]
      Issues: [...]
      Summary: [...]
)
```

#### Codex CLI

```
# Step 1: Generator executes
generator_id = spawn_agent(
  prompt: |
    あなたは [Generator] エージェントです。
    まず ~/.claude/skills/[generator]/SKILL.md を読み、その指示に従ってください。
    Sprint Contract: [contract content]
    タスク: [task_description]
    完了時、_STEP_COMPLETE フォーマットで結果を出力してください。
)
gen_result = wait_agent(generator_id)

# Step 2: Spawn Evaluators in parallel
eval1_id = spawn_agent(
  prompt: |
    あなたは [Evaluator-1] エージェントです。
    まず ~/.claude/skills/[evaluator-1]/SKILL.md を読み、その指示に従ってください。
    モード: EVALUATOR (コードを変更せず、評価のみ)
    Sprint Contract: [contract content]
    評価対象: {gen_result}
    EVALUATION_FEEDBACK フォーマットで結果を出力してください。
)
eval2_id = spawn_agent(
  prompt: |
    あなたは [Evaluator-2] エージェントです。
    ...同上...
)

# Step 3: Wait for all Evaluators
feedback1 = wait_agent(eval1_id)
feedback2 = wait_agent(eval2_id)

# Step 4: Aggregate → ACCEPT / REVISE / BLOCK
# If REVISE: spawn Generator again with REVISION_BRIEF
# If done: cleanup
close_agent(generator_id)
close_agent(eval1_id)
close_agent(eval2_id)
```
```

---

## Integration with Execution Phases

When Evaluator Loop is active, Phase 6: VERIFY expands:

```
Phase 6: VERIFY
  ├─ Evaluator Loop DISABLED → Traditional verification (tests, build, security scan)
  └─ Evaluator Loop ENABLED
       ↓
     6a: Spawn Evaluators (parallel, background)
     6b: Aggregate EVALUATION_FEEDBACK
     6c: Decision
          ├─ ACCEPT → Phase 7: DELIVER
          ├─ REVISE → Return to Phase 4: EXECUTE (Generator re-executes with feedback)
          └─ BLOCK → ESCALATE
```

The traditional VERIFY checks (tests pass, build OK) are subsumed by the Evaluator team — Radar handles test verification, Sentinel handles security, etc.

---

## Platform Compatibility

| Action | Claude Code | Codex CLI |
|--------|-------------|-----------|
| Spawn Generator (foreground) | `Agent(mode: bypassPermissions)` | `spawn_agent()` → `wait_agent()` |
| Spawn Evaluators (parallel) | `Agent(run_in_background: true)` × N | `spawn_agent()` × N → `wait_agent()` × N |
| Pass feedback to Generator | New `Agent()` with REVISION_BRIEF in prompt | `spawn_agent()` with REVISION_BRIEF |
| Cleanup | Automatic | `close_agent()` per agent |

---

## Anti-Patterns

1. **Self-evaluation** — Never let the Generator assess its own output; always use independent Evaluators
2. **Evaluator overload** — Don't assign more than 4 Evaluators per loop; diminishing returns
3. **Infinite loops** — Always enforce Max Iterations; accept best result when exhausted
4. **Vague feedback** — Evaluators must provide file:line references and actionable suggestions
5. **Evaluator as Generator** — Evaluators must not modify code; they only provide feedback
