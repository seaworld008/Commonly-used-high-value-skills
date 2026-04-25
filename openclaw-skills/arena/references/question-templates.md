# Question Templates

YAML templates for Arena's `AskUserQuestion` interaction triggers. Each template maps to one `INTERACTION_TRIGGERS` entry in SKILL.md.

---

## ON_PARADIGM_SELECTION

```yaml
questions:
  - question: "Which paradigm should Arena use for this task?"
    header: "Paradigm"
    options:
      - label: "COMPETE (Recommended)"
        description: "Same spec to multiple engines, compare and select the best variant"
      - label: "COLLABORATE"
        description: "Split task into subtasks, assign each to the best engine, integrate all results"
    multiSelect: false
```

## ON_MODE_SELECTION

```yaml
questions:
  - question: "Which execution mode should Arena use?"
    header: "Mode"
    options:
      - label: "Quick Mode (Recommended for small tasks)"
        description: "Streamlined 4-phase workflow, 2 variants, minimal overhead. COMPETE only. Eligible when ≤ 3 files, ≤ 2 criteria, ≤ 50 lines"
      - label: "Solo Mode"
        description: "Sequential execution, 2 variants/subtasks, standard workflow"
      - label: "Team Mode"
        description: "Parallel execution via Agent Teams, 3+ variants/subtasks, higher cost"
    multiSelect: false
```

## ON_ENGINE_SELECTION

```yaml
questions:
  - question: "Which AI engine(s) should be used?"
    header: "Engines"
    options:
      - label: "codex + gemini (Recommended)"
        description: "Compare both engines for best result"
      - label: "codex only"
        description: "Fast iteration, algorithmic tasks"
      - label: "gemini only"
        description: "Creative approaches, broad context"
    multiSelect: true
```

## ON_VARIANT_COUNT

```yaml
questions:
  - question: "How many implementation variants should be generated?"
    header: "Variants"
    options:
      - label: "2 variants (Recommended)"
        description: "Good balance of comparison and cost"
      - label: "3 variants"
        description: "More options, moderate cost increase"
      - label: "4+ variants"
        description: "Maximum exploration, higher cost"
    multiSelect: false
```

## ON_VARIANT_SELECTION

```yaml
questions:
  - question: "Which variant should be adopted?"
    header: "Selection"
    options:
      - label: "Variant A (Recommended)"
        description: "[Summary of Variant A strengths]"
      - label: "Variant B"
        description: "[Summary of Variant B strengths]"
      - label: "Hybrid approach"
        description: "Manually combine best parts of multiple variants"
    multiSelect: false
```

## ON_COST_THRESHOLD

Auto-trigger: shown automatically when variant_count ≥ 3 OR Team Mode is selected.

```yaml
questions:
  - question: "Cost estimate for this Arena session. How should we proceed?"
    header: "Cost"
    options:
      - label: "Proceed as planned (Recommended)"
        description: "{mode}, {variant_count} variants, {engines} — estimated {cost_level}"
      - label: "Reduce to 2 variants"
        description: "Minimize cost with standard 2-variant comparison"
      - label: "Switch to Quick Mode"
        description: "Lightweight comparison if task is eligible (≤ 3 files, ≤ 50 lines)"
      - label: "Single engine only"
        description: "Use only one engine to halve cost"
    multiSelect: false
```

## ON_ALL_DISQUALIFIED

Auto-trigger: shown automatically when all variants fail the REVIEW quality gate.

```yaml
questions:
  - question: "All variants were disqualified during REVIEW. How should Arena proceed?"
    header: "Recovery"
    options:
      - label: "Refine spec and re-run (Recommended)"
        description: "Analyze failure causes, improve the specification, and generate new variants"
      - label: "Fall back to Builder"
        description: "Hand off the task to Builder for direct implementation by Claude Code"
      - label: "Abort"
        description: "Stop the Arena session and return control to user"
    multiSelect: false
```
