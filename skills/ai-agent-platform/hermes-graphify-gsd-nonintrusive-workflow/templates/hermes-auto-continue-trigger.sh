#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/hermes-auto-continue-config.sh"
STATUS_SCRIPT="$ROOT/scripts/hermes-auto-continue-status.sh"
SUMMARY_SCRIPT="$ROOT/scripts/hermes-auto-continue-summary.sh"
INSTALL_SCRIPT="$ROOT/scripts/install-hermes-auto-continue-cron.sh"
hermes_auto_continue_ensure_dirs
cd "$ROOT"

export PATH="${HOME}/.local/bin:${HOME}/.hermes/node/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"
source_name="${1:-manual}"
writer_status="$(hermes_auto_continue_writer_surface_status)"
writer_recommended="$(printf '%s\n' "$writer_status" | awk -F= '$1=="writer_recommended"{print $2}')"
execution_surface="$(printf '%s\n' "$writer_status" | awk -F= '$1=="execution_surface"{print $2}')"
current_head="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
branch_name="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
max_passes="${HERMES_AUTO_CONTINUE_MAX_PASSES_PER_TRIGGER:-4}"
pass_idle_seconds="${HERMES_AUTO_CONTINUE_PASS_IDLE_SECONDS:-5}"
requirements_rel="${HERMES_AUTO_CONTINUE_REQUIREMENTS_FILE#$ROOT/}"
tasks_rel="${HERMES_AUTO_CONTINUE_TASKS_FILE#$ROOT/}"
task_board_rel="${HERMES_AUTO_CONTINUE_TASK_BOARD_FILE#$ROOT/}"

write_json_state() {
  local path="$1"
  local payload="$2"
  python3 - <<'PY' "$path" "$payload"
from pathlib import Path
import json, sys
Path(sys.argv[1]).write_text(json.dumps(json.loads(sys.argv[2]), ensure_ascii=False, indent=2) + "\n")
PY
}

mk_payload() {
  python3 - <<'PY' "$1" "$2" "$3" "$ROOT" "$source_name" "$branch_name" "$current_head"
import json, sys, datetime
print(json.dumps({
  'time': datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
  'state': sys.argv[1],
  'reason': sys.argv[2],
  'detail': sys.argv[3],
  'repo_root': sys.argv[4],
  'source': sys.argv[5],
  'branch': sys.argv[6],
  'head': sys.argv[7],
}))
PY
}

write_runtime_state() {
  local state="$1" reason="$2" detail="$3"
  local payload
  payload="$(mk_payload "$state" "$reason" "$detail")"
  write_json_state "$HERMES_AUTO_CONTINUE_STATE_FILE" "$payload"
  write_json_state "$HERMES_AUTO_CONTINUE_PLANNING_MIRROR" "$payload"
}

write_lease_state() {
  local active="$1" detail="$2"
  local payload
  payload="$(python3 - <<'PY' "$active" "$detail" "$ROOT" "$source_name" "$branch_name" "$current_head"
import json, sys, datetime
print(json.dumps({
  'time': datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
  'active': sys.argv[1] == 'true',
  'detail': sys.argv[2],
  'holder_repo': sys.argv[3],
  'source': sys.argv[4],
  'branch': sys.argv[5],
  'head': sys.argv[6],
}))
PY
)"
  write_json_state "$HERMES_AUTO_CONTINUE_LEASE_FILE" "$payload"
}

write_blocked() {
  local reason="$1" detail="$2"
  local payload
  payload="$(python3 - <<'PY' "$reason" "$detail" "$ROOT" "$source_name" "$branch_name" "$current_head" "$writer_status"
import json, sys, datetime
writer = dict(line.split('=', 1) for line in sys.argv[7].splitlines() if '=' in line)
print(json.dumps({
  'time': datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
  'project_key': writer.get('project_key'),
  'repo_root': sys.argv[3],
  'source': sys.argv[4],
  'branch': sys.argv[5],
  'head': sys.argv[6],
  'reason': sys.argv[1],
  'detail': sys.argv[2],
  'writer_status': writer,
}))
PY
)"
  write_json_state "$HERMES_AUTO_CONTINUE_BLOCKED_FILE" "$payload"
  write_runtime_state blocked "$reason" "$detail"
  bash "$SUMMARY_SCRIPT" >/dev/null 2>&1 || true
}

clear_blocked() {
  rm -f "$HERMES_AUTO_CONTINUE_BLOCKED_FILE"
}

handoff_active() {
  [ -s "$HERMES_AUTO_CONTINUE_HANDOFF_FILE" ]
}

if [ "$writer_recommended" != "yes" ] && [ "${HERMES_AUTO_CONTINUE_ALLOW_INCOMPLETE_ROOT:-0}" != "1" ]; then
  write_blocked writer_surface_not_recommended "execution_surface=$execution_surface"
  echo "[auto-continue] refusing to run on non-recommended writer surface"
  exit 2
fi

exec 9>"$HERMES_AUTO_CONTINUE_REPO_LOCK"
if ! flock -n 9; then
  write_blocked repo_lock_busy "repo-local runner already active"
  echo "[auto-continue] another repo-local run is in progress; skipping"
  exit 0
fi

status_line="$(bash "$STATUS_SCRIPT")"
echo "[auto-continue] source=$source_name status=$status_line"
if [[ "$status_line" == COMPLETE* ]]; then
  bash "$INSTALL_SCRIPT" uninstall >/dev/null 2>&1 || true
  write_runtime_state complete sentinel_valid "$status_line"
  write_lease_state false "completion already reached"
  bash "$SUMMARY_SCRIPT" >/dev/null 2>&1 || true
  echo "[auto-continue] project complete; cron removed"
  exit 0
fi

if handoff_active; then
  write_runtime_state handoff waiting_for_input "handoff file present before new run"
  write_lease_state false "handoff active"
  bash "$SUMMARY_SCRIPT" >/dev/null 2>&1 || true
  echo "[auto-continue] handoff already active; waiting for input"
  exit 0
fi

exec 8>"$HERMES_AUTO_CONTINUE_PROJECT_LOCK"
if ! flock -n 8; then
  holder_detail="$(python3 - <<'PY' "$HERMES_AUTO_CONTINUE_LEASE_FILE"
from pathlib import Path
import json, sys
p = Path(sys.argv[1])
if not p.exists():
    print('lease_file_missing')
else:
    try:
        data = json.loads(p.read_text())
        print(data.get('holder_repo', 'unknown'))
    except Exception as exc:
        print(f'invalid_lease:{exc}')
PY
)"
  write_blocked global_writer_busy "$holder_detail"
  echo "[auto-continue] project-level writer lock busy; skipping"
  exit 0
fi

pass_no=1
while [ "$pass_no" -le "$max_passes" ]; do
  clear_blocked
  write_lease_state true "writer lease acquired (pass $pass_no/$max_passes)"
  write_runtime_state running started "auto-continue pass $pass_no/$max_passes started"
  bash "$SUMMARY_SCRIPT" >/dev/null 2>&1 || true

  PROMPT="$(cat <<EOF
You are automatically continuing work in this repository.
This is pass $pass_no of $max_passes for trigger source "$source_name".
Read the local planning/docs/graph context first. Start with these files if they exist:
- graphify-out/GRAPH_REPORT.md
- .planning/PROJECT.md
- $task_board_rel
- $requirements_rel
- $tasks_rel
- .planning/ROADMAP.md
- .planning/STATE.md
- .planning/auto-continue-last-summary.md
- .planning/auto-workflow-state.json
Default continue, not default stop.
Do not stop because one small task is done.
If $task_board_rel does not exist yet and the repo already has planning docs, initialize it first by running:
  bash scripts/hermes-auto-continue-task-board-init.sh
When task board exists, prefer it as the canonical next-task selector:
- continue any task already marked in_progress
- otherwise pick the highest-priority task whose dependencies are satisfied
- update task status / notes / last_updated when you start, block, or finish meaningful work
Pick the highest-priority executable task and keep moving until the whole scoped project is complete, you are truly blocked, or you need external input.
After each meaningful implementation step, update the planning docs so the next pass can continue from current reality.
This runner currently holds the canonical writer lease for the project.
Any delegated helper agents must remain read-only unless they also hold the writer lease.
If you need human or external input before you can continue, write a structured handoff first by running:
  bash scripts/ai-workflow.sh auto-handoff-set "<reason>" "<detail>" "<requested_input>" "<resume_condition>" "<next_action>"
Then stop.
Only when the whole scoped project is complete should you run:
  bash scripts/hermes-auto-continue-mark-complete.sh
That script is the only allowed way to stop the loop.
EOF
)"

  set +e
  hermes chat -q "$PROMPT" >> "$HERMES_AUTO_CONTINUE_LOG_FILE" 2>&1
  hermes_exit=$?
  set -e

  if [ "$hermes_exit" -ne 0 ]; then
    write_blocked hermes_run_failed "exit=$hermes_exit source=$source_name pass=$pass_no/$max_passes"
    write_lease_state false "run failed"
    echo "[auto-continue] hermes run failed on pass $pass_no/$max_passes"
    exit "$hermes_exit"
  fi

  status_after="$(bash "$STATUS_SCRIPT")"
  echo "[auto-continue] post-run status=$status_after pass=$pass_no/$max_passes"

  if [[ "$status_after" == COMPLETE* ]]; then
    clear_blocked
    write_runtime_state complete verified "$status_after"
    write_lease_state false "completion reached"
    bash "$INSTALL_SCRIPT" uninstall >/dev/null 2>&1 || true
    bash "$SUMMARY_SCRIPT" >/dev/null 2>&1 || true
    echo "[auto-continue] project complete after run; cron removed"
    exit 0
  fi

  if handoff_active; then
    clear_blocked
    write_runtime_state handoff waiting_for_input "handoff file present after pass $pass_no/$max_passes"
    write_lease_state false "handoff active"
    bash "$SUMMARY_SCRIPT" >/dev/null 2>&1 || true
    echo "[auto-continue] handoff active after pass $pass_no/$max_passes; stopping autonomous loop"
    exit 0
  fi

  clear_blocked
  write_runtime_state inactive pass_finished "pass $pass_no/$max_passes finished without completion"
  write_lease_state false "pass $pass_no/$max_passes finished without completion"
  bash "$SUMMARY_SCRIPT" >/dev/null 2>&1 || true

  if [ "$pass_no" -lt "$max_passes" ]; then
    echo "[auto-continue] incomplete after pass $pass_no/$max_passes; continuing"
    sleep "$pass_idle_seconds"
  fi

  pass_no=$((pass_no + 1))
done

write_runtime_state inactive pass_budget_exhausted "max passes reached without completion or handoff"
write_lease_state false "pass budget exhausted"
bash "$SUMMARY_SCRIPT" >/dev/null 2>&1 || true
echo "[auto-continue] pass budget exhausted without completion"
