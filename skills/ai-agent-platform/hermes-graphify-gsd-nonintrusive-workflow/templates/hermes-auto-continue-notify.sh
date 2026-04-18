#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/hermes-auto-continue-config.sh"
hermes_auto_continue_ensure_dirs
cd "$ROOT"

event="${1:-}"
title="${2:-}"
detail="${3:-}"

[ -n "$event" ] || { echo "Usage: $0 <event> [title] [detail]" >&2; exit 1; }

case ",$HERMES_AUTO_CONTINUE_NOTIFY_EVENTS," in
  *",$event,"*) ;;
  *)
    echo "event_skipped=$event"
    exit 0
    ;;
esac

timestamp="$(date +%Y%m%d-%H%M%S)"
branch_name="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
head_sha="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
json_path="$HERMES_AUTO_CONTINUE_NOTIFY_DIR/${timestamp}-${event}.json"
md_path="$HERMES_AUTO_CONTINUE_NOTIFY_DIR/${timestamp}-${event}.md"

python3 - <<'PY' "$json_path" "$md_path" "$event" "$title" "$detail" "$ROOT" "$branch_name" "$head_sha" "$HERMES_AUTO_CONTINUE_SUMMARY_FILE" "$HERMES_AUTO_CONTINUE_NOTIFY_DELIVER" "$HERMES_GSD_NEXT_STATE_FILE"
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

json_path = Path(sys.argv[1])
md_path = Path(sys.argv[2])
event = sys.argv[3]
title = sys.argv[4] or event
detail = sys.argv[5]
repo_root = sys.argv[6]
branch = sys.argv[7]
head = sys.argv[8]
summary_file = sys.argv[9]
deliver = sys.argv[10]
gsd_state_file = sys.argv[11]
time = dt.datetime.now(dt.timezone.utc).astimezone().isoformat()

gsd_state = {}
try:
    gsd_state = json.loads(Path(gsd_state_file).read_text(encoding="utf-8"))
except Exception:
    gsd_state = {}

payload = {
    "time": time,
    "event": event,
    "title": title,
    "detail": detail,
    "repo_root": repo_root,
    "branch": branch,
    "head": head,
    "summary_file": summary_file,
    "deliver": deliver,
    "gsd": gsd_state,
}
json_path.parent.mkdir(parents=True, exist_ok=True)
json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

summary_text = ""
try:
    summary_text = Path(summary_file).read_text(encoding="utf-8")
except Exception:
    summary_text = ""

body = [
    f"# Hermes Auto Continue Notification",
    "",
    f"- Event: `{event}`",
    f"- Title: {title}",
    f"- Time: `{time}`",
    f"- Repo: `{repo_root}`",
    f"- Branch: `{branch}`",
    f"- Head: `{head}`",
]
if deliver:
    body.append(f"- Deliver: `{deliver}`")
if gsd_state:
    body.extend(
        [
            f"- GSD current phase: `{gsd_state.get('current_phase', '')}`",
            f"- GSD next step: `{gsd_state.get('gsd_next_step', '')}`",
            f"- GSD next command: `{gsd_state.get('gsd_next_command', '')}`",
        ]
    )
if detail:
    body.extend(["", "## Detail", "", detail])
if summary_text:
    body.extend(["", "## Latest Summary", "", summary_text.rstrip()])
md_path.write_text("\n".join(body).rstrip() + "\n", encoding="utf-8")
print(json_path)
print(md_path)
PY

if [ -n "$HERMES_AUTO_CONTINUE_NOTIFY_COMMAND" ]; then
  export HERMES_AUTO_CONTINUE_NOTIFY_EVENT="$event"
  export HERMES_AUTO_CONTINUE_NOTIFY_TITLE="$title"
  export HERMES_AUTO_CONTINUE_NOTIFY_DETAIL="$detail"
  export HERMES_AUTO_CONTINUE_NOTIFY_JSON="$json_path"
  export HERMES_AUTO_CONTINUE_NOTIFY_MD="$md_path"
  export HERMES_AUTO_CONTINUE_NOTIFY_DELIVER
  bash -lc "$HERMES_AUTO_CONTINUE_NOTIFY_COMMAND" || true
fi

if [ -x "$ROOT/scripts/hermes-auto-continue-learnings.sh" ]; then
  bash "$ROOT/scripts/hermes-auto-continue-learnings.sh" "$event" "$title" "$detail" >/dev/null 2>&1 || true
fi

echo "notify_json=$json_path"
echo "notify_md=$md_path"
