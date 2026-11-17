#!/usr/bin/env python3
"""Check local Markdown resource closure from skill entrypoints (optionally exports)."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

LINK_START = re.compile(r'!?\[(?:\\.|[^\]\\\n])*\]\(\s*')
REFERENCE_START = re.compile(r'^\s{0,3}\[(?:\\.|[^\]\\\n])+\]:\s*')


def markdown_destinations(text: str):
    """Yield (line, start, end, destination), leaving wrappers/titles untouched.

    Offsets refer to the original text. Skip fenced and inline code; support
    angle destinations, balanced parentheses, and reference definitions.
    """
    fence = None
    offset = 0
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        marker = re.match(r'^\s*(`{3,}|~{3,})(.*)$', line.rstrip('\r\n'))
        if marker:
            value, tail = marker.groups()
            if fence is None:
                fence = value
            elif value[0] == fence[0] and len(value) >= len(fence) and not tail.strip():
                fence = None
            offset += len(line)
            continue
        if fence is not None:
            offset += len(line)
            continue
        prose = re.sub(r'(`+)(?!`).*?(?<!`)\1(?!`)', lambda m: ' ' * len(m[0]), line)
        starts = [(m.end(), False) for m in LINK_START.finditer(prose)]
        definition = REFERENCE_START.match(prose)
        if definition:
            starts.append((definition.end(), True))
        for start, is_definition in sorted(starts):
            end = start
            if prose[start:start + 1] == '<':
                start += 1
                end = prose.find('>', start)
                if end < 0:
                    continue
            else:
                depth = 0
                while end < len(prose):
                    char = prose[end]
                    if char == '\\' and end + 1 < len(prose):
                        end += 2
                        continue
                    if char.isspace():
                        break
                    if char == '(':
                        depth += 1
                    elif char == ')':
                        if not depth:
                            break
                        depth -= 1
                    end += 1
                if depth:
                    continue
            if end > start:
                # Reference definitions end after a destination or optional title;
                # inline destinations must have the Markdown closing delimiter.
                tail = prose[end + (prose[end:end + 1] == '>'):].strip()
                if not is_definition and not re.fullmatch(r'(?:["\'].*["\']\s*|\(.*\)\s*)?\).*', tail):
                    continue
                yield number, offset + start, offset + end, text[offset + start:offset + end]
        offset += len(line)


def local_path(target: str) -> str | None:
    if '{{' in target and '}}' in target:
        return None  # Explicit project/output template, not a bundled asset.
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    return unquote(re.sub(r'\\([!"#$%&\'()*+,\-./:;<=>?@\[\]^_`{|}~\\])', r'\1', parsed.path))


def local_links(text: str):
    for number, _, _, target in markdown_destinations(text):
        path = local_path(target)
        if path is not None:
            yield number, path


def check(root: Path, *, include_exports: bool = False) -> list[str]:
    root = root.resolve()
    failures = []
    canonical = sorted((root / 'skills').glob('*/*/SKILL.md'))
    trees = [(root, canonical)]
    if include_exports:
        exports = root / 'openclaw-skills'
        if not exports.is_dir():
            failures.append('openclaw-skills: missing export tree (--include-exports requires generated exports)')
        for source in canonical:
            entry = exports / source.parent.name / 'SKILL.md'
            if not entry.is_file():
                failures.append(f'{entry.relative_to(root)}: missing exported entrypoint')
        trees.append((exports, sorted(exports.glob('*/SKILL.md'))))
    for boundary, entries in trees:
        pending = list(entries)
        visited = set()
        while pending:
            path = pending.pop().resolve()
            if path in visited:
                continue
            visited.add(path)
            if not path.is_relative_to(boundary):
                failures.append(f'{path}: entrypoint escapes bundle')
                continue
            for line, target in local_links(path.read_text(encoding='utf-8')):
                resolved = (path.parent / target).resolve()
                if not resolved.is_relative_to(boundary) or not resolved.exists():
                    failures.append(f'{path.relative_to(root)}:{line}: missing bundled resource {target}')
                elif resolved.is_file() and resolved.suffix.lower() in {'.md', '.markdown'}:
                    pending.append(resolved)
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--include-exports', action='store_true',
                        help='Also require openclaw-skills entries and check their resource closure within the export tree; absent exports are an error')
    args = parser.parse_args(argv)
    failures = check(args.root, include_exports=args.include_exports)
    for failure in failures:
        print(failure)
    print(f'Skill entrypoint reference check: {len(failures)} missing resource(s)')
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
