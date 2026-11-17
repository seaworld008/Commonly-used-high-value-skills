"""Offline regressions: real CLI/files with synthetic inputs and Office stand-ins."""

import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

from openpyxl import Workbook
import pytest


ROOT = Path(__file__).resolve().parents[1]
DCF = ROOT / "skills/finance-investing/financial-analyst/scripts/dcf_valuation.py"
ISO = ROOT / "skills/security-and-reliability/information-security-manager-iso27001/scripts/risk_assessment.py"
RECALC = ROOT / "skills/office-white-collar/xlsx/scripts/recalc.py"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
VALUES = ("terminal_value", "enterprise_value", "equity_value", "value_per_share")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cli(script, *args, env=None):
    return subprocess.run([sys.executable, str(script), *map(str, args)],
                          capture_output=True, text=True, timeout=15, env=env)


def dcf_result(tmp_path, growth):
    source = tmp_path / "valuation.json"
    source.write_text(json.dumps({
        "historical": {"revenue": [100], "net_debt": 0, "shares_outstanding": 10},
        "assumptions": {"terminal_growth_rate": growth, "exit_ev_ebitda_multiple": 12},
    }))
    before = source.read_bytes()
    result = cli(DCF, source, "--format", "json")
    assert result.returncode == 0, result.stderr
    assert source.read_bytes() == before
    return json.loads(result.stdout, parse_constant=lambda x: pytest.fail(f"Nonfinite JSON: {x}"))


@pytest.mark.parametrize("growth", [-3, -2.08125, -1.01])
def test_dcf_invalid_ordinary_perpetuity_preserves_independent_exit(tmp_path, growth):
    data = dcf_result(tmp_path, growth)
    assert all(data[name]["perpetuity_growth"] is None for name in VALUES)
    assert data["terminal_value"]["exit_multiple"] == pytest.approx(306.307575)
    assert all(math.isfinite(data[name]["exit_multiple"]) for name in VALUES)
    reason = data["unavailable_reasons"]["perpetuity_growth"]
    assert "estimable" in reason or "unavailable" in reason
    if growth == -3:
        assert "converge" in reason
    sensitivity = data["sensitivity_analysis"]
    for i, wacc in enumerate(sensitivity["wacc_values"]):
        for j, cell_growth in enumerate(sensitivity["growth_values"]):
            valid = cell_growth >= -1 and wacc > cell_growth
            for name in ("enterprise_value_table", "share_price_table"):
                assert (sensitivity[name][i][j] is not None) == valid
    assert sensitivity["unavailable_reasons"]["perpetuity_growth"]


@pytest.mark.parametrize("growth,terminal", [(0.025, 232.5668613888889), (-1, 0), (-0.5, None)])
def test_dcf_legal_growth_and_total_decline_boundary(tmp_path, growth, terminal):
    data = dcf_result(tmp_path, growth)
    if terminal is None:
        terminal = data["projected_fcf"][-1] * (1 + growth) / (data["wacc"] - growth)
    assert data["terminal_value"]["perpetuity_growth"] == pytest.approx(terminal)
    assert data["enterprise_value"]["perpetuity_growth"] > 0
    assert data["unavailable_reasons"] == {}
    if growth == -1:
        table = data["sensitivity_analysis"]["enterprise_value_table"]
        assert all(row[:2] == [None, None] for row in table)
        assert all(all(value is not None for value in row[2:]) for row in table)


def test_dcf_sensitivity_uses_same_domains_and_strict_convergence_boundary():
    module = load_module("numeric_dcf", DCF)
    model = module.DCFModel()
    model.set_historical_financials({"revenue": [100], "net_debt": 0, "shares_outstanding": 10})
    model.run_full_valuation()
    growths = [-3, -1.1, -1, -0.5, 0.025, 0.125]
    waccs = [-1.1, -1, -0.75, 0.125]
    table = model.sensitivity_analysis(waccs, growths)
    for i, wacc in enumerate(waccs):
        for j, growth in enumerate(growths):
            valid = wacc > -1 and growth >= -1 and abs(1 + growth) < 1 + wacc
            if not valid:
                assert table["enterprise_value_table"][i][j] is None
                assert table["share_price_table"][i][j] is None
            else:
                expected = sum(fcf / (1 + wacc) ** (k + 1)
                               for k, fcf in enumerate(model.projected_fcf))
                expected += model.projected_fcf[-1] * (1 + growth) / (wacc - growth) / (1 + wacc) ** 5
                assert table["enterprise_value_table"][i][j] == pytest.approx(round(expected, 2))
    model.set_assumptions({"terminal_growth_rate": model.wacc})
    assert model.run_full_valuation()["terminal_value"]["perpetuity_growth"] is None
    # Adding 1 rounds both rates to the same float; their spread is still valid.
    assert module.perpetuity_unavailable_reason(0, -1e-17) is None


def test_dcf_recovers_after_unavailable_perpetuity():
    module = load_module("numeric_dcf_recovery", DCF)
    model = module.DCFModel()
    model.set_historical_financials({"revenue": [100], "net_debt": 0, "shares_outstanding": 10})
    original = model.run_full_valuation()
    model.set_assumptions({"terminal_growth_rate": -3})
    assert model.run_full_valuation()["terminal_value"]["perpetuity_growth"] is None
    model.set_assumptions({"terminal_growth_rate": 0.025})
    assert model.run_full_valuation() == original


ASSET_HEADERS = ["id", "name", "type", "owner", "classification"]
ASSET_ROW = ["A1", "Synthetic database", "Information", "Test owner", "high"]
CONTROL_HEADERS = ["asset_id", "threat_id", "status", "effectiveness",
                   "evidence_ref", "assessed_by", "assessed_at"]
CONTROL_ROW = ["A1", "T01", "verified", "0.8", "offline-fixture", "Test reviewer", "2020-01-01"]


def csv_file(path, headers, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)
    return path


def iso_inputs(tmp_path):
    return (csv_file(tmp_path / "assets.csv", ASSET_HEADERS, [ASSET_ROW]),
            csv_file(tmp_path / "controls.csv", CONTROL_HEADERS, [CONTROL_ROW]))


@pytest.mark.parametrize("kind,field,duplicate,first,last", [
    ("controls", "status", "status", "unverified", "verified"),
    ("controls", "status", " STATUS ", "unverified", "verified"),
    ("controls", "status", "ＳＴＡＴＵＳ", "unverified", "verified"),
    ("controls", "effectiveness", " Effectiveness ", "0", "0.8"),
    ("controls", "evidence_ref", "evidence_ref", "", "offline-fixture"),
    ("assets", "classification", "classification", "critical", "low"),
    ("assets", "id", " ID ", "A2", "A1"),
    ("assets", "owner", "ｏｗｎｅｒ", "Other owner", "Test owner"),
])
@pytest.mark.parametrize("existing_output", [False, True])
def test_iso_duplicate_headers_rejected_before_report(tmp_path, kind, field, duplicate,
                                                     first, last, existing_output):
    assets, controls = iso_inputs(tmp_path)
    headers = list(CONTROL_HEADERS if kind == "controls" else ASSET_HEADERS)
    row = list(CONTROL_ROW if kind == "controls" else ASSET_ROW)
    row[headers.index(field)] = first
    csv_file(controls if kind == "controls" else assets, headers + [duplicate], [row + [last]])
    before = (assets.read_bytes(), controls.read_bytes())
    output = tmp_path / "report.json"
    if existing_output:
        output.write_text("prior trusted report")
    result = cli(ISO, "--scope", "offline-fixture", "--assets", assets,
                 "--control-evidence", controls, "--format", "json", "--output", output)
    assert result.returncode == 2
    assert "duplicate" in result.stderr.lower()
    assert result.stdout == ""
    assert (assets.read_bytes(), controls.read_bytes()) == before
    if existing_output:
        assert output.read_text() == "prior trusted report"
    else:
        assert not output.exists()


@pytest.mark.parametrize("status,expected", [("verified", 4), ("unverified", None)])
def test_iso_single_status_column_controls_risk(tmp_path, status, expected):
    assets, controls = iso_inputs(tmp_path)
    row = list(CONTROL_ROW)
    row[2] = status
    csv_file(controls, CONTROL_HEADERS, [row])
    result = cli(ISO, "--scope", "offline-fixture", "--assets", assets,
                 "--control-evidence", controls, "--format", "json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    risk = next(r for r in data["risks"] if r["threat_id"] == "T01")
    residual = next(r for r in data["residual_risks"] if r["risk_id"] == risk["id"])
    assert risk["score"] == 16
    assert residual["residual_score"] == expected
    assert residual["control_status"] == ("reported_verified" if expected else "unknown")


def test_iso_conflicting_rows_rejected(tmp_path):
    assets, controls = iso_inputs(tmp_path)
    unverified = list(CONTROL_ROW)
    unverified[2] = "unverified"
    csv_file(controls, CONTROL_HEADERS, [unverified, CONTROL_ROW])
    result = cli(ISO, "--scope", "offline-fixture", "--assets", assets,
                 "--control-evidence", controls, "--format", "json")
    assert result.returncode == 2
    assert "duplicate" in result.stderr
    assert result.stdout == ""


@pytest.fixture
def recalc_module(monkeypatch):
    monkeypatch.syspath_prepend(str(RECALC.parent))
    return load_module("numeric_recalc", RECALC)


def ooxml_book(path, kind, *, absolute_target=False):
    """Real OOXML; rename the cache sheet part so sheet-number guesses fail."""
    wb = Workbook()
    wb.active.title = "Decoy"
    wb.active["A1"] = "#REF!"
    wb.active["A1"].data_type = "s"
    sheet = wb.create_sheet("缓存 sheet")
    sheet["A1"] = '=IF(TRUE,"","ok")'
    wb.save(path)
    wb.close()
    with zipfile.ZipFile(path) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    old_part = "xl/worksheets/sheet2.xml"
    new_part = "xl/worksheets/nested/cache-results.xml"
    sheet = ET.fromstring(files.pop(old_part))
    cell = sheet.find(f".//{NS}c[@r='A1']")
    cell.set("t", "e" if kind == "error" else "n" if kind == "empty_numeric" else "str")
    value = cell.find(f"{NS}v")
    if kind == "missing":
        cell.remove(value)
    else:
        value.text = "#SPILL!" if kind == "error" else "ok" if kind == "nonempty" else None
    files[new_part] = ET.tostring(sheet)
    rel_path = "xl/_rels/workbook.xml.rels"
    relations = ET.fromstring(files[rel_path])
    for relation in relations:
        if relation.get("Target", "").endswith("worksheets/sheet2.xml"):
            relation.set("Target", "/" + new_part if absolute_target
                         else "worksheets/nested/cache-results.xml")
    files[rel_path] = ET.tostring(relations)
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return path


@pytest.mark.parametrize("absolute_target", [False, True])
@pytest.mark.parametrize("kind,status,missing,errors", [
    ("empty_string", "success", 0, 0), ("missing", "unverified", 1, 0),
    ("empty_numeric", "unverified", 1, 0), ("nonempty", "success", 0, 0),
    ("error", "errors_found", 0, 1),
])
def test_xlsx_cache_types_follow_workbook_relationships(recalc_module, tmp_path,
                                                        absolute_target, kind, status, missing, errors):
    path = ooxml_book(tmp_path / "cache.xlsx", kind, absolute_target=absolute_target)
    before = hashlib.sha256(path.read_bytes()).digest()
    result = recalc_module._inspect_caches(path)
    assert result["status"] == status
    assert result["total_formulas"] == 1
    assert result["missing_cached_values"] == missing
    assert result["total_errors"] == errors
    assert result["missing_cache_locations"] == (["缓存 sheet!A1"] if missing else [])
    assert result["error_summary"] == ({"#SPILL!": {"count": 1, "locations": ["缓存 sheet!A1"]}}
                                       if errors else {})
    assert hashlib.sha256(path.read_bytes()).digest() == before


def test_xlsx_workbook_part_can_also_be_relocated(recalc_module, tmp_path):
    path = ooxml_book(tmp_path / "relocated.xlsx", "empty_string", absolute_target=True)
    with zipfile.ZipFile(path) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    old_part, new_part = "xl/workbook.xml", "xl/model/valuation.xml"
    files[new_part] = files.pop(old_part)
    files["xl/model/_rels/valuation.xml.rels"] = files.pop("xl/_rels/workbook.xml.rels")
    for part, attr, old, new in [("_rels/.rels", "Target", old_part, new_part),
                                 ("[Content_Types].xml", "PartName", "/" + old_part, "/" + new_part)]:
        root = ET.fromstring(files[part])
        for item in root:
            if item.get(attr) == old:
                item.set(attr, new)
        files[part] = ET.tostring(root)
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    result = recalc_module._inspect_caches(path)
    assert result["status"] == "success"
    assert result["total_formulas"] == 1
    assert result["missing_cached_values"] == 0


@pytest.mark.parametrize("kind,status,exit_code", [("empty_string", "success", 0),
    ("missing", "unverified", 1), ("error", "errors_found", 1)])
def test_xlsx_real_cli_with_office_program_standin(tmp_path, kind, status, exit_code):
    # Shadow only the environment supplier in a copied runner, not host sockets.
    # The actual recalc.py source and both subprocess phases still execute.
    runner = tmp_path / "runner"
    runner.mkdir()
    (runner / "recalc.py").write_bytes(RECALC.read_bytes())
    office = runner / "office"
    office.mkdir()
    (office / "__init__.py").write_text("")
    (office / "soffice.py").write_text("import os\ndef get_soffice_env():\n    return dict(os.environ)\n")
    executable = runner / "soffice"
    executable.write_text(f"#!{sys.executable}\n" + '''
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET
uri = next(a.split("=", 1)[1] for a in sys.argv if a.startswith("-env:UserInstallation="))
profile = Path(unquote(urlparse(uri).path))
macro = profile / "user/basic/Standard/Module1.xba"
if "--terminate_after_init" in sys.argv:
    assert not macro.exists()
    macro.parent.mkdir(parents=True)
    macro.write_text("seeded initial Office macro")
else:
    basic = ET.fromstring(macro.read_text()).text
    assert "MacroExecMode.NEVER_EXECUTE" in basic
    assert "UpdateDocMode.NO_UPDATE" in basic
    assert "doc.calculateAll()" in basic
    assert "doc.store()" in basic
    document_uri = re.search(r'loadComponentFromURL\\("([^"]+)"', basic).group(1)
    assert Path(unquote(urlparse(document_uri).path)).is_file()
    (profile.parent / "recalculated.ok").write_text("recalculated\\n")
''')
    executable.chmod(0o700)
    path = ooxml_book(tmp_path / "offline.xlsx", kind)
    before = path.read_bytes()
    env = dict(os.environ, PATH=str(runner) + os.pathsep + os.environ["PATH"], TMPDIR=str(tmp_path))
    result = cli(runner / "recalc.py", path, "7", env=env)
    assert result.returncode == exit_code, result.stderr
    assert json.loads(result.stdout)["status"] == status
    assert path.read_bytes() == before
    assert not list(tmp_path.glob("xlsx-recalc-*"))
