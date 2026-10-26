#!/usr/bin/env python3
"""Check bundled local Markdown resource links in canonical skill entrypoints."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

LINK = re.compile(r'!?\[[^\]\n]*\]\(([^)\n]+)\)')


def local_links(text: str):
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            value = marker.group(1)
            if fence is None:
                fence = value
            elif value[0] == fence[0] and len(value) >= len(fence):
                fence = None
            continue
        if fence is not None:
            continue
        prose = re.sub(r'(`+).*?\1', '', line)
        for match in LINK.finditer(prose):
            target = match.group(1).strip()
            if target.startswith('<') and '>' in target:
                target = target[1:target.index('>')]
            else:
                target = re.split(r'\s+["\']', target, maxsplit=1)[0]
            if '{{' in target and '}}' in target:
                continue  # Explicit project/output template variable, not a bundled asset.
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            yield number, unquote(parsed.path)


def check(root: Path) -> list[str]:
    root = root.resolve()
    failures = []
    for path in sorted((root / 'skills').glob('*/*/SKILL.md')):
        for line, target in local_links(path.read_text(encoding='utf-8')):
            resolved = (path.parent / target).resolve()
            if not resolved.is_relative_to(root) or not resolved.exists():
                failures.append(f'{path.relative_to(root)}:{line}: missing bundled resource {target}')
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    failures = check(args.root)
    for failure in failures:
        print(failure)
    print(f'Skill entrypoint reference check: {len(failures)} missing resource(s)')
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
