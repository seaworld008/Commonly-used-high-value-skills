"""Regression checks for reported control statuses, coverage, and findings."""
import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = (Path(__file__).resolve().parents[1] / "skills/security-and-reliability"
          / "information-security-manager-iso27001/scripts/compliance_checker.py")
get_control_status = runpy.run_path(str(SCRIPT))["get_control_status"]


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--standard", "iso27001", *args],
        check=True, capture_output=True, text=True, timeout=10,
    ).stdout


@pytest.mark.parametrize("value", [None, False, 1, [], {}, "", "passed", "unassessed"])
def test_unrecognized_status_returns_unknown(value):
    assert get_control_status("A.5.1", {"A.5.1": value}) == "unknown"


def test_no_input_leaves_entire_catalog_unassessed():
    report = json.loads(run_cli("--format", "json", "--gap-analysis"))
    summary = report["summary"]
    assert summary["unknown"] == summary["total_controls"] > 0
    assert summary["implemented"] == summary["partial"] == summary["not_implemented"] == 0
    assert summary["assessed_controls"] == summary["assessment_coverage_percentage"] == 0
    assert summary["compliance_percentage"] is None
    assert report["findings"] == report["gap_analysis"] == []
    for domain in report["domains"].values():
        assert domain["unknown"] == len(domain["controls"])
        assert domain["compliance_percentage"] is None
        assert all(control["status"] == "unknown" for control in domain["controls"])

    markdown = run_cli("--gap-analysis")
    assert f"| Unknown (unassessed) | {summary['total_controls']} |" in markdown
    assert "| Not Implemented | 0 |" in markdown
    assert "| **Catalog score** | **Unassessed** |" in markdown


@pytest.mark.parametrize(("extension", "data"), [
    ("csv", "id,status\nA.5.1,IMPLEMENTED\nA.5.2, Partial \nA.5.4,not_implemented\n"
            "A.5.5,passed\nA.5.6\nA.5.7,\nA.6.1,implemented\n"),
    ("json", json.dumps({"A.5.1": "IMPLEMENTED", "A.5.2": " Partial ", "A.5.4": "not_implemented",
                         "A.5.5": True, "A.5.6": None, "A.5.7": {}, "A.6.1": "implemented"})),
])
def test_partial_input_counts_only_recognized_statuses(tmp_path, extension, data):
    controls = tmp_path / f"controls.{extension}"
    controls.write_text(data, encoding="utf-8")
    args = ("--controls-file", str(controls), "--domains", "organizational", "--gap-analysis")
    report = json.loads(run_cli(*args, "--format", "json"))
    domain = report["domains"]["organizational"]
    statuses = {control["id"]: control["status"] for control in domain["controls"]}
    assessed = {"A.5.1": "implemented", "A.5.2": "partial", "A.5.4": "not_implemented"}
    assert {key: value for key, value in statuses.items() if value != "unknown"} == assessed
    assert report["summary"]["total_controls"] == 10
    for counts in (report["summary"], domain):
        assert counts["implemented"] == counts["partial"] == counts["not_implemented"] == 1
        assert counts["unknown"] == 7
        assert counts["assessed_controls"] == 3
        assert counts["assessment_coverage_percentage"] == 30
        assert counts["compliance_percentage"] == 15
    assert [finding["control_id"] for finding in report["findings"]] == ["A.5.4"]
    assert [gap["control_id"] for gap in report["gap_analysis"]] == ["A.5.4"]

    markdown = run_cli(*args)
    assert "| A.5.1 | Policies for information security | Implemented |" in markdown
    assert "| Unknown (unassessed) | 7 |" in markdown
    assert "| Assessment coverage | 3/10 (30.0%) |" in markdown
    assert "| Organizational Controls | 1 | 1 | 1 | 7 | 30.0% | 15.0% |" in markdown


def test_csv_without_status_column_supplies_no_evidence(tmp_path):
    controls = tmp_path / "controls.csv"
    controls.write_text("control_id,notes\nA.8.5,implemented\n", encoding="utf-8")
    report = json.loads(run_cli("-c", str(controls), "-f", "json", "-g"))
    assert report["summary"]["unknown"] == report["summary"]["total_controls"]
    assert report["findings"] == report["gap_analysis"] == []
