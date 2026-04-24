#!/usr/bin/env python3
"""Check and synchronize upstream changes for tracked skills.

Reads the provenance mapping to find skills with external upstream sources,
checks for newer versions, and optionally applies updates.

Usage:
    # Check only — report which skills have upstream updates
    python scripts/sync_upstream.py --check-only

    # Apply updates — download and replace with upstream versions
    python scripts/sync_upstream.py --apply

    # Dry run — show what would be updated without writing
    python scripts/sync_upstream.py --apply --dry-run

    # Check a specific source only
    python scripts/sync_upstream.py --check-only --source "github:alirezarezvani/claude-skills"
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
PROVENANCE_FILE = REPO_ROOT / "docs" / "sources" / "in-house.skills.json"


def github_raw_url(repo: str, path: str, ref: str = "main") -> str:
    """Construct a GitHub raw content URL."""
    return f"https://raw.githubusercontent.com/{repo}/{ref}/{path}"


def fetch_url(url: str, token: str | None = None) -> str | None:
    """Fetch content from a URL."""
    headers = {"User-Agent": "skills-sync-bot"}
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"    Warning: fetch failed for {url}: {e}", file=sys.stderr)
        fallback = fetch_github_raw_via_api(url, token)
        if fallback is not None:
            return fallback
        return None


def github_api_get(url: str, token: str | None = None) -> dict | None:
    """Make a GET request to GitHub API."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "skills-sync-bot",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"    Warning: API request failed: {e}", file=sys.stderr)
        return None


def fetch_github_raw_via_api(raw_url: str, token: str | None = None) -> str | None:
    """Fallback for raw.githubusercontent.com fetches using GitHub Contents API."""
    m = re.match(r"https://raw\.githubusercontent\.com/([^/]+/[^/]+)/([^/]+)/(.*)", raw_url)
    if not m:
        return None

    repo, ref, path = m.groups()
    api_url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
    data = github_api_get(api_url, token)
    if not data or data.get("type") != "file":
        return None

    content = data.get("content", "")
    if data.get("encoding") == "base64":
        return base64.b64decode(content).decode("utf-8", errors="replace")
    return content


def parse_frontmatter(text: str) -> dict[str, str]:
    """Extract frontmatter key-value pairs."""
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def merge_frontmatter(local_content: str, upstream_content: str) -> str:
    """Merge upstream content body with local frontmatter enrichments.
    
    Strategy: Keep local frontmatter (tags, quality, author, etc.) but take
    upstream body content. Update version and updated_at.
    """
    local_fm = parse_frontmatter(local_content)
    upstream_fm = parse_frontmatter(upstream_content)

    # Extract body from upstream (everything after ---)
    upstream_body_match = re.match(r"^---\s*\n.*?\n---\s*\n(.*)", upstream_content, re.DOTALL)
    upstream_body = upstream_body_match.group(1) if upstream_body_match else upstream_content

    # Build merged frontmatter: upstream basics + local enrichments
    merged_fm = {}
    # From upstream: name, description (authoritative)
    merged_fm["name"] = upstream_fm.get("name", local_fm.get("name", ""))
    merged_fm["description"] = upstream_fm.get("description", local_fm.get("description", ""))
    # From local: enrichments
    for key in ["version", "author", "source", "source_url", "tags", "created_at", "quality", "complexity"]:
        if key in local_fm:
            merged_fm[key] = local_fm[key]
    # Update metadata
    merged_fm["updated_at"] = date.today().isoformat()
    # Bump patch version
    ver = merged_fm.get("version", "1.0.0")
    parts = ver.split(".")
    if len(parts) == 3:
        parts[2] = str(int(parts[2]) + 1)
        merged_fm["version"] = ".".join(parts)

    # Build frontmatter string
    fm_lines = ["---"]
    field_order = ["name", "description", "version", "author", "source", "source_url",
                   "tags", "created_at", "updated_at", "quality", "complexity"]
    for key in field_order:
        if key in merged_fm:
            val = merged_fm[key] if merged_fm[key] != "" else '""'
            # Quote values with special chars
            if isinstance(val, str) and not val.startswith(("[", '"')) and any(c in val for c in ":,#'\"[]"):
                if not val.startswith('"'):
                    val = f'"{val}"'
            fm_lines.append(f"{key}: {val}")
    fm_lines.append("---")
    fm_lines.append("")

    return "\n".join(fm_lines) + upstream_body


def load_skills_with_upstream() -> list[dict]:
    """Load skills that have external upstream sources from frontmatter."""
    results = []
    for skill_md in sorted(SKILLS_DIR.glob("*/*/SKILL.md")):
        content = skill_md.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(content)
        source = fm.get("source", "in-house")
        
        # Only process skills with external sources
        if source.startswith("github:"):
            repo = source.replace("github:", "")
            skill_name = fm.get("name", skill_md.parent.name)
            results.append({
                "name": skill_name,
                "category": skill_md.parent.parent.name,
                "source": source,
                "repo": repo,
                "local_path": skill_md,
                "source_url": fm.get("source_url", ""),
                "local_content": content,
            })
        elif source in ("skills.sh", "clawhub", "community"):
            # These don't have auto-syncable upstreams yet
            pass
    return results


def check_upstream_changes(skill: dict, token: str | None) -> dict | None:
    """Check if upstream has changes for a skill."""
    repo = skill["repo"]
    skill_name = skill["name"]
    
    # Try common paths in the upstream repo
    candidate_paths = [
        f"skills/{skill_name}/SKILL.md",
        f"skills/{skill['category']}/{skill_name}/SKILL.md",
        f"{skill_name}/SKILL.md",
    ]
    
    for path in candidate_paths:
        url = github_raw_url(repo, path)
        upstream_content = fetch_url(url, token)
        if upstream_content and "---" in upstream_content[:10]:
            # Compare content (ignore frontmatter for diff)
            local_body = re.sub(r"^---.*?---\s*", "", skill["local_content"], flags=re.DOTALL).strip()
            upstream_body = re.sub(r"^---.*?---\s*", "", upstream_content, flags=re.DOTALL).strip()
            
            if local_body != upstream_body:
                return {
                    "skill": skill,
                    "upstream_path": path,
                    "upstream_content": upstream_content,
                    "changes": "body_changed",
                }
            else:
                return None  # No changes
    
    return None  # Could not find upstream file


def sync_github_auxiliary_files(skill: dict, upstream_path: str, token: str | None) -> int:
    """Sync non-SKILL.md files that live beside the upstream SKILL.md."""
    repo = skill["repo"]
    upstream_dir = str(Path(upstream_path).parent)
    api_url = f"https://api.github.com/repos/{repo}/contents/{upstream_dir}?ref=main"
    data = github_api_get(api_url, token)
    if not isinstance(data, list):
        return 0

    synced = 0
    local_dir = skill["local_path"].parent
    for item in data:
        if item.get("type") != "file":
            continue
        name = item.get("name", "")
        if name == "SKILL.md" or not name:
            continue
        download_url = item.get("download_url")
        if not download_url:
            continue
        content = fetch_url(download_url, token)
        if content is None:
            continue
        (local_dir / name).write_text(content, encoding="utf-8")
        synced += 1
    return synced


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check and synchronize upstream changes for tracked skills."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-only", action="store_true", help="Only report updates, don't apply")
    group.add_argument("--apply", action="store_true", help="Apply upstream updates to local files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing")
    parser.add_argument("--source", help="Filter to a specific source (e.g. 'github:obra/superpowers')")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    skills = load_skills_with_upstream()
    
    if args.source:
        skills = [s for s in skills if s["source"] == args.source]
    
    print(f"Checking {len(skills)} skills with external upstream sources...")
    
    updates = []
    for skill in skills:
        print(f"  Checking: {skill['name']} ({skill['source']})")
        update = check_upstream_changes(skill, token)
        if update:
            updates.append(update)
            print(f"    → Update available!")
    
    print(f"\n{'='*60}")
    print(f"Results: {len(updates)} updates available out of {len(skills)} checked")
    
    if not updates:
        print("All skills are up to date.")
        return
    
    print("\nSkills with available updates:")
    for u in updates:
        s = u["skill"]
        print(f"  - {s['name']} ({s['category']}) ← {s['source']}")
    
    if args.check_only:
        print("\nRun with --apply to download and apply these updates.")
        return
    
    if args.apply:
        applied = 0
        for u in updates:
            s = u["skill"]
            print(f"\n  Applying update: {s['name']}")
            
            if args.dry_run:
                print(f"    [DRY RUN] Would merge upstream content into {s['local_path']}")
                applied += 1
                continue
            
            merged = merge_frontmatter(s["local_content"], u["upstream_content"])
            s["local_path"].write_text(merged, encoding="utf-8")
            print(f"    Updated: {s['local_path']}")
            if s["source"].startswith("github:"):
                aux_count = sync_github_auxiliary_files(s, u["upstream_path"], token)
                if aux_count:
                    print(f"    Synced auxiliary files: {aux_count}")
            applied += 1
        
        print(f"\nApplied {applied} updates.")
        if not args.dry_run:
            print("Run the full pipeline to regenerate views:")
            print("  python scripts/refresh_repo_views.py")


if __name__ == "__main__":
    main()
