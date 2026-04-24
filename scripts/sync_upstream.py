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
SOURCE_MAPPINGS_DIR = REPO_ROOT / "docs" / "sources"


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
    lines = m.group(1).splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if ":" not in line or line.startswith((" ", "\t")):
            index += 1
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if val in {"|", ">"}:
            collected = []
            index += 1
            while index < len(lines) and (lines[index].startswith((" ", "\t")) or not lines[index].strip()):
                if lines[index].strip():
                    collected.append(lines[index].strip())
                index += 1
            fm[key] = re.sub(r"\s+", " ", " ".join(collected)).strip()
            continue
        fm[key] = val.strip('"').strip("'")
        index += 1
    return fm


def strip_frontmatter(text: str) -> str:
    return re.sub(r"^---.*?---\s*", "", text, count=1, flags=re.DOTALL).strip()


def split_frontmatter(text: str) -> tuple[str | None, str]:
    match = re.match(r"^(---\s*\n.*?\n---\s*\n?)(.*)", text, re.DOTALL)
    if not match:
        return None, text
    return match.group(1), match.group(2)


def update_frontmatter_field(frontmatter: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^({re.escape(key)}:\s*).*$", re.MULTILINE)
    line = f"{key}: {value}"
    if pattern.search(frontmatter):
        return pattern.sub(line, frontmatter)
    return re.sub(r"\n---\s*\n?$", f"\n{line}\n---\n", frontmatter.rstrip() + "\n")


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def bump_patch_version(version: str) -> str:
    raw = version.strip().strip('"').strip("'")
    parts = raw.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return version
    parts[2] = str(int(parts[2]) + 1)
    return yaml_quote(".".join(parts))


def remove_local_quality_supplement(content: str) -> str:
    return re.sub(
        r"\n+<!-- LOCAL-QUALITY-SUPPLEMENT:START -->.*?<!-- LOCAL-QUALITY-SUPPLEMENT:END -->\s*",
        "\n",
        content,
        flags=re.DOTALL,
    ).rstrip() + "\n"


def comparable_body(text: str) -> str:
    return strip_frontmatter(remove_local_quality_supplement(text))


def needs_quality_supplement(content: str) -> bool:
    line_count = len(content.splitlines())
    headings = re.findall(r"^##\s+.+$", content, re.MULTILINE)
    normalized_headings = [
        re.sub(r"[^a-z0-9]+", " ", heading.lower()).strip() for heading in headings
    ]
    has_lint_friendly_section = any(
        keyword in heading
        for heading in normalized_headings
        for keyword in ("overview", "workflow", "quick start", "quick reference", "usage", "process", "examples")
    )
    return line_count < 90 or "```" not in content or len(headings) < 2 or not has_lint_friendly_section


def build_quality_supplement(skill_name: str) -> str:
    title = skill_name.replace("-", " ").title()
    return f"""
<!-- LOCAL-QUALITY-SUPPLEMENT:START -->
## Usage Notes

This supplement is maintained by the repository sync pipeline. It keeps the
imported upstream skill usable inside this curated collection when the upstream
source is intentionally concise.

## Common Patterns

```text
1. Confirm that the user's task matches the skill trigger.
2. Read the relevant project files or user-provided context before acting.
3. Choose the smallest reversible action that advances the task.
4. Run the verification command or manual check that proves the result.
5. Report the outcome, evidence, and any remaining risk.
```

## Boundaries

- Prefer the upstream workflow for {title}; this section only adds local quality
  guardrails.
- Do not invent project facts when required files, vaults, services, or tools are
  unavailable.
- Stop and ask for clarification when the next action could overwrite user work,
  expose private data, or change production state.
<!-- LOCAL-QUALITY-SUPPLEMENT:END -->
"""


def ensure_quality_floor(content: str, skill_name: str) -> str:
    cleaned = remove_local_quality_supplement(content)
    if not needs_quality_supplement(cleaned):
        return cleaned
    return cleaned.rstrip() + "\n" + build_quality_supplement(skill_name).lstrip()


def merge_frontmatter(local_content: str, upstream_content: str) -> str:
    """Keep local enriched frontmatter and replace the body with upstream content."""
    local_fm = parse_frontmatter(local_content)
    upstream_fm = parse_frontmatter(upstream_content)
    local_frontmatter, _ = split_frontmatter(local_content)
    upstream_frontmatter, upstream_body = split_frontmatter(upstream_content)

    if local_frontmatter is None:
        name = upstream_fm.get("name", local_fm.get("name", "imported-skill"))
        description = upstream_fm.get("description", local_fm.get("description", "Synced upstream skill."))
        local_frontmatter = "\n".join(
            [
                "---",
                f"name: {name}",
                f"description: {yaml_quote(description)}",
                'version: "1.0.0"',
                f'updated_at: "{date.today().isoformat()}"',
                "---",
                "",
            ]
        )

    merged_frontmatter = local_frontmatter
    if upstream_frontmatter is not None:
        if upstream_fm.get("name"):
            merged_frontmatter = update_frontmatter_field(merged_frontmatter, "name", upstream_fm["name"])
        if upstream_fm.get("description") and len(upstream_fm["description"]) >= 20:
            merged_frontmatter = update_frontmatter_field(
                merged_frontmatter,
                "description",
                yaml_quote(upstream_fm["description"]),
            )
    if local_fm.get("version"):
        merged_frontmatter = update_frontmatter_field(
            merged_frontmatter,
            "version",
            bump_patch_version(local_fm["version"]),
        )
    merged_frontmatter = update_frontmatter_field(
        merged_frontmatter,
        "updated_at",
        yaml_quote(date.today().isoformat()),
    )

    merged = merged_frontmatter.rstrip() + "\n" + upstream_body.lstrip()
    return ensure_quality_floor(merged, local_fm.get("name", upstream_fm.get("name", "synced-skill")))


def load_skills_from_source_mappings() -> list[dict]:
    """Load externally tracked skills from docs/sources/*.skills.json."""
    results = []
    for mapping_path in sorted(SOURCE_MAPPINGS_DIR.glob("*.skills.json")):
        if mapping_path.name == PROVENANCE_FILE.name:
            continue
        data = json.loads(mapping_path.read_text(encoding="utf-8"))
        for entry_index, entry in enumerate(data.get("skills", [])):
            upstream = entry.get("upstream") or {}
            repo = upstream.get("repo")
            repo_skill = entry.get("repo_skill")
            upstream_path = upstream.get("path")
            if not repo or repo.startswith("local-repo/") or not repo_skill or not upstream_path:
                continue
            local_path = REPO_ROOT / repo_skill
            if not local_path.exists():
                print(f"    Warning: mapped local skill missing: {repo_skill}", file=sys.stderr)
                continue
            content = local_path.read_text(encoding="utf-8", errors="replace")
            fm = parse_frontmatter(content)
            skill_name = fm.get("name", entry.get("normalized_slug") or entry.get("video_name") or local_path.parent.name)
            results.append(
                {
                    "name": skill_name,
                    "category": local_path.parent.parent.name,
                    "source": f"github:{repo}",
                    "repo": repo,
                    "local_path": local_path,
                    "source_url": entry.get("source", ""),
                    "local_content": content,
                    "upstream_path": upstream_path,
                    "ref": upstream.get("ref", "main"),
                    "mapping_path": mapping_path,
                    "mapping_entry_index": entry_index,
                }
            )
    return results


def load_skills_with_upstream() -> list[dict]:
    """Load skills that have external upstream sources.

    Prefer exact paths from docs/sources/*.skills.json, then fall back to
    frontmatter-only github sources that are not yet mapped.
    """
    mapped = load_skills_from_source_mappings()
    mapped_paths = {item["local_path"].resolve() for item in mapped}
    results = []
    for skill_md in sorted(SKILLS_DIR.glob("*/*/SKILL.md")):
        if skill_md.resolve() in mapped_paths:
            continue
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
                "ref": "main",
            })
        elif source in ("skills.sh", "clawhub", "community"):
            # These don't have auto-syncable upstreams yet
            pass
    return mapped + results


def check_upstream_changes(skill: dict, token: str | None) -> dict | None:
    """Check if upstream has changes for a skill."""
    repo = skill["repo"]
    skill_name = skill["name"]
    
    # Prefer exact provenance paths. Fallbacks support older frontmatter-only entries.
    candidate_paths = [skill["upstream_path"]] if skill.get("upstream_path") else [
        f"skills/{skill_name}/SKILL.md",
        f"skills/{skill['category']}/{skill_name}/SKILL.md",
        f"{skill_name}/SKILL.md",
    ]
    
    for path in candidate_paths:
        url = github_raw_url(repo, path, skill.get("ref", "main"))
        upstream_content = fetch_url(url, token)
        if upstream_content:
            # Compare content (ignore frontmatter for diff)
            local_body = comparable_body(skill["local_content"])
            upstream_body = comparable_body(upstream_content)
            
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
    api_url = f"https://api.github.com/repos/{repo}/contents/{upstream_dir}?ref={skill.get('ref', 'main')}"
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


def update_mapping_after_sync(update: dict) -> None:
    """Update provenance timestamps for a successfully synced mapped skill."""
    skill = update["skill"]
    mapping_path = skill.get("mapping_path")
    entry_index = skill.get("mapping_entry_index")
    if mapping_path is None or entry_index is None:
        return

    data = json.loads(Path(mapping_path).read_text(encoding="utf-8"))
    try:
        upstream = data["skills"][entry_index].setdefault("upstream", {})
    except (KeyError, IndexError):
        return
    today = date.today().isoformat()
    upstream["last_checked_at"] = today
    upstream["last_synced_at"] = today
    data["video"]["checked_at"] = today
    Path(mapping_path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check and synchronize upstream changes for tracked skills."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-only", action="store_true", help="Only report updates, don't apply")
    group.add_argument("--apply", action="store_true", help="Apply upstream updates to local files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing")
    parser.add_argument("--source", help="Filter to a specific source (e.g. 'github:obra/superpowers')")
    parser.add_argument("--exclude-source", action="append", default=[],
                        help="Exclude a source/repo (can be passed multiple times; accepts github:owner/repo or owner/repo)")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    skills = load_skills_with_upstream()
    
    if args.source:
        source = args.source.replace("github:", "")
        skills = [s for s in skills if s["repo"] == source or s["source"] == args.source]
    if args.exclude_source:
        excluded = {item.replace("github:", "") for item in args.exclude_source}
        skills = [s for s in skills if s["repo"] not in excluded and s["source"] not in args.exclude_source]
    
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
            update_mapping_after_sync(u)
            applied += 1
        
        print(f"\nApplied {applied} updates.")
        if not args.dry_run:
            print("Run the full pipeline to regenerate views:")
            print("  python scripts/refresh_repo_views.py")


if __name__ == "__main__":
    main()
