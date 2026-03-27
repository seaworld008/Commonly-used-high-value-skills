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

TRUSTED_SOURCE_SCORES = {
    "vercel-labs/agent-skills": 28,
    "supabase/agent-skills": 26,
    "obra/superpowers": 24,
    "alirezarezvani/claude-skills": 22,
    "google-labs-code/stitch-skills": 18,
    "ComposioHQ/awesome-claude-skills": 14,
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
    ["scripts/lint_skill_quality.py", "--min-lines", "50"],
    ["-m", "unittest", "discover", "tests", "-v"],
]


def resolve_python_cmd() -> list[str]:
    return [sys.executable] if sys.executable else ["python"]


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


def rank_discoveries(report: dict, *, existing_names: set[str], limit: int, min_score: int = 0) -> list[dict]:
    ranked = []
    for item in report.get("discoveries", []):
        name = item.get("name", "").strip()
        if not name or name in existing_names or name.startswith("[repo]"):
            continue

        score, reasons = score_candidate(item)
        if score < min_score:
            continue

        candidate = dict(item)
        candidate["slug"] = slugify(name)
        candidate["curation_score"] = score
        candidate["score_reasons"] = reasons
        candidate["recommended_category"] = suggest_category(name, item.get("description", ""))
        candidate["source_repo"] = parse_repo_from_candidate(item)
        ranked.append(candidate)

    ranked.sort(key=lambda item: (-item["curation_score"], -int(item.get("repo_stars", 0) or 0), item["name"]))
    return ranked[:limit]


def curate_candidates(
    *,
    repo_root: Path,
    discovery_output: Path,
    candidate_output: Path,
    top: int,
    min_score: int,
) -> dict:
    report = json.loads(discovery_output.read_text(encoding="utf-8"))
    ranked = rank_discoveries(
        report,
        existing_names=get_local_skill_names(repo_root / "skills"),
        limit=top,
        min_score=min_score,
    )
    payload = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_report": str(discovery_output.relative_to(repo_root)),
        "selected_count": len(ranked),
        "selected": ranked,
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

    lines = [
        "# Skills curation automation",
        "",
        "## Summary",
        f"- Sync mode: `{sync_mode}`",
        f"- Target base branch: `{base_branch}`",
        f"- Working branch: `{branch_name}`",
        f"- Ranked candidates: `{candidate_report.get('selected_count', len(selected))}`",
        f"- Ingested candidates: `{len(ingested)}`",
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


def synthesize_frontmatter(markdown: str, *, slug: str, description: str, source_id: str, source_url: str) -> str:
    if markdown.startswith("---\n") and re.search(r"^name:\s*", markdown, re.MULTILINE):
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


def ingest_candidates(
    *,
    repo_root: Path,
    report: dict,
    limit: int,
    python_cmd: list[str],
) -> dict:
    token = None
    ingested = []
    skipped = []

    for candidate in report.get("selected", [])[:limit]:
        markdown, repo = fetch_candidate_markdown(candidate, token=token)
        if not markdown:
            skipped.append({"name": candidate["name"], "reason": "upstream_markdown_not_found"})
            continue
        if len(markdown.splitlines()) < 50:
            skipped.append({"name": candidate["name"], "reason": "content_below_quality_floor"})
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

    return {"ingested": ingested, "skipped": skipped}


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified sync + discovery + curation workflow.")
    parser.add_argument("--sync-mode", choices=["skip", "check", "apply"], default="check")
    parser.add_argument("--discovery-output", default="docs/sources/reports/discovery.json")
    parser.add_argument("--candidate-output", default="docs/sources/reports/curation-candidates.json")
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
    python_cmd = resolve_python_cmd()
    initial_status = get_git_status(repo_root) if (args.prepare_pr or args.open_pr) else ""
    if args.prepare_pr or args.open_pr:
        assert_clean_worktree(repo_root, status_output=initial_status)

    if args.curate_only:
        report = curate_candidates(
            repo_root=repo_root,
            discovery_output=discovery_output,
            candidate_output=candidate_output,
            top=args.top,
            min_score=args.min_score,
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
