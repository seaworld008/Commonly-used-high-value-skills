"""Exercise real QA publication in child processes with isolated umasks."""

import contextlib
from datetime import datetime
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

import pytest


QA = (Path(__file__).resolve().parents[1]
      / "skills/developer-engineering/qa-expert/scripts/init_qa_project.py")
EVIDENCE = b"existing QA evidence\x00\xff\n"
MASKS = (0o000, 0o022)


class FixedDateTime(datetime):
    @classmethod
    def now(cls):
        return cls(2026, 1, 2, 3, 4, 5)


@pytest.fixture
def qa():
    spec = importlib.util.spec_from_file_location("qa_modes", QA)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.datetime = FixedDateTime
    return module


@pytest.fixture
def tree():
    # Never fall back to a shared system temporary directory.
    with tempfile.TemporaryDirectory(prefix="qa-modes-", dir=os.environ["TMPDIR"]) as root:
        yield Path(root)


CHILD = r'''
import contextlib
from datetime import datetime
import importlib.util
import io
import json
import os
from pathlib import Path
import sys

script, base, mask, fault, index = sys.argv[1:]
base = Path(base)
spec = importlib.util.spec_from_file_location("qa_child", script)
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)
class FixedDateTime(datetime):
    @classmethod
    def now(cls):
        return cls(2026, 1, 2, 3, 4, 5)
qa.datetime = FixedDateTime
os.umask(int(mask))  # Only this child process changes its umask.
real_open, real_write = os.open, os.write
trigger = base / qa.TARGET_FILES[int(index)]
first = base / qa.TARGET_FILES[0]
fired = False
partial_fd = None
partial_written = False
preserved = None
evidence = b"existing QA evidence\x00\xff\n"

def injected_open(path, flags, *args, **kwargs):
    global fired, partial_fd, preserved
    if Path(path) == trigger and flags & os.O_CREAT:
        fired = True
        if fault == "race-file":
            trigger.write_bytes(evidence)
        elif fault in ("race-symlink", "race-dangling"):
            trigger.symlink_to(base / "outside-evidence")
        elif fault in ("edit", "same-stat-edit", "replace", "symlink"):
            info = first.stat()
            if fault == "replace":
                # Pin the old inode so replacement cannot accidentally reuse it.
                preserved = first.read_bytes()
                first.rename(base / "pinned-original")
                first.write_bytes(preserved)
                os.utime(first, ns=(info.st_atime_ns, info.st_mtime_ns))
                assert first.stat().st_ino != info.st_ino
            elif fault == "symlink":
                first.unlink()
                first.symlink_to(base / "outside-evidence")
            else:
                preserved = (b"U" * info.st_size if fault == "same-stat-edit"
                             else b"externally modified QA evidence")
                first.write_bytes(preserved)
                if fault == "same-stat-edit":
                    os.utime(first, ns=(info.st_atime_ns, info.st_mtime_ns))
                    assert qa.file_identity(first.stat()) == qa.file_identity(info)
            raise OSError("injected publication failure")
        elif fault == "open-failure":
            raise OSError("injected publication failure")
        fd = real_open(path, flags, *args, **kwargs)
        if fault in ("partial-write", "zero-write"):
            partial_fd = fd
        return fd
    return real_open(path, flags, *args, **kwargs)

def injected_write(fd, content):
    global partial_written
    if fd == partial_fd:
        if not partial_written:
            partial_written = True
            return real_write(fd, content[:7])
        if fault == "zero-write":
            return 0
        raise OSError("injected partial write failure")
    return real_write(fd, content)

if fault:
    qa.os.open = injected_open
    qa.os.write = injected_write
sys.argv = [script, "mode-test", str(base)]
output = io.StringIO()
with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
    try:
        qa.main()
        code = 0
    except SystemExit as error:
        code = error.code
print(json.dumps({"code": code, "fired": fired, "partial": partial_written,
                  "preserved": preserved.hex() if preserved is not None else None,
                  "output": output.getvalue()}))
'''


def run_qa(base, mask, fault="", index=2):
    result = subprocess.run(
        [sys.executable, "-B", "-c", CHILD, str(QA), str(base), str(mask), fault, str(index)],
        cwd=base.parent, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def entries(base, qa):
    return {name for name in qa.TARGET_FILES if (base / name).exists()
            or (base / name).is_symlink()}


def render_expected(root, qa):
    with contextlib.redirect_stdout(io.StringIO()):
        qa.create_directory_structure(root)
        qa.create_test_execution_tracking(root, "mode-test")
        qa.create_bug_tracking_template(root)
        qa.create_baseline_metrics(root, "mode-test")
        qa.create_weekly_report_template(root)
        qa.create_master_qa_prompt(root, "mode-test")
        qa.create_readme(root, "mode-test")
    return {name: (root / name).read_bytes() for name in qa.TARGET_FILES}


@pytest.mark.parametrize("mask", MASKS, ids=["umask000", "umask022"])
def test_all_targets_have_private_modes_and_complete_content(tree, qa, mask):
    expected = render_expected(tree / "expected", qa)
    base = tree / "project"
    result = run_qa(base, mask)
    assert result["code"] == 0, result
    assert entries(base, qa) == set(qa.TARGET_FILES)
    for name, content in expected.items():
        path = base / name
        assert stat.S_ISREG(path.lstat().st_mode)
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert path.stat().st_mode & 0o022 == 0
        assert path.read_bytes() == content


@pytest.mark.parametrize("mask", MASKS, ids=["umask000", "umask022"])
@pytest.mark.parametrize("index", range(6))
@pytest.mark.parametrize("kind", ["file", "symlink", "dangling"])
@pytest.mark.parametrize("race", [False, True], ids=["preexisting", "after-preflight"])
def test_existing_targets_are_never_overwritten(tree, qa, mask, index, kind, race):
    base = tree / "project"
    base.mkdir()
    target = base / qa.TARGET_FILES[index]
    outside = base / "outside-evidence"
    if kind != "dangling":
        outside.write_bytes(EVIDENCE)
        outside.chmod(0o640)
    outside_info = outside.lstat() if outside.exists() else None
    if not race:
        target.parent.mkdir(parents=True)
        if kind == "file":
            target.write_bytes(EVIDENCE)
            target.chmod(0o640)
        else:
            target.symlink_to(outside)
        original = target.lstat()
    result = run_qa(base, mask, "race-" + kind if race else "", index)
    assert result["code"] != 0, result
    assert result["fired"] == race
    assert entries(base, qa) == {qa.TARGET_FILES[index]}
    if kind == "file":
        assert target.read_bytes() == EVIDENCE
        assert not target.is_symlink()
    else:
        assert target.is_symlink()
        assert target.readlink() == outside
    if not race:
        current = target.lstat()
        assert (current.st_ino, current.st_mode, current.st_size, current.st_mtime_ns) == (
            original.st_ino, original.st_mode, original.st_size, original.st_mtime_ns)
    if outside_info:
        assert outside.read_bytes() == EVIDENCE
        current = outside.lstat()
        assert (current.st_ino, current.st_mode, current.st_mtime_ns) == (
            outside_info.st_ino, outside_info.st_mode, outside_info.st_mtime_ns)
    else:
        assert not outside.exists()


@pytest.mark.parametrize("mask", MASKS, ids=["umask000", "umask022"])
@pytest.mark.parametrize("fault", ["open-failure", "partial-write", "zero-write"])
def test_partial_failure_rolls_back_and_can_retry(tree, qa, mask, fault):
    base = tree / "project"
    result = run_qa(base, mask, fault)
    assert result["code"] != 0 and result["fired"], result
    assert result["partial"] == (fault != "open-failure")
    assert entries(base, qa) == set()
    assert run_qa(base, mask)["code"] == 0
    expected = render_expected(tree / "expected", qa)
    for name, content in expected.items():
        assert (base / name).read_bytes() == content
        assert stat.S_IMODE((base / name).stat().st_mode) == 0o600


@pytest.mark.parametrize("mask", MASKS, ids=["umask000", "umask022"])
@pytest.mark.parametrize("fault", ["edit", "same-stat-edit", "replace", "symlink"])
def test_rollback_preserves_external_changes(tree, qa, mask, fault):
    base = tree / "project"
    base.mkdir()
    outside = base / "outside-evidence"
    outside.write_bytes(EVIDENCE)
    outside.chmod(0o640)
    original = outside.stat()
    result = run_qa(base, mask, fault)
    assert result["code"] != 0 and result["fired"], result
    assert entries(base, qa) == {qa.TARGET_FILES[0]}
    preserved = base / qa.TARGET_FILES[0]
    if fault == "symlink":
        assert preserved.is_symlink()
        assert preserved.readlink() == outside
    else:
        assert preserved.read_bytes() == bytes.fromhex(result["preserved"])
    assert run_qa(base, mask)["code"] != 0
    assert entries(base, qa) == {qa.TARGET_FILES[0]}
    assert outside.read_bytes() == EVIDENCE
    current = outside.stat()
    assert (current.st_ino, current.st_mode, current.st_mtime_ns) == (
        original.st_ino, original.st_mode, original.st_mtime_ns)
