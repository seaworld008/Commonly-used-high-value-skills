#!/usr/bin/env python3
"""Import and refresh addyosmani/agent-skills into the AI workflow category.

The upstream project is a fast-moving source of engineering workflow skills.
This script keeps our local copy reproducible:

* imports every upstream skills/<slug>/SKILL.md into skills/ai-workflow/<slug>
* preserves complete repository frontmatter and upstream provenance
* moves existing local AI workflow skills into the same category
* writes docs/sources/addyosmani-agent-skills-2026-04.skills.json
* copies upstream references and install/configuration bundle material

Typical use:
    python scripts/sync_addyosmani_agent_skills.py --apply
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path
from typing import NamedTuple


REPO_ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_REPO = "addyosmani/agent-skills"
UPSTREAM_URL = f"https://github.com/{UPSTREAM_REPO}.git"
UPSTREAM_WEB = f"https://github.com/{UPSTREAM_REPO}"
DEFAULT_CATEGORY = "ai-workflow"
MAPPING_FILE = "docs/sources/addyosmani-agent-skills-2026-04.skills.json"

EXISTING_AI_WORKFLOW_SKILLS = {
    "agent-workflow-designer",
    "brainstorming",
    "context-engineering",
    "deep-research",
    "dispatching-parallel-agents",
    "executing-plans",
    "find-skills",
    "finishing-a-development-branch",
    "prompt-optimizer",
    "receiving-code-review",
    "requesting-code-review",
    "skill-creator",
    "skill-reviewer",
    "skills-search",
    "subagent-driven-development",
    "test-driven-development",
    "using-git-worktrees",
    "using-superpowers",
    "verification-before-completion",
    "writing-plans",
    "writing-skills",
}

SHARED_REFERENCE_DIRS = ("references",)
UPSTREAM_BUNDLE_PATHS = (
    ".claude/commands",
    ".claude-plugin",
    "agents",
    "docs",
    "hooks",
    "references",
)

POST_SYNC_PIPELINE = (
    ("python", "scripts/enrich_frontmatter.py"),
    ("python", "scripts/bootstrap_in_house_sources.py", "--write-json", "docs/sources/in-house.skills.json"),
    ("python", "scripts/refresh_repo_views.py"),
    ("python", "scripts/generate_tags_index.py"),
    ("python", "scripts/build_catalog_json.py"),
    ("python", "scripts/generate_sources_index.py"),
    ("python", "scripts/lint_skill_quality.py", "--min-lines", "50"),
    ("python", "-m", "unittest", "discover", "tests", "-v"),
)


class UpstreamSkill(NamedTuple):
    slug: str
    source_dir: Path
    skill_file: Path
    description: str
    line_count: int


def run(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def clone_upstream(repo_url: str, ref: str, destination: Path) -> None:
    run(["git", "clone", "--depth", "1", "--branch", ref, repo_url, str(destination)])


def resolve_upstream(repo_url: str, ref: str, upstream_dir: Path | None) -> tuple[Path, str, tempfile.TemporaryDirectory[str] | None]:
    if upstream_dir is not None:
        upstream = upstream_dir.resolve()
        commit = run(["git", "rev-parse", "HEAD"], cwd=upstream)
        return upstream, commit, None

    temp = tempfile.TemporaryDirectory(prefix="agent-skills-")
    upstream = Path(temp.name) / "repo"
    clone_upstream(repo_url, ref, upstream)
    commit = run(["git", "rev-parse", "HEAD"], cwd=upstream)
    return upstream, commit, temp


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def strip_frontmatter(text: str) -> str:
    return re.sub(r"^---\s*\n.*?\n---\s*\n?", "", text, count=1, flags=re.DOTALL).lstrip()


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def format_tags(tags: list[str]) -> str:
    return "[" + ", ".join(yaml_quote(tag) for tag in sorted(dict.fromkeys(tags))) + "]"


def quality_for_lines(line_count: int) -> int:
    if line_count >= 200:
        return 5
    if line_count >= 100:
        return 4
    if line_count >= 80:
        return 3
    return 2


def discover_upstream_skills(upstream_root: Path) -> list[UpstreamSkill]:
    skills: list[UpstreamSkill] = []
    for skill_file in sorted((upstream_root / "skills").glob("*/SKILL.md")):
        text = skill_file.read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(text)
        slug = skill_file.parent.name
        skills.append(
            UpstreamSkill(
                slug=slug,
                source_dir=skill_file.parent,
                skill_file=skill_file,
                description=frontmatter.get("description", ""),
                line_count=len(text.splitlines()),
            )
        )
    return skills


def render_skill_markdown(skill: UpstreamSkill, body: str, today: str) -> str:
    tags = ["ai", "agent", "workflow", "engineering", skill.slug]
    frontmatter = [
        "---",
        f"name: {skill.slug}",
        f"description: {yaml_quote(skill.description)}",
        'version: "1.0.0"',
        "author: addyosmani",
        f"source: {yaml_quote('github:' + UPSTREAM_REPO)}",
        f"source_url: {yaml_quote(f'{UPSTREAM_WEB}/blob/main/skills/{skill.slug}/SKILL.md')}",
        "license: MIT",
        f"tags: {format_tags(tags)}",
        f'created_at: "{today}"',
        f'updated_at: "{today}"',
        f"quality: {quality_for_lines(skill.line_count)}",
        "complexity: advanced",
        f"upstream_slug: {skill.slug}",
        "---",
        "",
    ]
    return "\n".join(frontmatter) + body.rstrip() + "\n"


def replace_directory(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def copy_shared_references(upstream_root: Path, destination: Path) -> None:
    for rel in SHARED_REFERENCE_DIRS:
        source = upstream_root / rel
        if source.exists():
            replace_directory(source, destination / rel)


def copy_upstream_bundle(upstream_root: Path, destination: Path) -> None:
    bundle_root = destination / "upstream-bundle"
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle_root.mkdir(parents=True, exist_ok=True)
    for rel in UPSTREAM_BUNDLE_PATHS:
        source = upstream_root / rel
        if not source.exists():
            continue
        target = bundle_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)


def move_existing_ai_workflow_skills(repo_root: Path, category: str, dry_run: bool) -> dict[str, str]:
    skills_root = repo_root / "skills"
    target_category = skills_root / category
    moved: dict[str, str] = {}
    target_category.mkdir(parents=True, exist_ok=True)

    for skill in sorted(EXISTING_AI_WORKFLOW_SKILLS):
        matches = [
            path.parent
            for path in skills_root.glob(f"*/{skill}/SKILL.md")
            if path.parent.parent.name != category
        ]
        if not matches:
            continue
        source_dir = matches[0]
        target_dir = target_category / skill
        old_rel = (source_dir / "SKILL.md").relative_to(repo_root).as_posix()
        new_rel = (target_dir / "SKILL.md").relative_to(repo_root).as_posix()
        moved[old_rel] = new_rel
        if not dry_run:
            if target_dir.exists():
                shutil.rmtree(source_dir)
            else:
                shutil.move(str(source_dir), str(target_dir))

    return moved


def import_upstream_skills(
    *,
    repo_root: Path,
    upstream_root: Path,
    category: str,
    today: str,
    dry_run: bool,
) -> list[UpstreamSkill]:
    target_category = repo_root / "skills" / category
    target_category.mkdir(parents=True, exist_ok=True)
    skills = discover_upstream_skills(upstream_root)

    for skill in skills:
        destination = target_category / skill.slug
        if dry_run:
            continue
        replace_directory(skill.source_dir, destination)
        body = strip_frontmatter((destination / "SKILL.md").read_text(encoding="utf-8"))
        (destination / "SKILL.md").write_text(render_skill_markdown(skill, body, today), encoding="utf-8")
        copy_shared_references(upstream_root, destination)

    using_agent_skills = target_category / "using-agent-skills"
    if using_agent_skills.exists() and not dry_run:
        copy_upstream_bundle(upstream_root, using_agent_skills)

    return skills


def update_moved_paths_in_source_mappings(repo_root: Path, moved_paths: dict[str, str], dry_run: bool) -> None:
    if not moved_paths:
        return
    upstream_path_updates = dict(moved_paths)
    for old_file, new_file in moved_paths.items():
        upstream_path_updates[old_file.rsplit("/", 1)[0]] = new_file.rsplit("/", 1)[0]
    sources_dir = repo_root / "docs" / "sources"
    for mapping in sorted(sources_dir.glob("*.skills.json")):
        if mapping.name == Path(MAPPING_FILE).name:
            continue
        data = json.loads(mapping.read_text(encoding="utf-8"))
        changed = False
        kept_skills = []
        for entry in data.get("skills", []):
            repo_skill = entry.get("repo_skill")
            if repo_skill in moved_paths:
                entry["repo_skill"] = moved_paths[repo_skill]
                changed = True

            upstream = entry.get("upstream")
            if isinstance(upstream, dict) and upstream.get("path") in upstream_path_updates:
                upstream["path"] = upstream_path_updates[upstream["path"]]
                changed = True

            # addyosmani/agent-skills becomes authoritative for this exact skill.
            if (
                entry.get("video_name") == "test-driven-development"
                and (entry.get("upstream") or {}).get("repo") != UPSTREAM_REPO
            ):
                changed = True
                continue
            kept_skills.append(entry)
        data["skills"] = kept_skills
        if changed and not dry_run:
            mapping.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_source_mapping(
    *,
    repo_root: Path,
    skills: list[UpstreamSkill],
    category: str,
    commit: str,
    today: str,
) -> dict:
    entries = []
    for skill in skills:
        repo_skill = f"skills/{category}/{skill.slug}/SKILL.md"
        entries.append(
            {
                "video_name": skill.slug,
                "normalized_slug": skill.slug,
                "status": "verified_in_repo",
                "repo_skill": repo_skill,
                "source": f"{UPSTREAM_WEB}/blob/main/skills/{skill.slug}/SKILL.md",
                "notes": "Imported from addyosmani/agent-skills into the AI workflow category with repeatable upstream sync.",
                "upstream": {
                    "repo": UPSTREAM_REPO,
                    "path": f"skills/{skill.slug}/SKILL.md",
                    "ref": "main",
                    "last_checked_at": today,
                    "last_synced_at": today,
                    "last_synced_commit": commit,
                },
            }
        )

    return {
        "video": {
            "url": UPSTREAM_WEB,
            "checked_at": today,
            "note": "Curated full import of addyosmani/agent-skills; refresh with scripts/sync_addyosmani_agent_skills.py.",
        },
        "official_references": [
            {
                "name": "addyosmani/agent-skills repository",
                "url": UPSTREAM_WEB,
                "purpose": "Canonical upstream repository for the imported AI workflow skills.",
            },
            {
                "name": "Agent Skills getting started guide",
                "url": f"{UPSTREAM_WEB}/blob/main/docs/getting-started.md",
                "purpose": "Installation and configuration guidance for multiple AI coding clients.",
            },
        ],
        "skills": entries,
        "verification_attempts": [
            {
                "date": today,
                "method": "git-clone-and-local-import",
                "target": f"{UPSTREAM_WEB}@{commit}",
                "result": "success",
                "evidence": f"Imported {len(entries)} upstream skills into skills/{category}/.",
            }
        ],
    }


def write_source_mapping(repo_root: Path, payload: dict, dry_run: bool) -> None:
    output = repo_root / MAPPING_FILE
    if dry_run:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sync_agent_skills(
    *,
    repo_root: Path,
    upstream_root: Path,
    commit: str,
    category: str = DEFAULT_CATEGORY,
    today: str | None = None,
    move_existing: bool = True,
    dry_run: bool = False,
) -> dict:
    today = today or date.today().isoformat()
    moved_paths = move_existing_ai_workflow_skills(repo_root, category, dry_run) if move_existing else {}
    skills = import_upstream_skills(
        repo_root=repo_root,
        upstream_root=upstream_root,
        category=category,
        today=today,
        dry_run=dry_run,
    )
    update_moved_paths_in_source_mappings(repo_root, moved_paths, dry_run)
    payload = build_source_mapping(
        repo_root=repo_root,
        skills=skills,
        category=category,
        commit=commit,
        today=today,
    )
    write_source_mapping(repo_root, payload, dry_run)
    return {
        "imported_count": len(skills),
        "moved_count": len(moved_paths),
        "category": category,
        "mapping": MAPPING_FILE,
        "commit": commit,
    }


def run_post_sync_pipeline(repo_root: Path) -> None:
    for command in POST_SYNC_PIPELINE:
        print("Running:", " ".join(command))
        subprocess.run(command, cwd=repo_root, check=True)


def sync_to_codex(repo_root: Path, codex_root: Path) -> None:
    command = (
        "python",
        "scripts/sync_codex_skills.py",
        "--source-root",
        "skills",
        "--codex-root",
        str(codex_root),
    )
    print("Running:", " ".join(command))
    subprocess.run(command, cwd=repo_root, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync addyosmani/agent-skills into skills/ai-workflow with provenance."
    )
    parser.add_argument("--apply", action="store_true", help="Write changes. Without this, run as a dry run.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root.")
    parser.add_argument("--repo-url", default=UPSTREAM_URL, help="Upstream git URL.")
    parser.add_argument("--ref", default="main", help="Upstream git ref or branch.")
    parser.add_argument("--upstream-dir", type=Path, help="Use an existing local upstream checkout.")
    parser.add_argument("--category", default=DEFAULT_CATEGORY, help="Destination category under skills/.")
    parser.add_argument("--no-move-existing", action="store_true", help="Do not move existing local AI workflow skills.")
    parser.add_argument("--run-pipeline", action="store_true", help="After applying, run the full repository refresh and test pipeline.")
    parser.add_argument("--sync-codex-root", type=Path, help="After applying, sync all repo skills into this Codex skills root.")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    upstream, commit, temp = resolve_upstream(args.repo_url, args.ref, args.upstream_dir)
    try:
        summary = sync_agent_skills(
            repo_root=repo_root,
            upstream_root=upstream,
            commit=commit,
            category=args.category,
            move_existing=not args.no_move_existing,
            dry_run=not args.apply,
        )
    finally:
        if temp is not None:
            temp.cleanup()

    mode = "Applied" if args.apply else "Dry run"
    print(
        f"{mode}: imported {summary['imported_count']} addyosmani skills, "
        f"moved {summary['moved_count']} existing workflow skills into skills/{summary['category']}. "
        f"Mapping: {summary['mapping']}. Commit: {summary['commit']}."
    )
    if args.apply:
        if args.run_pipeline:
            run_post_sync_pipeline(repo_root)
        else:
            print("Next: run with --run-pipeline to refresh generated views and quality gates automatically.")
        if args.sync_codex_root:
            sync_to_codex(repo_root, args.sync_codex_root.expanduser())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
