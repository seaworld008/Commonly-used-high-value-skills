# Nexus Context Scoring Reference

**Purpose:** Confidence-scoring model for task understanding and routing.
**Read when:** You need weighted context analysis before deciding or asking.

## Contents
- Overview
- Scoring Sources
- Source Analysis Details
- Confidence Thresholds
- Integration with Auto-Decision
- Scoring Calculation
- Context Snapshot Format
- Boosting and Penalties
- Usage in Execution Phases
- Low-Confidence Intent Clarification
- Learning Loop

Context analysis and confidence scoring for autonomous decision-making.

---

## Overview

Context Scoring enables Nexus to make autonomous decisions by analyzing multiple information sources and calculating confidence levels. High-confidence decisions proceed automatically; low-confidence triggers clarification flows.

---

## Scoring Sources

| Source | Weight | Description |
|--------|--------|-------------|
| `git_history` | 0.30 | Recent commits, branches, changes in progress |
| `project_md` | 0.25 | `.agents/PROJECT.md` activity log, shared knowledge |
| `conversation` | 0.25 | Current session context, user messages |
| `codebase` | 0.20 | File structure, existing patterns, dependencies |

---

## Source Analysis Details

### git_history (weight: 0.30)

```yaml
git_analysis:
  signals:
    - current_branch: Indicates active work area
    - recent_commits: Shows development direction
    - uncommitted_changes: Highlights work in progress
    - branch_name_pattern: Often reveals intent (fix/, feat/, etc.)

  scoring:
    branch_matches_task: +0.15
    recent_commits_related: +0.10
    uncommitted_changes_relevant: +0.05
    no_relevant_history: +0.00
```

### project_md (weight: 0.25)

```yaml
project_analysis:
  signals:
    - activity_log: Recent agent actions and outcomes
    - shared_knowledge: Accumulated learnings
    - known_issues: Previously identified problems

  scoring:
    activity_matches_task: +0.15
    shared_knowledge_relevant: +0.07
    no_project_context: +0.00
```

### conversation (weight: 0.25)

```yaml
conversation_analysis:
  signals:
    - explicit_requirements: User-stated goals
    - implicit_intent: Tone, patterns, history
    - previous_corrections: Learned preferences

  scoring:
    clear_explicit_intent: +0.20
    inferable_implicit_intent: +0.10
    ambiguous_intent: +0.00
```

### codebase (weight: 0.20)

```yaml
codebase_analysis:
  signals:
    - file_patterns: Existing architecture
    - similar_implementations: Precedent code
    - dependency_graph: Impact scope

  scoring:
    clear_pattern_to_follow: +0.15
    partial_patterns: +0.08
    no_relevant_patterns: +0.00
```

---

## Confidence Thresholds

| Level | Score Range | Action |
|-------|-------------|--------|
| HIGH | >= 0.80 | Auto-proceed without confirmation |
| MEDIUM | 0.60 - 0.79 | Proceed with stated assumptions |
| LOW | 0.40 - 0.59 | Single clarification question |
| VERY_LOW | < 0.40 | Multi-step clarification required |

---

## Integration with Auto-Decision

```yaml
context_to_decision:
  high_confidence:
    action: AUTO_PROCEED
    log: "Proceeding based on context: [summary]"
    assumptions: "[list stated assumptions]"

  medium_confidence:
    action: PROCEED_WITH_ASSUMPTIONS
    log: "Proceeding with assumptions: [list]"
    notify_user: true  # Post-execution notification

  low_confidence:
    action: SINGLE_CLARIFICATION
    question_format: focused_choice
    max_options: 4

  very_low_confidence:
    action: STRUCTURED_CLARIFICATION
    method: intent_clarification  # See references/intent-clarification.md
```

---

## Scoring Calculation

```
Final Score = Σ (source_score × source_weight)

Where:
  git_score × 0.30 +
  project_score × 0.25 +
  conversation_score × 0.25 +
  codebase_score × 0.20
  = final_confidence (0.00 - 1.00)
```

### Simplified Scoring (cross-model)

When weighted calculation is difficult, use qualitative classification instead:

| Source | HIGH (3) | MEDIUM (2) | LOW (1) | NONE (0) |
|--------|----------|------------|---------|----------|
| `git_history` | Branch + commits match task | Some related commits | Repo exists, no match | No git info |
| `project_md` | Activity directly matches | Related activity found | File exists, no match | No file |
| `conversation` | Explicit clear request | Inferable intent | Vague request | No context |
| `codebase` | Clear pattern to follow | Partial patterns exist | Files exist, no pattern | No codebase |

| Total Points (max 12) | Confidence Level | Action |
|------------------------|-----------------|--------|
| 10-12 | HIGH | AUTO_PROCEED |
| 7-9 | MEDIUM | PROCEED_WITH_ASSUMPTIONS |
| 4-6 | LOW | SINGLE_CLARIFICATION |
| 0-3 | VERY_LOW | STRUCTURED_CLARIFICATION |

### Example Calculation

```yaml
example:
  task: "Fix the login issue"

  analysis:
    git_history:
      branch: "fix/auth-timeout"
      recent_commits: ["fix: extend session", "debug: add logging"]
      score: 0.28  # Strong signal (0.15 + 0.10 + 0.03)

    project_md:
      activity: "Scout investigated auth module yesterday"
      score: 0.18  # Good context (0.15 + 0.03)

    conversation:
      explicit: "login doesn't work"
      implicit: User frustrated (based on "STILL")
      score: 0.12  # Moderate clarity

    codebase:
      patterns: auth/* files exist
      score: 0.12  # Clear area to work in

  final_score: 0.28 + 0.18 + 0.12 + 0.12 = 0.70
  level: MEDIUM
  action: PROCEED_WITH_ASSUMPTIONS
```

---

## Context Snapshot Format

```yaml
_CONTEXT_SNAPSHOT:
  timestamp: [ISO timestamp]
  task: [Original request]

  scores:
    git_history: 0.XX
    project_md: 0.XX
    conversation: 0.XX
    codebase: 0.XX
    final: 0.XX

  confidence_level: [HIGH|MEDIUM|LOW|VERY_LOW]

  signals:
    git:
      - "[Key signal 1]"
      - "[Key signal 2]"
    project:
      - "[Key signal]"
    conversation:
      - "[Key signal]"
    codebase:
      - "[Key signal]"

  assumptions:
    - "[Assumption 1]"
    - "[Assumption 2]"

  recommended_action: [AUTO_PROCEED|PROCEED_WITH_ASSUMPTIONS|CLARIFY]
```

---

## Boosting and Penalties

### Confidence Boosters

| Signal | Boost |
|--------|-------|
| User confirmed similar task before | +0.10 |
| Single valid interpretation | +0.10 |
| Existing tests for target area | +0.05 |
| Small scope (< 3 files) | +0.05 |

### Confidence Penalties

| Signal | Penalty |
|--------|---------|
| Multiple valid interpretations | -0.15 |
| No git history for area | -0.10 |
| User previously corrected similar | -0.10 |
| Large scope (> 10 files) | -0.05 |
| Security-sensitive area | -0.05 |

---

## Usage in Execution Phases

### Phase 1: PLAN

```
1. Gather context from all sources
2. Calculate confidence score
3. Determine action based on threshold
4. If HIGH/MEDIUM: proceed to CHAIN_SELECT
5. If LOW/VERY_LOW: clarify first
```

### During CHAIN_SELECT

```
1. Use context signals to inform chain selection
2. If multiple valid chains and confidence >= 0.80:
   → Select highest-fit chain automatically
3. If multiple valid chains and confidence < 0.80:
   → Present options to user
```

### During EXECUTE

```
1. Pass context snapshot to agents
2. Agents use assumptions for decisions
3. If new information contradicts assumptions:
   → Re-score and potentially pause
```

---

## Low-Confidence Intent Clarification

When confidence is LOW or VERY_LOW, Nexus uses its internal intent clarification capability. See `references/intent-clarification.md` for the full methodology.

```
Nexus (low confidence)
    │
    ▼
┌──────────────────────────┐
│  Nexus Internal Process  │
│  (Intent Clarification)  │
│  - Analyze context gaps  │
│  - Resolve ambiguity     │
│  - Single Q if needed    │
└───────────┬──────────────┘
            │
            ▼
    Clarified Intent
            │
            ▼
    Nexus (re-score)
```

Intent clarification feeds back into Context Scoring:
- Clarified intent → +0.20 to conversation score
- Resolved assumptions → removes penalties
- User correction → recorded for future scoring

---

## Learning Loop

Context scoring improves over time:

```yaml
learning:
  on_success:
    - Record what signals led to correct decision
    - Boost similar patterns in future

  on_correction:
    - Record the gap between assumption and reality
    - Add to .agents/nexus.md as learned pattern
    - Adjust scoring weights for this task type
```
