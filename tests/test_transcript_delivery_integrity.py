"""Real SQLite/dataclass and OOXML regressions; providers/Office/browser are fake.

Requires pytest, httpx and openpyxl. Run with --basetemp under the task TMPDIR.
"""
import importlib.util
import json
import logging
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import types
from unittest.mock import Mock
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET
import zipfile

import httpx
import pytest
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/office-white-collar/transcript-fixer/scripts"
XLSX = ROOT / "skills/office-white-collar/xlsx/scripts"
MANIFEST_ENV = "TRANSCRIPT_FIXER_OUTPUT_MANIFEST"


def load(path, name, monkeypatch):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def isolation(tmp_path, monkeypatch):
    home, task_tmp = tmp_path / "home", tmp_path / "tmp"
    home.mkdir()
    task_tmp.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("TMPDIR", str(task_tmp))
    monkeypatch.setattr(tempfile, "tempdir", str(task_tmp))
    monkeypatch.setattr(sys, "path", sys.path.copy())
    for key in list(os.environ):
        if key.startswith("TRANSCRIPT_FIXER_") or key in (
            "GLM_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"
        ):
            monkeypatch.delenv(key)


@pytest.fixture
def transcript(monkeypatch):
    # Load real core/parser/service/repository, excluding unrelated utils exports.
    for key in list(sys.modules):
        if key.split(".")[0] in ("core", "cli", "utils"):
            monkeypatch.delitem(sys.modules, key)
    monkeypatch.syspath_prepend(str(SCRIPTS))
    utils = types.ModuleType("utils")
    utils.__path__ = [str(SCRIPTS / "utils")]
    utils.validate_configuration = Mock()
    utils.print_validation_summary = Mock()
    monkeypatch.setitem(sys.modules, "utils", utils)
    core = load(SCRIPTS / "core/__init__.py", "core", monkeypatch)
    config = load(SCRIPTS / "utils/config.py", "utils.config", monkeypatch)
    commands = load(SCRIPTS / "cli/commands.py", "cli.commands", monkeypatch)
    entry = load(SCRIPTS / "fix_transcription.py", "delivery_entry", monkeypatch)
    wrapper = load(SCRIPTS / "fix_transcript_enhanced.py", "delivery_wrapper", monkeypatch)
    cfg = config.Config.from_env()
    config.set_config(cfg)
    monkeypatch.setenv("GLM_API_KEY", "synthetic-test-key")
    return types.SimpleNamespace(core=core, config=cfg, commands=commands,
                                 entry=entry, wrapper=wrapper,
                                 ai=sys.modules["core.ai_processor_async"])


def run_cli(module, source, monkeypatch, stage=2):
    monkeypatch.setattr(sys, "argv", ["core", "--input", str(source), "--stage", str(stage)])
    module.entry.main()


@pytest.mark.parametrize("stage", [1, 2, 3])
def test_wrapper_delivers_only_current_outputs(stage, transcript, tmp_path, monkeypatch, capsys):
    source_dir, dest = tmp_path / "source", tmp_path / "dest"
    source_dir.mkdir()
    dest.mkdir()
    source = source_dir / "input.md"
    source.write_text("synthetic transcript")
    old = {}
    for directory in (source_dir, dest):
        for suffix in ("_stage2.md", "_对比.html", "_对比报告.md", "_修复报告.md"):
            path = directory / ("input" + suffix)
            path.write_bytes((directory.name + suffix).encode())
            old[path] = path.read_bytes()
    monkeypatch.setattr(transcript.ai.AIProcessorAsync, "process",
                        lambda self, text: ("corrected transcript", []))
    wrapper = transcript.wrapper
    monkeypatch.setattr(wrapper.path_validator, "validate_input_path", lambda _: source)
    browser = Mock()
    monkeypatch.setattr(wrapper, "open_html_in_browser", browser)
    calls = []

    def child(cmd, **kwargs):
        calls.append(cmd)
        with monkeypatch.context() as patch:
            patch.setattr(sys, "argv", ["core", *cmd[cmd.index("--input"):]])
            for key, value in kwargs.get("env", {}).items():
                patch.setenv(key, value)
            transcript.entry.main()
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(wrapper.subprocess, "run", child)
    monkeypatch.setattr(sys, "argv", ["wrapper", str(source), "--output", str(dest),
                                     "--stage", str(stage), "--auto-open"])
    wrapper.main()
    out = capsys.readouterr().out
    assert "--output" in calls[0]
    assert Path(calls[0][calls[0].index("--output") + 1]) == dest
    assert (dest / "input_stage1.md").read_text() == "synthetic transcript"
    assert not (source_dir / "input_stage1.md").exists()
    for path, content in old.items():
        if path == dest / "input_stage2.md" and stage >= 2:
            assert path.read_text() == "corrected transcript"
        else:
            assert path.read_bytes() == content
    assert "   - input_stage1.md" in out
    assert ("   - input_stage2.md" in out) == (stage >= 2)
    assert "   - input_对比.html" not in out
    browser.assert_not_called()


@pytest.mark.parametrize("auto_open", [False, True])
@pytest.mark.parametrize("generated", [None, False, True])
def test_wrapper_opens_only_manifest_html(auto_open, generated, transcript, tmp_path, monkeypatch):
    source = tmp_path / "input.md"
    source.write_text("synthetic")
    html = tmp_path / "input_对比.html"
    html.write_text("old html")
    wrapper = transcript.wrapper
    monkeypatch.setattr(wrapper.path_validator, "validate_input_path", lambda _: source)
    browser = Mock()
    monkeypatch.setattr(wrapper, "open_html_in_browser", browser)

    def child(cmd, **kwargs):
        manifest = kwargs.get("env", {}).get(MANIFEST_ENV)
        outputs = []
        if generated:
            html.write_text("current diff")
            outputs.append(str(html))
            for suffix in ("_stage1.md", "_stage2.md"):
                text = tmp_path / ("input" + suffix)
                text.write_text("current text")
                outputs.append(str(text))
        if manifest and generated is not None:
            Path(manifest).write_text(json.dumps({"outputs": outputs}))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(wrapper.subprocess, "run", child)
    monkeypatch.setattr(sys, "argv", ["wrapper", str(source), "--stage", "3",
                                     *(["--auto-open"] if auto_open else [])])
    if generated:
        wrapper.main()
    else:
        with pytest.raises(SystemExit) as exc:
            wrapper.main()
        assert exc.value.code == 1
    assert browser.call_count == int(bool(auto_open and generated))
    if not generated:
        assert html.read_text() == "old html"


def seed_learning(module):
    cfg = module.config
    cfg.features.enable_learning = True
    cfg.features.enable_auto_approval = False
    cfg.database.path.parent.mkdir(parents=True)
    service = module.core.CorrectionService(module.core.CorrectionRepository(cfg.database.path))
    service.add_correction("wrng", "right", "general")
    with service.repository._transaction() as conn:
        conn.execute("INSERT INTO context_rules (pattern, replacement, description) VALUES (?, ?, ?)",
                     ("bot", "robot", "synthetic rule"))
    service.close()


def fake_dataclass_ai(module, monkeypatch):
    change = module.ai.AIChange(1, "helo", "hello", 0.99,
                               "right ", " robot", "replacement")
    monkeypatch.setattr(module.ai.AIProcessorAsync, "process",
                        lambda self, text: ("right hello robot", [change]))
    return change


def test_learning_persists_real_history_and_dataclass_details(transcript, tmp_path, monkeypatch, capsys):
    seed_learning(transcript)
    fake_dataclass_ai(transcript, monkeypatch)
    source = tmp_path / "input.md"
    source.write_text("wrng helo bot")
    run_cli(transcript, source, monkeypatch)
    with sqlite3.connect(transcript.config.database.path) as conn:
        history = conn.execute("SELECT stage1_changes, stage2_changes, success FROM correction_history").fetchall()
        details = conn.execute("SELECT from_text, to_text, rule_type, context_before, context_after "
                               "FROM correction_changes ORDER BY id").fetchall()
    assert history == [(2, 1, 1)]
    assert len(details) == 3
    assert ("helo", "hello", "ai", "right ", " robot") in details
    assert {row[2] for row in details} == {"context", "dictionary", "ai"}
    assert "Correction complete!" in capsys.readouterr().out
    assert (tmp_path / "input_stage2.md").read_text() == "right hello robot"


@pytest.mark.parametrize("table", ["correction_history", "correction_changes"])
def test_sqlite_failure_rolls_back_and_reports_unsaved_text_separately(
    table, transcript, tmp_path, monkeypatch, capsys
):
    seed_learning(transcript)
    fake_dataclass_ai(transcript, monkeypatch)
    with sqlite3.connect(transcript.config.database.path) as conn:
        conn.execute(f"CREATE TRIGGER reject_save BEFORE INSERT ON {table} "
                     "BEGIN SELECT RAISE(ABORT, 'synthetic storage failure'); END")
    closed = []
    close = transcript.core.CorrectionService.close

    def tracked_close(service):
        close(service)
        closed.append(service)

    monkeypatch.setattr(transcript.core.CorrectionService, "close", tracked_close)
    source = tmp_path / "input.md"
    source.write_text("wrng helo bot")
    with pytest.raises(SystemExit) as exc:
        run_cli(transcript, source, monkeypatch)
    assert exc.value.code == 1
    assert (tmp_path / "input_stage2.md").read_text() == "right hello robot"
    with sqlite3.connect(transcript.config.database.path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM correction_history").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM correction_changes").fetchone()[0] == 0
    out = capsys.readouterr().out
    assert "History not saved" in out
    assert "Text output saved" in out
    assert "Correction complete!" not in out
    assert not (transcript.config.paths.config_dir / "learned").exists()
    assert len(closed) == 1
    assert closed[0].repository._pool._pool.empty()


def test_service_accepts_existing_dict_changes(transcript):
    seed_learning(transcript)
    service = transcript.commands._get_service()
    try:
        service.save_history("synthetic.md", "general", 5, 1, 0, "test",
                             [{"line_number": 4, "from_text": "a", "to_text": "b",
                               "rule_type": "dictionary"}])
    finally:
        service.close()
    with sqlite3.connect(transcript.config.database.path) as conn:
        assert conn.execute("SELECT line_number, from_text, to_text, rule_type FROM correction_changes").fetchall() == [
            (4, "a", "b", "dictionary")]


@pytest.mark.parametrize("existing", [False, True])
def test_learning_disabled_keeps_store_byte_identical(existing, transcript, tmp_path, monkeypatch):
    if existing:
        seed_learning(transcript)
        transcript.config.features.enable_learning = False
    fake_dataclass_ai(transcript, monkeypatch)
    before = {p.relative_to(Path.home()): p.read_bytes() for p in Path.home().rglob("*") if p.is_file()}
    source = tmp_path / "input.md"
    source.write_text("wrng helo bot")
    run_cli(transcript, source, monkeypatch)
    assert (tmp_path / "input_stage2.md").read_text() == "right hello robot"
    after = {p.relative_to(Path.home()): p.read_bytes() for p in Path.home().rglob("*") if p.is_file()}
    assert after == before


@pytest.mark.parametrize("mode, models", [
    ("primary", ["GLM-4.6"]),
    ("fallback", ["GLM-4.6", "GLM-4.5-Air"]),
    ("both_fail", ["GLM-4.6", "GLM-4.5-Air"]),
    ("transient", ["GLM-4.6"] * 3 + ["GLM-4.5-Air"]),
])
def test_real_async_cli_fallback_status_and_private_logs(
    mode, models, transcript, tmp_path, monkeypatch, caplog, capsys
):
    secret = "SYNTHETIC_PRIVATE_TRANSCRIPT_123"
    source = tmp_path / "input.md"
    source.write_text(secret)
    calls = []

    async def provider(self, chunk, context, model):
        calls.append(model)
        if mode == "both_fail" or (mode != "primary" and model == self.model):
            if mode == "transient":
                raise httpx.ConnectError(secret)
            raise ValueError(secret)
        return "corrected text"

    async def no_delay(_):
        pass

    monkeypatch.setattr(transcript.ai.AIProcessorAsync, "_process_chunk_async", provider)
    monkeypatch.setattr(transcript.ai.asyncio, "sleep", no_delay)
    with caplog.at_level(logging.DEBUG):
        if mode == "both_fail":
            with pytest.raises(SystemExit) as exc:
                run_cli(transcript, source, monkeypatch)
            assert exc.value.code == 1
        else:
            run_cli(transcript, source, monkeypatch)
    out = capsys.readouterr().out
    assert calls == models
    assert secret not in out
    assert secret not in caplog.text
    assert all(secret not in str(record.__dict__) for record in caplog.records)
    assert "TypeError" not in out + caplog.text
    if mode == "both_fail":
        assert not (tmp_path / "input_stage2.md").exists()
        assert "Correction complete!" not in out
        assert "AI correction failed" in out
    else:
        assert (tmp_path / "input_stage2.md").read_text() == "corrected text"
        assert "Correction complete!" in out
    assert any(getattr(record, "chunk_index", None) == 1 for record in caplog.records)


@pytest.mark.parametrize("failure", [False, True])
def test_async_chunk_order_cleanup_and_failure_cause(failure, transcript, monkeypatch, caplog):
    processor = transcript.ai.AIProcessorAsync("synthetic-key")
    # One failed chunk among four must fail the whole AI stage, even below 30%.
    chunks = ["first", "second", "third", "fourth"]
    monkeypatch.setattr(processor, "_split_into_chunks", lambda text: chunks)
    primary_error = ValueError("synthetic private primary body")
    fallback_error = ValueError("synthetic private fallback body")

    class Client:
        is_closed = False

        async def aclose(self):
            self.is_closed = True

    client = Client()
    processor._http_client = client

    async def provider(chunk, context, model):
        if failure and chunk == "second":
            raise primary_error if model == processor.model else fallback_error
        return chunk.upper()

    monkeypatch.setattr(processor, "_process_chunk_async", provider)
    if failure:
        with pytest.raises(RuntimeError, match="1/4") as exc:
            processor.process("synthetic")
        assert exc.value.__cause__.__cause__ is fallback_error
        assert fallback_error.__context__ is primary_error
    else:
        assert processor.process("synthetic")[0] == "FIRST\n\nSECOND\n\nTHIRD\n\nFOURTH"
    assert client.is_closed
    assert processor._http_client is None
    assert "private" not in caplog.text


def test_wrapper_reports_partial_text_delivery_on_history_failure(
    transcript, tmp_path, monkeypatch, capsys
):
    seed_learning(transcript)
    fake_dataclass_ai(transcript, monkeypatch)
    with sqlite3.connect(transcript.config.database.path) as conn:
        conn.execute("CREATE TRIGGER reject_save BEFORE INSERT ON correction_changes "
                     "BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END")
    source = tmp_path / "input.md"
    source.write_text("wrng helo bot")
    output = tmp_path / "output"
    output.mkdir()
    html = output / "input_对比.html"
    html.write_bytes(b"old diff")
    wrapper = transcript.wrapper
    browser = Mock()
    monkeypatch.setattr(wrapper, "open_html_in_browser", browser)
    monkeypatch.setattr(wrapper.path_validator, "validate_input_path", lambda _: source)

    def child(cmd, **kwargs):
        with monkeypatch.context() as patch:
            patch.setattr(sys, "argv", ["core", *cmd[cmd.index("--input"):]])
            for key, value in kwargs["env"].items():
                patch.setenv(key, value)
            try:
                transcript.entry.main()
            except SystemExit as exc:
                raise subprocess.CalledProcessError(exc.code, cmd)
        raise AssertionError("History failure must fail the child")

    monkeypatch.setattr(wrapper.subprocess, "run", child)
    monkeypatch.setattr(sys, "argv", ["wrapper", str(source), "--output", str(output), "--auto-open"])
    with pytest.raises(SystemExit) as exc:
        wrapper.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "History not saved" in out
    assert "Text output saved" in out
    assert "Processing complete!" not in out
    assert "   - input_stage2.md" in out
    assert "   - input_对比.html" not in out
    assert html.read_bytes() == b"old diff"
    browser.assert_not_called()
    assert list(Path(os.environ["TMPDIR"]).iterdir()) == []


@pytest.fixture
def recalc_module(monkeypatch):
    office = types.ModuleType("office")
    office.__path__ = [str(XLSX / "office")]
    monkeypatch.setitem(sys.modules, "office", office)
    helper = types.ModuleType("office.soffice")
    helper.get_soffice_env = lambda: {"SAL_USE_VCLPLUGIN": "svp"}
    monkeypatch.setitem(sys.modules, "office.soffice", helper)
    return load(XLSX / "recalc.py", "delivery_recalc", monkeypatch)


def cached_workbook(path, value, data_type, missing=False):
    wb = Workbook()
    wb.active["A1"] = "=1+1"
    if missing:
        wb.active["B1"] = "=2+2"
    wb.save(path)
    wb.close()
    with zipfile.ZipFile(path) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    sheet = ET.fromstring(files["xl/worksheets/sheet1.xml"])
    cell = sheet.find(f".//{ns}c[@r='A1']")
    cell.set("t", data_type)
    cell.find(f"{ns}v").text = str(value)
    files["xl/worksheets/sheet1.xml"] = ET.tostring(sheet)
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return path


@pytest.mark.parametrize("value, data_type, status", [
    ("说明：#REF! 曾发生", "str", "success"),
    ("#DIV/0!", "str", "success"),
    ("#DIV/0!", "e", "errors_found"),
    ("#REF!", "e", "errors_found"),
    ("#VALUE!", "e", "errors_found"),
    ("#NAME?", "e", "errors_found"),
    ("#NULL!", "e", "errors_found"),
    ("#NUM!", "e", "errors_found"),
    ("#N/A", "e", "errors_found"),
    ("#SPILL!", "e", "errors_found"),
    ("#CALC!", "e", "errors_found"),
    ("#BUSY!", "e", "errors_found"),
    ("#FUTURE!", "e", "errors_found"),
    (0, "n", "success"),
    (0, "b", "success"),
])
def test_real_xlsx_caches_classification_and_cli_exit(
    value, data_type, status, recalc_module, tmp_path, monkeypatch, capsys
):
    path = cached_workbook(tmp_path / "cache.xlsx", value, data_type)
    profiles = []

    def office(cmd, **kwargs):
        uri = next(arg.split("=", 1)[1] for arg in cmd if arg.startswith("-env:UserInstallation="))
        profile = Path(unquote(urlparse(uri).path))
        profiles.append(profile)
        assert profile.is_relative_to(Path(os.environ["TMPDIR"]))
        assert profile.parent.stat().st_mode & 0o777 == 0o700
        assert (profile / "user/basic/Standard/Module1.xba").is_file()
        (profile.parent / "recalculated.ok").write_text("recalculated\n")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(recalc_module.subprocess, "run", office)
    monkeypatch.setattr(sys, "argv", ["recalc.py", str(path), "7"])
    if status == "success":
        recalc_module.main()
    else:
        with pytest.raises(SystemExit) as exc:
            recalc_module.main()
        assert exc.value.code == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == status
    assert result["total_formulas"] == 1
    assert result["missing_cached_values"] == 0
    if data_type == "e":
        assert result["error_summary"] == {value: {"count": 1, "locations": ["Sheet!A1"]}}
        assert result["total_errors"] == 1
    else:
        assert result["total_errors"] == 0
    assert not profiles[0].parent.exists()


def test_missing_cache_and_new_error_are_independent(recalc_module, tmp_path):
    path = cached_workbook(tmp_path / "missing.xlsx", "#SPILL!", "e", missing=True)
    result = recalc_module._inspect_caches(path)
    assert result["status"] == "unverified"
    assert result["total_formulas"] == 2
    assert result["missing_cache_locations"] == ["Sheet!B1"]
    assert result["total_errors"] == 1
    assert result["error_summary"]["#SPILL!"]["locations"] == ["Sheet!A1"]


@pytest.mark.parametrize("value, data_type", [
    ("说明 #REF!", "s"), ("#REF!", "s"), ("#REF!", "e"), ("#SPILL!", "e")
])
def test_nonformula_cells_use_actual_error_type(value, data_type, recalc_module, tmp_path):
    path = tmp_path / "ordinary.xlsx"
    wb = Workbook()
    wb.active["A1"] = value
    wb.active["A1"].data_type = data_type
    wb.save(path)
    wb.close()
    result = recalc_module._inspect_caches(path)
    assert result["status"] == ("errors_found" if data_type == "e" else "success")
    assert result["total_errors"] == int(data_type == "e")
    assert result["total_formulas"] == result["missing_cached_values"] == 0
