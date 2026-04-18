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
resume_output=''
notify_paths=''
gsd_next_output=''
graphify_hints_output=''
[ -f "$HERMES_AUTO_CONTINUE_STATE_FILE" ] && state_json="$(cat "$HERMES_AUTO_CONTINUE_STATE_FILE")"
[ -f "$HERMES_AUTO_CONTINUE_LEASE_FILE" ] && lease_json="$(cat "$HERMES_AUTO_CONTINUE_LEASE_FILE")"
[ -f "$HERMES_AUTO_CONTINUE_HANDOFF_FILE" ] && handoff_json="$(cat "$HERMES_AUTO_CONTINUE_HANDOFF_FILE")"
[ -f "$HERMES_AUTO_CONTINUE_BLOCKED_FILE" ] && blocked_json="$(cat "$HERMES_AUTO_CONTINUE_BLOCKED_FILE")"
if [ -x "$ROOT/scripts/hermes-auto-continue-task-board-status.sh" ] && [ -f "$HERMES_AUTO_CONTINUE_TASK_BOARD_FILE" ]; then
  task_board_output="$(bash "$ROOT/scripts/hermes-auto-continue-task-board-status.sh" 2>/dev/null || true)"
fi
if [ -x "$ROOT/scripts/hermes-auto-continue-resume-if-ready.sh" ]; then
  resume_output="$(bash "$ROOT/scripts/hermes-auto-continue-resume-if-ready.sh" 2>/dev/null || true)"
fi
if [ -f "$HERMES_GSD_NEXT_STATE_FILE" ]; then
  gsd_next_output="$(cat "$HERMES_GSD_NEXT_STATE_FILE" 2>/dev/null || true)"
elif [ -x "$ROOT/scripts/hermes-gsd-next-state.sh" ]; then
  gsd_next_output="$(bash "$ROOT/scripts/hermes-gsd-next-state.sh" 2>/dev/null || true)"
fi
if [ -x "$ROOT/scripts/hermes-graphify-strategy-hints.sh" ]; then
  graphify_hints_output="$(bash "$ROOT/scripts/hermes-graphify-strategy-hints.sh" 2>/dev/null || true)"
fi
if [ -x "$ROOT/scripts/hermes-gsd-sync-runtime-mirror.sh" ]; then
  bash "$ROOT/scripts/hermes-gsd-sync-runtime-mirror.sh" >/dev/null 2>&1 || true
fi
if [ -d "$HERMES_AUTO_CONTINUE_NOTIFY_DIR" ]; then
  notify_paths="$(find "$HERMES_AUTO_CONTINUE_NOTIFY_DIR" -maxdepth 1 -type f | sort | tail -2 || true)"
fi
if [ -x "$ROOT/scripts/hermes-auto-continue-task-board-sync-docs.sh" ] && [ -f "$HERMES_AUTO_CONTINUE_TASK_BOARD_FILE" ]; then
  bash "$ROOT/scripts/hermes-auto-continue-task-board-sync-docs.sh" >/dev/null 2>&1 || true
fi
python3 - <<'PY' "$HERMES_AUTO_CONTINUE_SUMMARY_FILE" "$status_line" "$writer_status" "$state_json" "$lease_json" "$handoff_json" "$blocked_json" "$task_board_output" "$resume_output" "$notify_paths" "$gsd_next_output" "$graphify_hints_output"
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
resume_lines = sys.argv[9].splitlines()
notify_lines = sys.argv[10].splitlines()
gsd_lines = sys.argv[11].splitlines()
graphify_lines = sys.argv[12].splitlines()
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
        if k in {"todo", "in_progress", "blocked", "done", "dropped", "current_id", "current_status", "current_priority", "current_title", "next_id", "next_status", "next_priority", "next_title", "ready_to_complete"}:
            parts.append(f"- task_board_{k}: `{v}`")
for line in resume_lines:
    if line.strip():
        k, _, v = line.partition('=')
        if k in {"resume_ready", "reason", "cleared"}:
            parts.append(f"- resume_{k}: `{v}`")
if notify_lines:
    parts.append("- notify_recent_files:")
    parts.extend([f"  - `{line}`" for line in notify_lines if line.strip()])
for line in gsd_lines:
    if line.strip():
        k, _, v = line.partition('=')
        if k in {"current_phase", "current_phase_name", "state_status", "phase_has_context", "phase_has_plan", "phase_has_summary", "gsd_next_step", "gsd_next_phase", "gsd_next_command", "gsd_next_reason"}:
            parts.append(f"- gsd_{k}: `{v}`")
for line in graphify_lines:
    if line.strip():
        k, _, v = line.partition('=')
        if k in {"hint_count", "hint_1_kind", "hint_1_reason", "hint_1_command", "hint_2_kind", "hint_2_reason", "hint_2_command", "hint_3_kind", "hint_3_reason", "hint_3_command"}:
            parts.append(f"- graphify_{k}: `{v}`")
summary_path.write_text('\n'.join(parts) + '\n')
print(summary_path)
PY
