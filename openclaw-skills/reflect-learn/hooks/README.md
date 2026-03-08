# Reflect Hooks Integration

This directory contains hooks for integrating the reflect skill with Claude Code's hook system.

## Available Hooks

### precompact_reflect.py

Integrates with the `PreCompact` hook event to trigger reflection before context compaction.

**Modes:**

| Mode | Flag | Behavior |
|------|------|----------|
| Remind | `--remind` | Adds context reminder to run `/reflect` (non-blocking) |
| Auto | `--auto` | Triggers automatic reflection if enabled (creates output file) |
| Log Only | `--log-only` | Just logs the event without any output |

## Installation

### Option 1: Add to Existing PreCompact Hook Chain

If you already have a PreCompact hook (like running `/handover`), chain the reflect hook:

```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run /path/to/toolkit/packages/skills/reflect/hooks/precompact_reflect.py --remind"
          }
        ]
      }
    ]
  }
}
```

### Option 2: Combined Hook Command

Combine with your existing hook using shell chaining:

```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run ~/.claude/hooks/pre_compact.py --backup && uv run /path/to/precompact_reflect.py --remind"
          }
        ]
      }
    ]
  }
}
```

### Option 3: Copy to ~/.claude/hooks/

Copy the script to your hooks directory for easier access:

```bash
cp precompact_reflect.py ~/.claude/hooks/
chmod +x ~/.claude/hooks/precompact_reflect.py
```

Then configure:

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

## Configuration Examples

### Full Integration (Recommended)

This configuration:
1. Creates handover document
2. Backs up transcript
3. Adds reflect reminder (or auto-reflects if enabled)

```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "claude handover && uv run ~/.claude/hooks/pre_compact.py --backup && uv run ~/.claude/hooks/precompact_reflect.py --auto --verbose"
          }
        ]
      }
    ]
  }
}
```

### Minimal (Remind Only)

Just adds a reminder to run `/reflect`:

```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run /path/to/precompact_reflect.py --remind"
          }
        ]
      }
    ]
  }
}
```

### Auto-Reflection

Automatically creates reflection output file when context compacts:

```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run /path/to/precompact_reflect.py --auto"
          }
        ]
      }
    ]
  }
}
```

**Note:** Auto-reflection only runs if you've enabled it with `/reflect on`. Otherwise, it falls back to remind mode.

## Hook Input/Output

### Input (via stdin)

The hook receives JSON input from Claude Code:

```json
{
  "session_id": "abc123...",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/directory",
  "trigger": "auto|manual",
  "custom_instructions": "..."
}
```

### Output (via stdout)

The hook returns JSON that Claude processes:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreCompact",
    "additionalContext": "Message to add to Claude's context"
  }
}
```

## Enabling Auto-Reflection

To enable automatic reflection on context compaction:

```bash
/reflect on
```

This sets `auto_reflect: true` in the state file. When PreCompact triggers:

1. If `--auto` flag is set and auto_reflect is enabled:
   - Creates reflection output file
   - Updates indexes
   - Adds context about the reflection

2. If auto_reflect is disabled:
   - Falls back to remind mode
   - Adds reminder to run `/reflect` manually

## Logs

The hook logs events to `~/.claude/logs/reflect_precompact.log`:

```
[2026-01-24T10:30:00] session=abc123 trigger=auto mode=remind
[2026-01-24T11:45:00] session=def456 trigger=manual mode=auto
```

## Troubleshooting

### Hook not running

1. Check settings.json syntax (must be valid JSON)
2. Verify script path is correct
3. Check script has execute permissions: `chmod +x precompact_reflect.py`
4. Check uv is installed: `which uv`

### No output from hook

1. Run with `--verbose` flag for debugging
2. Check `~/.claude/logs/reflect_precompact.log` for events
3. Test script directly: `echo '{"trigger":"manual"}' | python precompact_reflect.py --remind`

### State not found

The hook looks for state in:
1. `$REFLECT_STATE_DIR` (if set)
2. `~/.claude/session/` (if exists)
3. `~/.reflect/` (fallback)

Run `/reflect status` to verify state location.

## Integration with Other Hooks

### SessionStart

You can also add reflection status to SessionStart:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python -c \"import json; print(json.dumps({'additionalContext': 'Auto-reflect: ' + ('enabled' if open(os.path.expanduser('~/.claude/session/reflect-state.yaml')).read().find('auto_reflect: true') >= 0 else 'disabled')}))\""
          }
        ]
      }
    ]
  }
}
```

### UserPromptSubmit

Inject reflection reminders at high context usage:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "your-script-that-checks-context-and-reminds.py"
          }
        ]
      }
    ]
  }
}
```

## Related Files

- `../scripts/state_manager.py` - State management
- `../scripts/output_generator.py` - Reflection output generation
- `../scripts/signal_detector.py` - Signal detection
- `../SKILL.md` - Main skill documentation
