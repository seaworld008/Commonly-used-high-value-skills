# Hub-Engine Authoring

Use this reference when binding a Nexus chain to the executing host. It owns the
Agent Spawn Template and Orchestrator Detection table. Domain methods remain in
the selected specialist skill.

## Orchestrator Detection

Inspect the callable tools once before delegation and reuse the result while the
host stays unchanged. A product name or a skill file does not prove tool access.

| Available capability | Binding |
|---|---|
| Claude Code `Agent` tool | Use its documented foreground/background and context options |
| Codex collaboration tools | Use the exposed spawn, message and wait schemas; names vary by host |
| Another host with delegation | Bind to its documented API and available model choices |
| No permitted delegation tool | Complete independent steps locally and report the capability limit |

Do not install another CLI or relax permissions just to satisfy a recipe. Treat
`_common/` protocols as optional upstream integration references: use them only
when installed and selected for this task, within current host and user rules.

## Claude Code hub

Keep the task, owned files, acceptance criteria and allowed effects clear. Use
background agents for genuinely independent work when supported. A producer runs
its relevant checks; independent review is added when the task or project needs
it. Do not duplicate successful checks merely to produce another status message.

Keep the current configured model and effort unless the user or project requests
a change. Check official documentation and the installed CLI before adopting new
frontmatter, permission modes, model IDs or orchestration features.

## Claude Code hub — Fable 5

This heading remains a reference anchor for upstream recipes. It does not select
a model or assert account access. If the current host explicitly supplies this
model, apply its current official guidance. Otherwise use the ordinary host
binding above. Do not infer model availability or pricing from a copied recipe.

Safety refusals are not permission to route the same prohibited action through
another engine. Report the actual restriction and continue supported work.

## Codex CLI hub

Use the runtime's available collaboration API; do not assume an API name from
another Codex release. Spawn bounded independent work, continue useful local work,
and wait at dependency barriers. Give each branch distinct file ownership.

Preserve a named model such as `gpt-6-astra`. Do not silently replace it with a
legacy role-based model table. Select supported reasoning settings from the host
and current official model guidance. API features do not automatically imply the
same feature exists in a CLI or desktop tool.

## agy hub

For a requested Antigravity workflow, verify the installed CLI's help and output
capture behavior before dispatch. Use the current configured model unless the
user requests another. Validate that a result artifact is nonempty and contains
the expected output; exit code alone does not establish task completion.

Keep retries bounded and distinguish output-capture failure, authentication,
quota exhaustion and task failure. A missing optional engine reduces comparison
coverage; it need not block independent work on an available engine.

## Agent Spawn Template

Translate this task envelope into the host's real tool schema. It is not a literal
cross-host API call and does not request permission bypass.

```text
Task: [concrete bounded outcome]
Owned files or investigation scope: [paths / questions]
Context: [relevant evidence and decisions]
Skill: [actual installed path, when needed]
Acceptance criteria: [observable success conditions]
Authority:
  allowed: [effects already authorized by the user or project]
  denied: [effects outside this step]
  redelegation: false
Completion: finish the in-scope work; if blocked, identify the remaining item,
  evidence and supported alternatives. Do not report unfinished work as SUCCESS.
Verification: [relevant checks and any valid existing evidence]
Output: concise outcome, changed files or findings, verification and residuals.

_STEP_COMPLETE:
  Agent: [role]
  Status: SUCCESS | PARTIAL | BLOCKED | FAILED
  Output: [deliverable]
  Residual: [none or outstanding work with evidence]
  Next: [dependency or DONE]
```

Scope bounds the work; authority bounds its effects. A branch cannot acquire
permissions its parent does not have. Existing authorization can cover later
steps, but ambiguous targets, scope increases or destructive effects need
resolution. Report a genuine missing prerequisite promptly rather than inventing
mandatory failed attempts to earn BLOCKED status.

## Spawn Template Variants

- Claude: use the installed skill path and supported Agent fields. Do not put
  `bypassPermissions` in a generic template.
- Codex: use the exposed collaboration schema and discovered skill paths. Preserve
  the user's model choice and the host's concurrency/context limits.
- Other hosts: retain the envelope and adapt only transport and supported options.
  Do not impersonate a tool the host does not expose.

Give isolated context to independent alternatives; preserve shared history when
continuity matters. Shared workspaces require nonoverlapping ownership and a
clear integration owner, regardless of context mode.

## Execution-Layer Key Rules

Use `reference/execution-layers.md` for recipe topology and checkpoint concepts.
Its CLI examples are host-specific references, not instructions to override live
tool schemas. Retry only the failed operation; consume completed branch outputs
without restarting unrelated work. Preserve user corrections and pause requests.

## Model Selection

| Decision | Default |
|---|---|
| User names a model | Preserve it; verify that the selected host supports it |
| No model is named | Inherit the configured host model |
| Routine versus difficult work | Keep settings stable; tune effort only with authority and evidence |
| Independent model comparison requested | Record model IDs, settings, budget and reduced coverage |
| Model or tool unavailable | Report the limit; use only an authorized, supported alternative |

A fixed word count, model family or reasoning level is not a universal performance
rule. Compare representative tasks under controlled settings before promoting a
new default. Report measured token, latency and correctness changes separately.

Current primary references:
- [OpenAI model guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra)
- [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Claude subagents](https://code.claude.com/docs/en/sub-agents)

## Operational Notes for Spawns

- Use `confidence-scoring.md` for unresolved scope and evidence bands; confidence
  never substitutes for authorization.
- Load only the references needed for the active phase.
- Keep `_STEP_COMPLETE` and `NEXUS_HANDOFF` usable for downstream aggregation.
- Track phase and step; persist checkpoints when the workflow requires recovery.
- For expensive recipes, the declared scope and budget need authorization. A user
  who already approved that exact envelope need not approve it again at launch.
