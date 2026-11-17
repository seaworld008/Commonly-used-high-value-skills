"""Run the real Node CLI with synthetic fetch responses and real filesystem calls.

Faults wrap Node's promise APIs; no server, socket, credentials or model is used.
"""

import base64
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/multimodal-media/gpt-image2/scripts/gpt-image2.mjs"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAIAAAADCAIAAAA2iEnWAAAAFElEQVR4nGMUCVjAwMDAxMDAgKAAExQBCsGXXKcAAAAASUVORK5CYII="
)
FINAL = "gpt-image2_20260102_030405_1.png"
OLD = b"user-owned old output"

# --require loads this before the actual CLI. Unintercepted fetch is never used.
PRELOAD = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const files = require('node:fs/promises');
const path = require('node:path');
const fixture = JSON.parse(process.env.ATOMIC_FIXTURE);
const png = Buffer.from(fixture.raw, 'base64');
const out = process.env.ATOMIC_OUT;
const audit = (event, detail = {}) => fs.appendFileSync(process.env.ATOMIC_AUDIT,
  JSON.stringify({event, ...detail}) + '\n');
const RealDate = Date;
global.Date = class extends RealDate {
  constructor(...args) { super(...(args.length ? args : [2026, 0, 2, 3, 4, 5])); }
};
process.umask(0); // Safe modes must come from the CLI, not a restrictive shell.
global.fetch = async (url, opts) => {
  audit('fetch', {url: String(url), method: opts.method});
  assert.equal(opts.redirect, 'error');
  if (opts.method === 'POST') {
    assert.equal(String(url), 'https://api.invalid/v1/images/generations');
    assert.equal(new Headers(opts.headers).get('authorization'), 'Bearer synthetic-key');
    return Response.json({data: fixture.data});
  }
  assert.equal(String(url), 'https://objects.invalid/synthetic.png');
  assert.equal(new Headers(opts.headers).get('authorization'), null);
  return new Response(png, {headers: {'content-type': 'image/png',
    'content-length': String(png.length)}});
};
let opened = 0;
const handles = new WeakMap();
const stages = new Map();
const fault = (stage, index) => fixture.fail === stage && index === fixture.fail_index;
const realMkdtemp = files.mkdtemp.bind(files);
files.mkdtemp = async (...args) => {
  audit('stage', {prefix: String(args[0])});
  assert.equal(path.dirname(args[0]), out);
  if (fault('stage', opened + 1)) {
    // Count the failed item so subsequent items can still succeed.
    opened++;
    throw Error('synthetic stage failure');
  }
  return realMkdtemp(...args);
};
const realOpen = files.open.bind(files);
files.open = async (name, flags, mode) => {
  const index = ++opened;
  audit('open', {name: String(name), flags, mode, index});
  assert.equal(path.dirname(path.dirname(name)), out);
  assert.equal(fs.statSync(path.dirname(name)).mode & 0o777, 0o700);
  assert.equal(flags, 'wx');
  assert.equal(mode, 0o600);
  if (fault('open', index)) throw Error('synthetic open failure');
  const handle = await realOpen(name, flags, mode);
  const state = {name, index, synced: false, closed: false};
  handles.set(handle, state);
  stages.set(String(name), state);
  const sync = handle.sync.bind(handle);
  handle.sync = async () => {
    audit('sync', {index});
    if (fault('sync', index)) throw Error('synthetic sync failure');
    await sync();
    state.synced = true;
  };
  const close = handle.close.bind(handle);
  let closeFailed = false;
  handle.close = async () => {
    audit('close', {index});
    if (fault('close', index) && !closeFailed) {
      closeFailed = true;
      throw Error('synthetic close failure');
    }
    await close();
    state.closed = true;
  };
  return handle;
};
const realWrite = files.writeFile.bind(files);
files.writeFile = async (target, data, ...rest) => {
  const state = handles.get(target);
  // The vulnerable baseline writes directly to the final path.
  audit('write', {index: state?.index ?? 1, staged: Boolean(state)});
  if (!state) return realWrite(target, data, ...rest);
  if (fault('write', state.index) || fault('short', state.index)) {
    const {bytesWritten} = await target.write(data.subarray(0, 11));
    assert.equal(bytesWritten, 11);
    assert.equal(fs.statSync(state.name).size, 11);
    audit('partial', {index: state.index, bytesWritten});
    if (fixture.fail === 'write') throw Error('synthetic partial write failure');
    return; // A faulty writer must never publish an incomplete success either.
  }
  if (fixture.chunked) {
    await realWrite(target, (async function* () {
      for (let offset = 0; offset < data.length; offset += 3) {
        yield data.subarray(offset, offset + 3);
      }
    })(), ...rest);
  } else {
    await realWrite(target, data, ...rest);
  }
};
const realLink = files.link.bind(files);
files.link = async (source, dest) => {
  // Verify actual bytes, modes, and completed sync/close before native publish.
  const index = Number(path.basename(dest).match(/_(\d+)\.png$/)[1]);
  const state = stages.get(String(source));
  assert.equal(state?.synced, true);
  assert.equal(state?.closed, true);
  assert.deepEqual(fs.readFileSync(source), png);
  assert.equal(fs.statSync(source).mode & 0o777, 0o600);
  assert.equal(path.dirname(path.dirname(source)), out);
  assert.equal(path.dirname(dest), out);
  audit('link', {source, dest, index});
  if (fixture.claim) fs.writeFileSync(dest, 'concurrent old output', {flag: 'wx'});
  if (fault('link', index)) throw Error('synthetic publish failure');
  if (fixture.barrier) {
    fs.writeFileSync(path.join(fixture.barrier, fixture.worker), 'ready', {flag: 'wx'});
    for (let attempt = 0; attempt < 500 && fs.readdirSync(fixture.barrier).length < 2; attempt++) {
      await new Promise(resolve => setTimeout(resolve, 10));
    }
    assert.equal(fs.readdirSync(fixture.barrier).length, 2, 'both Node processes reached publish');
  }
  await realLink(source, dest); // Real OS exclusion, including symlinks and FIFOs.
  audit('published', {dest, index});
};
const realRm = files.rm.bind(files);
files.rm = async (name, ...rest) => {
  audit('cleanup', {name: String(name)});
  assert.equal(path.dirname(name), out);
  assert.notEqual(path.basename(name), path.basename(out));
  if (fixture.cleanup_failure) throw Error('synthetic cleanup failure');
  return realRm(name, ...rest);
};
"""


@pytest.fixture
def atomic_cli(tmp_path):
    script = Path(shutil.copy(SCRIPT, tmp_path))
    preload = tmp_path / "atomic-preload.cjs"
    preload.write_text(PRELOAD)
    out = tmp_path / "out"
    out.mkdir()

    def prepare(*, n=1, route="b64_json", fail=None, fail_index=1, tag="run", **extra):
        raw = base64.b64encode(PNG).decode()
        item = {route: "https://objects.invalid/synthetic.png" if route == "url" else raw}
        fixture = dict(raw=raw, data=[item] * n, fail=fail, fail_index=fail_index, **extra)
        audit = tmp_path / f"{tag}.jsonl"
        command = ["node", "--require", str(preload), str(script), "synthetic prompt",
                   "--base-url", "https://api.invalid/v1", "--api-key", "synthetic-key",
                   "--out-dir", str(out), "-n", str(n)]
        env = {"PATH": os.environ["PATH"], "HOME": str(tmp_path), "TMPDIR": str(tmp_path),
               "ATOMIC_FIXTURE": json.dumps(fixture), "ATOMIC_OUT": str(out),
               "ATOMIC_AUDIT": str(audit)}
        return command, env, audit

    def invoke(**kwargs):
        command, env, audit = prepare(**kwargs)
        result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True,
                                text=True, timeout=15)
        return result, [json.loads(line) for line in audit.read_text().splitlines()]

    return out, prepare, invoke


def assert_receipt(result, saved, expected, *, failed=0):
    summary = f"已保存 {saved} 张，预期 {expected} 张，缺少 {max(0, expected - saved)} 张"
    if failed:
        assert result.returncode != 0, result.stdout + result.stderr
        assert f"{summary}，失败条目 {failed} 个" in result.stderr
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        assert summary in result.stdout
    assert result.stdout.count("] saved ") == saved


@pytest.mark.parametrize("route", ["b64_json", "url"])
@pytest.mark.parametrize("chunked", [False, True])
def test_real_node_publishes_only_complete_synced_private_images(atomic_cli, route, chunked):
    out, _, invoke = atomic_cli
    result, events = invoke(route=route, chunked=chunked)
    assert_receipt(result, 1, 1)
    assert list(out.iterdir()) == [out / FINAL]
    assert (out / FINAL).read_bytes() == PNG
    assert stat.S_IMODE((out / FINAL).stat().st_mode) == 0o600
    assert str(out / FINAL) in result.stdout
    order = [event["event"] for event in events]
    assert order.index("write") < order.index("sync") < order.index("close") < order.index("link")
    assert order.index("link") < order.index("published") < order.index("cleanup")
    stage = next(event["name"] for event in events if event["event"] == "open")
    assert not Path(stage).exists()
    assert len([e for e in events if e["event"] == "fetch"]) == (2 if route == "url" else 1)


@pytest.mark.parametrize("kind", ["file", "directory", "symlink", "dangling-symlink", "fifo"])
def test_existing_final_objects_are_never_followed_or_replaced(atomic_cli, kind):
    out, _, invoke = atomic_cli
    final = out / FINAL
    target = out.parent / "user-target"
    if kind == "file":
        final.write_bytes(OLD)
    elif kind == "directory":
        final.mkdir()
        (final / "sentinel").write_bytes(OLD)
    elif kind in {"symlink", "dangling-symlink"}:
        if kind == "symlink":
            target.write_bytes(OLD)
        final.symlink_to(target)
    else:
        os.mkfifo(final)
    before = final.lstat()
    result, events = invoke()
    assert_receipt(result, 0, 1, failed=1)
    after = final.lstat()
    assert (after.st_ino, after.st_mode, after.st_size) == (before.st_ino, before.st_mode, before.st_size)
    assert list(out.iterdir()) == [final]
    assert any(e["event"] == "link" for e in events)
    if kind == "file":
        assert final.read_bytes() == OLD
    elif kind == "directory":
        assert (final / "sentinel").read_bytes() == OLD
    elif kind == "symlink":
        assert target.read_bytes() == OLD and final.readlink() == target
    elif kind == "dangling-symlink":
        assert not target.exists() and final.readlink() == target
    else:
        assert stat.S_ISFIFO(after.st_mode)


@pytest.mark.parametrize("stage", ["stage", "open", "write", "short", "sync", "close", "link"])
def test_stage_write_sync_close_and_publish_faults_leave_no_half_image(atomic_cli, stage):
    out, _, invoke = atomic_cli
    sentinel = out / "user-unrelated"
    sentinel.write_bytes(OLD)
    result, events = invoke(fail=stage)
    assert_receipt(result, 0, 1, failed=1)
    assert list(out.iterdir()) == [sentinel] and sentinel.read_bytes() == OLD
    assert not any(e["event"] == "published" for e in events)
    if stage in {"write", "short"}:
        assert any(e["event"] == "partial" and e["bytesWritten"] == 11 for e in events)
    if stage != "stage":
        assert any(e["event"] == "cleanup" for e in events)


@pytest.mark.parametrize("stage", ["stage", "open", "write", "short", "sync", "close", "link"])
def test_partial_batch_keeps_successful_receipts_and_continues(atomic_cli, stage):
    out, _, invoke = atomic_cli
    result, _ = invoke(n=3, fail=stage, fail_index=2)
    assert_receipt(result, 2, 3, failed=1)
    finals = sorted(out.iterdir())
    assert [p.name for p in finals] == [FINAL, FINAL.replace("_1.png", "_3.png")]
    assert all(p.read_bytes() == PNG and str(p) in result.stdout for p in finals)


def test_object_created_at_publish_wins_without_being_deleted(atomic_cli):
    out, _, invoke = atomic_cli
    result, _ = invoke(claim=True)
    assert_receipt(result, 0, 1, failed=1)
    assert list(out.iterdir()) == [out / FINAL]
    assert (out / FINAL).read_bytes() == b"concurrent old output"


def test_cleanup_error_after_publish_preserves_delivered_receipt(atomic_cli):
    out, _, invoke = atomic_cli
    result, events = invoke(cleanup_failure=True)
    assert_receipt(result, 1, 1)
    assert (out / FINAL).read_bytes() == PNG
    assert "无法清理图片暂存目录" in result.stderr
    assert any(e["event"] == "cleanup" for e in events)
    stages = [p for p in out.iterdir() if p.name != FINAL]
    assert len(stages) == 1 and str(stages[0]) in result.stderr
    assert stat.S_IMODE(stages[0].stat().st_mode) == 0o700
    assert (stages[0] / "image").stat().st_ino == (out / FINAL).stat().st_ino


def test_cleanup_error_before_publish_keeps_primary_failure_and_old_outputs(atomic_cli):
    out, _, invoke = atomic_cli
    sentinel = out / "user-unrelated"
    sentinel.write_bytes(OLD)
    result, events = invoke(fail="write", cleanup_failure=True)
    assert_receipt(result, 0, 1, failed=1)
    assert "synthetic partial write failure" in result.stderr
    assert "无法清理图片暂存目录" in result.stderr
    assert sentinel.read_bytes() == OLD and not (out / FINAL).exists()
    assert not any(e["event"] == "published" for e in events)
    stages = [p for p in out.iterdir() if p != sentinel]
    assert len(stages) == 1 and str(stages[0]) in result.stderr
    assert stat.S_IMODE(stages[0].stat().st_mode) == 0o700


def test_two_real_node_processes_cannot_overwrite_the_same_final_name(atomic_cli):
    out, prepare, _ = atomic_cli
    barrier = out.parent / "publish-barrier"
    barrier.mkdir()
    processes = []
    try:
        for tag in ["first", "second"]:
            command, env, _ = prepare(tag=tag, barrier=str(barrier), worker=tag)
            processes.append(subprocess.Popen(command, cwd=out.parent, env=env,
                                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        results = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            results.append(subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr))
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate()
    assert sorted(r.returncode for r in results) == [0, 1]
    for result in results:
        assert_receipt(result, int(result.returncode == 0), 1, failed=int(result.returncode != 0))
    assert list(out.iterdir()) == [out / FINAL]
    assert (out / FINAL).read_bytes() == PNG
