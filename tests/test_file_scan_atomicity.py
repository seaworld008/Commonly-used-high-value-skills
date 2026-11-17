"""File-boundary and initialization regressions, using synthetic local data only."""
import builtins
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import Mock

import pytest


ROOT = Path(__file__).resolve().parents[1]
MIXER = ROOT / "skills/developer-engineering/repomix-safe-mixer/scripts"
QA = ROOT / "skills/developer-engineering/qa-expert/scripts/init_qa_project.py"


def load_module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cli(script, *args, timeout=5):
    return subprocess.run([sys.executable, str(script), *map(str, args)],
                          capture_output=True, text=True, timeout=timeout)


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "clean.py").write_text("value = 1\n")
    return root


@pytest.fixture
def pack(project, monkeypatch):
    module = load_module(MIXER / "safe_pack.py")
    monkeypatch.setattr(sys, "argv", ["safe_pack.py", str(project)])
    monkeypatch.setattr(module, "run_repomix", Mock())
    return module


@pytest.mark.parametrize("name", [".env.local", "ordinary.py"])
def test_outside_link_is_rejected_before_any_open(project, tmp_path, monkeypatch, name):
    outside = tmp_path / "outside.txt"
    outside.write_text("synthetic confidential content\n")
    (project / name).symlink_to(outside)
    scan = load_module(MIXER / "scan_secrets.py")
    attempts = []
    real_builtin_open, real_os_open = builtins.open, os.open

    def guard(original):
        def checked(path, *args, **kwargs):
            if not isinstance(path, int) and Path(path).resolve() == outside.resolve():
                attempts.append(path)
                raise PermissionError("outside target must never be opened")
            return original(path, *args, **kwargs)
        return checked

    monkeypatch.setattr(builtins, "open", guard(real_builtin_open))
    monkeypatch.setattr(scan.os, "open", guard(real_os_open))
    monkeypatch.setattr(sys, "argv", ["scan_secrets.py", str(project), "--json"])
    with pytest.raises(SystemExit) as error:
        scan.main()
    assert error.value.code == 2
    assert attempts == []


@pytest.mark.parametrize("kind", ["fifo", "outside-link", "directory-link"])
def test_unsafe_tree_stops_scanner_promptly_and_never_packs(pack, project, tmp_path, kind):
    if kind == "fifo":
        os.mkfifo(project / ".env.local")
    elif kind == "outside-link":
        outside = tmp_path / "outside.txt"
        outside.write_text("synthetic content")
        (project / "linked.py").symlink_to(outside)
    else:
        (project / "linked-directory").symlink_to(tmp_path, target_is_directory=True)
    start = time.monotonic()
    scan = cli(MIXER / "scan_secrets.py", project, "--json")
    assert scan.returncode == 2
    assert time.monotonic() - start < 5
    with pytest.raises(SystemExit) as error:
        pack.main()
    assert error.value.code == 2
    pack.run_repomix.assert_not_called()


def test_fd_check_rejects_file_replaced_with_real_fifo(project, monkeypatch):
    scan = load_module(MIXER / "scan_secrets.py")
    leaf = project / "clean.py"
    original = os.open
    raced = False

    def race(path, flags, *args, **kwargs):
        nonlocal raced
        if path == leaf.name and kwargs.get("dir_fd") is not None:
            assert flags & os.O_NONBLOCK  # A regression must fail, never hang pytest.
            leaf.unlink()
            os.mkfifo(leaf)
            raced = True
        return original(path, flags, *args, **kwargs)

    monkeypatch.setattr(scan.os, "open", race)
    read = Mock(wraps=scan.os.fdopen)
    monkeypatch.setattr(scan.os, "fdopen", read)
    with pytest.raises(OSError):
        scan.scan_file(leaf, project)
    assert raced
    read.assert_not_called()


def test_boundary_rechecked_after_fd_acquired(project, tmp_path, monkeypatch):
    scan = load_module(MIXER / "scan_secrets.py")
    leaf = project / "clean.py"
    outside = tmp_path / "outside.txt"
    outside.write_text("synthetic content")
    original = os.open

    def race(path, flags, *args, **kwargs):
        fd = original(path, flags, *args, **kwargs)
        if path == leaf.name and kwargs.get("dir_fd") is not None:
            leaf.unlink()
            leaf.symlink_to(outside)
        return fd

    monkeypatch.setattr(scan.os, "open", race)
    read = Mock(wraps=scan.os.fdopen)
    monkeypatch.setattr(scan.os, "fdopen", read)
    with pytest.raises(OSError):
        scan.scan_file(leaf, project)
    read.assert_not_called()


def test_parent_replaced_by_outside_link_cannot_redirect_open(project, tmp_path, monkeypatch):
    scan = load_module(MIXER / "scan_secrets.py")
    parent = project / "nested"
    parent.mkdir()
    (parent / "code.py").write_text("value = 1\n")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "code.py").write_text("synthetic confidential content")
    original = os.open

    def race(path, flags, *args, **kwargs):
        if path == "nested" and kwargs.get("dir_fd") is not None:
            parent.rename(project / "old-nested")
            parent.symlink_to(outside, target_is_directory=True)
        return original(path, flags, *args, **kwargs)

    monkeypatch.setattr(scan.os, "open", race)
    with pytest.raises(OSError):
        scan.scan_file(parent / "code.py", project)


def test_regular_files_and_internal_file_links_still_scan(project):
    (project / "internal.py").symlink_to(project / "clean.py")
    clean = cli(MIXER / "scan_secrets.py", project, "--json")
    assert clean.returncode == 0
    assert json.loads(clean.stdout) == []
    (project / ".env.local").write_text("API_KEY=syntheticcredentialvalue12345\n")
    found = cli(MIXER / "scan_secrets.py", project, "--json")
    assert found.returncode == 1
    findings = json.loads(found.stdout)
    assert findings[0]["file"] == ".env.local"
    assert findings[0]["match"] == findings[0]["context"] == "[REDACTED]"
    assert "syntheticcredential" not in found.stdout + found.stderr


def test_explicitly_excluded_links_preserve_existing_scan_scope(project, tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("synthetic content")
    (project / ".env.excluded").symlink_to(outside)
    (project / "excluded-directory").symlink_to(tmp_path, target_is_directory=True)
    result = cli(MIXER / "scan_secrets.py", project, "--json", "--exclude",
                 r"\.env\.excluded$", r"excluded-directory$")
    assert result.returncode == 0
    assert json.loads(result.stdout) == []


def test_scan_timeout_is_bounded_and_prevents_pack(pack, monkeypatch):
    def timeout(cmd, **kwargs):
        assert 0 < kwargs["timeout"] <= 60
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    monkeypatch.setattr(pack.subprocess, "run", timeout)
    with pytest.raises(SystemExit) as error:
        pack.main()
    assert error.value.code == 2
    pack.run_repomix.assert_not_called()


def test_completed_real_clean_scan_allows_pack(pack, project):
    pack.main()
    pack.run_repomix.assert_called_once_with(project.resolve(), None, None)


def test_real_scanner_subprocess_timeout_is_enforced(pack, tmp_path, monkeypatch):
    substitute = tmp_path / "substitute"
    substitute.mkdir()
    (substitute / "scan_secrets.py").write_text("import time\ntime.sleep(5)\n")
    monkeypatch.setattr(pack, "__file__", str(substitute / "safe_pack.py"))
    monkeypatch.setattr(pack, "SCAN_TIMEOUT_SECONDS", 0.1)
    start = time.monotonic()
    with pytest.raises(SystemExit) as error:
        pack.main()
    assert error.value.code == 2
    assert time.monotonic() - start < 3
    pack.run_repomix.assert_not_called()


@pytest.mark.parametrize("kind", ["missing", "directory", "fifo", "unreadable", "no-argument"])
def test_explicit_invalid_config_fails_before_scan_or_pack(pack, project, monkeypatch, kind):
    config = project / "config.json"
    if kind == "directory":
        config.mkdir()
    elif kind == "fifo":
        os.mkfifo(config)
    elif kind == "unreadable":
        config.write_text("{}")
        real_open = os.open

        def deny(path, *args, **kwargs):
            if Path(path) == config:
                raise PermissionError("synthetic denial")
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr(pack.os, "open", deny)
    args = ["safe_pack.py", str(project), "--config"]
    if kind != "no-argument":
        args.append(str(config))
    monkeypatch.setattr(sys, "argv", args)
    scan = Mock(return_value=[])
    monkeypatch.setattr(pack, "run_secret_scan", scan)
    with pytest.raises(SystemExit) as error:
        pack.main()
    assert error.value.code == 2
    scan.assert_not_called()
    pack.run_repomix.assert_not_called()


def test_relative_config_is_absolute_from_callers_cwd(project, tmp_path, monkeypatch):
    pack = load_module(MIXER / "safe_pack.py")
    caller = tmp_path / "caller"
    caller.mkdir()
    config = caller / "config.json"
    config.write_text('{"include": ["clean.py"]}')
    (project / "config.json").write_text('{"include": ["wrong.py"]}')
    monkeypatch.chdir(caller)
    monkeypatch.setattr(sys, "argv", ["safe_pack.py", str(project), "--config", "config.json"])
    monkeypatch.setattr(pack, "run_secret_scan", Mock(return_value=[]))
    command = Mock(return_value=subprocess.CompletedProcess([], 0, "packed", ""))
    monkeypatch.setattr(pack.subprocess, "run", command)
    pack.main()
    assert command.call_args.args[0] == ["repomix", "--config", str(config.resolve())]
    assert command.call_args.kwargs["cwd"] == project.resolve()


def test_direct_pack_missing_config_never_invokes_cli(project, monkeypatch):
    pack = load_module(MIXER / "safe_pack.py")
    command = Mock()
    monkeypatch.setattr(pack.subprocess, "run", command)
    with pytest.raises(SystemExit) as error:
        pack.run_repomix(project, config_file=project / "missing.json")
    assert error.value.code == 2
    command.assert_not_called()


def target_bytes(root, module):
    return {name: (root / name).read_bytes() for name in module.TARGET_FILES
            if (root / name).is_file()}


def test_qa_third_template_failure_can_retry_directly(tmp_path, monkeypatch):
    qa = load_module(QA)
    monkeypatch.setattr(sys, "argv", ["init_qa_project.py", "project", str(tmp_path)])
    original = builtins.open

    def fail_third(path, mode="r", *args, **kwargs):
        if Path(path).name == qa.BASELINE.name and mode == "x":
            raise OSError("injected third-template failure")
        return original(path, mode, *args, **kwargs)

    with monkeypatch.context() as failing:
        failing.setattr(builtins, "open", fail_third)
        with pytest.raises((SystemExit, OSError)):
            qa.main()
    assert target_bytes(tmp_path, qa) == {}
    qa.main()
    assert len(target_bytes(tmp_path, qa)) == 6
    assert b"project" in (tmp_path / qa.MASTER).read_bytes()


@pytest.mark.parametrize("user_change", ["none", "replace", "edit", "same-stat-edit", "new-target"])
def test_qa_publish_failure_rolls_back_only_own_files(tmp_path, monkeypatch, user_change):
    qa = load_module(QA)
    monkeypatch.setattr(sys, "argv", ["init_qa_project.py", "project", str(tmp_path)])
    real_open = os.open
    evidence = b"concurrent user evidence"
    preserved = tmp_path / (qa.BASELINE if user_change == "new-target" else qa.TRACKING)

    def fail_third(path, flags, *args, **kwargs):
        nonlocal evidence
        if Path(path) == tmp_path / qa.BASELINE and flags & os.O_CREAT:
            if user_change == "replace":
                preserved.unlink()
                preserved.write_bytes(evidence)
            elif user_change in ("edit", "new-target"):
                preserved.write_bytes(evidence)
            elif user_change == "same-stat-edit":
                info = preserved.stat()
                evidence = b"U" * info.st_size
                preserved.write_bytes(evidence)
                os.utime(preserved, ns=(info.st_atime_ns, info.st_mtime_ns))
            if user_change == "new-target":
                return real_open(path, flags, *args, **kwargs)
            raise OSError("injected publish failure")
        return real_open(path, flags, *args, **kwargs)

    with monkeypatch.context() as failing:
        failing.setattr(qa.os, "open", fail_third)
        with pytest.raises(SystemExit):
            qa.main()
    if user_change == "none":
        assert target_bytes(tmp_path, qa) == {}
        qa.main()
        assert len(target_bytes(tmp_path, qa)) == 6
    else:
        assert target_bytes(tmp_path, qa) == {preserved.relative_to(tmp_path): evidence}
        with pytest.raises(SystemExit):
            qa.main()
        assert preserved.read_bytes() == evidence


def test_qa_partial_publication_write_failure_is_retryable(tmp_path, monkeypatch):
    qa = load_module(QA)
    monkeypatch.setattr(sys, "argv", ["init_qa_project.py", "project", str(tmp_path)])
    original = os.write
    calls = 0

    def fail_partial(fd, content):
        nonlocal calls
        calls += 1
        if calls == 1:
            return original(fd, content[:10])
        raise OSError("injected partial write failure")

    with monkeypatch.context() as failing:
        failing.setattr(qa.os, "write", fail_partial)
        with pytest.raises(SystemExit):
            qa.main()
    assert target_bytes(tmp_path, qa) == {}
    qa.main()
    assert len(target_bytes(tmp_path, qa)) == 6


def test_qa_existing_evidence_is_unchanged(tmp_path, monkeypatch):
    qa = load_module(QA)
    monkeypatch.setattr(sys, "argv", ["init_qa_project.py", "project", str(tmp_path)])
    qa.main()
    for name in qa.TARGET_FILES:
        (tmp_path / name).write_bytes(b"recorded evidence: " + name.name.encode())
    before = target_bytes(tmp_path, qa)
    with pytest.raises(SystemExit):
        qa.main()
    assert len(before) == 6
    assert target_bytes(tmp_path, qa) == before
