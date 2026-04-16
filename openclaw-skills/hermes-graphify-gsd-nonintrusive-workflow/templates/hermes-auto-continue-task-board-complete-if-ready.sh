#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/hermes-auto-continue-config.sh"

python3 - <<'PY' "$HERMES_AUTO_CONTINUE_TASK_BOARD_FILE" "$@"
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

board_path = Path(sys.argv[1])
args = sys.argv[2:]

if not board_path.exists():
    print(f"missing={board_path}")
    raise SystemExit(1)

task_id = args[0] if args else ""
note = args[1] if len(args) > 1 else "Complete-if-ready gate passed"

data = json.loads(board_path.read_text(encoding="utf-8"))
tasks = data.get("tasks", [])


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat()


def save() -> None:
    data["updated_at"] = now()
    board_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def done_ids() -> set[str]:
    return {task.get("id") for task in tasks if task.get("status") == "done"}


def find_task(task_id: str) -> dict | None:
    for task in tasks:
        if task.get("id") == task_id:
            return task
    return None


def current_in_progress() -> dict | None:
    for task in tasks:
        if task.get("status") == "in_progress":
            return task
    return None


def record(task: dict, action: str, note: str = "") -> None:
    history = task.setdefault("history", [])
    if not isinstance(history, list):
        task["history"] = []
        history = task["history"]
    history.append(
        {
            "time": now(),
            "action": action,
            "note": note,
        }
    )
    task["last_updated"] = now()


task = find_task(task_id) if task_id else current_in_progress()
if task is None:
    print("task_id=")
    print("ready=no")
    print("reason=no_task_selected")
    raise SystemExit(2)

task_id = task.get("id", "")
status = task.get("status", "")
deps = task.get("depends_on") or []
acceptance = task.get("acceptance") or []
artifacts = task.get("artifacts") or []
blocked_by = task.get("blocked_by") or ""

reasons: list[str] = []
missing_deps = [dep for dep in deps if dep not in done_ids()]
if missing_deps:
    reasons.append(f"missing_dependencies:{','.join(missing_deps)}")

if status not in {"in_progress", "todo", "blocked"}:
    reasons.append(f"invalid_status:{status}")

if blocked_by:
    reasons.append("blocked_by_present")

if not acceptance:
    reasons.append("missing_acceptance")

missing_artifacts = []
for artifact in artifacts:
    if not artifact:
        continue
    if not Path(artifact).is_absolute():
        artifact_path = (board_path.parent.parent / artifact).resolve()
    else:
        artifact_path = Path(artifact)
    if not artifact_path.exists():
        missing_artifacts.append(str(artifact))
if missing_artifacts:
    reasons.append(f"missing_artifacts:{','.join(missing_artifacts)}")

if reasons:
    print(f"task_id={task_id}")
    print("ready=no")
    print(f"reason={'|'.join(reasons)}")
    record(task, "evaluate-not-ready", "|".join(reasons))
    save()
    raise SystemExit(2)

task["status"] = "done"
task["blocked_by"] = ""
task["completed_at"] = now()
record(task, "complete-if-ready", note)
save()
print(f"task_id={task_id}")
print("ready=yes")
print("status=done")
raise SystemExit(0)
PY
