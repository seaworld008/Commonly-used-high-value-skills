"""Offline CLI regressions using real files and a synthetic mmdc executable."""

import base64
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/office-white-collar/mermaid-tools/scripts"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC"
)
CHART = "## Current chart\n```mermaid\ngraph TD\nA-->NEW\n```\n"


@pytest.fixture
def cli(tmp_path):
    tools = tmp_path / "fake tools"
    tools.mkdir()
    out = tmp_path / "out with spaces ' $ ;"
    out.mkdir()
    source = tmp_path / "input ' $ ;.md"
    log = tmp_path / "rendered.jsonl"
    fixture = tmp_path / "fixture.png"
    fixture.write_bytes(PNG)
    renderer = tools / "mmdc"
    renderer.write_text(f"#!{sys.executable}\n" + '''import json, os, pathlib, sys
args = sys.argv[1:]
src = pathlib.Path(args[args.index('-i') + 1])
dst = pathlib.Path(args[args.index('-o') + 1])
with open(os.environ['RENDER_LOG'], 'a') as log:
    log.write(json.dumps({'input': str(src.resolve()), 'output': str(dst), 'args': args}) + '\\n')
body = src.read_text()
mode = os.environ.get('RENDER_MODE', 'success')
if mode == 'fail' or 'FAIL_RENDER' in body:
    sys.exit(8)
if mode == 'missing':
    sys.exit(0)
png = pathlib.Path(os.environ['PNG_FIXTURE']).read_bytes()
if mode == 'truncated':
    png = png[:-12]
elif mode == 'bad-crc':
    png = png[:29] + bytes([png[29] ^ 1]) + png[30:]
elif mode == 'invalid':
    png = b'broken PNG'
dst.write_bytes(png)
''')
    renderer.chmod(0o755)
    identify = tools / "identify"
    identify.write_text("#!/bin/sh\n[ \"$INSPECT_FAIL\" = 1 ] && exit 3\nprintf '1x1'\n")
    identify.chmod(0o755)
    env = dict(os.environ, PATH=f"{tools}:{os.environ['PATH']}", TMPDIR=str(tmp_path),
               PUPPETEER_EXECUTABLE_PATH=str(renderer), RENDER_LOG=str(log), PNG_FIXTURE=str(fixture))

    def run(body=CHART, *, direct=False, mode="success", extra_env=None, missing=False):
        if not missing:
            source.write_bytes(body.encode() if isinstance(body, str) else body)
        manifest = tmp_path / "manifest"
        command = ([sys.executable, str(SCRIPTS / "extract_diagrams.py"), str(source), str(out),
                    "--manifest", str(manifest)] if direct else
                   ["bash", str(SCRIPTS / "extract-and-generate.sh"), str(source), str(out)])
        result = subprocess.run(command, env=dict(env, RENDER_MODE=mode, **(extra_env or {})),
                                cwd=tmp_path, capture_output=True, text=True)
        assert not list(tmp_path.glob("mermaid-batch.*")), result.stdout + result.stderr
        return result

    return run, out, log, tmp_path


@pytest.mark.parametrize("opening,closing", [
    ("```mermaid", "```"), ("``` mermaid", "```"), ("~~~mermaid", "~~~"),
    ("~~~~ \tmermaid", "~~~~~~"), ("`````\tmermaid", "`````"),
    ("   ~~~ mermaid title=example", "   ~~~~"),
])
def test_legal_fences_extract_and_render(cli, opening, closing):
    run, out, log, _ = cli
    result = run(f"## Current chart\n{opening}\ngraph TD\nA-->NEW\n{closing}\n")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (out / "01-current-chart.mmd").read_text() == "graph TD\nA-->NEW"
    assert (out / "01-current-chart.png").read_bytes() == PNG
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert len(calls) == 1
    assert Path(calls[0]["input"]).parent != out
    assert Path(calls[0]["output"]).parent != out


@pytest.mark.parametrize("outer,close", [("````markdown", "````"), ("~~~~markdown", "~~~~")])
def test_nested_example_is_not_a_diagram(cli, outer, close):
    run, out, log, _ = cli
    result = run(f"{outer}\n```mermaid\ngraph TD\nA-->B\n```\n{close}\n")
    assert result.returncode == 0, result.stderr
    assert "Extracted 0 diagrams successfully" in result.stdout
    assert not log.exists()
    assert list(out.iterdir()) == []


def test_fence_character_and_length_control_closing(cli):
    run, out, _, _ = cli
    result = run("## Current chart\n````mermaid\ngraph TD\n```\n~~~\nA-->NEW\n`````\n", direct=True)
    assert result.returncode == 0, result.stderr
    assert (out / "01-current-chart.mmd").read_text() == "graph TD\n```\n~~~\nA-->NEW"


def test_duplicate_content_uses_its_own_context_and_order(cli):
    run, out, _, tmp = cli
    result = run(CHART + CHART.replace("Current chart", "Second chart"), direct=True)
    assert result.returncode == 0, result.stderr
    assert (tmp / "manifest").read_bytes() == b"01-current-chart.mmd\0" + b"02-second-chart.mmd\0"
    assert (out / "02-second-chart.mmd").read_text() == "graph TD\nA-->NEW"


@pytest.mark.parametrize("body,expected", [
    ("~~~mermaid\ngraph TD\nA-->B", "graph TD\nA-->B"),
    ("   ```mermaid\n   graph TD\n   A-->B\n   ```", "graph TD\nA-->B"),
])
def test_eof_and_indentation_follow_fence_rules(cli, body, expected):
    run, out, _, _ = cli
    result = run(body, direct=True)
    assert result.returncode == 0, result.stderr
    assert (out / "diagram-01.mmd").read_text() == expected


@pytest.mark.parametrize("body", [
    "    ```mermaid\ngraph TD\nA-->B\n    ```\n",
    "```mermaidx\ngraph TD\nA-->B\n```\n",
    "```mermaid `invalid info`\ngraph TD\nA-->B\n```\n",
])
def test_non_mermaid_or_invalid_opening_does_not_create_diagrams(cli, body):
    run, out, log, tmp = cli
    result = run(body, direct=True)
    assert result.returncode == 0, result.stderr
    assert (tmp / "manifest").read_bytes() == b""
    assert list(out.iterdir()) == []
    assert not log.exists()


def test_empty_document_succeeds_without_renderer_dependencies(cli):
    run, _, log, tmp = cli
    (tmp / "fake tools" / "mmdc").unlink()
    result = run("# no diagrams", extra_env={"PUPPETEER_EXECUTABLE_PATH": str(tmp / "absent-chrome")})
    assert result.returncode == 0, result.stdout + result.stderr
    assert not log.exists()


@pytest.mark.parametrize("direct", [False, True])
@pytest.mark.parametrize("body", [b"# plain document\n", b"", b"```python\nprint('hello')\n```\n"])
def test_empty_manifest_is_success_and_never_renders_history(cli, direct, body):
    run, out, log, tmp = cli
    (out / "historical.mmd").write_text("old source")
    result = run(body, direct=direct)
    assert result.returncode == 0, result.stderr
    assert not log.exists()
    assert (out / "historical.mmd").read_text() == "old source"
    if direct:
        assert (tmp / "manifest").read_bytes() == b""


@pytest.mark.parametrize("direct", [False, True])
@pytest.mark.parametrize("bad", ["encoding", "missing"])
def test_unreadable_input_is_nonzero(cli, direct, bad):
    run, out, log, _ = cli
    (out / "historical.mmd").write_text("old source")
    result = run(b"bad UTF8 \xff", direct=direct, missing=bad == "missing")
    assert result.returncode != 0
    assert "Extracted 0 diagrams successfully" not in result.stdout
    assert not log.exists()
    assert (out / "historical.mmd").read_text() == "old source"


@pytest.mark.parametrize("direct", [False, True])
def test_directory_input_is_a_read_error(cli, direct):
    run, _, log, tmp = cli
    (tmp / "input ' $ ;.md").mkdir()
    result = run(direct=direct, missing=True)
    assert result.returncode != 0
    assert not log.exists()
    assert "Extracted 0 diagrams successfully" not in result.stdout


def old_pair(out):
    mmd, png = out / "01-current-chart.mmd", out / "01-current-chart.png"
    mmd.write_bytes(b"old source")
    png.write_bytes(b"old PNG")
    return mmd, png


@pytest.mark.parametrize("mode,env", [
    ("fail", {}), ("missing", {}), ("invalid", {}), ("truncated", {}), ("bad-crc", {}),
    ("success", {"INSPECT_FAIL": "1"}),
])
def test_render_failure_preserves_both_old_files(cli, mode, env):
    run, out, log, _ = cli
    mmd, png = old_pair(out)
    result = run(mode=mode, extra_env=env)
    assert result.returncode != 0, result.stdout + result.stderr
    assert mmd.read_bytes() == b"old source"
    assert png.read_bytes() == b"old PNG"
    assert len(log.read_text().splitlines()) == 1
    assert "All PNG diagrams generated" not in result.stdout
    diagnostics = list(out.glob("failed-mermaid.*"))
    assert len(diagnostics) == 1
    assert (diagnostics[0] / mmd.name).read_text() == "graph TD\nA-->NEW"
    assert not (diagnostics[0] / png.name).exists()


def test_success_replaces_both_files_and_does_not_render_history(cli):
    run, out, log, _ = cli
    mmd, png = old_pair(out)
    (out / "history.mmd").write_text("history")
    result = run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert mmd.read_text() == "graph TD\nA-->NEW"
    assert png.read_bytes() == PNG
    assert (out / "history.mmd").read_text() == "history"
    assert len(log.read_text().splitlines()) == 1
    assert not list(out.glob(".mermaid-publish.*"))


@pytest.mark.parametrize("blocked", ["mmd", "png"])
def test_publish_obstruction_preserves_existing_files(cli, blocked):
    run, out, _, _ = cli
    mmd, png = old_pair(out)
    target = mmd if blocked == "mmd" else png
    target.unlink()
    target.mkdir()
    (target / "user-data").write_text("keep")
    result = run()
    assert result.returncode != 0, result.stdout + result.stderr
    assert (target / "user-data").read_text() == "keep"
    remaining = png if blocked == "mmd" else mmd
    assert remaining.read_bytes() == (b"old PNG" if blocked == "mmd" else b"old source")


@pytest.mark.parametrize("linked", ["mmd", "png"])
def test_publishing_refuses_symlinks_without_touching_referents(cli, linked):
    run, out, _, tmp = cli
    mmd, png = old_pair(out)
    target = mmd if linked == "mmd" else png
    protected = tmp / "user-owned-file"
    protected.write_bytes(b"protected data")
    target.unlink()
    target.symlink_to(protected)
    result = run()
    assert result.returncode != 0
    assert "refusing non-regular publication file" in result.stderr
    assert target.is_symlink()
    assert protected.read_bytes() == b"protected data"
    remaining = png if linked == "mmd" else mmd
    assert remaining.read_bytes() == (b"old PNG" if linked == "mmd" else b"old source")


@pytest.mark.parametrize("existing", [True, False])
def test_second_replace_failure_rolls_back_first(cli, existing):
    run, out, _, tmp = cli
    if existing:
        old_pair(out)
    # Inject an OS publication error in the real CLI process, after one replace.
    hooks = tmp / "fault injection"
    hooks.mkdir()
    marker = tmp / "fault-fired"
    (hooks / "sitecustomize.py").write_text('''import os
from pathlib import Path
real_replace = os.replace
def fail_second(src, dst, *args, **kwargs):
    marker = Path(os.environ['FAULT_MARKER'])
    if str(dst).endswith('01-current-chart.png') and not marker.exists():
        marker.write_text('injected publication failure')
        raise OSError('synthetic second replace failure')
    return real_replace(src, dst, *args, **kwargs)
os.replace = fail_second
''')
    result = run(extra_env={"PYTHONPATH": str(hooks), "FAULT_MARKER": str(marker)})
    assert marker.exists(), result.stdout + result.stderr
    assert result.returncode != 0
    assert "synthetic second replace failure" in result.stderr
    if existing:
        assert (out / "01-current-chart.mmd").read_bytes() == b"old source"
        assert (out / "01-current-chart.png").read_bytes() == b"old PNG"
    else:
        assert not (out / "01-current-chart.mmd").exists()
        assert not (out / "01-current-chart.png").exists()
    assert not list(out.glob(".mermaid-publish.*"))


@pytest.mark.parametrize("copy_target", ["new-0", "new-1", "old-0", "old-1"])
def test_copy_or_backup_failure_keeps_both_public_files(cli, copy_target):
    run, out, _, tmp = cli
    old_pair(out)
    hooks = tmp / "copy fault injection"
    hooks.mkdir()
    (hooks / "sitecustomize.py").write_text('''import os, shutil
real_copy = shutil.copy2
def fail_copy(src, dst, *args, **kwargs):
    if str(dst).endswith('/' + os.environ['FAIL_COPY_TARGET']):
        raise OSError('synthetic publication copy failure')
    return real_copy(src, dst, *args, **kwargs)
shutil.copy2 = fail_copy
''')
    result = run(extra_env={"PYTHONPATH": str(hooks), "FAIL_COPY_TARGET": copy_target})
    assert result.returncode != 0
    assert "synthetic publication copy failure" in result.stderr
    assert (out / "01-current-chart.mmd").read_bytes() == b"old source"
    assert (out / "01-current-chart.png").read_bytes() == b"old PNG"
    assert not list(out.glob(".mermaid-publish.*"))


def test_partial_staged_extraction_failure_never_renders_history(cli):
    run, out, log, tmp = cli
    old_pair(out)
    (out / "history.mmd").write_text("historical source")
    hooks = tmp / "extraction fault injection"
    hooks.mkdir()
    (hooks / "sitecustomize.py").write_text('''import builtins
real_open = builtins.open
def fail_second_input(file, mode='r', *args, **kwargs):
    if str(file).endswith('/02-second-chart.mmd') and 'w' in mode:
        raise OSError('synthetic staged extraction write failure')
    return real_open(file, mode, *args, **kwargs)
builtins.open = fail_second_input
''')
    result = run(CHART + CHART.replace("Current chart", "Second chart"), extra_env={"PYTHONPATH": str(hooks)})
    assert result.returncode != 0
    assert "Failed to extract diagrams" in result.stderr
    assert not log.exists()
    assert (out / "01-current-chart.mmd").read_bytes() == b"old source"
    assert (out / "01-current-chart.png").read_bytes() == b"old PNG"
    assert (out / "history.mmd").read_text() == "historical source"


def test_mixed_batch_aggregates_failures_and_publishes_successes(cli):
    run, out, log, _ = cli
    old_pair(out)
    result = run(CHART.replace("NEW", "FAIL_RENDER") + CHART.replace("Current chart", "Good chart")
                 + CHART.replace("Current chart", "Bad chart").replace("NEW", "FAIL_RENDER"))
    assert result.returncode != 0
    assert "01-current-chart.png" in result.stderr and "03-bad-chart.png" in result.stderr
    assert len(log.read_text().splitlines()) == 3
    assert (out / "01-current-chart.mmd").read_bytes() == b"old source"
    assert (out / "01-current-chart.png").read_bytes() == b"old PNG"
    assert (out / "02-good-chart.mmd").read_text() == "graph TD\nA-->NEW"
    assert (out / "02-good-chart.png").read_bytes() == PNG
    assert not (out / "03-bad-chart.mmd").exists()
    assert not (out / "03-bad-chart.png").exists()


def test_rollback_failure_is_explicit_and_keeps_original_backup(cli):
    run, out, _, tmp = cli
    old_pair(out)
    hooks = tmp / "rollback fault injection"
    hooks.mkdir()
    (hooks / "sitecustomize.py").write_text('''import os
real_replace = os.replace
def fail_publish_and_restore(src, dst, *args, **kwargs):
    if str(dst).endswith('01-current-chart.png') or str(src).endswith('old-0'):
        raise OSError('synthetic persistent filesystem failure')
    return real_replace(src, dst, *args, **kwargs)
os.replace = fail_publish_and_restore
''')
    result = run(extra_env={"PYTHONPATH": str(hooks)})
    assert result.returncode != 0
    assert "rollback incomplete" in result.stderr
    assert "recovery files retained" in result.stderr
    assert "All PNG diagrams generated" not in result.stdout
    backups = list(out.glob(".mermaid-publish.*"))
    assert len(backups) == 1
    assert (backups[0] / "old-0").read_bytes() == b"old source"
    assert (backups[0] / "old-1").read_bytes() == b"old PNG"
    assert (out / "01-current-chart.png").read_bytes() == b"old PNG"
