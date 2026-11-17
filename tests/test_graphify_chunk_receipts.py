import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/developer-engineering/graphify/scripts/validate_semantic_chunks.py'
spec = importlib.util.spec_from_file_location('graphify_receipts', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

MEDIA_SOURCES = {
    'paper.pdf': (
        b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
        b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n'
        b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] /Resources << >> >>\nendobj\n'
        b'xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n'
        b'0000000058 00000 n \n0000000115 00000 n \n'
        b'trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n201\n%%EOF\n'
    ),
    'image.png': bytes.fromhex(
        '89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c02'
        '0000000b4944415478da6364f80f00010501012718e3660000000049454e44ae426082'
    ),
}


def prepare(tmp_path, receipt, source_name='doc.md', source_bytes=None):
    if source_bytes is None:
        source_bytes = MEDIA_SOURCES.get(source_name, b'first\nsecond\n')
    (tmp_path / source_name).write_bytes(source_bytes)
    manifest = tmp_path / 'manifest.txt'; manifest.write_text(source_name + '\n')
    chunk = tmp_path / '.graphify_chunk_01.json'
    chunk.write_text(json.dumps({'nodes': [], 'edges': [], 'coverage': receipt}))
    return manifest, chunk


def test_complete_empty_extraction_is_valid(tmp_path):
    manifest, _ = prepare(tmp_path, {'doc.md': 2})
    assert module.validate(tmp_path, manifest, tmp_path, 1) == []


def test_empty_text_accepts_zero_coverage(tmp_path):
    manifest, _ = prepare(tmp_path, {'doc.md': 0}, source_bytes=b'')
    assert module.validate(tmp_path, manifest, tmp_path, 1) == []


@pytest.mark.parametrize('source_name', MEDIA_SOURCES)
def test_non_text_zero_coverage_cannot_pass(tmp_path, source_name):
    manifest, _ = prepare(tmp_path, {source_name: 0}, source_name)
    assert module.validate(tmp_path, manifest, tmp_path, 1) == [
        f'non-text coverage must be positive: {source_name}'
    ]


@pytest.mark.parametrize('source_name', MEDIA_SOURCES)
@pytest.mark.parametrize('coverage', [1, 17])
def test_non_text_positive_coverage_attestation_is_valid(tmp_path, source_name, coverage):
    manifest, _ = prepare(tmp_path, {source_name: coverage}, source_name)
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


@pytest.mark.parametrize('source_name, receipt, failure', [
    ('doc.md', {}, 'missing coverage: doc.md'),
    ('paper.pdf', {'paper.pdf': 0}, 'non-text coverage must be positive: paper.pdf'),
    ('image.png', {'image.png': 0}, 'non-text coverage must be positive: image.png'),
])
def test_cli_failure_preserves_existing_cache(tmp_path, source_name, receipt, failure):
    import subprocess
    import sys

    manifest, chunk = prepare(tmp_path, receipt, source_name)
    original_chunk = chunk.read_bytes()
    cache = tmp_path / '.graphify_cache.json'
    original = b'{"previous": "accepted extraction"}\n'
    cache.write_bytes(original)
    result = subprocess.run([sys.executable, str(SCRIPT), '--root', str(tmp_path),
        '--manifest', str(manifest), '--chunks-dir', str(tmp_path),
        '--expected-chunks', '1'], capture_output=True, text=True)
    assert result.returncode != 0
    assert json.loads(result.stdout) == {'ok': False, 'failures': [failure]}
    assert cache.read_bytes() == original
    assert chunk.read_bytes() == original_chunk
    assert not (tmp_path / '.graphify_semantic_new.json').exists()
