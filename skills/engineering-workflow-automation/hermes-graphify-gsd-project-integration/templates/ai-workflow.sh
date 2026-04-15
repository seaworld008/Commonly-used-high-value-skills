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

have_cmd() { command -v "$1" >/dev/null 2>&1; }

doctor() {
  echo "[ai-workflow] repo: $ROOT"
  if have_cmd hermes; then echo "[ai-workflow] hermes ok"; else echo "[ai-workflow] hermes missing"; fi
  if have_cmd graphify; then echo "[ai-workflow] graphify ok"; else echo "[ai-workflow] graphify missing"; fi
  if have_cmd gsd-sdk; then echo "[ai-workflow] gsd-sdk ok"; else echo "[ai-workflow] gsd-sdk missing"; fi
  [ -d "$GRAPH_DIR" ] && echo "[ai-workflow] graphify-out present" || echo "[ai-workflow] graphify-out missing"
  [ -d "$PLAN_DIR" ] && echo "[ai-workflow] .planning present" || echo "[ai-workflow] .planning missing"
  [ -d "$ROOT/.codex" ] && echo "[ai-workflow] .codex present" || echo "[ai-workflow] .codex missing"
}

context() {
  [ -f "$REPORT_MD" ] && echo "1. $REPORT_MD"
  [ -f "$STATE_MD" ] && echo "2. $STATE_MD"
  [ -f "$ROADMAP_MD" ] && echo "3. $ROADMAP_MD"
  [ -f "$PROJECT_MD" ] && echo "4. $PROJECT_MD"
  [ -x "$GRAPH_SCRIPT" ] && "$GRAPH_SCRIPT" status
}

sync() { [ -x "$GRAPH_SCRIPT" ] || { echo "graphify-sync missing" >&2; exit 1; }; "$GRAPH_SCRIPT" smart; }
force() { [ -x "$GRAPH_SCRIPT" ] || { echo "graphify-sync missing" >&2; exit 1; }; "$GRAPH_SCRIPT" force; }
next_steps() {
  echo "1. ./scripts/ai-workflow.sh sync"
  echo "2. Read graphify-out/GRAPH_REPORT.md"
  echo "3. Read .planning/STATE.md and .planning/ROADMAP.md"
  echo "4. Use GSD phase/plan/execute"
  echo "5. Implement and test"
  echo "6. ./scripts/ai-workflow.sh sync"
}
cmd="${1:-doctor}"
case "$cmd" in
  doctor) doctor ;;
  context) context ;;
  sync) sync ;;
  force) force ;;
  next) next_steps ;;
  *) echo "Usage: $0 {doctor|context|sync|force|next}" >&2; exit 1 ;;
esac
