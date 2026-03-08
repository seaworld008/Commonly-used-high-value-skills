#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml",
# ]
# ///
"""
PreCompact Reflect Hook

Integrates with Claude Code's PreCompact hook to trigger reflection
before context compaction. Can run in background mode to avoid blocking.

Usage in settings.json:
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

Modes:
  --remind    : Add reminder to run /reflect (non-blocking)
  --auto      : Trigger automatic reflection (blocking, generates output)
  --log-only  : Just log the event (non-blocking)
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def get_state_dir() -> Path:
    """Get the reflect state directory."""
    custom_dir = os.environ.get('REFLECT_STATE_DIR')
    if custom_dir:
        return Path(custom_dir).expanduser()

    claude_session = Path.home() / '.claude' / 'session'
    if claude_session.exists():
        return claude_session

    return Path.home() / '.reflect'


def load_state() -> dict:
    """Load reflect state."""
    state_file = get_state_dir() / 'reflect-state.yaml'
    if not state_file.exists():
        return {'auto_reflect': False}

    if yaml:
        with open(state_file) as f:
            return yaml.safe_load(f) or {}
    else:
        # Fallback: basic parsing
        return {'auto_reflect': False}


def is_auto_reflect_enabled() -> bool:
    """Check if auto-reflection is enabled."""
    state = load_state()
    return state.get('auto_reflect', False)


def log_precompact_event(input_data: dict, mode: str):
    """Log the PreCompact event for debugging."""
    log_dir = Path.home() / '.claude' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / 'reflect_precompact.log'

    timestamp = datetime.now().isoformat()
    session_id = input_data.get('session_id', 'unknown')[:8]
    trigger = input_data.get('trigger', 'unknown')

    log_entry = f"[{timestamp}] session={session_id} trigger={trigger} mode={mode}\n"

    with open(log_file, 'a') as f:
        f.write(log_entry)


def generate_reminder_context(trigger: str) -> dict:
    """Generate context reminder for reflection."""
    auto_enabled = is_auto_reflect_enabled()

    if trigger == 'auto':
        # Context window is filling up
        message = (
            "Context compaction triggered. "
            "Consider running `/reflect` to capture learnings from this session before compaction."
        )
    else:
        # Manual compaction
        message = (
            "Manual compaction requested. "
            "Run `/reflect` first if you want to preserve learnings from this session."
        )

    if auto_enabled:
        message += "\n\nNote: Auto-reflect is enabled. Running reflection analysis..."

    return {
        "hookSpecificOutput": {
            "hookEventName": "PreCompact",
            "additionalContext": message
        }
    }


def run_reflection_analysis(input_data: dict) -> dict:
    """
    Run reflection analysis on the session transcript.

    This reads the transcript and generates a reflection output file.
    """
    transcript_path = input_data.get('transcript_path', '')

    if not transcript_path or not Path(transcript_path).exists():
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreCompact",
                "additionalContext": "Could not access transcript for reflection analysis."
            }
        }

    # Import the output generator
    scripts_dir = Path(__file__).parent.parent / 'scripts'
    sys.path.insert(0, str(scripts_dir))

    try:
        from output_generator import generate_full_reflection

        # For auto-reflection, we create a minimal reflection record
        # The actual signal detection would be done by the LLM
        result = generate_full_reflection(
            signals=[],  # Would be populated by signal_detector
            agent_updates=[],
            new_skills=[],
            session_context={
                'trigger': input_data.get('trigger', 'auto'),
                'session_id': input_data.get('session_id', ''),
            },
            update_indexes=True
        )

        return {
            "hookSpecificOutput": {
                "hookEventName": "PreCompact",
                "additionalContext": (
                    f"Reflection placeholder created at: {result['reflection_file']}\n"
                    "Run `/reflect` to perform full analysis and populate with learnings."
                )
            }
        }
    except ImportError:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreCompact",
                "additionalContext": "Reflection analysis not available. Run `/reflect` manually."
            }
        }


def main():
    parser = argparse.ArgumentParser(description='PreCompact Reflect Hook')
    parser.add_argument('--remind', action='store_true',
                       help='Add reminder to run /reflect')
    parser.add_argument('--auto', action='store_true',
                       help='Trigger automatic reflection if enabled')
    parser.add_argument('--log-only', action='store_true',
                       help='Just log the event')
    parser.add_argument('--verbose', action='store_true',
                       help='Print verbose output')

    args = parser.parse_args()

    # Read input from stdin
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        input_data = {}

    trigger = input_data.get('trigger', 'unknown')

    # Determine mode
    if args.log_only:
        mode = 'log-only'
    elif args.auto:
        mode = 'auto'
    else:
        mode = 'remind'

    # Log the event
    log_precompact_event(input_data, mode)

    # Handle based on mode
    if mode == 'log-only':
        if args.verbose:
            print(f"Logged PreCompact event (trigger={trigger})")
        sys.exit(0)

    elif mode == 'auto' and is_auto_reflect_enabled():
        # Run automatic reflection
        output = run_reflection_analysis(input_data)
        print(json.dumps(output))
        sys.exit(0)

    elif mode == 'remind':
        # Just add a reminder
        output = generate_reminder_context(trigger)
        print(json.dumps(output))
        sys.exit(0)

    else:
        # Auto mode but not enabled, just remind
        if args.verbose:
            print("Auto-reflect not enabled, adding reminder")
        output = generate_reminder_context(trigger)
        print(json.dumps(output))
        sys.exit(0)


if __name__ == '__main__':
    main()
