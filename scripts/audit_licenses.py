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
import stat
import struct
import zlib
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
# Aggregated, unmodified font binaries only; never a software-license allowlist.
SCOPED_FONT_LICENSES = {"OFL-1.1"}
FONT_SUFFIXES = {".ttf", ".otf", ".woff", ".woff2"}
# Full standard OFL 1.1 text, from its dated heading through the disclaimer,
# case/whitespace normalized and with decorative horizontal rules removed.
# A hash of the entire body prevents truncated or edited conditions passing.
OFL_BODY_SHA256 = "f1d9649b3448d9da3dc507a47f809592dccd1cae2d99e639fe42244f26395276"
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
    if spdx != origin["license"] or spdx not in PERMISSIVE_LICENSES | SCOPED_FONT_LICENSES:
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
    if spdx == "OFL-1.1":
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            return False
        normalized = " ".join(re.sub(r"-{3,}", "", text.casefold()).split())
        heading = "sil open font license version 1.1 - 26 february 2007"
        prefix, found, body = normalized.partition(heading)
        # Only attribution/RFN lines and the standard license introduction
        # may precede the full terms. A script prepended to an OFL file is not
        # an additional license/notice artifact.
        prefix_lines = text.casefold().split("sil open font license version", 1)[0].splitlines()
        allowed_prefixes = (
            "copyright", "with reserved font name", "reserved font name",
            "this font software is licensed under the sil open font license, version 1.1.",
            "this license is copied below, and is also available with a faq at:",
            "https://openfontlicense.org", "http://scripts.sil.org/ofl",
            "https://scripts.sil.org/ofl",
        )
        if any(line.strip() and set(line.strip()) != {"-"}
               and not line.strip().startswith(allowed_prefixes) for line in prefix_lines):
            return False
        return bool(
            found and re.search(r"\bcopyright\b.*\d{4}[,\s]+\S", prefix)
            and hashlib.sha256((heading + body).encode()).hexdigest() == OFL_BODY_SHA256
        )
    # Complete Apache clauses 1-9 without the optional how-to appendix.
    # Reviewed against the full Apache template, with no legal term omitted.
    # Exact normalized text only; changed grants and appended conditions fail.
    if spdx == "Apache-2.0":
        normalized = " ".join(raw.decode("utf-8-sig", errors="replace").lower().split())
        if hashlib.sha256(normalized.encode()).hexdigest() == "95cef6332b35354c12f9d666ab9ff47002e6f7ef937924896882b2e0cdb7a0d6":
            return True
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


def _font_structure_error(raw: bytes, suffix: str) -> str:
    """Bounded container/table checks, not a complete font decoder or RFN review."""
    if len(raw) > 64 * 1024 * 1024:
        return "font exceeds the 64 MiB inspection limit"
    tables: dict[bytes, bytes] = {}
    try:
        if suffix in {".ttf", ".otf"}:
            flavor, count, search, selector, shift = struct.unpack_from(">4s4H", raw)
            if flavor != (b"OTTO" if suffix == ".otf" else b"\0\1\0\0"):
                return "font magic does not match extension"
            if not 1 <= count <= 4095:
                return "invalid sfnt table count"
            power = 1 << (count.bit_length() - 1)
            if (search, selector, shift) != (16 * power, power.bit_length() - 1, 16 * (count - power)):
                return "invalid sfnt search parameters"
            end = 12 + 16 * count
            ranges = []
            for i in range(count):
                tag, _, offset, size = struct.unpack_from(">4sIII", raw, 12 + i * 16)
                if tag in tables or offset % 4 or offset < end or not size or offset + size > len(raw):
                    return "invalid sfnt table bounds or duplicate tag"
                tables[tag] = raw[offset:offset + size]
                ranges.append((offset, offset + size))
        elif suffix == ".woff":
            magic, flavor, length, count, reserved, sfnt_size = struct.unpack_from(">4s4sIHHI", raw)
            if magic != b"wOFF" or flavor not in {b"OTTO", b"\0\1\0\0"}:
                return "invalid WOFF magic or flavor"
            if length != len(raw) or reserved or not 1 <= count <= 4095 or len(raw) < 44:
                return "invalid WOFF header"
            end, ranges, original_size = 44 + 20 * count, [], 12 + 16 * count
            meta, meta_size, meta_original, private, private_size = struct.unpack_from(">5I", raw, 24)
            if (bool(meta) != bool(meta_size) or bool(meta) != bool(meta_original)
                    or bool(private) != bool(private_size)):
                return "invalid WOFF metadata/private header"
            for offset, size in ((meta, meta_size), (private, private_size)):
                if offset:
                    if offset % 4 or offset < end or offset + size > len(raw):
                        return "invalid WOFF metadata/private bounds"
                    ranges.append((offset, offset + size))
            for i in range(count):
                tag, offset, compressed, size, _ = struct.unpack_from(">4sIIII", raw, 44 + i * 20)
                if (tag in tables or offset % 4 or offset < end or not 0 < compressed <= size
                        or size > 64 * 1024 * 1024 or offset + compressed > len(raw)):
                    return "invalid WOFF table bounds or duplicate tag"
                data = raw[offset:offset + compressed]
                if compressed < size:
                    decoder = zlib.decompressobj()
                    data = decoder.decompress(data, size + 1)
                    if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                        return "invalid WOFF compressed table"
                if len(data) != size:
                    return "invalid WOFF table length"
                tables[tag] = data
                ranges.append((offset, offset + compressed))
                original_size += (size + 3) & ~3
                if original_size > 64 * 1024 * 1024:
                    return "WOFF expands beyond inspection limit"
            if sfnt_size != original_size:
                return "invalid WOFF totalSfntSize"
        elif suffix == ".woff2":
            # WOFF2 needs Brotli and transformed-table decoding. Fail closed
            # rather than bless an opaque block with a plausible header.
            return "WOFF2 structure decoding is unavailable; use reviewed sfnt/WOFF bytes"
        else:
            return "unsupported font extension"
        ranges.sort()
        if any(left[1] > right[0] for left, right in zip(ranges, ranges[1:])):
            return "overlapping font tables"
        if not {b"head", b"maxp", b"name", b"cmap"} <= tables.keys():
            return "font lacks required tables"
        if flavor == b"OTTO":
            if not ({b"CFF ", b"CFF2"} & tables.keys()):
                return "OpenType font lacks outlines"
        elif not {b"glyf", b"loca"} <= tables.keys():
            return "TrueType font lacks outlines"
        head, maxp, name, cmap = (tables[tag] for tag in (b"head", b"maxp", b"name", b"cmap"))
        if (len(head) < 54 or head[12:16] != b"_\x0f<\xf5"
                or not 16 <= struct.unpack_from(">H", head, 18)[0] <= 16384
                or len(maxp) < 6 or not struct.unpack_from(">H", maxp, 4)[0]):
            return "invalid font head/maxp tables"
        glyphs = struct.unpack_from(">H", maxp, 4)[0]
        if maxp[:4] not in {b"\0\0P\0", b"\0\1\0\0"} or (maxp[:4] == b"\0\1\0\0" and len(maxp) < 32):
            return "invalid maxp version or length"
        if flavor != b"OTTO":
            loca_format = struct.unpack_from(">h", head, 50)[0]
            if loca_format not in {0, 1}:
                return "invalid glyph location format"
            width = 2 if loca_format == 0 else 4
            loca = tables[b"loca"]
            if len(loca) < (glyphs + 1) * width:
                return "truncated glyph location table"
            offsets = [struct.unpack_from(">H" if width == 2 else ">I", loca, i * width)[0]
                       * (2 if width == 2 else 1) for i in range(glyphs + 1)]
            if offsets != sorted(offsets) or offsets[-1] > len(tables[b"glyf"]):
                return "invalid glyph location bounds"
        version, records, strings = struct.unpack_from(">3H", name)
        if version not in {0, 1} or not records or strings < 6 + 12 * records or strings > len(name):
            return "invalid font name table"
        for i in range(records):
            size, offset = struct.unpack_from(">HH", name, 6 + i * 12 + 8)
            if not size or strings + offset + size > len(name):
                return "invalid font name string bounds"
        version, records = struct.unpack_from(">HH", cmap)
        if version or not records or 4 + 8 * records > len(cmap):
            return "invalid font cmap table"
        for i in range(records):
            offset = struct.unpack_from(">I", cmap, 4 + i * 8 + 4)[0]
            if offset < 4 + 8 * records or offset + 4 > len(cmap):
                return "invalid font cmap subtable bounds"
            fmt = struct.unpack_from(">H", cmap, offset)[0]
            if fmt in {0, 2, 4, 6}:
                size = struct.unpack_from(">H", cmap, offset + 2)[0]
                minimum = {0: 262, 2: 518, 4: 24, 6: 10}[fmt]
            elif fmt in {8, 10, 12, 13}:
                size = struct.unpack_from(">I", cmap, offset + 4)[0]
                minimum = {8: 8208, 10: 20, 12: 16, 13: 16}[fmt]
            elif fmt == 14:
                size = struct.unpack_from(">I", cmap, offset + 2)[0]
                minimum = 10
            else:
                return "unsupported cmap subtable format"
            if size < minimum or offset + size > len(cmap):
                return "invalid font cmap subtable length"
    except (struct.error, zlib.error):
        return "truncated or malformed font structure"
    return ""


def scoped_font_license_error(origin: dict, entry: dict, repo_root: Path) -> str:
    """Shared OFL gate: explicit font files and their exact reviewed notice.

    Managed SHA-256 values are reviewed checkpoints, not proof of an online
    upstream comparison. No modified-font/RFN or software relicensing approval
    is inferred here. Unknown containers fail closed.
    """
    if error := _checkpoint_error(origin):
        return error
    if not _origin_is_external(
        {key: value for key, value in origin.items() if key != "external"},
        str(entry.get("kind") or ""),
    ):
        return "OFL requires an external reviewed font origin, not a local/in-house label"
    artifacts = origin.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return "OFL requires explicit file artifacts including a font and its notice"
    repo_skill = entry.get("repo_skill")
    if (not safe_relative_path(repo_skill) or len(Path(repo_skill).parts) != 4
            or Path(repo_skill).parts[0] != "skills" or Path(repo_skill).name != "SKILL.md"
            or Path(repo_skill).parent.name != entry.get("normalized_slug")):
        return "OFL assets require an installed canonical skill tree"
    skill_root = Path(repo_skill).parent
    managed = entry.get("managed_files")
    if not isinstance(managed, list):
        return "OFL assets require managed_files checkpoints"
    checkpoint = origin["tracking"]["license_checkpoint"]
    fonts = notices = 0
    seen = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict) or artifact.get("type") != "file":
            return "OFL permits only explicit type=file mappings; directories are forbidden"
        source, target = artifact.get("source"), artifact.get("target")
        if any(not safe_relative_path(p) or any(ord(c) < 32 for c in p) for p in (source, target)):
            return "OFL artifact paths must be safe relative paths"
        relative = Path(target)
        if (relative == Path(repo_skill) or not relative.is_relative_to(skill_root)
                or any(part in {".data", ".git", "__pycache__", "node_modules"} for part in relative.parts)):
            return "OFL artifact must be an installed font/notice inside its skill tree"
        if target in seen:
            return "OFL artifact targets must be unique"
        seen.add(target)
        # Check every parent before reading; neither symlinks nor FIFOs can
        # supply evidence, and sensitive/cache directories are never inspected.
        candidate = repo_root
        for index, part in enumerate(relative.parts):
            candidate = candidate / part
            try:
                mode = candidate.lstat().st_mode
            except OSError:
                return f"OFL artifact {target} is missing or inaccessible"
            if not (stat.S_ISREG(mode) if index == len(relative.parts) - 1 else stat.S_ISDIR(mode)):
                return f"OFL artifact {target} must be a regular file without symlink parents"
        if candidate.stat().st_size > 64 * 1024 * 1024:
            return f"OFL artifact {target} exceeds inspection limit"
        raw = candidate.read_bytes()
        matches = [m for m in managed if isinstance(m, dict) and m.get("path") == target]
        if len(matches) != 1 or matches[0].get("sha256") != hashlib.sha256(raw).hexdigest():
            return f"OFL artifact {target} does not match its managed_files SHA-256 checkpoint"
        # Even an enclosing Apache directory cannot share ownership of a font.
        for peer in entry.get("origins", []):
            if not isinstance(peer, dict) or peer is origin:
                continue
            peer_artifacts = peer.get("artifacts")
            for other in peer_artifacts if isinstance(peer_artifacts, list) else []:
                if not isinstance(other, dict) or not safe_relative_path(other.get("target")):
                    continue
                peer_target = Path(other["target"])
                if relative == peer_target or (other.get("type") == "directory" and relative.is_relative_to(peer_target)):
                    return f"OFL artifact {target} must have exactly one origin owner"
        suffix = relative.suffix.lower()
        if suffix in FONT_SUFFIXES:
            if Path(source).suffix.lower() != suffix:
                return "OFL font source and target extensions must match"
            if error := _font_structure_error(raw, suffix):
                return f"OFL artifact {target}: {error}"
            fonts += 1
        else:
            # The reviewed notice must be explicitly mapped from the CP path;
            # arbitrary README/code files and uncheckpointed notices are denied.
            if (source != checkpoint["path"]
                    or relative.suffix.lower() not in {"", ".txt", ".md"}
                    or Path(source).suffix.lower() not in {"", ".txt", ".md"}
                    or not re.search(r"(?:^|[-_.])(ofl|license|licence|copying|copyright|notice)(?:[-_.]|$)", relative.name, re.I)):
                return "OFL non-font artifacts must be the original checkpointed license/notice"
            _, error = _bundled_license(checkpoint, {target: hashlib.sha256(raw).hexdigest()}, repo_root)
            if error:
                return error
            notices += 1
    if not fonts or not notices:
        return "OFL requires at least one font and its original full license/notice"
    # Inventory actual installed font paths, including unlisted symlinks and
    # special files. A valid declared font must not hide an unmapped sibling.
    declared_fonts = {
        artifact.get("target")
        for peer in entry.get("origins", []) if isinstance(peer, dict)
        for artifact in (peer.get("artifacts") if isinstance(peer.get("artifacts"), list) else [])
        if isinstance(artifact, dict) and artifact.get("type") == "file"
    }
    for directory, dirs, names in os.walk(repo_root / skill_root, followlinks=False):
        dirs[:] = sorted(set(dirs) - {"__pycache__", ".data", ".git", "node_modules"})
        for name in sorted(names + dirs):
            path = Path(directory) / name
            if path.suffix.lower() not in FONT_SUFFIXES:
                continue
            target = path.relative_to(repo_root).as_posix()
            if not stat.S_ISREG(path.lstat().st_mode):
                return f"OFL installed font {target} must be a regular file"
            if target not in declared_fonts:
                return f"OFL installed font {target} requires an explicit file artifact"
            if target not in seen:
                if path.stat().st_size > 64 * 1024 * 1024:
                    return f"OFL installed font {target} exceeds inspection limit"
                if error := _font_structure_error(path.read_bytes(), path.suffix.lower()):
                    return f"OFL installed font {target}: {error}"
    return ""


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
    elif license_tag not in PERMISSIVE_LICENSES | SCOPED_FONT_LICENSES:
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
        scoped = isinstance(origin.get("license"), str) and origin["license"] in SCOPED_FONT_LICENSES
        if scoped or _origin_is_external(origin, entry_kind):
            row = _origin_license_row(origin, mapping=claim["mapping"], index=index,
                                      require_checkpoint=not retired_metadata_only)
            if scoped and row["status"] == "OK":
                if error := scoped_font_license_error(origin, entry, repo_root):
                    row.update(status="MISSING", note=f"{row['repo']}: {error}")
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
