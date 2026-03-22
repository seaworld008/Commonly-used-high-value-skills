#!/usr/bin/env python3
"""Unified provenance pipeline runner.

Goal: replace patchwork command chains with one stable entrypoint.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def run(cmd: list[str], root: Path) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, cwd=root, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["all", "quick"], default="all")
    parser.add_argument("--config", default="docs/sources/provenance.config.json")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    cfg = json.loads((root / args.config).read_text(encoding="utf-8"))
    p = cfg["paths"]
    stale_days = str(cfg.get("stale_days", 30))
    coverage = str(cfg.get("coverage_min_percent", 95))

    # 1) Ensure in-house mapping is up to date.
    run(["python3", "scripts/bootstrap_in_house_sources.py", "--write-json", p["in_house_mapping"]], root)

    # 2) Validate + gate.
    run(["python3", "scripts/validate_skill_sources.py"], root)
    run(["python3", "scripts/check_source_coverage.py", "--min-percent", coverage], root)

    # 3) Reporting artifacts.
    run(["python3", "scripts/skills_refresh_planner.py", "--stale-days", stale_days, "--write-json", p["refresh_queue"]], root)
    run(["python3", "scripts/build_skills_catalog.py", "--write-json", p["catalog"]], root)
    run(["python3", "scripts/generate_sources_index.py", "--write-json", p["sources_index"]], root)

    if args.mode == "all":
        run(["python3", "scripts/skills_bulk_update_stub.py", "--queue", p["refresh_queue"], "--write-plan", p["bulk_plan"]], root)
        run(["python3", "scripts/check_upstream_github_updates.py", "--write-json", p["upstream_check"]], root)

    print("Provenance pipeline completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
