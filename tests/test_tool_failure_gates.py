"""Exercise CLI failure gates using only temporary, controlled inputs."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest


SKILLS = Path(__file__).resolve().parents[1] / "skills/developer-engineering"
MIXER = SKILLS / "repomix-safe-mixer/scripts"
TESTER = SKILLS / "skill-tester/scripts/script_tester.py"
QA = SKILLS / "qa-expert/scripts/init_qa_project.py"
MARKER = "harmless-regression-marker"
FINDING = {"file": ".env", "line": 1, "type": "generic_api_key",
           "match": "[REDACTED]", "context": "[REDACTED]"}


def run_cli(script, *args):
    return subprocess.run([sys.executable, str(script), *map(str, args)],
                          text=True, capture_output=True, timeout=15)


@pytest.fixture
def pack(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("safe_pack", MIXER / "safe_pack.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(sys, "argv", ["safe_pack.py", str(tmp_path), "--force"])
    monkeypatch.setattr(module, "run_repomix", Mock())
    return module


@pytest.mark.parametrize("code,stdout,stderr,expected", [
    (2, "[]", "", 2),
    (1, "[]", "", 2),
    (0, "", "", 2),
    (0, MARKER, "", 2),
    (0, "{}", "", 2),
    (0, "[]", MARKER, 2),
    (0, json.dumps([FINDING]), "", 2),
    (1, json.dumps([{"match": MARKER}]), "", 2),
    (1, json.dumps([FINDING]), "", 1),
])
def test_pack_rejects_scan_errors_and_findings(pack, monkeypatch, capsys, code, stdout, stderr, expected):
    monkeypatch.setattr(pack.subprocess, "run", Mock(return_value=subprocess.CompletedProcess(
        [], code, stdout, stderr)))
    with pytest.raises(SystemExit) as exit_info:
        pack.main()
    assert exit_info.value.code == expected
    pack.run_repomix.assert_not_called()
    output = capsys.readouterr()
    assert MARKER not in output.out + output.err


def test_pack_accepts_completed_clean_scan(pack, tmp_path, monkeypatch):
    monkeypatch.setattr(pack.subprocess, "run", Mock(return_value=subprocess.CompletedProcess(
        [], 0, "[]", "")))
    pack.main()
    pack.run_repomix.assert_called_once_with(tmp_path.resolve(), None, None)


def test_scanner_launch_failure_stops_pack(pack, monkeypatch, capsys):
    monkeypatch.setattr(pack.subprocess, "run", Mock(side_effect=OSError(MARKER)))
    with pytest.raises(SystemExit) as exit_info:
        pack.main()
    assert exit_info.value.code == 2
    pack.run_repomix.assert_not_called()
    output = capsys.readouterr()
    assert MARKER not in output.out + output.err


@pytest.mark.parametrize("unreadable", ["missing", "invalid-utf8"])
def test_incomplete_file_scan_stops_pack(pack, tmp_path, capsys, unreadable):
    # Include a readable file: partial results must never reach the packager.
    (tmp_path / "first.py").write_text("x = 1\n")
    broken = tmp_path / ".env.local"
    if unreadable == "missing":
        broken.symlink_to(tmp_path / "missing")
    else:
        broken.write_bytes(MARKER.encode() + b"\xff")
    with pytest.raises(SystemExit) as exit_info:
        pack.main()
    assert exit_info.value.code == 2
    pack.run_repomix.assert_not_called()
    output = capsys.readouterr()
    assert MARKER not in output.out + output.err


def test_env_and_pem_findings_are_redacted(tmp_path):
    names = [".env", ".env.local", ".env.custom-stage"]
    for name in names:
        (tmp_path / name).write_text(f"API_KEY={MARKER}\n")
    (tmp_path / "key.pem").write_text("-----BEGIN PRIVATE KEY-----\n")
    report = run_cli(MIXER / "scan_secrets.py", tmp_path, "--json")
    assert report.returncode == 1
    assert MARKER not in report.stdout + report.stderr
    findings = json.loads(report.stdout)
    expected = {(name, "generic_api_key") for name in names}
    expected.add(("key.pem", "private_key"))
    assert {(f["file"], f["type"]) for f in findings} == expected
    assert all(f["match"] == f["context"] == "[REDACTED]" for f in findings)


@pytest.mark.parametrize("setup,action,exit_code,json_verified", [
    ("", "raise RuntimeError('controlled failure')", 1, False),
    ("parser.add_argument('input_file')", "print('done')", 2, False),
    ("", "print('plain text')", 0, False),
    ("", "print(json.dumps([1]) if args.json else 'plain text')", 0, True),
])
def test_script_results_follow_execution(tmp_path, setup, action, exit_code, json_verified):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "subject.py").write_text(
        "import argparse\nimport json\n"
        "if __name__ == '__main__':\n"
        "    parser = argparse.ArgumentParser()\n"
        "    parser.add_argument('--json', action='store_true')\n"
        f"    {setup}\n"
        "    args = parser.parse_args()\n"
        f"    {action}\n")
    run = run_cli(TESTER, tmp_path, "--json")
    report = json.loads(run.stdout)
    script = report["script_results"]["subject.py"]
    checks = script["tests"]
    assert checks["help_functionality"]["passed"]
    assert checks["basic_execution"]["passed"] == (exit_code == 0)
    if exit_code:
        assert f"code {exit_code}" in checks["basic_execution"]["message"]
    assert checks["output_formats"]["details"]["json_support"] == json_verified
    assert checks["output_formats"]["passed"] == json_verified
    assert (run.returncode == 0) == json_verified
    assert (report["summary"]["overall_status"] == "PASS") == json_verified


def snapshot(root):
    return {p.relative_to(root): p.read_bytes() if p.is_file() else None
            for p in root.rglob("*")}


def test_qa_rerun_preserves_all_evidence(tmp_path):
    initial = run_cli(QA, "project", tmp_path)
    assert initial.returncode == 0, initial.stderr
    files = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert len(files) == 6
    for file in files:
        file.write_bytes(b"recorded evidence: " + file.name.encode())
    before = snapshot(tmp_path)
    rerun = run_cli(QA, "other project", tmp_path)
    assert rerun.returncode != 0
    assert snapshot(tmp_path) == before


def test_qa_last_target_conflict_prevents_all_writes(tmp_path):
    docs = tmp_path / "tests/docs"
    docs.mkdir(parents=True)
    (docs / "README.md").write_text("existing evidence")
    before = snapshot(tmp_path)
    rerun = run_cli(QA, "project", tmp_path)
    assert rerun.returncode != 0
    assert "README.md" in rerun.stderr
    assert snapshot(tmp_path) == before
