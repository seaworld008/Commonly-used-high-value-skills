#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

GRAPH_DIR="$ROOT/graphify-out"
GRAPH_JSON="$GRAPH_DIR/graph.json"
REPORT_MD="$GRAPH_DIR/GRAPH_REPORT.md"
GRAPHIFY_PY=""

pick_python() {
  local candidates=()
  if [ -n "${GRAPHIFY_PY:-}" ] && [ -x "${GRAPHIFY_PY}" ]; then
    candidates+=("${GRAPHIFY_PY}")
  fi
  candidates+=(
    "$ROOT/venv/bin/python3"
    "$HOME/.hermes/hermes-agent/venv/bin/python3"
    "$(command -v python3 2>/dev/null || true)"
    "$(command -v python 2>/dev/null || true)"
  )
  for py in "${candidates[@]}"; do
    [ -n "$py" ] || continue
    [ -x "$py" ] || continue
    if "$py" -c "import graphify" >/dev/null 2>&1; then
      GRAPHIFY_PY="$py"
      return 0
    fi
  done
  echo "[graphify-sync] ERROR: no Python interpreter with graphify installed was found." >&2
  exit 1
}

run_graphify_python() {
  "$GRAPHIFY_PY" "$@"
}

code_changed_since_head() {
  git diff --name-only HEAD -- | grep -E '\.(rs|ts|tsx|js|jsx|mjs|cjs|json|toml|yaml|yml|css|scss|html|py)$' >/dev/null 2>&1
}

docs_only_changed_since_head() {
  local changed
  changed="$(git diff --name-only HEAD -- || true)"
  [ -n "$changed" ] || return 1
  printf '%s\n' "$changed" | grep -Ev '^(|.*\.(md|png|jpg|jpeg|webp|svg|pdf|txt))$' >/dev/null 2>&1 && return 1
  return 0
}

status() {
  pick_python
  echo "[graphify-sync] ROOT=$ROOT"
  echo "[graphify-sync] PYTHON=$GRAPHIFY_PY"
  [ -f "$GRAPH_JSON" ] && [ -f "$REPORT_MD" ] && echo "[graphify-sync] graph outputs present" || echo "[graphify-sync] graph outputs missing"
  echo "[graphify-sync] manifest: optional / no longer required by current graphify versions"
  echo "[graphify-sync] changed files:"
  git status --short
  if code_changed_since_head; then
    echo "[graphify-sync] code changes detected against HEAD"
  elif docs_only_changed_since_head; then
    echo "[graphify-sync] only docs/media changes detected against HEAD"
  else
    echo "[graphify-sync] no code changes detected against HEAD"
  fi
}

smart() {
  pick_python
  if [ ! -f "$GRAPH_JSON" ] || [ ! -f "$REPORT_MD" ]; then
    echo "[graphify-sync] graph missing or incomplete -> running graphify update ."
    graphify update .
    return 0
  fi
  if code_changed_since_head; then
    echo "[graphify-sync] code changes detected -> running code-only rebuild"
    run_graphify_python - <<'PY'
from pathlib import Path
from graphify.watch import _rebuild_code
_rebuild_code(Path('.'))
print('[graphify-sync] code graph rebuilt')
PY
    return 0
  fi
  if docs_only_changed_since_head; then
    echo "[graphify-sync] only docs/media changes detected -> skipping automatic rebuild"
    echo "[graphify-sync] run full semantic refresh manually when needed"
    return 0
  fi
  echo "[graphify-sync] no relevant code changes detected -> nothing to do"
}

force() {
  pick_python
  echo "[graphify-sync] forcing graphify update ."
  graphify update .
}

serve() {
  pick_python
  [ -f "$GRAPH_JSON" ] || { echo "[graphify-sync] ERROR: graph.json not found" >&2; exit 1; }
  run_graphify_python -m graphify.serve "$GRAPH_JSON"
}

cmd="${1:-status}"
case "$cmd" in
  status) status ;;
  smart) smart ;;
  force) force ;;
  serve) serve ;;
  *) echo "Usage: $0 {status|smart|force|serve}" >&2; exit 1 ;;
esac
