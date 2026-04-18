#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/hermes-auto-continue-config.sh"

python3 - <<'PY' "$HERMES_AUTO_CONTINUE_TASK_BOARD_FILE" "$ROOT/.planning/STATE.md" "$ROOT/.planning/ROADMAP.md" "$HERMES_GSD_NEXT_STATE_FILE"
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

board_path = Path(sys.argv[1])
state_path = Path(sys.argv[2])
roadmap_path = Path(sys.argv[3])
gsd_state_path = Path(sys.argv[4])

if not board_path.exists():
    print(f"missing={board_path}")
    raise SystemExit(1)

data = json.loads(board_path.read_text(encoding="utf-8"))
tasks = data.get("tasks", [])
counts = Counter(task.get("status", "unknown") for task in tasks)
try:
    gsd_state = json.loads(gsd_state_path.read_text(encoding="utf-8"))
except Exception:
    gsd_state = {}

current = next((task for task in tasks if task.get("status") == "in_progress"), None)
blocked = [task for task in tasks if task.get("status") == "blocked"]

done_ids = {task.get("id") for task in tasks if task.get("status") == "done"}


def priority_rank(value: str) -> int:
    return {"p0": 0, "p1": 1, "p2": 2, "p3": 3}.get(str(value).lower(), 9)


def deps_satisfied(task: dict) -> bool:
    deps = task.get("depends_on") or []
    return all(dep in done_ids for dep in deps)


next_task = None
if not current:
    todos = [task for task in tasks if task.get("status") == "todo" and deps_satisfied(task)]
    todos.sort(key=lambda task: (priority_rank(task.get("priority", "p9")), task.get("id", "")))
    if todos:
        next_task = todos[0]


def task_line(task: dict) -> str:
    priority = task.get("priority", "p?")
    return f"- `{task.get('id','')}` [{priority}] {task.get('title','')}"


state_lines = [
    "## Runtime Task Board Mirror",
    "",
    "<!-- AUTO-TASK-BOARD-STATE:START -->",
    f"- Updated from task board: `{data.get('updated_at', 'unknown')}`",
    f"- Todo: `{counts.get('todo', 0)}`",
    f"- In progress: `{counts.get('in_progress', 0)}`",
    f"- Blocked: `{counts.get('blocked', 0)}`",
    f"- Done: `{counts.get('done', 0)}`",
]

if current:
    state_lines.extend(
        [
            f"- Current task: `{current.get('id','')}`",
            f"- Current title: {current.get('title','')}",
            f"- Current priority: `{current.get('priority','unknown')}`",
        ]
    )
else:
    state_lines.append("- Current task: none")

if next_task:
    state_lines.extend(
        [
            f"- Next task: `{next_task.get('id','')}`",
            f"- Next title: {next_task.get('title','')}",
            f"- Next priority: `{next_task.get('priority','unknown')}`",
        ]
    )
else:
    state_lines.append("- Next task: none")

if blocked:
    state_lines.append("- Blocked tasks:")
    state_lines.extend([f"  {task_line(task)}" for task in blocked[:5]])
else:
    state_lines.append("- Blocked tasks: none")

if gsd_state:
    state_lines.extend(
        [
            f"- GSD current phase: `{gsd_state.get('current_phase', '')}`",
            f"- GSD current phase name: {gsd_state.get('current_phase_name', '')}",
            f"- GSD next step: `{gsd_state.get('gsd_next_step', '')}`",
            f"- GSD next command: `{gsd_state.get('gsd_next_command', '')}`",
            f"- GSD next reason: `{gsd_state.get('gsd_next_reason', '')}`",
        ]
    )

state_lines.extend(["<!-- AUTO-TASK-BOARD-STATE:END -->", ""])


roadmap_lines = [
    "## Task Board Snapshot",
    "",
    "<!-- AUTO-TASK-BOARD-ROADMAP:START -->",
]

if current:
    roadmap_lines.extend(["### Current", task_line(current), ""])

if next_task:
    roadmap_lines.extend(["### Next", task_line(next_task), ""])

if gsd_state:
    roadmap_lines.extend(
        [
            "### GSD Lifecycle",
            f"- Current phase: `{gsd_state.get('current_phase', '')}` — {gsd_state.get('current_phase_name', '')}",
            f"- Next step: `{gsd_state.get('gsd_next_step', '')}`",
            f"- Next command: `{gsd_state.get('gsd_next_command', '')}`",
            f"- Reason: `{gsd_state.get('gsd_next_reason', '')}`",
            "",
        ]
    )

pending = [task for task in tasks if task.get("status") == "todo"]
pending.sort(key=lambda task: (priority_rank(task.get("priority", "p9")), task.get("id", "")))
if pending:
    roadmap_lines.append("### Upcoming")
    roadmap_lines.extend([task_line(task) for task in pending[:10]])
    roadmap_lines.append("")

if blocked:
    roadmap_lines.append("### Blocked")
    roadmap_lines.extend(
        [
            f"{task_line(task)} -- blocked_by: {task.get('blocked_by','') or 'n/a'}"
            for task in blocked[:10]
        ]
    )
    roadmap_lines.append("")

done_recent = [task for task in tasks if task.get("status") == "done"]
done_recent.sort(key=lambda task: task.get("completed_at", ""), reverse=True)
if done_recent:
    roadmap_lines.append("### Recently Done")
    roadmap_lines.extend([task_line(task) for task in done_recent[:10]])
    roadmap_lines.append("")

roadmap_lines.extend(["<!-- AUTO-TASK-BOARD-ROADMAP:END -->", ""])


def upsert_managed_section(path: Path, start_marker: str, end_marker: str, replacement_lines: list[str], title: str) -> None:
    replacement = "\n".join(replacement_lines).rstrip() + "\n"
    original = path.read_text(encoding="utf-8") if path.exists() else f"# {title}\n\n"
    pattern = re.compile(
        rf"{re.escape(start_marker)}.*?{re.escape(end_marker)}\n?",
        re.DOTALL,
    )
    if pattern.search(original):
        updated = pattern.sub(replacement, original)
    else:
        if not original.endswith("\n"):
            original += "\n"
        updated = original + "\n" + replacement
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8")


upsert_managed_section(
    state_path,
    "<!-- AUTO-TASK-BOARD-STATE:START -->",
    "<!-- AUTO-TASK-BOARD-STATE:END -->",
    state_lines,
    "State",
)
upsert_managed_section(
    roadmap_path,
    "<!-- AUTO-TASK-BOARD-ROADMAP:START -->",
    "<!-- AUTO-TASK-BOARD-ROADMAP:END -->",
    roadmap_lines,
    "Roadmap",
)

print(state_path)
print(roadmap_path)
PY
