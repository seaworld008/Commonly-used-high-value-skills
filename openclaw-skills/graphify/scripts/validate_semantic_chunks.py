#!/usr/bin/env python3
"""Validate expected Graphify chunk receipts before graph/cache mutation."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
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


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON field')
        result[key] = value
    return result


def check_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'\w+', value) or value != value.casefold():
        raise ValueError('invalid graph ID')


def records(payload, collection, receipt):
    items = payload.get(collection, [] if collection == 'hyperedges' else None)
    if not isinstance(items, list):
        raise ValueError(f'{collection} must be an array')
    for record in items:
        if not isinstance(record, dict):
            raise ValueError(f'{collection} record must be an object')
        source = record.get('source_file')
        if not isinstance(source, str) or source not in receipt:
            raise ValueError(f'{collection} record requires a source_file covered by this chunk')
        yield record


def check_entity(record, ids):
    identifier = record.get('id')
    check_id(identifier)
    if identifier in ids:
        raise ValueError('duplicate graph ID')
    ids.add(identifier)
    if not isinstance(record.get('label'), str) or not record['label'].strip():
        raise ValueError('missing label')


def check_relation(record, confidences):
    if not isinstance(record.get('relation'), str) or not record['relation'].strip():
        raise ValueError('missing relation')
    if record.get('confidence') not in confidences:
        raise ValueError('invalid confidence')
    score = record.get('confidence_score')
    if type(score) not in (int, float) or not 0 <= score <= 1:
        raise ValueError('invalid confidence_score')


def check_records(payload, receipt, node_ids, hyperedge_ids):
    for node in records(payload, 'nodes', receipt):
        check_entity(node, node_ids)
        if node.get('file_type') not in ('code', 'document', 'paper', 'image', 'concept', 'rationale'):
            raise ValueError('invalid node file_type')
    for edge in records(payload, 'edges', receipt):
        check_relation(edge, ('EXTRACTED', 'INFERRED', 'AMBIGUOUS'))
        # Endpoints can refer to the AST, cache or another chunk.
        check_id(edge.get('source'))
        check_id(edge.get('target'))
        weight = edge.get('weight', 1)
        if type(weight) not in (int, float) or (isinstance(weight, float) and not math.isfinite(weight)):
            raise ValueError('invalid edge weight')
    for hyperedge in records(payload, 'hyperedges', receipt):
        check_entity(hyperedge, hyperedge_ids)
        check_relation(hyperedge, ('EXTRACTED', 'INFERRED'))
        members = hyperedge.get('nodes')
        if not isinstance(members, list):
            raise ValueError('missing hyperedge nodes')
        for member in members:
            check_id(member)
        if len(set(members)) != len(members) or len(members) < 3:
            raise ValueError('hyperedge requires at least three distinct members')


def check_coverage(root, name, reported):
    source = (root / name).resolve(strict=True)
    if not source.is_relative_to(root):
        raise ValueError('source escapes the authorized scan root')
    if not source.is_file():
        raise ValueError('source must be a regular file')
    if source.suffix.lower() in TEXT_SUFFIXES:
        lines = len(read_regular(source).decode('utf-8', errors='replace').splitlines())
        if reported != lines:
            return f'coverage length mismatch: {name}'
    elif reported == 0:
        # Positive media coverage is an attestation, not proof of full reading or understanding.
        return f'non-text coverage must be positive: {name}'


def validate(root: Path, manifest: Path, chunks_dir: Path, count: int, chunk_plan: Path | None = None) -> list[str]:
    if not 0 <= count <= 4096:
        raise ValueError('expected chunk count must be between 0 and 4096')
    root = root.resolve(strict=True)
    expected = read_regular(manifest).decode('utf-8').splitlines()
    expected = [line for line in expected if line]
    if len(expected) != len(set(expected)):
        raise ValueError('expected file manifest contains duplicate paths')
    expected_files = set(expected)
    plan = None
    if chunk_plan is not None:
        plan = json.loads(read_regular(chunk_plan))
        if not isinstance(plan, list) or len(plan) != count:
            raise ValueError('chunk plan must contain one file list per chunk')
        for group in plan:
            if not isinstance(group, list) or not group or not all(isinstance(name, str) for name in group):
                raise ValueError('invalid chunk assignment')
            if len(group) != len(set(group)):
                raise ValueError('duplicate chunk assignment')
    names = {f'.graphify_chunk_{number:02d}.json' for number in range(1, count + 1)}
    if {path.name for path in chunks_dir.glob('.graphify_chunk_*.json')} != names:
        raise ValueError('missing or stale chunk files')
    seen = set()
    node_ids, hyperedge_ids = set(), set()
    failures = []
    for number in range(1, count + 1):
        payload = json.loads(read_regular(chunks_dir / f'.graphify_chunk_{number:02d}.json'), object_pairs_hook=unique_keys)
        if not isinstance(payload, dict):
            raise ValueError('chunk must be an object')
        receipt = payload.get('coverage')
        if not isinstance(receipt, dict):
            raise ValueError('chunk requires a coverage object')
        if plan is not None and set(receipt) != set(plan[number - 1]):
            raise ValueError('coverage does not match the chunk assignment')
        if not receipt and (count != 1 or not expected):
            raise ValueError('chunk has no coverage entries')
        for name, lines in receipt.items():
            if name not in expected_files or name in seen or type(lines) is not int or lines < 0:
                raise ValueError('invalid coverage entry')
            seen.add(name)
            failure = check_coverage(root, name, lines)
            if failure:
                failures.append(failure)
        check_records(payload, receipt, node_ids, hyperedge_ids)
        for field in ('input_tokens', 'output_tokens'):
            value = payload.get(field, 0)
            if type(value) is not int or value < 0:
                raise ValueError(f'invalid {field}')
    failures.extend(f'missing coverage: {name}' for name in expected if name not in seen)
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--chunks-dir', type=Path, required=True)
    parser.add_argument('--expected-chunks', type=int, required=True)
    parser.add_argument('--chunk-plan', type=Path, help='Trusted JSON array of assigned file lists in chunk-number order')
    args = parser.parse_args(argv)
    try:
        failures = validate(args.root, args.manifest, args.chunks_dir, args.expected_chunks, args.chunk_plan)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError) as error:
        print(json.dumps({'ok': False, 'error': type(error).__name__}), file=sys.stderr)
        return 1
    print(json.dumps({'ok': not failures, 'failures': failures}))
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
