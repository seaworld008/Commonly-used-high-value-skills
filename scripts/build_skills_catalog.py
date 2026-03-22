#!/usr/bin/env python3
"""Build a consolidated catalog from docs/sources/*.skills.json.

Detects conflicting canonical mappings and emits a normalized report for automation.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class CatalogItem:
    slug: str
    status: str
    repo_skill: str | None
    source_mapping: str
    source_url: str
    video_name: str


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", default="docs/sources/reports/catalog.json")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    mappings = sorted((root / "docs/sources").glob("*.skills.json"))
    if not mappings:
        print("No mapping files found under docs/sources/*.skills.json")
        return 1

    items: list[CatalogItem] = []
    conflicts: list[str] = []
    by_slug: dict[str, CatalogItem] = {}

    for mapping in mappings:
        data = json.loads(mapping.read_text(encoding="utf-8"))
        for s in data.get("skills", []):
            slug = s.get("normalized_slug")
            if not slug:
                continue
            item = CatalogItem(
                slug=slug,
                status=s.get("status", ""),
                repo_skill=s.get("repo_skill"),
                source_mapping=mapping.name,
                source_url=s.get("source", ""),
                video_name=s.get("video_name", ""),
            )
            if slug in by_slug:
                prev = by_slug[slug]
                if prev.repo_skill != item.repo_skill:
                    conflicts.append(
                        f"slug={slug} has conflicting repo_skill: {prev.repo_skill} ({prev.source_mapping}) vs {item.repo_skill} ({item.source_mapping})"
                    )
            else:
                by_slug[slug] = item
            items.append(item)

    out = root / args.write_json
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "total_mappings": len(mappings),
        "total_items_with_slug": len(items),
        "unique_slugs": len(by_slug),
        "conflicts": conflicts,
        "catalog": [asdict(by_slug[k]) for k in sorted(by_slug.keys())],
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote catalog: {out.relative_to(root)}")
    print(f"Unique slugs: {len(by_slug)}")
    if conflicts:
        print("Conflicts detected:")
        for c in conflicts:
            print(f"- {c}")
        return 1

    print("No slug conflicts detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
