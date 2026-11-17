"""Real Node/CLI descriptor regressions; every fixture and hook stays in TMPDIR.

The pnpm double writes real files/stdout. No network, ports or package scripts.
Faults intercept actual fs calls, never replace the implementation under test.
"""
import base64
import json
import os
import re

import pytest

from tests.test_web_artifact_runtime import (
    NOTICES, assert_old_delivery, cli, project, sandbox,
)


HOOK = r"""
const fs = require('node:fs');
const original = Object.fromEntries(['openSync', 'closeSync', 'lstatSync', 'fstatSync',
  'readSync', 'readFileSync', 'writeSync', 'writeFileSync', 'ftruncateSync', 'fsyncSync', 'renameSync']
  .map(name => [name, fs[name].bind(fs)]));
const mode = process.env.DESCRIPTOR_CASE;
const handles = new Map();
const evidence = {events: [], candidateOpens: 0, reads: [], writes: [], leaked: false};
let swapped = false, changed = false, failed = false;
let candidatePath;
const buildPath = p => String(p).includes('.artifact-build-') && String(p).endsWith('/dist/index.html');
const candidate = p => String(p).includes('.artifact-build-') && String(p).endsWith('/bundle.html');
function replace(p) {
  if (swapped) return;
  swapped = true;
  fs.unlinkSync(p);
  original.renameSync(process.env.REPLACEMENT, p);
  evidence.events.push('replaced');
}
function fail(point) {
  failed = true;
  evidence.events.push(point);
  throw new Error('injected ' + point);
}
// Exercise the historical lstat/read gap as well as replacement immediately
// before the hardened open. With no pre-open lstat, the latter fires instead.
fs.lstatSync = function(p, ...args) {
  const info = original.lstatSync(p, ...args);
  if (mode.startsWith('build-replace-') && buildPath(p)) replace(p);
  return info;
};
fs.openSync = function(p, flags, ...args) {
  if (mode.startsWith('build-replace-') && buildPath(p)) replace(p);
  const fd = original.openSync(p, flags, ...args);
  handles.set(fd, String(p));
  if (mode === 'build-after-open-symlink' && buildPath(p)) replace(p);
  if (mode === 'mutate-before-rewrite' && String(p).endsWith('/runtime-license-notices.json')) {
    const edit = original.openSync(candidatePath, 'r+');
    original.ftruncateSync(edit, 1);
    original.closeSync(edit);
    evidence.events.push('mutated-before-rewrite');
  }
  if (candidate(p)) {
    candidatePath = String(p);
    evidence.candidateOpens++;
    evidence.events.push('candidate-open');
  }
  return fd;
};
fs.readFileSync = function(p, ...args) {
  const data = original.readFileSync(p, ...args);
  if (buildPath(p) || candidate(p)) {
    evidence.reads.push({legacy: true});
    if (Buffer.from(data).includes(Buffer.from('EXTERNAL_SENTINEL'))) evidence.leaked = true;
  }
  return data;
};
fs.readSync = function(fd, buffer, offset, length, position) {
  const p = handles.get(fd);
  if (candidate(p) && mode.startsWith('candidate-read-')) replace(p);
  if (mode === 'read-short-success' && (buildPath(p) || candidate(p))) length = Math.min(13, length);
  const count = original.readSync(fd, buffer, offset, length, position);
  if (buildPath(p) || candidate(p)) {
    evidence.reads.push({candidate: candidate(p), position, length, count});
    if (buffer.subarray(offset, offset + count).includes(Buffer.from('EXTERNAL_SENTINEL'))) evidence.leaked = true;
    if (!changed && count && /^mutate-(build|candidate)-/.test(mode) &&
        (mode.includes('-candidate-') ? candidate(p) : buildPath(p))) {
      changed = true;
      const edit = original.openSync(p, 'r+');
      const size = original.fstatSync(edit).size;
      const kind = mode.split('-').at(-1);
      if (kind === 'grow') original.ftruncateSync(edit, size + 1);
      else if (kind === 'shrink') original.ftruncateSync(edit, size - 1);
      else if (kind === 'oversize') original.ftruncateSync(edit, 128 * 1024 * 1024 + 1);
      else {
        original.writeSync(edit, Buffer.from('X'), 0, 1, 0);
        fs.futimesSync(edit, 100, 100);
      }
      original.closeSync(edit);
      evidence.events.push('mutated-' + kind);
    }
  }
  return count;
};
fs.writeSync = function(fd, buffer, offset, length, position) {
  if (!candidate(handles.get(fd))) return original.writeSync(fd, buffer, offset, length, position);
  evidence.writes.push({position, length});
  if (mode === 'candidate-write-symlink') replace(candidatePath);
  if (mode === 'write-zero') { evidence.events.push('zero-write'); return 0; }
  if (mode === 'write-partial-fail' && evidence.writes.length > 1) fail('write');
  if (mode === 'write-partial-fail' || mode === 'write-short-success') length = Math.min(17, length);
  return original.writeSync(fd, buffer, offset, length, position);
};
fs.ftruncateSync = function(fd, length) {
  if (candidate(handles.get(fd))) {
    evidence.events.push('truncate');
    if (mode === 'truncate-fail') fail('truncate');
  }
  return original.ftruncateSync(fd, length);
};
fs.fsyncSync = function(fd) {
  if (candidate(handles.get(fd))) {
    evidence.events.push('sync');
    if (mode === 'sync-fail') fail('sync');
    if (mode === 'sync-corrupt') {
      original.writeSync(fd, Buffer.from('X'), 0, 1, 0);
      evidence.events.push('corrupted');
    }
  }
  return original.fsyncSync(fd);
};
fs.closeSync = function(fd) {
  const p = handles.get(fd);
  if (candidate(p)) {
    evidence.events.push('close');
    if (mode === 'close-fail-before' && !failed) fail('close-before');
  }
  handles.delete(fd);
  const result = original.closeSync(fd);
  if (candidate(p)) {
    if (mode === 'close-fail-after' && !failed) fail('close-after');
    if (mode.startsWith('candidate-close-')) replace(p);
  }
  return result;
};
fs.renameSync = function(p, q) {
  if (candidate(p) && String(q).endsWith('/bundle.html')) {
    evidence.events.push('publish');
    if (mode === 'rename-fail') fail('rename');
  }
  return original.renameSync(p, q);
};
process.on('exit', () => {
  // A simulated pre-release close error leaves a real descriptor for the test
  // harness to release. Production must not retry an ambiguously failed close.
  for (const fd of handles.keys()) {
    try { original.closeSync(fd); } catch {}
  }
  original.writeFileSync(process.env.DESCRIPTOR_LOG, JSON.stringify(evidence));
});
"""


def run_case(sandbox, mode, replacement=None):
    root, _, _ = sandbox
    folder = project(sandbox)
    hook = root / 'descriptor-hook.cjs'
    hook.write_text(HOOK)
    outside = root / 'external.html'
    outside.write_bytes(b'<html><body>EXTERNAL_SENTINEL</body></html>')
    substitute = root / 'replacement'
    if replacement == 'symlink':
        substitute.symlink_to(outside)
    elif replacement == 'fifo':
        os.mkfifo(substitute)
    elif replacement == 'directory':
        substitute.mkdir()
    elif replacement == 'oversize':
        with substitute.open('wb') as stream:
            stream.truncate(128 * 1024 * 1024 + 1)
    elif replacement == 'empty':
        substitute.touch()
    elif replacement == 'regular':
        substitute.write_bytes(b'<html><body>replacement inode</body></html>')
    log = root / 'descriptor-log.json'
    result = cli(sandbox, 'bundle', cwd=folder, NODE_OPTIONS='--require=' + str(hook),
                 DESCRIPTOR_CASE=mode, DESCRIPTOR_LOG=str(log), REPLACEMENT=str(substitute))
    evidence = json.loads(log.read_text())
    assert not evidence['leaked'], evidence
    assert outside.read_bytes() == b'<html><body>EXTERNAL_SENTINEL</body></html>'
    return folder, result, evidence


@pytest.mark.parametrize('kind', ['symlink', 'fifo', 'directory', 'oversize', 'empty'])
def test_build_replacement_at_open_rejected_without_read_or_hang(sandbox, kind):
    folder, result, evidence = run_case(sandbox, 'build-replace-' + kind, kind)
    assert result.returncode != 0, result.stdout
    assert evidence['events'] == ['replaced']
    assert evidence['reads'] == []
    assert_old_delivery(folder)


def test_build_path_replaced_after_open_reads_only_original_inode(sandbox):
    folder, result, evidence = run_case(sandbox, 'build-after-open-symlink', 'symlink')
    assert result.returncode != 0 and 'symlink' in result.stderr
    assert 'replaced' in evidence['events']
    assert evidence['reads'][0]['count'] > 0
    assert 'publish' not in evidence['events']
    assert_old_delivery(folder)


@pytest.mark.parametrize('target', ['build', 'candidate'])
@pytest.mark.parametrize('kind', ['grow', 'shrink', 'oversize', 'mtime'])
def test_open_html_changes_during_read_are_rejected(sandbox, target, kind):
    folder, result, evidence = run_case(sandbox, f'mutate-{target}-{kind}')
    assert result.returncode != 0 and 'changed during read' in result.stderr
    assert 'mutated-' + kind in evidence['events']
    assert 'publish' not in evidence['events']
    assert sum(r['count'] for r in evidence['reads']) < 4096
    assert_old_delivery(folder)


@pytest.mark.parametrize('point', ['read', 'close'])
@pytest.mark.parametrize('kind', ['symlink', 'fifo', 'directory', 'regular'])
def test_candidate_path_replacement_cannot_publish_or_touch_external_file(sandbox, point, kind):
    folder, result, evidence = run_case(sandbox, f'candidate-{point}-{kind}', kind)
    assert result.returncode != 0, result.stdout
    assert 'replaced' in evidence['events'] and 'publish' not in evidence['events']
    assert evidence['candidateOpens'] == 1
    assert_old_delivery(folder)


def test_candidate_replacement_before_fd_rewrite_leaves_external_file_untouched(sandbox):
    folder, result, evidence = run_case(sandbox, 'candidate-write-symlink', 'symlink')
    assert result.returncode != 0 and 'Candidate path was replaced' in result.stderr
    assert 'replaced' in evidence['events'] and evidence['writes']
    assert 'publish' not in evidence['events']
    assert_old_delivery(folder)


def test_candidate_change_after_validation_is_rejected_before_rewrite(sandbox):
    folder, result, evidence = run_case(sandbox, 'mutate-before-rewrite')
    assert result.returncode != 0 and 'changed before rewrite' in result.stderr
    assert 'mutated-before-rewrite' in evidence['events']
    assert evidence['writes'] == [] and 'publish' not in evidence['events']
    assert_old_delivery(folder)


@pytest.mark.parametrize('mode,event', [
    ('write-partial-fail', 'write'), ('write-zero', 'zero-write'),
    ('truncate-fail', 'truncate'), ('sync-fail', 'sync'),
    ('close-fail-before', 'close-before'), ('close-fail-after', 'close-after'),
    ('rename-fail', 'rename'), ('sync-corrupt', 'corrupted'),
])
def test_descriptor_failure_preserves_old_bundle_and_dist(sandbox, mode, event):
    folder, result, evidence = run_case(sandbox, mode)
    assert result.returncode != 0, result.stdout
    assert event in evidence['events']
    assert evidence['candidateOpens'] == 1
    if mode == 'write-partial-fail':
        assert len(evidence['writes']) == 2 and evidence['writes'][1]['position'] == 17
    if mode.startswith('close-fail'):
        assert evidence['events'].count('close') == 1
    if mode != 'rename-fail':
        assert 'publish' not in evidence['events']
    assert_old_delivery(folder)


@pytest.mark.parametrize('mode', ['normal', 'write-short-success', 'read-short-success'])
def test_shared_stdout_cursor_and_short_writes_produce_complete_bundle(sandbox, mode):
    folder, result, evidence = run_case(sandbox, mode)
    assert result.returncode == 0, result.stderr
    output = (folder / 'bundle.html').read_text()
    assert output.startswith('<!doctype html>') and output.endswith('</body></html>\n')
    assert 'window.artifactNew = true' in output
    encoded = re.search(r'data-encoding="base64-json">([^<]+)</template>', output)[1]
    data = json.loads(base64.b64decode(encoded))
    assert {n['name']: base64.b64decode(n['content']) for n in data['notices']} == NOTICES
    assert evidence['candidateOpens'] == 1
    reads = [r for r in evidence['reads'] if r['candidate']]
    assert reads[0]['position'] == 0 and reads[0]['count'] > 0
    assert all(isinstance(r['position'], int) for r in reads + evidence['writes'])
    assert evidence['writes'][0]['position'] == 0
    assert evidence['events'][-4:] == ['truncate', 'sync', 'close', 'publish']
    if mode == 'write-short-success':
        assert len(evidence['writes']) > 2
    if mode == 'read-short-success':
        assert len(reads) > 4 and reads[1]['position'] == 13
    assert (folder / 'dist/index.html').read_bytes() == b'old dist'
    assert (folder / 'dist/old.js').read_bytes() == b'old js'
    assert not list(folder.glob('.artifact-build-*'))
