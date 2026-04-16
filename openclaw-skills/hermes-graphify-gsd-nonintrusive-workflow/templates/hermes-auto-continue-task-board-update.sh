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

if not args:
    print("usage=claim-next|set-status <id> <status> [note]|append-note <id> <note>|append-acceptance <id> <text>")
    raise SystemExit(1)

data = json.loads(board_path.read_text(encoding="utf-8"))
tasks = data.get("tasks", [])
command = args[0]


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat()


def save() -> None:
    data["updated_at"] = now()
    board_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_task(task_id: str) -> dict:
    for task in tasks:
        if task.get("id") == task_id:
            return task
    raise SystemExit(f"missing_task={task_id}")


def ensure_history(task: dict) -> list:
    history = task.setdefault("history", [])
    if not isinstance(history, list):
        task["history"] = []
    return task["history"]


def record(task: dict, action: str, note: str = "") -> None:
    ensure_history(task).append(
        {
            "time": now(),
            "action": action,
            "note": note,
        }
    )
    task["last_updated"] = now()


def priority_rank(value: str) -> int:
    return {"p0": 0, "p1": 1, "p2": 2, "p3": 3}.get(str(value).lower(), 9)


def done_ids() -> set[str]:
    return {task.get("id") for task in tasks if task.get("status") == "done"}


def deps_satisfied(task: dict) -> bool:
    deps = task.get("depends_on") or []
    return all(dep in done_ids() for dep in deps)


def current_in_progress() -> dict | None:
    for task in tasks:
        if task.get("status") == "in_progress":
            return task
    return None


def claim_next() -> int:
    current = current_in_progress()
    if current:
        print(f"task_id={current.get('id','')}")
        print(f"status={current.get('status','')}")
        print(f"title={current.get('title','')}")
        return 0

    candidates = [task for task in tasks if task.get("status") == "todo" and deps_satisfied(task)]
    candidates.sort(key=lambda task: (priority_rank(task.get("priority", "p9")), task.get("id", "")))
    if not candidates:
        print("task_id=")
        print("status=")
        print("title=")
        return 2

    task = candidates[0]
    task["status"] = "in_progress"
    task["blocked_by"] = ""
    record(task, "claim-next", "Automatically claimed next executable task")
    save()
    print(f"task_id={task.get('id','')}")
    print(f"status={task.get('status','')}")
    print(f"title={task.get('title','')}")
    return 0


if command == "claim-next":
    raise SystemExit(claim_next())

if command == "set-status":
    if len(args) < 3:
        print("usage=set-status <task_id> <status> [note]")
        raise SystemExit(1)
    task_id = args[1]
    new_status = args[2]
    note = args[3] if len(args) > 3 else ""
    valid = {"todo", "in_progress", "blocked", "done", "dropped"}
    if new_status not in valid:
        print(f"invalid_status={new_status}")
        raise SystemExit(1)
    task = find_task(task_id)
    other = current_in_progress()
    if new_status == "in_progress" and other and other.get("id") != task_id:
        print(f"another_in_progress={other.get('id','')}")
        raise SystemExit(2)
    task["status"] = new_status
    if new_status != "blocked":
        task["blocked_by"] = ""
    elif note:
        task["blocked_by"] = note
    record(task, f"set-status:{new_status}", note)
    save()
    print(f"task_id={task.get('id','')}")
    print(f"status={task.get('status','')}")
    raise SystemExit(0)

if command == "append-note":
    if len(args) < 3:
        print("usage=append-note <task_id> <note>")
        raise SystemExit(1)
    task = find_task(args[1])
    note = args[2]
    existing = task.get("notes", "")
    task["notes"] = (existing + "\n" + note).strip() if existing else note
    record(task, "append-note", note)
    save()
    print(f"task_id={task.get('id','')}")
    print("note_appended=yes")
    raise SystemExit(0)

if command == "append-acceptance":
    if len(args) < 3:
        print("usage=append-acceptance <task_id> <text>")
        raise SystemExit(1)
    task = find_task(args[1])
    text = args[2]
    acceptance = task.setdefault("acceptance", [])
    if text not in acceptance:
        acceptance.append(text)
    record(task, "append-acceptance", text)
    save()
    print(f"task_id={task.get('id','')}")
    print("acceptance_appended=yes")
    raise SystemExit(0)

print(f"unknown_command={command}")
raise SystemExit(1)
PY
