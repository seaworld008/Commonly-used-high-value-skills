#!/usr/bin/env python3
"""
Output Generator for Reflect Skill

Generates reflection output files and manages indexes:
- Project reflections: .claude/reflections/YYYY-MM-DD_HH-MM-SS.md
- Project index: .claude/reflections/index.md
- Global index: ~/.claude/reflections/index.md
- Per-agent learnings: ~/.claude/reflections/by-agent/{agent}/learnings.md
- Cross-project: ~/.claude/reflections/by-project/{project}/

Usage:
    python output_generator.py --reflection-data '{"signals": [...], "changes": [...]}'
    python output_generator.py --create-skill skill-name --content '...'
    python output_generator.py --update-indexes
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None


def get_project_dir() -> Path:
    """Get the project root directory."""
    # Check for CLAUDE_PROJECT_DIR env var (set by hooks)
    if os.environ.get('CLAUDE_PROJECT_DIR'):
        return Path(os.environ['CLAUDE_PROJECT_DIR'])

    # Try to find .git directory
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / '.git').exists():
            return parent

    return cwd


def get_project_name() -> str:
    """Get the project name from directory."""
    return get_project_dir().name


def get_global_reflections_dir() -> Path:
    """Get the global reflections directory."""
    return Path.home() / '.claude' / 'reflections'


def get_project_reflections_dir() -> Path:
    """Get the project reflections directory."""
    return get_project_dir() / '.claude' / 'reflections'


def get_project_skills_dir() -> Path:
    """Get the project skills directory."""
    return get_project_dir() / '.claude' / 'skills'


def ensure_directories():
    """Ensure all required directories exist."""
    dirs = [
        get_project_reflections_dir(),
        get_project_skills_dir(),
        get_global_reflections_dir(),
        get_global_reflections_dir() / 'by-agent',
        get_global_reflections_dir() / 'by-project',
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def generate_reflection_filename() -> str:
    """Generate a timestamped reflection filename."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{timestamp}.md"


def create_reflection_file(
    signals: list,
    agent_updates: list,
    new_skills: list,
    session_context: Optional[dict] = None
) -> Path:
    """
    Create a reflection output file in the project's .claude/reflections/ directory.

    Returns the path to the created file.
    """
    ensure_directories()

    filename = generate_reflection_filename()
    filepath = get_project_reflections_dir() / filename

    # Build the reflection content
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    context = session_context or {}

    content = f"""# Reflection Analysis

## Session Context
- **Date**: {timestamp}
- **Project**: {get_project_name()}
- **Messages Analyzed**: {context.get('message_count', 'N/A')}
- **Focus**: {context.get('focus', 'All agents')}
- **Trigger**: {context.get('trigger', 'Manual')}

## Signals Detected

| # | Signal | Confidence | Source Quote | Category |
|---|--------|------------|--------------|----------|
"""

    # Add signals table
    for i, signal in enumerate(signals, 1):
        content += f"| {i} | {signal.get('signal', '')} | {signal.get('confidence', '')} | \"{signal.get('source_quote', '')}\" | {signal.get('category', '')} |\n"

    if not signals:
        content += "| - | No signals detected | - | - | - |\n"

    # Add agent updates section
    if agent_updates:
        content += "\n## Proposed Agent Updates\n\n"
        for i, update in enumerate(agent_updates, 1):
            content += f"""### Change {i}: Update {update.get('agent_name', 'Unknown')}

**Target**: `{update.get('file_path', '')}`
**Section**: {update.get('section', 'Unknown')}
**Confidence**: {update.get('confidence', 'Unknown')}
**Rationale**: {update.get('rationale', '')}

```diff
{update.get('diff', '')}
```

"""

    # Add new skills section
    if new_skills:
        content += "\n## Proposed New Skills\n\n"
        for i, skill in enumerate(new_skills, 1):
            content += f"""### Skill {i}: {skill.get('name', 'Unknown')}

**Quality Gate Check**:
- [{'x' if skill.get('reusable') else ' '}] Reusable: {skill.get('reusable_reason', '')}
- [{'x' if skill.get('nontrivial') else ' '}] Non-trivial: {skill.get('nontrivial_reason', '')}
- [{'x' if skill.get('specific') else ' '}] Specific: {skill.get('specific_reason', '')}
- [{'x' if skill.get('verified') else ' '}] Verified: {skill.get('verified_reason', '')}
- [{'x' if skill.get('no_duplication') else ' '}] No duplication: {skill.get('nodupe_reason', '')}

**Will create**: `.claude/skills/{skill.get('name', 'unknown')}/SKILL.md`

"""

    # Add summary
    high_count = sum(1 for s in signals if s.get('confidence') == 'HIGH')
    medium_count = sum(1 for s in signals if s.get('confidence') == 'MEDIUM')
    low_count = sum(1 for s in signals if s.get('confidence') == 'LOW')

    content += f"""
## Summary

- **Total Signals**: {len(signals)} ({high_count} high, {medium_count} medium, {low_count} low)
- **Agent Updates**: {len(agent_updates)} proposed
- **New Skills**: {len(new_skills)} proposed
- **Status**: Pending review

---
*Generated by reflect skill*
"""

    filepath.write_text(content)
    return filepath


def update_project_index(reflection_file: Path, signals: list, new_skills: list):
    """Update the project's reflection index."""
    index_path = get_project_reflections_dir() / 'index.md'

    # Create or read existing index
    if index_path.exists():
        existing_content = index_path.read_text()
    else:
        existing_content = f"""# Reflection Index - {get_project_name()}

This file tracks all reflection analyses for this project.

---

"""

    # Generate entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    high_count = sum(1 for s in signals if s.get('confidence') == 'HIGH')
    medium_count = sum(1 for s in signals if s.get('confidence') == 'MEDIUM')
    low_count = sum(1 for s in signals if s.get('confidence') == 'LOW')

    skill_names = [s.get('name', 'unknown') for s in new_skills] if new_skills else []

    entry = f"""## {timestamp}

- **File**: [{reflection_file.name}](./{reflection_file.name})
- **Signals**: {len(signals)} detected ({high_count} high, {medium_count} medium, {low_count} low)
- **New Skills**: {', '.join(skill_names) if skill_names else 'None'}
- **Key Learnings**: [Brief summary]

"""

    # Append entry after header
    updated_content = existing_content + entry
    index_path.write_text(updated_content)


def update_global_index(reflection_file: Path, signals: list, new_skills: list):
    """Update the global reflection index."""
    ensure_directories()
    index_path = get_global_reflections_dir() / 'index.md'

    # Create or read existing index
    if index_path.exists():
        existing_content = index_path.read_text()
    else:
        existing_content = """# Global Reflection Index

This file tracks all reflection analyses across all projects.

---

"""

    # Generate entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    project_name = get_project_name()
    project_path = get_project_dir()

    skill_names = [s.get('name', 'unknown') for s in new_skills] if new_skills else []

    entry = f"""## {timestamp} - {project_name}

- **Project Path**: `{project_path}`
- **Reflection**: `{project_path}/.claude/reflections/{reflection_file.name}`
- **Signals**: {len(signals)} detected
- **New Skills**: {', '.join(skill_names) if skill_names else 'None'}

"""

    # Append entry
    updated_content = existing_content + entry
    index_path.write_text(updated_content)


def update_agent_learnings(agent_name: str, learning: dict):
    """Update per-agent learnings file."""
    ensure_directories()

    agent_dir = get_global_reflections_dir() / 'by-agent' / agent_name
    agent_dir.mkdir(parents=True, exist_ok=True)

    learnings_path = agent_dir / 'learnings.md'

    # Create or read existing
    if learnings_path.exists():
        existing_content = learnings_path.read_text()
    else:
        existing_content = f"""# Learnings for {agent_name}

Accumulated learnings from reflection analyses targeting this agent.

---

"""

    # Generate entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    entry = f"""## {timestamp} - {learning.get('signal', 'Unknown')}

- **Source Project**: {get_project_name()}
- **Confidence**: {learning.get('confidence', 'Unknown')}
- **Source Quote**: "{learning.get('source_quote', '')}"
- **Proposed Addition**: {learning.get('proposed_addition', '')}
- **Status**: {learning.get('status', 'Pending review')}

"""

    updated_content = existing_content + entry
    learnings_path.write_text(updated_content)


def copy_to_by_project(reflection_file: Path):
    """Copy reflection to global by-project directory."""
    ensure_directories()

    project_name = get_project_name()
    by_project_dir = get_global_reflections_dir() / 'by-project' / project_name
    by_project_dir.mkdir(parents=True, exist_ok=True)

    dest_path = by_project_dir / reflection_file.name
    shutil.copy2(reflection_file, dest_path)


def create_skill_file(skill_name: str, skill_content: str) -> Path:
    """Create a new skill file in the project's .claude/skills/ directory."""
    ensure_directories()

    skill_dir = get_project_skills_dir() / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    skill_path = skill_dir / 'SKILL.md'
    skill_path.write_text(skill_content)

    return skill_path


def generate_full_reflection(
    signals: list,
    agent_updates: list,
    new_skills: list,
    session_context: Optional[dict] = None,
    update_indexes: bool = True
) -> dict:
    """
    Generate a complete reflection with all outputs.

    Returns dict with paths to all created files.
    """
    result = {
        'reflection_file': None,
        'skills_created': [],
        'indexes_updated': [],
        'agent_learnings_updated': []
    }

    # Create main reflection file
    reflection_file = create_reflection_file(
        signals=signals,
        agent_updates=agent_updates,
        new_skills=new_skills,
        session_context=session_context
    )
    result['reflection_file'] = str(reflection_file)

    if update_indexes:
        # Update project index
        update_project_index(reflection_file, signals, new_skills)
        result['indexes_updated'].append(str(get_project_reflections_dir() / 'index.md'))

        # Update global index
        update_global_index(reflection_file, signals, new_skills)
        result['indexes_updated'].append(str(get_global_reflections_dir() / 'index.md'))

        # Copy to by-project
        copy_to_by_project(reflection_file)

        # Update per-agent learnings for HIGH confidence signals
        for update in agent_updates:
            if update.get('confidence') == 'HIGH':
                agent_name = update.get('agent_name', '').replace('.md', '')
                if agent_name:
                    update_agent_learnings(agent_name, {
                        'signal': update.get('summary', ''),
                        'confidence': update.get('confidence'),
                        'source_quote': update.get('source_quote', ''),
                        'proposed_addition': update.get('diff', ''),
                        'status': 'Pending review'
                    })
                    result['agent_learnings_updated'].append(agent_name)

    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Generate reflection outputs')
    parser.add_argument('--reflection-data', type=str,
                       help='JSON string with reflection data (signals, changes, skills)')
    parser.add_argument('--create-skill', type=str,
                       help='Create a new skill with this name')
    parser.add_argument('--content', type=str,
                       help='Content for skill file')
    parser.add_argument('--update-indexes', action='store_true',
                       help='Update all index files')
    parser.add_argument('--show-paths', action='store_true',
                       help='Show all output paths')
    parser.add_argument('--json', action='store_true',
                       help='Output as JSON')

    args = parser.parse_args()

    if args.show_paths:
        paths = {
            'project_reflections': str(get_project_reflections_dir()),
            'project_skills': str(get_project_skills_dir()),
            'global_reflections': str(get_global_reflections_dir()),
            'global_by_agent': str(get_global_reflections_dir() / 'by-agent'),
            'global_by_project': str(get_global_reflections_dir() / 'by-project'),
        }
        if args.json:
            print(json.dumps(paths, indent=2))
        else:
            print("\n=== Output Paths ===\n")
            for key, path in paths.items():
                print(f"{key}: {path}")
        return

    if args.create_skill:
        if not args.content:
            print("Error: --content required when creating a skill", file=sys.stderr)
            sys.exit(1)

        skill_path = create_skill_file(args.create_skill, args.content)
        if args.json:
            print(json.dumps({'skill_path': str(skill_path)}))
        else:
            print(f"Created skill at: {skill_path}")
        return

    if args.reflection_data:
        try:
            data = json.loads(args.reflection_data)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}", file=sys.stderr)
            sys.exit(1)

        result = generate_full_reflection(
            signals=data.get('signals', []),
            agent_updates=data.get('agent_updates', []),
            new_skills=data.get('new_skills', []),
            session_context=data.get('session_context'),
            update_indexes=True
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n=== Reflection Generated ===\n")
            print(f"Reflection file: {result['reflection_file']}")
            print(f"Indexes updated: {len(result['indexes_updated'])}")
            print(f"Agent learnings: {len(result['agent_learnings_updated'])}")
        return

    if args.update_indexes:
        ensure_directories()
        print("Directories ensured. Run with --reflection-data to generate outputs.")
        return

    parser.print_help()


if __name__ == '__main__':
    main()
