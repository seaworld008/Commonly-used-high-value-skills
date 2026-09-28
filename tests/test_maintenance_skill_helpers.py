"""Regressions from the full maintenance audit; no network or user installs."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCANNER = ROOT / "skills/developer-engineering/dependency-auditor/scripts/dep_scanner.py"


def scanner_module():
    spec = importlib.util.spec_from_file_location("maintenance_dependency_scanner", SCANNER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("relative", [
    "skills/ai-workflow/writing-skills/render-graphs.js",
    "skills/ai-agent-platform/develop-web-game/scripts/web_game_playwright_client.js",
])
def test_direct_node_helpers_have_explicit_module_scope(relative):
    result = subprocess.run(["node", "--check", str(ROOT / relative)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_dependency_inventory_does_not_claim_a_vulnerability_assessment(tmp_path):
    (tmp_path / "Cargo.lock").write_text('[[package]]\nname = "serde"\nversion = "1.0.100"\n')
    scanner = scanner_module().DependencyScanner()
    result = scanner.scan_project(str(tmp_path))
    report = scanner.generate_report(result, "json")
    assert result["vulnerability_status"] == "not_assessed"
    assert "RUSTSEC-2022-0061" not in report
    assert result["vulnerabilities_found"] == 0
    assert "NOT ASSESSED" in scanner.generate_report(result)
    assert "go.sum" not in scanner.supported_files


def test_unassessed_security_gate_fails_closed(tmp_path):
    (tmp_path / "package.json").write_text('{"dependencies":{"lodash":"4.17.20"}}')
    result = subprocess.run([sys.executable, str(SCANNER), str(tmp_path), "--format", "json", "--fail-on-high"], capture_output=True, text=True)
    assert result.returncode == 2
    assert json.loads(result.stdout)["vulnerability_status"] == "not_assessed"


def test_malformed_manifest_is_reported_as_incomplete_inventory(tmp_path):
    (tmp_path / "package.json").write_text('{broken')
    result = scanner_module().DependencyScanner().scan_project(str(tmp_path))
    assert result["inventory_status"] == "partial"
    assert len(result["parse_errors"]) == 1
    assert result["parse_errors"][0]["path"].endswith("package.json")


def load_helper(name):
    path = SCANNER.parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"maintenance_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_upgrade_planner_does_not_fabricate_latest_versions(tmp_path):
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps({"dependencies":[{"name":"react", "version":"16.0.0", "ecosystem":"npm", "direct":True}]}))
    result = subprocess.run([sys.executable, str(SCANNER.parent / 'upgrade_planner.py'), str(inventory), '--format', 'json'], capture_output=True, text=True)
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report['version_status'] == 'not_assessed'
    assert report['available_upgrades'] == []
    assert '18.2.0' not in result.stdout


@pytest.mark.parametrize('license_name', ['MIT AND GPL-3.0', 'not-a-permit-license', 'Unlicense', 'public domain'])
def test_license_classifier_does_not_turn_substrings_or_other_licenses_into_mit(license_name):
    result = load_helper('license_checker').LicenseChecker()._resolve_license_info(license_name)
    assert result is None or result.spdx_id != 'MIT'
