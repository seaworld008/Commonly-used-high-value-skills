#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


SKILL_FILENAME = "SKILL.md"
IGNORED_NAMES = {
    ".DS_Store",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".git",
}


def split_frontmatter(text: str) -> tuple[str | None, str]:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", text, re.DOTALL)
    if not match:
        return None, text
    return match.group(1), text[match.end() :]


def parse_frontmatter_blocks(frontmatter: str) -> list[tuple[str, list[str]]]:
    lines = frontmatter.splitlines()
    blocks: list[tuple[str, list[str]]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        key_match = re.match(r"^([A-Za-z0-9_-]+):(.*)$", line)
        if not key_match:
            index += 1
            continue

        key = key_match.group(1)
        block_lines = [line]
        index += 1
        while index < len(lines):
            next_line = lines[index]
            if re.match(r"^[A-Za-z0-9_-]+:(?:\s.*)?$", next_line):
                break
            block_lines.append(next_line)
            index += 1
        blocks.append((key, block_lines))
    return blocks


def extract_scalar_value(block_lines: list[str]) -> str:
    if not block_lines:
        return ""

    first = block_lines[0]
    _, _, raw_value = first.partition(":")
    raw_value = raw_value.strip()

    if raw_value.startswith(("|", ">")):
        multiline = [line.strip() for line in block_lines[1:] if line.strip()]
        return collapse_whitespace(" ".join(multiline))

    if raw_value:
        if (raw_value.startswith("'") and raw_value.endswith("'")) or (
            raw_value.startswith('"') and raw_value.endswith('"')
        ):
            raw_value = raw_value[1:-1]
        return collapse_whitespace(raw_value.replace("''", "'"))

    multiline = [line.strip() for line in block_lines[1:] if line.strip()]
    return collapse_whitespace(" ".join(multiline))


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_markdown(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("*", "").replace("_", "")
    return collapse_whitespace(text)


def derive_description_from_body(body: str) -> str:
    lines = body.splitlines()
    paragraph: list[str] = []
    in_code_block = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if not stripped:
            if paragraph:
                break
            continue
        if stripped in {"---", "***"}:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith(("**Tier:**", "**Category:**", "**Domain:**")):
            continue
        if stripped.startswith(("|", "- ", "* ")):
            if paragraph:
                break
            continue
        paragraph.append(stripped)

    text = strip_markdown(" ".join(paragraph))
    if text:
        return text.rstrip(".") + "."
    return "Skill exported from categorized source tree."


def yaml_scalar(text: str) -> str:
    if is_yaml_plain_scalar_safe(text):
        return text
    return "'" + text.replace("'", "''") + "'"


def is_yaml_plain_scalar_safe(text: str) -> bool:
    if not text:
        return False
    if text != text.strip():
        return False
    if "\n" in text or "\r" in text:
        return False
    if any(char in text for char in "[]{}#,|>@`\""):
        return False
    if ": " in text or text.endswith(":"):
        return False
    if text[0] in "-?:!&*%@'":
        return False
    return bool(re.match(r"^[A-Za-z0-9][A-Za-z0-9 ._/:+()-]*$", text))


def normalize_frontmatter_block(block_lines: list[str]) -> list[str]:
    if not block_lines:
        return block_lines

    first = block_lines[0]
    key_match = re.match(r"^([A-Za-z0-9_-]+):(.*)$", first)
    if not key_match:
        return block_lines

    key = key_match.group(1)
    value = key_match.group(2).strip()

    if len(block_lines) == 1 and value:
        if (value.startswith("'") and value.endswith("'")) or (
            value.startswith('"') and value.endswith('"')
        ):
            return block_lines
        return [f"{key}: {yaml_scalar(value)}"]

    return block_lines


def normalize_skill_markdown(skill_name: str, raw_text: str) -> str:
    frontmatter_raw, body = split_frontmatter(raw_text)
    body = body.lstrip("\r\n")

    extra_blocks: list[list[str]] = []
    name = skill_name
    description = ""

    if frontmatter_raw is not None:
        for key, block_lines in parse_frontmatter_blocks(frontmatter_raw):
            if key == "name":
                continue
            elif key == "description":
                description = extract_scalar_value(block_lines)
            else:
                extra_blocks.append(block_lines)

    if not description:
        description = derive_description_from_body(body)

    out_lines = ["---", f"name: {yaml_scalar(name)}", f"description: {yaml_scalar(description)}"]
    for block_lines in extra_blocks:
        out_lines.extend(normalize_frontmatter_block(block_lines))
    out_lines.append("---")
    out_lines.append("")
    out_lines.append(body.rstrip())
    return "\n".join(out_lines).rstrip() + "\n"


def discover_source_skills(source_root: Path) -> list[Path]:
    skills: list[Path] = []
    for category_dir in sorted(source_root.iterdir()):
        if not category_dir.is_dir():
            continue
        for skill_dir in sorted(category_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            if (skill_dir / SKILL_FILENAME).exists():
                skills.append(skill_dir)
    return skills


def ignore_entries(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORED_NAMES}


def export_openclaw_skills(source_root: Path | str, output_root: Path | str) -> list[Path]:
    source_root = Path(source_root)
    output_root = Path(output_root)

    if not source_root.exists():
        raise FileNotFoundError(f"Source root does not exist: {source_root}")

    skill_dirs = discover_source_skills(source_root)
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "README.md").write_text(
        "\n".join(
            [
                "# OpenClaw Skills Export",
                "",
                "This directory is generated from the categorized `skills/` source tree.",
                "",
                "- Do not edit files here by hand.",
                "- Refresh with: `python3 scripts/export_openclaw_skills.py`",
                "- OpenClaw should point to this directory, not the categorized `skills/` root.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    exported: list[Path] = []
    for skill_dir in skill_dirs:
        destination = output_root / skill_dir.name
        shutil.copytree(skill_dir, destination, ignore=ignore_entries)

        for skill_md in destination.rglob(SKILL_FILENAME):
            normalized_name = skill_md.parent.name
            skill_md.write_text(
                normalize_skill_markdown(normalized_name, skill_md.read_text(encoding="utf-8")),
                encoding="utf-8",
            )
        exported.append(destination)

    return exported


def build_parser() -> argparse.ArgumentParser:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Export categorized skills into a flat OpenClaw-compatible skill root."
    )
    parser.add_argument(
        "--source-root",
        default=str(repo_root / "skills"),
        help="Categorized skill source root (default: ./skills)",
    )
    parser.add_argument(
        "--output-root",
        default=str(repo_root / "openclaw-skills"),
        help="Flat OpenClaw skill root to generate (default: ./openclaw-skills)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    exported = export_openclaw_skills(args.source_root, args.output_root)
    print(f"Exported {len(exported)} skills to {args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
