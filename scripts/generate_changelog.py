#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import re
import subprocess
from collections import defaultdict
from pathlib import Path


AUTO_START = "<!-- AUTO-CHANGELOG:START -->"
AUTO_END = "<!-- AUTO-CHANGELOG:END -->"


def update_unreleased(existing: str, body: str) -> str:
    """Replace only our bounded block; fail closed on ambiguous document ownership."""
    headings = list(re.finditer(r"^## \[Unreleased\][^\n]*\n", existing, re.MULTILINE))
    if len(headings) != 1:
        raise ValueError("--preserve-history requires exactly one ## [Unreleased] section")
    section_start = headings[0].end()
    following = re.search(r"^## ", existing[section_start:], re.MULTILINE)
    section_end = section_start + following.start() if following else len(existing)
    block = f"{AUTO_START}\n{body.rstrip()}\n{AUTO_END}"
    start_count, end_count = existing.count(AUTO_START), existing.count(AUTO_END)
    if start_count == end_count == 0:
        # Insert immediately after the heading; everything existing stays byte-for-byte.
        return existing[:section_start] + "\n" + block + "\n" + existing[section_start:]
    if start_count != 1 or end_count != 1:
        raise ValueError("Malformed or duplicate AUTO-CHANGELOG markers; refusing to overwrite history")
    start, end = existing.index(AUTO_START), existing.index(AUTO_END)
    if not section_start <= start < end < section_end:
        raise ValueError("AUTO-CHANGELOG markers must be ordered within the Unreleased section")
    end += len(AUTO_END)
    return existing[:start] + block + existing[end:]


def run_git_command(args: list[str], *, allow_failure: bool = False) -> str:
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
        if allow_failure:
            return ""
        raise SystemExit(f"Git command failed: {' '.join(args)}\n{e.stderr}") from e


def resolve_log_args(since: str, to_ref: str) -> tuple[list[str], str]:
    """Return git-log revision arguments and a human-readable revision range."""
    if since == "last-tag":
        tag = run_git_command(["describe", "--tags", "--abbrev=0", to_ref], allow_failure=True)
        if not tag:
            raise ValueError("Cannot resolve --since last-tag: repository has no reachable tag")
        revision = f"{tag}..{to_ref}"
        return [revision], revision

    verified = run_git_command(
        ["rev-parse", "--verify", "--quiet", f"{since}^{{commit}}"], allow_failure=True
    )
    if verified:
        revision = f"{since}..{to_ref}"
        return [revision], revision
    return [to_ref, f"--since={since}"], f"{since}..{to_ref} (date range)"


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
    parser.add_argument(
        "--since",
        default="last-tag",
        help="Starting tag/ref/date; 'last-tag' resolves the latest reachable tag (default)",
    )
    parser.add_argument("--to", default="HEAD", help="Ending revision (default: HEAD)")
    parser.add_argument("--output", default="CHANGELOG.md", help="Output file (default: CHANGELOG.md)")
    parser.add_argument("--dry-run", action="store_true", help="Only output to console, don't write to file.")
    parser.add_argument(
        "--preserve-history",
        action="store_true",
        help="Update only a managed block in an existing Unreleased section; preserve release history",
    )
    args = parser.parse_args()

    try:
        existing = ""
        if args.preserve_history:
            existing = Path(args.output).read_text(encoding="utf-8")
            update_unreleased(existing, "")  # Validate ownership before invoking Git.
        revisions, revision_label = resolve_log_args(args.since, args.to)
    except (ValueError, OSError) as error:
        parser.error(str(error))

    # Use a real ref range for release changelogs so older history cannot leak in.
    log_output = run_git_command(
        ["log", *revisions, "--pretty=format:%as%x00%s%x00%H"]
    )
    if not log_output and not args.preserve_history:
        print("No commits found.")
        return

    changelog_data = defaultdict(lambda: {"Added": [], "Changed": [], "Fixed": []})

    for line in log_output.splitlines():
        if not line:
            continue
        date, subject, commit_hash = line.split("\0", 2)
        if args.preserve_history:
            changed = run_git_command([
                "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit_hash
            ]).splitlines()
            if changed == ["CHANGELOG.md"]:
                # Otherwise each automated refresh creates the next week's refresh.
                continue
        
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
        f"Revision range: `{revision_label}`.",
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
    if args.preserve_history:
        entries = "\n".join(output_lines[5:])
        # Dates and categories are subordinate to Unreleased, not release-level headings.
        entries = re.sub(r"^(#{2,3}) ", r"##\1 ", entries, flags=re.MULTILINE)
        body = (
            "### 自动更新 / Automated updates\n\n"
            f"变更范围 / Revision range: `{revision_label}`.\n\n"
            + (entries or "此范围内暂无可归类的变更。 / No categorized changes in this range.\n")
        )
        content = update_unreleased(existing, body)

    if args.dry_run:
        print(content)
    else:
        Path(args.output).write_text(content, encoding="utf-8")
        print(f"Changelog generated: {args.output}")

if __name__ == "__main__":
    main()
