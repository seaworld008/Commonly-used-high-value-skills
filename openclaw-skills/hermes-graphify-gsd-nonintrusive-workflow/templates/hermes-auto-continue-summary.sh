#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/hermes-auto-continue-config.sh"
hermes_auto_continue_ensure_dirs
cd "$ROOT"
status_line="$(bash "$ROOT/scripts/hermes-auto-continue-status.sh")"
writer_status="$(hermes_auto_continue_writer_surface_status)"
state_json='{}'
lease_json='{}'
handoff_json='{}'
blocked_json='{}'
task_board_output=''
[ -f "$HERMES_AUTO_CONTINUE_STATE_FILE" ] && state_json="$(cat "$HERMES_AUTO_CONTINUE_STATE_FILE")"
[ -f "$HERMES_AUTO_CONTINUE_LEASE_FILE" ] && lease_json="$(cat "$HERMES_AUTO_CONTINUE_LEASE_FILE")"
[ -f "$HERMES_AUTO_CONTINUE_HANDOFF_FILE" ] && handoff_json="$(cat "$HERMES_AUTO_CONTINUE_HANDOFF_FILE")"
[ -f "$HERMES_AUTO_CONTINUE_BLOCKED_FILE" ] && blocked_json="$(cat "$HERMES_AUTO_CONTINUE_BLOCKED_FILE")"
if [ -x "$ROOT/scripts/hermes-auto-continue-task-board-status.sh" ] && [ -f "$HERMES_AUTO_CONTINUE_TASK_BOARD_FILE" ]; then
  task_board_output="$(bash "$ROOT/scripts/hermes-auto-continue-task-board-status.sh" 2>/dev/null || true)"
fi
python3 - <<'PY' "$HERMES_AUTO_CONTINUE_SUMMARY_FILE" "$status_line" "$writer_status" "$state_json" "$lease_json" "$handoff_json" "$blocked_json" "$task_board_output"
import json, sys
from pathlib import Path
summary_path = Path(sys.argv[1])
status_line = sys.argv[2]
writer_status_lines = sys.argv[3].splitlines()
state = json.loads(sys.argv[4]) if sys.argv[4].strip() else {}
lease = json.loads(sys.argv[5]) if sys.argv[5].strip() else {}
handoff = json.loads(sys.argv[6]) if sys.argv[6].strip() else {}
blocked = json.loads(sys.argv[7]) if sys.argv[7].strip() else {}
task_board_lines = sys.argv[8].splitlines()
summary_path.parent.mkdir(parents=True, exist_ok=True)
parts = ['# Auto Continue Last Summary', '', f'- Status: `{status_line}`']
for line in writer_status_lines:
    if line.strip():
        k, _, v = line.partition('=')
        parts.append(f'- {k}: `{v}`')
parts.append(f"- Runner state: `{state.get('state', 'unknown')}`")
parts.append(f"- Runner reason: `{state.get('reason', 'n/a')}`")
parts.append(f"- Lease holder: `{lease.get('holder_repo', 'n/a')}`")
parts.append(f"- Lease active: `{lease.get('active', 'n/a')}`")
parts.append(f"- Handoff active: `{bool(handoff)}`")
parts.append(f"- Blocked active: `{bool(blocked)}`")
if handoff:
    parts.append(f"- Handoff reason: `{handoff.get('reason', 'n/a')}`")
    parts.append(f"- Handoff detail: `{handoff.get('detail', 'n/a')}`")
if blocked:
    parts.append(f"- Blocked reason: `{blocked.get('reason', 'n/a')}`")
    parts.append(f"- Blocked detail: `{blocked.get('detail', 'n/a')}`")
for line in task_board_lines:
    if line.strip():
        k, _, v = line.partition('=')
        if k in {"todo", "in_progress", "blocked", "done", "dropped", "next_id", "next_status", "next_priority", "next_title"}:
            parts.append(f"- task_board_{k}: `{v}`")
summary_path.write_text('\n'.join(parts) + '\n')
print(summary_path)
PY
