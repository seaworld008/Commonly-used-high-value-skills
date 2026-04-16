#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/hermes-auto-continue-config.sh"

python3 - <<'PY' "$HERMES_GSD_LOCAL_ROOT" "$HERMES_GSD_WORKFLOWS_DIR" "$HERMES_GSD_SKILLS_DIR" "$HERMES_GSD_TOOLS_CJS"
from __future__ import annotations

import sys
from pathlib import Path

local_root = Path(sys.argv[1])
workflows_dir = Path(sys.argv[2])
skills_dir = Path(sys.argv[3])
tools_cjs = Path(sys.argv[4])

required_workflows = [
    "map-codebase",
    "new-project",
    "discuss-phase",
    "plan-phase",
    "execute-phase",
    "verify-work",
    "next",
]
required_skills = [
    "gsd-map-codebase",
    "gsd-new-project",
    "gsd-discuss-phase",
    "gsd-plan-phase",
    "gsd-execute-phase",
    "gsd-verify-work",
    "gsd-next",
    "gsd-graphify",
]


def yes(value: bool) -> str:
    return "yes" if value else "no"


print(f"gsd_local_root={local_root}")
print(f"gsd_local_root_exists={yes(local_root.exists())}")
print(f"gsd_workflows_dir={workflows_dir}")
print(f"gsd_workflows_dir_exists={yes(workflows_dir.exists())}")
print(f"gsd_skills_dir={skills_dir}")
print(f"gsd_skills_dir_exists={yes(skills_dir.exists())}")
print(f"gsd_tools_cjs={tools_cjs}")
print(f"gsd_tools_cjs_exists={yes(tools_cjs.exists())}")

missing_workflows = [name for name in required_workflows if not (workflows_dir / f"{name}.md").exists()]
missing_skills = [name for name in required_skills if not (skills_dir / name / "SKILL.md").exists()]

print(f"missing_workflows={','.join(missing_workflows)}")
print(f"missing_skills={','.join(missing_skills)}")
print(f"gsd_phase_engine_ready={yes(not missing_workflows and not missing_skills)}")
PY
