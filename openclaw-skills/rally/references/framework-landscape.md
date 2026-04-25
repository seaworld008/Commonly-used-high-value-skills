# Multi-Agent Framework Landscape (2025-2026)

> Purpose: Read this when comparing Rally to other frameworks or deciding whether Rally is the correct execution layer.

## Table of Contents

1. Comparison Matrix
2. Rally Fit
3. Cross-Framework Best Practices
4. Selection Tree

## Comparison Matrix

| Framework | Core style | State management | Parallel support | HITL style | Best fit |
|-----------|------------|------------------|------------------|------------|----------|
| LangGraph | graph-based workflows | graph state | fan-out and fan-in | interrupts | complex conditional workflows |
| CrewAI | role-based crews | task chains | sequential or hierarchical | limited | role-driven collaboration |
| AutoGen or AG2 | conversation-driven | conversation state | group chat | human proxy patterns | experimentation and research |
| Google ADK | workflow plus LLM agents | session state | `ParallelAgent` | built-in | Google Cloud ecosystems |
| OpenAI Agents SDK | handoff-driven | conversation and session | limited built-in support | guardrails | OpenAI-native apps |
| Claude Agent Teams | lead + teammates | `TaskList + SendMessage` | `TeamCreate + Task` | `plan` plus approval | Rally's execution layer |

## Rally Fit

### Rally strengths

| Area | Rally advantage |
|------|-----------------|
| Execution environment | native inside Claude Code CLI |
| Writable coordination | `exclusive_write` and `shared_read` discipline |
| Structured communication | `TaskList` and `SendMessage` |
| Lifecycle | `TeamCreate -> TeamDelete` supervision |
| Learning | HARMONIZE and TES |

### Use Rally when

1. work happens inside the Claude Code ecosystem
2. file ownership matters
3. existing skill agents such as Builder, Artisan, or Radar should work as teammates
4. structured task orchestration is required

### Prefer another framework when

| Need | Better fit |
|------|------------|
| rich conditional control flow | LangGraph |
| role-centric business collaboration | CrewAI |
| research-grade multi-agent experimentation | AutoGen or AG2 |
| Google Cloud alignment | Google ADK |
| OpenAI-native application runtime | OpenAI Agents SDK |

## Cross-Framework Best Practices

1. Start with a single agent, then justify more orchestration.
2. Begin small; `3-5` agents is a reasonable upper starting point.
3. Separate roles clearly.
4. Pass only the minimum necessary context.
5. Design human checkpoints for high-risk actions.

### Human-in-the-Loop Patterns

| Pattern | Rally implementation |
|---------|----------------------|
| pre-approval | `plan` mode |
| escalation on uncertainty | `Ask first` rules |
| audit after execution | `SYNTHESIZE` |
| staged autonomy | `default` -> `bypassPermissions` |

## Selection Tree

```text
What execution environment are you in?
├─ Claude Code CLI -> Rally
├─ Python application
│  ├─ complex control flow -> LangGraph
│  ├─ role-based collaboration -> CrewAI
│  └─ research or experimentation -> AutoGen or AG2
├─ Google Cloud -> Google ADK
└─ OpenAI API -> OpenAI Agents SDK
```
