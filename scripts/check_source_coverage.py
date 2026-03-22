#!/usr/bin/env python3
"""Check provenance coverage: how many local skills are represented in source mappings."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


VALID_TRACKED = {"verified_in_repo", "in_house"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-percent", type=float, default=95.0)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    total_skills = len(list(root.glob("skills/*/*/SKILL.md")))

    tracked: set[str] = set()
    for m in sorted((root / "docs/sources").glob("*.skills.json")):
        data = json.loads(m.read_text(encoding="utf-8"))
        for s in data.get("skills", []):
            if s.get("status") in VALID_TRACKED and s.get("repo_skill"):
                tracked.add(s["repo_skill"])

    covered = len(tracked)
    pct = (covered / total_skills * 100) if total_skills else 0
    print(f"Source coverage: {covered}/{total_skills} ({pct:.2f}%)")

    if pct < args.min_percent:
        print(f"Coverage below threshold: required {args.min_percent:.2f}%")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
