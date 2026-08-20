#!/usr/bin/env python3
"""Validate the durable keep/merge/snapshot/retire decision ledger."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = REPO_ROOT / "docs" / "sources" / "portfolio-decisions-2026-08.json"
DECISIONS = {"keep", "merge", "snapshot", "retire"}
REQUIRED = {
    "name",
    "decision",
    "replacement",
    "unique_assets",
    "external_contract",
    "license_lineage",
    "local_cleanup_action",
    "rationale",
}


def validate(data: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["ledger must be a JSON object"]
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    entries = data.get("decisions")
    if not isinstance(entries, list) or not entries:
        return errors + ["decisions must be a non-empty array"]
    names: set[str] = set()
    for index, entry in enumerate(entries):
        label = f"decisions[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue
        missing = sorted(REQUIRED - set(entry))
        if missing:
            errors.append(f"{label} missing fields: {', '.join(missing)}")
            continue
        name = entry["name"]
        if not isinstance(name, str) or not re.fullmatch(
            r"[a-z0-9]+(?:-[a-z0-9]+)*", name
        ):
            errors.append(f"{label}.name must be a safe skill or bundle slug")
        elif name in names:
            errors.append(f"{label}.name duplicates {name}")
        else:
            names.add(name)
        decision = entry["decision"]
        if decision not in DECISIONS:
            errors.append(f"{label}.decision must be one of {sorted(DECISIONS)}")
        replacement = entry["replacement"]
        if decision == "merge" and (
            not isinstance(replacement, str) or not replacement.strip()
        ):
            errors.append(f"{label}.replacement is required for merge")
        if decision == "retire" and replacement is not None and (
            not isinstance(replacement, str) or not replacement.strip()
        ):
            errors.append(
                f"{label}.replacement must be null or a non-empty string for retire"
            )
        if decision == "keep" and replacement is not None:
            errors.append(f"{label}.replacement must be null for keep")
        assets = entry["unique_assets"]
        if not isinstance(assets, list) or any(
            not isinstance(item, str) or not item.strip() for item in assets
        ):
            errors.append(f"{label}.unique_assets must be a string array")
        for field in ("license_lineage", "local_cleanup_action", "rationale"):
            if not isinstance(entry[field], str) or not entry[field].strip():
                errors.append(f"{label}.{field} must be a non-empty string")
        if decision == "snapshot" and "permissive" not in entry["license_lineage"].lower():
            errors.append(f"{label}.license_lineage must document a permissive snapshot license")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    args = parser.parse_args()
    data = json.loads(args.ledger.read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Portfolio decision ledger valid: {len(data['decisions'])} decisions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
