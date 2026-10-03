"""Offline coverage for the 2026-09-30 curated update; no live account calls."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SHEETS = ROOT / 'skills/knowledge-and-pm-integrations/lark-sheets/scripts'


def load_module(name: str, path: Path):
    assert path.is_file(), f'missing bundled dependency: {path}'
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_lark_default_selection_excludes_hidden_non_grid_and_unknown():
    module = load_module('lark_read_review', SHEETS / 'lark_sheet_read_cli.py')
    assert hasattr(module, 'visible_grid_selection')
    result = module.visible_grid_selection({'sheets': [
        {'sheet_id': 'hidden', 'resource_type': 'sheet', 'is_hidden': True},
        {'sheet_id': 'board', 'resource_type': 'bitable', 'is_hidden': False},
        {'sheet_id': 'unknown', 'resource_type': 'sheet'},
        {'sheet_id': 'visible', 'resource_type': 'sheet', 'is_hidden': False},
    ]})
    assert result['selected']['sheet_id'] == 'visible'
    assert {item['reason'] for item in result['excluded']} == {
        'hidden', 'non_grid', 'visibility_unknown',
    }
    assert result['ambiguous'] is False


def test_lark_multiple_visible_sheets_never_choose_first_by_index():
    module = load_module('lark_read_ambiguous', SHEETS / 'lark_sheet_read_cli.py')
    assert hasattr(module, 'visible_grid_selection')
    result = module.visible_grid_selection({'sheets': [
        {'sheet_id': 'b', 'resource_type': 'sheet', 'is_hidden': False, 'index': 0},
        {'sheet_id': 'a', 'resource_type': 'sheet', 'is_hidden': False, 'index': 1},
    ]})
    assert result['selected'] is None and result['ambiguous'] is True
    with pytest.raises(module.LarkCliError, match='not a grid'):
        module.visible_grid_selection({'sheets': [
            {'sheet_id': 'board', 'resource_type': 'bitable', 'is_hidden': False},
        ]}, sheet_id='board')


def test_lark_dataframe_helper_is_renamed_without_losing_legacy_import_path():
    assert (SHEETS / 'lark_sheets_df.py').is_file()
    assert (SHEETS / 'sheets_df.py').is_file()
    text = (SHEETS / 'lark_sheets_df.py').read_text()
    assert 'column labels collide after str() conversion' in text
    assert 'def df_to_sheet' in text and 'def sheet_to_df' in text


@pytest.mark.parametrize('skill,resource', [
    ('developer-engineering/neon-postgres', 'references/lakebase-search-drizzle.md'),
    ('security-and-reliability/gha-security-review', 'references/expression-injection.md'),
    ('security-and-reliability/security-review', 'references/authorization.md'),
    ('ai-workflow/security-and-hardening', 'references/hardening-patterns.md'),
])
def test_new_dependency_closure_is_bundled_and_owned(skill, resource):
    path = ROOT / 'skills' / skill / resource
    assert path.is_file()
    matches = []
    for mapping in (ROOT / 'docs/sources').glob('*.skills.json'):
        for entry in json.loads(mapping.read_text()).get('skills', []):
            for item in entry.get('managed_files', []):
                if item['path'] == path.relative_to(ROOT).as_posix():
                    matches.append((entry, item))
    assert len(matches) == 1
    entry, item = matches[0]
    assert item['owner'] == entry['normalized_slug']
    assert any(o.get('license') and not o['repo'].startswith('local-repo/')
               for o in entry['origins'])


def test_unavailable_source_artifacts_are_explicit_immutable_sidecars():
    mappings = [json.loads(p.read_text()) for p in (ROOT / 'docs/sources').glob('*.skills.json')]
    builder = next(e for m in mappings for e in m.get('skills', [])
                   if e.get('normalized_slug') == 'builder')
    archived = [o for o in builder['origins'] if o['sync_mode'] == 'archived']
    assert archived
    for origin in archived:
        assert origin['tracking']['channel'] == 'fixed_ref'
        assert origin['tracking']['ref'] == origin['tracking']['resolved_commit']
        assert len(origin['tracking']['resolved_commit']) == 40
        assert origin['license']
        assert all(a.get('type', 'file') == 'file' for a in origin['artifacts'])
        assert all(a['target'] != builder['repo_skill'] for a in origin['artifacts'])


def test_graphify_watch_quotes_both_interpreter_and_scan_root():
    text = (ROOT / 'skills/developer-engineering/graphify/references/add-watch.md').read_text()
    assert '"$(cat graphify-out/.graphify_python)" -m graphify.watch "$(cat graphify-out/.graphify_root)"' in text


@pytest.mark.parametrize('name', ['security-review', 'gha-security-review'])
def test_sentry_allowed_tools_use_upstream_space_separated_syntax(name):
    text = (ROOT / 'skills/security-and-reliability' / name / 'SKILL.md').read_text()
    assert 'Read, Grep, Glob, Bash, Task' not in text.split('---', 2)[1]
    assert 'Read Grep Glob Bash Task' in text.split('---', 2)[1]
