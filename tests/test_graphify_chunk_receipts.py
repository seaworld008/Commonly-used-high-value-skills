import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/developer-engineering/graphify/scripts/validate_semantic_chunks.py'
spec = importlib.util.spec_from_file_location('graphify_receipts', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def prepare(tmp_path, receipt):
    (tmp_path / 'doc.md').write_text('first\nsecond\n')
    manifest = tmp_path / 'manifest.txt'; manifest.write_text('doc.md\n')
    chunk = tmp_path / '.graphify_chunk_01.json'
    chunk.write_text(json.dumps({'nodes': [], 'edges': [], 'coverage': receipt}))
    return manifest, chunk


def test_complete_empty_extraction_is_valid(tmp_path):
    manifest, _ = prepare(tmp_path, {'doc.md': 2})
    assert module.validate(tmp_path, manifest, tmp_path, 1) == []


def test_missing_file_attestation_cannot_pass(tmp_path):
    manifest, _ = prepare(tmp_path, {})
    assert module.validate(tmp_path, manifest, tmp_path, 1) == ['missing coverage: doc.md']


def test_partial_file_cannot_pass(tmp_path):
    manifest, _ = prepare(tmp_path, {'doc.md': 1})
    assert module.validate(tmp_path, manifest, tmp_path, 1) == ['coverage length mismatch: doc.md']


def test_overclaimed_line_count_is_not_accepted(tmp_path):
    manifest, _ = prepare(tmp_path, {'doc.md': 9999})
    assert module.validate(tmp_path, manifest, tmp_path, 1) == ['coverage length mismatch: doc.md']


def test_missing_expected_chunk_is_error(tmp_path):
    manifest, _ = prepare(tmp_path, {'doc.md': 2})
    with pytest.raises(ValueError, match='missing or stale'): module.validate(tmp_path, manifest, tmp_path, 2)


def test_unexpected_stale_chunk_is_error(tmp_path):
    manifest, _ = prepare(tmp_path, {'doc.md': 2})
    (tmp_path / '.graphify_chunk_99.json').write_text('{}')
    with pytest.raises(ValueError, match='missing or stale'): module.validate(tmp_path, manifest, tmp_path, 1)


@pytest.mark.parametrize('receipt', [{'unknown.md': 3}, {'doc.md': True}, {'doc.md': -1}, {'doc.md': '2'}])
def test_invalid_coverage_is_error(tmp_path, receipt):
    manifest, _ = prepare(tmp_path, receipt)
    with pytest.raises(ValueError): module.validate(tmp_path, manifest, tmp_path, 1)


def test_empty_manifest_preserves_cached_only_route(tmp_path):
    manifest = tmp_path / 'manifest.txt'; manifest.write_text('')
    assert module.validate(tmp_path, manifest, tmp_path, 0) == []


def test_source_outside_root_is_rejected(tmp_path):
    root = tmp_path / 'scan'; root.mkdir()
    outside = tmp_path / 'outside.md'; outside.write_text('secret\n')
    manifest = root / 'manifest.txt'; manifest.write_text(str(outside)+'\n')
    (root / '.graphify_chunk_01.json').write_text(json.dumps({'nodes': [], 'edges': [], 'coverage': {str(outside): 1}}))
    with pytest.raises(ValueError, match='escapes'): module.validate(root, manifest, root, 1)


def test_chunk_symlink_is_not_followed(tmp_path):
    manifest, chunk = prepare(tmp_path, {'doc.md': 2})
    target = tmp_path / 'saved.json'; chunk.rename(target)
    try: chunk.symlink_to(target)
    except OSError: pytest.skip('symlinks unavailable')
    with pytest.raises(ValueError): module.validate(tmp_path, manifest, tmp_path, 1)
