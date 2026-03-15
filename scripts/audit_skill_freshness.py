#!/usr/bin/env python3
"""Local-first skill freshness audit.

Why this script exists:
- Avoid per-skill online probing (which may trigger provider risk controls).
- Enforce local install-command conventions.
- Optionally compare local skill set against a single pre-fetched snapshot file.

Usage examples:
  python3 scripts/audit_skill_freshness.py
  python3 scripts/audit_skill_freshness.py --snapshot /path/to/clawhub_skills_snapshot.json

Snapshot format (JSON):
  {
    "skills": ["agent-browser", "weather", "..."],
    "captured_at": "2026-03-15T12:00:00Z",
    "source": "manual export / one-shot API dump"
  }
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SKILL_FILES = sorted(ROOT.glob("skills/*/*/SKILL.md"))

PINNED_RE = re.compile(r"npx\s+clawhub@(?!latest)([^\s]+)\s+install\s+", re.IGNORECASE)
PLAIN_RE = re.compile(r"(?:^|\n)\s*clawhub\s+install\s+", re.IGNORECASE)
LATEST_RE = re.compile(r"npx\s+clawhub@latest\s+install\s+", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit skill freshness without per-skill online requests.")
    parser.add_argument(
        "--snapshot",
        type=Path,
        help="Optional JSON snapshot containing a `skills` list fetched in one batch by trusted means.",
    )
    return parser.parse_args()


def local_skill_names(skill_files: Iterable[Path]) -> set[str]:
    return {path.parent.name for path in skill_files}


def parse_snapshot(snapshot_path: Path) -> set[str]:
    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("skills"), list):
        skills = data["skills"]
    elif isinstance(data, list):
        skills = data
    else:
        raise ValueError("Snapshot must be a JSON list or an object containing a `skills` list.")

    normalized = {str(item).strip() for item in skills if str(item).strip()}
    if not normalized:
        raise ValueError("Snapshot contains no skill names.")
    return normalized


def main() -> int:
    args = parse_args()

    pinned: list[Path] = []
    plain: list[Path] = []
    latest = 0

    for file in SKILL_FILES:
        text = file.read_text(encoding="utf-8")
        if LATEST_RE.search(text):
            latest += 1
        if PINNED_RE.search(text):
            pinned.append(file)
        if PLAIN_RE.search(text):
            plain.append(file)

    print(f"skills scanned: {len(SKILL_FILES)}")
    print(f"using npx clawhub@latest install: {latest}")
    print(f"pinned clawhub versions found: {len(pinned)}")
    print(f"plain 'clawhub install' commands found: {len(plain)}")

    if pinned:
        print("\nPinned versions to review:")
        for f in pinned:
            print(f"- {f.relative_to(ROOT)}")

    if plain:
        print("\nPlain install commands (consider npx clawhub@latest for consistency):")
        for f in plain:
            print(f"- {f.relative_to(ROOT)}")

    if args.snapshot:
        snapshot_skills = parse_snapshot(args.snapshot)
        local_skills = local_skill_names(SKILL_FILES)

        missing_in_repo = sorted(snapshot_skills - local_skills)
        extra_in_repo = sorted(local_skills - snapshot_skills)

        print(f"\nsnapshot skills: {len(snapshot_skills)}")
        print(f"missing in repo vs snapshot: {len(missing_in_repo)}")
        print(f"extra in repo vs snapshot: {len(extra_in_repo)}")

        if missing_in_repo:
            print("\nMissing in repo (present in snapshot):")
            for name in missing_in_repo:
                print(f"- {name}")

    # Non-zero for pinned versions only; snapshot diff is advisory and printed for planning.
    return 1 if pinned else 0


if __name__ == "__main__":
    raise SystemExit(main())
