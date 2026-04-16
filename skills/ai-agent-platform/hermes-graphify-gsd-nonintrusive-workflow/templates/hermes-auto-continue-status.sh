#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/hermes-auto-continue-config.sh"
hermes_auto_continue_ensure_dirs
cd "$ROOT"
CURRENT_HEAD="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
SENTINEL_REL="${HERMES_AUTO_CONTINUE_SENTINEL#$ROOT/}"
EVIDENCE_REL="${HERMES_AUTO_CONTINUE_EVIDENCE_DOC#$ROOT/}"
SUMMARY_REL="${HERMES_AUTO_CONTINUE_SUMMARY_FILE#$ROOT/}"
BLOCKED_REL="${HERMES_AUTO_CONTINUE_BLOCKED_FILE#$ROOT/}"
MIRROR_REL="${HERMES_AUTO_CONTINUE_PLANNING_MIRROR#$ROOT/}"
STATE_DIR_REL="${HERMES_AUTO_CONTINUE_STATE_DIR#$ROOT/}"
STATUS_LINES="$(git status --porcelain 2>/dev/null || true)"
FILTERED_STATUS="$(printf '%s\n' "$STATUS_LINES" | grep -v -F " $SENTINEL_REL" | grep -v -F " $EVIDENCE_REL" | grep -v -F " $SUMMARY_REL" | grep -v -F " $BLOCKED_REL" | grep -v -F " $MIRROR_REL" | grep -v -F ' .planning/logs/' | grep -v -F ' .planning/checkpoints/' | grep -v -F ' .planning/runtime/' | grep -v -F ' .planning/.hermes-auto-continue.lock' || true)"
WORKTREE_DIRTY=0
if [ -n "$FILTERED_STATUS" ]; then
  WORKTREE_DIRTY=1
fi

if [ ! -f "$HERMES_AUTO_CONTINUE_SENTINEL" ]; then
  echo "INCOMPLETE reason=missing_sentinel head=$CURRENT_HEAD dirty=$WORKTREE_DIRTY"
  exit 0
fi

python3 - <<'PY' "$HERMES_AUTO_CONTINUE_SENTINEL" "$CURRENT_HEAD" "$WORKTREE_DIRTY"
import json
from pathlib import Path
import sys
sentinel_path = Path(sys.argv[1])
current_head = sys.argv[2]
dirty = sys.argv[3] == '1'
try:
    data = json.loads(sentinel_path.read_text())
except Exception as exc:
    print(f"INCOMPLETE reason=invalid_sentinel error={exc}")
    raise SystemExit(0)
if data.get('status') != 'complete':
    print('INCOMPLETE reason=sentinel_status_not_complete')
    raise SystemExit(0)
if data.get('head') != current_head:
    print(f"INCOMPLETE reason=head_mismatch sentinel_head={data.get('head')} current_head={current_head}")
    raise SystemExit(0)
if dirty:
    print(f"INCOMPLETE reason=dirty_worktree head={current_head}")
    raise SystemExit(0)
print(f"COMPLETE sentinel={sentinel_path} head={current_head}")
PY
