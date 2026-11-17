"""Offline CLI tests with real files, signals and subprocesses on the DevTools pipe."""
import base64
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/multimodal-media/live-panel/scripts"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC"
)
# Synthetic ISO BMFF boxes for the container check, without a playable H.264 stream.
MP4 = (b"\0\0\0\x14ftypisom\0\0\0\0isom" + b"\0\0\0\x09mdatx" +
       b"\0\0\0\x10moov\0\0\0\x08free")

CHROME = r'''
import base64, json, os, sys, time
from pathlib import Path

Path("browser.pid").write_text(str(os.getpid()))
Path("flags").write_text(json.dumps(sys.argv[1:]))
mode = os.environ["MODE"]
shots = 0
data = b""
while True:
    while b"\0" not in data:
        part = os.read(3, 65536)
        if not part:
            sys.exit(0)
        data += part
    packet, data = data.split(b"\0", 1)
    msg = json.loads(packet)
    method = msg["method"]
    if method == mode or (method == "Page.captureScreenshot" and mode == "active"):
        if mode == "active":
            while not Path("encoder.pid").exists():
                time.sleep(0.01)
        Path("ready").touch()
        time.sleep(30)
    result = {}
    if method == "Target.createTarget":
        result["targetId"] = "target"
    elif method == "Target.attachToTarget":
        result["sessionId"] = "session"
    elif method == "Page.captureScreenshot":
        shots += 1
        result["data"] = base64.b64encode(Path("good.png").read_bytes()).decode()
    elif method == "Runtime.evaluate":
        expr = msg["params"]["expression"]
        if expr == "window.__ready===true":
            value = True
        elif expr == "window.__error||''":
            value = "late page failure" if mode == "pageerror" and shots == 2 else ""
        elif expr == "window.__check()":
            with open("measurements", "a") as f:
                f.write("measured\n")
            value = ["overflow"] if mode == "overflow" else []
        elif "getImageData" in expr:
            value = [51, 255] if mode == "replay" else [0, 0]
        else:
            assert expr.startswith("window.seek(")
            value = None
        result = {"result": {"value": value}}
    os.write(4, json.dumps({"id": msg["id"], "result": result}).encode() + b"\0")
'''

ENCODER = '''
import os, sys
from pathlib import Path

out = Path(sys.argv[-1])
mode = os.environ["MODE"]
Path("encoder.pid").write_text(str(os.getpid()))
with Path("encoder-paths").open("a") as paths:
    paths.write(str(out) + "\\n")
if "-frames:v" in sys.argv:
    source = Path("good.png")
    if mode == "extract":
        import time
        Path("ready").touch()
        time.sleep(30)
    if mode == "late" and out.name.startswith("frame_2"):
        sys.exit(0)
else:
    source = Path("good.mp4")
    if mode == "pageerror":
        out.write_bytes(b"partial video")
    sys.stdin.buffer.read()
if mode == "missing":
    sys.exit(0)
if mode == "invalid":
    out.write_bytes(b"garbage")
elif mode == "empty":
    out.touch()
elif mode == "symlink":
    out.symlink_to(source.resolve())
elif mode == "directory":
    out.mkdir()
elif mode == "truncated":
    out.write_bytes(source.read_bytes()[:16])
else:
    out.write_bytes(source.read_bytes())
sys.exit(9 if mode == "nonzero" else 0)
'''


def pid_gone(path):
    with pytest.raises(ProcessLookupError):
        os.kill(int(path.read_text()), 0)


@pytest.fixture
def cli(tmp_path):
    (tmp_path / "good.png").write_bytes(PNG)
    (tmp_path / "good.mp4").write_bytes(MP4)
    (tmp_path / "config.json").write_text(json.dumps({
        "private": "synthetic configuration", "canvas": {"width": 2, "height": 2, "duration": 1, "fps": 2},
    }))
    for name, body in (("chrome", CHROME), ("ffmpeg", ENCODER)):
        exe = tmp_path / name
        exe.write_text(f"#!{sys.executable}\n" + body)
        exe.chmod(0o700)
    outputs = tmp_path / "deliveries with spaces"
    outputs.mkdir()

    def command(entry, *args, mode="success", background=False):
        options = ["--out", outputs / "movie.mp4"] if entry == "render" else [
            "--out-dir", outputs, "--samples", "1", "--png", "2",
        ]
        cmd = [sys.executable, "-B", SCRIPTS / (entry + ".py"), "--config", "config.json",
               "--chrome", tmp_path / "chrome", "--ffmpeg", tmp_path / "ffmpeg", *options, *args]
        kwargs = dict(cwd=tmp_path, env=dict(os.environ, MODE=mode, TMPDIR=str(tmp_path)),
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if background:
            return subprocess.Popen(cmd, start_new_session=True, **kwargs)
        return subprocess.run(cmd, timeout=10, **kwargs)

    return command, outputs


def frame_names(outputs):
    return [outputs / "frame_1_t00.25.png", outputs / "frame_2_t00.75.png"]


@pytest.mark.parametrize("entry", ["render", "check_frames"])
@pytest.mark.parametrize("mode", ["success", "missing", "invalid", "empty", "truncated", "symlink", "directory", "nonzero"])
def test_encoder_deliveries(cli, tmp_path, entry, mode):
    run, outputs = cli
    render = entry == "render"
    files = [outputs / "movie.mp4"] if render else frame_names(outputs)
    for file in files:
        file.write_bytes(b"prior delivery")
        file.chmod(0o600)
    result = run(entry, *([] if render else ["--video", "good.mp4"]), mode=mode)
    assert (result.returncode == 0) == (mode == "success"), result.stdout + result.stderr
    for file in files:
        assert file.read_bytes() == ((MP4 if render else PNG) if mode == "success" else b"prior delivery")
        assert file.stat().st_mode & 0o777 == 0o600
    assert set(outputs.iterdir()) == set(files)
    for path in (tmp_path / "encoder-paths").read_text().splitlines():
        assert Path(path).parent.parent == outputs and Path(path) not in files
    assert not list(tmp_path.glob("livepanel-*"))
    assert "--no-sandbox" not in json.loads((tmp_path / "flags").read_text())
    if mode != "success":
        assert "wrote " not in result.stderr and "0 distinct problems" not in result.stdout


@pytest.mark.parametrize("mode", ["late", "overflow", "replay"])
def test_video_batch_failure_keeps_earlier_png(cli, mode):
    run, outputs = cli
    first, second = frame_names(outputs)
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    result = run("check_frames", "--video", "good.mp4", "--repeat", mode=mode)
    assert result.returncode != 0
    assert (first.read_bytes(), second.read_bytes()) == (b"first", b"second")


def test_late_page_error_keeps_video_and_frames(cli):
    run, outputs = cli
    movie = outputs / "movie.mp4"
    kept = outputs / "f_0000.png"
    movie.write_bytes(b"prior video")
    kept.write_bytes(b"prior frame")
    result = run("render", "--keep-frames", outputs, mode="pageerror")
    assert result.returncode != 0 and "late page failure" in result.stderr
    assert {p.name: p.read_bytes() for p in outputs.iterdir()} == {
        movie.name: b"prior video", kept.name: b"prior frame",
    }


def test_success_publishes_mp4_with_frames_and_explicit_page(cli, tmp_path):
    run, outputs = cli
    frames = tmp_path / "frames"
    html = tmp_path / "explicit.html"
    result = run("render", "--keep-frames", frames, "--html-out", html)
    assert result.returncode == 0, result.stderr
    assert (outputs / "movie.mp4").read_bytes() == MP4
    assert {f.name: f.read_bytes() for f in frames.iterdir()} == {"f_0000.png": PNG, "f_0001.png": PNG}
    assert "synthetic configuration" in html.read_text()
    assert not list(tmp_path.glob("livepanel-*"))


def test_zero_render_frames_rejected(cli, tmp_path):
    run, outputs = cli
    result = run("render", "--duration", "0.01")
    assert result.returncode != 0 and "at least one frame" in result.stderr
    assert not (tmp_path / "browser.pid").exists()
    assert not list(outputs.iterdir())


@pytest.mark.parametrize("samples,png,repeat,ok", [
    (0, 0, False, False), (0, 0, True, False), (1, 0, True, False), (-1, 2, False, False),
    (2, -1, False, False), (2, 0, False, True), (0, 2, True, True),
])
def test_real_check_points(cli, tmp_path, samples, png, repeat, ok):
    run, outputs = cli
    result = run("check_frames", "--samples", str(samples), "--png", str(png), *(["--repeat"] if repeat else []))
    assert (result.returncode == 0) == ok, result.stdout + result.stderr
    if ok:
        assert (tmp_path / "measurements").read_text().count("measured") == samples + png
        assert len(list(outputs.glob("*.png"))) == png
    else:
        assert not (tmp_path / "browser.pid").exists()


@pytest.mark.parametrize("entry,mode", [
    ("render", "Page.navigate"), ("check_frames", "Page.navigate"),
    ("render", "active"), ("render", "Target.createTarget"), ("check_frames", "extract"),
])
def test_sigterm_cleans_and_reaps(cli, tmp_path, entry, mode):
    run, outputs = cli
    old = outputs / "movie.mp4"
    old.write_bytes(b"old")
    proc = run(entry, *(["--video", "good.mp4"] if mode == "extract" else []), mode=mode, background=True)
    try:
        deadline = time.monotonic() + 5
        while not (tmp_path / "ready").exists():
            assert proc.poll() is None and time.monotonic() < deadline
            time.sleep(0.02)
        if mode != "extract":
            page, = tmp_path.glob("livepanel-page-*/page.html")
            assert "synthetic configuration" in page.read_text()
        proc.terminate()
        proc.communicate(timeout=7)
        assert proc.returncode != 0
        assert not list(tmp_path.glob("livepanel-*"))
        assert list(outputs.iterdir()) == [old] and old.read_bytes() == b"old"
        pid_gone(tmp_path / "browser.pid")
        if mode in {"active", "extract"}:
            pid_gone(tmp_path / "encoder.pid")
    finally:
        # Also clean up the fake children if the CLI under test fails the signal check.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()


@pytest.mark.parametrize("entry", ["render", "check_frames"])
def test_handler_restored_after_import_and_main(tmp_path, entry):
    probe = """
import importlib, signal, sys
def previous(*args):
    pass
signal.signal(signal.SIGTERM, previous)
module = importlib.import_module(sys.argv[1])
assert signal.getsignal(signal.SIGTERM) is previous
sys.argv = [sys.argv[1], '--help']
try:
    module.main()
except SystemExit as exc:
    assert exc.code == 0
assert signal.getsignal(signal.SIGTERM) is previous
"""
    subprocess.run([sys.executable, "-B", "-c", probe, entry], cwd=SCRIPTS,
                   env=dict(os.environ, TMPDIR=str(tmp_path)), capture_output=True, check=True)


@pytest.mark.parametrize("entry", ["render", "check_frames"])
def test_missing_output_without_history(cli, entry):
    run, outputs = cli
    result = run(entry, *([] if entry == "render" else ["--video", "good.mp4"]), mode="missing")
    assert result.returncode != 0 and "missing or non-regular" in result.stderr
    assert not list(outputs.iterdir())


def test_replace_failure_rolls_back_delivered_files(tmp_path, monkeypatch):
    # Inject only the final rename error. The staging files, earlier renames and rollback are real.
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import livepanel

    original = Path.replace
    old, new, blocked = [tmp_path / name for name in ("old.png", "new.png", "blocked.png")]
    old.write_bytes(b"previous")
    blocked.write_bytes(b"blocked previous")

    def replace(source, target):
        if target == blocked:
            assert old.read_bytes() == new.read_bytes() == PNG
            raise PermissionError("injected rename failure")
        return original(source, target)

    monkeypatch.setattr(Path, "replace", replace)
    with pytest.raises(PermissionError, match="injected rename failure"):
        with livepanel.MediaOutputs() as batch:
            for path in [old, new, blocked]:
                batch.stage(path, "PNG").write_bytes(PNG)
            batch.publish()
    assert old.read_bytes() == b"previous" and blocked.read_bytes() == b"blocked previous"
    assert set(tmp_path.iterdir()) == {old, blocked}
