"""Offline CLI regression tests; all state is private to the task TMPDIR."""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile

import pytest

SKILL = Path(__file__).resolve().parents[1] / 'skills/office-white-collar/transcript-fixer'
CLI = SKILL / 'scripts/fix_transcription.py'


@pytest.fixture
def sandbox():
    with tempfile.TemporaryDirectory(prefix='transcript-preflight-', dir=os.environ['TMPDIR']) as root:
        yield Path(root).resolve()


def environment(root, **overrides):
    # Synthetic environment: never load real provider credentials/config.
    values = {'PATH': os.environ['PATH'], 'HOME': str(root / 'home'),
            'TMPDIR': str(root), 'PYTHONDONTWRITEBYTECODE': '1',
            'TRANSCRIPT_FIXER_CONFIG_DIR': str(root / 'selected'),
            'TRANSCRIPT_FIXER_ENABLE_LEARNING': '0', **overrides}
    return {name: value for name, value in values.items() if value is not None}


def run_cli(root, *args, **env):
    return subprocess.run([sys.executable, str(CLI), *args], env=environment(root, **env),
                          cwd=SKILL, capture_output=True, text=True)


def create_database(path, healthy=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        if healthy:
            conn.executescript((SKILL / 'scripts/core/schema.sql').read_text())
        else:
            conn.execute('CREATE TABLE sentinel(value TEXT)')
            conn.execute("INSERT INTO sentinel VALUES ('keep-existing-data')")
    conn.close()


def fingerprint(root):
    return {str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime_ns,
            hashlib.sha256(p.read_bytes()).hexdigest()) for p in root.rglob('*') if p.is_file()}


def test_selected_database_is_checked_and_default_is_untouched(sandbox):
    default = sandbox / 'home/.transcript-fixer/corrections.db'
    selected = sandbox / 'selected/corrections.db'
    create_database(default, healthy=False)
    create_database(selected)
    before = fingerprint(sandbox)
    result = run_cli(sandbox, '--validate')
    assert result.returncode == 0, result.stdout + result.stderr
    assert str(selected) in result.stdout
    assert 'All 8 tables present' in result.stdout
    assert fingerprint(sandbox) == before


def test_explicit_database_override_reports_missing_tables_without_repair(sandbox):
    selected = sandbox / 'custom dir/dictionary #1?.db'
    create_database(selected, healthy=False)
    create_database(sandbox / 'selected/corrections.db')
    before = fingerprint(sandbox)
    result = run_cli(sandbox, '--validate', TRANSCRIPT_FIXER_DB_PATH=str(selected))
    assert result.returncode == 1, result.stdout + result.stderr
    assert 'missing tables' in result.stdout
    assert str(selected) in result.stdout
    assert 'All 8 tables present' not in result.stdout
    assert fingerprint(sandbox) == before


def test_missing_database_is_failure_without_creating_anything(sandbox):
    before = fingerprint(sandbox)
    result = run_cli(sandbox, '--validate')
    assert result.returncode == 1
    assert 'Database not found' in result.stdout
    assert fingerprint(sandbox) == before
    assert not (sandbox / 'home').exists()
    assert not (sandbox / 'selected').exists()


@pytest.mark.parametrize('kind', ['corrupt', 'empty', 'directory'])
def test_invalid_database_never_becomes_healthy(sandbox, kind):
    db = sandbox / 'selected/corrections.db'
    db.parent.mkdir()
    if kind == 'directory':
        db.mkdir()
    else:
        db.write_bytes(b'not a sqlite database' if kind == 'corrupt' else b'')
    before = fingerprint(sandbox)
    result = run_cli(sandbox, '--validate')
    assert result.returncode == 1
    assert 'All 8 tables present' not in result.stdout
    assert fingerprint(sandbox) == before


@pytest.mark.parametrize('sidecar', ['-wal', '-shm', '-journal'])
def test_sidecars_are_explicitly_unverified_without_changes(sandbox, sidecar):
    db = sandbox / 'selected/corrections.db'
    create_database(db)
    Path(str(db) + sidecar).write_bytes(b'synthetic-sidecar-do-not-touch')
    before = fingerprint(sandbox)
    result = run_cli(sandbox, '--validate')
    assert result.returncode == 1
    assert 'not verified' in result.stdout
    assert fingerprint(sandbox) == before


def test_live_wal_with_committed_schema_is_not_ignored(sandbox):
    db = sandbox / 'selected/corrections.db'
    create_database(db)
    conn = sqlite3.connect(db)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('CREATE TABLE committed_in_wal(value TEXT)')
        conn.commit()
        assert Path(str(db) + '-wal').stat().st_size > 0
        before = fingerprint(sandbox)
        result = run_cli(sandbox, '--validate')
        assert result.returncode == 1
        assert 'not verified' in result.stdout
        assert 'All 8 tables present' not in result.stdout
        assert fingerprint(sandbox) == before
    finally:
        conn.close()


def test_checkpointed_wal_without_sidecars_is_checked_without_source_writes(sandbox):
    db = sandbox / 'selected/corrections.db'
    create_database(db)
    conn = sqlite3.connect(db)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.close()
    assert not Path(str(db) + '-wal').exists()
    before = fingerprint(sandbox)
    result = run_cli(sandbox, '--validate')
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'All 8 tables present' in result.stdout
    assert fingerprint(sandbox) == before


@pytest.mark.parametrize('mutation', ['database', 'sidecar'])
def test_snapshot_change_is_rejected_instead_of_reporting_stale_health(sandbox, mutation):
    db = sandbox / 'selected/corrections.db'
    create_database(db)
    # Inject an external-writer event at the copy boundary, then run the real CLI.
    runner = sandbox / 'writer_event_runner.py'
    runner.write_text('''import pathlib, runpy, shutil, sqlite3, sys
sys.path.insert(0, sys.argv.pop(1))
from utils import validation
original_copy = shutil.copyfile
mutation = sys.argv.pop(1)
def copy_and_change(source, target):
    result = original_copy(source, target)
    if mutation == 'database':
        conn = sqlite3.connect(source)
        conn.execute('CREATE TABLE concurrent_writer(value TEXT)')
        conn.commit()
        conn.close()
    else:
        pathlib.Path(str(source) + '-wal').write_bytes(b'concurrent-wal')
    return result
validation.shutil.copyfile = copy_and_change
runpy.run_path(sys.argv.pop(1), run_name='__main__')
''')
    result = subprocess.run([sys.executable, str(runner), str(SKILL / 'scripts'), mutation,
                             str(CLI), '--validate'], env=environment(sandbox),
                            capture_output=True, text=True)
    assert result.returncode == 1, result.stdout + result.stderr
    assert 'not verified' in result.stdout, result.stderr
    assert 'All 8 tables present' not in result.stdout


def test_database_from_selected_config_instance_is_used(sandbox):
    db = sandbox / 'configured/selected.db'
    create_database(db, healthy=False)
    config = sandbox / 'configuration.json'
    config.write_text(json.dumps({'database': {'path': str(db)},
                                  'paths': {'config_dir': str(db.parent)}}))
    before = fingerprint(sandbox)
    code = ('import runpy,sys; from pathlib import Path; sys.path.insert(0,sys.argv.pop(1)); '
            'from utils.config import Config,set_config; '
            'set_config(Config.from_file(Path(sys.argv.pop(1)))); '
            "runpy.run_path(sys.argv.pop(1),run_name='__main__')")
    result = subprocess.run([sys.executable, '-c', code, str(SKILL / 'scripts'), str(config),
                             str(CLI), '--validate'], env=environment(sandbox),
                            capture_output=True, text=True)
    assert result.returncode == 1, result.stdout + result.stderr
    assert str(db) in result.stdout and 'missing tables' in result.stdout
    assert fingerprint(sandbox) == before


def presence_commands():
    for doc in sorted((SKILL / 'references').glob('*.md')):
        for line in doc.read_text().splitlines():
            if "python -c 'import os, sys;" in line and 'GLM_API_KEY' in line:
                yield doc.name, line


@pytest.mark.parametrize('key,expected', [('synthetic-preflight-secret-only', 0), ('', 1), (None, 1)])
@pytest.mark.parametrize('trace', [False, True])
def test_all_documented_presence_checks_hide_values_under_shell_trace(sandbox, key, expected, trace):
    commands = list(presence_commands())
    assert {'workflow_guide.md', 'troubleshooting.md'} <= {name for name, _ in commands}
    for name, command in commands:
        result = subprocess.run(['/bin/sh', *(['-x'] if trace else []), '-c', command],
                                env=environment(sandbox, GLM_API_KEY=key),
                                capture_output=True, text=True)
        assert result.returncode == expected, (name, result.stdout, result.stderr)
        assert 'synthetic-preflight-secret-only' not in result.stdout + result.stderr
    for doc in [SKILL / 'SKILL.md', *(SKILL / 'references').glob('*.md')]:
        assert not re.search(r'(?:echo|printenv|\[\s+-[nz])[^\n]*\$\{?GLM_API_KEY', doc.read_text()), doc


@pytest.mark.parametrize('healthy', [True, False])
@pytest.mark.parametrize('key', ['synthetic-preflight-secret-only', ''])
@pytest.mark.parametrize('trace', [False, True])
def test_complete_documented_preflight_runs_actual_validate(sandbox, healthy, key, trace):
    db = sandbox / 'selected/corrections.db'
    if healthy:
        create_database(db)
    bindir = sandbox / 'bin'
    bindir.mkdir()
    uv = bindir / 'uv'
    # Only replace the external uv launcher, never the validate handler.
    uv.write_text(f'#!{sys.executable}\n' + '''import os, sys
assert sys.argv[1] == 'run'
os.execv(sys.executable, [sys.executable, *sys.argv[2:]])
''')
    uv.chmod(0o755)
    before = fingerprint(sandbox)
    section = (SKILL / 'references/workflow_guide.md').read_text().split('**Quick validation**:', 1)[1]
    command = re.search(r'```bash\n(.*?)\n```', section, re.S).group(1)
    result = subprocess.run(['/bin/sh', *(['-x'] if trace else []), '-c', command], cwd=SKILL,
                            env=environment(sandbox, GLM_API_KEY=key,
                                PATH=str(bindir) + os.pathsep + os.environ['PATH']),
                            capture_output=True, text=True)
    assert result.returncode == (0 if healthy and key else 1), result.stdout + result.stderr
    assert str(db) in result.stdout
    assert ('All 8 tables present' in result.stdout) == healthy
    assert 'synthetic-preflight-secret-only' not in result.stdout + result.stderr
    assert fingerprint(sandbox) == before


def test_stage1_and_missing_key_match_documented_outputs_and_exit(sandbox):
    original = sandbox / 'meeting.md'
    original.write_text('今天讨论具身智能。\n')
    manifest = sandbox / 'manifest.json'
    result = run_cli(sandbox, '--input', str(original), '--stage', '1',
                     TRANSCRIPT_FIXER_OUTPUT_MANIFEST=str(manifest))
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(manifest.read_text()) == {'outputs': [str(sandbox / 'meeting_stage1.md')]}
    assert not (sandbox / 'selected').exists()
    result = run_cli(sandbox, '--input', str(original), '--stage', '2',
                     TRANSCRIPT_FIXER_OUTPUT_MANIFEST=str(manifest))
    assert result.returncode == 1
    assert 'GLM_API_KEY' in result.stdout
    assert not (sandbox / 'meeting_stage2.md').exists()
    assert original.read_text() == '今天讨论具身智能。\n'
    assert json.loads(manifest.read_text()) == {'outputs': [str(sandbox / 'meeting_stage1.md')]}


@pytest.mark.parametrize('provider_mode', ['success', 'fail'])
def test_stage2_cumulative_output_and_failure_receipt_with_synthetic_provider(sandbox, provider_mode):
    db = sandbox / 'selected/corrections.db'
    create_database(db)
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO corrections(from_text,to_text,domain,source) "
                 "VALUES ('巨升智能','具身智能','general','manual')")
    conn.commit()
    conn.close()
    original = sandbox / 'meeting.md'
    original.write_text('今天讨论巨升智能。\n')
    stage2 = sandbox / 'meeting_stage2.md'
    stage2.write_text('previous-output-must-survive-failure')
    runner = sandbox / 'synthetic_provider.py'
    runner.write_text('''import os, pathlib, runpy, sys
sys.path.insert(0, sys.argv.pop(1))
from core.ai_processor_async import AIProcessorAsync
async def request(self, chunk, context, model):
    assert '具身智能' in chunk and '巨升智能' not in chunk
    with pathlib.Path(os.environ['ATTEMPTS']).open('a') as log:
        log.write(model + '\\n')
    if os.environ['PROVIDER_MODE'] == 'fail':
        raise ValueError('synthetic-provider-unavailable')
    return chunk
AIProcessorAsync._process_chunk_async = request
runpy.run_path(sys.argv.pop(1), run_name='__main__')
''')
    manifest, attempts = sandbox / 'outputs.json', sandbox / 'attempts.txt'
    result = subprocess.run([sys.executable, str(runner), str(SKILL / 'scripts'), str(CLI),
                             '--input', str(original), '--stage', '2'],
                            env=environment(sandbox, GLM_API_KEY='synthetic-only',
                                TRANSCRIPT_FIXER_OUTPUT_MANIFEST=str(manifest),
                                ATTEMPTS=str(attempts), PROVIDER_MODE=provider_mode),
                            capture_output=True, text=True)
    outputs = json.loads(manifest.read_text())['outputs']
    assert (sandbox / 'meeting_stage1.md').read_text() == '今天讨论具身智能。\n'
    if provider_mode == 'success':
        assert result.returncode == 0, result.stdout + result.stderr
        assert '具身智能' in stage2.read_text()
        assert outputs == [str(sandbox / 'meeting_stage1.md'), str(stage2)]
        assert len(attempts.read_text().splitlines()) == 1
    else:
        assert result.returncode == 1, result.stdout + result.stderr
        assert stage2.read_text() == 'previous-output-must-survive-failure'
        assert outputs == [str(sandbox / 'meeting_stage1.md')]
        assert len(attempts.read_text().splitlines()) == 2


def test_real_diff_entrypoint_generates_only_requested_html(sandbox):
    original, corrected = sandbox / 'original.md', sandbox / 'corrected.md'
    original.write_text('巨升智能\n')
    corrected.write_text('具身智能\n')
    html = sandbox / 'review.html'
    result = subprocess.run([sys.executable, str(SKILL / 'scripts/generate_word_diff.py'),
                             str(original), str(corrected), str(html)],
                            env=environment(sandbox), capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert html.is_file() and '<html' in html.read_text()


@pytest.mark.parametrize('child_exit', [0, 7])
def test_wrapper_passes_declared_dependencies_and_preserves_child_failure(sandbox, child_exit):
    # Real wrapper + fake external uv: no install, network, provider, or browser.
    bindir = sandbox / 'bin'
    bindir.mkdir()
    uv = bindir / 'uv'
    uv.write_text(f'#!{sys.executable}\n' + '''import json, os, pathlib, sys
pathlib.Path(os.environ['CAPTURE']).write_text(json.dumps(sys.argv[1:]))
args = sys.argv[1:]
source = pathlib.Path(args[args.index('--input') + 1])
output = pathlib.Path(args[args.index('--output') + 1]) / (source.stem + '_stage1.md')
output.write_text(source.read_text())
pathlib.Path(os.environ['TRANSCRIPT_FIXER_OUTPUT_MANIFEST']).write_text(json.dumps({'outputs':[str(output)]}))
sys.exit(int(os.environ['CHILD_EXIT']))
''')
    uv.chmod(0o755)
    original = sandbox / 'meeting.md'
    original.write_text('合成文本\n')
    capture = sandbox / 'uv-args.json'
    result = subprocess.run([sys.executable, str(SKILL / 'scripts/fix_transcript_enhanced.py'),
                             str(original), '--stage', '1'], cwd=sandbox,
                            env=environment(sandbox, PATH=str(bindir) + os.pathsep + os.environ['PATH'],
                                            CAPTURE=str(capture), CHILD_EXIT=str(child_exit)),
                            capture_output=True, text=True)
    assert result.returncode == child_exit, result.stdout + result.stderr
    args = json.loads(capture.read_text())
    requirements = [line.strip() for line in (SKILL / 'requirements.txt').read_text().splitlines()
                    if line.strip() and not line.startswith('#')]
    assert [args[i + 1] for i, arg in enumerate(args) if arg == '--with'] == requirements
    assert 'h2' not in ' '.join(requirements)
    assert 'Opening HTML' not in result.stdout
