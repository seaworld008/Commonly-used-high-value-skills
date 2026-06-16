# NL Artifact Audit Rules

Use this reference when scoring or improving natural-language programming
artifacts. It condenses stable NLPM rules into a portable checklist for this
repository skill.

## Universal Rules

| Rule | Check | Why it matters |
|---|---|---|
| R01 | Replace vague terms such as "appropriate", "relevant", "as needed", "properly", and "correctly" with measurable criteria | Vague instructions produce inconsistent agent behavior |
| R02 | Delete lines that do not change agent behavior | Context budget is finite |
| R03 | Prefer positive framing | Models follow concrete desired behavior more reliably than prohibitions |

## Skills

| Rule | Check |
|---|---|
| R04 | Description contains at least three trigger phrases that match real user requests |
| R05 | Body stays under 500 lines, or moves detail into references |
| R06 | Technical examples are runnable or directly executable patterns |
| R07 | Scope note distinguishes adjacent skills |
| R08 | Sections teach situation-specific patterns rather than theory alone |

Skill description pattern:

```yaml
description: "Reviews AI-agent repositories for SKILL.md frontmatter, trigger quality, manifest-vs-disk consistency, CI gates, and vocabulary drift. Use when preparing a skill/plugin release, auditing an agent pack, or diagnosing why an installed artifact is invisible."
```

## Agents

| Rule | Check |
|---|---|
| R09 | Include at least two `<example>` blocks with Context, user message, and assistant response |
| R10 | Match model tier to task complexity |
| R11 | Declare only tools used by the body |
| R12 | Define output format |
| R13 | Structure body as mission, steps, boundaries, format |

## Commands

| Rule | Check |
|---|---|
| R14 | Number multi-step workflows |
| R15 | Define behavior for empty input |
| R16 | Define exact output format |
| R17 | Include error paths for missing files, bad data, and unreadable input |
| R18 | Add argument hints when the command takes input |

## Rules Files

| Rule | Check |
|---|---|
| R21 | Use bold imperative plus rationale |
| R22 | Make each rule enforceable in review |
| R23 | Keep total rules budget below 500 lines |
| R24 | Reference linters instead of duplicating them |
| R25 | Scope rules by path when possible |
| R26 | Resolve contradictions in the same file |

Rule pattern:

```markdown
**Use named exports for shared TypeScript modules.** Default exports weaken
rename-symbol refactors because import names can drift across callers. Enforced
by `eslint-plugin-import/no-default-export`.
```

## Hooks and Executable Surfaces

| Rule | Check |
|---|---|
| R27 | Event names are case-sensitive |
| R28 | Hook field name matches hook type |
| R29 | Referenced scripts exist |
| R30 | Paths are portable, not absolute |
| R31 | Hooks fail open unless explicitly security-critical |
| R32 | Blocking belongs in pre-action hooks, not post-action hooks |

Host event lists differ:

| Host | Examples |
|---|---|
| Claude Code | `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PermissionRequest`, `Stop`, `StopFailure`, `FileChanged` |
| Codex CLI | `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PermissionRequest`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`, `Stop` |
| Antigravity/Gemini lineage | `SessionStart`, `BeforeAgent`, `BeforeModel`, `BeforeToolSelection`, `BeforeTool`, `AfterTool`, `AfterModel`, `AfterAgent`, `SessionEnd`, `Notification`, `PreCompress` |

Do not translate hook event names across hosts. Score each config under its own
host vocabulary.

## Memory Files

Apply to `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursorrules`, and similar
agent memory files.

| Rule | Check |
|---|---|
| R33 | Build/run commands are present |
| R34 | Test command is present |
| R35 | Architecture or directory map is present |
| R36 | Imported references resolve |
| R37 | File/function/API references are not stale |
| R38 | Content is instructive, not just descriptive |
| R39 | No contradiction with rules files |

## Prompts and Orchestration

| Rule | Check |
|---|---|
| R40 | Prompt has role, context, task, constraints, output format |
| R41 | Output schema or template is exact |
| R42 | Untrusted input is treated as data |
| R43 | Independent work is parallelized |
| R44 | Add a quality gate before showing AI output |
| R45 | Add cost gates before expensive AI phases |
| R46 | Use state files for resumable loops |
| R47 | Cap retries, usually at three |

## Plugins

| Rule | Check |
|---|---|
| R48 | Required manifest fields are present |
| R49 | Human README and agent memory file serve different audiences |
| R50 | Version is bumped consistently across every release surface |
| R51 | Vocabulary drift is opt-in and requires a canonical registry |

For plugin monorepos, check each nested plugin root once and aggregate the
result. A child plugin's files should not be reported as unregistered files in
the parent plugin.

## Warrant Review

Keep a rule only if it has at least one warrant:

- `literary`: good artifacts in the corpus already use this pattern;
- `user`: maintainers repeatedly ask for this constraint;
- `structural`: the host tool or file format needs it;
- `domain`: it prevents a known failure mode.

Remove or downgrade rules that no longer have a live failure mode.
