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
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

REPO_ROOT = Path(__file__).resolve().parents[1]

WATCHED_REPOS = [
    "alirezarezvani/claude-skills",
    "obra/superpowers",
    "anthropics/prompt-eng",
    "ComposioHQ/awesome-claude-skills",
]

SEARCH_QUERIES = [
    "SKILL.md agent skill in:path language:Markdown stars:>10",
    "claude code skill SKILL.md stars:>5",
]

SEARCH_KEYWORDS = [
    "kubernetes",
    "docker",
    "terraform",
    "aws",
    "react",
    "nextjs",
    "python",
    "rust",
    "typescript",
    "testing",
    "security",
    "devops",
    "database",
    "api",
    "performance",
    "debugging",
    "automation",
    "documentation",
    "code review",
    "refactoring",
    "supabase",
    "tailwind",
    "graphql",
    "web scraping",
    "data analysis",
]

SOURCE_GITHUB = "github"
SOURCE_SKILLS_SH = "skills_sh"
SOURCE_CLAWHUB = "clawhub"
SOURCE_HEALTH_LOCK = Lock()


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_day() -> str:
    return utc_now().strftime("%Y-%m-%d")


def utc_timestamp() -> str:
    return utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def get_local_skill_names(skills_dir: Path) -> set[str]:
    names = set()
    if not skills_dir.exists():
        return names
    for skill_md in skills_dir.glob("*/*/SKILL.md"):
        names.add(skill_md.parent.name)
    return names


def new_source_health() -> dict[str, dict]:
    return {
        SOURCE_GITHUB: {"status": "unknown", "queries": 0, "results": 0, "errors": []},
        SOURCE_SKILLS_SH: {"status": "unknown", "queries": 0, "results": 0, "errors": []},
        SOURCE_CLAWHUB: {"status": "unknown", "queries": 0, "results": 0, "errors": []},
    }


def classify_fetch_error(status_code: int | None, message: str) -> dict[str, str | int | None]:
    lowered = message.lower()
    if status_code == 401:
        kind = "unauthorized"
    elif status_code == 403 and "rate limit" in lowered:
        kind = "rate_limited"
    elif status_code == 403:
        kind = "forbidden"
    elif status_code == 404:
        kind = "not_found"
    elif status_code == 429:
        kind = "rate_limited"
    elif status_code is None:
        kind = "network_error"
    elif 500 <= status_code <= 599:
        kind = "upstream_error"
    else:
        kind = "request_failed"
    return {"kind": kind, "status_code": status_code, "message": message}


def record_query(source_health: dict[str, dict], source_key: str) -> None:
    with SOURCE_HEALTH_LOCK:
        source_health[source_key]["queries"] += 1


def record_results(source_health: dict[str, dict], source_key: str, count: int) -> None:
    with SOURCE_HEALTH_LOCK:
        source_health[source_key]["results"] += count


def record_error(
    source_health: dict[str, dict],
    source_key: str,
    *,
    status_code: int | None,
    message: str,
) -> None:
    with SOURCE_HEALTH_LOCK:
        source_health[source_key]["errors"].append(classify_fetch_error(status_code, message))


def finalize_source_health(source_health: dict[str, dict]) -> dict[str, dict]:
    finalized: dict[str, dict] = {}
    for source_key, raw in source_health.items():
        entry = {
            "queries": raw["queries"],
            "results": raw["results"],
            "errors": raw["errors"],
            "status": "unknown",
        }
        if raw["queries"] == 0:
            entry["status"] = "unknown"
        elif not raw["errors"]:
            entry["status"] = "healthy"
        elif raw["results"] > 0:
            entry["status"] = "degraded"
        else:
            entry["status"] = "unavailable"
        finalized[source_key] = entry
    return finalized


def flatten_errors(source_health: dict[str, dict]) -> list[dict]:
    errors = []
    for source_key, entry in source_health.items():
        for item in entry.get("errors", []):
            error = dict(item)
            error["source"] = source_key
            errors.append(error)
    return errors


def fetch_url(
    url: str,
    *,
    source_key: str,
    source_health: dict[str, dict],
    headers: dict | None = None,
) -> str | None:
    request_headers = {"User-Agent": "skills-discovery-bot"}
    if headers:
        request_headers.update(headers)

    record_query(source_health, source_key)
    req = urllib.request.Request(url, headers=request_headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        record_error(source_health, source_key, status_code=exc.code, message=str(exc))
        print(f"  Warning: Request failed for {url}: {exc}", file=sys.stderr)
        return None
    except urllib.error.URLError as exc:
        record_error(source_health, source_key, status_code=None, message=str(exc))
        print(f"  Warning: Request failed for {url}: {exc}", file=sys.stderr)
        return None
    except Exception as exc:  # pragma: no cover - defensive
        record_error(source_health, source_key, status_code=None, message=str(exc))
        print(f"  Warning: Request failed for {url}: {exc}", file=sys.stderr)
        return None


def github_api_get(url: str, token: str | None, source_health: dict[str, dict]) -> dict | list | None:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "skills-discovery-bot",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    content = fetch_url(url, source_key=SOURCE_GITHUB, source_health=source_health, headers=headers)
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        record_error(source_health, SOURCE_GITHUB, status_code=None, message=f"json_decode_error: {exc}")
        return None


def make_discovery(
    *,
    name: str,
    source: str,
    url: str,
    repo_stars: int,
    description: str,
) -> dict:
    return {
        "name": name,
        "source": source,
        "url": url,
        "repo_stars": repo_stars,
        "description": description,
        "discovered_at": utc_day(),
    }


def discover_from_watched_repos(token: str | None, source_health: dict[str, dict]) -> list[dict]:
    discoveries = []
    for repo in WATCHED_REPOS:
        print(f"  Checking watched repo: {repo}")
        info = github_api_get(f"https://api.github.com/repos/{repo}", token, source_health)
        if not isinstance(info, dict):
            continue

        search_url = f"https://api.github.com/search/code?q=filename:SKILL.md+repo:{repo}"
        results = github_api_get(search_url, token, source_health)
        if not isinstance(results, dict):
            continue

        items = results.get("items", [])
        record_results(source_health, SOURCE_GITHUB, len(items))
        for item in items:
            path = item.get("path", "")
            parts = Path(path).parts
            if len(parts) >= 2 and parts[-1] == "SKILL.md":
                discoveries.append(
                    make_discovery(
                        name=parts[-2],
                        source=f"GitHub ({repo})",
                        url=f"https://github.com/{repo}/blob/main/{path}",
                        repo_stars=info.get("stargazers_count", 0),
                        description=info.get("description", ""),
                    )
                )
    return discoveries


def discover_from_github_search(token: str | None, source_health: dict[str, dict]) -> list[dict]:
    discoveries = []
    seen_repos = set()

    for query in SEARCH_QUERIES:
        print(f"  GitHub searching: {query}")
        encoded_q = urllib.parse.quote(query)
        url = f"https://api.github.com/search/repositories?q={encoded_q}&sort=stars&per_page=20"
        results = github_api_get(url, token, source_health)
        if not isinstance(results, dict):
            continue

        items = results.get("items", [])
        record_results(source_health, SOURCE_GITHUB, len(items))
        for repo in items:
            full_name = repo["full_name"]
            if full_name in seen_repos or full_name in WATCHED_REPOS:
                continue
            seen_repos.add(full_name)
            discoveries.append(
                make_discovery(
                    name=f"[repo] {full_name}",
                    source="GitHub Search",
                    url=repo.get("html_url", ""),
                    repo_stars=repo.get("stargazers_count", 0),
                    description=repo.get("description", ""),
                )
            )
    return discoveries


def discover_from_skills_sh(keywords: list[str], source_health: dict[str, dict]) -> list[dict]:
    discoveries = []
    seen_ids = set()

    for kw in keywords:
        print(f"  skills.sh searching: {kw}")
        api_url = f"https://skills.sh/api/search?q={urllib.parse.quote(kw)}"
        content = fetch_url(api_url, source_key=SOURCE_SKILLS_SH, source_health=source_health)
        if content:
            try:
                data = json.loads(content)
                items = data.get("skills", [])
                record_results(source_health, SOURCE_SKILLS_SH, len(items))
                for item in items:
                    skill_id = item.get("id")
                    if skill_id and skill_id not in seen_ids:
                        seen_ids.add(skill_id)
                        discoveries.append(
                            make_discovery(
                                name=item.get("name", ""),
                                source=f"skills.sh ({item.get('source', '')})",
                                url=f"https://skills.sh/{item.get('id', '')}",
                                repo_stars=item.get("installs", 0),
                                description=f"Installs: {item.get('installs', 0)}",
                            )
                        )
                continue
            except json.JSONDecodeError as exc:
                record_error(
                    source_health,
                    SOURCE_SKILLS_SH,
                    status_code=None,
                    message=f"json_decode_error: {exc}",
                )

        page_url = f"https://skills.sh/s/{urllib.parse.quote(kw)}"
        html = fetch_url(page_url, source_key=SOURCE_SKILLS_SH, source_health=source_health)
        if not html:
            continue

        matches = re.finditer(
            r'href="/([^"]+/[^"]+/[^"]+)"[^>]*>.*?<strong>(.*?)</strong>.*?(\d+\.?\d*[Kk]?)',
            html,
            re.DOTALL,
        )
        count = 0
        for match in matches:
            skill_id = match.group(1)
            if skill_id in seen_ids:
                continue
            seen_ids.add(skill_id)
            installs_str = match.group(3).lower()
            installs = 0
            if "k" in installs_str:
                try:
                    installs = int(float(installs_str.replace("k", "")) * 1000)
                except ValueError:
                    installs = 0
            else:
                try:
                    installs = int(installs_str)
                except ValueError:
                    installs = 0
            discoveries.append(
                make_discovery(
                    name=match.group(2).strip(),
                    source="skills.sh (scraped)",
                    url=f"https://skills.sh/{skill_id}",
                    repo_stars=installs,
                    description=f"Installs: {match.group(3)}",
                )
            )
            count += 1
        record_results(source_health, SOURCE_SKILLS_SH, count)

    return discoveries


def discover_from_clawhub(keywords: list[str], source_health: dict[str, dict]) -> list[dict]:
    discoveries = []
    seen_slugs = set()

    for kw in keywords:
        print(f"  ClawHub searching: {kw}")
        api_url = f"https://clawhub.com/api/search?q={urllib.parse.quote(kw)}"
        content = fetch_url(api_url, source_key=SOURCE_CLAWHUB, source_health=source_health)
        if content:
            try:
                data = json.loads(content)
                results = data if isinstance(data, list) else data.get("results", [])
                record_results(source_health, SOURCE_CLAWHUB, len(results))
                for item in results:
                    slug = item.get("slug")
                    if slug and slug not in seen_slugs:
                        seen_slugs.add(slug)
                        discoveries.append(
                            make_discovery(
                                name=item.get("displayName", slug),
                                source="ClawHub",
                                url=f"https://clawhub.com/s/{slug}",
                                repo_stars=int(item.get("score", 0) * 10),
                                description=item.get("summary", ""),
                            )
                        )
                continue
            except (json.JSONDecodeError, TypeError) as exc:
                record_error(source_health, SOURCE_CLAWHUB, status_code=None, message=f"json_decode_error: {exc}")

        page_url = f"https://clawhub.com/search?q={urllib.parse.quote(kw)}"
        html = fetch_url(page_url, source_key=SOURCE_CLAWHUB, source_health=source_health)
        if not html:
            continue

        count = 0
        matches = re.finditer(r'href="/s/([^"]+)"[^>]*>.*?<h[^>]*>(.*?)</h', html, re.DOTALL)
        for match in matches:
            slug = match.group(1)
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            discoveries.append(
                make_discovery(
                    name=match.group(2).strip(),
                    source="ClawHub (scraped)",
                    url=f"https://clawhub.com/s/{slug}",
                    repo_stars=0,
                    description="",
                )
            )
            count += 1
        record_results(source_health, SOURCE_CLAWHUB, count)

    return discoveries


def dedupe_discoveries(all_discoveries: list[dict], local_names: set[str]) -> list[dict]:
    seen_names = set()
    unique_discoveries = []
    for item in all_discoveries:
        name = item["name"]
        if name in local_names or name in seen_names:
            continue
        seen_names.add(name)
        unique_discoveries.append(item)
    unique_discoveries.sort(key=lambda entry: entry.get("repo_stars", 0), reverse=True)
    return unique_discoveries


def build_discovery_report(
    *,
    local_skill_count: int,
    all_discoveries: list[dict],
    unique_discoveries: list[dict],
    source_health: dict[str, dict],
) -> dict:
    finalized_health = finalize_source_health(source_health)
    return {
        "generated_at": utc_timestamp(),
        "local_skill_count": local_skill_count,
        "total_discovered": len(all_discoveries),
        "unique_discovered": len(unique_discoveries),
        "discoveries": unique_discoveries,
        "source_health": finalized_health,
        "errors": flatten_errors(finalized_health),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover new agent skills from external sources.")
    parser.add_argument("--output", default="docs/sources/reports/discovery.json")
    parser.add_argument("--skills-dir", default="skills")
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
        keywords = [item.strip() for item in args.keywords.split(",") if item.strip()]

    source_health = new_source_health()
    all_discoveries: list[dict] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        print("\n--- Checking watched repositories ---")
        watched_future = executor.submit(discover_from_watched_repos, token, source_health)

        print("\n--- Searching GitHub ---")
        github_future = executor.submit(discover_from_github_search, token, source_health)

        print("\n--- Searching skills.sh ---")
        skills_future = executor.submit(discover_from_skills_sh, keywords, source_health)

        print("\n--- Searching ClawHub ---")
        clawhub_future = executor.submit(discover_from_clawhub, keywords, source_health)

        all_discoveries.extend(watched_future.result())
        all_discoveries.extend(github_future.result())
        all_discoveries.extend(skills_future.result())
        all_discoveries.extend(clawhub_future.result())

    unique_discoveries = dedupe_discoveries(all_discoveries, local_names)
    report = build_discovery_report(
        local_skill_count=len(local_names),
        all_discoveries=all_discoveries,
        unique_discoveries=unique_discoveries,
        source_health=source_health,
    )

    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote discovery report: {output_path}")
    print(f"Total discovered: {len(all_discoveries)}, Unique/New: {len(unique_discoveries)}")

    if args.recommend:
        print("\n### Recommended New Skills (Top 20)")
        print("| Skill | Source | Stars/Installs | Description |")
        print("| :--- | :--- | :--- | :--- |")
        for item in unique_discoveries[:20]:
            name = item["name"]
            url = item["url"]
            source = item["source"]
            stars = item["repo_stars"]
            desc = item["description"].replace("\n", " ")[:100]
            if len(item["description"]) > 100:
                desc += "..."
            print(f"| [{name}]({url}) | {source} | {stars} | {desc} |")


if __name__ == "__main__":
    main()
