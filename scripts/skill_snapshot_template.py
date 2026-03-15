#!/usr/bin/env python3
"""Generate and validate skill snapshot JSON files.

Use this to reduce manual work when maintaining `--snapshot` inputs for
`scripts/audit_skill_freshness.py`.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_GLOB = "skills/*/*/SKILL.md"


def discover_local_skills() -> list[str]:
    names = {path.parent.name for path in ROOT.glob(SKILL_GLOB)}
    return sorted(names)


def build_snapshot(source: str, skills: list[str]) -> dict:
    return {
        "skills": skills,
        "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": source,
    }


def validate_snapshot_data(data: object) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "snapshot must be a JSON object"

    skills = data.get("skills")
    captured_at = data.get("captured_at")
    source = data.get("source")

    if not isinstance(skills, list) or not skills:
        return False, "`skills` must be a non-empty list"
    if not all(isinstance(s, str) and s.strip() for s in skills):
        return False, "`skills` must contain non-empty strings"
    if len(skills) != len(set(skills)):
        return False, "`skills` contains duplicates"

    if not isinstance(captured_at, str) or not captured_at.strip():
        return False, "`captured_at` must be a non-empty string"

    if not isinstance(source, str) or not source.strip():
        return False, "`source` must be a non-empty string"

    return True, "ok"


def cmd_generate(args: argparse.Namespace) -> int:
    output: Path = args.output
    output.parent.mkdir(parents=True, exist_ok=True)

    skills = discover_local_skills() if args.from_local else []
    source = args.source or ("local repo scan" if args.from_local else "manual")
    snapshot = build_snapshot(source=source, skills=skills or ["example-skill"])

    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"snapshot written: {output}")
    print(f"skills count: {len(snapshot['skills'])}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    snapshot_path: Path = args.snapshot
    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    ok, message = validate_snapshot_data(data)
    if ok:
        print(f"valid snapshot: {snapshot_path}")
        print(f"skills count: {len(data['skills'])}")
        return 0
    print(f"invalid snapshot: {snapshot_path}")
    print(message)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate/validate snapshot JSON for skill freshness auditing.")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate a snapshot template JSON.")
    gen.add_argument("--output", type=Path, required=True, help="Output JSON file path.")
    gen.add_argument(
        "--from-local",
        action="store_true",
        help="Populate `skills` from local repository (skills/*/*/SKILL.md).",
    )
    gen.add_argument("--source", type=str, default="", help="Optional custom source label.")
    gen.set_defaults(func=cmd_generate)

    val = sub.add_parser("validate", help="Validate a snapshot JSON file.")
    val.add_argument("--snapshot", type=Path, required=True, help="Snapshot JSON path.")
    val.set_defaults(func=cmd_validate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
