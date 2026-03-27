#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import shutil
from pathlib import Path


SKILL_FILENAME = "SKILL.md"
REPO_ROOT = Path(__file__).resolve().parents[1]


def load_export_module(repo_root: Path):
    script_path = repo_root / "scripts" / "export_openclaw_skills.py"
    spec = importlib.util.spec_from_file_location("export_openclaw_skills", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def discover_source_skills(source_root: Path) -> list[Path]:
    return sorted(path.parent for path in source_root.glob("*/*/SKILL.md"))


def discover_codex_skills(codex_root: Path) -> list[Path]:
    if not codex_root.exists():
        return []
    return sorted(path for path in codex_root.iterdir() if path.is_dir() and (path / SKILL_FILENAME).exists())


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_skill_markdown(repo_root: Path, skill_name: str, skill_file: Path) -> None:
    export_module = load_export_module(repo_root)
    raw_text = skill_file.read_text(encoding="utf-8")
    normalized = export_module.normalize_skill_markdown(skill_name, raw_text)
    if normalized != raw_text:
        skill_file.write_text(normalized, encoding="utf-8")


def replace_directory(source_dir: Path, dest_dir: Path) -> None:
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.copytree(source_dir, dest_dir)


def sync_codex_skills(
    *,
    source_root: Path,
    codex_root: Path,
    repo_root: Path | None = None,
) -> dict:
    repo_root = repo_root or REPO_ROOT
    codex_root.mkdir(parents=True, exist_ok=True)

    source_skill_dirs = discover_source_skills(source_root)
    source_by_name = {path.name: path for path in source_skill_dirs}
    codex_skill_dirs = discover_codex_skills(codex_root)
    codex_by_name = {path.name: path for path in codex_skill_dirs}

    added_count = 0
    updated_count = 0
    unchanged_count = 0

    for skill_name, source_dir in sorted(source_by_name.items()):
        dest_dir = codex_root / skill_name
        source_skill_file = source_dir / SKILL_FILENAME
        dest_skill_file = dest_dir / SKILL_FILENAME

        source_hash = file_hash(source_skill_file)
        dest_hash = file_hash(dest_skill_file) if dest_skill_file.exists() else None

        if dest_dir.exists():
            replace_directory(source_dir, dest_dir)
            if source_hash == dest_hash:
                unchanged_count += 1
            else:
                updated_count += 1
        else:
            replace_directory(source_dir, dest_dir)
            added_count += 1

        normalize_skill_markdown(repo_root, skill_name, dest_dir / SKILL_FILENAME)

    preserved_extra = sorted(set(codex_by_name) - set(source_by_name))

    return {
        "source_skill_count": len(source_by_name),
        "codex_skill_count_before": len(codex_by_name),
        "added_count": added_count,
        "updated_count": updated_count,
        "unchanged_count": unchanged_count,
        "preserved_extra_count": len(preserved_extra),
        "preserved_extras": preserved_extra,
        "codex_root": str(codex_root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync categorized repository skills into a flat Codex skills directory."
    )
    parser.add_argument(
        "--source-root",
        default=str(REPO_ROOT / "skills"),
        help="Categorized repository skills root (default: repo ./skills)",
    )
    parser.add_argument(
        "--codex-root",
        default=str(Path.home() / ".codex" / "skills"),
        help="Flat Codex skills root (default: ~/.codex/skills)",
    )
    args = parser.parse_args()

    summary = sync_codex_skills(
        source_root=Path(args.source_root),
        codex_root=Path(args.codex_root),
        repo_root=REPO_ROOT,
    )

    print(
        "Synced {source_skill_count} repo skills into {codex_root}. "
        "Added: {added_count}, Updated: {updated_count}, Unchanged: {unchanged_count}, "
        "Preserved Codex-only skills: {preserved_extra_count}.".format(**summary)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
