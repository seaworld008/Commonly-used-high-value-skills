#!/usr/bin/env python3
"""Unified orchestration for syncing, discovering, scoring, and curating skills."""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PR_BODY = "docs/sources/reports/curation-pr.md"
DEFAULT_POLICY_PATH = "docs/sources/curation-policy.json"
DEFAULT_LICENSE_REWRITE_LOG = "docs/sources/reports/license-rewrite-log.json"
DEFAULT_UNLICENSED_REWRITE_MIN_SCORE = 55
DEFAULT_UNLICENSED_REWRITE_MIN_LINES = 80

TRUSTED_SOURCE_SCORES = {
    "vercel-labs/agent-skills": 28,
    "supabase/agent-skills": 26,
    "obra/superpowers": 24,
    "alirezarezvani/claude-skills": 22,
    "google-labs-code/stitch-skills": 18,
    "ComposioHQ/awesome-claude-skills": 14,
}

PERMISSIVE_LICENSES = {
    "MIT", "Apache-2.0", "Apache 2.0", "BSD-2-Clause", "BSD-3-Clause",
    "ISC", "CC-BY-4.0", "CC0-1.0", "Unlicense", "0BSD", "MPL-2.0",
}
GITHUB_LICENSE_KEYS = {
    "mit": "MIT",
    "apache-2.0": "Apache-2.0",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "isc": "ISC",
    "cc-by-4.0": "CC-BY-4.0",
    "cc0-1.0": "CC0-1.0",
    "unlicense": "Unlicense",
    "0bsd": "0BSD",
    "mpl-2.0": "MPL-2.0",
}

CATEGORY_KEYWORDS = {
    "developer-engineering": {"react", "nextjs", "typescript", "python", "rust", "debug", "test", "graphql", "api"},
    "devops-sre": {"terraform", "docker", "kubernetes", "aws", "infra", "ci", "cd", "runbook", "sre"},
    "finance-investing": {"finance", "invest", "portfolio", "valuation", "stock", "trading"},
    "growth-operations-xiaohongshu": {"seo", "marketing", "campaign", "growth", "social"},
    "product-design": {"design", "ux", "ui", "figma", "landing-page"},
    "security-and-reliability": {"security", "compliance", "threat", "reliability", "audit"},
    "ai-agent-platform": {"agent", "llm", "prompt", "rag", "memory"},
    "engineering-workflow-automation": {"automation", "workflow", "review", "refactor", "scraping"},
    "operations-general": {"summary", "communication", "productivity", "search"},
    "task-understanding-decomposition": {"plan", "task", "decomposition", "subagent"},
    "deployment-platforms": {"vercel", "cloudflare", "render", "netlify", "deploy"},
    "office-automation": {"spreadsheet", "excel", "ppt", "document", "notion"},
    "media-and-content": {"video", "content", "script", "audio", "image"},
    "cross-border-ecommerce": {"ecommerce", "sourcing", "tariff", "product-selection"},
    "customer-lifecycle": {"customer", "crm", "retention", "onboarding", "churn"},
}

ACTIONABLE_NAME_TOKENS = {
    "best-practices": 12,
    "automation": 10,
    "debug": 10,
    "security": 12,
    "deploy": 10,
    "review": 8,
    "testing": 8,
    "runbook": 9,
    "infra": 8,
}

FULL_PIPELINE_COMMANDS = [
    ["scripts/enrich_frontmatter.py"],
    ["scripts/bootstrap_in_house_sources.py", "--write-json", "docs/sources/in-house.skills.json"],
    ["scripts/refresh_repo_views.py"],
    ["scripts/generate_tags_index.py"],
    ["scripts/build_catalog_json.py"],
    ["scripts/check_readme_sync.py"],
    ["scripts/lint_skill_quality.py", "--min-lines", "50"],
    ["scripts/audit_licenses.py"],
    ["-m", "unittest", "discover", "tests", "-v"],
]

DEFAULT_POLICY = {
    "allow_repos": [],
    "deny_repos": [],
    "prefer_repos": {},
    "min_repo_stars": 0,
    "min_score_override": None,
    "unlicensed_auto_rewrite_min_score": DEFAULT_UNLICENSED_REWRITE_MIN_SCORE,
    "unlicensed_auto_rewrite_min_lines": DEFAULT_UNLICENSED_REWRITE_MIN_LINES,
}


def resolve_python_cmd() -> list[str]:
    return [sys.executable] if sys.executable else ["python"]


def load_curation_policy(path: Path | None = None) -> dict:
    policy = dict(DEFAULT_POLICY)
    if path is None or not path.exists():
        return policy

    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        policy.update(raw)
    policy["allow_repos"] = list(policy.get("allow_repos") or [])
    policy["deny_repos"] = list(policy.get("deny_repos") or [])
    policy["prefer_repos"] = dict(policy.get("prefer_repos") or {})
    policy["min_repo_stars"] = int(policy.get("min_repo_stars") or 0)
    policy["unlicensed_auto_rewrite_min_score"] = int(
        policy.get("unlicensed_auto_rewrite_min_score") or DEFAULT_UNLICENSED_REWRITE_MIN_SCORE
    )
    policy["unlicensed_auto_rewrite_min_lines"] = int(
        policy.get("unlicensed_auto_rewrite_min_lines") or DEFAULT_UNLICENSED_REWRITE_MIN_LINES
    )
    return policy


def run_command(
    cmd: list[str],
    *,
    cwd: Path,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        text=True,
        capture_output=capture_output,
    )


def fetch_url(url: str, headers: dict | None = None) -> str | None:
    request_headers = {"User-Agent": "skills-auto-curator"}
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(url, headers=request_headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError):
        return None


def github_api_get(url: str, token: str | None = None) -> dict | list | None:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    raw = fetch_url(url, headers=headers)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def parse_frontmatter(markdown: str) -> dict[str, str]:
    match = re.match(r"^---\s*\n(.*?)\n---", markdown, re.DOTALL)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if line.startswith((" ", "\t")) or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def normalize_license_tag(value: str) -> str:
    raw = value.strip().strip('"').strip("'")
    return GITHUB_LICENSE_KEYS.get(raw.lower(), raw)


def fetch_repo_license(repo: str | None, token: str | None = None) -> str | None:
    if not repo:
        return None
    payload = github_api_get(f"https://api.github.com/repos/{repo}", token)
    if not isinstance(payload, dict):
        return None
    key = ((payload.get("license") or {}).get("key") or "").lower()
    return GITHUB_LICENSE_KEYS.get(key)


def resolve_candidate_license(markdown: str, repo: str | None, token: str | None = None) -> str | None:
    frontmatter_license = normalize_license_tag(parse_frontmatter(markdown).get("license", ""))
    if frontmatter_license in PERMISSIVE_LICENSES:
        return frontmatter_license
    repo_license = fetch_repo_license(repo, token)
    if repo_license in PERMISSIVE_LICENSES:
        return repo_license
    return None


def get_local_skill_names(skills_dir: Path) -> set[str]:
    names = set()
    if not skills_dir.exists():
        return names
    for skill_md in skills_dir.glob("*/*/SKILL.md"):
        names.add(skill_md.parent.name)
    return names


def parse_repo_from_candidate(candidate: dict) -> str | None:
    source = candidate.get("source", "")
    match = re.search(r"\(([^)]+/[^)]+)\)", source)
    if match:
        return match.group(1)

    url = candidate.get("url", "")
    match = re.search(r"github\.com/([^/]+/[^/]+)", url)
    if match:
        return match.group(1)
    return None


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "unnamed-skill"


def suggest_category(name: str, description: str) -> str:
    haystack = f"{name} {description}".lower()
    best_category = "operations-general"
    best_score = 0
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for token in keywords if token in haystack)
        if score > best_score:
            best_category = category
            best_score = score
    return best_category


def score_candidate(candidate: dict) -> tuple[int, list[str]]:
    name = candidate.get("name", "")
    description = candidate.get("description", "")
    source = candidate.get("source", "")
    repo = parse_repo_from_candidate(candidate)

    score = 0
    reasons: list[str] = []

    if repo and repo in TRUSTED_SOURCE_SCORES:
        score += TRUSTED_SOURCE_SCORES[repo]
        reasons.append(f"trusted_source:{repo}")
    elif source.startswith("skills.sh"):
        score += 12
        reasons.append("trusted_registry:skills.sh")
    elif source.startswith("GitHub"):
        score += 8
        reasons.append("trusted_registry:github")

    stars = int(candidate.get("repo_stars", 0) or 0)
    if stars > 0:
        star_score = min(15, int(math.log10(stars + 1) * 5))
        score += star_score
        reasons.append(f"popularity:{star_score}")

    lowered = f"{name} {description}".lower()
    for token, bonus in ACTIONABLE_NAME_TOKENS.items():
        if token in lowered:
            score += bonus
            reasons.append(f"keyword:{token}")

    if len(description.strip()) >= 20:
        score += 6
        reasons.append("descriptive_summary")

    if "[repo]" in name:
        score -= 20
        reasons.append("repo_only_not_skill")

    return score, reasons


def evaluate_policy(candidate: dict, policy: dict) -> tuple[bool, str | None, int]:
    repo = parse_repo_from_candidate(candidate)
    stars = int(candidate.get("repo_stars", 0) or 0)
    allow_repos = set(policy.get("allow_repos") or [])
    deny_repos = set(policy.get("deny_repos") or [])
    prefer_repos = dict(policy.get("prefer_repos") or {})
    min_repo_stars = int(policy.get("min_repo_stars") or 0)

    if allow_repos and repo not in allow_repos:
        return False, "not_in_allowlist", 0
    if repo in deny_repos:
        return False, "deny_repo", 0
    if stars < min_repo_stars:
        return False, "below_min_repo_stars", 0
    return True, None, int(prefer_repos.get(repo, 0) or 0)


def rank_discoveries(
    report: dict,
    *,
    existing_names: set[str],
    limit: int,
    min_score: int = 0,
    policy: dict | None = None,
) -> tuple[list[dict], list[dict]]:
    ranked = []
    skipped = []
    policy = policy or dict(DEFAULT_POLICY)
    effective_min_score = policy.get("min_score_override")
    effective_min_score = min_score if effective_min_score in (None, "") else int(effective_min_score)

    for item in report.get("discoveries", []):
        name = item.get("name", "").strip()
        if not name:
            skipped.append({"name": name, "reason": "missing_name"})
            continue
        if name in existing_names:
            skipped.append({"name": name, "reason": "already_indexed"})
            continue
        if name.startswith("[repo]"):
            skipped.append({"name": name, "reason": "repo_only_not_skill"})
            continue

        allowed, reason, policy_bonus = evaluate_policy(item, policy)
        if not allowed:
            skipped.append({"name": name, "reason": reason, "source_repo": parse_repo_from_candidate(item)})
            continue

        score, reasons = score_candidate(item)
        if policy_bonus:
            score += policy_bonus
            reasons.append(f"policy_bonus:{policy_bonus}")
        if score < effective_min_score:
            skipped.append({"name": name, "reason": "below_min_score", "score": score})
            continue

        candidate = dict(item)
        candidate["slug"] = slugify(name)
        candidate["curation_score"] = score
        candidate["score_reasons"] = reasons
        candidate["recommended_category"] = suggest_category(name, item.get("description", ""))
        candidate["source_repo"] = parse_repo_from_candidate(item)
        ranked.append(candidate)

    ranked.sort(key=lambda item: (-item["curation_score"], -int(item.get("repo_stars", 0) or 0), item["name"]))
    return ranked[:limit], skipped


def curate_candidates(
    *,
    repo_root: Path,
    discovery_output: Path,
    candidate_output: Path,
    top: int,
    min_score: int,
    policy: dict | None = None,
) -> dict:
    report = json.loads(discovery_output.read_text(encoding="utf-8"))
    ranked, skipped = rank_discoveries(
        report,
        existing_names=get_local_skill_names(repo_root / "skills"),
        limit=top,
        min_score=min_score,
        policy=policy,
    )
    payload = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_report": str(discovery_output.relative_to(repo_root)),
        "selected_count": len(ranked),
        "selected": ranked,
        "skipped_count": len(skipped),
        "skipped": skipped,
    }
    candidate_output.parent.mkdir(parents=True, exist_ok=True)
    candidate_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def build_execution_plan(
    *,
    python_cmd: list[str],
    discovery_output: str,
    candidate_output: str,
    sync_mode: str,
    top: int,
    min_score: int,
    policy_path: str,
) -> list[dict]:
    steps: list[dict] = []
    if sync_mode == "check":
        steps.append({"name": "sync-upstream-check", "cmd": python_cmd + ["scripts/sync_upstream.py", "--check-only"]})
    elif sync_mode == "apply":
        steps.append({"name": "sync-upstream-apply", "cmd": python_cmd + ["scripts/sync_upstream.py", "--apply"]})

    steps.append(
        {
            "name": "discover-new-skills",
            "cmd": python_cmd + ["scripts/discover_new_skills.py", "--output", discovery_output],
        }
    )
    steps.append(
        {
            "name": "rank-candidates",
            "cmd": python_cmd
            + [
                "scripts/auto_curate_skills.py",
                "--curate-only",
                "--discovery-output",
                discovery_output,
                "--candidate-output",
                candidate_output,
                "--top",
                str(top),
                "--min-score",
                str(min_score),
                "--policy",
                policy_path,
            ],
        }
    )

    for command in FULL_PIPELINE_COMMANDS:
        steps.append({"name": command[0], "cmd": python_cmd + command})
    return steps


def run_plan(steps: list[dict], *, repo_root: Path) -> None:
    for step in steps:
        cmd = step["cmd"]
        print("$", " ".join(cmd))
        run_command(cmd, cwd=repo_root)


def build_branch_name(topic: str, timestamp: datetime | None = None) -> str:
    timestamp = timestamp or datetime.now(UTC)
    slug = slugify(topic)
    return f"codex/{slug}-{timestamp.strftime('%Y%m%d-%H%M%S')}"


def get_git_status(repo_root: Path) -> str:
    result = run_command(["git", "status", "--short"], cwd=repo_root, capture_output=True)
    return result.stdout.strip()


def assert_clean_worktree(repo_root: Path, status_output: str | None = None) -> None:
    status = status_output if status_output is not None else get_git_status(repo_root)
    if status.strip():
        raise RuntimeError("Cannot auto-commit or open PR from a dirty worktree.")


def write_pr_summary(
    output_path: Path,
    *,
    candidate_report: dict,
    ingest_result: dict,
    sync_mode: str,
    branch_name: str,
    base_branch: str,
) -> None:
    selected = candidate_report.get("selected", [])
    ingested = ingest_result.get("ingested", [])
    skipped = ingest_result.get("skipped", [])
    rewritten = ingest_result.get("unlicensed_rewrites", [])

    lines = [
        "# Skills curation automation",
        "",
        "## Summary",
        f"- Sync mode: `{sync_mode}`",
        f"- Target base branch: `{base_branch}`",
        f"- Working branch: `{branch_name}`",
        f"- Ranked candidates: `{candidate_report.get('selected_count', len(selected))}`",
        f"- Ingested candidates: `{len(ingested)}`",
        f"- Auto-rewritten unlicensed candidates: `{len(rewritten)}`",
        f"- Skipped candidates: `{len(skipped)}`",
        "",
        "## Top candidates",
    ]

    if selected:
        for item in selected[:10]:
            lines.append(
                f"- `{item['name']}` score={item.get('curation_score', '-')}, category=`{item.get('recommended_category', '-')}`"
            )
    else:
        lines.append("- No candidates selected.")

    lines.extend(["", "## Ingested"])
    if ingested:
        for item in ingested:
            lines.append(f"- `{item['name']}` -> `{item['path']}`")
    else:
        lines.append("- No candidates were ingested.")

    lines.extend(["", "## Auto-Rewritten Unlicensed Candidates"])
    if rewritten:
        for item in rewritten:
            lines.append(
                f"- `{item['name']}` -> `{item['path']}` score={item.get('curation_score', '-')}, source=`{item.get('source_repo', '-')}`"
            )
    else:
        lines.append("- No unlicensed candidates required in-house rewriting.")

    lines.extend(["", "## Skipped"])
    if skipped:
        for item in skipped:
            lines.append(f"- `{item['name']}` skipped: `{item['reason']}`")
    else:
        lines.append("- No candidates were skipped.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_branch(repo_root: Path, branch_name: str) -> None:
    run_command(["git", "switch", "-c", branch_name], cwd=repo_root)


def stage_and_commit(repo_root: Path, message: str) -> bool:
    status = get_git_status(repo_root)
    if not status:
        return False
    run_command(["git", "add", "-A"], cwd=repo_root)
    run_command(["git", "commit", "-m", message], cwd=repo_root)
    return True


def gh_is_authenticated(repo_root: Path) -> bool:
    result = run_command(["gh", "auth", "status"], cwd=repo_root, check=False, capture_output=True)
    return result.returncode == 0


def create_pull_request(
    repo_root: Path,
    *,
    base_branch: str,
    title: str,
    body_path: Path,
) -> None:
    run_command(
        [
            "gh",
            "pr",
            "create",
            "--base",
            base_branch,
            "--title",
            title,
            "--body-file",
            str(body_path),
        ],
        cwd=repo_root,
    )


def github_raw_url(repo: str, path: str, ref: str = "main") -> str:
    return f"https://raw.githubusercontent.com/{repo}/{ref}/{path}"


def discover_upstream_skill_path(repo: str, slug: str, token: str | None) -> str | None:
    guesses = [
        f"skills/{slug}/SKILL.md",
        f"{slug}/SKILL.md",
    ]
    for guess in guesses:
        if fetch_url(github_raw_url(repo, guess)):
            return guess

    query = urllib.parse.quote(f"filename:SKILL.md repo:{repo} {slug}")
    results = github_api_get(f"https://api.github.com/search/code?q={query}&per_page=10", token)
    if not isinstance(results, dict):
        return None
    for item in results.get("items", []):
        path = item.get("path", "")
        if path.endswith("/SKILL.md") and slug in path.lower():
            return path
    return None


def synthesize_frontmatter(markdown: str, *, slug: str, description: str, source_id: str, source_url: str, license_tag: str | None = None) -> str:
    if markdown.startswith("---\n") and re.search(r"^name:\s*", markdown, re.MULTILINE):
        if license_tag and not re.search(r"^license:\s*", markdown, re.MULTILINE):
            return re.sub(r"\n---\s*\n", f"\nlicense: {license_tag}\n---\n", markdown, count=1)
        return markdown

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    desc = description.strip() or f"Imported skill for {slug}."
    frontmatter = [
        "---",
        f"name: {slug}",
        f'description: "{desc.replace(chr(34), chr(39))}"',
        'version: "1.0.0"',
        'author: "seaworld008"',
        f'source: "{source_id}"',
        f'source_url: "{source_url}"',
        'tags: ["imported"]',
        f'created_at: "{today}"',
        f'updated_at: "{today}"',
        "quality: 2",
        'complexity: "intermediate"',
        "---",
        "",
    ]
    if license_tag:
        frontmatter.insert(6, f"license: {license_tag}")
    return "\n".join(frontmatter) + markdown.lstrip()


def fetch_candidate_markdown(candidate: dict, token: str | None = None) -> tuple[str | None, str | None]:
    url = candidate.get("url", "")
    repo = candidate.get("source_repo")
    slug = candidate.get("slug") or slugify(candidate.get("name", ""))

    blob_match = re.search(r"github\.com/([^/]+/[^/]+)/blob/([^/]+)/(.*)$", url)
    if blob_match:
        repo = blob_match.group(1)
        ref = blob_match.group(2)
        path = blob_match.group(3)
        return fetch_url(github_raw_url(repo, path, ref)), repo

    if repo:
        path = discover_upstream_skill_path(repo, slug, token)
        if path:
            return fetch_url(github_raw_url(repo, path)), repo
    return None, repo


def build_license_review_entry(candidate: dict, repo: str | None, reason: str) -> dict:
    return {
        "name": candidate.get("name", ""),
        "slug": candidate.get("slug", slugify(candidate.get("name", ""))),
        "source_repo": repo or candidate.get("source_repo"),
        "source": candidate.get("source", ""),
        "url": candidate.get("url", ""),
        "recommended_category": candidate.get("recommended_category", ""),
        "curation_score": candidate.get("curation_score"),
        "score_reasons": candidate.get("score_reasons", []),
        "reason": reason,
    }


def should_auto_rewrite_unlicensed(candidate: dict, markdown: str, policy: dict | None = None) -> bool:
    policy = policy or DEFAULT_POLICY
    min_score = int(policy.get("unlicensed_auto_rewrite_min_score") or DEFAULT_UNLICENSED_REWRITE_MIN_SCORE)
    min_lines = int(policy.get("unlicensed_auto_rewrite_min_lines") or DEFAULT_UNLICENSED_REWRITE_MIN_LINES)
    score = int(candidate.get("curation_score", 0) or 0)
    line_count = len(markdown.splitlines())
    return score >= min_score and line_count >= min_lines


def infer_tags_from_candidate(candidate: dict) -> list[str]:
    tokens = [
        token
        for token in re.split(r"[^a-z0-9]+", f"{candidate.get('slug', '')} {candidate.get('recommended_category', '')}".lower())
        if len(token) >= 3
    ]
    tags = ["in-house", "curated"]
    for token in tokens:
        if token not in tags:
            tags.append(token)
        if len(tags) >= 6:
            break
    return tags


def build_in_house_skill_from_candidate(candidate: dict, repo: str | None) -> str:
    """Create original in-house skill content without copying unlicensed upstream text."""
    slug = candidate.get("slug") or slugify(candidate.get("name", ""))
    title = candidate.get("name", slug).strip() or slug
    category = candidate.get("recommended_category", "operations-general")
    description = candidate.get("description", "").strip() or f"Curated in-house skill for {title} workflows."
    source_url = candidate.get("url", "")
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    tags = ", ".join(f'"{tag}"' for tag in infer_tags_from_candidate(candidate))
    score_reasons = candidate.get("score_reasons", [])
    reason_lines = "\n".join(f"- {reason}" for reason in score_reasons[:8]) or "- Strong topical fit from automated curation signals."

    return f"""---
name: {slug}
description: "{description.replace(chr(34), chr(39))}"
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
license: MIT
tags: [{tags}]
created_at: "{today}"
updated_at: "{today}"
quality: 4
complexity: "intermediate"
---

# {title}

This is an original in-house skill generated from repository curation signals. The upstream candidate had no detectable permissive license, so its text was not copied. Use this skill as the maintained local version for `{category}` work.

## When to Use

- You need a repeatable workflow for `{title}` instead of one-off improvisation.
- You want the agent to choose tools, checks, and outputs before editing files.
- You are working in a repository where changes should be small, auditable, and easy to review.
- You need practical guidance that can be followed by an autonomous coding agent.
- You want decisions to be grounded in local project conventions.
- You need a consistent handoff format for future agents.
- You want quality gates to run before code is committed.
- You need a skill that is safe to distribute under this repository's MIT license.

## Core Capabilities

- Convert vague requests into a scoped execution plan.
- Inspect the current repository before changing behavior.
- Identify the files, scripts, commands, and generated artifacts that matter.
- Prefer established local patterns over new abstractions.
- Apply changes in small, reviewable increments.
- Keep generated files and source-of-truth files separate.
- Run targeted validation before broader pipelines.
- Summarize outcomes with commit-ready evidence.

## Curation Signal

This local skill was created because the candidate scored highly during automated discovery, but its upstream license could not be confirmed.

Candidate metadata:

- Candidate name: `{title}`
- Recommended category: `{category}`
- Source repository: `{repo or candidate.get('source_repo') or 'unknown'}`
- Candidate URL: `{source_url or 'unknown'}`
- Curation score: `{candidate.get('curation_score', '-')}`

Score reasons:

{reason_lines}

## Operating Workflow

1. Restate the user's goal in concrete terms.
2. Inspect the relevant files with fast search tools such as `rg` and `rg --files`.
3. Identify source-of-truth files before touching generated outputs.
4. Decide whether the task is a narrow fix, a workflow change, or a catalog update.
5. Make the smallest coherent implementation.
6. Update tests or add focused coverage for changed behavior.
7. Run the repository's quality gates.
8. Review the diff for unrelated generated noise.
9. Commit with a message that describes the behavior change.
10. Push and verify CI when the task changes automation or release behavior.

## Input Template

```yaml
goal: "What the user wants done"
scope:
  include:
    - "Files, directories, or workflows that may change"
  exclude:
    - "Generated files or unrelated areas to leave alone"
quality_gates:
  - "python scripts/lint_skill_quality.py --min-lines 50"
  - "python scripts/audit_licenses.py"
  - "python -m unittest discover tests -v"
handoff:
  summary: "What changed and why"
  evidence: "Commands run and CI status"
```

## Decision Rules

| Situation | Action |
|---|---|
| Local conventions exist | Follow them exactly. |
| The change affects generated artifacts | Update source files first, then regenerate. |
| A candidate has no license | Do not copy upstream text; generate original in-house guidance. |
| Tests are expensive | Run focused tests first, then the required pipeline. |
| CI has failed before | Add a guard or test that prevents the same failure mode. |
| Diff includes unrelated churn | Remove the churn before commit. |

## Implementation Patterns

Use this pattern when turning the skill into action:

```text
1. Discover context with read-only commands.
2. Choose the smallest responsible edit.
3. Patch source files.
4. Run targeted validation.
5. Run repository-level validation.
6. Commit and push only after checks pass.
```

Use this pattern when the task involves external material:

```text
if external_license_is_permissive:
    import_with_license_metadata()
elif candidate_is_high_quality:
    create_original_in_house_skill_without_copying_upstream_text()
else:
    skip_candidate()
```

## Quality Checklist

- The skill has complete frontmatter.
- `name` matches the skill directory.
- `source` is accurate for the actual content.
- External content includes license metadata before import.
- In-house rewrites do not copy unlicensed upstream wording.
- The body has actionable workflow guidance.
- The body includes examples or templates.
- The body explains boundaries.
- Generated artifacts are refreshed by scripts.
- Quality lint passes at the configured minimum line count.
- License audit reports zero missing licenses.
- Unit tests cover the automation path that changed.

## Boundaries

- Do not copy text from sources with missing, unknown, or restrictive licenses.
- Do not mark externally copied content as `in-house`.
- Do not lower quality gates to force an import.
- Do not commit report noise from ignored discovery outputs unless explicitly requested.
- Do not replace a mature existing skill unless the new version is clearly stronger.
- Do not skip CI verification for changes to automation, provenance, or licensing.

## Output Format

When finished, report:

- Files changed.
- Whether the skill was imported or rewritten in-house.
- Validation commands and results.
- Any candidates skipped for low quality or missing source files.
- Commit hash and CI status when changes were pushed.
"""


def write_license_rewrite_log(repo_root: Path, entries: list[dict], output_path: str = DEFAULT_LICENSE_REWRITE_LOG) -> None:
    payload = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rewrite_count": len(entries),
        "policy": "High-quality external candidates without a detectable permissive license are auto-rewritten as original in-house MIT skills; upstream text is not copied.",
        "rewrites": entries,
    }
    out = repo_root / output_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ingest_candidates(
    *,
    repo_root: Path,
    report: dict,
    limit: int,
    python_cmd: list[str],
    policy: dict | None = None,
) -> dict:
    token = None
    ingested = []
    skipped = []
    unlicensed_rewrites = []
    policy = policy or DEFAULT_POLICY

    for candidate in report.get("selected", [])[:limit]:
        markdown, repo = fetch_candidate_markdown(candidate, token=token)
        if not markdown:
            skipped.append({"name": candidate["name"], "reason": "upstream_markdown_not_found"})
            continue
        if len(markdown.splitlines()) < 50:
            skipped.append({"name": candidate["name"], "reason": "content_below_quality_floor"})
            continue
        license_tag = resolve_candidate_license(markdown, repo, token)
        if not license_tag:
            if not should_auto_rewrite_unlicensed(candidate, markdown, policy):
                skipped.append(build_license_review_entry(candidate, repo, "missing_or_unapproved_license"))
                continue
            category = candidate["recommended_category"]
            slug = candidate["slug"]
            skill_dir = repo_root / "skills" / category / slug
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(build_in_house_skill_from_candidate(candidate, repo), encoding="utf-8")
            cmd = python_cmd + [
                "scripts/ingest_skill.py",
                "--dir",
                str(skill_dir.relative_to(repo_root)),
                "--source",
                "in-house",
                "--skip-pipeline",
            ]
            run_command(cmd, cwd=repo_root)
            rewrite_entry = {
                "name": candidate["name"],
                "path": str(skill_dir.relative_to(repo_root)),
                "source_repo": repo or candidate.get("source_repo"),
                "source_url": candidate.get("url", ""),
                "curation_score": candidate.get("curation_score"),
                "reason": "auto_rewritten_from_unlicensed_high_quality_candidate",
            }
            ingested.append({"name": candidate["name"], "path": str(skill_dir.relative_to(repo_root)), "mode": "in_house_rewrite"})
            unlicensed_rewrites.append(rewrite_entry)
            continue

        category = candidate["recommended_category"]
        slug = candidate["slug"]
        skill_dir = repo_root / "skills" / category / slug
        skill_dir.mkdir(parents=True, exist_ok=True)

        source_id = f"github:{repo}" if repo else "community"
        prepared = synthesize_frontmatter(
            markdown,
            slug=slug,
            description=candidate.get("description", ""),
            source_id=source_id,
            source_url=candidate.get("url", ""),
            license_tag=license_tag,
        )
        (skill_dir / "SKILL.md").write_text(prepared, encoding="utf-8")

        cmd = python_cmd + [
            "scripts/ingest_skill.py",
            "--dir",
            str(skill_dir.relative_to(repo_root)),
            "--source",
            source_id,
            "--source-url",
            candidate.get("url", ""),
            "--skip-pipeline",
        ]
        run_command(cmd, cwd=repo_root)
        ingested.append({"name": candidate["name"], "path": str(skill_dir.relative_to(repo_root))})

    write_license_rewrite_log(repo_root, unlicensed_rewrites)
    return {"ingested": ingested, "skipped": skipped, "unlicensed_rewrites": unlicensed_rewrites}


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified sync + discovery + curation workflow.")
    parser.add_argument("--sync-mode", choices=["skip", "check", "apply"], default="check")
    parser.add_argument("--discovery-output", default="docs/sources/reports/discovery.json")
    parser.add_argument("--candidate-output", default="docs/sources/reports/curation-candidates.json")
    parser.add_argument("--policy", default=DEFAULT_POLICY_PATH, help="Path to curation policy JSON")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--min-score", type=int, default=20)
    parser.add_argument("--curate-only", action="store_true", help="Only rank candidates from an existing discovery report")
    parser.add_argument("--execute", action="store_true", help="Run the generated orchestration plan")
    parser.add_argument("--auto-ingest-top", type=int, default=0, help="Best-effort fetch and ingest the top N ranked candidates")
    parser.add_argument("--skip-pipeline", action="store_true", help="Skip the post-ingestion refresh pipeline")
    parser.add_argument("--prepare-pr", action="store_true", help="Write PR summary and prepare a branch after execution")
    parser.add_argument("--open-pr", action="store_true", help="Open a GitHub PR after commit")
    parser.add_argument("--branch-name", default=None, help="Override the generated codex/ branch name")
    parser.add_argument("--base-branch", default="main", help="Base branch for the pull request")
    parser.add_argument("--commit-message", default="feat: automate skills curation update", help="Commit message for auto-generated changes")
    parser.add_argument("--pr-title", default="feat: automate skills curation update", help="PR title when --open-pr is used")
    parser.add_argument("--pr-body-path", default=DEFAULT_PR_BODY, help="Where to write the PR body markdown")
    args = parser.parse_args()

    repo_root = REPO_ROOT
    discovery_output = repo_root / args.discovery_output
    candidate_output = repo_root / args.candidate_output
    policy_path = repo_root / args.policy
    python_cmd = resolve_python_cmd()
    initial_status = get_git_status(repo_root) if (args.prepare_pr or args.open_pr) else ""
    policy = load_curation_policy(policy_path)
    if args.prepare_pr or args.open_pr:
        assert_clean_worktree(repo_root, status_output=initial_status)

    if args.curate_only:
        report = curate_candidates(
            repo_root=repo_root,
            discovery_output=discovery_output,
            candidate_output=candidate_output,
            top=args.top,
            min_score=args.min_score,
            policy=policy,
        )
        print(f"Wrote candidate report: {candidate_output.relative_to(repo_root)} ({report['selected_count']} selected)")
        return 0

    steps = build_execution_plan(
        python_cmd=python_cmd,
        discovery_output=args.discovery_output,
        candidate_output=args.candidate_output,
        sync_mode=args.sync_mode,
        top=args.top,
        min_score=args.min_score,
        policy_path=args.policy,
    )

    if not args.execute:
        print("Planned commands:")
        for step in steps:
            print("$", " ".join(step["cmd"]))
        return 0

    pre_pipeline = steps[:-len(FULL_PIPELINE_COMMANDS)]
    pipeline_steps = steps[-len(FULL_PIPELINE_COMMANDS):]
    run_plan(pre_pipeline, repo_root=repo_root)

    report = json.loads(candidate_output.read_text(encoding="utf-8"))
    ingest_result = {"ingested": [], "skipped": []}
    if args.auto_ingest_top > 0:
        ingest_result = ingest_candidates(
            repo_root=repo_root,
            report=report,
            limit=args.auto_ingest_top,
            python_cmd=python_cmd,
            policy=policy,
        )
        print(json.dumps(ingest_result, ensure_ascii=False, indent=2))
    if not args.skip_pipeline:
        run_plan(pipeline_steps, repo_root=repo_root)

    if args.prepare_pr or args.open_pr:
        branch_name = args.branch_name or build_branch_name("skills-curation")
        ensure_branch(repo_root, branch_name)
        pr_body_path = repo_root / args.pr_body_path
        write_pr_summary(
            pr_body_path,
            candidate_report=report,
            ingest_result=ingest_result,
            sync_mode=args.sync_mode,
            branch_name=branch_name,
            base_branch=args.base_branch,
        )
        committed = stage_and_commit(repo_root, args.commit_message)
        if not committed:
            print("No changes detected after curation; skipped commit/PR preparation.")
            return 0
        if args.open_pr:
            if not gh_is_authenticated(repo_root):
                raise RuntimeError("GitHub CLI is not authenticated; cannot open PR.")
            create_pull_request(
                repo_root,
                base_branch=args.base_branch,
                title=args.pr_title,
                body_path=pr_body_path,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
