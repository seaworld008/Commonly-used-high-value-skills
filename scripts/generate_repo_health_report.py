#!/usr/bin/env python3
"""Generate a unified repository health report from existing maintenance artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "docs" / "sources" / "reports"
VALID_TRACKED = {"verified_in_repo", "in_house"}


def load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def compute_source_coverage(root: Path) -> dict[str, float | int]:
    total_skills = len(list((root / "skills").glob("*/*/SKILL.md")))
    tracked: set[str] = set()
    for mapping in sorted((root / "docs" / "sources").glob("*.skills.json")):
        data = json.loads(mapping.read_text(encoding="utf-8"))
        for skill in data.get("skills", []):
            if skill.get("status") in VALID_TRACKED and skill.get("repo_skill"):
                tracked.add(skill["repo_skill"])
    covered = len(tracked)
    pct = (covered / total_skills * 100) if total_skills else 0.0
    return {"covered": covered, "total": total_skills, "percent": round(pct, 2)}


def build_payload(root: Path) -> dict:
    catalog = load_json(root / "docs" / "catalog.json") or {}
    license_audit = load_json(REPORTS_DIR / "license-audit.json") or {}
    dead_links = load_json(REPORTS_DIR / "dead-links.json") or {}
    refresh_queue = load_json(REPORTS_DIR / "refresh-queue.json") or []
    source_catalog = load_json(REPORTS_DIR / "catalog.json") or {}

    source_coverage = compute_source_coverage(root)
    skills_total = len(catalog.get("skills", [])) if isinstance(catalog, dict) else 0
    categories_total = len(catalog.get("categories", [])) if isinstance(catalog, dict) else 0
    source_conflicts = len(source_catalog.get("conflicts", [])) if isinstance(source_catalog, dict) else 0
    top_dead = []
    if isinstance(dead_links, dict):
        top_dead = dead_links.get("dead", [])[:10]

    return {
        "skills_total": skills_total,
        "categories_total": categories_total,
        "source_coverage": source_coverage,
        "license_audit": {
            "exempt": license_audit.get("exempt", 0),
            "ok": license_audit.get("ok", 0),
            "missing": license_audit.get("missing", 0),
            "unknown": license_audit.get("unknown", 0),
        },
        "dead_links": {
            "total": dead_links.get("total", 0) if isinstance(dead_links, dict) else 0,
            "dead_count": dead_links.get("dead_count", 0) if isinstance(dead_links, dict) else 0,
            "top_dead": top_dead,
        },
        "refresh_queue": {
            "count": len(refresh_queue) if isinstance(refresh_queue, list) else 0,
            "top_items": refresh_queue[:10] if isinstance(refresh_queue, list) else [],
        },
        "source_catalog": {
            "total_items_with_slug": source_catalog.get("total_items_with_slug", 0) if isinstance(source_catalog, dict) else 0,
            "unique_slugs": source_catalog.get("unique_slugs", 0) if isinstance(source_catalog, dict) else 0,
            "conflicts": source_conflicts,
        },
    }


def write_markdown(payload: dict, output: Path) -> None:
    lines = [
        "# Repo Health Report",
        "",
        "## Summary",
        "",
        f"- Skills: **{payload['skills_total']}** across **{payload['categories_total']}** categories",
        f"- Source coverage: **{payload['source_coverage']['covered']}/{payload['source_coverage']['total']} ({payload['source_coverage']['percent']}%)**",
        f"- License audit: **missing {payload['license_audit']['missing']} / unknown {payload['license_audit']['unknown']}**",
        f"- Dead links: **{payload['dead_links']['dead_count']}/{payload['dead_links']['total']}**",
        f"- Refresh queue: **{payload['refresh_queue']['count']}** pending items",
        f"- Source slug conflicts: **{payload['source_catalog']['conflicts']}**",
        "",
        "## License Audit",
        "",
        f"- Exempt (in-house): **{payload['license_audit']['exempt']}**",
        f"- OK: **{payload['license_audit']['ok']}**",
        f"- Missing: **{payload['license_audit']['missing']}**",
        f"- Unknown: **{payload['license_audit']['unknown']}**",
        "",
        "## Dead Links (Top 10)",
        "",
    ]

    if payload["dead_links"]["top_dead"]:
        lines.extend(["| URL | Status | Refs |", "|---|---:|---|"])
        for row in payload["dead_links"]["top_dead"]:
            refs = ", ".join(f"`{ref}`" for ref in row.get("refs", [])[:2])
            lines.append(f"| {row.get('url','')} | {row.get('status','')} | {refs} |")
    else:
        lines.append("- No dead-link data available.")

    lines.extend(["", "## Refresh Queue (Top 10)", ""])
    if payload["refresh_queue"]["top_items"]:
        lines.extend(["| Priority | Status | Video Name | Reasons |", "|---:|---|---|---|"])
        for row in payload["refresh_queue"]["top_items"]:
            reasons = ", ".join(row.get("reasons", []))
            lines.append(
                f"| {row.get('priority','')} | {row.get('status','')} | `{row.get('video_name','')}` | {reasons} |"
            )
    else:
        lines.append("- No refresh backlog.")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", default="docs/sources/reports/repo-health.json")
    parser.add_argument("--output-md", default="docs/sources/reports/repo-health.md")
    args = parser.parse_args()

    payload = build_payload(REPO_ROOT)
    json_path = REPO_ROOT / args.output_json
    md_path = REPO_ROOT / args.output_md
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(payload, md_path)

    print(f"Wrote {json_path.relative_to(REPO_ROOT)}")
    print(f"Wrote {md_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
