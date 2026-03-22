#!/usr/bin/env python3
"""Fail if git conflict markers are present in tracked text files."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

CONFLICT_RE = re.compile(r"^(<<<<<<< .+|=======|>>>>>>> .+)$", re.MULTILINE)
SKIP_SUFFIX = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".pdf", ".pyc", ".zip"}


def tracked_files(root: Path) -> list[Path]:
    out = subprocess.check_output(["git", "ls-files"], cwd=root, text=True)
    paths = []
    for line in out.splitlines():
        p = root / line
        if p.suffix.lower() in SKIP_SUFFIX:
            continue
        paths.append(p)
    return paths


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    bad: list[str] = []
    for p in tracked_files(root):
        try:
            content = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if CONFLICT_RE.search(content):
            bad.append(str(p.relative_to(root)))

    if bad:
        print("Conflict markers found:")
        for b in bad:
            print(f"- {b}")
        return 1

    print("No merge conflict markers found in tracked files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
