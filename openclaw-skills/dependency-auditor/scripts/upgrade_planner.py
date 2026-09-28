#!/usr/bin/env python3
"""Compatibility entry point for the retired simulated upgrade planner.

No registry or advisory service is queried. The previous hard-coded "latest"
versions and fabricated migration estimates have been removed. Use maintained
package-manager reports and verified release notes to build an upgrade plan.

License: MIT
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


class UpgradePlanner:
    """Report missing evidence instead of inventing available updates."""

    def analyze_upgrades(self, dependency_inventory: str, timeline_days: int = 90) -> dict:
        data = json.loads(Path(dependency_inventory).read_text(encoding="utf-8"))
        dependencies = data.get("dependencies") if isinstance(data, dict) else data
        if not isinstance(dependencies, list) or not all(isinstance(d, dict) for d in dependencies):
            raise ValueError("Inventory must be a dependency list or an object with a dependencies list")
        if timeline_days < 1:
            raise ValueError("timeline must be a positive number of days")
        return {
            "status": "retired_simulation",
            "version_status": "not_assessed",
            "vulnerability_status": "not_assessed",
            "dependencies_analyzed": len(dependencies),
            "timeline_days": timeline_days,
            "available_upgrades": [],
            "upgrade_statistics": {},
            "risk_assessment": {"overall_risk": "not_assessed"},
            "upgrade_plans": [],
            "recommendations": [
                "Generate a current package-manager outdated report using the configured registry.",
                "Verify exact affected and fixed versions against a maintained advisory source.",
                "Review release notes, runtime requirements, tests, and rollback before choosing a target.",
                "An empty available_upgrades list here means NOT ASSESSED, not up to date.",
            ],
        }

    def generate_report(self, analysis_results: dict, format: str = "text") -> str:
        if format == "json":
            return json.dumps(analysis_results, indent=2, ensure_ascii=False)
        return "UPGRADE ASSESSMENT: NOT ASSESSED\nThe simulated version catalog has been retired.\n" + "\n".join(analysis_results["recommendations"])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory_file")
    parser.add_argument("--timeline", type=int, default=90)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--output", "-o")
    # Accept historical options so automation receives an explicit migration
    # result rather than a misleading successful plan or an unknown flag error.
    parser.add_argument("--risk-threshold", choices=["safe", "low", "medium", "high", "critical"], default="high")
    parser.add_argument("--security-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        planner = UpgradePlanner()
        report = planner.generate_report(planner.analyze_upgrades(args.inventory_file, args.timeline), args.format)
        if args.output:
            Path(args.output).write_text(report + "\n", encoding="utf-8")
        else:
            print(report)
        return 2  # Never satisfy an upgrade/security gate without evidence.
    except (OSError, ValueError, TypeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
