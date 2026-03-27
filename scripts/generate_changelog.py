#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import re
import subprocess
from collections import defaultdict
from pathlib import Path

def run_git_command(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8"
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {' '.join(args)}")
        print(e.stderr)
        return ""

def get_skill_info(skill_path_str: str) -> tuple[str, str, str]:
    """Extract category, skill_id and basic info from SKILL.md path."""
    path = Path(skill_path_str)
    # Expected: skills/{category}/{skill_id}/SKILL.md
    parts = path.parts
    if len(parts) >= 4 and parts[0] == "skills":
        category = parts[1]
        skill_id = parts[2]
        
        # Try to read the name from the file
        name = skill_id
        description = ""
        if path.exists():
            content = path.read_text(encoding="utf-8")
            # Simple regex to find name and description in frontmatter
            name_match = re.search(r"^name:\s*(.*)$", content, re.MULTILINE)
            desc_match = re.search(r"^description:\s*(.*)$", content, re.MULTILINE)
            if name_match:
                name = name_match.group(1).strip().strip('"').strip("'")
            if desc_match:
                description = desc_match.group(1).strip().strip('"').strip("'")
        
        return category, skill_id, f"`{skill_id}` ({category}) — {name}"
    return "", "", ""

def main():
    parser = argparse.ArgumentParser(description="Generate CHANGELOG.md from git log.")
    parser.add_argument("--since", default="1 month ago", help="Starting commit/tag/date (default: '1 month ago')")
    parser.add_argument("--output", default="CHANGELOG.md", help="Output file (default: CHANGELOG.md)")
    parser.add_argument("--dry-run", action="store_true", help="Only output to console, don't write to file.")
    args = parser.parse_args()

    # Get commit log: date|subject|hash
    log_output = run_git_command(["log", f"--since={args.since}", "--pretty=format:%as|%s|%H"])
    if not log_output:
        print("No commits found.")
        return

    changelog_data = defaultdict(lambda: {"Added": [], "Changed": [], "Fixed": []})

    for line in log_output.splitlines():
        if not line:
            continue
        date, subject, commit_hash = line.split("|", 2)
        
        # Check for added skills in this commit
        diff_output = run_git_command(["diff-tree", "--no-commit-id", "--name-only", "-r", "--diff-filter=A", commit_hash])
        added_skills = []
        for file_path in diff_output.splitlines():
            if file_path.endswith("SKILL.md") and file_path.startswith("skills/"):
                _, _, info = get_skill_info(file_path)
                if info:
                    added_skills.append(info)
        
        if added_skills:
            changelog_data[date]["Added"].extend(added_skills)
        
        # Categorize other changes
        # Subject format usually: feat: description, fix: description, etc.
        clean_subject = subject.strip()
        if clean_subject.lower().startswith("feat"):
            msg = re.sub(r"^feat(\(.*\))?:\s*", "", clean_subject, flags=re.IGNORECASE)
            changelog_data[date]["Changed"].append(msg)
        elif clean_subject.lower().startswith("fix"):
            msg = re.sub(r"^fix(\(.*\))?:\s*", "", clean_subject, flags=re.IGNORECASE)
            changelog_data[date]["Fixed"].append(msg)
        elif clean_subject.lower().startswith("docs"):
            msg = re.sub(r"^docs(\(.*\))?:\s*", "", clean_subject, flags=re.IGNORECASE)
            changelog_data[date]["Changed"].append(msg)
        elif clean_subject.lower().startswith("refactor") or clean_subject.lower().startswith("chore"):
            # Optional: group these under Changed or ignore
            msg = re.sub(r"^(refactor|chore)(\(.*\))?:\s*", "", clean_subject, flags=re.IGNORECASE)
            changelog_data[date]["Changed"].append(msg)

    # Build Markdown
    output_lines = [
        "# Changelog",
        "",
        "All notable changes to this repository are documented here.",
        ""
    ]

    for date in sorted(changelog_data.keys(), reverse=True):
        output_lines.append(f"## [{date}]")
        output_lines.append("")
        
        for section in ["Added", "Changed", "Fixed"]:
            items = changelog_data[date][section]
            if items:
                # Remove duplicates while preserving order
                seen = set()
                unique_items = [x for x in items if not (x in seen or seen.add(x))]
                
                output_lines.append(f"### {section}")
                for item in unique_items:
                    output_lines.append(f"- {item}")
                output_lines.append("")

    content = "\n".join(output_lines)

    if args.dry_run:
        print(content)
    else:
        Path(args.output).write_text(content, encoding="utf-8")
        print(f"Changelog generated: {args.output}")

if __name__ == "__main__":
    main()
