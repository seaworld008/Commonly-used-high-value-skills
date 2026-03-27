#!/usr/bin/env python3
"""Generate a tags index from all skill frontmatter tags."""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_frontmatter(text: str) -> dict:
    """Extract frontmatter fields from SKILL.md content."""
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
    """Parse tags from frontmatter value like '[k8s, devops, container]'."""
    val = val.strip("[]")
    return [t.strip().strip('"').strip("'") for t in val.split(",") if t.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate tags index.")
    parser.add_argument("--skills-dir", default="skills")
    parser.add_argument("--output", default="docs/TAGS-INDEX.md")
    args = parser.parse_args()

    skills_dir = REPO_ROOT / args.skills_dir
    output_path = REPO_ROOT / args.output

    # Collect tags → skills mapping
    tag_map: dict[str, list[dict]] = defaultdict(list)
    
    for skill_md in sorted(skills_dir.glob("*/*/SKILL.md")):
        content = skill_md.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(content)
        name = fm.get("name", skill_md.parent.name)
        desc = fm.get("description", "")
        quality = fm.get("quality", "3")
        tags_str = fm.get("tags", "")
        category = skill_md.parent.parent.name
        
        tags = parse_tags(tags_str)
        if not tags:
            tags = [category]  # Fallback to category name
        
        skill_info = {
            "name": name,
            "description": desc[:80],
            "quality": quality,
            "category": category,
            "path": f"skills/{category}/{skill_md.parent.name}",
        }
        
        for tag in tags:
            tag_map[tag.lower()].append(skill_info)

    # Generate markdown
    lines = [
        "# Tags Index",
        "",
        f"> Auto-generated from {sum(len(v) for v in tag_map.values())} skill-tag mappings across {len(tag_map)} tags.",
        f"> Last updated: see git log.",
        "",
        "## Quick Navigation",
        "",
    ]
    
    # Table of contents
    sorted_tags = sorted(tag_map.keys(), key=lambda t: (-len(tag_map[t]), t))
    for tag in sorted_tags:
        count = len(tag_map[tag])
        lines.append(f"- [`{tag}`](#{tag.replace(' ', '-')}) ({count})")
    lines.append("")
    
    # Detail sections
    lines.append("---")
    lines.append("")
    for tag in sorted_tags:
        skills = sorted(tag_map[tag], key=lambda s: -int(s.get("quality", "3")))
        lines.append(f"## {tag}")
        lines.append("")
        lines.append(f"**{len(skills)} skills**")
        lines.append("")
        lines.append("| Skill | Category | Quality | Description |")
        lines.append("|-------|----------|---------|-------------|")
        for s in skills:
            q = int(s.get("quality", "3"))
            stars = "★" * q + "☆" * (5 - q)
            lines.append(
                f"| [{s['name']}]({s['path']}) | {s['category']} | {stars} | {s['description']} |"
            )
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote tags index: {output_path}")
    print(f"Tags: {len(tag_map)}, Skill-tag mappings: {sum(len(v) for v in tag_map.values())}")


if __name__ == "__main__":
    main()
