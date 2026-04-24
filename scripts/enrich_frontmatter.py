#!/usr/bin/env python3
"""Enrich skill frontmatter with missing fields and normalized metadata.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from collections import Counter
from pathlib import Path

# Mapping skill directory names to source
NEW_SKILLS_MAP = {
    "kubernetes-specialist": "skills.sh",
    "docker-expert": "skills.sh",
    "aws-solution-architect": "skills.sh",
    "terraform-engineer": "skills.sh",
    "nextjs-app-router": "skills.sh",
    "supabase-postgres": "skills.sh",
    "tailwind-design-system": "skills.sh",
    "python-performance": "skills.sh",
    "rust-engineer": "skills.sh",
    "senior-architect": "github:alirezarezvani/claude-skills",
    "skill-security-auditor": "github:alirezarezvani/claude-skills",
    "landing-page-generator": "github:alirezarezvani/claude-skills",
    "saas-metrics-coach": "github:alirezarezvani/claude-skills",
    "agent-hub": "github:alirezarezvani/claude-skills",
    "systematic-debugging": "github:obra/superpowers",
    "test-driven-development": "github:obra/superpowers",
    "subagent-driven-development": "github:obra/superpowers",
    "typescript-best-practices": "community",
    "graphql-expert": "community",
    "web-scraper": "community",
    "context-engineering": "community",
    "confidence-check": "community",
    "supermemory": "community",
    "seo-audit": "community",
}

# Category name to initial tags
CATEGORY_TAGS = {
    "developer-engineering": ["development"],
    "devops-sre": ["devops", "sre"],
    "finance-investing": ["finance"],
    "growth-operations-xiaohongshu": ["marketing", "growth"],
    "security-and-reliability": ["security"],
    "ai-agent-platform": ["ai", "agent"],
    "ai-workflow": ["ai", "agent", "workflow"],
    "product-design": ["product", "design"],
    "operations-general": ["productivity"],
    "task-understanding-decomposition": ["planning", "workflow"],
    "engineering-workflow-automation": ["automation", "workflow"],
    "deployment-platforms": ["deployment"],
    "office-automation": ["office", "automation"],
    "media-and-content": ["content", "media"],
}

FIELD_ORDER = [
    "name", "description", "version", "author", "source", "source_url",
    "tags", "created_at", "updated_at", "quality", "complexity"
]

def get_git_date(filepath: Path, first: bool = False) -> str | None:
    """Get the first or last commit date for a file via git."""
    cmd = ["git", "log", "-1", "--format=%aI", "--", str(filepath)]
    if first:
        # Use --diff-filter=A to find the commit where the file was added
        cmd = ["git", "log", "--diff-filter=A", "--format=%aI", "--", str(filepath)]
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        out = res.stdout.strip()
        
        # If diff-filter=A yielded nothing (e.g. file was moved), fall back to oldest commit in log
        if not out and first:
            res = subprocess.run(["git", "log", "--format=%aI", "--", str(filepath)], capture_output=True, text=True, check=True)
            lines = res.stdout.strip().splitlines()
            out = lines[-1] if lines else ""
            
        if out:
            return out[:10]  # Return YYYY-MM-DD
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return None

def quote_value(value: str) -> str:
    """Quote value if it contains special characters or is empty."""
    if not value:
        return '""'
    # If already quoted with double or single quotes, return as is
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value
    # Check for special characters that require quoting in YAML
    if any(char in value for char in ":#'\""):
        # Escape existing double quotes if we use double quotes
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value

def format_tags(tags: list[str]) -> str:
    """Format tags as a YAML list [ "tag1", "tag2" ]."""
    return "[" + ", ".join(f'"{t}"' for t in sorted(set(tags))) + "]"

def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich SKILL.md frontmatter with missing metadata.")
    parser.add_argument("--skills-dir", default="skills", help="Root directory for skills (default: skills)")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without writing files")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    skills_root = root / args.skills_dir
    
    if not skills_root.exists():
        print(f"Error: Skills directory not found at {skills_root}")
        return 1

    stats = Counter()
    total_files = 0

    # Glob for skills/*/*/SKILL.md
    for skill_file in skills_root.glob("*/*/SKILL.md"):
        total_files += 1
        try:
            content = skill_file.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Error reading {skill_file}: {e}")
            continue
        
        # Extract frontmatter and body
        # We look for --- at the start and the next ---
        match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)", content, re.DOTALL)
        if not match:
            print(f"Skipping {skill_file.relative_to(root)}: No YAML frontmatter found.")
            continue
            
        fm_text = match.group(1)
        body = match.group(2)

        # Parse existing fields, preserving nested (indented) blocks verbatim.
        # A "nested block" is a top-level key whose value spans subsequent
        # indented lines (e.g. `metadata:\n  hermes:\n    tags: [...]`).
        # These must not be flattened or we lose structured metadata.
        fm_data: dict[str, str] = {}
        nested_blocks: dict[str, list[str]] = {}
        current_top_key: str | None = None
        for line in fm_text.splitlines():
            if line and (line[0] == " " or line[0] == "\t"):
                # Indented continuation — belongs to the most recent top-level key.
                if current_top_key is not None:
                    nested_blocks.setdefault(current_top_key, []).append(line)
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                current_top_key = k.strip()
                fm_data[current_top_key] = v.strip()
        
        # 1. Fill missing fields or apply defaults
        if "version" not in fm_data:
            fm_data["version"] = '"1.0.0"'
            stats["version_added"] += 1
            
        if "author" not in fm_data:
            fm_data["author"] = '"seaworld008"'
            stats["author_added"] += 1
            
        if "source_url" not in fm_data:
            fm_data["source_url"] = '""'
            stats["source_url_added"] += 1
            
        if "complexity" not in fm_data:
            fm_data["complexity"] = '"intermediate"'
            stats["complexity_added"] += 1
            
        # 2. Source Inference
        skill_dir_name = skill_file.parent.name
        if "source" not in fm_data:
            source = NEW_SKILLS_MAP.get(skill_dir_name, "in-house")
            fm_data["source"] = f'"{source}"'
            stats["source_added"] += 1
            
        # 3. Tags Inference
        if "tags" not in fm_data:
            category_name = skill_file.parent.parent.name
            tags = CATEGORY_TAGS.get(category_name, []).copy()
            # Extract keywords from skill directory name (split by -)
            keywords = [p for p in skill_dir_name.split("-") if len(p) > 2][:3]
            tags.extend(keywords)
            fm_data["tags"] = format_tags(tags)
            stats["tags_added"] += 1
            
        # 4. Dates using Git
        if "created_at" not in fm_data:
            date = get_git_date(skill_file, first=True)
            if not date:
                date = "2026-03-27"
            fm_data["created_at"] = f'"{date}"'
            stats["created_at_added"] += 1
            
        if "updated_at" not in fm_data:
            date = get_git_date(skill_file, first=False)
            if not date:
                # Use created_at value if updated_at is missing from git
                date = fm_data["created_at"].strip('"')
            fm_data["updated_at"] = f'"{date}"'
            stats["updated_at_added"] += 1
            
        # 5. Quality (based on line count of the whole file)
        if "quality" not in fm_data:
            line_count = len(content.splitlines())
            if line_count < 50:
                q = 2
            elif line_count < 100:
                q = 3
            elif line_count < 200:
                q = 4
            else:
                q = 5
            fm_data["quality"] = str(q)
            stats["quality_added"] += 1
            
        # Special handling for name and description quoting
        if "name" in fm_data:
            fm_data["name"] = quote_value(fm_data["name"])
        if "description" in fm_data:
            fm_data["description"] = quote_value(fm_data["description"])
            
        # Construct new frontmatter with fixed field order. Preserve any
        # nested block (indented continuation lines) attached to a key.
        def _emit(field: str) -> list[str]:
            val = fm_data[field]
            lines_out = [f"{field}: {val}" if val != "" else f"{field}:"]
            for cont in nested_blocks.get(field, []):
                lines_out.append(cont)
            return lines_out

        new_fm_lines: list[str] = []
        for field in FIELD_ORDER:
            if field in fm_data:
                new_fm_lines.extend(_emit(field))

        # Add any other fields that might have existed but aren't in FIELD_ORDER
        for k in fm_data:
            if k not in FIELD_ORDER:
                new_fm_lines.extend(_emit(k))
                
        new_fm_text = "---\n" + "\n".join(new_fm_lines) + "\n---\n"
        new_content = new_fm_text + body
        
        # Write back if changed
        # Normalize line endings to \n for consistency if needed, but here we just write
        if new_content.replace("\r\n", "\n") != content.replace("\r\n", "\n"):
            if args.dry_run:
                print(f"[DRY-RUN] Would update {skill_file.relative_to(root)}")
                stats["files_to_update"] += 1
            else:
                skill_file.write_text(new_content, encoding="utf-8")
                stats["files_updated"] += 1
        else:
            stats["files_unchanged"] += 1

    print("\nProcessing stats:")
    print(f"Total SKILL.md files found: {total_files}")
    for key in sorted(stats.keys()):
        print(f"  {key}: {stats[key]}")
    
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
