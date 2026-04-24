#!/usr/bin/env python3
"""Build a machine-readable JSON catalog of all skills."""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from generate_repo_banner import generate_banner_from_catalog

REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_frontmatter(text: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            fm[key] = val
    return fm


def parse_tags(val: str) -> list[str]:
    val = val.strip("[]")
    return [t.strip().strip('"').strip("'") for t in val.split(",") if t.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build skills catalog JSON.")
    parser.add_argument("--skills-dir", default="skills")
    parser.add_argument("--output", default="docs/catalog.json")
    args = parser.parse_args()

    skills_dir = REPO_ROOT / args.skills_dir
    output_path = REPO_ROOT / args.output

    categories = defaultdict(int)
    skills = []

    for skill_md in sorted(skills_dir.glob("*/*/SKILL.md")):
        content = skill_md.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(content)
        category = skill_md.parent.parent.name
        skill_name = fm.get("name", skill_md.parent.name)
        
        line_count = len(content.splitlines())
        categories[category] += 1
        
        skills.append({
            "name": skill_name,
            "category": category,
            "description": fm.get("description", ""),
            "version": fm.get("version", "1.0.0"),
            "author": fm.get("author", ""),
            "source": fm.get("source", "in-house"),
            "source_url": fm.get("source_url", ""),
            "tags": parse_tags(fm.get("tags", "")),
            "quality": int(fm.get("quality", "3")),
            "complexity": fm.get("complexity", "intermediate"),
            "created_at": fm.get("created_at", ""),
            "updated_at": fm.get("updated_at", ""),
            "line_count": line_count,
            "path": f"skills/{category}/{skill_md.parent.name}/SKILL.md",
        })

    catalog = {
        "version": "1.0.0",
        "generated_at": __import__("datetime").date.today().isoformat(),
        "total_skills": len(skills),
        "total_categories": len(categories),
        "categories": [
            {"name": cat, "count": count}
            for cat, count in sorted(categories.items(), key=lambda x: -x[1])
        ],
        "skills": skills,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    generate_banner_from_catalog(output_path, REPO_ROOT / ".github" / "assets" / "repo-banner.svg")
    print(f"Wrote catalog: {output_path}")
    print(f"Skills: {len(skills)}, Categories: {len(categories)}")


if __name__ == "__main__":
    main()
