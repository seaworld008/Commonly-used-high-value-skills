#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import re
from pathlib import Path


CN_CATEGORY_RE = re.compile(r"^###\s+\d+\.\s+(?P<title>.+?)（(?P<category>[a-z0-9-]+)，\d+）\s*$")
EN_CATEGORY_RE = re.compile(r"^###\s+\d+\.\s+(?P<title>.+?)\s+\((?P<category>[a-z0-9-]+),\s*\d+\)\s*$")
SKILL_BULLET_RE = re.compile(r"^-\s+(?:\[)?`(?P<name>[^`]+)`")


def parse_frontmatter(content: str) -> dict[str, str]:
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def skill_tree_with_descriptions(skills_root: Path) -> dict[str, dict[str, dict[str, str]]]:
    tree: dict[str, dict[str, dict[str, str]]] = {}
    for skill_md in sorted(skills_root.glob("*/*/SKILL.md")):
        category = skill_md.parent.parent.name
        name = skill_md.parent.name
        frontmatter = parse_frontmatter(skill_md.read_text(encoding="utf-8", errors="replace"))
        description = frontmatter.get("description", "").strip()
        zh_description = frontmatter.get("zh_description", "").strip()
        tree.setdefault(category, {})[name] = {
            "description": description,
            "zh_description": zh_description or description,
        }
    return {category: dict(sorted(skills.items())) for category, skills in sorted(tree.items())}


def parse_existing_overview(
    content: str,
    *,
    category_re: re.Pattern[str],
) -> tuple[list[str], dict[str, str], dict[str, str], dict[str, dict[str, str]]]:
    order: list[str] = []
    anchors: dict[str, str] = {}
    titles: dict[str, str] = {}
    bullets: dict[str, dict[str, str]] = {}
    current: str | None = None
    pending_anchor = ""

    for line in content.splitlines():
        if line.startswith("<a id="):
            pending_anchor = line
            continue
        heading = category_re.match(line)
        if heading:
            current = heading.group("category")
            order.append(current)
            anchors[current] = pending_anchor
            titles[current] = heading.group("title").strip()
            bullets[current] = {}
            pending_anchor = ""
            continue
        if line.startswith("## "):
            current = None
        if current:
            skill = SKILL_BULLET_RE.match(line)
            if skill:
                bullets[current][skill.group("name")] = line

    return order, anchors, titles, bullets


def replace_section(content: str, start_heading: str, end_heading: str, replacement: str) -> str:
    start = content.find(start_heading)
    if start == -1:
        return content
    end = content.find(end_heading, start + len(start_heading))
    if end == -1:
        return content
    return content[:start] + replacement.rstrip() + "\n\n" + content[end:]


def build_cn_overview(content: str, skills_root: Path, category_count: int, skill_count: int) -> str:
    tree = skill_tree_with_descriptions(skills_root)
    order, anchors, titles, bullets = parse_existing_overview(content, category_re=CN_CATEGORY_RE)
    ordered_categories = [category for category in order if category in tree]
    ordered_categories.extend(category for category in tree if category not in ordered_categories)

    lines = [f"## 技能总览（按分类，{category_count} 类 / {skill_count} 技能）", ""]
    for index, category in enumerate(ordered_categories, start=1):
        anchor = anchors.get(category) or f'<a id="cat-{category}"></a>'
        title = titles.get(category, category)
        skills = tree[category]
        lines.extend([anchor, f"### {index}. {title}（{category}，{len(skills)}）", ""])
        for skill_name, metadata in skills.items():
            existing = bullets.get(category, {}).get(skill_name)
            description = metadata["zh_description"]
            has_explicit_zh = bool(description and description != metadata["description"])
            if existing and not has_explicit_zh:
                lines.append(existing)
            else:
                suffix = description.rstrip(".。") if description else "新增技能"
                lines.append(f"- `{skill_name}`：{suffix}。")
        lines.append("")
    return "\n".join(lines).rstrip()


def build_en_overview(content: str, skills_root: Path, category_count: int, skill_count: int) -> str:
    tree = skill_tree_with_descriptions(skills_root)
    order, anchors, titles, bullets = parse_existing_overview(content, category_re=EN_CATEGORY_RE)
    ordered_categories = [category for category in order if category in tree]
    ordered_categories.extend(category for category in tree if category not in ordered_categories)

    lines = [f"## Skill Overview (by category, {category_count} categories / {skill_count} skills)", ""]
    for index, category in enumerate(ordered_categories, start=1):
        anchor = anchors.get(category) or f'<a id="cat-{category}"></a>'
        title = titles.get(category, category)
        skills = tree[category]
        lines.extend([anchor, f"### {index}. {title} ({category}, {len(skills)})", ""])
        for skill_name in skills:
            existing = bullets.get(category, {}).get(skill_name)
            if existing:
                lines.append(existing)
            else:
                lines.append(f"- [`{skill_name}`](./skills/{category}/{skill_name}/)")
        lines.append("")
    return "\n".join(lines).rstrip()


def load_module(module_name: str, script_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def count_source_skills(skills_root: Path) -> int:
    total = 0
    for category_dir in skills_root.iterdir():
        if not category_dir.is_dir():
            continue
        for skill_dir in category_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                total += 1
    return total


def count_category_readmes(skills_root: Path) -> int:
    total = 0
    for category_dir in skills_root.iterdir():
        if category_dir.is_dir() and (category_dir / "README.md").exists():
            total += 1
    return total


def count_exported_skills(output_root: Path) -> int:
    total = 0
    if not output_root.exists():
        return 0
    for skill_dir in output_root.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            total += 1
    return total


def update_root_readmes(repo_root: Path, category_count: int, skill_count: int) -> None:
    """Update top-level README counters (CN + EN) and badge numbers."""
    skills_root = repo_root / "skills"
    replacements = [
        (
            repo_root / "README.md",
            [
                (
                    re.compile(r"\[!\[Skills\]\(https://img\.shields\.io/badge/Skills-\d+-7c3aed\)\]\(\./skills/\)"),
                    f"[![Skills](https://img.shields.io/badge/Skills-{skill_count}-7c3aed)](./skills/)",
                ),
                (
                    re.compile(r"当前共 \*\*\d+ 个分类 / \d+ 个技能\*\*。"),
                    f"当前共 **{category_count} 个分类 / {skill_count} 个技能**。",
                ),
                (
                    re.compile(r"## 技能总览（按分类，\d+ 类 / \d+ 技能）"),
                    f"## 技能总览（按分类，{category_count} 类 / {skill_count} 技能）",
                ),
                (
                    re.compile(r"`\d+ 类 / \d+ 技能`"),
                    f"`{category_count} 类 / {skill_count} 技能`",
                ),
            ],
        ),
        (
            repo_root / "README.en.md",
            [
                (
                    re.compile(r"\[!\[Skills\]\(https://img\.shields\.io/badge/Skills-\d+-7c3aed\)\]\(\./skills/\)"),
                    f"[![Skills](https://img.shields.io/badge/Skills-{skill_count}-7c3aed)](./skills/)",
                ),
                (
                    re.compile(r"This repository currently contains \*\*\d+ categories / \d+ skills\*\*\."),
                    f"This repository currently contains **{category_count} categories / {skill_count} skills**.",
                ),
                (
                    re.compile(r"## Skill Overview \(by category, \d+ categories / \d+ skills\)"),
                    f"## Skill Overview (by category, {category_count} categories / {skill_count} skills)",
                ),
            ],
        ),
    ]

    for readme_path, rules in replacements:
        if not readme_path.exists():
            continue
        content = readme_path.read_text(encoding="utf-8")
        updated = content
        for pattern, repl in rules:
            updated = pattern.sub(repl, updated)
        if readme_path.name == "README.md":
            updated = replace_section(
                updated,
                "## 技能总览",
                "## 下一轮建议补充方向",
                build_cn_overview(updated, skills_root, category_count, skill_count),
            )
        elif readme_path.name == "README.en.md":
            updated = replace_section(
                updated,
                "## Skill Overview",
                "## Next Curation Directions",
                build_en_overview(updated, skills_root, category_count, skill_count),
            )
        if updated != content:
            readme_path.write_text(updated, encoding="utf-8")


def refresh_repo_views(repo_root: Path | str, scripts_root: Path | str | None = None) -> dict:
    repo_root = Path(repo_root)
    skills_root = repo_root / "skills"
    output_root = repo_root / "openclaw-skills"
    scripts_root = Path(scripts_root) if scripts_root is not None else repo_root / "scripts"

    category_module = load_module(
        "generate_category_readmes", scripts_root / "generate_category_readmes.py"
    )
    export_module = load_module(
        "export_openclaw_skills", scripts_root / "export_openclaw_skills.py"
    )
    normalize_module = load_module(
        "normalize_codex_skills", scripts_root / "normalize_codex_skills.py"
    )

    normalization_summary = normalize_module.normalize_codex_skill_tree(
        skills_root, repo_root=repo_root, scripts_root=scripts_root
    )

    category_outputs = category_module.generate_category_readmes(skills_root)
    export_outputs = export_module.export_openclaw_skills(skills_root, output_root)
    normalize_module.normalize_codex_skill_tree(
        output_root, repo_root=repo_root, scripts_root=scripts_root
    )

    update_root_readmes(repo_root, count_category_readmes(skills_root), count_source_skills(skills_root))

    summary = {
        "source_skill_count": count_source_skills(skills_root),
        "category_readme_count": count_category_readmes(skills_root),
        "exported_skill_count": count_exported_skills(output_root),
        "generated_category_readmes": len(category_outputs),
        "generated_openclaw_skills": len(export_outputs),
        "normalized_source_skills": normalization_summary["normalized_count"],
    }

    if summary["source_skill_count"] != summary["exported_skill_count"]:
        raise RuntimeError(
            "Mismatch between source skill count and exported OpenClaw skill count: "
            f"{summary['source_skill_count']} vs {summary['exported_skill_count']}"
        )

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh generated repository views for category READMEs and OpenClaw export."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repository root (default: current repo root)",
    )
    args = parser.parse_args()

    summary = refresh_repo_views(args.repo_root)
    print(
        "Refreshed repository views: "
        f"{summary['source_skill_count']} source skills, "
        f"{summary['category_readme_count']} category READMEs, "
        f"{summary['exported_skill_count']} exported OpenClaw skills."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
