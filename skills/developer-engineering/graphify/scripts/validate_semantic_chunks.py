#!/usr/bin/env python3
"""Validate expected Graphify chunk receipts before graph/cache mutation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import stat
import sys

MAX_BYTES = 8 * 1024 * 1024
TEXT_SUFFIXES = {'.md', '.txt', '.rst', '.csv', '.json', '.yaml', '.yml', '.html', '.xml'}


def read_regular(path: Path) -> bytes:
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError('receipt input must be a regular file')
    with path.open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('receipt input exceeds 8 MiB')
    return data


def validate(root: Path, manifest: Path, chunks_dir: Path, count: int) -> list[str]:
    if not 0 <= count <= 4096:
        raise ValueError('expected chunk count must be between 0 and 4096')
    root = root.resolve(strict=True)
    expected = read_regular(manifest).decode('utf-8').splitlines()
    expected = [line for line in expected if line]
    if len(expected) != len(set(expected)):
        raise ValueError('expected file manifest contains duplicate paths')
    names = {f'.graphify_chunk_{number:02d}.json' for number in range(1, count + 1)}
    if {path.name for path in chunks_dir.glob('.graphify_chunk_*.json')} != names:
        raise ValueError('missing or stale chunk files')
    coverage = {}
    for number in range(1, count + 1):
        payload = json.loads(read_regular(chunks_dir / f'.graphify_chunk_{number:02d}.json'))
        if not isinstance(payload, dict) or not isinstance(payload.get('nodes'), list) or not isinstance(payload.get('edges'), list):
            raise ValueError('chunk requires nodes and edges arrays')
        if not isinstance(payload.get('hyperedges', []), list):
            raise ValueError('hyperedges must be an array')
        receipt = payload.get('coverage')
        if not isinstance(receipt, dict):
            raise ValueError('chunk requires a coverage object')
        for name, lines in receipt.items():
            if name not in expected or isinstance(lines, bool) or not isinstance(lines, int) or lines < 0:
                raise ValueError('invalid coverage entry')
            coverage[name] = max(coverage.get(name, 0), lines)
    failures = []
    for name in expected:
        if name not in coverage:
            failures.append(f'missing coverage: {name}')
            continue
        source = Path(name)
        source = (source if source.is_absolute() else root / source).resolve(strict=True)
        if not source.is_relative_to(root):
            raise ValueError('source escapes the authorized scan root')
        if not source.is_file():
            raise ValueError('source must be a regular file')
        if source.suffix.lower() in TEXT_SUFFIXES:
            lines = len(read_regular(source).decode('utf-8', errors='replace').splitlines())
            if coverage[name] != lines:
                failures.append(f'coverage length mismatch: {name}')
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--chunks-dir', type=Path, required=True)
    parser.add_argument('--expected-chunks', type=int, required=True)
    args = parser.parse_args(argv)
    try:
        failures = validate(args.root, args.manifest, args.chunks_dir, args.expected_chunks)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError) as error:
        print(json.dumps({'ok': False, 'error': type(error).__name__}), file=sys.stderr)
        return 1
    print(json.dumps({'ok': not failures, 'failures': failures}))
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
