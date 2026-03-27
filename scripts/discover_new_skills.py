#!/usr/bin/env python3
"""Discover new agent skills from external sources.

Scans GitHub for popular repositories containing SKILL.md files,
compares against locally indexed skills, and reports new discoveries.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Well-known skill repositories to monitor
WATCHED_REPOS = [
    "alirezarezvani/claude-skills",
    "obra/superpowers",
    "anthropics/prompt-eng",
    "ComposioHQ/awesome-claude-skills",
]

# GitHub search queries for discovering new skill repos
SEARCH_QUERIES = [
    "SKILL.md agent skill in:path language:Markdown stars:>10",
    "claude code skill SKILL.md stars:>5",
]


def get_local_skill_names(skills_dir: Path) -> set[str]:
    """Return set of locally indexed skill directory names."""
    names = set()
    for skill_md in skills_dir.glob("*/*/SKILL.md"):
        names.add(skill_md.parent.name)
    return names


def github_api_get(url: str, token: str | None = None) -> dict | list | None:
    """Make a GET request to GitHub API."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "skills-discovery-bot",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"  Warning: API request failed for {url}: {e}", file=sys.stderr)
        return None


def discover_from_watched_repos(token: str | None) -> list[dict]:
    """Check watched repositories for SKILL.md files."""
    discoveries = []
    for repo in WATCHED_REPOS:
        print(f"  Checking watched repo: {repo}")
        # Get repo info
        info = github_api_get(f"https://api.github.com/repos/{repo}", token)
        if not info:
            continue
        
        # Search for SKILL.md files in the repo
        search_url = f"https://api.github.com/search/code?q=filename:SKILL.md+repo:{repo}"
        results = github_api_get(search_url, token)
        if not results or "items" not in results:
            continue
        
        for item in results.get("items", []):
            path = item.get("path", "")
            # Extract skill name from path like "skills/category/skill-name/SKILL.md"
            parts = Path(path).parts
            if len(parts) >= 2 and parts[-1] == "SKILL.md":
                skill_name = parts[-2]
                discoveries.append({
                    "name": skill_name,
                    "source_repo": repo,
                    "source_path": path,
                    "repo_stars": info.get("stargazers_count", 0),
                    "repo_description": info.get("description", ""),
                    "discovered_at": datetime.utcnow().strftime("%Y-%m-%d"),
                })
    return discoveries


def discover_from_search(token: str | None) -> list[dict]:
    """Search GitHub for repositories with SKILL.md files."""
    discoveries = []
    seen_repos = set()
    
    for query in SEARCH_QUERIES:
        print(f"  Searching: {query}")
        encoded_q = urllib.parse.quote(query)
        url = f"https://api.github.com/search/repositories?q={encoded_q}&sort=stars&per_page=20"
        results = github_api_get(url, token)
        if not results or "items" not in results:
            continue
        
        for repo in results.get("items", []):
            full_name = repo["full_name"]
            if full_name in seen_repos or full_name in WATCHED_REPOS:
                continue
            seen_repos.add(full_name)
            
            discoveries.append({
                "name": f"[repo] {full_name}",
                "source_repo": full_name,
                "source_path": "",
                "repo_stars": repo.get("stargazers_count", 0),
                "repo_description": repo.get("description", ""),
                "discovered_at": datetime.utcnow().strftime("%Y-%m-%d"),
            })
    return discoveries


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover new agent skills from external sources.")
    parser.add_argument("--output", default="docs/sources/reports/discovery.json",
                        help="Output JSON file path (default: docs/sources/reports/discovery.json)")
    parser.add_argument("--skills-dir", default="skills",
                        help="Local skills directory (default: skills)")
    args = parser.parse_args()
    
    skills_dir = REPO_ROOT / args.skills_dir
    output_path = REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    token = os.environ.get("GITHUB_TOKEN")
    local_names = get_local_skill_names(skills_dir)
    print(f"Local skills indexed: {len(local_names)}")
    
    # Discover from all sources
    print("\n--- Checking watched repositories ---")
    watched = discover_from_watched_repos(token)
    print(f"  Found {len(watched)} skills in watched repos")
    
    print("\n--- Searching GitHub ---")
    searched = discover_from_search(token)
    print(f"  Found {len(searched)} candidate repos")
    
    all_discoveries = watched + searched
    
    # Filter out already indexed skills
    new_discoveries = [d for d in all_discoveries if d["name"] not in local_names]
    
    report = {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "local_skill_count": len(local_names),
        "total_discovered": len(all_discoveries),
        "new_discoveries": len(new_discoveries),
        "discoveries": sorted(new_discoveries, key=lambda x: x.get("repo_stars", 0), reverse=True),
    }
    
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote discovery report: {output_path}")
    print(f"Total discovered: {len(all_discoveries)}, New: {len(new_discoveries)}")


if __name__ == "__main__":
    import urllib.parse
    main()
