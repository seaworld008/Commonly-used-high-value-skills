#!/usr/bin/env python3
"""Audit license attribution for every canonical skill.

Policy:
  - Provenance v2 ``origins[]`` is the source of truth. Every external origin
    must carry a reviewed license_checkpoint at its own resolved commit
    matching its allowed SPDX identifier.
  - Active canonical copies must also ship the reviewed upstream license bytes
    in the individual skill's install tree.
  - Provenance v1 repositories fall back to SKILL.md ``source``/``license``
    frontmatter for metadata-only review until their mappings are migrated.
  - Local-only provenance entries and in-house frontmatter fallbacks are exempt.

Exit code:
  0  all applicable metadata and distribution checks passed
  1  missing evidence or a disallowed identifier

Usage:
    python scripts/audit_licenses.py           # report + exit code
    python scripts/audit_licenses.py --json    # machine-readable report
    python scripts/audit_licenses.py --output-json docs/sources/reports/license-audit.json --output-md docs/sources/reports/license-audit.md
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
import re
from typing import Any
from pathlib import Path

try:
    from provenance_v2 import ACTIVE_STATUSES, COMMIT_RE, SHA256_RE, safe_relative_path, sha256_file
except ModuleNotFoundError:  # package imports in tests
    from scripts.provenance_v2 import ACTIVE_STATUSES, COMMIT_RE, SHA256_RE, safe_relative_path, sha256_file

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
    if repo and repo in INHOUSE_SOURCES:
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


def _checkpoint_error(origin: dict) -> str:
    tracking = origin.get("tracking")
    if not isinstance(tracking, dict) or "license_checkpoint" not in tracking:
        return "missing license_checkpoint"
    checkpoint = tracking["license_checkpoint"]
    if not isinstance(checkpoint, dict):
        return "invalid license_checkpoint"
    for field, pattern in (
        ("resolved_commit", COMMIT_RE),
        ("blob_sha", COMMIT_RE),
        ("content_sha256", SHA256_RE),
    ):
        value = checkpoint.get(field)
        if not isinstance(value, str) or not pattern.fullmatch(value):
            return f"invalid license_checkpoint.{field}"
    path = checkpoint.get("path")
    if not safe_relative_path(path) or any(ord(char) < 32 for char in path):
        return "invalid license_checkpoint.path"
    if checkpoint["resolved_commit"] != tracking.get("resolved_commit"):
        return "license_checkpoint.resolved_commit inconsistent with origin tracking"
    spdx = checkpoint.get("spdx")
    if spdx != origin["license"] or spdx not in PERMISSIVE_LICENSES:
        return "license_checkpoint.spdx inconsistent with origin license"
    if checkpoint.get("api_spdx") not in (None, "NOASSERTION", origin["license"]):
        return "license_checkpoint.api_spdx inconsistent with origin license"
    return ""


def _shipped_files(skill_dir: Path, repo_root: Path) -> dict[str, str]:
    """Index packaged regular files without following links or manifest paths."""
    files = {}
    for directory, dirs, names in os.walk(skill_dir, followlinks=False):
        dirs[:] = sorted(set(dirs) - {"__pycache__", ".data", ".git", "node_modules"})
        for name in sorted(names):
            path = Path(directory) / name
            if name != "__pycache__" and not path.is_symlink() and path.is_file():
                files[path.relative_to(repo_root).as_posix()] = sha256_file(path)
    return files


def _has_notice_body(path: Path, spdx: str) -> bool:
    """Require actual grant terms, not arbitrary nonempty checkpointed text."""
    raw = path.read_bytes()
    # This exact Vercel README was manually reviewed at b8caa260...: its
    # explicit License/MIT declaration is preserved with separate full terms.
    # A changed README needs a fresh review; arbitrary READMEs are not grants.
    if (spdx == "MIT" and hashlib.sha256(raw).hexdigest()
            == "c0a05286fc2a9d52ec2480bf070867665b9357beef37c9c2812e5b2ece571b6a"):
        return True
    text = " ".join(raw.decode("utf-8-sig", errors="replace").casefold().split())
    clauses = {
        "MIT": ("permission is hereby granted", "free of charge", "subject to the following conditions",
                "the software is provided", "without warranty"),
        "Apache-2.0": ("apache license", "version 2.0", "terms and conditions for use, reproduction, and distribution",
                       "limitations under the license"),
        "ISC": ("permission to use, copy, modify", "for any purpose", "is hereby granted",
                "copyright notice", "the software is provided"),
        "0BSD": ("permission to use, copy, modify", "for any purpose", "is hereby granted",
                 "the software is provided"),
        "BSD-2-Clause": ("redistribution and use in source and binary forms", "redistributions of source code",
                         "redistributions in binary form", "this software is provided"),
        "BSD-3-Clause": ("redistribution and use in source and binary forms", "redistributions of source code",
                         "redistributions in binary form", "neither the name", "this software is provided"),
        "MPL-2.0": ("mozilla public license", "version 2.0", "covered software", "grants"),
        "Unlicense": ("free and unencumbered software", "public domain", "anyone is free", "the software is provided"),
        "CC0-1.0": ("cc0 1.0 universal", "waiver", "public license fallback"),
        "CC-BY-4.0": ("attribution 4.0 international", "public license", "licensed rights", "attribution"),
    }.get(spdx)
    return bool(clauses and all(clause in text for clause in clauses))


def _bundled_license(
    checkpoint: dict, shipped: dict[str, str], repo_root: Path,
) -> tuple[str | None, str]:
    expected = checkpoint["content_sha256"].lower()
    for path, digest in shipped.items():
        if digest != expected:
            continue
        installed = repo_root / path
        blob_sha = checkpoint["blob_sha"].lower()
        algorithm = hashlib.sha1 if len(blob_sha) == 40 else hashlib.sha256
        with installed.open("rb") as handle:
            size = os.fstat(handle.fileno()).st_size
            blob = algorithm(f"blob {size}\0".encode("ascii"))
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                blob.update(chunk)
        if blob.hexdigest() != blob_sha:
            return None, f"{path} does not match license_checkpoint.blob_sha"
        if not _has_notice_body(installed, checkpoint["spdx"]):
            return None, f"{path} contains no upstream license body"
        return path, ""
    return None, f"no installed file matches license_checkpoint SHA-256 {expected}"


def _origin_license_row(
    origin: dict[str, Any],
    *,
    mapping: str,
    index: int,
    require_checkpoint: bool = True,
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
    elif require_checkpoint and (error := _checkpoint_error(origin)):
        status = "MISSING"
        note = f"{repo}: {error}"
    else:
        status = "OK"
        note = "" if require_checkpoint else "retired metadata only; no distributed artifacts or immutable-license claim"
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
    skill_md: Path | None,
    repo_root: Path,
) -> dict[str, Any]:
    entry = claim["entry"]
    entry_kind = str(entry.get("kind") or "")
    repo_skill = str(entry.get("repo_skill") or "")
    check_distribution = (
        bool(repo_skill)
        and entry_kind != "reference_only"
        and (skill_md is not None or entry.get("status") in ACTIVE_STATUSES)
    )
    shipped = None
    external_origins: list[dict[str, Any]] = []
    origins = entry.get("origins")
    if not isinstance(origins, list):
        origins = []
    retired_metadata_only = (
        entry.get("status") == "retired" and not repo_skill
        and not entry.get("managed_files")
        and all(isinstance(origin, dict) and not origin.get("artifacts") for origin in origins)
    )
    for index, origin in enumerate(origins):
        if not isinstance(origin, dict):
            continue
        if _origin_is_external(origin, entry_kind):
            row = _origin_license_row(origin, mapping=claim["mapping"], index=index,
                                      require_checkpoint=not retired_metadata_only)
            if check_distribution and row["status"] == "OK":
                if shipped is None:
                    shipped = _shipped_files(skill_md.parent, repo_root) if skill_md else {}
                path, error = _bundled_license(
                    origin["tracking"]["license_checkpoint"], shipped, repo_root,
                )
                if error:
                    row.update(status="MISSING", note=f"{row['repo']}: {error}")
                else:
                    row["bundled_license"] = path
            external_origins.append(row)
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


def _skill_entries(repo_root: Path) -> dict[str, Path]:
    def directories(parent: Path) -> list[Path]:
        return sorted(
            p for p in parent.iterdir()
            if not p.name.startswith(".") and not p.is_symlink() and p.is_dir()
        )

    root = repo_root / "skills"
    entries = {}
    if root.is_symlink() or not root.is_dir():
        return entries
    for category in directories(root):
        for directory in directories(category):
            path = directory / "SKILL.md"
            if not path.is_symlink() and path.is_file():
                entries[path.relative_to(repo_root).as_posix()] = path
    return entries


def _distribution_restrictions(skill_dir: Path, repo_root: Path) -> list[dict[str, str]]:
    """An in-house label cannot override explicit bundled redistribution bans."""
    restrictions = []
    for directory, dirs, names in os.walk(skill_dir, followlinks=False):
        dirs[:] = [name for name in dirs if name not in {"__pycache__", ".git", "node_modules"}
                   and not (Path(directory) / name).is_symlink()]
        for name in sorted(names):
            if not re.fullmatch(r"(?:licen[cs]e|copying|notice|copyright)(?:[.-].+)?", name, re.I):
                continue
            path = Path(directory) / name
            if path.is_symlink() or not path.is_file():
                continue
            raw = path.read_bytes()
            text = " ".join(raw.decode("utf-8-sig", errors="replace").casefold().split())
            prohibited = (
                "redistribution is prohibited" in text
                or re.search(r"users may not:.{0,2500}distribute, sublicense, or transfer", text)
            )
            if prohibited:
                restrictions.append({"path": path.relative_to(repo_root).as_posix(),
                                     "sha256": hashlib.sha256(raw).hexdigest()})
    return restrictions


def audit(
    repo_root: Path = REPO_ROOT,
    mapping_paths: list[Path] | None = None,
) -> list[dict[str, Any]]:
    provenance_entries = load_provenance_entries(repo_root, mapping_paths)
    rows: list[dict[str, Any]] = []
    skills = _skill_entries(repo_root)

    # Provenance v2 is the primary audit collection. Iterate every mapping entry
    # once, including metadata-only records for non-installed bundles.
    v2_claimed_skills: set[str] = set()
    for claim in provenance_entries:
        entry = claim["entry"]
        is_v2 = claim["schema_version"] == 2 or "origins" in entry
        if not is_v2:
            continue

        repo_skill = str(entry.get("repo_skill") or "")
        fm: dict[str, str] = {}
        skill_md = skills.get(repo_skill)
        if repo_skill:
            v2_claimed_skills.add(repo_skill)
            if skill_md is not None:
                fm = parse_frontmatter(
                    skill_md.read_text(encoding="utf-8", errors="replace")
                )
        rows.append(
            _aggregate_v2_row(
                fm=fm,
                claim=claim,
                skill_md=skill_md,
                repo_root=repo_root,
            )
        )

    # Preserve the v1/frontmatter fallback only for canonical skills that are
    # not already represented by a v2 entry.
    for rel, skill_md in skills.items():
        if rel in v2_claimed_skills:
            continue
        fm = parse_frontmatter(skill_md.read_text(encoding="utf-8", errors="replace"))
        rows.append(_frontmatter_row(skill_md=skill_md, repo_root=repo_root, fm=fm))
    for row in rows:
        skill_md = skills.get(row.get("path"))
        if skill_md is None:
            continue
        restrictions = _distribution_restrictions(skill_md.parent, repo_root)
        if restrictions:
            row["status"] = "UNKNOWN"
            row["distribution_restrictions"] = restrictions
            reason = "Bundled third-party terms prohibit redistribution; source/in-house labels do not grant permission: "
            row["note"] = "; ".join(filter(None, [row["note"], reason + ", ".join(r["path"] for r in restrictions)]))
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
        f"- v1 frontmatter fallbacks (metadata only): **{payload['v1_fallback_skills']}**",
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
        print(f"  v1 fallbacks (metadata only): {payload['v1_fallback_skills']}")
        print(f"  EXEMPT (in-house): {payload['exempt']}")
        print(f"  OK:                {payload['ok']}")
        print(f"  MISSING:           {len(missing)}")
        print(f"  DISALLOWED SPDX:   {len(unknown)}")
        for r in missing:
            print(f"    MISSING  {r['skill']} ({r['source']}): {r['note']}")
        for r in unknown:
            print(f"    DISALLOWED  {r['skill']} ({r['source']}): {r['license']}")

    fail = bool(missing) or bool(unknown)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
