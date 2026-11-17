"""Root-identity regressions using real renames and synthetic files only."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest


SCRIPTS = (Path(__file__).resolve().parents[1]
           / "skills/developer-engineering/repomix-safe-mixer/scripts")
OUTSIDE = "OUTSIDE_SYNTHETIC_BODY"


def load(name):
    spec = importlib.util.spec_from_file_location("root_identity_" + name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def tree(tmp_path):
    parent = tmp_path / "parent"
    parent.mkdir()
    root = parent / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    for directory, body in ((root, "value = 1\n"), (outside, OUTSIDE + "\n")):
        for name in ("first.py", "second.py"):
            (directory / name).write_text(body, encoding="utf-8")
    return root, outside


def switch(tree, component):
    root, outside = tree
    if component in ("root", "root-directory"):
        root.rename(root.with_name("original-project"))
        if component == "root":
            root.symlink_to(outside, target_is_directory=True)
        else:
            root.mkdir()
            for file in outside.glob("*.py"):
                (root / file.name).write_bytes(file.read_bytes())
    elif component == "parent-directory":
        # Preserve the exact root inode but replace its parent with a new
        # regular directory: a root-inode-only check must not accept this.
        parent = root.parent
        moved = parent.with_name("original-parent")
        parent.rename(moved)
        parent.mkdir()
        (moved / root.name).rename(root)
    else:
        replacement = outside / "project"
        replacement.mkdir()
        for file in outside.glob("*.py"):
            (replacement / file.name).write_bytes(file.read_bytes())
        parent = root.parent
        parent.rename(parent.with_name("original-parent"))
        parent.symlink_to(outside, target_is_directory=True)


def observe_reads(scan, monkeypatch):
    outside_reads = []
    real_finditer = scan.re.finditer

    def finditer(pattern, line, *args, **kwargs):
        if OUTSIDE in line:
            outside_reads.append(line)
        return real_finditer(pattern, line, *args, **kwargs)

    monkeypatch.setattr(scan.re, "finditer", finditer)
    return outside_reads


def scanner_cli(scan, argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(sys, "argv", argv)
            with pytest.raises(SystemExit) as result:
                scan.main()
    return subprocess.CompletedProcess(argv, result.value.code, out.getvalue(), err.getvalue())


@pytest.mark.parametrize("component", ["root", "parent", "root-directory", "parent-directory"])
@pytest.mark.parametrize("file_number", [1, 2])
def test_root_identity_cannot_change_between_files(tree, monkeypatch, component, file_number):
    scan = load("scan_secrets")
    reads = observe_reads(scan, monkeypatch)
    real_scan = scan.scan_file
    count = 0

    def race(file, directory):
        nonlocal count
        count += 1
        if count == file_number:
            switch(tree, component)
        return real_scan(file, directory)

    monkeypatch.setattr(scan, "scan_file", race)
    result = scanner_cli(scan, ["scan_secrets.py", str(tree[0]), "--json"])
    assert reads == [], "scanner consumed an outside synthetic file"
    assert result.returncode == 2
    assert result.stdout == ""


@pytest.mark.parametrize("component", ["root", "parent", "root-directory", "parent-directory"])
@pytest.mark.parametrize("stage", ["before-scanner", "after-scanner", "during-scanner"])
def test_pack_keeps_original_root_across_scanner_boundary(tree, monkeypatch, component, stage):
    pack, scan = load("safe_pack"), load("scan_secrets")
    reads = observe_reads(scan, monkeypatch)
    packer = Mock()
    monkeypatch.setattr(pack, "run_repomix", packer)
    monkeypatch.setattr(sys, "argv", ["safe_pack.py", str(tree[0])])
    real_scan = scan.scan_file
    switched = False

    def race(file, directory):
        nonlocal switched
        if stage == "during-scanner" and not switched:
            switch(tree, component)
            switched = True
        return real_scan(file, directory)

    monkeypatch.setattr(scan, "scan_file", race)

    def scanner_substitute(command, **kwargs):
        assert 0 < kwargs["timeout"] <= 60
        if stage == "before-scanner":
            switch(tree, component)
        result = scanner_cli(scan, command[1:])
        if stage == "after-scanner":
            assert result.returncode == 0
            switch(tree, component)
        return result

    monkeypatch.setattr(pack.subprocess, "run", scanner_substitute)
    with pytest.raises(SystemExit) as result:
        pack.main()
    assert result.value.code == 2
    assert reads == []
    packer.assert_not_called()


@pytest.mark.parametrize("component", ["root", "parent", "parent-directory"])
def test_root_rechecked_after_file_fd_acquired(tree, monkeypatch, component):
    scan = load("scan_secrets")
    reads = observe_reads(scan, monkeypatch)
    real_open = os.open
    switched = False

    def race(path, flags, *args, **kwargs):
        nonlocal switched
        fd = real_open(path, flags, *args, **kwargs)
        if str(path).endswith(".py") and kwargs.get("dir_fd") is not None and not switched:
            switch(tree, component)
            switched = True
        return fd

    monkeypatch.setattr(scan.os, "open", race)
    result = scanner_cli(scan, ["scan_secrets.py", str(tree[0]), "--json"])
    assert switched
    assert reads == []
    assert result.returncode == 2


@pytest.mark.parametrize("component", ["root", "parent", "parent-directory"])
def test_empty_scan_cannot_hide_root_switch(tree, monkeypatch, component):
    scan = load("scan_secrets")
    for file in tree[0].iterdir():
        file.unlink()
    real_walk = scan.os.fwalk

    def walk(*args, **kwargs):
        yield from real_walk(*args, **kwargs)
        switch(tree, component)

    monkeypatch.setattr(scan.os, "fwalk", walk)
    result = scanner_cli(scan, ["scan_secrets.py", str(tree[0]), "--json"])
    assert result.returncode == 2
    assert result.stdout == ""


@pytest.mark.parametrize("component", ["root", "parent"])
def test_traversal_never_enumerates_replacement_root(tree, monkeypatch, component):
    scan = load("scan_secrets")
    real_walk, real_scandir = scan.os.fwalk, scan.os.scandir
    outside_ids, enumerated = set(), []

    def walk(*args, **kwargs):
        switch(tree, component)
        for directory in (tree[1], tree[1] / "project"):
            if directory.is_dir():
                info = directory.stat()
                outside_ids.add((info.st_dev, info.st_ino))
        yield from real_walk(*args, **kwargs)

    def scandir(path):
        info = os.fstat(path) if isinstance(path, int) else os.stat(path)
        if (info.st_dev, info.st_ino) in outside_ids:
            enumerated.append(path)
        return real_scandir(path)

    monkeypatch.setattr(scan.os, "fwalk", walk)
    monkeypatch.setattr(scan.os, "scandir", scandir)
    result = scanner_cli(scan, ["scan_secrets.py", str(tree[0]), "--json"])
    assert outside_ids
    assert enumerated == []
    assert result.returncode == 2


@pytest.mark.parametrize("component", [None, "root", "parent", "root-directory", "parent-directory"])
def test_real_child_handoff_and_pack_launch_window(tree, tmp_path, monkeypatch, component):
    """Use the real scanner child and a bounded harmless executable substitute."""
    pack = load("safe_pack")
    marker = tmp_path / "packer-started.json"
    real_run = subprocess.run
    invocations = []

    def launch(command, **kwargs):
        if command[0] != "repomix":
            return real_run(command, **kwargs)
        invocations.append(command)
        if component is not None:
            # This happens after run_repomix's parent-side checks, immediately
            # before the real subprocess handles cwd and runs preexec_fn.
            switch(tree, component)
        substitute = (
            "import json, os; from pathlib import Path; "
            f"Path({str(marker)!r}).write_text(json.dumps([os.stat('.').st_dev, os.stat('.').st_ino]))"
        )
        return real_run([sys.executable, "-c", substitute], timeout=5, **kwargs)

    initial = tree[0].stat()
    monkeypatch.setattr(pack.subprocess, "run", launch)
    monkeypatch.setattr(sys, "argv", ["safe_pack.py", str(tree[0])])
    if component is None:
        pack.main()
        assert json.loads(marker.read_text()) == [initial.st_dev, initial.st_ino]
    else:
        with pytest.raises(SystemExit) as result:
            pack.main()
        assert result.value.code == 2
        assert not marker.exists(), "packer executable must not start after a root switch"
    assert len(invocations) == 1


@pytest.mark.parametrize("capability", ["DIR_FD_SUPPORTED", "O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK", "fwalk"])
def test_missing_safe_scan_primitives_fail_closed(tree, monkeypatch, capability):
    scan = load("scan_secrets")
    reads = observe_reads(scan, monkeypatch)
    if capability == "DIR_FD_SUPPORTED":
        monkeypatch.setattr(scan, capability, False)
    else:
        monkeypatch.delattr(scan.os, capability)
    result = scanner_cli(scan, ["scan_secrets.py", str(tree[0]), "--json"])
    assert result.returncode == 2
    assert result.stdout == ""
    assert reads == []


def test_missing_safe_pack_cwd_primitive_never_launches(tree, monkeypatch):
    pack = load("safe_pack")
    monkeypatch.delattr(pack.os, "fchdir")
    command = Mock()
    monkeypatch.setattr(pack.subprocess, "run", command)
    with pytest.raises(SystemExit) as result:
        pack.run_repomix(tree[0])
    assert result.value.code == 2
    command.assert_not_called()


@pytest.mark.parametrize("identity", ["null", "[]", "{}", "invalid-json"])
def test_invalid_inherited_identity_never_falls_back_to_a_new_root(tree, identity, monkeypatch):
    scan = load("scan_secrets")
    read = Mock(wraps=scan.os.fdopen)
    monkeypatch.setattr(scan.os, "fdopen", read)
    result = scanner_cli(scan, ["scan_secrets.py", str(tree[0]), "--json",
                                "--root-identity", identity])
    assert result.returncode == 2
    assert result.stdout == ""
    read.assert_not_called()


def test_real_scanner_handoff_preserves_exclusions(tree, monkeypatch):
    pack = load("safe_pack")
    (tree[0] / "first.py").write_text("-----BEGIN PRIVATE KEY-----\n")
    packer = Mock()
    monkeypatch.setattr(pack, "run_repomix", packer)
    monkeypatch.setattr(sys, "argv", ["safe_pack.py", str(tree[0]), "--exclude", "first.py$"])
    pack.main()
    packer.assert_called_once_with(tree[0].resolve(), None, None)


@pytest.mark.parametrize("body,code", [("value = 1\n", 0), ("-----BEGIN PRIVATE KEY-----\n", 1)])
def test_regular_files_keep_success_findings_and_redaction(tree, body, code):
    scan = load("scan_secrets")
    (tree[0] / "first.py").write_text(body)
    result = scanner_cli(scan, ["scan_secrets.py", str(tree[0]), "--json"])
    assert result.returncode == code
    findings = json.loads(result.stdout)
    assert bool(findings) == bool(code)
    if findings:
        assert findings[0]["match"] == findings[0]["context"] == "[REDACTED]"
        assert body.strip() not in result.stdout + result.stderr
