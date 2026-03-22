#!/usr/bin/env python3
"""Validate OpenClaw video skills mapping JSON against repository skill files."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REQUIRED_TOP = {"video", "official_references", "skills"}
REQUIRED_SKILL_KEYS = {"video_name", "normalized_slug", "status", "repo_skill", "source", "notes"}
VALID_STATUS = {"verified_in_repo", "not_a_skill", "unverified_slug"}


def parse_name_from_skill_md(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    # minimal frontmatter parser: first line '---', then key: value until next '---'
    if not text.startswith("---\n"):
        return None
    fm = text.split("\n---\n", 1)[0]
    m = re.search(r"^name:\s*['\"]?([^'\"\n]+)['\"]?\s*$", fm, re.MULTILINE)
    return m.group(1).strip() if m else None


def validate(mapping_path: Path, repo_root: Path) -> list[str]:
    errors: list[str] = []
    data = json.loads(mapping_path.read_text(encoding="utf-8"))

    missing_top = REQUIRED_TOP - set(data.keys())
    if missing_top:
        errors.append(f"Missing top-level keys: {sorted(missing_top)}")

    skills = data.get("skills", [])
    if not isinstance(skills, list) or not skills:
        errors.append("skills must be a non-empty array")
        return errors

    for idx, item in enumerate(skills, 1):
        missing = REQUIRED_SKILL_KEYS - set(item.keys())
        if missing:
            errors.append(f"skills[{idx}] missing keys: {sorted(missing)}")
            continue

        status = item["status"]
        slug = item["normalized_slug"]
        repo_skill = item["repo_skill"]

        if status not in VALID_STATUS:
            errors.append(f"skills[{idx}] invalid status: {status}")

        if status == "verified_in_repo":
            if not slug:
                errors.append(f"skills[{idx}] verified_in_repo must have normalized_slug")
            if not repo_skill:
                errors.append(f"skills[{idx}] verified_in_repo must have repo_skill")
                continue
            path = repo_root / repo_skill
            if not path.exists():
                errors.append(f"skills[{idx}] repo_skill does not exist: {repo_skill}")
                continue
            parsed_name = parse_name_from_skill_md(path)
            if parsed_name != slug:
                errors.append(
                    f"skills[{idx}] slug mismatch: normalized_slug={slug}, SKILL.md name={parsed_name}, file={repo_skill}"
                )

        if status in {"not_a_skill", "unverified_slug"} and slug is not None:
            errors.append(f"skills[{idx}] status {status} should keep normalized_slug as null until verified")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mapping",
        default="docs/sources/openclaw-video-2nP0YCjM_hk.skills.json",
        help="Path to mapping JSON",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    mapping_path = repo_root / args.mapping
    errors = validate(mapping_path, repo_root)
    if errors:
        print("Validation failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("Validation passed:")
    print(f"- mapping: {args.mapping}")
    print("- all verified_in_repo entries exist and match SKILL.md frontmatter name")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
