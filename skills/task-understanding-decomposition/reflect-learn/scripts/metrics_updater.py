#!/usr/bin/env python3
"""
Metrics Updater for Reflect Skill

Tracks and aggregates reflection metrics including:
- Sessions analyzed
- Signals detected by confidence level
- Changes proposed vs accepted
- Most frequently updated agents

Usage:
    python metrics_updater.py --accepted 3 --rejected 1 --confidence high:2,medium:1
    python metrics_updater.py --show
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

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

    claude_session = Path.home() / '.claude' / 'session'
    if claude_session.exists():
        return claude_session

    return Path.home() / '.reflect'


def get_metrics_file() -> Path:
    """Return path to reflect-metrics.yaml."""
    return get_state_dir() / 'reflect-metrics.yaml'


def load_metrics() -> dict:
    """Load metrics from file or return defaults."""
    metrics_file = get_metrics_file()

    if not metrics_file.exists():
        return get_default_metrics()

    with open(metrics_file, 'r') as f:
        return yaml.safe_load(f) or get_default_metrics()


def save_metrics(metrics: dict) -> None:
    """Save metrics to file."""
    metrics_file = get_metrics_file()
    metrics_file.parent.mkdir(parents=True, exist_ok=True)

    with open(metrics_file, 'w') as f:
        yaml.dump(metrics, f, default_flow_style=False, sort_keys=False)


def get_default_metrics() -> dict:
    """Return default metrics structure."""
    return {
        'last_reflection': None,
        'total_sessions_analyzed': 0,
        'total_signals_detected': 0,
        'total_changes_proposed': 0,
        'total_changes_accepted': 0,
        'acceptance_rate': 0,
        'most_updated_agents': {},
        'confidence_breakdown': {
            'high': 0,
            'medium': 0,
            'low': 0
        },
        'skills_created': 0,
        'estimated_time_saved': '~0 hours'
    }


def update_metrics(
    accepted: int = 0,
    rejected: int = 0,
    high: int = 0,
    medium: int = 0,
    low: int = 0,
    agents: Optional[list[str]] = None,
    skills: int = 0
) -> dict:
    """
    Update metrics with new reflection results.

    Args:
        accepted: Number of accepted changes
        rejected: Number of rejected changes
        high: Number of high-confidence signals
        medium: Number of medium-confidence signals
        low: Number of low-confidence signals
        agents: List of agent names that were updated
        skills: Number of new skills created

    Returns:
        Updated metrics dict
    """
    metrics = load_metrics()

    # Update timestamp
    metrics['last_reflection'] = datetime.now().isoformat()

    # Increment session count
    metrics['total_sessions_analyzed'] = metrics.get('total_sessions_analyzed', 0) + 1

    # Update signal counts
    total_signals = high + medium + low
    metrics['total_signals_detected'] = metrics.get('total_signals_detected', 0) + total_signals

    # Update change counts
    proposed = accepted + rejected
    metrics['total_changes_proposed'] = metrics.get('total_changes_proposed', 0) + proposed
    metrics['total_changes_accepted'] = metrics.get('total_changes_accepted', 0) + accepted

    # Calculate acceptance rate
    total_proposed = metrics['total_changes_proposed']
    total_accepted = metrics['total_changes_accepted']
    if total_proposed > 0:
        metrics['acceptance_rate'] = round((total_accepted / total_proposed) * 100)

    # Update confidence breakdown
    breakdown = metrics.get('confidence_breakdown', {'high': 0, 'medium': 0, 'low': 0})
    breakdown['high'] = breakdown.get('high', 0) + high
    breakdown['medium'] = breakdown.get('medium', 0) + medium
    breakdown['low'] = breakdown.get('low', 0) + low
    metrics['confidence_breakdown'] = breakdown

    # Update agent counts
    if agents:
        agent_counts = metrics.get('most_updated_agents', {})
        for agent in agents:
            agent_counts[agent] = agent_counts.get(agent, 0) + 1
        # Sort by count and keep top 10
        sorted_agents = dict(sorted(agent_counts.items(), key=lambda x: -x[1])[:10])
        metrics['most_updated_agents'] = sorted_agents

    # Update skills count
    metrics['skills_created'] = metrics.get('skills_created', 0) + skills

    # Estimate time saved (rough heuristic: 5 min per accepted learning)
    total_accepted = metrics['total_changes_accepted']
    hours_saved = round(total_accepted * 5 / 60, 1)
    metrics['estimated_time_saved'] = f"~{hours_saved} hours"

    save_metrics(metrics)
    return metrics


def show_metrics() -> None:
    """Display current metrics."""
    metrics = load_metrics()

    print("\n=== Reflect Metrics ===\n")
    print(f"Last Reflection: {metrics.get('last_reflection', 'Never')}")
    print(f"Sessions Analyzed: {metrics.get('total_sessions_analyzed', 0)}")
    print(f"Total Signals: {metrics.get('total_signals_detected', 0)}")
    print(f"Changes Proposed: {metrics.get('total_changes_proposed', 0)}")
    print(f"Changes Accepted: {metrics.get('total_changes_accepted', 0)}")
    print(f"Acceptance Rate: {metrics.get('acceptance_rate', 0)}%")
    print(f"Skills Created: {metrics.get('skills_created', 0)}")
    print(f"Estimated Time Saved: {metrics.get('estimated_time_saved', '~0 hours')}")

    breakdown = metrics.get('confidence_breakdown', {})
    print(f"\nConfidence Breakdown:")
    print(f"  High: {breakdown.get('high', 0)}")
    print(f"  Medium: {breakdown.get('medium', 0)}")
    print(f"  Low: {breakdown.get('low', 0)}")

    agents = metrics.get('most_updated_agents', {})
    if agents:
        print(f"\nMost Updated Agents:")
        for agent, count in list(agents.items())[:5]:
            print(f"  {agent}: {count}")


def parse_confidence(conf_str: str) -> tuple[int, int, int]:
    """Parse confidence string like 'high:2,medium:1,low:3'."""
    high = medium = low = 0

    for part in conf_str.split(','):
        if ':' in part:
            level, count = part.split(':')
            count = int(count)
            if level.lower() == 'high':
                high = count
            elif level.lower() == 'medium':
                medium = count
            elif level.lower() == 'low':
                low = count

    return high, medium, low


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Update reflection metrics')
    parser.add_argument('--accepted', type=int, default=0, help='Number of accepted changes')
    parser.add_argument('--rejected', type=int, default=0, help='Number of rejected changes')
    parser.add_argument('--confidence', type=str, help='Confidence breakdown (e.g., high:2,medium:1)')
    parser.add_argument('--agents', type=str, help='Comma-separated list of updated agents')
    parser.add_argument('--skills', type=int, default=0, help='Number of skills created')
    parser.add_argument('--show', action='store_true', help='Show current metrics')
    parser.add_argument('--reset', action='store_true', help='Reset all metrics')

    args = parser.parse_args()

    if args.show:
        show_metrics()
        return

    if args.reset:
        save_metrics(get_default_metrics())
        print("Metrics reset to defaults.")
        return

    high = medium = low = 0
    if args.confidence:
        high, medium, low = parse_confidence(args.confidence)

    agents = None
    if args.agents:
        agents = [a.strip() for a in args.agents.split(',')]

    metrics = update_metrics(
        accepted=args.accepted,
        rejected=args.rejected,
        high=high,
        medium=medium,
        low=low,
        agents=agents,
        skills=args.skills
    )

    print(f"Metrics updated. Acceptance rate: {metrics['acceptance_rate']}%")


if __name__ == '__main__':
    main()
