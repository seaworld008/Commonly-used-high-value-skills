#!/usr/bin/env python3
"""Bootstrap an in-house provenance mapping for all local skills.

This ensures global source coverage even before external-source mappings are completed.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path


def parse_frontmatter_name(skill_md: Path) -> str:
    text = skill_md.read_text(encoding="utf-8")
    m = re.search(r"^name:\s*['\"]?([^'\"\n]+)['\"]?\s*$", text, re.MULTILINE)
    if not m:
        raise ValueError(f"Missing frontmatter name in {skill_md}")
    return m.group(1).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", default="docs/sources/in-house.skills.json")
    parser.add_argument("--repo-url", default="https://github.com/your-org/Commonly-used-high-value-skills")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    today = date.today().isoformat()
    skill_files = sorted(root.glob("skills/*/*/SKILL.md"))

    skills = []
    for sf in skill_files:
        name = parse_frontmatter_name(sf)
        rel = sf.relative_to(root).as_posix()
        skills.append(
            {
                "video_name": name,
                "normalized_slug": name,
                "status": "in_house",
                "repo_skill": rel,
                "source": args.repo_url,
                "notes": "In-house canonical skill (local repository source of truth).",
                "upstream": {
                    "repo": "local-repo/in-house",
                    "path": rel.rsplit("/", 1)[0],
                    "ref": "main",
                    "last_checked_at": today,
                    "last_synced_at": today,
                    "last_synced_commit": None,
                },
            }
        )

    payload = {
        "video": {
            "url": args.repo_url,
            "checked_at": today,
            "note": "Auto-generated in-house provenance mapping for all local skills.",
        },
        "official_references": [
            {
                "name": "Repository canonical skills tree",
                "url": args.repo_url,
                "purpose": "Marks local source-of-truth skills as in_house.",
            }
        ],
        "skills": skills,
        "verification_attempts": [
            {
                "date": today,
                "method": "local-scan",
                "target": "skills/*/*/SKILL.md",
                "result": "success",
                "evidence": f"Discovered {len(skills)} local skills",
            }
        ],
    }

    out = root / args.write_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote in-house mapping: {out.relative_to(root)}")
    print(f"Skills mapped: {len(skills)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
