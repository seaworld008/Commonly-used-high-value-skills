#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/hermes-auto-continue-config.sh"

python3 - <<'PY' "$ROOT/.planning/STATE.md" "$ROOT/.planning/ROADMAP.md" "$ROOT/.planning/phases" "$HERMES_GSD_NEXT_STATE_FILE"
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

state_path = Path(sys.argv[1])
roadmap_path = Path(sys.argv[2])
phases_root = Path(sys.argv[3])
output_path = Path(sys.argv[4])


def parse_frontmatter(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            result[k.strip()] = v.strip().strip("'").strip('"')
    return result


def parse_phase_number(raw: str) -> tuple:
    if not raw:
        return (9999,)
    return tuple(int(part) for part in raw.split(".") if part.isdigit())


def roadmap_phase_entries(path: Path) -> list[tuple[str, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []
    entries: list[tuple[str, str]] = []
    pattern = re.compile(r"^###\s+Phase\s+([0-9]+(?:\.[0-9]+)?)\s*:\s*(.+?)\s*$", re.MULTILINE)
    for match in pattern.finditer(text):
        entries.append((match.group(1), match.group(2).strip()))
    return entries


def phase_dir_for(phase: str) -> Path | None:
    if not phases_root.exists():
        return None
    prefix = phase.zfill(2) if "." not in phase and len(phase) < 2 else phase
    for child in phases_root.iterdir():
        if child.is_dir() and child.name.startswith(prefix + "-"):
            return child
    return None


def has_any(path: Path | None, suffix: str) -> bool:
    return bool(path and any(path.glob(f"*{suffix}")))


state = parse_frontmatter(state_path)
roadmap_entries = roadmap_phase_entries(roadmap_path)
roadmap_entries.sort(key=lambda item: parse_phase_number(item[0]))

payload: dict[str, str] = {}

if not roadmap_entries:
    payload = {
        "gsd_state_present": "no",
        "gsd_next_step": "new-project",
        "gsd_next_command": "$gsd-new-project",
        "gsd_next_reason": "no_roadmap",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for key, value in payload.items():
        print(f"{key}={value}")
    raise SystemExit(0)

current_phase = state.get("phase", "").strip()
if not current_phase:
    current_phase = roadmap_entries[0][0]

phase_numbers = [phase for phase, _ in roadmap_entries]
if current_phase not in phase_numbers:
    current_phase = roadmap_entries[0][0]

phase_index = phase_numbers.index(current_phase)
phase_name = roadmap_entries[phase_index][1]
phase_dir = phase_dir_for(current_phase)

has_context = has_any(phase_dir, "-CONTEXT.md") or has_any(phase_dir, "-RESEARCH.md")
has_plan = has_any(phase_dir, "-PLAN.md")
has_summary = has_any(phase_dir, "-SUMMARY.md")
state_status = state.get("status", "unknown")
paused = bool(state.get("paused_at"))

next_step = ""
next_command = ""
next_reason = ""
next_phase = current_phase

if paused:
    next_step = "resume"
    next_command = "$gsd-resume-work"
    next_reason = "state_paused"
elif not phases_root.exists() or not phase_dir:
    next_step = "discuss"
    next_command = f"$gsd-discuss-phase {current_phase}"
    next_reason = "phase_dir_missing"
elif not has_context:
    next_step = "discuss"
    next_command = f"$gsd-discuss-phase {current_phase}"
    next_reason = "missing_context"
elif not has_plan:
    next_step = "plan"
    next_command = f"$gsd-plan-phase {current_phase}"
    next_reason = "missing_plans"
elif has_plan and not has_summary:
    next_step = "execute"
    next_command = f"$gsd-execute-phase {current_phase}"
    next_reason = "plans_without_summaries"
else:
    if phase_index + 1 < len(roadmap_entries):
        next_phase = roadmap_entries[phase_index + 1][0]
        next_step = "verify"
        next_command = f"$gsd-verify-work {current_phase}"
        next_reason = "phase_summaries_present"
    else:
        next_step = "complete"
        next_command = "$gsd-complete-milestone"
        next_reason = "all_phases_complete_candidate"

payload = {
    "gsd_state_present": "yes",
    "current_phase": current_phase,
    "current_phase_name": phase_name,
    "state_status": state_status,
    "phase_dir": str(phase_dir) if phase_dir else "",
    "phase_has_context": "yes" if has_context else "no",
    "phase_has_plan": "yes" if has_plan else "no",
    "phase_has_summary": "yes" if has_summary else "no",
    "gsd_next_step": next_step,
    "gsd_next_phase": next_phase,
    "gsd_next_command": next_command,
    "gsd_next_reason": next_reason,
}
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
for key, value in payload.items():
    print(f"{key}={value}")
PY

if [ -x "$ROOT/scripts/hermes-gsd-sync-runtime-mirror.sh" ]; then
  bash "$ROOT/scripts/hermes-gsd-sync-runtime-mirror.sh" >/dev/null 2>&1 || true
fi
