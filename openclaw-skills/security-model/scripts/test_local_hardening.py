# Apache-2.0; adapted Sentry test path for this repository. See the security-model license and source inventory.
"""Local boundary regressions; fixtures never execute policy contents."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("resolve_security_model.py")
spec = importlib.util.spec_from_file_location("local_security_model", SCRIPT)
assert spec and spec.loader
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)


def run(repo: Path, command: str = "check", *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), command, "--repo", str(repo), *args],
        capture_output=True, text=True, timeout=10,
    )


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
    ).stdout.strip()


def commit(repo: Path) -> None:
    git(repo, "add", "-A")
    git(repo, "-c", "user.email=test@example.invalid", "-c", "user.name=Local Test",
        "commit", "-qm", "fixture")


@pytest.fixture
def plain_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "SECURITY_MODEL.md").write_text("# Trusted policy\n", encoding="utf-8")
    (repo / "normal.py").write_text("def internal_symbol(): pass\n", encoding="utf-8")
    return repo


@pytest.fixture
def git_repo(plain_repo: Path) -> Path:
    git(plain_repo, "init", "-q", "-b", "main")
    commit(plain_repo)
    return plain_repo


@pytest.mark.parametrize("command", ["list", "resolve", "check"])
@pytest.mark.parametrize("ref", ["", " ", "\t\n"])
def test_explicit_empty_ref_fails(git_repo: Path, command: str, ref: str) -> None:
    args = ["--ref", ref]
    if command == "resolve":
        args += ["--scope", "."]
    out = run(git_repo, command, *args)
    assert out.returncode == 2
    assert "--ref" in out.stderr and "empty or whitespace" in out.stderr
    assert not out.stdout


def test_empty_ref_outside_git_does_not_fall_back(plain_repo: Path) -> None:
    assert run(plain_repo, "list", "--ref", "").returncode == 2


@pytest.mark.parametrize("ref", ["--all", "--help", "--output=untrusted"])
def test_ref_cannot_be_git_option(git_repo: Path, ref: str) -> None:
    out = run(git_repo, "list", f"--ref={ref}")
    assert out.returncode == 2 and not out.stdout


def test_ref_is_pinned_to_commit_oid(git_repo: Path) -> None:
    oid = git(git_repo, "rev-parse", "HEAD")
    source = resolver.Source(git_repo, "SECURITY_MODEL.md", "main")
    assert source.ref == oid
    (git_repo / "SECURITY_MODEL.md").write_text("# Changed policy\n")
    (git_repo / "new.py").write_text("pass\n")
    commit(git_repo)
    assert source.read("SECURITY_MODEL.md") == "# Trusted policy\n"
    assert "new.py" not in source.files()
    assert "Trusted policy" in source.resolve(".", False)


@pytest.mark.parametrize("use_git", [False, True])
def test_external_sentinel_never_matches(plain_repo: Path, tmp_path: Path, use_git: bool) -> None:
    sentinel = tmp_path / "sentinel.py"
    sentinel.write_text("external_sentinel\n/external/sentinel\n")
    (plain_repo / "leak.py").symlink_to(sentinel)
    (plain_repo / "outside").symlink_to(tmp_path, target_is_directory=True)
    (plain_repo / "SECURITY_MODEL.md").write_text(
        "`external_sentinel`, `/external/sentinel`, `leak.py`, `outside/sentinel.py`, "
        "`*.py`, `internal_symbol`, `normal.py`\n"
    )
    if use_git:
        git(plain_repo, "init", "-q", "-b", "main")
        commit(plain_repo)
    out = run(plain_repo)
    assert out.returncode == 1, out.stderr
    assert {line.split("`")[1] for line in out.stdout.splitlines()} == {
        "external_sentinel", "/external/sentinel", "leak.py", "outside/sentinel.py",
    }
    # No normal local source can satisfy a symbol if the only other file is external.
    (plain_repo / "normal.py").unlink()
    (plain_repo / "SECURITY_MODEL.md").write_text("`external_sentinel` and `*.py`\n")
    out = run(plain_repo)
    assert out.returncode == 1
    assert {line.split("`")[1] for line in out.stdout.splitlines()} == {"external_sentinel", "*.py"}


def test_external_file_is_not_opened(plain_repo: Path, tmp_path: Path, monkeypatch) -> None:
    sentinel = tmp_path / "sentinel.py"
    sentinel.write_text("external_sentinel\n")
    (plain_repo / "leak.py").symlink_to(sentinel)
    (plain_repo / "SECURITY_MODEL.md").write_text("`external_sentinel`\n")
    real_open = os.open

    def guarded_open(path, *args, **kwargs):
        assert Path(path).resolve() != sentinel
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(resolver.os, "open", guarded_open)
    source = resolver.Source(plain_repo, "SECURITY_MODEL.md", None)
    assert len(source.check(None)) == 1


def test_deleted_tracked_file_fails_worktree_but_exists_in_history(git_repo: Path) -> None:
    (git_repo / "SECURITY_MODEL.md").write_text("`normal.py` and `internal_symbol`\n")
    commit(git_repo)
    (git_repo / "normal.py").unlink()
    out = run(git_repo)
    assert out.returncode == 1
    assert {line.split("`")[1] for line in out.stdout.splitlines()} == {"normal.py", "internal_symbol"}
    historical = run(git_repo, "check", "--ref", "main")
    assert historical.returncode == 0, historical.stderr
    assert not historical.stdout
    (git_repo / "SECURITY_MODEL.md").unlink()
    assert json.loads(run(git_repo, "list").stdout) == []
    assert "normal.py" in run(git_repo, "resolve", "--scope", ".", "--ref", "main").stdout


@pytest.mark.parametrize("target", ["outside.md", "normal.py"])
def test_historical_policy_symlink_is_warned_and_never_read(git_repo: Path, target: str, monkeypatch, capsys) -> None:
    policy = git_repo / "SECURITY_MODEL.md"
    policy.unlink()
    policy.symlink_to(target)
    commit(git_repo)
    real_git = resolver.run_git
    reads = []

    def spy(repo, *args, **kwargs):
        if args[:2] == ("cat-file", "blob"):
            reads.append(args)
        return real_git(repo, *args, **kwargs)

    monkeypatch.setattr(resolver, "run_git", spy)
    source = resolver.Source(git_repo, "SECURITY_MODEL.md", "main")
    assert source.read("SECURITY_MODEL.md") is None
    assert source.list() == []
    assert "SECURITY_MODEL.md" not in source.files()
    assert not reads
    assert "historical symlink; ignored" in capsys.readouterr().err
    for command in ("list", "resolve", "check"):
        args = ["--ref", "main"] + (["--scope", "."] if command == "resolve" else [])
        out = run(git_repo, command, *args)
        assert out.returncode == 0, out.stderr
        assert "historical symlink; ignored" in out.stderr


def test_historical_symlink_blob_is_not_symbol_or_path(git_repo: Path) -> None:
    (git_repo / "leak.py").symlink_to("external_sentinel")
    (git_repo / "SECURITY_MODEL.md").write_text("`external_sentinel` and `leak.py`\n")
    commit(git_repo)
    out = run(git_repo, "check", "--ref", "main")
    assert out.returncode == 1
    assert {line.split("`")[1] for line in out.stdout.splitlines()} == {"external_sentinel", "leak.py"}


def test_historical_oversize_rejected_before_blob_read(git_repo: Path, monkeypatch) -> None:
    (git_repo / "SECURITY_MODEL.md").write_bytes(b"x" * (8 * resolver.MAX_BYTES))
    commit(git_repo)
    real_git = resolver.run_git
    calls = []

    def guard(repo, *args, **kwargs):
        calls.append(args)
        assert args[:2] != ("cat-file", "blob"), "oversize content must never be requested"
        return real_git(repo, *args, **kwargs)

    monkeypatch.setattr(resolver, "run_git", guard)
    source = resolver.Source(git_repo, "SECURITY_MODEL.md", "main")
    with pytest.raises(resolver.PolicyError, match="exceeds 1 MiB"):
        source.read("SECURITY_MODEL.md")
    assert any(args[:2] == ("cat-file", "-s") for args in calls)
    out = run(git_repo, "resolve", "--scope", ".", "--ref", "main")
    assert out.returncode == 2 and "exceeds 1 MiB" in out.stderr


@pytest.mark.parametrize("use_git", [False, True])
def test_special_files_do_not_block_or_count_as_paths(plain_repo: Path, use_git: bool) -> None:
    fifo = plain_repo / "pipe.py"
    policy_dir = plain_repo / "fifo_policy"
    policy_dir.mkdir()
    os.mkfifo(fifo)
    os.mkfifo(policy_dir / "SECURITY_MODEL.md")
    # A symlink to an existing device must also be rejected without reading it.
    (plain_repo / "device.py").symlink_to("/dev/zero")
    (plain_repo / "SECURITY_MODEL.md").write_text("`pipe.py`, `device.py`, `absent_symbol`, `internal_symbol`\n")
    if use_git:
        git(plain_repo, "init", "-q", "-b", "main")
        git(plain_repo, "add", "SECURITY_MODEL.md", "normal.py", "device.py")
        git(plain_repo, "-c", "user.email=test@example.invalid", "-c", "user.name=Local Test",
            "commit", "-qm", "fixture")
    out = run(plain_repo)
    assert out.returncode == 1, out.stderr
    assert {line.split("`")[1] for line in out.stdout.splitlines()} == {"pipe.py", "device.py", "absent_symbol"}
    assert json.loads(run(plain_repo, "list").stdout) == ["SECURITY_MODEL.md"]
    out = run(plain_repo, "resolve", "--scope", "fifo_policy")
    assert out.returncode == 0, out.stderr


def test_warning_budget_reports_remaining_and_total(plain_repo: Path) -> None:
    total = resolver.MAX_BYTES // 2  # 1 MiB of Cc characters
    (plain_repo / "SECURITY_MODEL.md").write_bytes(b"\xc2\x80" * total)
    out = run(plain_repo, "resolve", "--scope", ".")
    assert out.returncode == 0, out.stderr
    assert out.stderr.count("hidden character at") == resolver.MAX_HIDDEN_DETAILS
    assert f"{total - resolver.MAX_HIDDEN_DETAILS} additional hidden characters omitted ({total} total)" in out.stderr
    assert len(out.stderr.splitlines()) == resolver.MAX_HIDDEN_DETAILS + 2  # large-file warning + summary


def test_combining_characters_and_emoji_are_not_flagged(plain_repo: Path) -> None:
    ordinary = "Cafe\u0301 👩🏽\u200d💻 ❤️ 🇨🇳 🏴\U000e0067\U000e0062\U000e007f\n"
    (plain_repo / "SECURITY_MODEL.md").write_text(ordinary, encoding="utf-8")
    out = run(plain_repo, "resolve", "--scope", ".", "--show-hidden")
    assert out.returncode == 0
    assert not out.stderr
    assert ordinary in out.stdout


def test_literal_git_pathspec_keeps_normal_source_match(git_repo: Path) -> None:
    special = git_repo / "[source].py"
    special.write_text("literal_pathspec_symbol\n")
    (git_repo / "SECURITY_MODEL.md").write_text("`literal_pathspec_symbol`\n")
    assert run(git_repo).returncode == 0
    commit(git_repo)
    assert run(git_repo, "check", "--ref", "main").returncode == 0


def test_missing_optional_open_flags_still_read_regular_file(plain_repo, monkeypatch):
    class PortableOS:
        def __getattr__(self, name):
            if name in {'O_NOFOLLOW', 'O_NONBLOCK'}:
                raise AttributeError(name)
            return getattr(os, name)
    monkeypatch.setattr(resolver, 'os', PortableOS())
    source = resolver.Source(plain_repo, 'SECURITY_MODEL.md', None)
    assert source.read('SECURITY_MODEL.md') == '# Trusted policy\n'


def test_cli_name_must_be_portable_bare_filename(plain_repo):
    result = run(plain_repo, 'check', '--name', r'..\outside.md')
    assert result.returncode == 2


@pytest.mark.parametrize("reference,target", [("../auth.py", "auth.py"), ("./handler.py", "api/handler.py")])
def test_historical_relative_reference_is_normalized(git_repo, reference, target):
    (git_repo / "api").mkdir()
    (git_repo / target).write_text("pass\n")
    (git_repo / "api/SECURITY_MODEL.md").write_text(f"`{reference}`\n")
    commit(git_repo)
    assert run(git_repo).returncode == 0
    result = run(git_repo, "check", "--ref", "main")
    assert result.returncode == 0, result.stdout + result.stderr


def test_historical_relative_reference_cannot_escape_root(git_repo):
    (git_repo / "api").mkdir()
    (git_repo / "outside.py").write_text("pass\n")
    (git_repo / "api/SECURITY_MODEL.md").write_text("`../../outside.py`\n")
    commit(git_repo)
    result = run(git_repo, "check", "--ref", "main")
    assert result.returncode == 1
    assert "../../outside.py" in result.stdout


def test_normalized_reference_never_falls_back_to_head(git_repo):
    (git_repo / "api").mkdir()
    (git_repo / "api/SECURITY_MODEL.md").write_text("`./head_only.py`\n")
    commit(git_repo)
    base = git(git_repo, "rev-parse", "HEAD")
    (git_repo / "api/head_only.py").write_text("pass\n")
    assert run(git_repo).returncode == 0
    result = run(git_repo, "check", "--ref", base)
    assert result.returncode == 1
    assert "./head_only.py" in result.stdout


def test_history_keeps_trailing_whitespace_in_repo_path(tmp_path):
    repo = tmp_path / "repo "
    repo.mkdir()
    (repo / "SECURITY_MODEL.md").write_text("# Trusted whitespace repository\n")
    git(repo, "init", "-q", "-b", "main")
    commit(repo)
    result = run(repo, "resolve", "--scope", ".", "--ref", "main")
    assert result.returncode == 0, result.stderr
    assert "Trusted whitespace repository" in result.stdout


def test_history_keeps_leading_whitespace_in_component_prefix(git_repo):
    component = git_repo / " api"
    component.mkdir()
    (component / "SECURITY_MODEL.md").write_text("# Trusted whitespace component\n")
    (component / "handler.py").write_text("pass\n")
    commit(git_repo)
    result = run(component, "resolve", "--scope", "handler.py", "--ref", "main")
    assert result.returncode == 0, result.stderr
    assert "Trusted whitespace component" in result.stdout
