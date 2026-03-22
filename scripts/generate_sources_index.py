#!/usr/bin/env python3
"""Generate a global index for all source mapping files.

This index supports repository-scale governance and quick global health checks.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", default="docs/sources/index.json")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    mappings = sorted((root / "docs/sources").glob("*.skills.json"))

    status_counter: Counter[str] = Counter()
    mapping_rows: list[dict] = []
    total_skills = 0

    for m in mappings:
        data = json.loads(m.read_text(encoding="utf-8"))
        skills = data.get("skills", [])
        total_skills += len(skills)
        local_counter: Counter[str] = Counter(s.get("status", "unknown") for s in skills)
        status_counter.update(local_counter)
        mapping_rows.append(
            {
                "mapping": m.name,
                "source_url": (data.get("video") or {}).get("url"),
                "checked_at": (data.get("video") or {}).get("checked_at"),
                "skill_count": len(skills),
                "status_breakdown": dict(sorted(local_counter.items())),
            }
        )

    payload = {
        "total_mappings": len(mappings),
        "total_skills_tracked": total_skills,
        "global_status_breakdown": dict(sorted(status_counter.items())),
        "mappings": mapping_rows,
    }

    out = root / args.write_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote source index: {out.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
