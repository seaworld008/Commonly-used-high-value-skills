> **Historical compatibility snapshot — not current upstream guidance.** Upstream removed this path by `f425adcb2111ca8c0be88b325888ff61b64dec49`. Preserved from `bd5d9cd61c0718c3c093e9cfcce2bd20e9cb4104` under the recorded license. Use the canonical skill and current references for new work.

# Guardian — AUTORUN `_STEP_COMPLETE` Schema

When Guardian receives `_AGENT_CONTEXT`, parse `task_type`, `description`, and `Constraints`, execute the standard workflow, and return `_STEP_COMPLETE`.

### `_STEP_COMPLETE`

```yaml
_STEP_COMPLETE:
  Agent: Guardian
  Status: SUCCESS | PARTIAL | BLOCKED | FAILED
  Output:
    deliverable: [primary artifact]
    parameters:
      task_type: "[task type]"
      scope: "[scope]"
  Validations:
    completeness: "[complete | partial | blocked]"
    quality_check: "[passed | flagged | skipped]"
  Next: [recommended next agent or DONE]
  Reason: [Why this next step]
```
