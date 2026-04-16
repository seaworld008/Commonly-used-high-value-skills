#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/hermes-auto-continue-config.sh"

python3 - <<'PY' "$HERMES_AUTO_CONTINUE_TASK_BOARD_FILE"
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

board_path = Path(sys.argv[1])
if not board_path.exists():
    print(f"missing={board_path}")
    raise SystemExit(1)

data = json.loads(board_path.read_text(encoding="utf-8"))
tasks = data.get("tasks", [])
counts = Counter(task.get("status", "unknown") for task in tasks)
done_ids = {task.get("id") for task in tasks if task.get("status") == "done"}
in_progress = [task for task in tasks if task.get("status") == "in_progress"]

def priority_rank(value: str) -> int:
    return {"p0": 0, "p1": 1, "p2": 2, "p3": 3}.get(str(value).lower(), 9)

def deps_satisfied(task: dict) -> bool:
    deps = task.get("depends_on") or []
    return all(dep in done_ids for dep in deps)

candidate = None
if in_progress:
    candidate = in_progress[0]
else:
    todos = [t for t in tasks if t.get("status") == "todo" and deps_satisfied(t)]
    todos.sort(key=lambda t: (priority_rank(t.get("priority", "p9")), t.get("id", "")))
    if todos:
        candidate = todos[0]

print(f"board={board_path}")
print(f"project={data.get('project', 'unknown')}")
print(f"updated_at={data.get('updated_at', 'unknown')}")
for key in ("todo", "in_progress", "blocked", "done", "dropped"):
    print(f"{key}={counts.get(key, 0)}")
if in_progress:
    current = in_progress[0]
    print(f"current_id={current.get('id', 'unknown')}")
    print(f"current_status={current.get('status', 'unknown')}")
    print(f"current_priority={current.get('priority', 'unknown')}")
    print(f"current_title={current.get('title', '')}")
else:
    print("current_id=")
    print("current_status=")
    print("current_priority=")
    print("current_title=")
if candidate:
    print(f"next_id={candidate.get('id', 'unknown')}")
    print(f"next_status={candidate.get('status', 'unknown')}")
    print(f"next_priority={candidate.get('priority', 'unknown')}")
    print(f"next_title={candidate.get('title', '')}")
else:
    print("next_id=")
    print("next_status=")
    print("next_priority=")
    print("next_title=")

ready_to_complete = []
for task in tasks:
    status = task.get("status")
    if status != "in_progress":
        continue
    deps = task.get("depends_on") or []
    acceptance = task.get("acceptance") or []
    artifacts = task.get("artifacts") or []
    blocked_by = task.get("blocked_by") or ""
    if blocked_by:
        continue
    if deps and not all(dep in done_ids for dep in deps):
        continue
    if not acceptance:
        continue
    artifact_missing = False
    for artifact in artifacts:
        if not artifact:
            continue
        path = Path(artifact)
        if not path.is_absolute():
            path = (board_path.parent.parent / artifact).resolve()
        if not path.exists():
            artifact_missing = True
            break
    if artifact_missing:
        continue
    ready_to_complete.append(task.get("id", "unknown"))

print(f"ready_to_complete={','.join(ready_to_complete)}")
PY
