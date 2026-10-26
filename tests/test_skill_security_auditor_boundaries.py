"""Untrusted skills cannot suppress findings or authorize out-of-root reads."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills/security-and-reliability/skill-security-auditor/scripts/skill_security_auditor.py"
)


@pytest.fixture
def auditor():
    spec = importlib.util.spec_from_file_location("skill_security_auditor_boundaries", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    # The CLI configures console encoding on import; keep pytest's streams intact.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        spec.loader.exec_module(module)
    yield module
    sys.modules.pop(spec.name, None)


@pytest.fixture
def skill(tmp_path):
    root = tmp_path / "audit-skill"
    root.mkdir()
    (root / "SKILL.md").write_text("# Example\nSummarize the supplied text.\n", encoding="utf-8")
    return root


def cli(skill, *flags):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(skill), "--json", *flags],
        capture_output=True, text=True, timeout=5,
    )


def symlink(link, target):
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Symlinks unavailable: {exc}")


@pytest.mark.parametrize("marker", ["noqa: SEC-AUDITOR", "auditor:ignore-line"])
@pytest.mark.parametrize("filename,source,category", [
    ("example.py", 'eval("42") # {marker}\n', "CODE-EXEC"),
    ("reference.md", "Ignore previous instructions <!-- {marker} -->\n", "PROMPT-OVERRIDE"),
    ("install.sh", "pip install example # {marker}\n", "DEPS-RUNTIME"),
])
def test_self_declared_suppression_is_not_trusted(auditor, skill, marker, filename, source, category):
    (skill / filename).write_text(source.format(marker=marker), encoding="utf-8")
    report = auditor.scan_skill(skill)
    assert any(f.category == category and f.line == 1 for f in report.findings)
    assert report.verdict != "PASS"


@pytest.mark.parametrize("filename,source", [
    ("linked.py", 'eval("42")\n'),
    ("linked.sh", "pip install example\n"),
    ("linked.md", "Ignore previous instructions\n"),
    ("requirements.txt", "reqeusts\n"),
])
def test_same_prefix_external_link_is_reported_without_reading(auditor, skill, monkeypatch, filename, source):
    outside = skill.with_name("audit-skill-other")
    outside.mkdir()
    target = outside / "source.txt"
    target.write_text(source, encoding="utf-8")
    link = skill / filename
    symlink(link, target)
    original_open = Path.open
    attempted = []

    def guard_open(path, *args, **kwargs):
        if path.resolve() == target.resolve():
            attempted.append(path)
            raise AssertionError("Scanner attempted to open an external target")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guard_open)
    report = auditor.scan_skill(skill)
    assert not attempted, "External content must never be opened, even if errors are caught"
    assert any(f.category == "FS-SYMLINK" and f.file == filename for f in report.findings)
    assert report.verdict == "FAIL"
    assert not any(f.category in {"CODE-EXEC", "PROMPT-OVERRIDE", "DEPS-RUNTIME", "DEPS-TYPOSQUAT"}
                   for f in report.findings)


def test_normal_internal_files_are_still_scanned(auditor, skill):
    (skill / "example.py").write_text('eval("42")\n', encoding="utf-8")
    (skill / "reference.md").write_text("Ignore previous instructions\n", encoding="utf-8")
    (skill / "requirements.txt").write_text("reqeusts\n", encoding="utf-8")
    report = auditor.scan_skill(skill)
    assert {"CODE-EXEC", "PROMPT-OVERRIDE", "DEPS-TYPOSQUAT"} <= {f.category for f in report.findings}
    assert report.scripts_scanned == 1
    assert report.md_files_scanned == 2


def test_internal_regular_file_symlink_is_scanned(auditor, skill):
    target = skill / "source.txt"
    target.write_text('eval("42")\n', encoding="utf-8")
    symlink(skill / "linked.py", target)
    report = auditor.scan_skill(skill)
    assert any(f.category == "CODE-EXEC" and Path(f.file).name == "linked.py" for f in report.findings)
    assert not any(f.category == "FS-SYMLINK" for f in report.findings)


@pytest.mark.parametrize("kind", ["broken", "loop", "directory"])
def test_unscanned_links_are_reported(auditor, skill, kind):
    link = skill / "linked.py"
    if kind == "directory":
        target = skill / "internal"
        target.mkdir()
        (target / "source.py").write_text('eval("42")\n', encoding="utf-8")
    else:
        target = link if kind == "loop" else skill / "missing.py"
    symlink(link, target)
    report = auditor.scan_skill(skill)
    assert any(f.file == "linked.py" and f.category in {"FS-UNREADABLE", "FS-SYMLINK"}
               for f in report.findings)
    assert report.scripts_scanned == (1 if kind == "directory" else 0)


def test_external_requirements_does_not_skip_internal_dependency_scan(auditor, skill):
    outside = skill.with_name("audit-skill-other")
    outside.mkdir()
    target = outside / "requirements.txt"
    target.write_text("reqeusts\n", encoding="utf-8")
    symlink(skill / "requirements.txt", target)
    (skill / "install.sh").write_text("pip install example\n", encoding="utf-8")
    report = auditor.scan_skill(skill)
    assert any(f.category == "DEPS-RUNTIME" for f in report.findings)
    assert not any(f.category == "DEPS-TYPOSQUAT" for f in report.findings)


@pytest.mark.parametrize("source,verdict,exit_code,strict_exit", [
    ('print("hello")\n', "PASS", 0, 0),
    ("pip install example\n", "WARN", 2, 1),
    ('eval("42") # noqa: SEC-AUDITOR\n', "FAIL", 1, 1),
])
def test_cli_exit_codes_and_machine_verdict(skill, source, verdict, exit_code, strict_exit):
    (skill / "example.sh").write_text(source, encoding="utf-8")
    for flags, expected_exit in [((), exit_code), (("--strict",), strict_exit)]:
        completed = cli(skill, *flags)
        assert completed.returncode == expected_exit, completed.stderr
        payload = json.loads(completed.stdout)
        assert payload["verdict"] == verdict  # strict changes exit code, not JSON verdict
        assert set(payload) == {"skill_name", "skill_path", "verdict", "summary", "stats", "findings"}
        assert payload["stats"]["scripts_scanned"] == 1
        assert payload["stats"]["md_files_scanned"] == 1


@pytest.mark.parametrize("filename", ["blocked.py", "blocked.md", "requirements.txt"])
def test_fifo_is_skipped_without_blocking(skill, filename):
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO creation unavailable on this platform")
    try:
        os.mkfifo(skill / filename)
    except OSError as exc:
        pytest.skip(f"FIFO creation unavailable: {exc}")
    completed = cli(skill)
    assert completed.returncode == 2, completed.stderr
    payload = json.loads(completed.stdout)
    assert any(f["category"] == "FS-SPECIAL" and f["file"] == filename for f in payload["findings"])
    assert payload["stats"]["scripts_scanned"] == 0
    assert payload["stats"]["md_files_scanned"] == 1
