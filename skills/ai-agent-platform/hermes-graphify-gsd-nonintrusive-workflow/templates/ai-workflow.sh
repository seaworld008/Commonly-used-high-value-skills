#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

GRAPH_SCRIPT="$ROOT/scripts/graphify-sync.sh"
GRAPH_DIR="$ROOT/graphify-out"
PLAN_DIR="$ROOT/.planning"
REPORT_MD="$GRAPH_DIR/GRAPH_REPORT.md"
STATE_MD="$PLAN_DIR/STATE.md"
ROADMAP_MD="$PLAN_DIR/ROADMAP.md"
PROJECT_MD="$PLAN_DIR/PROJECT.md"
AUTO_CONFIG="$ROOT/scripts/hermes-auto-continue-config.sh"
AUTO_STATUS="$ROOT/scripts/hermes-auto-continue-status.sh"
AUTO_TRIGGER="$ROOT/scripts/hermes-auto-continue-trigger.sh"
AUTO_CHECKPOINT="$ROOT/scripts/hermes-auto-continue-checkpoint.sh"
AUTO_MARK_COMPLETE="$ROOT/scripts/hermes-auto-continue-mark-complete.sh"
AUTO_INSTALL="$ROOT/scripts/install-hermes-auto-continue-cron.sh"
AUTO_SUMMARY="$ROOT/scripts/hermes-auto-continue-summary.sh"
AUTO_TASK_BOARD_INIT="$ROOT/scripts/hermes-auto-continue-task-board-init.sh"
AUTO_TASK_BOARD_STATUS="$ROOT/scripts/hermes-auto-continue-task-board-status.sh"
AUTO_TASK_BOARD_UPDATE="$ROOT/scripts/hermes-auto-continue-task-board-update.sh"
AUTO_TASK_BOARD_COMPLETE="$ROOT/scripts/hermes-auto-continue-task-board-complete-if-ready.sh"

have_cmd() { command -v "$1" >/dev/null 2>&1; }
have_file() { [ -f "$1" ]; }
have_exec() { [ -x "$1" ]; }
require_exec() { [ -x "$1" ] || { echo "missing executable: $1" >&2; exit 1; }; }
maybe_source_auto_config() { have_file "$AUTO_CONFIG" && . "$AUTO_CONFIG"; }

json_pretty() {
  local path="$1"
  if [ -f "$path" ]; then
    python3 - <<'PY' "$path"
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
try:
    print(json.dumps(json.loads(p.read_text()), ensure_ascii=False, indent=2))
except Exception:
    print(p.read_text())
PY
  else
    echo "missing: $path"
  fi
}

doctor() {
  echo "[ai-workflow] repo: $ROOT"
  if have_cmd hermes; then echo "[ai-workflow] hermes ok"; else echo "[ai-workflow] hermes missing"; fi
  if have_cmd graphify; then echo "[ai-workflow] graphify ok"; else echo "[ai-workflow] graphify missing"; fi
  if have_cmd gsd-sdk; then echo "[ai-workflow] gsd-sdk ok"; else echo "[ai-workflow] gsd-sdk missing"; fi
  [ -d "$GRAPH_DIR" ] && echo "[ai-workflow] graphify-out present" || echo "[ai-workflow] graphify-out missing"
  [ -d "$PLAN_DIR" ] && echo "[ai-workflow] .planning present" || echo "[ai-workflow] .planning missing"
  [ -d "$ROOT/.codex" ] && echo "[ai-workflow] .codex present" || echo "[ai-workflow] .codex missing"
  if have_file "$AUTO_CONFIG"; then
    maybe_source_auto_config
    echo "[ai-workflow] auto-continue config present"
    printf '%s\n' "$(hermes_auto_continue_writer_surface_status)" | sed 's/^/[ai-workflow] /'
  else
    echo "[ai-workflow] auto-continue config missing"
  fi
}

context() {
  [ -f "$REPORT_MD" ] && echo "1. $REPORT_MD"
  [ -f "$STATE_MD" ] && echo "2. $STATE_MD"
  [ -f "$ROADMAP_MD" ] && echo "3. $ROADMAP_MD"
  [ -f "$PROJECT_MD" ] && echo "4. $PROJECT_MD"
  [ -x "$GRAPH_SCRIPT" ] && "$GRAPH_SCRIPT" status
}

sync() { require_exec "$GRAPH_SCRIPT"; "$GRAPH_SCRIPT" smart; }
force() { require_exec "$GRAPH_SCRIPT"; "$GRAPH_SCRIPT" force; }
next_steps() {
  echo "1. ./scripts/ai-workflow.sh sync"
  echo "2. Read graphify-out/GRAPH_REPORT.md"
  echo "3. Read .planning/STATE.md and .planning/ROADMAP.md"
  echo "4. Use GSD phase/plan/execute"
  echo "5. Implement and test"
  echo "6. ./scripts/ai-workflow.sh sync"
}

auto_status() { require_exec "$AUTO_STATUS"; bash "$AUTO_STATUS"; }
auto_trigger() { require_exec "$AUTO_TRIGGER"; bash "$AUTO_TRIGGER" "${1:-manual}"; }
auto_checkpoint() { require_exec "$AUTO_CHECKPOINT"; bash "$AUTO_CHECKPOINT" "$@"; }
auto_mark_complete() { require_exec "$AUTO_MARK_COMPLETE"; bash "$AUTO_MARK_COMPLETE"; }
auto_install() { require_exec "$AUTO_INSTALL"; bash "$AUTO_INSTALL" install; }
auto_uninstall() { require_exec "$AUTO_INSTALL"; bash "$AUTO_INSTALL" uninstall; }
auto_summary() { require_exec "$AUTO_SUMMARY"; bash "$AUTO_SUMMARY"; }
auto_task_board_init() { require_exec "$AUTO_TASK_BOARD_INIT"; bash "$AUTO_TASK_BOARD_INIT" "$@"; }
auto_task_board_show() { require_exec "$AUTO_TASK_BOARD_STATUS"; bash "$AUTO_TASK_BOARD_STATUS"; }
auto_task_board_claim_next() { require_exec "$AUTO_TASK_BOARD_UPDATE"; bash "$AUTO_TASK_BOARD_UPDATE" claim-next; }
auto_task_board_update() { require_exec "$AUTO_TASK_BOARD_UPDATE"; bash "$AUTO_TASK_BOARD_UPDATE" "$@"; }
auto_task_board_complete_if_ready() { require_exec "$AUTO_TASK_BOARD_COMPLETE"; bash "$AUTO_TASK_BOARD_COMPLETE" "$@"; }

auto_execution_surface_show() {
  maybe_source_auto_config
  have_file "$AUTO_CONFIG" || { echo "auto-continue config missing" >&2; exit 1; }
  hermes_auto_continue_writer_surface_status
}

auto_runner_show() {
  maybe_source_auto_config
  have_file "$AUTO_CONFIG" || { echo "auto-continue config missing" >&2; exit 1; }
  echo "[auto-runner-show] status=$(bash "$AUTO_STATUS")"
  echo "[auto-runner-show] state_file=$HERMES_AUTO_CONTINUE_STATE_FILE"
  json_pretty "$HERMES_AUTO_CONTINUE_STATE_FILE"
  echo "[auto-runner-show] lease_file=$HERMES_AUTO_CONTINUE_LEASE_FILE"
  json_pretty "$HERMES_AUTO_CONTINUE_LEASE_FILE"
  echo "[auto-runner-show] blocked_file=$HERMES_AUTO_CONTINUE_BLOCKED_FILE"
  json_pretty "$HERMES_AUTO_CONTINUE_BLOCKED_FILE"
}

auto_workflow_state_show() {
  maybe_source_auto_config
  have_file "$AUTO_CONFIG" || { echo "auto-continue config missing" >&2; exit 1; }
  echo "[auto-workflow-state-show] mirror=$HERMES_AUTO_CONTINUE_PLANNING_MIRROR"
  json_pretty "$HERMES_AUTO_CONTINUE_PLANNING_MIRROR"
}

auto_progress() {
  maybe_source_auto_config
  have_file "$AUTO_CONFIG" || { echo "auto-continue config missing" >&2; exit 1; }
  local status_line state_json handoff_state summary_path writer_status
  status_line="$(bash "$AUTO_STATUS")"
  writer_status="$(hermes_auto_continue_writer_surface_status)"
  summary_path="$HERMES_AUTO_CONTINUE_SUMMARY_FILE"
  state_json='{}'
  if [ -f "$HERMES_AUTO_CONTINUE_STATE_FILE" ]; then state_json="$(cat "$HERMES_AUTO_CONTINUE_STATE_FILE")"; fi
  python3 - <<'PY' "$status_line" "$writer_status" "$state_json" "$summary_path" "$HERMES_AUTO_CONTINUE_HANDOFF_FILE" "$HERMES_AUTO_CONTINUE_BLOCKED_FILE"
import json, sys
status_line = sys.argv[1]
writer = dict(line.split('=', 1) for line in sys.argv[2].splitlines() if '=' in line)
state = json.loads(sys.argv[3]) if sys.argv[3].strip() else {}
summary_path = sys.argv[4]
handoff_file = sys.argv[5]
blocked_file = sys.argv[6]
handoff_active = False
blocked = {}
try:
    with open(handoff_file) as f:
        handoff_active = bool(json.load(f))
except Exception:
    handoff_active = False
try:
    with open(blocked_file) as f:
        blocked = json.load(f)
except Exception:
    blocked = {}
print(f"status={status_line}")
print(f"execution_surface={writer.get('execution_surface','unknown')}")
print(f"writer_recommended={writer.get('writer_recommended','unknown')}")
print(f"runner_state={state.get('state','unknown')}")
print(f"reason={state.get('reason','n/a')}")
print(f"head={state.get('head','unknown')}")
print(f"handoff_active={'yes' if handoff_active else 'no'}")
print(f"blocked_active={'yes' if bool(blocked) else 'no'}")
print(f"blocked_reason={blocked.get('reason','n/a')}")
print(f"summary_file={summary_path}")
PY
}

auto_handoff_show() {
  maybe_source_auto_config
  have_file "$AUTO_CONFIG" || { echo "auto-continue config missing" >&2; exit 1; }
  json_pretty "$HERMES_AUTO_CONTINUE_HANDOFF_FILE"
}

auto_handoff_set() {
  maybe_source_auto_config
  have_file "$AUTO_CONFIG" || { echo "auto-continue config missing" >&2; exit 1; }
  local reason="${1:-}" detail="${2:-}" requested_input="${3:-}" resume_condition="${4:-}" next_action="${5:-}"
  [ -n "$reason" ] && [ -n "$detail" ] || { echo "Usage: $0 auto-handoff-set <reason> <detail> [requested_input] [resume_condition] [next_action]" >&2; exit 1; }
  python3 - <<'PY' "$HERMES_AUTO_CONTINUE_HANDOFF_FILE" "$reason" "$detail" "$requested_input" "$resume_condition" "$next_action"
from pathlib import Path
import json, sys, datetime
payload = {
  'time': datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
  'reason': sys.argv[2],
  'detail': sys.argv[3],
  'requested_input': sys.argv[4],
  'resume_condition': sys.argv[5],
  'next_action': sys.argv[6],
}
Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)
Path(sys.argv[1]).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
print(sys.argv[1])
PY
}

auto_handoff_clear() {
  maybe_source_auto_config
  have_file "$AUTO_CONFIG" || { echo "auto-continue config missing" >&2; exit 1; }
  rm -f "$HERMES_AUTO_CONTINUE_HANDOFF_FILE"
  echo "cleared"
}

cmd="${1:-doctor}"
case "$cmd" in
  doctor) doctor ;;
  context) context ;;
  sync) sync ;;
  force) force ;;
  next) next_steps ;;
  auto-status) auto_status ;;
  auto-trigger) shift; auto_trigger "$@" ;;
  auto-checkpoint) shift; auto_checkpoint "$@" ;;
  auto-mark-complete) auto_mark_complete ;;
  auto-install) auto_install ;;
  auto-uninstall) auto_uninstall ;;
  auto-summary) auto_summary ;;
  auto-task-board-init) shift; auto_task_board_init "$@" ;;
  auto-task-board-show) auto_task_board_show ;;
  auto-task-board-claim-next) auto_task_board_claim_next ;;
  auto-task-board-update) shift; auto_task_board_update "$@" ;;
  auto-task-board-complete-if-ready) shift; auto_task_board_complete_if_ready "$@" ;;
  auto-progress) auto_progress ;;
  auto-runner-show) auto_runner_show ;;
  auto-execution-surface-show) auto_execution_surface_show ;;
  auto-workflow-state-show) auto_workflow_state_show ;;
  auto-handoff-show) auto_handoff_show ;;
  auto-handoff-set) shift; auto_handoff_set "$@" ;;
  auto-handoff-clear) auto_handoff_clear ;;
  *)
    echo "Usage: $0 {doctor|context|sync|force|next|auto-status|auto-trigger|auto-checkpoint|auto-mark-complete|auto-install|auto-uninstall|auto-summary|auto-task-board-init|auto-task-board-show|auto-task-board-claim-next|auto-task-board-update|auto-task-board-complete-if-ready|auto-progress|auto-runner-show|auto-execution-surface-show|auto-workflow-state-show|auto-handoff-show|auto-handoff-set|auto-handoff-clear}" >&2
    exit 1
    ;;
esac
