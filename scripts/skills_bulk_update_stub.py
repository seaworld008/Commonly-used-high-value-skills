#!/usr/bin/env python3
"""Generate a batch update execution plan from refresh queue.

Safe by default (dry-run only): outputs actionable steps without mutating source files.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path


def recommendation_for(item: dict) -> list[str]:
    reasons = set(item.get("reasons", []))
    recs: list[str] = []

    if "slug_unverified" in reasons:
        recs.append("Verify official slug via registry/docs; keep normalized_slug=null until confirmed.")
        recs.append("Record attempt under verification_attempts with date/method/result.")

    if "repo_skill_missing" in reasons:
        recs.append("Either fix repo_skill path or downgrade status to verified_not_in_repo/unverified_slug.")

    if any(r.startswith("stale_last_checked") or r.startswith("stale_by_video_checked_at") for r in reasons):
        recs.append("Re-check upstream source and update upstream.last_checked_at.")

    if any(r.startswith("stale_last_synced") for r in reasons):
        recs.append("Compare upstream version and update local skill if changed; then set upstream.last_synced_at.")

    if "missing_upstream_metadata" in reasons:
        recs.append("Add upstream metadata: repo/path/ref/last_checked_at/last_synced_at.")

    if not recs:
        recs.append("Manual review needed.")
    return recs


def build_plan(queue: list[dict], limit: int) -> str:
    lines: list[str] = []
    lines.append(f"# Skills Bulk Update Plan ({date.today().isoformat()})")
    lines.append("")
    lines.append(f"Generated from refresh queue entries: {len(queue)}")
    lines.append("")

    for i, item in enumerate(queue[:limit], 1):
        lines.append(f"## {i}. {item.get('video_name', 'Unknown')} ({item.get('status', '-')})")
        lines.append(f"- Mapping: `{item.get('mapping', '-')}`")
        lines.append(f"- Slug: `{item.get('normalized_slug')}`")
        lines.append(f"- Repo skill: `{item.get('repo_skill')}`")
        lines.append(f"- Priority: `{item.get('priority')}`")
        lines.append(f"- Reasons: `{', '.join(item.get('reasons', []))}`")
        lines.append("- Recommended actions:")
        for rec in recommendation_for(item):
            lines.append(f"  - {rec}")
        lines.append("")

    lines.append("## Standard validation commands")
    lines.append("```bash")
    lines.append("python3 scripts/validate_openclaw_video_sources.py")
    lines.append("python3 scripts/skills_refresh_planner.py --stale-days 30 --write-json docs/sources/reports/refresh-queue.json")
    lines.append("python3 scripts/build_skills_catalog.py --write-json docs/sources/reports/catalog.json")
    lines.append("```")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default="docs/sources/reports/refresh-queue.json")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--write-plan", default="docs/sources/reports/bulk-update-plan.md")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    queue_path = root / args.queue
    if not queue_path.exists():
        print(f"Queue file not found: {args.queue}")
        return 1

    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    if not isinstance(queue, list):
        print("Queue file must be a JSON array")
        return 1

    plan = build_plan(queue, args.limit)
    out = root / args.write_plan
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(plan, encoding="utf-8")
    print(f"Wrote bulk update plan: {out.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
