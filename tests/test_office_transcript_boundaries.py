"""Boundary regressions: no real Office, network, browser, or user configuration."""

import argparse
import builtins
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import types
from unittest.mock import Mock
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET
import zipfile

import pytest
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
OFFICE = ROOT / "skills/office-white-collar"
TRANSCRIPT = OFFICE / "transcript-fixer/scripts"


def load(path, name, monkeypatch):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    temporary = tmp_path / "tmp"
    temporary.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("TMPDIR", str(temporary))
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", str(temporary))
    monkeypatch.setattr(sys, "path", sys.path.copy())
    for name in (
        "TRANSCRIPT_FIXER_CONFIG_DIR", "TRANSCRIPT_FIXER_DB_PATH",
        "TRANSCRIPT_FIXER_ENABLE_LEARNING", "TRANSCRIPT_FIXER_AUTO_APPROVE",
        "GLM_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("skill", ["docx", "pptx", "xlsx"])
def test_socket_restriction_blocks_office_without_workaround(skill, tmp_path, monkeypatch):
    module = load(OFFICE / skill / "scripts/office/soffice.py", "office_helper", monkeypatch)
    monkeypatch.setattr(module.socket, "socket", Mock(side_effect=PermissionError("blocked")))
    run = Mock(side_effect=AssertionError("must not launch or compile"))
    monkeypatch.setattr(module.subprocess, "run", run)
    before = set(tmp_path.rglob("*"))
    with pytest.raises(RuntimeError, match="has not run"):
        module.run_soffice(["--headless"])
    run.assert_not_called()
    assert set(tmp_path.rglob("*")) == before


def test_office_helpers_are_identical_and_do_not_inject_preload(monkeypatch):
    paths = [OFFICE / skill / "scripts/office/soffice.py" for skill in ("docx", "pptx", "xlsx")]
    assert len({path.read_bytes() for path in paths}) == 1
    module = load(paths[0], "office_helper", monkeypatch)
    socket = Mock()
    socket.__enter__ = Mock(return_value=socket)
    socket.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(module.socket, "socket", Mock(return_value=socket))
    monkeypatch.delenv("LD_PRELOAD", raising=False)
    env = module.get_soffice_env()
    assert env["SAL_USE_VCLPLUGIN"] == "svp"
    assert "LD_PRELOAD" not in env


@pytest.fixture
def recalc_module(monkeypatch):
    package = types.ModuleType("office")
    package.__path__ = [str(OFFICE / "xlsx/scripts/office")]
    monkeypatch.setitem(sys.modules, "office", package)
    helper = load(OFFICE / "xlsx/scripts/office/soffice.py", "office.soffice", monkeypatch)
    monkeypatch.setattr(helper, "get_soffice_env", lambda: {"SAL_USE_VCLPLUGIN": "svp"})
    return load(OFFICE / "xlsx/scripts/recalc.py", "boundary_recalc", monkeypatch)


def workbook(path, cached=None):
    wb = Workbook()
    wb.active["A1"] = "=1+1"
    wb.active["B1"] = "ordinary text"
    wb.save(path)
    wb.close()
    if cached is not None:
        # Write synthetic OOXML cache values, without running Excel/LibreOffice.
        with zipfile.ZipFile(path) as source:
            files = {name: source.read(name) for name in source.namelist()}
        namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        sheet = ET.fromstring(files["xl/worksheets/sheet1.xml"])
        cell = sheet.find(f".//{namespace}c[@r='A1']")
        cell.find(f"{namespace}v").text = str(cached)
        if isinstance(cached, str):
            cell.set("t", "e" if cached.startswith("#") else "str")
        files["xl/worksheets/sheet1.xml"] = ET.tostring(sheet)
        with zipfile.ZipFile(path, "w") as dest:
            for name, value in files.items():
                dest.writestr(name, value)
    return path


def fake_office(monkeypatch, module, *, receipt=True, returncode=0, timeout=False):
    calls = []

    def run(cmd, **kwargs):
        assert cmd[0] == "soffice"  # No external timeout executable.
        assert kwargs["timeout"] == 7
        profile_arg = next(arg for arg in cmd if arg.startswith("-env:UserInstallation="))
        profile = Path(unquote(urlparse(profile_arg.split("=", 1)[1]).path))
        assert profile.is_relative_to(Path(os.environ["TMPDIR"]))
        assert profile.parent.stat().st_mode & 0o777 == 0o700
        macro = profile / "user/basic/Standard/Module1.xba"
        assert macro.is_file()
        assert (macro.parent / "script.xlb").is_file()
        assert (profile / "user/basic/script.xlc").is_file()
        calls.append(profile)
        if timeout:
            raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])
        if receipt:
            (profile.parent / "recalculated.ok").write_text("recalculated\n")
        return subprocess.CompletedProcess(cmd, returncode, "", "failed" if returncode else "")

    monkeypatch.setattr(module.subprocess, "run", run)
    return calls


@pytest.mark.parametrize("macro_dir", [
    "Library/Application Support/LibreOffice/4/user/basic/Standard",
    ".config/libreoffice/4/user/basic/Standard",
])
def test_recalc_preserves_user_macros_and_cleans_private_profile(
    macro_dir, tmp_path, recalc_module, monkeypatch
):
    user_macro = Path.home() / macro_dir / "Module1.xba"
    user_macro.parent.mkdir(parents=True)
    original = b"Sub UserMacro\n  REM do not replace\nEnd Sub\n"
    user_macro.write_bytes(original)
    home_before = {p.relative_to(Path.home()): p.read_bytes()
                   for p in Path.home().rglob("*") if p.is_file()}
    path = workbook(tmp_path / "book.xlsx", cached=2)
    calls = fake_office(monkeypatch, recalc_module)
    result = recalc_module.recalc(path, timeout=7)
    assert result["status"] == "success"
    assert result["total_formulas"] == 1
    assert user_macro.read_bytes() == original
    assert home_before == {p.relative_to(Path.home()): p.read_bytes()
                           for p in Path.home().rglob("*") if p.is_file()}
    assert len(calls) == 1
    assert not calls[0].parent.exists()


@pytest.mark.parametrize("mode", ["timeout", "exit124", "exit2"])
def test_recalc_timeout_and_process_failure_cannot_pass(mode, tmp_path, recalc_module, monkeypatch):
    path = workbook(tmp_path / "cached.xlsx", cached=2)
    calls = fake_office(
        monkeypatch, recalc_module, timeout=mode == "timeout",
        returncode=124 if mode == "exit124" else (2 if mode == "exit2" else 0),
    )
    inspect = Mock(side_effect=AssertionError("do not accept previous caches"))
    monkeypatch.setattr(recalc_module, "_inspect_caches", inspect)
    result = recalc_module.recalc(path, timeout=7)
    assert result["status"] == "recalculation_failed"
    if mode == "timeout":
        assert "timed out" in result["error"]
    inspect.assert_not_called()
    assert not calls[0].parent.exists()


def test_recalc_missing_formula_cache_is_unverified(tmp_path, recalc_module, monkeypatch):
    path = workbook(tmp_path / "no-cache.xlsx")
    fake_office(monkeypatch, recalc_module)
    result = recalc_module.recalc(path, timeout=7)
    assert result["status"] == "unverified"
    assert result["total_errors"] == 0
    assert result["missing_cached_values"] == 1
    assert result["missing_cache_locations"] == ["Sheet!A1"]


def test_recalc_process_exit_without_macro_receipt_is_unverified(tmp_path, recalc_module, monkeypatch):
    path = workbook(tmp_path / "previous-cache.xlsx", cached=2)
    fake_office(monkeypatch, recalc_module, receipt=False)
    assert recalc_module.recalc(path, timeout=7)["status"] == "unverified"


@pytest.mark.parametrize("cache, status", [(0, "success"), (False, "success"), ("#DIV/0!", "errors_found")])
def test_recalc_checks_cache_values(cache, status, tmp_path, recalc_module, monkeypatch):
    # False is encoded as numeric zero in a spreadsheet cache.
    path = workbook(tmp_path / "cache.xlsx", cached=int(cache) if isinstance(cache, bool) else cache)
    fake_office(monkeypatch, recalc_module)
    result = recalc_module.recalc(path, timeout=7)
    assert result["status"] == status
    if status == "errors_found":
        assert result["error_summary"]["#DIV/0!"]["locations"] == ["Sheet!A1"]


def test_recalc_unavailable_isolation_fails_without_launch(tmp_path, recalc_module, monkeypatch):
    path = workbook(tmp_path / "book.xlsx")
    monkeypatch.setattr(recalc_module.tempfile, "TemporaryDirectory",
                        Mock(side_effect=PermissionError("isolation unavailable")))
    run = Mock(side_effect=AssertionError("no launch"))
    monkeypatch.setattr(recalc_module.subprocess, "run", run)
    assert recalc_module.recalc(path)["status"] == "recalculation_failed"
    run.assert_not_called()


def test_recalc_blocked_host_is_not_rendered(tmp_path, recalc_module, monkeypatch):
    path = workbook(tmp_path / "book.xlsx")
    monkeypatch.setattr(recalc_module, "get_soffice_env",
                        Mock(side_effect=RuntimeError("rendering has not run")))
    run = Mock(side_effect=AssertionError("no launch"))
    monkeypatch.setattr(recalc_module.subprocess, "run", run)
    result = recalc_module.recalc(path)
    assert result["status"] == "recalculation_failed"
    assert "has not run" in result["error"]
    run.assert_not_called()


@pytest.mark.parametrize("status", ["unverified", "recalculation_failed", "errors_found"])
def test_recalc_cli_unverified_is_nonzero(status, tmp_path, recalc_module, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["recalc.py", str(tmp_path / "book.xlsx")])
    monkeypatch.setattr(recalc_module, "recalc", lambda *args: {"status": status})
    with pytest.raises(SystemExit) as exc:
        recalc_module.main()
    assert exc.value.code == 1


@pytest.fixture
def transcript_modules(monkeypatch):
    # Load only required utilities, avoiding unrelated package initialization.
    utils = types.ModuleType("utils")
    utils.__path__ = [str(TRANSCRIPT / "utils")]
    utils.validate_configuration = Mock()
    utils.print_validation_summary = Mock()
    monkeypatch.setitem(sys.modules, "utils", utils)
    config = load(TRANSCRIPT / "utils/config.py", "utils.config", monkeypatch)
    learning = load(TRANSCRIPT / "core/learning_engine.py", "boundary_learning", monkeypatch)
    dictionary = load(TRANSCRIPT / "core/dictionary_processor.py", "boundary_dictionary", monkeypatch)
    core = types.ModuleType("core")
    core.CorrectionRepository = Mock(side_effect=AssertionError("unexpected persistent repository"))
    core.CorrectionService = Mock()
    core.DictionaryProcessor = dictionary.DictionaryProcessor
    core.AIProcessor = Mock(side_effect=AssertionError("real AI must never run"))
    core.LearningEngine = learning.LearningEngine
    monkeypatch.setitem(sys.modules, "core", core)
    commands = load(TRANSCRIPT / "cli/commands.py", "boundary_commands", monkeypatch)
    wrapper = load(TRANSCRIPT / "fix_transcript_enhanced.py", "boundary_wrapper", monkeypatch)
    return types.SimpleNamespace(config=config, learning=learning, commands=commands, wrapper=wrapper)


def test_wrapper_env_key_never_reads_shell_files(transcript_modules, monkeypatch):
    wrapper = transcript_modules.wrapper
    monkeypatch.setenv("GLM_API_KEY", "synthetic-key-for-regression-only")
    monkeypatch.setattr(Path, "home", Mock(side_effect=AssertionError("must not search HOME")))
    monkeypatch.setattr(builtins, "open", Mock(side_effect=AssertionError("must not read any shell file")))
    assert wrapper.find_glm_api_key() == "synthetic-key-for-regression-only"
    monkeypatch.delenv("GLM_API_KEY")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "unrelated-synthetic-key")
    assert wrapper.find_glm_api_key() is None


@pytest.mark.parametrize("options, should_open", [([], False), (["--auto-open"], True), (["--no-auto-open"], False)])
def test_wrapper_browser_requires_explicit_opt_in(options, should_open, tmp_path, transcript_modules, monkeypatch):
    wrapper = transcript_modules.wrapper
    source = tmp_path / "input.md"
    source.write_text("example")
    (tmp_path / "input_对比.html").write_text("<p>diff</p>")
    monkeypatch.setenv("GLM_API_KEY", "synthetic-key-for-regression-only")
    monkeypatch.setattr(sys, "argv", ["wrapper", str(source), *options])
    monkeypatch.setattr(wrapper.path_validator, "validate_input_path", lambda _: source)
    launch = Mock(return_value=subprocess.CompletedProcess([], 0))
    browser = Mock()
    monkeypatch.setattr(wrapper.subprocess, "run", launch)
    monkeypatch.setattr(wrapper, "open_html_in_browser", browser)
    wrapper.main()
    launch.assert_called_once()
    assert browser.call_count == int(should_open)


def test_wrapper_missing_env_key_does_not_launch(tmp_path, transcript_modules, monkeypatch):
    wrapper = transcript_modules.wrapper
    source = tmp_path / "input.md"
    source.write_text("example")
    monkeypatch.setattr(wrapper.path_validator, "validate_input_path", lambda _: source)
    monkeypatch.setattr(sys, "argv", ["wrapper", str(source)])
    launch = Mock()
    monkeypatch.setattr(wrapper.subprocess, "run", launch)
    with pytest.raises(SystemExit) as exc:
        wrapper.main()
    assert exc.value.code == 1
    launch.assert_not_called()


def test_default_configuration_does_not_create_store(transcript_modules):
    module = transcript_modules.config
    assert not module.FeatureFlags().enable_learning
    for config in (module.Config(), module.Config.from_env()):
        assert not config.features.enable_learning
        assert not config.features.enable_auto_approval
    assert not (Path.home() / ".transcript-fixer").exists()


@pytest.mark.parametrize("enabled", ["1", "true"])
def test_explicit_file_and_env_learning_configuration(enabled, tmp_path, transcript_modules, monkeypatch):
    module = transcript_modules.config
    monkeypatch.setenv("TRANSCRIPT_FIXER_ENABLE_LEARNING", enabled)
    monkeypatch.setenv("TRANSCRIPT_FIXER_AUTO_APPROVE", "1")
    config = module.Config.from_env()
    assert config.features.enable_learning and config.features.enable_auto_approval
    path = tmp_path / "selected.json"
    path.write_text(json.dumps({
        "database": {"path": str(tmp_path / "selected/corrections.db")},
        "paths": {"config_dir": str(tmp_path / "selected")},
        "features": {"enable_learning": True, "enable_auto_approval": True},
    }))
    config = module.Config.from_file(path)
    assert config.features.enable_learning and config.features.enable_auto_approval
    assert not (tmp_path / "selected").exists()


def test_selected_config_directory_scopes_default_dictionary(tmp_path, transcript_modules):
    path = tmp_path / "selected.json"
    path.write_text(json.dumps({"paths": {"config_dir": str(tmp_path / "project-store")}}))
    config = transcript_modules.config.Config.from_file(path)
    assert config.database.path == tmp_path / "project-store/corrections.db"
    assert not config.features.enable_learning
    assert not (tmp_path / "project-store").exists()


def changes():
    return [types.SimpleNamespace(from_text="wrong", to_text="right", confidence=0.99)] * 5


@pytest.mark.parametrize("learning, auto, expected", [(False, False, 0), (False, True, 0), (True, False, 0), (True, True, 1)])
def test_learning_engine_checks_both_switches(learning, auto, expected, tmp_path, transcript_modules):
    service = Mock()
    store = tmp_path / "learning"
    engine = transcript_modules.learning.LearningEngine(
        store / "history", store / "learned", service,
        enable_learning=learning, enable_auto_approval=auto,
    )
    result = engine.analyze_and_auto_approve(changes())
    assert result["auto_approved"] == expected
    assert service.add_correction.call_count == expected
    if not expected:
        assert not store.exists()
    if learning and not auto:
        assert result["pending_review"] == 1
        assert result["suggestions"][0]["to"] == "right"
    if expected:
        # Explicit approval still works on a second run with existing audit JSON.
        assert engine.analyze_and_auto_approve(changes())["auto_approved"] == 1
        saved = json.loads((store / "learned/auto_approved.json").read_text())
        assert len(saved["auto_approved"]) == 2


def test_engine_defaults_do_not_persist(transcript_modules, tmp_path):
    service = Mock()
    engine = transcript_modules.learning.LearningEngine(
        tmp_path / "absent/history", tmp_path / "absent/learned", service
    )
    assert engine.analyze_and_suggest() == []
    assert engine.analyze_and_auto_approve(changes())["auto_approved"] == 0
    service.add_correction.assert_not_called()
    assert not (tmp_path / "absent").exists()


def seed_dictionary(path):
    path.parent.mkdir(parents=True)
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE corrections (from_text, to_text, domain, is_active)")
        conn.execute("INSERT INTO corrections VALUES ('wrong', 'right', 'general', 1)")
        conn.execute("CREATE TABLE context_rules (pattern, replacement, description, is_active, priority)")


@pytest.mark.parametrize("existing", [False, True])
def test_disabled_learning_workflow_has_no_store_writes(existing, tmp_path, transcript_modules, monkeypatch):
    module = transcript_modules
    commands = module.commands
    config = module.config.Config.from_env()
    if existing:
        seed_dictionary(config.database.path)
    before = {p.relative_to(Path.home()): p.read_bytes()
              for p in Path.home().rglob("*") if p.is_file()}
    source = tmp_path / "input.md"
    source.write_text("wrong")
    module.config.set_config(config)
    monkeypatch.setenv("GLM_API_KEY", "synthetic-key-for-regression-only")
    fake_ai = Mock()
    fake_ai.process.return_value = ("right", changes())
    monkeypatch.setattr(commands, "AIProcessor", Mock(return_value=fake_ai))
    persist = Mock(side_effect=AssertionError("learning disabled"))
    monkeypatch.setattr(commands, "_get_service", persist)
    monkeypatch.setattr(commands, "LearningEngine", persist)
    commands.cmd_run_correction(argparse.Namespace(input=str(source), output=None, domain="general", stage=3))
    assert (tmp_path / "input_stage2.md").read_text() == "right"
    if existing:
        assert (tmp_path / "input_stage1.md").read_text() == "right"
    persist.assert_not_called()
    after = {p.relative_to(Path.home()): p.read_bytes()
             for p in Path.home().rglob("*") if p.is_file()}
    assert after == before
    assert not (Path.home() / ".transcript-fixer/learned").exists()
    if not existing:
        assert not (Path.home() / ".transcript-fixer").exists()


@pytest.mark.parametrize("auto_approval", [False, True])
def test_cli_honors_selected_learning_directory(auto_approval, tmp_path, transcript_modules, monkeypatch):
    module = transcript_modules
    config = module.config.Config.from_env()
    config.features.enable_learning = True
    config.features.enable_auto_approval = auto_approval
    config.paths.config_dir = tmp_path / "selected-store"
    module.config.set_config(config)
    source = tmp_path / "input.md"
    source.write_text("wrong")
    monkeypatch.setenv("GLM_API_KEY", "synthetic-key-for-regression-only")
    service = Mock()
    service.get_corrections.return_value = {}
    service.load_context_rules.return_value = []
    monkeypatch.setattr(module.commands, "_get_service", lambda: service)
    fake_ai = Mock()
    fake_ai.process.return_value = ("right", changes())
    monkeypatch.setattr(module.commands, "AIProcessor", Mock(return_value=fake_ai))
    module.commands.cmd_run_correction(argparse.Namespace(input=str(source), output=None, domain="general", stage=2))
    service.save_history.assert_called_once()
    assert service.add_correction.call_count == int(auto_approval)
    assert (tmp_path / "selected-store/learned/auto_approved.json").exists() == auto_approval
    service.close.assert_called_once()
    assert not (Path.home() / ".transcript-fixer").exists()


@pytest.mark.parametrize("active_wal", [False, True])
def test_disabled_learning_does_not_create_or_change_wal_sidecars(
    active_wal, transcript_modules
):
    commands = transcript_modules.commands
    path = Path.home() / "dictionary/corrections.db"
    seed_dictionary(path)
    writer = sqlite3.connect(path)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("UPDATE corrections SET to_text = 'latest'")
        writer.commit()
        if not active_wal:
            writer.close()
        before = {p.name: p.read_bytes() for p in path.parent.iterdir()}
        corrections, rules = commands._read_dictionary(path, "general")
        assert corrections == {"wrong": "latest"}
        assert rules == []
        assert before == {p.name: p.read_bytes() for p in path.parent.iterdir()}
        assert list(Path(os.environ["TMPDIR"]).iterdir()) == []
    finally:
        writer.close()


def test_dictionary_changed_during_snapshot_is_not_used(transcript_modules, monkeypatch):
    commands = transcript_modules.commands
    path = Path.home() / "dictionary/corrections.db"
    seed_dictionary(path)
    copyfile = commands.shutil.copyfile

    def concurrent_change(source, dest):
        copyfile(source, dest)
        source.write_bytes(source.read_bytes() + b"concurrent change")

    monkeypatch.setattr(commands.shutil, "copyfile", concurrent_change)
    with pytest.raises(RuntimeError, match="changed during snapshot"):
        commands._read_dictionary(path, "general")
    assert list(Path(os.environ["TMPDIR"]).iterdir()) == []
