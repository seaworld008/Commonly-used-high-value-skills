"""Offline boundary regressions for the bundled command-line helpers."""

import base64
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import Mock

import pytest


SKILLS = Path(__file__).resolve().parents[1] / "skills"
MEDIA = SKILLS / "multimodal-media"
IMAGE = MEDIA / "gpt-image2/scripts/gpt-image2.mjs"
PANEL = MEDIA / "live-panel/scripts"
MERMAID = SKILLS / "office-white-collar/mermaid-tools/scripts"
GUARD = SKILLS / "openclaw-memory-and-safety/input-guard/scripts"


def load_script(directory, name, monkeypatch):
    spec = importlib.util.spec_from_file_location(name, directory / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(sys, "path", sys.path.copy())
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(("flags", "env", "dotenv", "reads", "expected"), [
    ([], {}, "", [], "缺少接口配置"),
    ([], {"OPENAI_API_KEY": "fake"}, "", [], "缺少接口配置"),
    (["--use-codex-auth", "--base-url", "https://cli.invalid", "--api-key", "fake"],
     {"OPENAI_BASE_URL": "https://env.invalid"}, "", [], "https://cli.invalid"),
    (["--use-codex-auth"], {"OPENAI_BASE_URL": "https://env.invalid"},
     "GPT_IMAGE2_BASE_URL=https://dotenv.invalid\nGPT_IMAGE2_API_KEY=fake", [], "https://env.invalid"),
    (["--use-codex-auth"], {}, "OPENAI_BASE_URL=https://dotenv.invalid",
     ["auth.json"], "https://dotenv.invalid"),
    (["--use-codex-auth"], {"OPENAI_API_KEY": "fake"}, "", ["config.toml"], "https://codex.invalid"),
    (["--use-codex-auth"], {}, "", ["auth.json", "config.toml"], "https://codex.invalid"),
])
def test_image_codex_probes(tmp_path, flags, env, dotenv, reads, expected):
    script = shutil.copy(IMAGE, tmp_path)
    (tmp_path / ".env").write_text(dotenv)
    preload = tmp_path / "mock.cjs"
    preload.write_text(r"""
        const fs = require("node:fs");
        const path = require("node:path");
        const files = {
          "config.toml": 'model_provider = "test"\n[model_providers.test]\nbase_url = "https://codex.invalid"',
          "auth.json": '{"OPENAI_API_KEY":"fake"}',
        };
        for (const method of ["existsSync", "readFileSync"]) {
          const original = fs[method];
          fs[method] = function(file, ...args) {
            if (!String(file).split(path.sep).includes(".codex")) return original(file, ...args);
            const name = path.basename(file);
            console.error(method + " " + name);
            return method === "existsSync" ? name in files : files[name];
          };
        }
        global.fetch = () => { throw Error("unexpected network call"); };
    """)
    result = subprocess.run(
        ["node", "--require", preload, script, "--dry-run", "example", *flags],
        cwd=tmp_path, env={"PATH": os.environ["PATH"], "HOME": str(tmp_path), **env},
        capture_output=True, text=True,
    )
    if expected == "缺少接口配置":
        assert result.returncode != 0 and expected in result.stderr
    else:
        assert result.returncode == 0, result.stderr
        assert expected + "/images/generations" in result.stdout
    for method in ("existsSync", "readFileSync"):
        assert sorted(line.split()[1] for line in result.stderr.splitlines()
                      if line.startswith(method + " ")) == reads


@pytest.mark.parametrize("kwargs", [{}, {"no_sandbox": False}, {"no_sandbox": None}, {"no_sandbox": True}])
def test_root_chrome_flags(kwargs, tmp_path, monkeypatch):
    panel = load_script(PANEL, "livepanel", monkeypatch)
    monkeypatch.setattr(panel.os, "geteuid", lambda: 0, raising=False)
    monkeypatch.setattr(panel.tempfile, "tempdir", str(tmp_path))
    launch = Mock()
    monkeypatch.setattr(panel.subprocess, "Popen", launch)
    monkeypatch.setattr(panel.Chrome, "call", Mock(side_effect=RuntimeError("closed pipe")))
    with pytest.raises(RuntimeError, match="rendering unverified"):
        panel.Chrome("fake-chrome", 200, 100, **kwargs)
    launch.assert_called_once()
    assert ("--no-sandbox" in launch.call_args.args[0]) == (kwargs.get("no_sandbox") is True)
    launch.return_value.terminate.assert_called_once()


@pytest.mark.parametrize("flags", [[], ["--no-sandbox"]])
def test_render_cli_flags(flags, tmp_path, monkeypatch):
    panel = load_script(PANEL, "livepanel", monkeypatch)
    render = load_script(PANEL, "render", monkeypatch)
    monkeypatch.setattr(sys, "argv", ["render", "--config", "fixture", "--out", str(tmp_path / "out.mp4"), *flags])
    monkeypatch.setattr(render.tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(panel, "find_chrome", Mock(return_value="chrome"))
    monkeypatch.setattr(panel, "find_exe", Mock(return_value="ffmpeg"))
    monkeypatch.setattr(panel, "build_page", Mock(return_value={}))
    chrome = Mock(side_effect=RuntimeError("Chrome startup failed"))
    monkeypatch.setattr(panel, "Chrome", chrome)
    encoder = Mock()
    monkeypatch.setattr(render.subprocess, "Popen", encoder)
    with pytest.raises(RuntimeError, match="Chrome startup failed"):
        render.main()
    chrome.assert_called_once_with("chrome", 1200, 1500, bool(flags))
    encoder.assert_not_called()


def test_mermaid_config():
    args = json.loads((MERMAID / "puppeteer-config.json").read_text())["args"]
    assert {"--no-sandbox", "--disable-setuid-sandbox"}.isdisjoint(args)


@pytest.mark.parametrize("fail", [False, True])
def test_mermaid_batch(tmp_path, fail):
    names = ["good", "missing", "invalid", "failed", "truncated", "corrupt", "inspection", "last"]
    markdown = tmp_path / "input.md"
    markdown.write_text("".join(f"## {name}\n```mermaid\ngraph TD\nA-->{name}\n```\n" for name in names))
    png = tmp_path / "fixture.png"
    png.write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC"
    ))
    out = tmp_path / "out"
    out.mkdir()
    shutil.copy(png, out / "02-missing.png")  # Old output must not mask a failure.
    mmdc = tmp_path / "mmdc"
    mmdc.write_text("""#!/bin/sh
        while [ "$1" != "-o" ]; do shift; done
        output=$2
        if [ "$FAIL" = 1 ]; then
            case "$output" in
                *missing.png) exit 0 ;;
                *invalid.png) echo invalid > "$output"; exit 0 ;;
                *failed.png) exit 2 ;;
                *truncated.png) head -c 33 "$FIXTURE" > "$output"; exit 0 ;;
                *corrupt.png) cp "$FIXTURE" "$output"
                    printf X | dd of="$output" bs=1 seek=43 conv=notrunc 2>/dev/null; exit 0 ;;
            esac
        fi
        cp "$FIXTURE" "$output"
    """)
    mmdc.chmod(0o755)
    # The supported Linux/WSL environment uses GNU stat.
    stat = tmp_path / "stat"
    stat.write_text('#!/bin/sh\nwc -c < "$2"\n')
    stat.chmod(0o755)
    identify = tmp_path / "identify"
    identify.write_text('#!/bin/sh\ncase "$FAIL:$3" in 1:*inspection.png) exit 1;; esac\necho 1x1\n')
    identify.chmod(0o755)
    result = subprocess.run(
        ["bash", MERMAID / "extract-and-generate.sh", markdown, out], cwd=tmp_path,
        env={"PATH": f"{tmp_path}:{os.environ['PATH']}", "HOME": str(tmp_path),
             "TMPDIR": str(tmp_path), "PUPPETEER_EXECUTABLE_PATH": str(mmdc),
             "FIXTURE": str(png), "FAIL": str(int(fail))},
        capture_output=True, text=True,
    )
    assert (result.returncode != 0) == fail, result.stdout + result.stderr
    assert ("All PNG diagrams generated and validated successfully!" in result.stdout) == (not fail)
    assert (out / "08-last.png").read_bytes() == png.read_bytes()
    if fail:
        assert "Failed PNGs (6)" in result.stderr
        for index, name in enumerate(names[1:-1], 2):
            assert f"{index:02d}-{name}.png" in result.stderr


@pytest.fixture
def taxonomy(tmp_path, monkeypatch):
    module = load_script(GUARD, "get_taxonomy", monkeypatch)
    package = tmp_path / "package"
    package.mkdir()
    bundled = package / "taxonomy.json"
    bundled.write_text('{"categories": [{"name": "bundled"}]}')
    os.utime(bundled, (100, 100))
    monkeypatch.setattr(module, "SKILL_ROOT", package)
    monkeypatch.setattr(module, "TAXONOMY_FILE", bundled)
    monkeypatch.setenv("PROMPTINTEL_API_KEY", "fixture")
    monkeypatch.delenv("INPUT_GUARD_TAXONOMY_CACHE", raising=False)
    return module


def test_taxonomy_reads_are_offline(taxonomy, tmp_path, monkeypatch, capsys):
    fetch = Mock(side_effect=AssertionError("unexpected taxonomy request"))
    monkeypatch.setattr(taxonomy, "fetch_taxonomy", fetch)
    cache = tmp_path / "unused" / "taxonomy.json"
    monkeypatch.setenv("INPUT_GUARD_TAXONOMY_CACHE", str(cache))
    for action in ("show", "prompt"):
        monkeypatch.setattr(sys, "argv", ["get_taxonomy.py", action])
        taxonomy.main()
        assert "bundled" in capsys.readouterr().out

    monkeypatch.setitem(sys.modules, "requests", Mock())
    scanner = load_script(GUARD, "llm_scanner", monkeypatch)
    monkeypatch.setattr(scanner, "_detect_provider", lambda: ("openai", "fixture", "mock-model"))
    model = Mock(return_value={"choices": [{"message": {"content": '{"verdict":"SAFE"}'}}]})
    monkeypatch.setattr(scanner, "_call_openai", model)
    assert scanner.scan_with_llm("fixture").verdict == "SAFE"
    assert "bundled" in model.call_args.args[2]
    assert taxonomy.TAXONOMY_FILE.stat().st_mtime == 100
    assert not cache.parent.exists()
    taxonomy.TAXONOMY_FILE.unlink()
    assert taxonomy.get_taxonomy() is None
    fetch.assert_not_called()


def test_taxonomy_refresh_and_clear(taxonomy, tmp_path, monkeypatch, capsys):
    cache = tmp_path / "task-cache" / "taxonomy.json"
    fresh = {"categories": [{"name": "refreshed"}]}
    fetch = Mock(return_value={"data": fresh})
    monkeypatch.setattr(taxonomy, "fetch_taxonomy", fetch)
    for action in ("fetch", "refresh"):
        monkeypatch.setattr(sys, "argv", ["get_taxonomy.py", action, "--cache-file", str(cache)])
        taxonomy.main()
        assert json.loads(cache.read_text()) == fresh
    assert fetch.call_count == 2
    assert taxonomy.get_taxonomy(cache_file=cache) == fresh
    assert taxonomy.get_taxonomy()["categories"][0]["name"] == "bundled"
    fetch.side_effect = OSError("offline")
    assert taxonomy.get_taxonomy(force_refresh=True, cache_file=cache) is None
    assert json.loads(cache.read_text()) == fresh

    monkeypatch.setenv("INPUT_GUARD_TAXONOMY_CACHE", str(cache))
    monkeypatch.setattr(sys, "argv", ["get_taxonomy.py", "clear"])
    taxonomy.main()
    assert not cache.exists()
    assert taxonomy.TAXONOMY_FILE.stat().st_mtime == 100

    fetch.reset_mock()
    alias = tmp_path / "alias"
    alias.symlink_to(taxonomy.TAXONOMY_FILE)
    for target in (taxonomy.TAXONOMY_FILE, alias):
        monkeypatch.setenv("INPUT_GUARD_TAXONOMY_CACHE", str(target))
        with pytest.raises(ValueError, match="outside the skill"):
            taxonomy.main()  # clear
        with pytest.raises(ValueError, match="outside the skill"):
            taxonomy.get_taxonomy(force_refresh=True)
    monkeypatch.delenv("INPUT_GUARD_TAXONOMY_CACHE")
    assert taxonomy.get_taxonomy(force_refresh=True) is None
    monkeypatch.delenv("PROMPTINTEL_API_KEY")
    assert taxonomy.get_taxonomy(force_refresh=True, cache_file=cache) is None
    assert "PROMPTINTEL_API_KEY not set" in capsys.readouterr().err
    fetch.assert_not_called()
