#!/usr/bin/env python3
"""Validate that Chinese and English root READMEs stay aligned with the skill tree."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


CN_CATEGORY_RE = re.compile(r"^###\s+\d+\.\s+.+?（(?P<category>[a-z0-9-]+)，(?P<count>\d+)）\s*$")
EN_CATEGORY_RE = re.compile(r"^###\s+\d+\.\s+.+?\((?P<category>[a-z0-9-]+),\s*(?P<count>\d+)\)\s*$")
SKILL_BULLET_RE = re.compile(r"^-\s+(?:\[)?`(?P<name>[^`]+)`")
BADGE_RE = re.compile(r"Skills-(?P<count>\d+)-7c3aed")
CN_TOTAL_RE = re.compile(r"当前共 \*\*(?P<categories>\d+) 个分类 / (?P<skills>\d+) 个技能\*\*。")
EN_TOTAL_RE = re.compile(r"This repository currently contains \*\*(?P<categories>\d+) categories / (?P<skills>\d+) skills\*\*\.")


def actual_skill_tree(repo_root: Path) -> dict[str, list[str]]:
    tree: dict[str, list[str]] = {}
    for skill_md in sorted((repo_root / "skills").glob("*/*/SKILL.md")):
        category = skill_md.parent.parent.name
        tree.setdefault(category, []).append(skill_md.parent.name)
    return {category: sorted(names) for category, names in sorted(tree.items())}


def parse_readme_categories(readme_path: Path, category_re: re.Pattern[str]) -> dict[str, dict[str, object]]:
    categories: dict[str, dict[str, object]] = {}
    current: str | None = None
    for line in readme_path.read_text(encoding="utf-8").splitlines():
        heading = category_re.match(line)
        if heading:
            current = heading.group("category")
            categories[current] = {
                "count": int(heading.group("count")),
                "skills": [],
            }
            continue
        if line.startswith("## "):
            current = None
            continue
        if current:
            skill = SKILL_BULLET_RE.match(line)
            if skill:
                categories[current]["skills"].append(skill.group("name"))
    return categories


def parse_counts(readme_path: Path, total_re: re.Pattern[str]) -> tuple[int, int, int]:
    text = readme_path.read_text(encoding="utf-8")
    badge = BADGE_RE.search(text)
    total = total_re.search(text)
    if not badge or not total:
        raise AssertionError(f"{readme_path.name} is missing badge or total count text")
    return int(total.group("categories")), int(total.group("skills")), int(badge.group("count"))


def validate_readme(
    *,
    readme_path: Path,
    category_re: re.Pattern[str],
    total_re: re.Pattern[str],
    expected_tree: dict[str, list[str]],
) -> list[str]:
    errors: list[str] = []
    expected_category_count = len(expected_tree)
    expected_skill_count = sum(len(skills) for skills in expected_tree.values())

    try:
        category_count, skill_count, badge_count = parse_counts(readme_path, total_re)
    except AssertionError as exc:
        return [str(exc)]

    if category_count != expected_category_count:
        errors.append(f"{readme_path.name}: total category count {category_count} != {expected_category_count}")
    if skill_count != expected_skill_count:
        errors.append(f"{readme_path.name}: total skill count {skill_count} != {expected_skill_count}")
    if badge_count != expected_skill_count:
        errors.append(f"{readme_path.name}: badge skill count {badge_count} != {expected_skill_count}")

    parsed = parse_readme_categories(readme_path, category_re)
    if set(parsed) != set(expected_tree):
        errors.append(
            f"{readme_path.name}: category set mismatch; missing={sorted(set(expected_tree) - set(parsed))}, "
            f"extra={sorted(set(parsed) - set(expected_tree))}"
        )

    for category, expected_skills in expected_tree.items():
        if category not in parsed:
            continue
        declared_count = parsed[category]["count"]
        declared_skills = sorted(parsed[category]["skills"])
        if declared_count != len(expected_skills):
            errors.append(f"{readme_path.name}: {category} heading count {declared_count} != {len(expected_skills)}")
        if declared_skills != expected_skills:
            errors.append(
                f"{readme_path.name}: {category} skill list mismatch; "
                f"missing={sorted(set(expected_skills) - set(declared_skills))}, "
                f"extra={sorted(set(declared_skills) - set(expected_skills))}"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check README.md and README.en.md sync with the skill tree.")
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    expected_tree = actual_skill_tree(repo_root)
    errors = []
    errors.extend(
        validate_readme(
            readme_path=repo_root / "README.md",
            category_re=CN_CATEGORY_RE,
            total_re=CN_TOTAL_RE,
            expected_tree=expected_tree,
        )
    )
    errors.extend(
        validate_readme(
            readme_path=repo_root / "README.en.md",
            category_re=EN_CATEGORY_RE,
            total_re=EN_TOTAL_RE,
            expected_tree=expected_tree,
        )
    )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        f"README sync OK: {len(expected_tree)} categories / "
        f"{sum(len(skills) for skills in expected_tree.values())} skills"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
