Purpose: Use this file when you are choosing agent architecture, MCP design, structured-output strategy, or multi-agent boundaries.

## Contents
- Agent patterns
- Reliability principles
- MCP rules
- Tool and schema design
- Caching and multi-agent rules
- Oracle gates

# LLM Application Patterns

## Agent Architecture Patterns

| ID | Pattern | Best for | Main risk |
|----|---------|----------|-----------|
| `AP-01` | ReAct | dynamic reasoning with tool use | loops and drift |
| `AP-02` | Plan-and-Execute | long, auditable multi-step tasks | rigid plans |
| `AP-03` | Specialized Multi-Agent | composite domains | handoff failure |
| `AP-04` | Router | diverse input types | misclassification |
| `AP-05` | Supervisor | coordinated child agents | bottlenecks |

Default:
- use Plan-and-Execute for predictable multi-step work;
- use ReAct only for dynamic sub-tasks;
- use agents when branching is dynamic, and fixed workflows when the path is predictable.

## Reliability Principles

| Principle | Required behavior |
|-----------|-------------------|
| Structured outputs | JSON schema on all machine-read outputs |
| Validation at every step | pass/fail gate per stage |
| Immutable audit trail | log tool calls and rationale |
| Least privilege | read-only default, minimal tool scope |
| Cost and latency caps | circuit breakers and budget ceilings |

### Failure Modes

| Failure | Detection | Mitigation |
|---------|-----------|------------|
| Format drift | schema validation | structured outputs |
| Plan divergence | step monitoring | bounded reasoning loop |
| Ambiguity loops | loop count | explicit tool-choice schema |
| Silent errors | quality sampling | embedded validation |
| Tool abuse | audit log | usage policy and permissions |
| Cost explosion | spend monitoring | cost ceiling and breaker |
| State corruption | snapshot diff | explicit state handling |

## MCP Design

### Core Primitives

- Tools: actions
- Resources: read-only structured context
- Prompts: reusable templates

### MCP Best Practices

| Rule | Detail |
|------|--------|
| single responsibility | one server = one clear domain |
| secure transport | `stdio` for local, Streamable HTTP for networked |
| idempotent tools | client request IDs and deterministic results |
| pagination | keep list responses small |
| confirmation | require approval for writes, deletes, or spending |
| output schemas | structured outputs for efficient context usage |
| human + model readability | JSON for machines, readable blocks for humans |

### MCP Security

- never pass raw user input without sanitization
- validate tool results before adding them to context
- rate-limit per server
- audit every tool call
- split permissions by capability

## Tool And Structured Output Design

Rules:
- descriptions must say when to call the tool;
- required parameters should be minimal;
- use enums and defaults where possible;
- return actionable error messages;
- validate all outputs with a schema before downstream use.

## Caching And Multi-Agent Rules

### Cache Strategy

| Strategy | Use case | Expected hit rate |
|----------|----------|------------------|
| exact cache | repeated classification / FAQ | `40-70%` |
| semantic cache | similar chat queries | `10-30%` |
| prompt cache | stable system prompts and tool definitions | up to `90%` input-cost reduction |
| KV cache | multi-turn prefixes | provider-managed |

### Multi-Agent Rules

- one agent = one clear responsibility;
- use structured interfaces, not free-form inter-agent prose;
- isolate failures;
- keep orchestration centralized;
- light agents `<3k` tokens are preferred;
- `25k+` custom agents are bottlenecks.

## Streaming And UX

- token streaming for chat
- progressive loading for long generation
- optimistic UI only when downstream semantics are safe
- user cancellation support for long tasks

## Oracle Gates

- no structured-output schema -> block at `DESIGN`
- no per-step validation -> require validation-embedded plan
- no cost cap -> require budget ceiling
- multi-agent design with implicit communication -> require structured interfaces
