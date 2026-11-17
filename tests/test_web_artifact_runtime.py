"""Offline CLI regressions, written locally; no upstream test code copied.

All projects, command doubles, logs and scratch data live below task TMPDIR.
Real pnpm, network installation, servers and browsers are never invoked.
"""
import base64
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'skills/developer-engineering/web-artifacts-builder/scripts'
NODE = shutil.which('node')
NOTICES = {
    'LICENSE.txt': b'Apache notice\r\nCopyright upstream\n',
    'THIRD_PARTY_NOTICES.md': b'Upstream notices\x00\xff\n</template><script>throw "injected"</script>',
    'LICENSE.shadcn.txt': 'MIT\nCopyright shadcn\n中文通知'.encode(),
}
DOC = '<!doctype html><html><head><title>New</title></head><body><div id="root">new app</div>{}</body></html>'


@pytest.fixture
def sandbox():
    assert NODE, 'Node is required for these offline runtime tests'
    task_tmp = os.environ.get('TMPDIR')
    assert task_tmp and Path(task_tmp).is_dir(), 'Use an existing task-specific TMPDIR'
    with tempfile.TemporaryDirectory(prefix='artifact-tests-', dir=task_tmp) as directory:
        root = Path(directory)
        scripts = root / 'skill/scripts'
        scripts.mkdir(parents=True)
        for name in ('init-artifact.sh', 'bundle-artifact.sh', 'artifact-runtime.mjs', 'collect-runtime-notices.mjs', 'runtime-license-notices.json', 'template-pnpm-lock.yaml', 'shadcn-components.tar.gz'):
            shutil.copyfile(SOURCE / name, scripts / name)
        shutil.copytree(SOURCE / 'runtime-scrollbar', scripts / 'runtime-scrollbar')
        for name, content in NOTICES.items():
            (scripts.parent / name).write_bytes(content)
        bin_dir = root / 'bin'
        bin_dir.mkdir()
        node = bin_dir / 'node'
        node.write_text('#!/bin/bash\nif [ "$1" = "--version" ]; then printf "%s\\n" "${TEST_NODE_VERSION:-v22.12.0}"; else exec ' +
                        "'" + NODE.replace("'", "'\\''") + "'" + ' "$@"; fi\n')
        node.chmod(0o755)
        pnpm = bin_dir / 'pnpm'
        pnpm.write_text('#!' + sys.executable + '\n' + r'''
import json, os, pathlib, sys
args = sys.argv[1:]
mode = os.environ.get('TEST_MODE', '')
with open(os.environ['TEST_CALLS'], 'a') as stream:
    stream.write(json.dumps({'args': args, 'cwd': os.getcwd()}) + '\n')
doc = '<!doctype html><html><head><title>New</title></head><body><div id="root">new app</div>{}</body></html>'
if args[0] == 'install':
    if mode == 'install-fail': sys.exit(4)
    package = json.loads(pathlib.Path('package.json').read_text())
    for name, version in package.get('dependencies', {}).items():
        folder = pathlib.Path('node_modules') / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'package.json').write_text(json.dumps({'name':name,'version':version,'license':'MIT'}))
        (folder / 'LICENSE').write_text('Synthetic installed dependency notice, never distributed as real package evidence.')
elif args[0] == 'add':
    if mode == 'install-fail': sys.exit(4)
elif args[:3] == ['exec', 'parcel', 'build']:
    dist = pathlib.Path(args[args.index('--dist-dir') + 1])
    dist.mkdir()
    (dist / 'app.js').write_text('window.artifactNew = true;')
    (dist / 'index.html').write_text(doc.format('<script src="app.js"></script>'))
    if mode == 'build-fail': sys.exit(7)
    if mode == 'build-empty': (dist / 'index.html').write_text('')
    if mode == 'build-invalid': (dist / 'index.html').write_text('not an html document')
    if mode == 'build-missing': (dist / 'index.html').unlink()
elif args[:2] == ['exec', 'html-inline']:
    source = pathlib.Path(args[2])
    assert source.is_relative_to(pathlib.Path.cwd())
    assert source.name == 'index.html' and source.parent.name == 'dist'
    assert source.is_file()
    if mode == 'inline-fail':
        print('<html>partial output')
        sys.exit(9)
    if mode == 'inline-empty': sys.exit(0)
    if mode == 'inline-whitespace':
        print('   ')
        sys.exit(0)
    script = '<script>window.artifactNew = true; const text = "</template></body><script>";</script>'
    if mode == 'inline-resource': script = '<script src="app.js"></script>'
    if mode == 'inline-style-resource': script = '<style>body{background:url(./asset.png)}</style>'
    if mode == 'inline-style-data': script = '<style>body{background:url("data:image/png;base64,YQ==")}</style>'
    if mode == 'inline-asset': script = '<script>new URL("./app.js", import.meta.url)</script>'
    if mode == 'inline-invalid':
        print('<html><body>missing closing tags')
        sys.exit(0)
    print(doc.format(script))
else:
    raise AssertionError('Unexpected command: ' + repr(args))
''')
        pnpm.chmod(0o755)
        npm = bin_dir / 'npm'
        npm.write_text('#!/bin/bash\nprintf "unexpected npm invocation" >> "$TEST_CALLS"\nexit 99\n')
        npm.chmod(0o755)
        env = {**os.environ, 'PATH': str(bin_dir) + ':/usr/bin:/bin',
               'TMPDIR': str(root), 'TEST_CALLS': str(root / 'calls.jsonl')}
        yield root, scripts, env


def cli(sandbox, mode, *args, cwd=None, **environment):
    root, scripts, env = sandbox
    return subprocess.run(['/bin/bash', str(scripts / f'{mode}-artifact.sh'), *map(str, args)],
                          cwd=cwd or root, env={**env, **environment}, text=True,
                          capture_output=True, timeout=30)


def calls(sandbox):
    log = Path(sandbox[2]['TEST_CALLS'])
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def project(sandbox):
    root, _, _ = sandbox
    folder = root / 'project with 空格'
    folder.mkdir()
    (folder / 'package.json').write_text('{"name":"fixture","private":true}')
    (folder / 'index.html').write_text(DOC.format('<script src="src/main.tsx"></script>'))
    (folder / 'bundle.html').write_bytes(b'old html\x00unchanged')
    (folder / 'dist').mkdir()
    (folder / 'dist/index.html').write_bytes(b'old dist')
    (folder / 'dist/old.js').write_bytes(b'old js')
    for name, content in NOTICES.items():
        (folder / name).write_bytes(content)
    return folder


def assert_old_delivery(folder):
    assert (folder / 'bundle.html').read_bytes() == b'old html\x00unchanged'
    assert (folder / 'dist/index.html').read_bytes() == b'old dist'
    assert (folder / 'dist/old.js').read_bytes() == b'old js'
    assert not list(folder.glob('.artifact-build-*'))


def test_missing_pnpm_never_installs_global_tools(sandbox):
    root, _, _ = sandbox
    (root / 'bin/pnpm').unlink()
    result = cli(sandbox, 'init', 'new')
    assert result.returncode != 0 and 'pnpm is required' in result.stderr
    assert not calls(sandbox) and not (root / 'new').exists()
    folder = project(sandbox)
    result = cli(sandbox, 'bundle', cwd=folder)
    assert result.returncode != 0 and 'pnpm is required' in result.stderr
    assert_old_delivery(folder)
    assert not calls(sandbox)


@pytest.mark.parametrize('version', ['v18.20.8', 'v20.18.3', 'v21.7.3', 'v22.11.0'])
def test_unsupported_engines_fail_before_install(sandbox, version):
    root, _, _ = sandbox
    result = cli(sandbox, 'init', 'new', TEST_NODE_VERSION=version)
    assert result.returncode != 0 and 'unsupported' in result.stderr
    assert not calls(sandbox) and not (root / 'new').exists()
    folder = project(sandbox)
    result = cli(sandbox, 'bundle', cwd=folder, TEST_NODE_VERSION=version)
    assert result.returncode != 0 and 'unsupported' in result.stderr
    assert_old_delivery(folder)


@pytest.mark.parametrize('kind', ['nonempty', 'file', 'symlink'])
def test_existing_targets_are_preserved(sandbox, kind):
    root, _, _ = sandbox
    target = root / 'existing'
    if kind == 'nonempty':
        target.mkdir()
        (target / '.hidden').write_text('user data')
    elif kind == 'file':
        target.write_text('user data')
    else:
        (root / 'user-dir').mkdir()
        target.symlink_to(root / 'user-dir')
    result = cli(sandbox, 'init', target)
    assert result.returncode != 0 and 'Refusing to overwrite' in result.stderr
    assert not calls(sandbox)
    if kind == 'nonempty': assert (target / '.hidden').read_text() == 'user data'
    elif kind == 'file': assert target.read_text() == 'user data'
    else: assert target.is_symlink()


@pytest.mark.parametrize('version', ['v20.19.0', 'v22.12.0', 'v24.15.0'])
def test_scaffold_preserves_all_components_and_pins(sandbox, version):
    root, scripts, _ = sandbox
    name = '-中文 空格 & "\' $(`touch INJECTED`) \\ <b>'
    target = root / name
    target.mkdir()  # Existing empty targets are permitted.
    result = cli(sandbox, 'init', name, TEST_NODE_VERSION=version)
    assert result.returncode == 0, result.stderr
    title = re.search(r'<title>(.*?)</title>', (target / 'index.html').read_text())[1]
    assert html.unescape(title) == name
    assert '<b>' not in title and '&amp;' in title
    assert not (root / 'INJECTED').exists()
    package = json.loads((target / 'package.json').read_text())
    assert package['name'] == 'web-artifact'
    versions = package['dependencies'] | package['devDependencies']
    assert all(re.fullmatch(r'\d+\.\d+\.\d+', version) for version in versions.values())
    assert versions['react-day-picker'] == '9.14.0'
    assert versions['react-resizable-panels'] == '2.1.7'
    assert versions['zod'] == '3.24.1' and versions['@hookform/resolvers'] == '3.9.1'
    assert versions['date-fns'] == '3.6.0' and versions['react'] == '18.3.1'
    assert versions['vite'] == '8.3.8'
    with tarfile.open(scripts / 'shadcn-components.tar.gz') as archive:
        components = [m for m in archive.getmembers() if m.isfile() and m.name.startswith('components/ui/')]
        assert len(components) == 43
        assert sum(m.isfile() and m.name.endswith(('.ts', '.tsx')) for m in archive.getmembers()) == 45
        for member in archive.getmembers():
            if member.isfile() and member.name.startswith(('components/', 'lib/', 'hooks/')):
                assert (target / 'src' / member.name).read_bytes() == archive.extractfile(member).read()
    for notice, content in NOTICES.items(): assert (target / notice).read_bytes() == content
    assert [c['args'] for c in calls(sandbox)] == [['install', '--frozen-lockfile', '--ignore-scripts']]
    assert not list(root.glob('.artifact-init-*'))
    # Check source through stdin: Node's filename-based --check rejects a literal
    # backslash in a directory name before it even reads the source on POSIX.
    checked = subprocess.run([NODE, '--check'], input=(target / 'tailwind.config.cjs').read_bytes(), capture_output=True)
    assert checked.returncode == 0, checked.stderr


def test_init_install_failure_does_not_publish_partial_project(sandbox):
    root, _, _ = sandbox
    result = cli(sandbox, 'init', 'partial', TEST_MODE='install-fail')
    assert result.returncode != 0 and '(4)' in result.stderr
    assert not (root / 'partial').exists() and not list(root.glob('.artifact-init-*'))


def test_normal_scaffold_to_bundle_cli_flow(sandbox):
    root, _, _ = sandbox
    result = cli(sandbox, 'init', '完整项目')
    assert result.returncode == 0, result.stderr
    folder = root / '完整项目'
    result = cli(sandbox, 'bundle', cwd=folder)
    assert result.returncode == 0, result.stderr
    assert (folder / 'bundle.html').stat().st_size > 0
    assert 'artifact-license-notices' in (folder / 'bundle.html').read_text()
    assert len(list((folder / 'src').rglob('*.tsx'))) == 45  # 43 UI + main + App.


def test_missing_source_notice_prevents_scaffolding(sandbox):
    root, scripts, _ = sandbox
    (scripts.parent / 'LICENSE.shadcn.txt').unlink()
    result = cli(sandbox, 'init', 'new')
    assert result.returncode != 0 and 'LICENSE.shadcn.txt' in result.stderr
    assert not calls(sandbox) and not (root / 'new').exists()


@pytest.mark.parametrize('failure', ['install-fail', 'build-fail', 'build-empty', 'build-invalid',
                                   'build-missing', 'inline-fail', 'inline-empty', 'inline-whitespace',
                                   'inline-invalid', 'inline-resource', 'inline-style-resource', 'inline-asset'])
def test_bundle_failures_preserve_both_previous_deliveries(sandbox, failure):
    folder = project(sandbox)
    result = cli(sandbox, 'bundle', cwd=folder, TEST_MODE=failure)
    assert result.returncode != 0, (failure, result.stdout, result.stderr)
    assert_old_delivery(folder)
    if failure == 'build-fail': assert '(7)' in result.stderr
    if failure == 'inline-fail': assert '(9)' in result.stderr


@pytest.mark.parametrize('mode', ['', 'inline-style-data'])
def test_bundle_commits_current_html_and_recoverable_inert_notices(sandbox, mode):
    folder = project(sandbox)
    result = cli(sandbox, 'bundle', cwd=folder, TEST_MODE=mode)
    assert result.returncode == 0, result.stderr
    output = (folder / 'bundle.html').read_text()
    encoded = re.search(r'<template id="artifact-license-notices" data-encoding="base64-json">([A-Za-z0-9+/=]+)</template>', output)[1]
    data = json.loads(base64.b64decode(encoded))
    assert data['scope'] == 'bundled-source-and-runtime-notices'
    assert {n['name']: base64.b64decode(n['content']) for n in data['notices']} == NOTICES
    assert 'throw "injected"' not in output
    assert output.count('id="artifact-license-notices"') == 1
    if not mode: assert 'const text = "</template></body><script>";' in output
    assert (folder / 'dist/index.html').read_bytes() == b'old dist'
    assert not list(folder.glob('.artifact-build-*'))
    actual = calls(sandbox)
    assert actual[0]['args'] == ['add', '--ignore-scripts', '--save-dev', '--save-exact', 'parcel@2.16.4', '@parcel/config-default@2.16.4', 'html-inline@1.2.0']
    assert not (folder / '.parcelrc').exists()
    build = actual[1]
    assert '--no-cache' in build['args']
    dist = Path(build['args'][build['args'].index('--dist-dir') + 1])
    assert dist.parent.parent == folder.resolve() and dist.parent.name.startswith('.artifact-build-')
    assert Path(actual[2]['cwd']) == folder.resolve()


def test_existing_project_tools_are_used_without_install(sandbox):
    folder = project(sandbox)
    for name in ('parcel', '@parcel/config-default', 'html-inline'):
        location = folder / 'node_modules' / name
        location.mkdir(parents=True)
        (location / 'package.json').write_text('{"version":"1.0.0"}')
    result = cli(sandbox, 'bundle', cwd=folder)
    assert result.returncode == 0, result.stderr
    assert calls(sandbox)[0]['args'][:3] == ['exec', 'parcel', 'build']


@pytest.mark.parametrize('mode', ['write', 'rename'])
def test_write_or_publish_failure_keeps_old_delivery(sandbox, mode):
    root, _, _ = sandbox
    folder = project(sandbox)
    hook = root / 'fail-fs.cjs'
    hook.write_text("const fs = require('node:fs');\n" + (
        "const old = fs.writeFileSync; fs.writeFileSync = function(p, ...args) { if (String(p).includes('.artifact-build-') && String(p).endsWith('bundle.html')) { const e = new Error('simulated ENOSPC'); e.code='ENOSPC'; throw e; } return old.call(this,p,...args); };\n"
        if mode == 'write' else
        "const old = fs.renameSync; fs.renameSync = function(p, q) { if (String(q).endsWith('bundle.html')) { const e = new Error('simulated EACCES'); e.code='EACCES'; throw e; } return old.call(this,p,q); };\n"))
    result = cli(sandbox, 'bundle', cwd=folder, NODE_OPTIONS='--require=' + str(hook))
    assert result.returncode != 0 and 'simulated' in result.stderr
    assert_old_delivery(folder)


@pytest.mark.parametrize('bad_notice', ['missing', 'symlink', 'oversize', 'empty'])
def test_invalid_notices_fail_before_tools_or_publication(sandbox, bad_notice):
    root, _, _ = sandbox
    folder = project(sandbox)
    notice = folder / 'LICENSE.txt'
    notice.unlink()
    if bad_notice == 'symlink':
        private = root / 'do-not-copy'
        private.write_text('private bytes')
        notice.symlink_to(private)
    elif bad_notice == 'oversize': notice.write_bytes(b'x' * (1024 * 1024 + 1))
    elif bad_notice == 'empty': notice.write_bytes(b'')
    result = cli(sandbox, 'bundle', cwd=folder)
    assert result.returncode != 0
    assert_old_delivery(folder)
    assert not calls(sandbox)
