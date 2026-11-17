"""Offline CLI regressions using synthetic fixtures, never organization data."""
import csv
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = (Path(__file__).resolve().parents[1] / "skills/security-and-reliability"
          / "information-security-manager-iso27001/scripts/risk_assessment.py")


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--scope", "nonexistent-fixture-system", *args],
        capture_output=True, text=True, timeout=10,
    )


def report(*args):
    result = run_cli(*args, "--format", "json")
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.fixture
def assets(tmp_path):
    path = tmp_path / "assets.csv"
    path.write_text('id,name,type,owner,classification\n'
                    'DB01,"Fixture database, primary",Information,Fixture owner,critical\n'
                    'APP02,Fixture app,Software,Fixture owner,medium\n', encoding="utf-8")
    return path


def evidence_file(tmp_path, **changes):
    row = dict(asset_id="DB01", threat_id="T01", status="verified", effectiveness="0.5",
               evidence_ref="fixture-review-001", assessed_by="Fixture reviewer",
               assessed_at="2020-01-15")
    row.update(changes)
    path = tmp_path / "control-evidence.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    return path


def assert_unknown(residuals):
    assert residuals
    for risk in residuals:
        assert risk["control_status"] == "unknown"
        assert risk["control_effectiveness"] is None
        assert risk["residual_status"] == "not_estimable"
        assert risk["residual_likelihood"] is None
        assert risk["residual_score"] is None
        assert risk["residual_level"] is None


@pytest.mark.parametrize("fmt", ["json", "markdown", "csv"])
def test_scope_without_input_refuses_and_does_not_write(tmp_path, fmt):
    output = tmp_path / f"report.{fmt}"
    result = run_cli("--format", fmt, "--output", str(output))
    assert result.returncode == 2
    assert "--demo" in result.stderr and "--assets" in result.stderr
    assert result.stdout == ""
    assert not output.exists()
    output.write_text("existing report", encoding="utf-8")
    result = run_cli("--format", fmt, "--output", str(output))
    assert result.returncode == 2
    assert output.read_text() == "existing report"


@pytest.mark.parametrize("template", ["general", "healthcare", "cloud"])
def test_explicit_demo_retains_useful_catalog_with_clear_origins(template):
    data = report("--demo", "--template", template)
    metadata = data["metadata"]
    assert metadata["demo"] is True
    assert metadata["asset_source"] == "synthetic_demo"
    assert metadata["assessment_kind"] == "catalog_scenario_analysis"
    assert metadata["scenario_source"] == f"bundled_catalog:{template}"
    assert data["summary"]["total_assets"] == 8
    assert data["summary"]["total_risks"] == 40
    assert len(data["residual_risks"]) == 40
    assert all(r["scenario_status"] == "unverified_catalog_scenario" for r in data["risks"])
    assert all(r["vulnerability_status"] == "unknown" for r in data["risks"])
    assert_unknown(data["residual_risks"])


@pytest.mark.parametrize("demo", [False, True])
def test_markdown_and_csv_preserve_sources_and_unknowns(assets, demo):
    args = ("--demo",) if demo else ("--assets", str(assets))
    source = "synthetic_demo" if demo else "user_supplied_csv"
    markdown = run_cli(*args, "--format", "markdown")
    assert markdown.returncode == 0, markdown.stderr
    assert f"**Demo:** {demo}" in markdown.stdout
    assert source in markdown.stdout
    assert "bundled_catalog:general" in markdown.stdout
    assert "not a site scan or formal assessment" in markdown.stdout
    assert "effectiveness=unknown; residual=None (not_estimable)" in markdown.stdout
    if demo:
        assert "DEMO (synthetic assets)" in markdown.stdout
    else:
        assert str(assets) in markdown.stdout

    result = run_cli(*args, "--format", "csv")
    assert result.returncode == 0, result.stderr
    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    assert len(rows) == (40 if demo else 10)
    for row in rows:
        assert row["demo"] == str(demo)
        assert row["asset_source"] == source
        assert row["assessment_kind"] == "catalog_scenario_analysis"
        assert row["scenario_source"] == "bundled_catalog:general"
        assert "not a site scan or formal assessment" in row["limitations"]
        assert row["control_status"] == "unknown"
        assert row["control_effectiveness"] == row["residual_score"] == ""
    if not demo:
        assert {r["asset_name"] for r in rows} == {"Fixture database, primary", "Fixture app"}
        assert all(r["asset_source_ref"] == str(assets) for r in rows)


def test_known_assets_are_not_scanned_and_controls_are_not_assumed(assets):
    data = report("--assets", str(assets))
    assert data["metadata"]["demo"] is False
    assert data["metadata"]["asset_source_ref"] == str(assets)
    assert data["summary"]["total_assets"] == 2
    assert data["summary"]["total_risks"] == 10
    assert {asset["id"] for asset in data["assets"]} == {"DB01", "APP02"}
    assert all(r["scenario_status"] == "unverified_catalog_scenario" for r in data["risks"])
    assert_unknown(data["residual_risks"])


@pytest.mark.parametrize("changes", [
    {"status": "implemented"}, {"status": "unknown"}, {"status": ""},
    {"effectiveness": ""}, {"effectiveness": "nan"}, {"effectiveness": "inf"},
    {"effectiveness": "-0.1"}, {"effectiveness": "1.1"},
    {"evidence_ref": ""}, {"assessed_by": ""}, {"assessed_at": ""},
    {"assessed_at": "not-a-date"}, {"assessed_at": "9999-01-01"},
])
def test_incomplete_or_unverified_control_never_reduces_risk(tmp_path, assets, changes):
    evidence = evidence_file(tmp_path, **changes)
    data = report("--assets", str(assets), "--control-evidence", str(evidence))
    assert_unknown(data["residual_risks"])


@pytest.mark.parametrize(("effectiveness", "expected_likelihood"), [
    ("0", 4), ("0.3", 3), ("0.5", 2), ("1", 1),
])
def test_complete_evidence_only_affects_matching_scenario(tmp_path, assets, effectiveness, expected_likelihood):
    evidence = evidence_file(tmp_path, effectiveness=effectiveness)
    args = ("--assets", str(assets), "--control-evidence", str(evidence))
    data = report(*args)
    by_id = {r["id"]: r for r in data["risks"]}
    estimates = [r for r in data["residual_risks"] if r["control_status"] != "unknown"]
    assert len(estimates) == 1
    estimate = estimates[0]
    assert (by_id[estimate["risk_id"]]["asset_id"], by_id[estimate["risk_id"]]["threat_id"]) == ("DB01", "T01")
    assert estimate["control_status"] == "reported_verified"
    assert estimate["residual_status"] == "conditional_estimate"
    assert estimate["control_effectiveness"] == float(effectiveness)
    assert estimate["residual_likelihood"] == expected_likelihood
    assert estimate["residual_score"] == expected_likelihood * 5
    assert estimate["evidence_ref"] == "fixture-review-001"
    assert "not independently verified" in estimate["basis"]
    assert_unknown([r for r in data["residual_risks"] if r != estimate])
    assert data["metadata"]["control_source_ref"] == str(evidence)

    csv_result = run_cli(*args, "--format", "csv")
    assert csv_result.returncode == 0, csv_result.stderr
    rows = list(csv.DictReader(io.StringIO(csv_result.stdout)))
    supplied = [r for r in rows if r["control_status"] == "reported_verified"]
    assert len(supplied) == 1
    assert supplied[0]["residual_score"] == str(expected_likelihood * 5)
    assert supplied[0]["evidence_ref"] == "fixture-review-001"
    markdown = run_cli(*args)
    assert markdown.returncode == 0, markdown.stderr
    assert f"residual={expected_likelihood * 5} (conditional_estimate)" in markdown.stdout
    assert "evidence=fixture-review-001" in markdown.stdout


@pytest.mark.parametrize("content", ["", "id,name,classification\n",
    "name,classification\nFixture,high\n", "id,name,classification\nA,Fixture,confidential\n",
    "id,name,classification\nA,Fixture,high\nA,Other,low\n"])
def test_invalid_inventory_fails_without_demo_fallback(tmp_path, content):
    path = tmp_path / "invalid.csv"
    path.write_text(content, encoding="utf-8")
    output = tmp_path / "report.json"
    result = run_cli("--assets", str(path), "--output", str(output))
    assert result.returncode == 2
    assert result.stdout == ""
    assert not output.exists()


def test_missing_file_and_conflicting_modes_fail(tmp_path, assets):
    for args in [("--assets", str(tmp_path / "missing.csv")),
                 ("--assets", str(assets), "--demo"),
                 ("--demo", "--control-evidence", "missing.csv")]:
        result = run_cli(*args)
        assert result.returncode == 2
        assert result.stdout == ""


def test_evidence_for_unknown_or_duplicate_pair_is_rejected(tmp_path, assets):
    for changes in [{"asset_id": "missing"}, {"threat_id": "T10"}]:
        path = evidence_file(tmp_path, **changes)
        result = run_cli("--assets", str(assets), "--control-evidence", str(path))
        assert result.returncode == 2
        assert "unknown or duplicate" in result.stderr
    path = evidence_file(tmp_path)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(path.read_text().splitlines()[1] + "\n")
    result = run_cli("--assets", str(assets), "--control-evidence", str(path))
    assert result.returncode == 2
    assert "unknown or duplicate" in result.stderr


def test_json_output_file_is_explicit_json(tmp_path):
    output = tmp_path / "demo.json"
    result = run_cli("--demo", "--format", "json", "--output", str(output))
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert json.loads(output.read_text())["metadata"]["demo"] is True


def test_malformed_evidence_schema_cannot_produce_a_report(tmp_path, assets):
    evidence = tmp_path / "incomplete.csv"
    evidence.write_text("asset_id,threat_id,status\nDB01,T01,verified\n", encoding="utf-8")
    output = tmp_path / "report.json"
    result = run_cli("--assets", str(assets), "--control-evidence", str(evidence),
                     "--format", "json", "--output", str(output))
    assert result.returncode == 2
    assert "Control evidence CSV requires" in result.stderr
    assert not output.exists()
