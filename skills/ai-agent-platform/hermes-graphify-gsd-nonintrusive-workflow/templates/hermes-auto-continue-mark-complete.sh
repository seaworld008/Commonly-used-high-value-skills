#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/hermes-auto-continue-config.sh"
cd "$ROOT"
mkdir -p "$(dirname "$HERMES_AUTO_CONTINUE_SENTINEL")"
VERIFY_CMD="$HERMES_AUTO_CONTINUE_FULL_VERIFY_CMD"
HEAD_SHA="$(git rev-parse HEAD)"
BRANCH_NAME="$(git rev-parse --abbrev-ref HEAD)"
VERIFY_STARTED_AT="$(date -Is)"
VERIFY_OUTPUT_FILE="$(mktemp /tmp/hermes-auto-verify.XXXXXX.log)"
cleanup() { rm -f "$VERIFY_OUTPUT_FILE"; }
trap cleanup EXIT
set +e
bash -lc "$VERIFY_CMD" >"$VERIFY_OUTPUT_FILE" 2>&1
VERIFY_EXIT=$?
set -e
if [ "$VERIFY_EXIT" -ne 0 ]; then
  echo "[auto-continue] full verification failed; sentinel not written" >&2
  cat "$VERIFY_OUTPUT_FILE" >&2
  exit "$VERIFY_EXIT"
fi
if [ -n "$(git status --porcelain)" ]; then
  echo "[auto-continue] working tree is dirty after verification; refusing to mark complete" >&2
  git status --short >&2 || true
  exit 2
fi
VERIFY_FINISHED_AT="$(date -Is)"
python3 - <<'PY' "$HERMES_AUTO_CONTINUE_SENTINEL" "$HERMES_AUTO_CONTINUE_EVIDENCE_DOC" "$HEAD_SHA" "$BRANCH_NAME" "$VERIFY_STARTED_AT" "$VERIFY_FINISHED_AT" "$VERIFY_CMD" "$VERIFY_OUTPUT_FILE"
import json
from pathlib import Path
import sys
sentinel_path = Path(sys.argv[1])
evidence_path = Path(sys.argv[2])
head = sys.argv[3]
branch = sys.argv[4]
started = sys.argv[5]
finished = sys.argv[6]
verify_cmd = sys.argv[7]
output_path = Path(sys.argv[8])
log_text = output_path.read_text(errors='replace')
sentinel = {
    'status': 'complete',
    'head': head,
    'branch': branch,
    'verified_at_start': started,
    'verified_at_finish': finished,
    'verify_command': verify_cmd,
    'evidence_doc': str(evidence_path),
}
sentinel_path.write_text(json.dumps(sentinel, ensure_ascii=False, indent=2) + '\n')
evidence_path.parent.mkdir(parents=True, exist_ok=True)
evidence = f'''# Auto Continue Completion Evidence\n\n- Status: complete\n- Git HEAD: `{head}`\n- Branch: `{branch}`\n- Verification started: `{started}`\n- Verification finished: `{finished}`\n- Verification command:\n\n```bash\n{verify_cmd}\n```\n\n## Verification Output\n\n```text\n{log_text}\n```\n'''
evidence_path.write_text(evidence)
PY
echo "[auto-continue] completion sentinel written: $HERMES_AUTO_CONTINUE_SENTINEL"
echo "[auto-continue] evidence written: $HERMES_AUTO_CONTINUE_EVIDENCE_DOC"
if [ -x "$ROOT/scripts/hermes-auto-continue-notify.sh" ]; then
  bash "$ROOT/scripts/hermes-auto-continue-notify.sh" complete "project_complete" "$HERMES_AUTO_CONTINUE_EVIDENCE_DOC" >/dev/null 2>&1 || true
fi
