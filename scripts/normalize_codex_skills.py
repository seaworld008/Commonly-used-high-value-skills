#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


def load_export_module(repo_root: Path, scripts_root: Path | None = None):
    script_path = (scripts_root or (repo_root / "scripts")) / "export_openclaw_skills.py"
    spec = importlib.util.spec_from_file_location("export_openclaw_skills", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def discover_skill_files(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("SKILL.md")
        if ".git" not in path.parts and "__pycache__" not in path.parts
    )


def normalize_codex_skill_tree(
    root: Path | str,
    repo_root: Path | str | None = None,
    scripts_root: Path | str | None = None,
) -> dict:
    root = Path(root)
    repo_root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[1]
    scripts_root = Path(scripts_root) if scripts_root is not None else None
    export_module = load_export_module(repo_root, scripts_root=scripts_root)

    skill_files = discover_skill_files(root)
    normalized_count = 0
    for skill_file in skill_files:
        raw_text = skill_file.read_text(encoding="utf-8")
        skill_name = skill_file.parent.name
        normalized = export_module.normalize_skill_markdown(skill_name, raw_text)
        if normalized != raw_text:
            skill_file.write_text(normalized, encoding="utf-8")
            normalized_count += 1

    return {
        "skill_file_count": len(skill_files),
        "normalized_count": normalized_count,
        "root": str(root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize SKILL.md files in a Codex skill tree for YAML frontmatter compatibility."
    )
    parser.add_argument(
        "skills_root",
        nargs="?",
        default=str(Path.home() / ".codex" / "skills"),
        help="Codex skills root (default: ~/.codex/skills)",
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repository root used to load normalization helpers",
    )
    args = parser.parse_args()

    summary = normalize_codex_skill_tree(args.skills_root, repo_root=args.repo_root)
    print(
        f"Normalized {summary['normalized_count']} of {summary['skill_file_count']} SKILL.md file(s) under {summary['root']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
