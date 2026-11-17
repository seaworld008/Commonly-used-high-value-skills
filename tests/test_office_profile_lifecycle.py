"""Offline XML/CLI contracts; these tests never launch real LibreOffice or UNO."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import types
from unittest.mock import Mock
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET
import zipfile

from openpyxl import Workbook
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/office-white-collar/xlsx/scripts/recalc.py"
MACRO_URI = "macro:///Standard.Module1.RecalculateAndSave()"
PRESET = "first-run preset Module1, not our macro"


@pytest.fixture
def recalc_module(monkeypatch, tmp_path):
    # Isolate all files and stub only the environment supplier, never sockets.
    monkeypatch.setattr(__import__("tempfile"), "tempdir", str(tmp_path))
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    office = types.ModuleType("office")
    office.__path__ = []
    helper = types.ModuleType("office.soffice")
    helper.get_soffice_env = lambda: dict(os.environ, SAL_USE_VCLPLUGIN="svp")
    monkeypatch.setitem(sys.modules, "office", office)
    monkeypatch.setitem(sys.modules, "office.soffice", helper)
    spec = importlib.util.spec_from_file_location("lifecycle_recalc", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def workbook(path, value="2", data_type="n", *, missing=False):
    """Create real OOXML, with explicitly synthetic formula caches."""
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
    cell.find(f"{ns}v").text = value
    files["xl/worksheets/sheet1.xml"] = ET.tostring(sheet)
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return path


def profile_from(cmd):
    uri = next(arg.split("=", 1)[1] for arg in cmd
               if arg.startswith("-env:UserInstallation="))
    return Path(unquote(urlparse(uri).path))


def fake_office(monkeypatch, module, *, fail_phase=None, failure=None):
    calls = []

    def run(cmd, **kwargs):
        profile = profile_from(cmd)
        phase = "init" if "--terminate_after_init" in cmd else "execute"
        macro = profile / "user/basic/Standard/Module1.xba"
        receipt = profile.parent / "recalculated.ok"
        assert cmd[:4] == ["soffice", f"-env:UserInstallation={profile.as_uri()}",
                           "--headless", "--norestore"]
        assert 0 < kwargs["timeout"] <= 7
        assert kwargs["capture_output"] and kwargs["text"]
        assert kwargs["env"]["SAL_USE_VCLPLUGIN"] == "svp"
        assert profile.parent.stat().st_mode & 0o777 == 0o700
        calls.append((phase, profile, kwargs["timeout"]))
        if phase == "init":
            assert not macro.exists(), "macro installed before the preset overwrite"
            assert len(cmd) == 5
            macro.parent.mkdir(parents=True)
            # Emulate the actual first-run overwrite, even if a caller had
            # incorrectly installed the module before this first launch.
            macro.write_text(PRESET, encoding="utf-8")
        else:
            assert cmd[4:] == [MACRO_URI]  # No asynchronously queued document.
            assert calls[0][0] == "init"
            assert profile == calls[0][1]
            assert "loadComponentFromURL" in ET.fromstring(macro.read_text()).text
            ET.parse(macro.parent / "script.xlb")
            ET.parse(profile / "user/basic/script.xlc")
        if phase == fail_phase:
            if failure == "timeout":
                raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])
            if failure in ("nonzero", "nonzero_with_receipt"):
                if failure == "nonzero_with_receipt":
                    receipt.write_text("recalculated\n")
                return subprocess.CompletedProcess(cmd, 2, "", "offline failure")
            if failure == "macro_error":
                # The Basic error path exits without a success receipt.
                return subprocess.CompletedProcess(cmd, 0, "", "")
            if failure == "bad_receipt":
                receipt.write_text("incomplete\n")
                return subprocess.CompletedProcess(cmd, 0, "", "")
        if phase == "execute":
            receipt.write_text("recalculated\n")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(module.subprocess, "run", run)
    return calls


def test_initializes_before_install_and_preserves_user_macros(
    recalc_module, tmp_path, monkeypatch
):
    canaries = []
    for relative in ("Library/Application Support/LibreOffice/4/user/basic/Standard",
                     ".config/libreoffice/4/user/basic/Standard"):
        canary = Path.home() / relative / "Module1.xba"
        canary.parent.mkdir(parents=True)
        canary.write_bytes(b"user macro must survive")
        canaries.append(canary)
    original_setup = recalc_module.setup_libreoffice_macro
    installed = []

    def install(profile, receipt, filename):
        macro = profile / "user/basic/Standard/Module1.xba"
        assert macro.read_text() == PRESET
        original_setup(profile, receipt, filename)
        installed.append(profile)

    monkeypatch.setattr(recalc_module, "setup_libreoffice_macro", install)
    calls = fake_office(monkeypatch, recalc_module)
    result = recalc_module.recalc(workbook(tmp_path / "book.xlsx"), timeout=7)
    assert result["status"] == "success"
    assert result["total_formulas"] == 1
    assert [phase for phase, _, _ in calls] == ["init", "execute"]
    assert installed == [calls[0][1]]
    assert not calls[0][1].parent.exists()
    assert all(canary.read_bytes() == b"user macro must survive" for canary in canaries)


def test_macro_xml_has_synchronous_document_and_safe_load_properties(
    recalc_module, tmp_path, monkeypatch
):
    # Quotes/XML metacharacters, Unicode, template-like tokens and relative input.
    name = '表 {document_uri} __RECEIPT__ & <tag> "quote" # %.xlsx'
    document = workbook(tmp_path / name)
    monkeypatch.chdir(tmp_path)
    profile = tmp_path / "private profile & quotes"
    completion = tmp_path / '回执 {receipt_path} __DOCUMENT__ & <ok> "q".ok'
    recalc_module.setup_libreoffice_macro(profile, completion, Path(name))
    # Existing seeded directories must be accepted (only in this private profile).
    recalc_module.setup_libreoffice_macro(profile, completion, Path(name))
    macro_path = profile / "user/basic/Standard/Module1.xba"
    raw = macro_path.read_text()
    macro = ET.fromstring(raw).text
    assert ET.fromstring(raw).attrib["{http://openoffice.org/2000/script}name"] == "Module1"
    assert "ThisComponent" not in macro
    assert (f'doc = StarDesktop.loadComponentFromURL("{document.as_uri()}", '
            '"_blank", 0, loadProperties())') in macro
    assert f'Open "{str(completion).replace(chr(34), chr(34) * 2)}"' in macro
    assert "&amp;" in raw and "&lt;ok&gt;" in raw
    for index, name, value in (
        (0, "Hidden", "True"),
        (1, "MacroExecutionMode", "com.sun.star.document.MacroExecMode.NEVER_EXECUTE"),
        (2, "UpdateDocMode", "com.sun.star.document.UpdateDocMode.NO_UPDATE"),
    ):
        assert f'loadProperties({index}).Name = "{name}"' in macro
        assert f"loadProperties({index}).Value = {value}" in macro
    assert "ALLOW" not in macro
    assert "On Error GoTo Failed" in macro
    success, failure = macro.split("Failed:")
    steps = ("loadComponentFromURL", "doc.calculateAll()", "doc.store()",
             "doc.close(True)", 'Print #receipt, "recalculated"', "Close #receipt",
             "StarDesktop.terminate()", "Exit Sub")
    assert [success.index(step) for step in steps] == sorted(success.index(step) for step in steps)
    assert "On Error Resume Next" in failure
    assert "Kill " in failure and "doc.close(True)" in failure
    assert "StarDesktop.terminate()" in failure and "Print #receipt" not in failure
    catalog = ET.parse(profile / "user/basic/script.xlc").getroot()
    library = catalog.find("{http://openoffice.org/2000/library}library")
    assert library.attrib["{http://www.w3.org/1999/xlink}href"] == (macro_path.parent / "script.xlb").as_uri()


@pytest.mark.parametrize("phase", ["init", "execute"])
@pytest.mark.parametrize("failure", ["timeout", "nonzero", "nonzero_with_receipt"])
def test_failed_process_cannot_inspect_old_caches(
    phase, failure, recalc_module, tmp_path, monkeypatch
):
    path = workbook(tmp_path / "old-good-cache.xlsx")
    calls = fake_office(monkeypatch, recalc_module, fail_phase=phase, failure=failure)
    inspect = Mock(side_effect=AssertionError("old caches are not proof of this run"))
    monkeypatch.setattr(recalc_module, "_inspect_caches", inspect)
    setup = Mock(wraps=recalc_module.setup_libreoffice_macro)
    monkeypatch.setattr(recalc_module, "setup_libreoffice_macro", setup)
    result = recalc_module.recalc(path, timeout=7)
    assert result["status"] == "recalculation_failed"
    if failure == "timeout":
        assert "timed out after 7 seconds" in result["error"]
    else:
        assert result["returncode"] == 2
    assert len(calls) == (1 if phase == "init" else 2)
    if phase == "init":
        setup.assert_not_called()
    inspect.assert_not_called()
    assert not calls[0][1].parent.exists()


@pytest.mark.parametrize("failure", ["macro_error", "bad_receipt"])
def test_macro_failure_or_bad_receipt_cannot_inspect_caches(
    failure, recalc_module, tmp_path, monkeypatch
):
    calls = fake_office(monkeypatch, recalc_module, fail_phase="execute", failure=failure)
    inspect = Mock(side_effect=AssertionError("receipt required before inspection"))
    monkeypatch.setattr(recalc_module, "_inspect_caches", inspect)
    result = recalc_module.recalc(workbook(tmp_path / "book.xlsx"), timeout=7)
    assert result["status"] == "unverified"
    inspect.assert_not_called()
    assert not calls[0][1].parent.exists()


def test_initialization_and_execution_share_one_deadline(recalc_module, tmp_path, monkeypatch):
    # Start at 10, initialization starts at 11, execution starts at 15.
    ticks = iter([10, 11, 15])
    monkeypatch.setattr(recalc_module.time, "monotonic", lambda: next(ticks))
    calls = fake_office(monkeypatch, recalc_module)
    result = recalc_module.recalc(workbook(tmp_path / "book.xlsx"), timeout=7)
    assert result["status"] == "success"
    assert [remaining for _, _, remaining in calls] == [6, 2]


def test_expired_total_budget_does_not_launch_macro(recalc_module, tmp_path, monkeypatch):
    ticks = iter([10, 11, 18])
    monkeypatch.setattr(recalc_module.time, "monotonic", lambda: next(ticks))
    calls = fake_office(monkeypatch, recalc_module)
    inspect = Mock()
    monkeypatch.setattr(recalc_module, "_inspect_caches", inspect)
    result = recalc_module.recalc(workbook(tmp_path / "book.xlsx"), timeout=7)
    assert result["status"] == "recalculation_failed"
    assert "timed out" in result["error"]
    assert [phase for phase, _, _ in calls] == ["init"]
    inspect.assert_not_called()


@pytest.mark.parametrize("value, data_type, missing, status", [
    ("0", "n", False, "success"),
    ("0", "b", False, "success"),
    ("#REF!", "str", False, "success"),
    ("#SPILL!", "e", False, "errors_found"),
    ("#FUTURE!", "e", True, "unverified"),
    ("2", "n", True, "unverified"),
])
def test_receipt_then_actual_ooxml_cache_inspection_and_cli_status(
    value, data_type, missing, status, recalc_module, tmp_path, monkeypatch, capsys
):
    path = workbook(tmp_path / "book.xlsx", value, data_type, missing=missing)
    fake_office(monkeypatch, recalc_module)
    monkeypatch.setattr(sys, "argv", ["recalc.py", str(path), "7"])
    if status == "success":
        recalc_module.main()
    else:
        with pytest.raises(SystemExit) as exc:
            recalc_module.main()
        assert exc.value.code == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == status
    assert result["total_formulas"] == (2 if missing else 1)
    assert result["missing_cached_values"] == int(missing)
    assert result["total_errors"] == int(data_type == "e")
    if data_type == "e":
        assert result["error_summary"][value]["locations"] == ["Sheet!A1"]


@pytest.mark.parametrize("failure", ["timeout", "nonzero", "macro_error"])
def test_cli_failures_are_nonzero(failure, recalc_module, tmp_path, monkeypatch, capsys):
    path = workbook(tmp_path / "book.xlsx")
    fake_office(monkeypatch, recalc_module, fail_phase="execute", failure=failure)
    monkeypatch.setattr(sys, "argv", ["recalc.py", str(path), "7"])
    with pytest.raises(SystemExit) as exc:
        recalc_module.main()
    assert exc.value.code == 1
    assert json.loads(capsys.readouterr().out)["status"] != "success"


def test_actual_subprocess_cli_double_first_run_overwrite(
    recalc_module, tmp_path, monkeypatch
):
    """Exercise real argv/processes against a harmless Python CLI stand-in."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    executable = bin_dir / "soffice"
    executable.write_text(f"#!{sys.executable}\n" + '''
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET
uri = next(arg.split("=", 1)[1] for arg in sys.argv if arg.startswith("-env:UserInstallation="))
profile = Path(unquote(urlparse(uri).path))
macro = profile / "user/basic/Standard/Module1.xba"
if "--terminate_after_init" in sys.argv:
    assert not macro.exists()
    macro.parent.mkdir(parents=True)
    macro.write_text("first-run preset overwrite")
else:
    assert sys.argv[4:] == ["macro:///Standard.Module1.RecalculateAndSave()"]
    basic = ET.fromstring(macro.read_text()).text
    assert "ThisComponent" not in basic
    assert "MacroExecMode.NEVER_EXECUTE" in basic
    assert "UpdateDocMode.NO_UPDATE" in basic
    document_uri = re.search(r'loadComponentFromURL\\("([^"]+)"', basic).group(1)
    assert Path(unquote(urlparse(document_uri).path)).is_file()
    (profile.parent / "recalculated.ok").write_text("recalculated\\n")
''', encoding="utf-8")
    executable.chmod(0o700)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    result = recalc_module.recalc(workbook(tmp_path / '离线 & "quotes".xlsx'), timeout=7)
    assert result["status"] == "success"
    assert not list(tmp_path.glob("xlsx-recalc-*"))
