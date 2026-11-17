"""Exercise the documented Graphify merge steps and the token generator CLI locally."""

import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
GRAPHIFY = ROOT / 'skills/developer-engineering/graphify'
VALIDATOR = GRAPHIFY / 'scripts/validate_semantic_chunks.py'
TOKENS = ROOT / 'skills/product-design/ui-design-system/scripts/design_token_generator.py'
PNG = bytes.fromhex(
    '89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c02'
    '0000000b4944415478da6364f80f00010501012718e3660000000049454e44ae426082'
)


def run_step(document, marker):
    # Execute just the named inline Python program, without invoking the shell.
    blocks = re.findall(r'```bash\n(.*?)\n```', (GRAPHIFY / document).read_text(), re.S)
    block, = [block for block in blocks if marker in block]
    args = shlex.split(block)
    assert args[-2] == '-c'
    exec(compile(args[-1], str(GRAPHIFY / document), 'exec'), {})


def chunk(name, count=1):
    return {'coverage': {name: count}, 'nodes': [], 'edges': []}


def extraction(name):
    node = {'id': 'b_主题', 'label': '主题', 'file_type': 'concept', 'source_file': name}
    edge = {'source': 'b_主题', 'target': 'cached_entity', 'relation': 'references',
            'confidence': 'EXTRACTED', 'confidence_score': 1, 'weight': 1, 'source_file': name}
    group = {'id': 'group', 'label': 'Group', 'nodes': ['b_主题', 'cached_entity', 'ast_entity'],
             'relation': 'form', 'confidence': 'INFERRED', 'confidence_score': 0.75, 'source_file': name}
    return {**chunk(name), 'nodes': [node], 'edges': [edge], 'hyperedges': [group], 'input_tokens': 12}


@pytest.fixture
def workflow(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / 'graphify-out'
    out.mkdir()
    old = b'previous accepted result'
    cache = out / 'cache-store'
    graph = out / 'graph.json'
    semantic = out / '.graphify_semantic.json'
    for path in (cache, graph, semantic):
        path.write_bytes(old)
    (out / '.graphify_root').write_text(str(tmp_path))
    (out / '.graphify_ast.json').write_text(json.dumps({'nodes': [{'id': 'ast_entity'}], 'edges': []}))
    saves = []

    def save(nodes, edges, groups, **kwargs):
        saves.append(kwargs['allowed_source_files'])
        cache.write_text(json.dumps([nodes, edges, groups]))
        return len(kwargs['allowed_source_files'])

    def lookup(files, **kwargs):
        assert 'cached.md' in files
        return [{'id': 'cached_entity'}], [], [], [name for name in files if name != 'cached.md']

    cache_api = SimpleNamespace(check_semantic_cache=lookup, save_semantic_cache=save)
    monkeypatch.setitem(sys.modules, 'graphify.cache', cache_api)

    def run(files, assignments, chunks, *, with_plan=False):
        (tmp_path / 'cached.md').write_text('previously extracted')
        detected = {'document': ['cached.md'], 'image': []}
        for name, data in files.items():
            (tmp_path / name).write_bytes(data)
            detected['image' if name.endswith('.png') else 'document'].append(name)
        (out / '.graphify_detect.json').write_text(json.dumps({'files': detected}))
        run_step('EXTENDED.md', 'from graphify.cache import check_semantic_cache')
        for index, payload in enumerate(chunks, 1):
            path = out / f'.graphify_chunk_{index:02d}.json'
            path.write_text(payload if isinstance(payload, str) else json.dumps(payload))
        cmd = [sys.executable, str(VALIDATOR), '--root', str(tmp_path), '--manifest',
               str(out / '.graphify_uncached.txt'), '--chunks-dir', str(out),
               '--expected-chunks', str(len(assignments))]
        if with_plan:
            plan = tmp_path / 'assignments.json'
            plan.write_text(json.dumps(assignments))
            cmd.extend(['--chunk-plan', str(plan)])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        new = out / '.graphify_semantic_new.json'
        merged = out / '.graphify_extract.json'
        if result.returncode:
            assert json.loads(result.stdout or result.stderr)['ok'] is False
            assert not saves
            assert all(path.read_bytes() == old for path in (cache, graph, semantic))
            assert not new.exists() and not merged.exists()
            return result

        assert json.loads(result.stdout)['ok'] is True
        run_step('EXTENDED.md', 'chunks = sorted(glob.glob')
        run_step('EXTENDED.md', 'from graphify.cache import save_semantic_cache')
        run_step('EXTENDED.md', 'deduped = []')
        run_step('SKILL.md', 'merged_nodes = list(ast')
        # Stand in for graphify.build/export at the final write boundary.
        graph.write_bytes(merged.read_bytes())
        assert saves == [list(files)]
        assert new.exists() and semantic.read_bytes() != old
        return result

    return run


@pytest.mark.parametrize('first_count', [0, 1])
def test_overlapping_png_receipts_stop_before_any_write(workflow, first_count):
    second = chunk('b.png')
    second['coverage']['a.png'] = 1
    result = workflow({'a.png': PNG, 'b.png': PNG}, [['a.png'], ['b.png']],
                      [chunk('a.png', first_count), second])
    assert result.returncode != 0


def test_duplicate_key_within_receipt_is_rejected(workflow):
    raw = '{"nodes":[],"edges":[],"coverage":{"a.png":0,"a.png":1}}'
    assert workflow({'a.png': PNG}, [['a.png']], [raw]).returncode != 0


def test_trusted_chunk_plan_detects_swapped_exclusive_receipts(workflow):
    assert workflow({'a.png': PNG, 'b.png': PNG}, [['a.png'], ['b.png']],
                    [chunk('b.png'), chunk('a.png')], with_plan=True).returncode != 0


def test_empty_chunk_cannot_transfer_its_work_to_another(workflow):
    second = chunk('b.md')
    second['coverage']['a.md'] = 1
    assert workflow({'a.md': b'first', 'b.md': b'second'}, [['a.md'], ['b.md']],
                    [dict(chunk('a.md'), coverage={}), second]).returncode != 0


@pytest.mark.parametrize('with_plan', [True, False])
def test_exclusive_media_receipts_with_empty_extraction_can_commit(workflow, with_plan):
    assert workflow({'a.png': PNG, 'b.png': PNG}, [['a.png'], ['b.png']],
                    [chunk('a.png'), chunk('b.png')], with_plan=with_plan).returncode == 0


def test_empty_text_and_cross_tier_references_survive_merge(workflow, tmp_path):
    record = extraction('b.md')
    assert workflow({'a.md': b'', 'b.md': b'one\n'}, [['a.md'], ['b.md']],
                    [chunk('a.md', 0), record], with_plan=True).returncode == 0
    out = tmp_path / 'graphify-out'
    assert json.loads((out / 'cache-store').read_bytes()) == [
        record[key] for key in ('nodes', 'edges', 'hyperedges')
    ]
    graph = json.loads((out / 'graph.json').read_bytes())
    assert [item['id'] for item in graph['nodes']] == ['ast_entity', 'cached_entity', 'b_主题']
    assert graph['edges'] == [dict(record['edges'][0], _origin='semantic')]
    assert graph['hyperedges'] == record['hyperedges']
    assert graph['input_tokens'] == 12


@pytest.mark.parametrize('collection, field, value', [
    ('nodes', None, {}), ('nodes', 'id', ''), ('nodes', 'id', []), ('nodes', 'id', 'bad/id'),
    ('nodes', 'label', '  '), ('nodes', 'file_type', 'generic'), ('nodes', 'source_file', 'a.md'),
    ('edges', None, {}), ('edges', 'source', None), ('edges', 'target', {}),
    ('edges', 'relation', ''), ('edges', 'confidence', 'unknown'), ('edges', 'confidence_score', True),
    ('edges', 'weight', '1'), ('edges', 'source_file', 'a.md'),
    ('hyperedges', None, {}), ('hyperedges', 'id', 1), ('hyperedges', 'label', ''),
    ('hyperedges', 'relation', ''), ('hyperedges', 'nodes', ['a', 'b', 'b']),
    ('hyperedges', 'nodes', ['a', 'b', {}]), ('hyperedges', 'source_file', 'a.md'),
])
def test_malformed_second_chunk_blocks_all_writes(workflow, collection, field, value):
    second = extraction('b.md')
    if field is None:
        second[collection] = [value]
    else:
        second[collection][0][field] = value
    assert workflow({'a.md': b'first', 'b.md': b'second'}, [['a.md'], ['b.md']],
                    [chunk('a.md'), second]).returncode != 0


@pytest.mark.parametrize('invalid', ['duplicate_id', 'input_tokens'])
def test_unmergeable_records_fail_at_the_receipt_gate(workflow, invalid):
    first, second = extraction('a.md'), extraction('b.md')
    first.pop('hyperedges')
    if invalid == 'input_tokens':
        first['nodes'][0]['id'] = 'a_主题'
        second['input_tokens'] = '12'
    assert workflow({'a.md': b'first', 'b.md': b'second'}, [['a.md'], ['b.md']],
                    [first, second]).returncode != 0


@pytest.mark.parametrize('fmt', ['css', 'json', 'scss'])
@pytest.mark.parametrize('color', ['#aB01cD', 'aB01cD'])
def test_valid_color_exports_keep_hex_value(tmp_path, fmt, color):
    result = subprocess.run([sys.executable, TOKENS, color, 'modern', fmt], cwd=tmp_path,
                            capture_output=True, text=True, check=True, timeout=10)
    if fmt == 'json':
        assert json.loads(result.stdout)['colors']['primary']['DEFAULT'] == '#aB01cD'
    else:
        prefix = '--' if fmt == 'css' else '$'
        assert f'{prefix}colors-primary-DEFAULT: #aB01cD;' in result.stdout


@pytest.mark.parametrize('color', ['#abcdef; $sample: 1', '#abcdef00', '##abcdef', '#abc',
                                   '#abcdeg', '#abcdef\n', ' abcdef'])
def test_invalid_color_emits_no_data(tmp_path, color):
    result = subprocess.run([sys.executable, TOKENS, color, 'modern', 'scss'], cwd=tmp_path,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert 'brand_color' in result.stderr
    assert result.stdout == ''
    assert not list(tmp_path.iterdir())


def test_invalid_scss_cannot_write_to_existing_output_stream(tmp_path):
    artifact = tmp_path / 'tokens.scss'
    artifact.write_bytes(b'previous stylesheet')
    with artifact.open('r+b') as output:
        result = subprocess.run([sys.executable, TOKENS, '#abcdef; $sample: 1', 'modern', 'scss'],
                                cwd=tmp_path, stdout=output, stderr=subprocess.PIPE, timeout=10)
        assert result.returncode != 0
        assert output.tell() == 0
    assert artifact.read_bytes() == b'previous stylesheet'
