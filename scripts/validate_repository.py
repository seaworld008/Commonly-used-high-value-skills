#!/usr/bin/env python3
"""Run repository gates with the current Python interpreter, stopping on failure."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REFRESH = (
    ("scripts/enrich_frontmatter.py",),
    ("scripts/bootstrap_in_house_sources.py", "--write-json", "docs/sources/in-house.skills.json"),
    ("scripts/refresh_repo_views.py",),
    ("scripts/generate_tags_index.py",),
    ("scripts/build_catalog_json.py",),
)
CHECKS = (
    ("scripts/audit_skill_instructions.py",),
    ("scripts/lint_skill_quality.py", "--min-lines", "50", "--strict"),
    ("scripts/audit_skill_portfolio.py", "--check-policy"),
    ("scripts/audit_licenses.py",),
    ("scripts/validate_skill_sources.py",),
    ("scripts/reconcile_artifact_inventory.py", "--offline", "--check-clean", "--quiet"),
    ("scripts/check_source_coverage.py", "--min-percent", "100"),
    ("scripts/check_readme_sync.py",),
    ("scripts/check_merge_conflicts.py",),
    ("-m", "pytest", "-q", "tests"),
)


def run_pipeline(root: Path, *, refresh=False, run=subprocess.run) -> int:
    for command in (REFRESH if refresh else ()) + CHECKS:
        print("Running: python " + " ".join(command), flush=True)
        result = run([sys.executable, *command], cwd=root, check=False)
        if result.returncode:
            print(f"Stopped after failed gate (exit {result.returncode}).", file=sys.stderr)
            return result.returncode
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Regenerate derived views before checking")
    args = parser.parse_args(argv)
    return run_pipeline(Path(__file__).resolve().parents[1], refresh=args.refresh)


if __name__ == "__main__":
    raise SystemExit(main())
