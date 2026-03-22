#!/usr/bin/env python3
"""Validate skill source mapping JSON files against repository skill files.

Default behavior validates all `docs/sources/*.skills.json` mappings.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REQUIRED_TOP = {"video", "official_references", "skills"}
REQUIRED_SKILL_KEYS = {"video_name", "normalized_slug", "status", "repo_skill", "source", "notes"}
VALID_STATUS = {"verified_in_repo", "verified_not_in_repo", "not_a_skill", "unverified_slug", "in_house"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URL_RE = re.compile(r"^https?://")


def parse_name_from_skill_md(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    fm = text.split("\n---\n", 1)[0]
    m = re.search(r"^name:\s*['\"]?([^'\"\n]+)['\"]?\s*$", fm, re.MULTILINE)
    return m.group(1).strip() if m else None


def _validate_top(data: dict, mapping: Path, errors: list[str]) -> None:
    missing_top = REQUIRED_TOP - set(data.keys())
    if missing_top:
        errors.append(f"{mapping}: missing top-level keys: {sorted(missing_top)}")

    video = data.get("video", {})
    checked = video.get("checked_at")
    if checked and not DATE_RE.match(str(checked)):
        errors.append(f"{mapping}: video.checked_at should be YYYY-MM-DD")


def _validate_verification_attempts(data: dict, mapping: Path, errors: list[str]) -> None:
    attempts = data.get("verification_attempts", [])
    if attempts and not isinstance(attempts, list):
        errors.append(f"{mapping}: verification_attempts must be an array")
        return
    for i, item in enumerate(attempts, 1):
        d = item.get("date")
        if d and not DATE_RE.match(str(d)):
            errors.append(f"{mapping}: verification_attempts[{i}].date must be YYYY-MM-DD")




def _validate_upstream(item: dict, mapping: Path, idx: int, errors: list[str]) -> None:
    upstream = item.get("upstream")
    if upstream is None:
        return
    if not isinstance(upstream, dict):
        errors.append(f"{mapping}: skills[{idx}] upstream must be an object")
        return

    for key in ("last_checked_at", "last_synced_at"):
        val = upstream.get(key)
        if val and not DATE_RE.match(str(val)):
            errors.append(f"{mapping}: skills[{idx}] upstream.{key} must be YYYY-MM-DD")

    repo = upstream.get("repo")
    if repo and "/" not in str(repo):
        errors.append(f"{mapping}: skills[{idx}] upstream.repo should look like owner/repo")


def validate_mapping(mapping_path: Path, repo_root: Path) -> list[str]:
    errors: list[str] = []
    data = json.loads(mapping_path.read_text(encoding="utf-8"))

    _validate_top(data, mapping_path, errors)
    _validate_verification_attempts(data, mapping_path, errors)

    skills = data.get("skills", [])
    if not isinstance(skills, list) or not skills:
        errors.append(f"{mapping_path}: skills must be a non-empty array")
        return errors

    for idx, item in enumerate(skills, 1):
        missing = REQUIRED_SKILL_KEYS - set(item.keys())
        if missing:
            errors.append(f"{mapping_path}: skills[{idx}] missing keys: {sorted(missing)}")
            continue

        status = item["status"]
        slug = item["normalized_slug"]
        repo_skill = item["repo_skill"]
        source = item["source"]

        if status not in VALID_STATUS:
            errors.append(f"{mapping_path}: skills[{idx}] invalid status: {status}")
        if source and not URL_RE.match(str(source)):
            errors.append(f"{mapping_path}: skills[{idx}] source must be http/https URL")
        _validate_upstream(item, mapping_path, idx, errors)

        if status in {"verified_in_repo", "in_house"}:
            if not slug:
                errors.append(f"{mapping_path}: skills[{idx}] {status} must have normalized_slug")
            if not repo_skill:
                errors.append(f"{mapping_path}: skills[{idx}] {status} must have repo_skill")
                continue
            path = repo_root / repo_skill
            if not path.exists():
                errors.append(f"{mapping_path}: skills[{idx}] repo_skill does not exist: {repo_skill}")
                continue
            parsed_name = parse_name_from_skill_md(path)
            if parsed_name != slug:
                errors.append(
                    f"{mapping_path}: skills[{idx}] slug mismatch: normalized_slug={slug}, "
                    f"SKILL.md name={parsed_name}, file={repo_skill}"
                )

        if status in {"not_a_skill", "unverified_slug"} and slug is not None:
            errors.append(
                f"{mapping_path}: skills[{idx}] status {status} should keep normalized_slug as null until verified"
            )

    return errors


def discover_mappings(repo_root: Path, mapping: str | None) -> list[Path]:
    if mapping:
        return [repo_root / mapping]
    return sorted((repo_root / "docs/sources").glob("*.skills.json"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mapping",
        default=None,
        help="Specific mapping file to validate (default: validate all docs/sources/*.skills.json)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    mappings = discover_mappings(repo_root, args.mapping)
    if not mappings:
        print("No mapping files found under docs/sources/*.skills.json")
        return 1

    all_errors: list[str] = []
    for m in mappings:
        if not m.exists():
            all_errors.append(f"Mapping not found: {m}")
            continue
        all_errors.extend(validate_mapping(m, repo_root))

    if all_errors:
        print("Validation failed:")
        for err in all_errors:
            print(f"- {err}")
        return 1

    print("Validation passed:")
    for m in mappings:
        print(f"- {m.relative_to(repo_root)}")
    print("- all verified entries have valid repo_skill and frontmatter name alignment")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
