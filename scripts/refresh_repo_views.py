#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


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
