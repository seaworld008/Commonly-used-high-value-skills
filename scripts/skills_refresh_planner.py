#!/usr/bin/env python3
"""Build a prioritized refresh queue from docs/sources/*.skills.json mappings.

This script is network-agnostic: it uses local metadata (checked dates, statuses,
upstream fields) to quickly identify which curated skills likely need attention.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

ACTIVE_STATUSES = {"verified_in_repo", "verified_not_in_repo", "unverified_slug"}


@dataclass
class QueueItem:
    mapping: str
    video_name: str
    status: str
    normalized_slug: str | None
    repo_skill: str | None
    priority: int
    reasons: list[str]
    source: str


def parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def load_mappings(root: Path) -> list[Path]:
    return sorted((root / "docs/sources").glob("*.skills.json"))


def days_since(d: date | None, today: date) -> int | None:
    if d is None:
        return None
    return (today - d).days


def evaluate_item(
    mapping_name: str,
    video_checked_at: date | None,
    skill: dict[str, Any],
    today: date,
    stale_days: int,
) -> QueueItem | None:
    status = skill.get("status")
    if status not in ACTIVE_STATUSES:
        return None

    reasons: list[str] = []
    priority = 0

    upstream = skill.get("upstream") or {}
    last_checked = parse_date(upstream.get("last_checked_at"))
    last_synced = parse_date(upstream.get("last_synced_at"))

    if status == "unverified_slug":
        reasons.append("slug_unverified")
        priority += 100

    if skill.get("repo_skill") and not (Path(skill["repo_skill"]).exists()):
        reasons.append("repo_skill_missing")
        priority += 80

    if status in {"verified_in_repo", "verified_not_in_repo"}:
        if not upstream:
            reasons.append("missing_upstream_metadata")
            priority += 50

    d_last_checked = days_since(last_checked, today)
    d_video = days_since(video_checked_at, today)

    if d_last_checked is None:
        if d_video is not None and d_video > stale_days:
            reasons.append(f"stale_by_video_checked_at>{stale_days}d")
            priority += 35
    elif d_last_checked > stale_days:
        reasons.append(f"stale_last_checked>{stale_days}d")
        priority += 40

    d_last_synced = days_since(last_synced, today)
    if d_last_synced is not None and d_last_synced > stale_days * 2:
        reasons.append(f"stale_last_synced>{stale_days*2}d")
        priority += 20

    if not reasons:
        return None

    return QueueItem(
        mapping=mapping_name,
        video_name=skill.get("video_name", ""),
        status=status,
        normalized_slug=skill.get("normalized_slug"),
        repo_skill=skill.get("repo_skill"),
        priority=priority,
        reasons=reasons,
        source=skill.get("source", ""),
    )


def build_queue(root: Path, stale_days: int) -> list[QueueItem]:
    today = date.today()
    items: list[QueueItem] = []

    for mapping in load_mappings(root):
        data = json.loads(mapping.read_text(encoding="utf-8"))
        video_checked = parse_date((data.get("video") or {}).get("checked_at"))

        for skill in data.get("skills", []):
            q = evaluate_item(mapping.name, video_checked, skill, today, stale_days)
            if q:
                items.append(q)

    items.sort(key=lambda x: (-x.priority, x.mapping, x.video_name))
    return items


def print_table(items: list[QueueItem], limit: int) -> None:
    print("priority | status | video_name | mapping | reasons")
    print("---|---|---|---|---")
    for item in items[:limit]:
        print(
            f"{item.priority} | {item.status} | {item.video_name} | {item.mapping} | {', '.join(item.reasons)}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stale-days", type=int, default=30, help="Days after which source checks are considered stale")
    parser.add_argument("--limit", type=int, default=50, help="Max rows to print")
    parser.add_argument("--write-json", default=None, help="Optional output path for full refresh queue JSON")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    queue = build_queue(root, args.stale_days)

    if not queue:
        print("No refresh candidates found.")
        return 0

    print_table(queue, args.limit)

    if args.write_json:
        out = root / args.write_json
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps([asdict(x) for x in queue], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote refresh queue JSON: {out.relative_to(root)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
