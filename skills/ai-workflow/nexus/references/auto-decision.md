# Nexus Auto-Decision Reference

**Purpose:** Confidence thresholds for acting without user confirmation.
**Read when:** You need to decide whether Nexus should act autonomously or ask.

## Contents
- Overview
- Decision Thresholds
- Auto-Proceed Conditions
- Decision Types
- Decision Flow
- Reversibility Assessment
- Assumption Documentation
- Confidence Degradation
- Safety Overrides
- Mode-Specific Behavior
- Metrics and Learning
- Integration with Other Systems

Confidence-based autonomous decision-making for reduced user interaction.

---

## Overview

Auto-Decision enables Nexus to proceed autonomously when confidence levels meet thresholds. This reduces unnecessary user interactions while maintaining safety through guardrails.

---

## Decision Thresholds

| Decision Type | Threshold | Rationale |
|---------------|-----------|-----------|
| Chain Selection | >= 0.85 | High bar - wrong chain wastes significant effort |
| Approach Selection | >= 0.80 | Medium bar - approaches are usually recoverable |
| Recovery Action | >= 0.75 | Lower bar - recovery is inherently corrective |
| Agent Routing | >= 0.80 | Medium bar - misrouting causes delays |
| Parallel vs Sequential | >= 0.70 | Lower bar - both are valid, just different efficiency |

### Decision by Confidence Level (cross-model)

When numeric thresholds are difficult to calculate, map directly from confidence levels (see `context-scoring.md` Simplified Scoring):

| Decision Type | Minimum Level | Rationale |
|---------------|--------------|-----------|
| Chain Selection | HIGH | Wrong chain wastes significant effort |
| Approach Selection | MEDIUM+ | Approaches are usually recoverable |
| Recovery Action | MEDIUM | Recovery is inherently corrective |
| Agent Routing | MEDIUM+ | Misrouting causes delays |
| Parallel vs Sequential | MEDIUM | Both are valid, just different efficiency |

`MEDIUM+` = MEDIUM with no blocking open questions. If open questions exist, treat as LOW.

---

## Auto-Proceed Conditions

```yaml
AUTO_PROCEED_IF:
  all_required:
    - confidence >= threshold_for_decision_type
    - no_l4_security_implications
    - action_is_reversible

  any_blocking:
    - l4_security_trigger  # Always requires user
    - data_destructive_action  # Deletions, migrations
    - external_system_modification  # APIs, deployments
    - cost_incurring_action  # Cloud resources, payments
```

---

## Decision Types

### 1. Chain Selection

```yaml
chain_selection:
  threshold: 0.85
  auto_proceed_when:
    - Single best-fit chain identified
    - Context clearly indicates task type
    - No conflicting signals

  ask_when:
    - Multiple equally valid chains
    - Task type ambiguous
    - User has preference history we're unsure about

  output:
    auto: "Selecting [Chain] based on: [reasons]"
    ask: "[Present options with ON_CHAIN_DESIGN trigger]"
```

### 2. Approach Selection

```yaml
approach_selection:
  threshold: 0.80
  auto_proceed_when:
    - Clear best approach exists
    - Approach matches project patterns
    - Low risk if wrong

  ask_when:
    - Trade-offs are significant
    - User preference unknown
    - Approaches have different outcomes

  output:
    auto: "Using [approach] because: [reason]"
    ask: "[Present ON_MULTI_CANDIDATE_MODE]"
```

### 3. Recovery Action

```yaml
recovery_action:
  threshold: 0.75
  auto_proceed_when:
    - Clear recovery path exists
    - Previous similar recovery succeeded
    - Rollback is available

  ask_when:
    - Multiple recovery options
    - Recovery might lose work
    - Previous recovery failed

  output:
    auto: "Recovering via [action]: [reason]"
    ask: "[Present recovery options]"
```

### 4. Agent Routing

```yaml
agent_routing:
  threshold: 0.80
  auto_proceed_when:
    - Clear agent-task match
    - Agent available and capable
    - No specialist override needed

  ask_when:
    - Multiple specialists could help
    - Agent capabilities overlap
    - Task spans multiple domains

  output:
    auto: "Routing to [Agent]: [reason]"
    ask: "[Present ON_MULTI_AGENT_CHOICE]"
```

---

## Decision Flow

```
Input (task/decision needed)
         │
         ▼
┌─────────────────────────┐
│   Calculate Confidence  │ ← See context-scoring.md
└───────────┬─────────────┘
            │
    ┌───────┴───────┐
    ▼               ▼
 >= threshold    < threshold
    │               │
    ▼               ▼
┌─────────┐   ┌─────────────┐
│ Check   │   │ Prepare     │
│ Blockers│   │ Question    │
└────┬────┘   └──────┬──────┘
     │               │
  ┌──┴──┐            ▼
  ▼     ▼        Ask User
 OK  Blocked        │
  │     │           ▼
  ▼     ▼       Integrate
Auto   Ask       Answer
Proceed User        │
  │     │           │
  └──┬──┴───────────┘
     ▼
  Execute Decision
```

---

## Reversibility Assessment

Actions are categorized by reversibility:

| Category | Examples | Auto-Proceed |
|----------|----------|--------------|
| Fully Reversible | Code changes (git), test runs | Yes |
| Easily Reversible | Config changes, refactoring | Yes |
| Moderately Reversible | Database migrations (with rollback) | With caution |
| Difficult to Reverse | Data deletion, external API calls | No |
| Irreversible | Production deployments, payments | Never auto |

```yaml
reversibility_check:
  fully_reversible:
    - file_modifications  # git reset
    - branch_operations   # git checkout
    - test_execution      # no side effects
    - lint_fixes          # auto-fixable

  requires_confirmation:
    - database_changes
    - external_service_calls
    - deployment_actions
    - user_data_modifications
```

---

## Assumption Documentation

When auto-proceeding, always document assumptions:

```yaml
_AUTO_DECISION:
  decision_type: [chain_selection|approach|recovery|routing]
  confidence: 0.XX
  threshold: 0.XX

  decision: "[What was decided]"

  assumptions:
    - "[Assumption 1]"
    - "[Assumption 2]"

  signals_used:
    - "[Signal that supported this decision]"
    - "[Another signal]"

  reversibility: [fully|easily|moderate]
  rollback_plan: "[How to undo if wrong]"
```

---

## Confidence Degradation

Confidence decreases in certain conditions:

```yaml
degradation_triggers:
  - consecutive_errors: -0.10 per error
  - user_correction: -0.15 for this session
  - unexpected_state: -0.10
  - missing_expected_file: -0.05

recovery:
  - successful_execution: +0.05
  - user_confirmation: restore to baseline
  - explicit_approval: +0.10 for similar decisions
```

---

## Safety Overrides

These conditions ALWAYS require user confirmation regardless of confidence:

```yaml
ALWAYS_ASK:
  security:
    - credential_changes
    - authentication_modifications
    - permission_changes
    - encryption_key_operations

  data:
    - bulk_data_deletion
    - schema_breaking_changes
    - user_data_export

  external:
    - production_deployment
    - external_api_key_usage
    - payment_operations
    - third_party_integrations

  scope:
    - changes_affecting_10plus_files
    - architectural_changes
    - breaking_api_changes
```

---

## Mode-Specific Behavior

| Mode | Auto-Decision Behavior |
|------|------------------------|
| AUTORUN_FULL | Full auto-decision with guardrails |
| AUTORUN | Auto-decision for SIMPLE, ask for COMPLEX |
| GUIDED | Auto-decision with confirmation at triggers |
| INTERACTIVE | No auto-decision, ask everything |

---

## Metrics and Learning

Track auto-decision performance:

```yaml
metrics:
  auto_decision_count: N
  accuracy_rate: X%  # Decisions that didn't need correction

  by_type:
    chain_selection: {count: N, accuracy: X%}
    approach: {count: N, accuracy: X%}
    recovery: {count: N, accuracy: X%}
    routing: {count: N, accuracy: X%}

learning:
  on_correction:
    - Record the gap
    - Adjust threshold for this pattern (+0.05)
    - Add to learned patterns in .agents/nexus.md
```

---

## Integration with Other Systems

### With Context Scoring

```
Context Scoring → confidence score
                      │
                      ▼
Auto-Decision → threshold check → proceed/ask
```

### With Guardrails

```
Auto-Decision → proceed
                   │
                   ▼
Guardrails → monitor execution
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
    L1-L2: continue      L3-L4: escalate
```

### With Handoff Validation

```
Agent completes → Handoff with confidence
                          │
                          ▼
Auto-Decision → route to next agent
           OR → ask user about findings
```
