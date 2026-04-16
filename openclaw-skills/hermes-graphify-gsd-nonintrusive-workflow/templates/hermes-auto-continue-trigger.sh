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

write_lease_state true "writer lease acquired"
write_runtime_state running started "auto-continue session started"
bash "$SUMMARY_SCRIPT" >/dev/null 2>&1 || true

read -r -d '' PROMPT <<'EOF' || true
You are automatically continuing work in this repository.
Read the local planning/docs/graph context first.
Default continue, not default stop.
Do not stop because one small task is done.
This runner currently holds the canonical writer lease for the project.
Any delegated helper agents must remain read-only unless they also hold the writer lease.
Only when the whole scoped project is complete should you run:
  bash scripts/hermes-auto-continue-mark-complete.sh
That script is the only allowed way to stop the loop.
EOF

hermes chat -q "$PROMPT" >> "$HERMES_AUTO_CONTINUE_LOG_FILE" 2>&1 || true
status_after="$(bash "$STATUS_SCRIPT")"
echo "[auto-continue] post-run status=$status_after"
if [[ "$status_after" == COMPLETE* ]]; then
  write_runtime_state complete verified "$status_after"
  write_lease_state false "completion reached"
  bash "$INSTALL_SCRIPT" uninstall >/dev/null 2>&1 || true
  echo "[auto-continue] project complete after run; cron removed"
else
  write_runtime_state inactive run_finished "$status_after"
  write_lease_state false "run finished without completion"
fi
bash "$SUMMARY_SCRIPT" >/dev/null 2>&1 || true
