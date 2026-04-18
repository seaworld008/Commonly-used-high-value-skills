#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/hermes-auto-continue-config.sh"
hermes_auto_continue_ensure_dirs

event="${1:-}"
title="${2:-}"
detail="${3:-}"
[ -n "$event" ] || { echo "Usage: $0 <event> [title] [detail]" >&2; exit 1; }

python3 - <<'PY' "$HERMES_AUTO_CONTINUE_LEARNINGS_LOG" "$HERMES_AUTO_CONTINUE_SKILL_CANDIDATES_DIR" "$event" "$title" "$detail" "$ROOT"
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path

log_path = Path(sys.argv[1])
candidate_dir = Path(sys.argv[2])
event = sys.argv[3]
title = sys.argv[4] or event
detail = sys.argv[5]
root = Path(sys.argv[6])


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat()


entry = {
    "time": now(),
    "event": event,
    "title": title,
    "detail": detail,
}
log_path.parent.mkdir(parents=True, exist_ok=True)
with log_path.open("a", encoding="utf-8") as f:
    f.write(json.dumps(entry, ensure_ascii=False) + "\n")

entries = []
for line in log_path.read_text(encoding="utf-8").splitlines():
    try:
        entries.append(json.loads(line))
    except Exception:
        continue

blocked_reasons = [
    (item.get("event", ""), item.get("title", ""), item.get("detail", ""))
    for item in entries
    if item.get("event") in {"run_failed", "pass_budget_exhausted", "handoff"}
]

counter = Counter()
for ev, ttl, det in blocked_reasons:
    key = ttl or ev
    counter[key] += 1

candidate_dir.mkdir(parents=True, exist_ok=True)
for key, count in counter.items():
    if count < 2:
        continue
    slug = re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-") or "learning"
    path = candidate_dir / f"{slug}.md"
    body = [
        f"# Skill Candidate: {key}",
        "",
        f"- Count: `{count}`",
        f"- Source log: `{log_path}`",
        "",
        "## Why It Matters",
        "",
        "This recurring pattern appeared at least twice in the autonomous workflow and is a candidate for memory capture or a dedicated skill refinement.",
        "",
        "## Recent Evidence",
        "",
    ]
    recent = [item for item in entries if (item.get("title") or item.get("event")) == key][-5:]
    for item in recent:
        body.append(f"- `{item.get('time','')}` — {item.get('event','')} — {item.get('detail','')}")
    path.write_text("\n".join(body).rstrip() + "\n", encoding="utf-8")

print(f"learnings_log={log_path}")
print(f"skill_candidates_dir={candidate_dir}")
PY
