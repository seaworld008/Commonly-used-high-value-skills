#!/usr/bin/env python3
"""Evaluate repo health against configured thresholds."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(payload: dict, thresholds: dict) -> tuple[list[dict], bool]:
    checks = [
        {
            "name": "source_coverage",
            "actual": payload["source_coverage"]["percent"],
            "target": thresholds["source_coverage_min_percent"],
            "operator": ">=",
            "ok": payload["source_coverage"]["percent"] >= thresholds["source_coverage_min_percent"],
        },
        {
            "name": "license_missing",
            "actual": payload["license_audit"]["missing"],
            "target": thresholds["license_missing_max"],
            "operator": "<=",
            "ok": payload["license_audit"]["missing"] <= thresholds["license_missing_max"],
        },
        {
            "name": "license_unknown",
            "actual": payload["license_audit"]["unknown"],
            "target": thresholds["license_unknown_max"],
            "operator": "<=",
            "ok": payload["license_audit"]["unknown"] <= thresholds["license_unknown_max"],
        },
        {
            "name": "dead_links",
            "actual": payload["dead_links"]["dead_count"],
            "target": thresholds["dead_links_max"],
            "operator": "<=",
            "ok": payload["dead_links"]["dead_count"] <= thresholds["dead_links_max"],
        },
        {
            "name": "refresh_queue",
            "actual": payload["refresh_queue"]["count"],
            "target": thresholds["refresh_queue_max"],
            "operator": "<=",
            "ok": payload["refresh_queue"]["count"] <= thresholds["refresh_queue_max"],
        },
        {
            "name": "source_conflicts",
            "actual": payload["source_catalog"]["conflicts"],
            "target": thresholds["source_conflicts_max"],
            "operator": "<=",
            "ok": payload["source_catalog"]["conflicts"] <= thresholds["source_conflicts_max"],
        },
    ]
    passed = all(check["ok"] for check in checks)
    return checks, passed


def write_markdown(checks: list[dict], passed: bool, output: Path) -> None:
    lines = [
        "# Repo Health Evaluation",
        "",
        f"- Overall status: **{'PASS' if passed else 'FAIL'}**",
        "",
        "| Check | Actual | Target | Rule | Status |",
        "|---|---:|---:|---|---|",
    ]
    for check in checks:
        status = "PASS" if check["ok"] else "FAIL"
        lines.append(
            f"| `{check['name']}` | {check['actual']} | {check['target']} | {check['operator']} | **{status}** |"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="docs/sources/reports/repo-health.json")
    parser.add_argument("--config", default="docs/sources/provenance.config.json")
    parser.add_argument("--output-md", default="docs/sources/reports/repo-health-eval.md")
    args = parser.parse_args()

    report = load_json(REPO_ROOT / args.report)
    config = load_json(REPO_ROOT / args.config)
    thresholds = config.get("health_thresholds", {})
    checks, passed = evaluate(report, thresholds)
    write_markdown(checks, passed, REPO_ROOT / args.output_md)
    print(f"Wrote {(REPO_ROOT / args.output_md).relative_to(REPO_ROOT)}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
