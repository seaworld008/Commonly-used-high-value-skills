"""Offline behavioral regressions for the final upstream and PR review pass."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SHEETS = ROOT / 'skills/knowledge-and-pm-integrations/lark-sheets/scripts'

@pytest.fixture
def quality(monkeypatch):
    monkeypatch.syspath_prepend(str(SHEETS))
    spec = importlib.util.spec_from_file_location('quality_followup', SHEETS / 'lark_chart_quality_check.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_quality(module, monkeypatch, sheets, explicit=None):
    monkeypatch.setattr(module, 'parse_args', lambda: SimpleNamespace(
        sheet_id='spreadsheet-token', worksheet_id=explicit, timeout=10, sample_limit=10))
    monkeypatch.setattr(module, 'run_sheets', lambda *a, **kw: {'data': {'sheets': sheets}})
    checked = []
    def check(locator, sheet, **kw):
        checked.append(sheet['sheet_id'])
        return {'sheet_name': '', 'sheet_id': sheet['sheet_id'], 'chart_count': 0,
                'issue_count': 0, 'unverifiable_count': 0, 'warnings': []}
    monkeypatch.setattr(module, 'check_sheet', check)
    module.main()
    return checked


def test_chart_default_checks_only_visible_grid_sheets(quality, monkeypatch):
    assert run_quality(quality, monkeypatch, [
        {'sheet_id': 'grid', 'resource_type': 'sheet', 'is_hidden': False},
        {'sheet_id': 'board', 'resource_type': 'bitable', 'is_hidden': False},
        {'sheet_id': 'unknown-type', 'resource_type': '#UNSUPPORTED_TYPE', 'is_hidden': False},
        {'sheet_id': 'hidden', 'resource_type': 'sheet', 'is_hidden': True},
        {'sheet_id': 'unknown-visibility', 'resource_type': 'sheet'},
        {'sheet_id': 'legacy', 'row_count': 5, 'column_count': 5, 'is_hidden': False},
    ]) == ['grid', 'legacy']


def test_chart_explicit_non_grid_is_rejected_before_read(quality, monkeypatch, capsys):
    with pytest.raises(SystemExit) as error:
        run_quality(quality, monkeypatch, [
            {'sheet_id': 'board', 'resource_type': 'bitable', 'is_hidden': False},
        ], 'board')
    assert error.value.code == 1
    assert 'not a grid' in json.loads(capsys.readouterr().out)['error']


def test_chart_explicit_hidden_grid_is_permitted(quality, monkeypatch):
    assert run_quality(quality, monkeypatch, [
        {'sheet_id': 'grid', 'resource_type': 'sheet', 'is_hidden': True},
    ], 'grid') == ['grid']


@pytest.mark.parametrize('problem', ['lark-cli timed out after 10s',
    'lark-cli stdout was not JSON: truncated', '{"error":{"subtype":"timeout"}}'])
def test_chart_transient_read_retries_once(quality, monkeypatch, problem):
    assert hasattr(quality, '_run_sheets_once')
    calls = []
    def read(*a, **kw):
        calls.append((a, kw))
        if len(calls) == 1:
            raise quality.LarkCliError(problem)
        return {'ok': True, 'data': {}}
    monkeypatch.setattr(quality, '_run_sheets_once', read)
    assert quality.run_sheets('+chart-list', spreadsheet_token='redacted') == {'ok': True, 'data': {}}
    assert len(calls) == 2 and calls[0] == calls[1]


@pytest.mark.parametrize('problem,shortcut,count', [
    ('lark-cli timed out after 10s', '+chart-list', 2),
    ('lark-cli stdout was not JSON: truncated', '+workbook-info', 2),
    ('Permission denied', '+chart-list', 1),
    ('lark-cli not found', '+chart-list', 1),
    ('lark-cli timed out after 10s', '+table-set', 1),
])
def test_chart_retry_is_bounded_and_never_retries_writes(quality, monkeypatch, problem, shortcut, count):
    assert hasattr(quality, '_run_sheets_once')
    calls = []
    def read(*a, **kw):
        calls.append(1)
        raise quality.LarkCliError(problem)
    monkeypatch.setattr(quality, '_run_sheets_once', read)
    with pytest.raises(quality.LarkCliError):
        quality.run_sheets(shortcut, spreadsheet_token='redacted')
    assert len(calls) == count


def test_idempotency_example_rethrows_the_original_non_unique_error():
    text = (ROOT / 'skills/ai-workflow/api-and-interface-design/SKILL.md').read_text()
    code = text.split('// ✓ let the unique constraint pick the winner\n', 1)[1].split('```', 1)[0]
    harness = '''const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
const expected = new Error('test storage failure');
const run = new AsyncFunction('db','key','requestHash','isUniqueViolation','replayOrReject','chargeCard','amount', JSON.parse(process.argv[1]));
run({insert: async()=>{throw expected}},'k','h',()=>false,()=>{},()=>{},1)
.then(()=>{process.exitCode=1}, e=>{if(e!==expected) process.exitCode=1});'''
    result = subprocess.run(['node', '-e', harness, json.dumps(code)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_prisma_example_requires_a_verified_rollback_runbook():
    text = (ROOT / 'skills/ai-workflow/shipping-and-launch/SKILL.md').read_text()
    assert 'npx prisma migrate rollback' not in text
    assert '<verified command or runbook link>' in text


def test_performance_examples_have_a_resolvable_local_reference():
    root = ROOT / 'skills/ai-workflow/performance-optimization'
    text = (root / 'SKILL.md').read_text()
    assert '(references/optimization-patterns.md)' in text
    reference = (root / 'references/optimization-patterns.md').read_text()
    assert '../../../references/' not in reference
    assert 'performance-checklist.md#caching-strategies' in reference
    assert (root / 'references/performance-checklist.md').is_file()


def test_xquik_read_helper_never_follows_credentialed_redirects(monkeypatch):
    path = ROOT / 'skills/growth-operations-xiaohongshu/x-twitter-scraper/references/reads.md'
    blocks = re.findall(r'```python\n(.*?)\n```', path.read_text(), re.S)
    code = next(b for b in blocks if 'def get_json(' in b)
    calls = []
    response = SimpleNamespace(status_code=302, ok=True, headers={}, json=lambda: {'location': 'untrusted'})
    def get(*a, **kw):
        calls.append((a, kw))
        return response
    monkeypatch.setitem(sys.modules, 'requests', SimpleNamespace(
        get=get, ConnectionError=ConnectionError, Timeout=TimeoutError,
        exceptions=SimpleNamespace(ChunkedEncodingError=OSError)))
    monkeypatch.setenv('XQUIK_API_KEY', 'test-only-not-a-secret')
    namespace = {}
    exec(compile(code, str(path), 'exec'), namespace)
    with pytest.raises(namespace['XquikError']) as error:
        namespace['get_json']('/x/tweets/search', budget_s=0)
    assert error.value.status == 302
    assert len(calls) == 1 and calls[0][1]['allow_redirects'] is False
