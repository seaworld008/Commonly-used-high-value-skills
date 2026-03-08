#!/usr/bin/env python3
"""
State Manager for Reflect Skill

Manages state files for reflection tracking including:
- reflect-state.yaml: Toggle state, pending reviews
- reflect-metrics.yaml: Aggregate metrics
- learnings.yaml: Log of applied learnings

State directory is configurable via REFLECT_STATE_DIR env var.
Defaults to ~/.reflect/ for portability or ~/.claude/session/ for Claude Code.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("PyYAML required. Install with: pip install pyyaml")
    sys.exit(1)


def get_state_dir() -> Path:
    """Return state directory, configurable via env or default."""
    custom_dir = os.environ.get('REFLECT_STATE_DIR')
    if custom_dir:
        return Path(custom_dir).expanduser()

    # Check for Claude Code installation
    claude_session = Path.home() / '.claude' / 'session'
    if claude_session.exists():
        return claude_session

    # Portable default
    return Path.home() / '.reflect'


def ensure_state_dir() -> Path:
    """Create state directory if it doesn't exist."""
    state_dir = get_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def get_state_file() -> Path:
    """Return path to reflect-state.yaml."""
    return get_state_dir() / 'reflect-state.yaml'


def get_metrics_file() -> Path:
    """Return path to reflect-metrics.yaml."""
    return get_state_dir() / 'reflect-metrics.yaml'


def get_learnings_file() -> Path:
    """Return path to learnings.yaml."""
    return get_state_dir() / 'learnings.yaml'


def load_yaml(path: Path) -> dict:
    """Load YAML file, return empty dict if not found."""
    if not path.exists():
        return {}
    with open(path, 'r') as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data: dict) -> None:
    """Save data to YAML file."""
    ensure_state_dir()
    with open(path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def init_state() -> dict:
    """Initialize or load state from state directory."""
    state_file = get_state_file()

    if state_file.exists():
        state = load_yaml(state_file)
        print(f"Loaded existing state from {state_file}")
        return state

    # Create default state
    default_state = {
        'auto_reflect': False,
        'last_reflection': None,
        'pending_low_confidence': []
    }
    save_yaml(state_file, default_state)
    print(f"Initialized new state at {state_file}")
    return default_state


def get_state() -> dict:
    """Get current state without modifying."""
    return load_yaml(get_state_file())


def set_auto_reflect(enabled: bool) -> None:
    """Enable or disable auto-reflection."""
    state = get_state()
    state['auto_reflect'] = enabled
    save_yaml(get_state_file(), state)
    status = "enabled" if enabled else "disabled"
    print(f"Auto-reflection {status}")


def update_last_reflection() -> None:
    """Update last_reflection timestamp."""
    state = get_state()
    state['last_reflection'] = datetime.now().isoformat()
    save_yaml(get_state_file(), state)


def add_pending_low_confidence(signal: dict) -> None:
    """Add signal to pending review queue."""
    state = get_state()
    pending = state.get('pending_low_confidence', [])
    pending.append({
        'signal': signal.get('signal', ''),
        'detected': datetime.now().isoformat(),
        'awaiting_validation': True,
        'source_quote': signal.get('source_quote', ''),
        'category': signal.get('category', 'Unknown')
    })
    state['pending_low_confidence'] = pending
    save_yaml(get_state_file(), state)


def get_pending_reviews() -> list:
    """Get all pending low-confidence learnings."""
    state = get_state()
    return state.get('pending_low_confidence', [])


def clear_pending_review(index: int) -> bool:
    """Remove a pending review by index."""
    state = get_state()
    pending = state.get('pending_low_confidence', [])
    if 0 <= index < len(pending):
        pending.pop(index)
        state['pending_low_confidence'] = pending
        save_yaml(get_state_file(), state)
        return True
    return False


def add_learning(learning: dict) -> None:
    """Add a learning to the learnings log."""
    learnings_file = get_learnings_file()
    learnings = load_yaml(learnings_file)

    if 'entries' not in learnings:
        learnings['entries'] = []

    learnings['entries'].append({
        'timestamp': datetime.now().isoformat(),
        'signal': learning.get('signal', ''),
        'confidence': learning.get('confidence', 'unknown'),
        'source': learning.get('source', ''),
        'target': learning.get('target', ''),
        'status': learning.get('status', 'applied'),
        'session_id': learning.get('session_id', '')
    })

    save_yaml(learnings_file, learnings)


def show_status() -> None:
    """Print current state and metrics."""
    state = get_state()
    metrics = load_yaml(get_metrics_file())

    print("\n=== Reflect Status ===\n")
    print(f"State Directory: {get_state_dir()}")
    print(f"Auto-Reflect: {'Enabled' if state.get('auto_reflect') else 'Disabled'}")
    print(f"Last Reflection: {state.get('last_reflection', 'Never')}")

    pending = state.get('pending_low_confidence', [])
    print(f"Pending Reviews: {len(pending)}")

    if metrics:
        print(f"\n=== Metrics ===\n")
        print(f"Total Sessions: {metrics.get('total_sessions_analyzed', 0)}")
        print(f"Signals Detected: {metrics.get('total_signals_detected', 0)}")
        print(f"Changes Proposed: {metrics.get('total_changes_proposed', 0)}")
        print(f"Changes Accepted: {metrics.get('total_changes_accepted', 0)}")
        print(f"Acceptance Rate: {metrics.get('acceptance_rate', 0)}%")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Reflect State Manager')
    parser.add_argument('command', choices=['init', 'status', 'on', 'off', 'pending'],
                       help='Command to execute')

    args = parser.parse_args()

    if args.command == 'init':
        init_state()
    elif args.command == 'status':
        show_status()
    elif args.command == 'on':
        set_auto_reflect(True)
    elif args.command == 'off':
        set_auto_reflect(False)
    elif args.command == 'pending':
        pending = get_pending_reviews()
        if not pending:
            print("No pending low-confidence learnings.")
        else:
            print(f"\n=== Pending Reviews ({len(pending)}) ===\n")
            for i, item in enumerate(pending):
                print(f"{i+1}. {item.get('signal')}")
                print(f"   Detected: {item.get('detected')}")
                print(f"   Quote: \"{item.get('source_quote', 'N/A')}\"")
                print()


if __name__ == '__main__':
    main()
