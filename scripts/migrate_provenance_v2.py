#!/usr/bin/env python3
"""Add provenance v2 fields to source mappings.

The migration is dry-run by default.  Pass ``--write`` to atomically update the
selected JSON mappings.  Legacy fields are retained for older sync consumers.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from provenance_v2 import (
        SCHEMA_VERSION,
        atomic_write_json,
        discover_source_mappings,
        migrate_payload,
    )
except ModuleNotFoundError:  # pragma: no cover - import path used by unit tests
    from scripts.provenance_v2 import (
        SCHEMA_VERSION,
        atomic_write_json,
        discover_source_mappings,
        migrate_payload,
    )


def discover_mappings(repo_root: Path, requested: list[str]) -> list[Path]:
    if requested:
        return [repo_root / value for value in requested]
    return discover_source_mappings(repo_root / "docs" / "sources")


def migrate_file(
    path: Path,
    repo_root: Path,
    *,
    write: bool = False,
    refresh_managed_digests: bool = False,
) -> bool:
    original = json.loads(path.read_text(encoding="utf-8"))
    migrated = migrate_payload(
        original,
        repo_root,
        refresh_managed_digests=refresh_managed_digests,
    )
    changed = migrated != original
    if write and changed:
        atomic_write_json(path, migrated)
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mapping",
        action="append",
        default=[],
        help="Mapping path relative to the repository (repeatable)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Atomically update mappings (default: dry-run only)",
    )
    parser.add_argument(
        "--refresh-managed-digests",
        action="store_true",
        help=(
            "Recompute hashes for existing declared managed files; "
            "still requires --write to persist"
        ),
    )
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()
    mappings = discover_mappings(repo_root, args.mapping)
    if not mappings:
        print("No mapping files found.")
        return 1

    changed = 0
    for mapping in mappings:
        if not mapping.is_file():
            print(f"ERROR missing mapping: {mapping}")
            return 1
        needs_change = migrate_file(
            mapping,
            repo_root,
            write=args.write,
            refresh_managed_digests=args.refresh_managed_digests,
        )
        changed += int(needs_change)
        if needs_change and args.refresh_managed_digests:
            state = (
                "refreshed managed digests"
                if args.write
                else "would refresh managed digests"
            )
        else:
            state = "migrated" if args.write and needs_change else (
                "would migrate" if needs_change else "already v2"
            )
        try:
            label = mapping.relative_to(repo_root)
        except ValueError:
            label = mapping
        print(f"- {label}: {state}")

    mode = "write" if args.write else "dry-run"
    operation = (
        "migration with managed digest refresh"
        if args.refresh_managed_digests
        else "migration"
    )
    print(
        f"Provenance v{SCHEMA_VERSION} {operation} {mode}: "
        f"{changed}/{len(mappings)} mapping(s) changed"
    )
    if changed and not args.write:
        print("No files were written. Re-run with --write after reviewing the report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
