#!/usr/bin/env python3
"""Synchronize every auto-upgradeable upstream skill source.

This is the one-command entrypoint for routine repository maintenance:

1. refresh addyosmani/agent-skills with its richer bundle-aware importer
2. refresh all other externally mapped skills through docs/sources provenance
3. optionally run the repository generation, lint, and test pipeline
4. optionally install/sync the result into a local Codex skills root
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ADDY_SOURCE = "github:addyosmani/agent-skills"
SIMOTA_SOURCE = "github:simota/agent-skills"

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


def run(command: tuple[str, ...] | list[str], *, repo_root: Path, enabled: bool = True) -> None:
    print("Running:", " ".join(command))
    if enabled:
        subprocess.run(command, cwd=repo_root, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync all externally tracked upstream skills.")
    parser.add_argument("--apply", action="store_true", help="Write updates. Without this, performs check/dry-run style commands.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root.")
    parser.add_argument("--run-pipeline", action="store_true", help="Run generation, lint, and tests after syncing.")
    parser.add_argument("--sync-codex-root", type=Path, help="Sync all repo skills into this Codex skills root after applying.")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()

    if args.apply:
        run(("python", "scripts/sync_addyosmani_agent_skills.py", "--apply"), repo_root=repo_root)
        run(("python", "scripts/sync_simota_agent_skills.py", "--apply"), repo_root=repo_root)
        run(
            (
                "python",
                "scripts/sync_upstream.py",
                "--apply",
                "--exclude-source",
                ADDY_SOURCE,
                "--exclude-source",
                SIMOTA_SOURCE,
            ),
            repo_root=repo_root,
        )
    else:
        run(("python", "scripts/sync_addyosmani_agent_skills.py"), repo_root=repo_root)
        run(("python", "scripts/sync_simota_agent_skills.py"), repo_root=repo_root)
        run(
            (
                "python",
                "scripts/sync_upstream.py",
                "--check-only",
                "--exclude-source",
                ADDY_SOURCE,
                "--exclude-source",
                SIMOTA_SOURCE,
            ),
            repo_root=repo_root,
        )

    if args.apply and args.run_pipeline:
        for command in POST_SYNC_PIPELINE:
            run(command, repo_root=repo_root)

    if args.apply and args.sync_codex_root:
        run(
            (
                "python",
                "scripts/sync_codex_skills.py",
                "--source-root",
                "skills",
                "--codex-root",
                str(args.sync_codex_root.expanduser()),
            ),
            repo_root=repo_root,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
