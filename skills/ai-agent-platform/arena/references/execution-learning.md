# Execution Learning (CALIBRATE)

## Overview

Arena's learning subsystem for improving execution outcomes through cross-session analysis of paradigm, engine, and mode effectiveness.

**Responsibility separation:**

| Subsystem | Owner | Focus |
|-----------|-------|-------|
| Execution learning | Arena (CALIBRATE) | Engine-task fitness, paradigm selection optimization, mode/parameter tuning |
| Cross-agent knowledge synthesis | Lore | Pattern aggregation across all agents |
| Quality PDCA | Judge | Output quality measurement and improvement cycles |
| Known-pattern auto-remediation | Mend | Automated fixes for recognized failure patterns |

CALIBRATE learns *within* Arena's execution-orchestration domain — which engines excel at which task types, when COMPETE outperforms COLLABORATE, and what team sizes/timeouts yield optimal results. Extracted patterns are shared to Lore for cross-agent synthesis; quality metrics flow to Judge for PDCA integration.

---

## CALIBRATE Workflow

```
COLLECT → EVALUATE → EXTRACT → ADAPT → SAFEGUARD → RECORD
```

| Phase | Purpose | Key Actions |
|-------|---------|-------------|
| COLLECT | Execution result gathering | Capture session completion data: paradigm, mode, engines, variants, scores, cost, timing, user interventions |
| EVALUATE | Effectiveness assessment | Calculate AES, update Engine Proficiency Matrix, compare against historical baseline |
| EXTRACT | Pattern identification | Identify engine × task-type win-rate patterns, paradigm effectiveness conditions, optimal team size |
| ADAPT | Adaptation proposal | Update engine default selection, improve paradigm selection heuristics, adjust Quick Mode eligibility |
| SAFEGUARD | Change verification | Verify consistency with existing evaluation framework, create rollback snapshot |
| RECORD | Learning persistence | Write journal entry, share patterns with Lore, share quality data with Judge |

### Phase Details

#### COLLECT

Capture after every session execution (AT-01):

```yaml
EXECUTION_DATA:
  session_id: <unique session identifier>
  task_type: <feature | bugfix | refactor | optimization | migration>
  paradigm: <COMPETE | COLLABORATE>
  mode: <Quick | Solo | Team>
  engines_used:
    - engine: <codex | gemini>
      model: <model variant if specified>
      role: <variant | subtask>
  variant_count: <int>
  self_competition: <bool>
  self_competition_strategy: <approach_hint | model_variant | prompt_verbosity | null>
  winner:
    engine: <engine name>
    score: <float>
    runner_up_score: <float>
  evaluation_scores:
    - variant: <branch name>
      correctness: <float>
      code_quality: <float>
      performance: <float>
      safety: <float>
      simplicity: <float>
      total: <float>
  cost:
    total_tokens: <int>
    execution_time_seconds: <int>
  user_interventions:
    - type: <paradigm_override | engine_override | mode_override | manual_fix | abort>
      detail: <description>
  final_status: <SUCCESS | PARTIAL | BLOCKED | FAILED>
```

#### EVALUATE

Calculate Arena Effectiveness Score (see AES section below). Compare against:
- Historical average for same task type
- Historical average for same paradigm × mode combination
- Previous session with same engine set (if applicable)

#### EXTRACT

Identify patterns from accumulated data (minimum 3 data points):
- **Engine-task fitness**: Which engines consistently win for which task types
- **Paradigm effectiveness**: Conditions where COMPETE outperforms COLLABORATE and vice versa
- **Mode optimization**: Team size, timeout, and Quick Mode eligibility patterns
- **Self-competition insights**: When single-engine competition is sufficient vs. cross-engine

#### ADAPT

Generate concrete adaptation proposals:
- Engine default selection updates (e.g., "default to codex for bugfix tasks")
- Paradigm selection heuristic improvements (e.g., "prefer COLLABORATE for migration tasks with 5+ files")
- Quick Mode eligibility criteria adjustments (e.g., "tighten to ≤ 2 files based on escalation rate")
- Team Mode recommendations (e.g., "recommend Team Mode for refactor tasks based on score gap data")

Each proposal must include: rationale, expected AES impact, rollback plan.

#### SAFEGUARD

Before applying any adaptation:
1. Verify existing evaluation framework is preserved (Correctness 40% / Quality 25% / Perf 15% / Safety 15% / Simplicity 5%) — **invariant, never modify**
2. Check proposal against established paradigm/mode rules — reject if contradiction
3. Create snapshot of current defaults and heuristic state
4. Verify minimum evidence threshold (≥ 3 data points)
5. For AES ≥ B configurations: require human approval (do not auto-adapt)
6. Ensure change volume stays within session limit (max 3 parameter changes)

#### RECORD

Record learning outcomes:
1. Write feedback record to `.agents/arena.md`
2. Share extracted patterns to Lore via `ARENA_TO_LORE_HANDOFF`
3. Share quality metrics to Judge via quality data channel
4. Update Engine Proficiency Matrix if sufficient data accumulated

---

## Learning Triggers

| ID | Condition | Scope | Actions |
|----|-----------|-------|---------|
| AT-01 | Session execution complete (every time) | Lightweight | COLLECT + EVALUATE only |
| AT-02 | Same engine + task type fails or scores low 3+ times | Full cycle | All 6 CALIBRATE phases |
| AT-03 | User manually overrides paradigm or engine selection | Full cycle | All 6 CALIBRATE phases |
| AT-04 | Quality feedback arrives from Judge | Medium | COLLECT + EVALUATE + EXTRACT + RECORD |
| AT-05 | Lore sends execution-related pattern notification | Medium | COLLECT + EVALUATE + EXTRACT + RECORD |
| AT-06 | 30+ days since last full CALIBRATE cycle | Full cycle | All 6 CALIBRATE phases |

### Trigger Priority

When multiple triggers fire simultaneously:
1. AT-03 (user override — highest signal value)
2. AT-02 (repeated failures — urgent)
3. AT-04 (quality feedback — actionable)
4. AT-05 (Lore pattern — opportunity)
5. AT-06 (scheduled review — lowest urgency)
6. AT-01 (routine collection — always runs)

---

## Arena Effectiveness Score (AES)

```
AES = Win_Clarity × 0.30
    + Engine_Fitness × 0.25
    + Cost_Efficiency × 0.20
    + Paradigm_Fitness × 0.15
    + User_Autonomy × 0.10
```

### Components

| Component | Weight | Definition | Range |
|-----------|--------|------------|-------|
| Win_Clarity | 0.30 | Winner score gap over runner-up (normalized). Higher gap = clearer winner | 0.0–1.0 |
| Engine_Fitness | 0.25 | Engine-task type match rate based on Engine Proficiency Matrix | 0.0–1.0 |
| Cost_Efficiency | 0.20 | Quality per token/time unit: `total_score / normalized_cost` (capped at 1.0) | 0.0–1.0 |
| Paradigm_Fitness | 0.15 | Post-hoc assessment: would the other paradigm have been better? 1.0 = correct choice | 0.0–1.0 |
| User_Autonomy | 0.10 | `1 - (user_overrides / total_decisions)` — fewer interventions is better | 0.0–1.0 |

### Grading Scale

| Grade | AES Range | Interpretation |
|-------|-----------|----------------|
| A | ≥ 0.90 | Excellent — configuration is well-optimized |
| B | ≥ 0.80 | Good — no auto-changes permitted (human approval required) |
| C | ≥ 0.70 | Acceptable — adaptation candidates |
| D | ≥ 0.60 | Below standard — systematic review recommended |
| F | < 0.60 | Poor — full CALIBRATE cycle required |

### Data Requirements

- AES calculation requires ≥ 3 data points for the same task-type/paradigm combination
- Grades are provisional until ≥ 5 data points
- Trend analysis requires ≥ 10 data points
- Below minimum threshold, AES is reported as `INSUFFICIENT_DATA`

---

## Engine Proficiency Matrix

Track cumulative engine effectiveness by task type. Each cell represents a grade derived from historical win rates and scores.

```
             | feature | bugfix | refactor | optimization | migration |
codex        |    —    |   —    |    —     |      —       |     —     |
gemini       |    —    |   —    |    —     |      —       |     —     |
```

`—` = `INSUFFICIENT_DATA` (fewer than 3 data points). Default grade is B until sufficient data.

### Update Rules

1. After each session (AT-01), record engine × task-type outcome
2. When a cell reaches ≥ 3 data points, calculate grade from win rate and average score
3. Grade calculation: `win_rate × 0.60 + avg_normalized_score × 0.40`
4. Apply same A/B/C/D/F grading scale as AES
5. Matrix informs Engine_Fitness component of AES calculation

### Usage in Execution

- When selecting engines for a task, consult the matrix for task-type column
- Prefer engines with higher grades for the given task type
- If all engines show `INSUFFICIENT_DATA`, use default selection heuristics (codex for speed/algorithms, gemini for creativity/broad context)

---

## Adaptation Rules

### Allowed Scope by Grade

| Current AES Grade | Allowed Adaptations | Approval |
|-------------------|---------------------|----------|
| A (≥ 0.90) | No auto-changes — human approval required for any modification | Human required |
| B (≥ 0.80) | No auto-changes — human approval required | Human required |
| C (≥ 0.70) | Engine default preference adjustments, Quick Mode criteria tuning | Auto with snapshot |
| D (≥ 0.60) | Engine defaults + paradigm heuristic adjustments + mode recommendations | Auto with snapshot |
| F (< 0.60) | Full review — engine, paradigm, mode, and parameter reassessment | Auto with snapshot |

### Adaptation Types

| Type | Example | Max per Session |
|------|---------|-----------------|
| Engine default preference | Prefer codex for bugfix tasks (win rate 80%+) | 2 |
| Paradigm selection heuristic | Prefer COLLABORATE for migration tasks with 5+ files | 1 |
| Quick Mode eligibility | Tighten to ≤ 2 files based on escalation rate > 30% | 1 |
| Team Mode recommendation | Recommend Team Mode for refactor tasks (score gap > Solo) | 1 |
| Self-competition strategy | Default to approach_hint for optimization tasks | 1 |

**Total maximum: 3 parameter default changes per session.**

### Application Process

1. **Propose**: Generate adaptation with rationale and expected AES impact
2. **Validate**: Run SAFEGUARD checks (evaluation framework invariant, evidence threshold, grade ceiling)
3. **Snapshot**: Save current configuration state for rollback
4. **Apply**: Implement the adaptation
5. **Monitor**: Track AES for next 3 executions to verify improvement

---

## Safety Guardrails

| Mechanism | Rule | Rationale |
|-----------|------|-----------|
| Change volume limit | Maximum 3 parameter default changes per session | Prevent cascading unintended effects |
| Auto-adaptation ceiling | AES ≥ B configurations require human approval | Protect well-performing configurations |
| Rollback snapshot | Save configuration state before every adaptation | Enable instant rollback on regression |
| Diminishing returns detection | 3 consecutive AES improvements < 0.02 → pause CALIBRATE | Avoid churn on marginal gains |
| Lore sync mandatory | All extracted patterns must be shared to Lore | Prevent knowledge silos |
| Minimum evidence | No adaptation with < 3 execution data points | Prevent overfitting to outliers |
| Evaluation framework invariant | Never modify existing 5-criteria scoring (Correctness 40% / Quality 25% / Perf 15% / Safety 15% / Simplicity 5%) | Preserve established evaluation integrity |

### Rollback Protocol

1. Detect regression: AES drops ≥ 0.10 after adaptation (monitored over next 3 executions)
2. Load pre-adaptation snapshot
3. Restore previous defaults and heuristic state
4. Record rollback event in journal with root cause analysis
5. Share rollback event to Lore as negative pattern

---

## Integration Points

| Partner | Direction | Data Exchanged |
|---------|-----------|----------------|
| Lore | Arena → Lore | Engine proficiency data, paradigm effectiveness patterns, AES trends |
| Lore | Lore → Arena | Cross-agent execution patterns, validated best practices |
| Judge | Arena → Judge | Execution quality data (AES scores, engine comparison results) |
| Judge | Judge → Arena | Quality feedback, code review assessments (AT-04) |
| Nexus | Arena → Nexus | Execution reports, paradigm effectiveness data |
| Guardian | Arena → Guardian | PR preparation, merge candidates |
| Radar | Arena → Radar | Test verification requests |
| Sentinel | Arena → Sentinel | Security review requests for winning variants |

### Lore Sync Protocol

**Arena → Lore (pattern share):**

```yaml
ARENA_TO_LORE_PATTERN:
  type: EXECUTION_LEARNING_PATTERN
  pattern_name: <descriptive name>
  source_data:
    task_type: <task type>
    paradigm: <paradigm>
    engines: <engine list>
    sample_size: <int>
    aes_impact: <float>
  pattern_detail: <description>
  confidence: <HIGH | MEDIUM | LOW>
  actionable: <bool>
```

**Lore → Arena (pattern notification):**

```yaml
LORE_TO_ARENA_PATTERN:
  type: EXECUTION_PATTERN_UPDATE
  pattern_name: <descriptive name>
  source_agents: <list of contributing agents>
  recommendation: <action to consider>
  priority: <HIGH | MEDIUM | LOW>
```

---

## Templates

### Session Feedback Record

```markdown
## Session Feedback — <session_id>

**Date:** YYYY-MM-DD
**Task Type:** <feature | bugfix | refactor | optimization | migration>
**Paradigm:** <COMPETE | COLLABORATE> | **Mode:** <Quick | Solo | Team>
**Engines:** <engine list> | **Variants:** <count>
**Final Status:** <SUCCESS | PARTIAL | BLOCKED | FAILED>
**AES:** <score> (Grade: <A-F>) | **Previous AES:** <score> (Grade: <A-F>)

### Winner
- **Engine:** <engine> | **Score:** <total> | **Runner-up Score:** <total>
- **Score Gap:** <delta>

### Component Scores
| Component | Score | Note |
|-----------|-------|------|
| Win_Clarity | <0.00-1.00> | |
| Engine_Fitness | <0.00-1.00> | |
| Cost_Efficiency | <0.00-1.00> | |
| Paradigm_Fitness | <0.00-1.00> | |
| User_Autonomy | <0.00-1.00> | |

### User Interventions
- <intervention or "None">

### Observations
- <key observation 1>
- <key observation 2>
```

### Engine Profile Update

```markdown
## Engine Profile Update — <date>

**Engine:** <engine name>
**Task Type:** <task type>
**Previous Grade:** <grade or INSUFFICIENT_DATA>
**New Grade:** <grade>
**Data Points:** <count>

### Evidence
- Win rate: <percentage> over <count> sessions
- Average score: <float>
- Notable strengths: <list>
- Notable weaknesses: <list>
```

### Adaptation Log

```markdown
## Adaptation Log — <date>

**Trigger:** <AT-xx>
**Current AES:** <score> (Grade: <grade>)
**Target AES:** <expected score>

### Change
- **Type:** <adaptation type>
- **Detail:** <specific change>
- **Rationale:** <why this change>

### Safeguard Check
- Evaluation framework invariant: PASS / FAIL
- Evidence threshold (≥ 3): PASS / FAIL
- Grade ceiling check: PASS / FAIL
- Snapshot saved: <snapshot identifier>

### Outcome (post-monitoring)
- AES after 3 executions: <score>
- Rollback needed: YES / NO
```
