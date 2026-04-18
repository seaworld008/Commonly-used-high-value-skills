#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/hermes-auto-continue-config.sh"
cd "$ROOT"

python3 - <<'PY' "$ROOT" "$HERMES_GRAPHIFY_HINTS_FILE" "$HERMES_GSD_NEXT_STATE_FILE"
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
hints_path = Path(sys.argv[2])
gsd_state_path = Path(sys.argv[3])


def git_changed_files() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", "--"],
            capture_output=True,
            text=True,
            check=False,
            cwd=root,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []


changed = git_changed_files()
top_dirs = sorted({path.split("/", 1)[0] for path in changed if "/" in path})

try:
    gsd_state = json.loads(gsd_state_path.read_text(encoding="utf-8"))
except Exception:
    gsd_state = {}

hints: list[dict] = []

if len(top_dirs) >= 3:
    hints.append(
        {
            "kind": "graphify-path",
            "reason": "diff spans 3+ top-level directories",
            "suggested_command": "bash scripts/ai-workflow.sh graphify-path <nodeA> <nodeB>",
        }
    )

cross_layer_markers = {"src", "src-tauri", "app", "server", "packages", "backend", "frontend"}
if len(cross_layer_markers.intersection(set(top_dirs))) >= 2:
    hints.append(
        {
            "kind": "graphify-query",
            "reason": "changed files cross application layers",
            "suggested_command": "bash scripts/ai-workflow.sh graphify-query \"What is the dependency path between the changed layers?\"",
        }
    )

if gsd_state.get("gsd_next_step") in {"discuss", "plan"}:
    hints.append(
        {
            "kind": "graphify-explain",
            "reason": f"GSD next step is {gsd_state.get('gsd_next_step')}",
            "suggested_command": "bash scripts/ai-workflow.sh graphify-explain <node>",
        }
    )

if not gsd_state or gsd_state.get("gsd_next_reason") in {"phase_dir_missing", "missing_context", "missing_plans"}:
    hints.append(
        {
            "kind": "graphify-wiki",
            "reason": "brownfield or sparse planning context",
            "suggested_command": "bash scripts/ai-workflow.sh graphify-wiki",
        }
    )

payload = {
    "changed_files": changed,
    "top_dirs": top_dirs,
    "gsd": gsd_state,
    "hints": hints,
}
hints_path.parent.mkdir(parents=True, exist_ok=True)
hints_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(f"hints_file={hints_path}")
print(f"hint_count={len(hints)}")
for idx, hint in enumerate(hints, start=1):
    print(f"hint_{idx}_kind={hint['kind']}")
    print(f"hint_{idx}_reason={hint['reason']}")
    print(f"hint_{idx}_command={hint['suggested_command']}")
PY
