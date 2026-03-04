---
name: reflect
description: |
  Self-improvement through conversation analysis. Extracts learnings from
  corrections and success patterns, proposes updates to agent files or
  creates new skills. Philosophy: "Correct once, never again."

  Use when: (1) User explicitly corrects behavior ("never do X", "always Y"),
  (2) Session ending or context compaction, (3) User requests /reflect,
  (4) Successful pattern worth preserving.
version: 2.0.0
author: Claude Code Toolkit
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
---

# Reflect - Self-Improvement Skill

## Quick Reference

| Command | Action |
|---------|--------|
| `/reflect` | Analyze conversation for learnings |
| `/reflect on` | Enable auto-reflection |
| `/reflect off` | Disable auto-reflection |
| `/reflect status` | Show state and metrics |
| `/reflect review` | Review low-confidence learnings |
| `/reflect [agent]` | Focus on specific agent |

## Core Philosophy

**"Correct once, never again."**

When users correct behavior, those corrections become permanent improvements encoded into the agent system - across all future sessions.

## Workflow

### Step 1: Initialize State

Check and initialize state files using the state manager:

```bash
# Check for existing state
python scripts/state_manager.py init

# State directory is configurable via REFLECT_STATE_DIR env var
# Default: ~/.reflect/ (portable) or ~/.claude/session/ (Claude Code)
```

State includes:
- `reflect-state.yaml` - Toggle state, pending reviews
- `reflect-metrics.yaml` - Aggregate metrics
- `learnings.yaml` - Log of all applied learnings

### Step 2: Scan Conversation for Signals

Use the signal detector to identify learnings:

```bash
python scripts/signal_detector.py --input conversation.txt
```

#### Signal Confidence Levels

| Confidence | Triggers | Examples |
|------------|----------|----------|
| **HIGH** | Explicit corrections | "never", "always", "wrong", "stop", "the rule is" |
| **MEDIUM** | Approved approaches | "perfect", "exactly", accepted output |
| **LOW** | Observations | Patterns that worked, not validated |

See [signal_patterns.md](references/signal_patterns.md) for full detection rules.

### Step 3: Classify & Match to Target Files

Map each signal to the appropriate target:

**Learning Categories:**

| Category | Target Files |
|----------|--------------|
| Code Style | `code-reviewer`, `backend-developer`, `frontend-developer` |
| Architecture | `solution-architect`, `api-architect`, `architecture-reviewer` |
| Process | `CLAUDE.md`, orchestrator agents |
| Domain | Domain-specific agents, `CLAUDE.md` |
| Tools | `CLAUDE.md`, relevant specialists |
| New Skill | `.claude/skills/{name}/SKILL.md` |

See [agent_mappings.md](references/agent_mappings.md) for mapping rules.

### Step 4: Check for Skill-Worthy Signals

Some learnings should become new skills rather than agent updates:

**Skill-Worthy Criteria:**
- Non-obvious debugging (>10 min investigation)
- Misleading error (root cause different from message)
- Workaround discovered through experimentation
- Configuration insight (differs from documented)
- Reusable pattern (helps in similar situations)

**Quality Gates (must pass all):**
- [ ] Reusable: Will help with future tasks
- [ ] Non-trivial: Requires discovery, not just docs
- [ ] Specific: Can describe exact trigger conditions
- [ ] Verified: Solution actually worked
- [ ] No duplication: Doesn't exist already

See [skill_template.md](references/skill_template.md) for skill creation guidelines.

### Step 5: Generate Proposals

Produce output in this format:

```markdown
# Reflection Analysis

## Session Context
- **Date**: [timestamp]
- **Messages Analyzed**: [count]
- **Focus**: [all agents OR specific agent name]

## Signals Detected

| # | Signal | Confidence | Source Quote | Category |
|---|--------|------------|--------------|----------|
| 1 | [learning] | HIGH | "[exact words]" | Code Style |
| 2 | [learning] | MEDIUM | "[context]" | Architecture |

## Proposed Agent Updates

### Change 1: Update [agent-name]

**Target**: `[file path]`
**Section**: [section name]
**Confidence**: [HIGH/MEDIUM/LOW]
**Rationale**: [why this change]

```diff
--- a/path/to/agent.md
+++ b/path/to/agent.md
@@ -82,6 +82,7 @@
 ## Section

 * Existing rule
+* New rule from learning
```

## Proposed New Skills

### Skill 1: [skill-name]

**Quality Gate Check**:
- [x] Reusable: [why]
- [x] Non-trivial: [why]
- [x] Specific: [trigger conditions]
- [x] Verified: [how verified]
- [x] No duplication: [checked against]

**Will create**: `.claude/skills/[skill-name]/SKILL.md`

## Conflict Check

- [x] No conflicts with existing rules detected
- OR: Warning - potential conflict with [file:line]

## Commit Message

```
reflect: add learnings from session [date]

Agent updates:
- [learning 1 summary]

New skills:
- [skill-name]: [brief description]

Extracted: [N] signals ([H] high, [M] medium, [L] low confidence)
```

## Review Prompt

Apply these changes?
- `Y` - Apply all changes and commit
- `N` - Discard all changes
- `modify` - Adjust specific changes
- `1,3` - Apply only changes 1 and 3
- `s1` - Apply only skill 1
- `all-skills` - Apply all skills, skip agent updates
```

### Step 6: Handle User Response

**On `Y` (approve):**
1. Apply each change using Edit tool
2. Run `git add` on modified files
3. Commit with generated message
4. Update learnings log
5. Update metrics

**On `N` (reject):**
1. Discard proposed changes
2. Log rejection for analysis
3. Ask if user wants to modify any signals

**On `modify`:**
1. Present each change individually
2. Allow editing the proposed addition
3. Reconfirm before applying

**On selective (e.g., `1,3`):**
1. Apply only specified changes
2. Log partial acceptance
3. Commit only applied changes

### Step 7: Update Metrics

```bash
python scripts/metrics_updater.py --accepted 3 --rejected 1 --confidence high:2,medium:1
```

## Toggle Commands

### Enable Auto-Reflection

```bash
/reflect on
# Sets auto_reflect: true in state file
# Will trigger on PreCompact hook
```

### Disable Auto-Reflection

```bash
/reflect off
# Sets auto_reflect: false in state file
```

### Check Status

```bash
/reflect status
# Shows current state and metrics
```

### Review Pending

```bash
/reflect review
# Shows low-confidence learnings awaiting validation
```

## Output Locations

**Project-level (versioned with repo):**
- `.claude/reflections/YYYY-MM-DD_HH-MM-SS.md` - Full reflection
- `.claude/reflections/index.md` - Project summary
- `.claude/skills/{name}/SKILL.md` - New skills

**Global (user-level):**
- `~/.claude/reflections/by-project/{project}/` - Cross-project
- `~/.claude/reflections/by-agent/{agent}/learnings.md` - Per-agent
- `~/.claude/reflections/index.md` - Global summary

## Memory Integration

Some learnings belong in **auto-memory** (`~/.claude/projects/*/memory/MEMORY.md`) rather than agent files:

| Learning Type | Best Target |
|---------------|-------------|
| Behavioral correction ("always do X") | Agent file |
| Project-specific pattern | MEMORY.md |
| Recurring bug/workaround | New skill OR MEMORY.md |
| Tool preference | CLAUDE.md |
| Domain knowledge | MEMORY.md or compound-docs |

When a signal is LOW confidence and project-specific, prefer writing to MEMORY.md over modifying agents.

## Safety Guardrails

### Human-in-the-Loop
- NEVER apply changes without explicit user approval
- Always show full diff before applying
- Allow selective application

### Git Versioning
- All changes committed with descriptive messages
- Easy rollback via `git revert`
- Learning history preserved

### Incremental Updates
- ONLY add to existing sections
- NEVER delete or rewrite existing rules
- Preserve original structure

### Conflict Detection
- Check if proposed rule contradicts existing
- Warn user if conflict detected
- Suggest resolution strategy

## Integration

### With /handover
If auto-reflection is enabled, PreCompact hook triggers reflection before handover.

### With Session Health
At 70%+ context (Yellow status), reminders to run `/reflect` are injected.

### Hook Integration (Claude Code)

The skill includes hook scripts for automatic integration:

```bash
# Install hook to your Claude hooks directory
cp hooks/precompact_reflect.py ~/.claude/hooks/
```

Configure in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run ~/.claude/hooks/precompact_reflect.py --auto"
          }
        ]
      }
    ]
  }
}
```

See [hooks/README.md](hooks/README.md) for full configuration options.

## Portability

This skill works with any LLM tool that supports:
- File read/write operations
- Text pattern matching
- Git operations (optional, for commits)

### Configurable State Location

```bash
# Set custom state directory
export REFLECT_STATE_DIR=/path/to/state

# Or use default
# ~/.reflect/ (portable default)
# ~/.claude/session/ (Claude Code default)
```

### No Task Tool Dependency

Unlike the previous agent-based approach, this skill executes directly without spawning subagents. The LLM reads SKILL.md and follows the workflow.

### Git Operations Optional

Commits are wrapped with availability checks - if not in a git repo, changes are still saved but not committed.

## Troubleshooting

**No signals detected:**
- Session may not have had corrections
- Try `/reflect review` to check pending items

**Conflict warning:**
- Review the existing rule cited
- Decide if new rule should override
- Can modify before applying

**Agent file not found:**
- Check agent name spelling
- Use `/reflect status` to see available targets
- May need to create agent file first

## File Structure

```
reflect/
├── SKILL.md                      # This file
├── scripts/
│   ├── state_manager.py          # State file CRUD
│   ├── signal_detector.py        # Pattern matching
│   ├── metrics_updater.py        # Metrics aggregation
│   └── output_generator.py       # Reflection file & index generation
├── hooks/
│   ├── precompact_reflect.py     # PreCompact hook integration
│   ├── settings-snippet.json     # Settings.json examples
│   └── README.md                 # Hook configuration guide
├── references/
│   ├── signal_patterns.md        # Detection rules
│   ├── agent_mappings.md         # Target mappings
│   └── skill_template.md         # Skill generation
└── assets/
    ├── reflection_template.md    # Output template
    └── learnings_schema.yaml     # Schema definition
```
