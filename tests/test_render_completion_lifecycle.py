"""Offline regressions: real temporary HTML/files, fake Chrome and encoders only."""

import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock
from urllib.parse import unquote, urlsplit

import pytest


ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "skills/multimodal-media/live-panel/scripts"
MERMAID = ROOT / "skills/office-white-collar/mermaid-tools/scripts"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC"
)


def load(directory, name, monkeypatch):
    spec = importlib.util.spec_from_file_location(name, directory / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(sys, "path", sys.path.copy())
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def panel_run(tmp_path, monkeypatch):
    lp = load(PANEL, "livepanel", monkeypatch)
    render = load(PANEL, "render", monkeypatch)
    checker = load(PANEL, "check_frames", monkeypatch)
    monkeypatch.setattr(render.tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(lp, "find_chrome", Mock(return_value="fake-chrome"))
    monkeypatch.setattr(lp, "find_exe", Mock(return_value="fake-ffmpeg"))
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"marker": "synthetic-private-config", "canvas": {
        "width": 100, "height": 80, "fps": 2, "duration": 1,
    }}))
    pages = []
    original_build = lp.build_page
    state = {"failure": None, "error_seek": None, "error_shot": None, "rc": 0, "diff": [0, 0]}

    def build(*args):
        page = Path(args[1])
        pages.append(page)
        cfg = original_build(*args)  # Real template and embedded config on disk.
        assert "synthetic-private-config" in page.read_text()
        if state["failure"] == "build":
            raise RuntimeError("build failed after writing")
        return cfg

    monkeypatch.setattr(lp, "build_page", build)

    class Page:
        def __init__(self):
            self.seeks = 0
            self.shots = 0
            self.error = ""
            self.closed = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.closed = True

        def open(self, url):
            assert "synthetic-private-config" in Path(unquote(urlsplit(url).path)).read_text()
            if state["failure"] == "open":
                raise RuntimeError("open failed")

        def seek(self, t):
            self.seeks += 1
            if state["error_seek"] == self.seeks:
                self.error = "synthetic seek failure"
            if state["failure"] == "seek":
                raise RuntimeError("seek failed")
            if state["failure"] == "interrupt":
                raise KeyboardInterrupt()

        def shot(self):
            self.shots += 1
            if state["failure"] == "shot":
                raise RuntimeError("shot failed")
            if state["error_shot"] == self.shots:
                self.error = "synthetic screenshot failure"
            return PNG

        def eval(self, expr):
            if expr == "window.__error||''":
                return self.error
            if expr == "window.__check()":
                if state["failure"] == "measure":
                    raise RuntimeError("measurement failed")
                return ["overflow"] if state["failure"] == "overflow" else []
            if "getImageData" in expr:
                return state["diff"]
            raise AssertionError(f"unexpected JS: {expr}")

    page = Page()

    def chrome(*args):
        if state["failure"] == "chrome":
            raise RuntimeError("chrome failed")
        return page

    launch = Mock(side_effect=chrome)
    monkeypatch.setattr(lp, "Chrome", launch)

    def write(data):
        if state["failure"] == "pipe":
            raise BrokenPipeError("pipe failed")
        return len(data)

    def close():
        if state["failure"] == "close":
            raise BrokenPipeError("close failed")

    pipe = Mock(write=Mock(side_effect=write), close=Mock(side_effect=close))
    encoder = Mock(stdin=pipe)
    encoder.wait.side_effect = lambda **kwargs: state["rc"]

    def popen(cmd, **kwargs):
        if state["failure"] == "encoder_start":
            raise OSError("encoder launch failed")
        Path(cmd[-1]).write_bytes(b"synthetic partial video")
        return encoder

    start = Mock(side_effect=popen)
    monkeypatch.setattr(render.subprocess, "Popen", start)
    video = Mock()
    monkeypatch.setattr(checker.subprocess, "run", video)

    def run(entry="render", explicit=False, extra=()):
        module = render if entry == "render" else checker
        args = [entry, "--config", str(config)]
        args += ["--out", str(tmp_path / "out.mp4"), "--keep-frames", str(tmp_path / "frames")] if entry == "render" else [
            "--out-dir", str(tmp_path / "frames"), "--samples", "1", "--png", "1",
        ]
        if explicit:
            args += ["--html-out", str(tmp_path / "kept.html")]
        monkeypatch.setattr(sys, "argv", [*args, *extra])
        return module.main()

    return type("Run", (), dict(run=staticmethod(run), state=state, pages=pages, page=page,
                               launch=launch, encoder=encoder, start=start, video=video,
                               render=render, checker=checker, tmp=tmp_path))


def assert_page_lifetime(run, explicit):
    assert len(run.pages) == 1
    page = run.pages[0]
    assert page.exists() == explicit
    if explicit:
        assert "synthetic-private-config" in page.read_text()
    else:
        assert not page.parent.exists()
    assert not list(run.tmp.glob("livepanel-page-*"))


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("entry", ["render", "check"])
def test_success_preserves_outputs_and_scopes_html(panel_run, entry, explicit, capsys):
    run = panel_run
    with pytest.raises(SystemExit) as exc:
        run.run(entry, explicit, ["--repeat"] if entry == "check" else [])
    assert exc.value.code == 0
    assert_page_lifetime(run, explicit)
    assert run.page.closed
    assert run.launch.call_args.args[-1] is False
    if entry == "render":
        assert run.encoder.stdin.write.call_count == 2
        run.encoder.stdin.close.assert_called_once()
        run.encoder.wait.assert_called_once_with(timeout=30)
        assert len(list((run.tmp / "frames").glob("*.png"))) == 2
        assert "wrote " in capsys.readouterr().err
    else:
        assert len(list((run.tmp / "frames").glob("*.png"))) == 1
        assert "identical" in capsys.readouterr().out
        run.start.assert_not_called()


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("failure", ["build", "chrome", "open", "encoder_start", "seek", "shot", "pipe", "close", "interrupt"])
def test_render_failures_clean_html_and_reap_encoder(panel_run, explicit, failure, capsys):
    run = panel_run
    run.state["failure"] = failure
    with pytest.raises((RuntimeError, OSError, KeyboardInterrupt)):
        run.run(explicit=explicit)
    assert_page_lifetime(run, explicit)
    err = capsys.readouterr().err
    assert "wrote " not in err
    if failure in {"seek", "shot", "pipe", "close", "interrupt"}:
        run.encoder.stdin.close.assert_called_once()
        run.encoder.wait.assert_called_once_with(timeout=30)
        assert "partial output" in err and "partial frames" in err
        assert run.page.closed
    else:
        run.encoder.wait.assert_not_called()


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("stage", ["seek", "shot"])
def test_late_page_error_fails_even_when_encoder_succeeds(panel_run, explicit, stage, capsys):
    run = panel_run
    run.state[f"error_{stage}"] = 2  # Startup and first frame succeeded.
    with pytest.raises(RuntimeError, match="page errors: synthetic"):
        run.run(explicit=explicit)
    assert run.encoder.stdin.write.call_count == 1
    run.encoder.stdin.close.assert_called_once()
    run.encoder.wait.assert_called_once_with(timeout=30)
    assert run.page.closed
    assert_page_lifetime(run, explicit)
    err = capsys.readouterr().err
    assert "wrote " not in err and "partial output" in err


@pytest.mark.parametrize("explicit", [False, True])
def test_encoder_nonzero_is_failure(panel_run, explicit, capsys):
    run = panel_run
    run.state["rc"] = 9
    with pytest.raises(RuntimeError, match="encoder exited with status 9"):
        run.run(explicit=explicit)
    assert_page_lifetime(run, explicit)
    assert "partial output" in capsys.readouterr().err


@pytest.mark.parametrize("kill", [False, True])
def test_stalled_encoder_is_reaped_and_fails(panel_run, kill, capsys):
    run = panel_run
    timeout = subprocess.TimeoutExpired("fake-ffmpeg", 30)
    run.encoder.wait.side_effect = [timeout, timeout, -9] if kill else [timeout, -15]
    with pytest.raises(RuntimeError, match="encoder did not finish"):
        run.run()
    run.encoder.terminate.assert_called_once()
    assert run.encoder.kill.call_count == int(kill)
    assert run.encoder.wait.call_count == (3 if kill else 2)
    assert_page_lifetime(run, False)
    assert "wrote " not in capsys.readouterr().err


def test_interruption_during_encoder_wait_still_reaps_it(panel_run):
    run = panel_run
    run.encoder.wait.side_effect = [KeyboardInterrupt(), -15]
    with pytest.raises(KeyboardInterrupt):
        run.run()
    run.encoder.terminate.assert_called_once()
    assert run.encoder.wait.call_count == 2
    assert_page_lifetime(run, False)


@pytest.mark.parametrize("entry", ["render", "check"])
@pytest.mark.parametrize("explicit", [False, True])
def test_frame_write_failure_scopes_html_and_reaps_encoder(panel_run, monkeypatch, entry, explicit):
    run = panel_run
    original = Path.write_bytes

    def write(path, data):
        if path.suffix == ".png":
            raise OSError("frame write failed")
        return original(path, data)

    monkeypatch.setattr(Path, "write_bytes", write)
    with pytest.raises(OSError, match="frame write failed"):
        run.run(entry, explicit)
    assert_page_lifetime(run, explicit)
    assert run.page.closed
    if entry == "render":
        run.encoder.stdin.close.assert_called_once()
        run.encoder.wait.assert_called_once_with(timeout=30)


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("failure", ["build", "chrome", "open", "seek", "shot", "measure", "interrupt"])
def test_checker_exception_paths_clean_html(panel_run, explicit, failure):
    run = panel_run
    run.state["failure"] = failure
    with pytest.raises((RuntimeError, KeyboardInterrupt)):
        run.run("check", explicit)
    assert_page_lifetime(run, explicit)
    run.start.assert_not_called()


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("seek_number", [1, 3, 4, 5])
def test_checker_detects_errors_in_sampling_export_and_repeat(panel_run, explicit, seek_number):
    run = panel_run
    run.state["error_seek"] = seek_number
    with pytest.raises(RuntimeError, match="synthetic seek failure"):
        run.run("check", explicit, ["--repeat"])
    assert_page_lifetime(run, explicit)
    assert run.page.closed


@pytest.mark.parametrize("failure", ["overflow", "replay", "video"])
def test_checker_reports_existing_failure_paths(panel_run, failure):
    run = panel_run
    run.state["failure"] = failure
    if failure == "replay":
        run.state["diff"] = [51, 255]
    if failure == "video":
        run.video.side_effect = subprocess.CalledProcessError(7, "fake-ffmpeg")
    expected = subprocess.CalledProcessError if failure == "video" else SystemExit
    extra = ["--video", "synthetic.mp4"] if failure == "video" else ["--repeat"]
    with pytest.raises(expected) as exc:
        run.run("check", extra=extra)
    if failure != "video":
        assert exc.value.code == 1
    assert_page_lifetime(run, False)


def test_checker_video_success_and_explicit_sandbox_flag(panel_run):
    run = panel_run
    with pytest.raises(SystemExit) as exc:
        run.run("check", extra=["--video", "synthetic.mp4", "--no-sandbox"])
    assert exc.value.code == 0
    run.video.assert_called_once()
    assert run.video.call_args.kwargs["check"] is True
    assert run.launch.call_args.args[-1] is True
    assert_page_lifetime(run, False)


@pytest.fixture
def mermaid_run(tmp_path):
    fixture = tmp_path / "fixture.png"
    fixture.write_bytes(PNG)
    log = tmp_path / "rendered.txt"
    out = tmp_path / "out with spaces"
    out.mkdir()
    source = tmp_path / "input.md"
    for name, body in {
        "mmdc": '''#!/bin/sh
while [ "$#" -gt 0 ]; do
    case "$1" in -i) input=$2; shift;; -o) output=$2; shift;; esac
    shift
done
printf '%s\\n' "$input" >> "$RENDER_LOG"
case "$RENDER_MODE" in
    fail) exit 8;;
    missing) exit 0;;
    invalid) printf invalid > "$output"; exit 0;;
esac
cp "$FIXTURE" "$output"
''',
        "identify": '#!/bin/sh\nprintf "1x1"\n',
        "stat": '#!/bin/sh\nwc -c < "$2"\n',
    }.items():
        tool = tmp_path / name
        tool.write_text(body)
        tool.chmod(0o755)
    env = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}", TMPDIR=str(tmp_path),
               PUPPETEER_EXECUTABLE_PATH=str(tmp_path / "mmdc"), FIXTURE=str(fixture), RENDER_LOG=str(log))

    def run(body, mode="success", direct=False):
        source.write_bytes(body)
        cmd = [sys.executable, MERMAID / "extract_diagrams.py"] if direct else ["bash", MERMAID / "extract-and-generate.sh"]
        result = subprocess.run([*cmd, source, out], cwd=tmp_path,
                                env=dict(env, RENDER_MODE=mode), capture_output=True, text=True)
        assert not list(tmp_path.glob("mermaid-batch.*"))
        return result

    return run, out, log


DIAGRAM = b"## Current chart\n```mermaid\ngraph TD\nA-->B\n```\n"


@pytest.mark.parametrize("direct", [False, True])
@pytest.mark.parametrize("old", [False, True])
def test_invalid_utf8_extraction_fails_without_rendering(mermaid_run, direct, old):
    run, out, log = mermaid_run
    if old:
        (out / "old.mmd").write_text("historical input")
    result = run(b"invalid UTF8: \xff", direct=direct)
    assert result.returncode != 0
    assert "Failed to extract diagrams" in result.stderr
    assert "Extracted 0 diagrams successfully" not in result.stdout
    assert not log.exists()
    assert not list(out.glob("*.png"))


@pytest.mark.parametrize("old", [False, True])
def test_valid_document_without_diagrams_is_success(mermaid_run, old):
    run, out, log = mermaid_run
    if old:
        (out / "old.mmd").write_text("historical input")
    result = run(b"# Valid Markdown\nNo diagrams here.\n")
    assert result.returncode == 0, result.stderr
    assert "Extracted 0 diagrams successfully" in result.stdout
    assert not log.exists()


@pytest.mark.parametrize("mode", ["success", "fail", "missing", "invalid"])
def test_only_current_manifest_is_rendered_and_png_failures_propagate(mermaid_run, mode):
    run, out, log = mermaid_run
    (out / "00-old.mmd").write_text("historical input")
    (out / "old.png").write_bytes(PNG)
    (out / "01-current-chart.png").write_bytes(PNG)  # Cannot mask a bad new render.
    result = run(DIAGRAM, mode)
    assert (result.returncode == 0) == (mode == "success"), result.stdout + result.stderr
    assert log.read_text().splitlines() == ["01-current-chart.mmd"]
    assert ("All PNG diagrams generated and validated successfully!" in result.stdout) == (mode == "success")
    assert "00-old" not in result.stdout and "old.png" not in result.stdout
    assert (out / "00-old.mmd").read_text() == "historical input"
    assert (out / "old.png").read_bytes() == PNG
    if mode == "success":
        assert (out / "01-current-chart.png").read_bytes() == PNG


def test_partial_extraction_write_failure_never_renders_a_batch(mermaid_run):
    run, out, log = mermaid_run
    (out / "02-blocked.mmd").mkdir()
    result = run(DIAGRAM + b"## Blocked\n```mermaid\ngraph LR\nB-->C\n```\n")
    assert result.returncode != 0
    assert "Failed to extract diagrams" in result.stderr
    assert (out / "01-current-chart.mmd").exists()
    assert not log.exists()
    assert not list(out.glob("*.png"))
