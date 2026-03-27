#!/usr/bin/env python3
"""Register a new skill into the repository's provenance system.

This script handles the "last mile" of skill ingestion:
1. Validates the SKILL.md exists and has required frontmatter
2. Enriches frontmatter with missing fields (source, tags, dates)
3. Updates the provenance mapping (in-house.skills.json)
4. Optionally runs the full refresh pipeline

Usage:
    # Register a single skill
    python scripts/ingest_skill.py --dir skills/developer-engineering/vue-composition-api --source "github:vuejs/vue"

    # Register with explicit category and source URL
    python scripts/ingest_skill.py --dir skills/devops-sre/ansible-expert --source "skills.sh" --source-url "https://skills.sh/s/ansible"

    # Batch register all untracked skills
    python scripts/ingest_skill.py --batch

    # Dry run (show what would be done without writing)
    python scripts/ingest_skill.py --batch --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
PROVENANCE_FILE = REPO_ROOT / "docs" / "sources" / "in-house.skills.json"


def parse_frontmatter(text: str) -> dict[str, str]:
    """Extract frontmatter key-value pairs from SKILL.md content."""
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def update_frontmatter_field(content: str, key: str, value: str) -> str:
    """Add or update a single frontmatter field."""
    m = re.match(r"^(---\s*\n)(.*?)(\n---)", content, re.DOTALL)
    if not m:
        return content
    header, fm_body, footer = m.group(1), m.group(2), m.group(3)

    # Check if key already exists
    pattern = re.compile(rf"^{re.escape(key)}:\s*.*$", re.MULTILINE)
    if pattern.search(fm_body):
        # Update existing
        fm_body = pattern.sub(f"{key}: {value}", fm_body)
    else:
        # Add before closing ---
        fm_body = fm_body.rstrip() + f"\n{key}: {value}"

    return header + fm_body + footer + content[m.end():]


def get_tracked_skills(provenance_path: Path) -> set[str]:
    """Return set of skill names already in the provenance file."""
    if not provenance_path.exists():
        return set()
    data = json.loads(provenance_path.read_text(encoding="utf-8"))
    return {
        entry.get("video_name", "")
        for entry in data.get("skills", [])
    }


def find_untracked_skills(skills_dir: Path, tracked: set[str]) -> list[Path]:
    """Find skills that exist on disk but are not in the provenance mapping."""
    untracked = []
    for skill_md in sorted(skills_dir.glob("*/*/SKILL.md")):
        skill_name = skill_md.parent.name
        if skill_name not in tracked:
            untracked.append(skill_md.parent)
    return untracked


def get_git_created_date(filepath: Path) -> str:
    """Get the first commit date for a file from git log."""
    try:
        result = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%aI", "--", str(filepath)],
            capture_output=True, text=True, cwd=REPO_ROOT, timeout=10
        )
        if result.stdout.strip():
            return result.stdout.strip().split("T")[0]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return date.today().isoformat()


def ingest_one(skill_dir: Path, source: str, source_url: str, dry_run: bool) -> bool:
    """Ingest a single skill directory."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print(f"  ERROR: {skill_md} does not exist", file=sys.stderr)
        return False

    content = skill_md.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(content)

    if not fm.get("name"):
        print(f"  ERROR: {skill_dir.name} — missing 'name' in frontmatter", file=sys.stderr)
        return False

    skill_name = fm["name"]
    category = skill_dir.parent.name
    today = date.today().isoformat()

    print(f"  Ingesting: {skill_name} ({category})")

    if dry_run:
        print(f"    [DRY RUN] Would enrich frontmatter and update provenance")
        return True

    # Enrich frontmatter with source info
    updated = content
    if not fm.get("source") or fm.get("source") == "in-house":
        if source:
            updated = update_frontmatter_field(updated, "source", f'"{source}"')
    if not fm.get("source_url") and source_url:
        updated = update_frontmatter_field(updated, "source_url", f'"{source_url}"')
    if not fm.get("created_at"):
        created = get_git_created_date(skill_md)
        updated = update_frontmatter_field(updated, "created_at", f'"{created}"')
    if not fm.get("updated_at"):
        updated = update_frontmatter_field(updated, "updated_at", f'"{today}"')

    if updated != content:
        skill_md.write_text(updated, encoding="utf-8")
        print(f"    Updated frontmatter")

    return True


def run_pipeline(dry_run: bool) -> None:
    """Run the post-ingestion pipeline."""
    if dry_run:
        print("\n[DRY RUN] Would run pipeline scripts")
        return

    print("\nRunning post-ingestion pipeline...")
    scripts = [
        ["python", "scripts/enrich_frontmatter.py"],
        ["python", "scripts/bootstrap_in_house_sources.py", "--write-json", "docs/sources/in-house.skills.json"],
        ["python", "scripts/refresh_repo_views.py"],
        ["python", "scripts/generate_tags_index.py"],
        ["python", "scripts/build_catalog_json.py"],
    ]
    for cmd in scripts:
        print(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"    WARNING: {cmd[1]} returned {result.returncode}", file=sys.stderr)
            if result.stderr:
                print(f"    {result.stderr.strip()[:200]}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Register new skills into the repository's provenance system.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --dir skills/developer-engineering/vue-expert --source "github:vuejs/vue"
  %(prog)s --batch --dry-run
  %(prog)s --batch --source "community"
        """
    )
    parser.add_argument("--dir", type=Path, help="Path to the skill directory to ingest")
    parser.add_argument("--source", default="in-house",
                        help="Source identifier (in-house, skills.sh, clawhub, github:<owner>/<repo>, community)")
    parser.add_argument("--source-url", default="", help="Original source URL")
    parser.add_argument("--batch", action="store_true",
                        help="Batch ingest all untracked skills")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without writing")
    parser.add_argument("--skip-pipeline", action="store_true",
                        help="Skip the post-ingestion pipeline")
    args = parser.parse_args()

    if not args.dir and not args.batch:
        parser.error("Specify --dir <path> for single ingestion or --batch for all untracked skills")

    success_count = 0
    fail_count = 0

    if args.batch:
        tracked = get_tracked_skills(PROVENANCE_FILE)
        untracked = find_untracked_skills(SKILLS_DIR, tracked)
        print(f"Found {len(untracked)} untracked skills (out of {len(tracked)} tracked)")
        for skill_dir in untracked:
            ok = ingest_one(skill_dir, args.source, args.source_url, args.dry_run)
            if ok:
                success_count += 1
            else:
                fail_count += 1
    else:
        skill_dir = REPO_ROOT / args.dir if not args.dir.is_absolute() else args.dir
        ok = ingest_one(skill_dir, args.source, args.source_url, args.dry_run)
        if ok:
            success_count += 1
        else:
            fail_count += 1

    print(f"\nIngestion complete: {success_count} succeeded, {fail_count} failed")

    if success_count > 0 and not args.skip_pipeline:
        run_pipeline(args.dry_run)


if __name__ == "__main__":
    main()
