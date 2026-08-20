#!/usr/bin/env python3
"""Audit license attribution for every canonical skill.

Policy:
  - Provenance v2 ``origins[]`` is the source of truth. Every external origin
    MUST declare an allowed SPDX license identifier on the origin itself.
  - Provenance v1 repositories fall back to SKILL.md ``source``/``license``
    frontmatter until their mappings are migrated.
  - Skills with `source: in-house` are exempt (licensed under the repo's own
    LICENSE file).

Exit code:
  0  every external origin carries an allowed SPDX license
  1  one or more external origins are missing or use a disallowed identifier

Usage:
    python scripts/audit_licenses.py           # report + exit code
    python scripts/audit_licenses.py --json    # machine-readable report
    python scripts/audit_licenses.py --output-json docs/sources/reports/license-audit.json --output-md docs/sources/reports/license-audit.md
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import re
from typing import Any
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

INHOUSE_SOURCES = {"in-house", "", "local-repo/in-house"}
# Repository policy allowlist. Values are canonical SPDX identifiers.
PERMISSIVE_LICENSES = {
    "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause",
    "ISC", "CC-BY-4.0", "CC0-1.0", "Unlicense", "0BSD", "MPL-2.0",
}
LOCAL_REPOS = {
    "local-repo/in-house",
    "seaworld008/commonly-used-high-value-skills",
    "your-org/commonly-used-high-value-skills",
}


def parse_frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm: dict[str, str] = {}
    current = None
    for line in m.group(1).splitlines():
        if line and (line[0] == " " or line[0] == "\t"):
            continue  # skip nested blocks
        if ":" in line:
            k, v = line.split(":", 1)
            current = k.strip()
            fm[current] = v.strip().strip('"').strip("'")
    return fm


def discover_mapping_paths(repo_root: Path) -> list[Path]:
    sources_dir = repo_root / "docs" / "sources"
    paths = set(sources_dir.glob("*.skills.json"))
    paths.update(sources_dir.glob("*.bundle.json"))
    return sorted(paths)


def load_provenance_claims(
    repo_root: Path,
    mapping_paths: list[Path] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Index v1 and v2 provenance entries by canonical ``repo_skill`` path."""
    claims: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in load_provenance_entries(repo_root, mapping_paths):
        item = record["entry"]
        if not item.get("repo_skill"):
            continue
        claims[str(item["repo_skill"])].append(record)
    return claims


def load_provenance_entries(
    repo_root: Path,
    mapping_paths: list[Path] | None = None,
) -> list[dict[str, Any]]:
    """Load every provenance entry exactly once, including noncanonical bundles.

    License policy is attached to upstream artifacts, not only to canonical
    ``SKILL.md`` files.  Keeping a flat entry inventory ensures a bundle,
    snapshot, or reference-only record without ``repo_skill`` cannot disappear
    from the audit.
    """
    resolved_root = repo_root.resolve()
    selected_paths = (
        discover_mapping_paths(repo_root)
        if mapping_paths is None
        else mapping_paths
    )
    records: list[dict[str, Any]] = []
    seen_mappings: set[Path] = set()
    for candidate in selected_paths:
        mapping = candidate.resolve()
        if mapping in seen_mappings:
            continue
        seen_mappings.add(mapping)
        data = json.loads(mapping.read_text(encoding="utf-8"))
        schema_version = data.get("schema_version", 1)
        for entry_index, item in enumerate(data.get("skills", [])):
            if not isinstance(item, dict):
                continue
            records.append(
                {
                    "mapping": mapping.relative_to(resolved_root).as_posix(),
                    "schema_version": schema_version,
                    "entry_index": entry_index,
                    "entry": item,
                }
            )
    return records


def _origin_is_external(origin: dict[str, Any], entry_kind: str) -> bool:
    explicit = origin.get("external")
    if explicit is True:
        return True

    repo = str(origin.get("repo") or origin.get("source") or "").strip()
    normalized_repo = repo.removeprefix("https://github.com/").removeprefix(
        "http://github.com/"
    ).strip("/").lower()
    origin_kind = str(origin.get("kind") or "").strip().lower().replace("-", "_")

    if normalized_repo in LOCAL_REPOS or normalized_repo.startswith("local-repo/"):
        return False
    if repo in INHOUSE_SOURCES:
        return False

    remote_locator = any(
        origin.get(key)
        for key in ("repo", "url", "source", "source_url", "ref", "tracking")
    )
    if origin_kind in {"in_house", "local", "local_repo"} and not remote_locator:
        return False
    if entry_kind == "in_house" and not remote_locator:
        return False
    # An unclassified v2 origin is treated as external. This is intentionally
    # conservative: missing provenance must not create a license exemption.
    return True


def _origin_license_row(
    origin: dict[str, Any],
    *,
    mapping: str,
    index: int,
) -> dict[str, Any]:
    license_tag = str(origin.get("license") or "").strip()
    repo = str(origin.get("repo") or origin.get("source") or "")
    path = str(origin.get("path") or "")
    if not license_tag:
        status = "MISSING"
        note = f"external origin {repo or '<unknown>'!r} lacks an SPDX license"
    elif license_tag not in PERMISSIVE_LICENSES:
        status = "UNKNOWN"
        note = f"license {license_tag!r} is not in the allowed SPDX set"
    else:
        status = "OK"
        note = ""
    return {
        "mapping": mapping,
        "origin_index": index,
        "repo": repo,
        "path": path,
        "source_url": str(origin.get("url") or origin.get("source_url") or ""),
        "license": license_tag,
        "status": status,
        "note": note,
    }


def _aggregate_v2_row(
    *,
    fm: dict[str, str],
    claim: dict[str, Any],
) -> dict[str, Any]:
    entry = claim["entry"]
    entry_kind = str(entry.get("kind") or "")
    repo_skill = str(entry.get("repo_skill") or "")
    external_origins: list[dict[str, Any]] = []
    origins = entry.get("origins")
    if not isinstance(origins, list):
        origins = []
    for index, origin in enumerate(origins):
        if not isinstance(origin, dict):
            continue
        if _origin_is_external(origin, entry_kind):
            external_origins.append(
                _origin_license_row(
                    origin,
                    mapping=claim["mapping"],
                    index=index,
                )
            )
    # Mirror-like entries represent copied artifacts and must identify an
    # auditable external origin. A composite is local orchestration over
    # separately claimed dependencies, while a reference-only entry may merely
    # record a rejected/unavailable candidate; either is exempt when it has no
    # external origin. Any external origin that is present is still audited.
    if (
        entry_kind in {"mirror", "overlay", "bundle", "snapshot"}
        and not external_origins
    ):
        external_origins.append(
            {
                "mapping": claim["mapping"],
                "origin_index": None,
                "repo": "",
                "path": "",
                "source_url": "",
                "license": "",
                "status": "MISSING",
                "note": (
                    f"provenance v2 {entry_kind or '<missing kind>'!r} entry "
                    "has no auditable external origin"
                ),
            }
        )

    status = "EXEMPT"
    note = ""
    if external_origins:
        if any(origin["status"] == "MISSING" for origin in external_origins):
            status = "MISSING"
        elif any(origin["status"] == "UNKNOWN" for origin in external_origins):
            status = "UNKNOWN"
        else:
            status = "OK"
        note = "; ".join(
            origin["note"] for origin in external_origins if origin["note"]
        )

    display_name = (
        entry.get("normalized_slug")
        or entry.get("video_name")
        or entry.get("name")
        or (Path(repo_skill).parent.name if repo_skill else "")
        or f"{Path(claim['mapping']).stem}#{claim['entry_index']}"
    )
    audit_path = repo_skill or f"{claim['mapping']}#skills[{claim['entry_index']}]"
    return {
        "skill": str(display_name),
        "path": audit_path,
        "source": ", ".join(
            dict.fromkeys(origin["repo"] for origin in external_origins if origin["repo"])
        )
        or "provenance:v2-local",
        "source_url": next(
            (origin["source_url"] for origin in external_origins if origin["source_url"]),
            "",
        ),
        "license": ", ".join(
            dict.fromkeys(
                origin["license"] for origin in external_origins if origin["license"]
            )
        ),
        "status": status,
        "note": note,
        "evidence": "provenance_v2_origins",
        "origins": external_origins,
        "frontmatter_source": fm.get("source", ""),
        "frontmatter_license": fm.get("license", ""),
        "mapping": claim["mapping"],
        "entry_index": claim["entry_index"],
        "kind": entry_kind,
        "canonical": bool(repo_skill),
        "tracked_origin_count": sum(
            1 for origin in origins if isinstance(origin, dict)
        ),
        "external_origin_count": len(
            [
                origin
                for origin in origins
                if isinstance(origin, dict)
                and _origin_is_external(origin, entry_kind)
            ]
        ),
    }


def _frontmatter_row(
    *,
    skill_md: Path,
    repo_root: Path,
    fm: dict[str, str],
) -> dict[str, Any]:
    source = fm.get("source", "in-house")
    license_tag = fm.get("license", "")
    status = "OK"
    note = ""
    if source in INHOUSE_SOURCES:
        status = "EXEMPT"
    elif not license_tag:
        status = "MISSING"
        note = f"external source {source!r} lacks an SPDX license"
    elif license_tag not in PERMISSIVE_LICENSES:
        status = "UNKNOWN"
        note = f"license {license_tag!r} is not in the allowed SPDX set"
    return {
        "skill": skill_md.parent.name,
        "path": skill_md.relative_to(repo_root).as_posix(),
        "source": source,
        "source_url": fm.get("source_url", ""),
        "license": license_tag,
        "status": status,
        "note": note,
        "evidence": "frontmatter_v1_fallback",
        "origins": [],
        "frontmatter_source": source,
        "frontmatter_license": license_tag,
    }


def audit(
    repo_root: Path = REPO_ROOT,
    mapping_paths: list[Path] | None = None,
) -> list[dict[str, Any]]:
    provenance_entries = load_provenance_entries(repo_root, mapping_paths)
    rows: list[dict[str, Any]] = []

    # Provenance v2 is the primary audit collection. Iterate every mapping entry
    # once so noncanonical bundles and snapshots receive exactly the same
    # license gate as canonical skills.
    v2_claimed_skills: set[str] = set()
    for claim in provenance_entries:
        entry = claim["entry"]
        is_v2 = claim["schema_version"] == 2 or "origins" in entry
        if not is_v2:
            continue

        repo_skill = str(entry.get("repo_skill") or "")
        fm: dict[str, str] = {}
        if repo_skill:
            v2_claimed_skills.add(repo_skill)
            skill_md = repo_root / repo_skill
            if skill_md.is_file():
                fm = parse_frontmatter(
                    skill_md.read_text(encoding="utf-8", errors="replace")
                )
        rows.append(
            _aggregate_v2_row(
                fm=fm,
                claim=claim,
            )
        )

    # Preserve the v1/frontmatter fallback only for canonical skills that are
    # not already represented by a v2 entry.
    for skill_md in sorted((repo_root / "skills").glob("*/*/SKILL.md")):
        fm = parse_frontmatter(skill_md.read_text(encoding="utf-8", errors="replace"))
        rel = skill_md.relative_to(repo_root).as_posix()
        if rel in v2_claimed_skills:
            continue
        rows.append(_frontmatter_row(skill_md=skill_md, repo_root=repo_root, fm=fm))
    return rows


def summarize(rows: list[dict]) -> dict:
    missing = [r for r in rows if r["status"] == "MISSING"]
    unknown = [r for r in rows if r["status"] == "UNKNOWN"]
    exempt = [r for r in rows if r["status"] == "EXEMPT"]
    ok = [r for r in rows if r["status"] == "OK"]
    return {
        "total": len(rows),
        "v2_entries": sum(
            1 for row in rows if row.get("evidence") == "provenance_v2_origins"
        ),
        "noncanonical_v2_entries": sum(
            1
            for row in rows
            if row.get("evidence") == "provenance_v2_origins"
            and not row.get("canonical")
        ),
        "v1_fallback_skills": sum(
            1 for row in rows if row.get("evidence") == "frontmatter_v1_fallback"
        ),
        "tracked_origins": sum(
            int(row.get("tracked_origin_count", 0)) for row in rows
        ),
        "external_origins": sum(
            int(row.get("external_origin_count", 0)) for row in rows
        ),
        "exempt": len(exempt),
        "ok": len(ok),
        "missing": len(missing),
        "unknown": len(unknown),
        "rows": rows,
    }


def write_json_report(
    payload: dict,
    output_path: str,
    repo_root: Path = REPO_ROOT,
) -> None:
    out = repo_root / output_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_markdown_report(
    payload: dict,
    output_path: str,
    repo_root: Path = REPO_ROOT,
) -> None:
    out = repo_root / output_path
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# License Audit Report",
        "",
        f"- Total skills / provenance entries: **{payload['total']}**",
        f"- Provenance v2 entries: **{payload['v2_entries']}**",
        f"- Noncanonical v2 entries: **{payload['noncanonical_v2_entries']}**",
        f"- Tracked origins: **{payload['tracked_origins']}**",
        f"- External origins: **{payload['external_origins']}**",
        f"- v1 frontmatter fallbacks: **{payload['v1_fallback_skills']}**",
        f"- Exempt (in-house): **{payload['exempt']}**",
        f"- OK: **{payload['ok']}**",
        f"- Missing: **{payload['missing']}**",
        f"- Disallowed SPDX: **{payload['unknown']}**",
        "",
    ]

    for section in ("MISSING", "UNKNOWN"):
        rows = [r for r in payload["rows"] if r["status"] == section]
        if not rows:
            continue
        lines.extend([f"## {section.title()}", "", "| Skill | Source | License | Path | Source URL | Note |", "|---|---|---|---|---|---|"])
        for row in rows:
            source_url = row["source_url"] or ""
            lines.append(
                f"| `{row['skill']}` | `{row['source']}` | `{row['license']}` | `{row['path']}` | {source_url} | {row['note']} |"
            )
        lines.append("")

    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root to audit (primarily for isolated tests).",
    )
    parser.add_argument(
        "--mapping",
        action="append",
        default=None,
        help="Repo-relative provenance mapping to audit (repeatable).",
    )
    parser.add_argument("--output-json", help="Write full machine-readable audit report to a repo-relative path.")
    parser.add_argument("--output-md", help="Write markdown audit report to a repo-relative path.")
    parser.add_argument("--strict", action="store_true",
                        help="Deprecated compatibility flag; disallowed SPDX identifiers always fail.")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    mapping_paths = (
        [repo_root / path for path in args.mapping] if args.mapping is not None else None
    )
    rows = audit(repo_root=repo_root, mapping_paths=mapping_paths)
    payload = summarize(rows)
    missing = [r for r in rows if r["status"] == "MISSING"]
    unknown = [r for r in rows if r["status"] == "UNKNOWN"]

    if args.output_json:
        write_json_report(payload, args.output_json, repo_root)
    if args.output_md:
        write_markdown_report(payload, args.output_md, repo_root)

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"License audit: {len(rows)} skills / provenance entries")
        print(f"  Provenance v2 entries: {payload['v2_entries']}")
        print(f"  Noncanonical entries:  {payload['noncanonical_v2_entries']}")
        print(f"  Tracked origins:       {payload['tracked_origins']}")
        print(f"  External origins:      {payload['external_origins']}")
        print(f"  v1 fallbacks:          {payload['v1_fallback_skills']}")
        print(f"  EXEMPT (in-house): {payload['exempt']}")
        print(f"  OK:                {payload['ok']}")
        print(f"  MISSING:           {len(missing)}")
        print(f"  DISALLOWED SPDX:   {len(unknown)}")
        for r in missing:
            print(f"    MISSING  {r['skill']} ({r['source']})")
        for r in unknown:
            print(f"    DISALLOWED  {r['skill']} ({r['source']}): {r['license']}")

    fail = bool(missing) or bool(unknown)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
