#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export HERMES_AUTO_CONTINUE_ROOT="$ROOT"
export HERMES_AUTO_CONTINUE_SENTINEL="$ROOT/.planning/auto-continue-complete.json"
export HERMES_AUTO_CONTINUE_EVIDENCE_DOC="$ROOT/docs/auto-continue-completion-evidence.md"
export HERMES_AUTO_CONTINUE_SUMMARY_FILE="$ROOT/.planning/auto-continue-last-summary.md"
export HERMES_AUTO_CONTINUE_BLOCKED_FILE="$ROOT/.planning/auto-continue-last-blocked.json"
export HERMES_AUTO_CONTINUE_PLANNING_MIRROR="$ROOT/.planning/auto-workflow-state.json"
export HERMES_AUTO_CONTINUE_FULL_VERIFY_CMD="${HERMES_AUTO_CONTINUE_FULL_VERIFY_CMD:-pnpm lint && pnpm build && pnpm test}"
export HERMES_AUTO_CONTINUE_PROJECT_KEY="${HERMES_AUTO_CONTINUE_PROJECT_KEY:-$(basename "$ROOT")}"
export HERMES_AUTO_CONTINUE_STATE_DIR="${HERMES_AUTO_CONTINUE_STATE_DIR:-$ROOT/.planning/runtime}"
export HERMES_AUTO_CONTINUE_PRIMARY_ROOT="${HERMES_AUTO_CONTINUE_PRIMARY_ROOT:-$ROOT}"
export HERMES_AUTO_CONTINUE_BACKEND_ROOT="${HERMES_AUTO_CONTINUE_BACKEND_ROOT:-src-tauri}"
export HERMES_AUTO_CONTINUE_REPO_LOCK="$ROOT/.planning/.hermes-auto-continue.lock"
export HERMES_AUTO_CONTINUE_PROJECT_LOCK="$HERMES_AUTO_CONTINUE_STATE_DIR/${HERMES_AUTO_CONTINUE_PROJECT_KEY}.writer.lock"
export HERMES_AUTO_CONTINUE_LEASE_FILE="$HERMES_AUTO_CONTINUE_STATE_DIR/${HERMES_AUTO_CONTINUE_PROJECT_KEY}.writer.json"
export HERMES_AUTO_CONTINUE_STATE_FILE="$HERMES_AUTO_CONTINUE_STATE_DIR/${HERMES_AUTO_CONTINUE_PROJECT_KEY}.state.json"
export HERMES_AUTO_CONTINUE_HANDOFF_FILE="$HERMES_AUTO_CONTINUE_STATE_DIR/${HERMES_AUTO_CONTINUE_PROJECT_KEY}.handoff.json"
export HERMES_AUTO_CONTINUE_LOG_DIR="$ROOT/.planning/logs"
export HERMES_AUTO_CONTINUE_LOG_FILE="$HERMES_AUTO_CONTINUE_LOG_DIR/hermes-auto-continue.log"
export HERMES_AUTO_CONTINUE_MAX_PASSES_PER_TRIGGER="${HERMES_AUTO_CONTINUE_MAX_PASSES_PER_TRIGGER:-4}"
export HERMES_AUTO_CONTINUE_PASS_IDLE_SECONDS="${HERMES_AUTO_CONTINUE_PASS_IDLE_SECONDS:-5}"
export HERMES_AUTO_CONTINUE_CRON_SCHEDULE="${HERMES_AUTO_CONTINUE_CRON_SCHEDULE:-*/15 * * * *}"
export HERMES_AUTO_CONTINUE_REQUIREMENTS_FILE="${HERMES_AUTO_CONTINUE_REQUIREMENTS_FILE:-$ROOT/.planning/REQUIREMENTS.md}"
export HERMES_AUTO_CONTINUE_TASKS_FILE="${HERMES_AUTO_CONTINUE_TASKS_FILE:-$ROOT/.planning/TASKS.md}"
export HERMES_AUTO_CONTINUE_TASK_BOARD_FILE="${HERMES_AUTO_CONTINUE_TASK_BOARD_FILE:-$ROOT/.planning/task-board.json}"
export HERMES_AUTO_CONTINUE_NOTIFY_DIR="${HERMES_AUTO_CONTINUE_NOTIFY_DIR:-$ROOT/.planning/notifications}"
export HERMES_AUTO_CONTINUE_NOTIFY_DELIVER="${HERMES_AUTO_CONTINUE_NOTIFY_DELIVER:-}"
export HERMES_AUTO_CONTINUE_NOTIFY_COMMAND="${HERMES_AUTO_CONTINUE_NOTIFY_COMMAND:-}"
export HERMES_AUTO_CONTINUE_NOTIFY_EVENTS="${HERMES_AUTO_CONTINUE_NOTIFY_EVENTS:-task_done,handoff,resume,run_failed,pass_budget_exhausted,complete}"

hermes_auto_continue_ensure_dirs() {
  mkdir -p "$ROOT/.planning" "$ROOT/docs" "$HERMES_AUTO_CONTINUE_STATE_DIR" "$HERMES_AUTO_CONTINUE_LOG_DIR" "$ROOT/.planning/checkpoints" "$HERMES_AUTO_CONTINUE_NOTIFY_DIR"
}

hermes_auto_continue_lockfile_present() {
  [ -f "$ROOT/pnpm-lock.yaml" ] || [ -f "$ROOT/package-lock.json" ] || [ -f "$ROOT/yarn.lock" ] || [ -f "$ROOT/bun.lockb" ]
}

hermes_auto_continue_execution_surface_details() {
  local missing=()
  [ -f "$ROOT/package.json" ] || missing+=("package.json")
  hermes_auto_continue_lockfile_present || missing+=("lockfile")
  [ -d "$ROOT/$HERMES_AUTO_CONTINUE_BACKEND_ROOT" ] || missing+=("$HERMES_AUTO_CONTINUE_BACKEND_ROOT")
  [ -f "$ROOT/.planning/STATE.md" ] || missing+=(".planning/STATE.md")
  [ -x "$ROOT/scripts/graphify-sync.sh" ] || missing+=("scripts/graphify-sync.sh")
  if [ "${#missing[@]}" -eq 0 ]; then
    printf 'ready\n'
  else
    printf 'incomplete:%s\n' "$(IFS=,; echo "${missing[*]}")"
  fi
}

hermes_auto_continue_writer_surface_status() {
  local execution_surface writer_eligible primary_root_match writer_recommended
  execution_surface="$(hermes_auto_continue_execution_surface_details)"
  if [ "$execution_surface" = "ready" ] || [ "${HERMES_AUTO_CONTINUE_ALLOW_INCOMPLETE_ROOT:-0}" = "1" ]; then
    writer_eligible=yes
  else
    writer_eligible=no
  fi
  if [ "$ROOT" = "$HERMES_AUTO_CONTINUE_PRIMARY_ROOT" ]; then
    primary_root_match=yes
  else
    primary_root_match=no
  fi
  if [ "$writer_eligible" = yes ] && [ "$primary_root_match" = yes ]; then
    writer_recommended=yes
  else
    writer_recommended=no
  fi
  cat <<EOF
root=$ROOT
primary_root=$HERMES_AUTO_CONTINUE_PRIMARY_ROOT
project_key=$HERMES_AUTO_CONTINUE_PROJECT_KEY
execution_surface=$execution_surface
writer_eligible=$writer_eligible
primary_root_match=$primary_root_match
writer_recommended=$writer_recommended
EOF
}
