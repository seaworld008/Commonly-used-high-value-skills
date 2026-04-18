#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/hermes-auto-continue-config.sh"

python3 - <<'PY' "$HERMES_AUTO_CONTINUE_PLANNING_MIRROR" "$HERMES_GSD_NEXT_STATE_FILE"
from __future__ import annotations

import json
import sys
from pathlib import Path

mirror_path = Path(sys.argv[1])
gsd_path = Path(sys.argv[2])

try:
    mirror = json.loads(mirror_path.read_text(encoding="utf-8"))
except Exception:
    mirror = {}

try:
    gsd_state = json.loads(gsd_path.read_text(encoding="utf-8"))
except Exception:
    gsd_state = {}

if not gsd_state:
    print("gsd_state_present=no")
    raise SystemExit(0)

mirror["gsd"] = gsd_state
mirror_path.parent.mkdir(parents=True, exist_ok=True)
mirror_path.write_text(json.dumps(mirror, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("gsd_state_present=yes")
print(f"mirror={mirror_path}")
PY
