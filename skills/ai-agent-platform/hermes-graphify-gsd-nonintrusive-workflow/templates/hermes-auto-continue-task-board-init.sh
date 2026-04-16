#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/hermes-auto-continue-config.sh"
hermes_auto_continue_ensure_dirs

force_mode="${1:-}"
if [ -f "$HERMES_AUTO_CONTINUE_TASK_BOARD_FILE" ] && [ "$force_mode" != "--force" ]; then
  echo "task_board_exists=$HERMES_AUTO_CONTINUE_TASK_BOARD_FILE"
  echo "use --force to rebuild"
  exit 0
fi

python3 - <<'PY' "$ROOT" "$HERMES_AUTO_CONTINUE_TASK_BOARD_FILE" "$HERMES_AUTO_CONTINUE_REQUIREMENTS_FILE" "$ROOT/.planning/ROADMAP.md" "$ROOT/.planning/STATE.md"
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
board_path = Path(sys.argv[2])
requirements_path = Path(sys.argv[3])
roadmap_path = Path(sys.argv[4])
state_path = Path(sys.argv[5])


def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def normalize_title(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" -\t")


def collect_candidates(path: Path, label: str) -> list[dict]:
    text = load_text(path)
    if not text:
        return []
    candidates: list[dict] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for prefix in ("- [ ] ", "- ", "* ", "+ "):
            if line.startswith(prefix):
                title = normalize_title(line[len(prefix):])
                if title and len(title) > 6 and title.lower() not in seen:
                    candidates.append({"title": title, "source": f"{label}:{path.name}"})
                    seen.add(title.lower())
                break
        else:
            match = re.match(r"^\d+\.\s+(.+)$", line)
            if match:
                title = normalize_title(match.group(1))
                if title and len(title) > 6 and title.lower() not in seen:
                    candidates.append({"title": title, "source": f"{label}:{path.name}"})
                    seen.add(title.lower())
    return candidates


requirements = collect_candidates(requirements_path, "requirements")
roadmap = collect_candidates(roadmap_path, "roadmap")
state = collect_candidates(state_path, "state")

seed = requirements + roadmap + state
if not seed:
    seed = [
        {
            "title": "Normalize requirements, roadmap, and task board from current project scope",
            "source": "bootstrap:fallback",
        }
    ]

tasks = []
for idx, item in enumerate(seed, start=1):
    tasks.append(
        {
            "id": f"T{idx:03d}",
            "title": item["title"],
            "status": "todo",
            "priority": "p1" if idx == 1 else "p2",
            "depends_on": [] if idx == 1 else [f"T{idx-1:03d}"],
            "summary": "",
            "acceptance": [],
            "artifacts": [],
            "blocked_by": "",
            "notes": "",
            "source": item["source"],
            "owner": "auto",
            "last_updated": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(),
        }
    )

payload = {
    "version": 1,
    "project": root.name,
    "updated_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(),
    "rules": {
        "selection_policy": "Prefer in_progress first, then highest-priority todo whose dependencies are done.",
        "completion_policy": "Only mark done when acceptance is satisfied or the task is explicitly verified.",
        "blocked_policy": "Use blocked when external input or a hard dependency prevents progress.",
    },
    "tasks": tasks,
}

board_path.parent.mkdir(parents=True, exist_ok=True)
board_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(board_path)
PY

if [ -x "$ROOT/scripts/hermes-auto-continue-task-board-sync-docs.sh" ]; then
  bash "$ROOT/scripts/hermes-auto-continue-task-board-sync-docs.sh" >/dev/null 2>&1 || true
fi
