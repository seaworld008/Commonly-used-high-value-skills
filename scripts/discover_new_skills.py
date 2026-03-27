#!/usr/bin/env python3
"""Discover new agent skills from external sources.

Scans GitHub, skills.sh, and ClawHub for popular agent skills,
compares against locally indexed skills, and reports new discoveries.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

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

# Standard search keywords for skills.sh and ClawHub
SEARCH_KEYWORDS = [
    "kubernetes", "docker", "terraform", "aws", "react", "nextjs",
    "python", "rust", "typescript", "testing", "security", "devops",
    "database", "api", "performance", "debugging", "automation",
    "documentation", "code review", "refactoring", "supabase",
    "tailwind", "graphql", "web scraping", "data analysis",
]


def get_local_skill_names(skills_dir: Path) -> set[str]:
    """Return set of locally indexed skill directory names."""
    names = set()
    if not skills_dir.exists():
        return names
    for skill_md in skills_dir.glob("*/*/SKILL.md"):
        names.add(skill_md.parent.name)
    return names


def fetch_url(url: str, headers: dict | None = None) -> str | None:
    """Fetch URL content with standard error handling."""
    if headers is None:
        headers = {"User-Agent": "skills-discovery-bot"}
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"  Warning: Request failed for {url}: {e}", file=sys.stderr)
        return None


def github_api_get(url: str, token: str | None = None) -> dict | list | None:
    """Make a GET request to GitHub API."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "skills-discovery-bot",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    
    content = fetch_url(url, headers)
    if content:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None
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
                    "source": f"GitHub ({repo})",
                    "url": f"https://github.com/{repo}/blob/main/{path}",
                    "repo_stars": info.get("stargazers_count", 0),
                    "description": info.get("description", ""),
                    "discovered_at": datetime.utcnow().strftime("%Y-%m-%d"),
                })
    return discoveries


def discover_from_github_search(token: str | None) -> list[dict]:
    """Search GitHub for repositories with SKILL.md files."""
    discoveries = []
    seen_repos = set()
    
    for query in SEARCH_QUERIES:
        print(f"  GitHub Searching: {query}")
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
                "source": "GitHub Search",
                "url": repo.get("html_url", ""),
                "repo_stars": repo.get("stargazers_count", 0),
                "description": repo.get("description", ""),
                "discovered_at": datetime.utcnow().strftime("%Y-%m-%d"),
            })
    return discoveries


def discover_from_skills_sh(keywords: list[str]) -> list[dict]:
    """Search skills.sh for skills."""
    discoveries = []
    seen_ids = set()
    
    for kw in keywords:
        print(f"  skills.sh searching: {kw}")
        # Try API
        api_url = f"https://skills.sh/api/search?q={urllib.parse.quote(kw)}"
        content = fetch_url(api_url)
        if content:
            try:
                data = json.loads(content)
                for item in data.get("skills", []):
                    skill_id = item.get("id")
                    if skill_id and skill_id not in seen_ids:
                        seen_ids.add(skill_id)
                        discoveries.append({
                            "name": item.get("name", ""),
                            "source": f"skills.sh ({item.get('source', '')})",
                            "url": f"https://skills.sh/{item.get('id', '')}",
                            "repo_stars": item.get("installs", 0),  # Use installs as stars equivalent
                            "description": f"Installs: {item.get('installs', 0)}",
                            "discovered_at": datetime.utcnow().strftime("%Y-%m-%d"),
                        })
                continue
            except json.JSONDecodeError:
                pass
        
        # Fallback to scraping
        page_url = f"https://skills.sh/s/{urllib.parse.quote(kw)}"
        html = fetch_url(page_url)
        if html:
            # Simple regex to extract skill links and names from HTML
            # Look for <a> tags with skill paths or specific patterns
            # Pattern based on web_fetch: [**name** \n\n source \n\n installs](url)
            # In HTML it might look like <a href="/source/skill">...<strong>name</strong>...
            matches = re.finditer(r'href="/([^"]+/[^"]+/[^"]+)"[^>]*>.*?<strong>(.*?)</strong>.*?(\d+\.?\d*[Kk]?)', html, re.DOTALL)
            for m in matches:
                skill_id = m.group(1)
                if skill_id not in seen_ids:
                    seen_ids.add(skill_id)
                    installs_str = m.group(3).lower()
                    installs = 0
                    if 'k' in installs_str:
                        try:
                            installs = int(float(installs_str.replace('k', '')) * 1000)
                        except ValueError: pass
                    else:
                        try: installs = int(installs_str)
                        except ValueError: pass
                    
                    discoveries.append({
                        "name": m.group(2).strip(),
                        "source": "skills.sh (scraped)",
                        "url": f"https://skills.sh/{skill_id}",
                        "repo_stars": installs,
                        "description": f"Installs: {m.group(3)}",
                        "discovered_at": datetime.utcnow().strftime("%Y-%m-%d"),
                    })
    
    if not discoveries:
        print("  Warning: skills.sh discovery yielded no results (or failed).", file=sys.stderr)
    return discoveries


def discover_from_clawhub(keywords: list[str]) -> list[dict]:
    """Search ClawHub for skills."""
    discoveries = []
    seen_slugs = set()
    
    for kw in keywords:
        print(f"  ClawHub searching: {kw}")
        # Try API
        api_url = f"https://clawhub.com/api/search?q={urllib.parse.quote(kw)}"
        content = fetch_url(api_url)
        if content:
            try:
                data = json.loads(content)
                # Results can be a list or a dict with "results"
                results = data if isinstance(data, list) else data.get("results", [])
                for item in results:
                    slug = item.get("slug")
                    if slug and slug not in seen_slugs:
                        seen_slugs.add(slug)
                        discoveries.append({
                            "name": item.get("displayName", slug),
                            "source": "ClawHub",
                            "url": f"https://clawhub.com/s/{slug}",
                            "repo_stars": int(item.get("score", 0) * 10), # Pseudo-score
                            "description": item.get("summary", ""),
                            "discovered_at": datetime.utcnow().strftime("%Y-%m-%d"),
                        })
                continue
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Fallback to scraping
        page_url = f"https://clawhub.com/search?q={urllib.parse.quote(kw)}"
        html = fetch_url(page_url)
        if html:
            # ClawHub is often client-side rendered, but let's try to catch any baked-in data
            # Or look for patterns in the HTML
            matches = re.finditer(r'href="/s/([^"]+)"[^>]*>.*?<h[^>]*>(.*?)</h', html, re.DOTALL)
            for m in matches:
                slug = m.group(1)
                if slug not in seen_slugs:
                    seen_slugs.add(slug)
                    discoveries.append({
                        "name": m.group(2).strip(),
                        "source": "ClawHub (scraped)",
                        "url": f"https://clawhub.com/s/{slug}",
                        "repo_stars": 0,
                        "description": "",
                        "discovered_at": datetime.utcnow().strftime("%Y-%m-%d"),
                    })
    
    if not discoveries:
        print("  Warning: ClawHub discovery yielded no results (or failed).", file=sys.stderr)
    return discoveries


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover new agent skills from external sources.")
    parser.add_argument("--output", default="docs/sources/reports/discovery.json",
                        help="Output JSON file path (default: docs/sources/reports/discovery.json)")
    parser.add_argument("--skills-dir", default="skills",
                        help="Local skills directory (default: skills)")
    parser.add_argument("--keywords", help="Comma-separated list of custom keywords to search")
    parser.add_argument("--recommend", action="store_true", help="Output a recommendation Markdown table")
    args = parser.parse_args()
    
    skills_dir = REPO_ROOT / args.skills_dir
    output_path = REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    token = os.environ.get("GITHUB_TOKEN")
    local_names = get_local_skill_names(skills_dir)
    print(f"Local skills indexed: {len(local_names)}")
    
    keywords = SEARCH_KEYWORDS
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",")]
    
    # Discovery functions
    all_discoveries = []
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        print("\n--- Checking watched repositories ---")
        f_watched = executor.submit(discover_from_watched_repos, token)
        
        print("\n--- Searching GitHub ---")
        f_github = executor.submit(discover_from_github_search, token)
        
        print("\n--- Searching skills.sh ---")
        f_skills_sh = executor.submit(discover_from_skills_sh, keywords)
        
        print("\n--- Searching ClawHub ---")
        f_clawhub = executor.submit(discover_from_clawhub, keywords)
        
        all_discoveries.extend(f_watched.result())
        all_discoveries.extend(f_github.result())
        all_discoveries.extend(f_skills_sh.result())
        all_discoveries.extend(f_clawhub.result())
    
    # Filter out duplicates and already indexed skills
    seen_names = set()
    unique_discoveries = []
    for d in all_discoveries:
        # Check if already indexed
        if d["name"] in local_names:
            continue
        # Deduplicate within discovery session
        if d["name"] in seen_names:
            continue
        seen_names.add(d["name"])
        unique_discoveries.append(d)
    
    # Sort by "stars" (installs or repo stars)
    unique_discoveries.sort(key=lambda x: x.get("repo_stars", 0), reverse=True)
    
    report = {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "local_skill_count": len(local_names),
        "total_discovered": len(all_discoveries),
        "unique_discovered": len(unique_discoveries),
        "discoveries": unique_discoveries,
    }
    
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote discovery report: {output_path}")
    print(f"Total discovered: {len(all_discoveries)}, Unique/New: {len(unique_discoveries)}")
    
    if args.recommend:
        print("\n### Recommended New Skills (Top 20)")
        print("| Skill | Source | Stars/Installs | Description |")
        print("| :--- | :--- | :--- | :--- |")
        for d in unique_discoveries[:20]:
            name = d["name"]
            url = d["url"]
            source = d["source"]
            stars = d["repo_stars"]
            desc = d["description"].replace("\n", " ")[:100]
            if len(d["description"]) > 100: desc += "..."
            print(f"| [{name}]({url}) | {source} | {stars} | {desc} |")


if __name__ == "__main__":
    main()
