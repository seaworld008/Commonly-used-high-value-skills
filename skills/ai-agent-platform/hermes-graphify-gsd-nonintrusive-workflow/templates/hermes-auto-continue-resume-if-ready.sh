#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/hermes-auto-continue-config.sh"
hermes_auto_continue_ensure_dirs

writer_status="$(hermes_auto_continue_writer_surface_status)"
writer_recommended="$(printf '%s\n' "$writer_status" | awk -F= '$1=="writer_recommended"{print $2}')"

repo_lock_free="no"
exec 9>"$HERMES_AUTO_CONTINUE_REPO_LOCK"
if flock -n 9; then
  repo_lock_free="yes"
fi

project_lock_free="no"
exec 8>"$HERMES_AUTO_CONTINUE_PROJECT_LOCK"
if flock -n 8; then
  project_lock_free="yes"
fi

set +e
python3 - <<'PY' "$ROOT" "$HERMES_AUTO_CONTINUE_HANDOFF_FILE" "$HERMES_AUTO_CONTINUE_BLOCKED_FILE" "$HERMES_AUTO_CONTINUE_STATE_FILE" "$HERMES_AUTO_CONTINUE_PLANNING_MIRROR" "$HERMES_AUTO_CONTINUE_TASK_BOARD_FILE" "$writer_recommended" "$repo_lock_free" "$project_lock_free"
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
handoff_path = Path(sys.argv[2])
blocked_path = Path(sys.argv[3])
state_path = Path(sys.argv[4])
mirror_path = Path(sys.argv[5])
board_path = Path(sys.argv[6])
writer_recommended = sys.argv[7] == "yes"
repo_lock_free = sys.argv[8] == "yes"
project_lock_free = sys.argv[9] == "yes"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat()


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_state(state: str, reason: str, detail: str) -> None:
    payload = {
        "time": now(),
        "state": state,
        "reason": reason,
        "detail": detail,
        "repo_root": str(root),
    }
    for path in (state_path, mirror_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def task_board() -> dict:
    return load_json(board_path) if board_path.exists() else {}


def find_task(task_id: str) -> dict | None:
    for task in task_board().get("tasks", []):
        if task.get("id") == task_id:
            return task
    return None


def done_ids() -> set[str]:
    return {task.get("id") for task in task_board().get("tasks", []) if task.get("status") == "done"}


def ready_to_complete(task_id: str) -> bool:
    task = find_task(task_id)
    if not task:
        return False
    deps = task.get("depends_on") or []
    acceptance = task.get("acceptance") or []
    artifacts = task.get("artifacts") or []
    blocked_by = task.get("blocked_by") or ""
    if blocked_by:
        return False
    if deps and not all(dep in done_ids() for dep in deps):
        return False
    if not acceptance:
        return False
    for artifact in artifacts:
        if not artifact:
            continue
        path = Path(artifact)
        if not path.is_absolute():
            path = (board_path.parent.parent / artifact).resolve()
        if not path.exists():
            return False
    return True


def board_has_next_task() -> bool:
    tasks = task_board().get("tasks", [])
    in_progress = next((task for task in tasks if task.get("status") == "in_progress"), None)
    if in_progress:
        return True
    for task in tasks:
        if task.get("status") == "todo":
            deps = task.get("depends_on") or []
            if all(dep in done_ids() for dep in deps):
                return True
    return False


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (root / value).resolve()


def eval_probe(token: str) -> bool:
    token = token.strip()
    if not token:
        return True
    if token == "writer_recommended":
        return writer_recommended
    if token == "repo_lock_free":
        return repo_lock_free
    if token == "project_lock_free":
        return project_lock_free
    if token == "board_has_next_task":
        return board_has_next_task()
    if token.startswith("file_exists:"):
        return resolve_path(token.split(":", 1)[1]).exists()
    if token.startswith("file_missing:"):
        return not resolve_path(token.split(":", 1)[1]).exists()
    if token.startswith("task_done:"):
        task_id = token.split(":", 1)[1]
        task = find_task(task_id)
        return bool(task and task.get("status") == "done")
    if token.startswith("task_status:"):
        _, task_id, expected = token.split(":", 2)
        task = find_task(task_id)
        return bool(task and task.get("status") == expected)
    if token.startswith("ready_to_complete:"):
        task_id = token.split(":", 1)[1]
        return ready_to_complete(task_id)
    return False


def eval_condition(expr: str) -> bool:
    parts = [part.strip() for part in expr.split("&&")]
    return all(eval_probe(part) for part in parts if part.strip())


handoff = load_json(handoff_path) if handoff_path.exists() else {}
blocked = load_json(blocked_path) if blocked_path.exists() else {}

if handoff:
    resume_condition = str(handoff.get("resume_condition", "")).strip()
    if resume_condition and eval_condition(resume_condition):
        handoff_path.unlink(missing_ok=True)
        blocked_path.unlink(missing_ok=True)
        write_state("inactive", "resume_condition_satisfied", resume_condition)
        print("resume_ready=yes")
        print("cleared=handoff")
        raise SystemExit(0)
    print("resume_ready=no")
    print("reason=handoff_not_ready")
    raise SystemExit(2)

if blocked:
    reason = blocked.get("reason", "")
    if reason == "writer_surface_not_recommended" and writer_recommended:
        blocked_path.unlink(missing_ok=True)
        write_state("inactive", "writer_surface_recovered", "writer_recommended=yes")
        print("resume_ready=yes")
        print("cleared=blocked")
        raise SystemExit(0)
    if reason in {"repo_lock_busy", "global_writer_busy"} and repo_lock_free and project_lock_free:
        blocked_path.unlink(missing_ok=True)
        write_state("inactive", "locks_recovered", reason)
        print("resume_ready=yes")
        print("cleared=blocked")
        raise SystemExit(0)
    print("resume_ready=no")
    print("reason=blocked_not_ready")
    raise SystemExit(2)

print("resume_ready=no")
print("reason=no_handoff_or_blocked")
raise SystemExit(2)
PY

resume_exit=$?
set -e
if [ "$resume_exit" -eq 0 ] && [ -x "$ROOT/scripts/hermes-auto-continue-notify.sh" ]; then
  bash "$ROOT/scripts/hermes-auto-continue-notify.sh" resume "auto-resume" "A blocked or handoff state was cleared because its resume condition is now satisfied." >/dev/null 2>&1 || true
fi
exit "$resume_exit"
