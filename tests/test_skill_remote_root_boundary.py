"""Exercise remote selection through the CLI with a fixture checkout."""

import contextlib
import io
import json
import runpy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


SCRIPT = (Path(__file__).resolve().parents[1] / "skills/security-and-reliability"
          / "skill-security-auditor/scripts/skill_security_auditor.py")


def make_skill(path):
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text("# Example\n", encoding="utf-8")
    return path


@pytest.fixture
def checkout(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))

    def fake_clone(cmd, **kwargs):
        assert cmd[:4] == ["git", "clone", "--depth", "1"]
        shutil.copytree(source, cmd[-1], symlinks=True, dirs_exist_ok=True)

    monkeypatch.setattr(subprocess, "run", fake_clone)

    def audit(name):
        monkeypatch.setattr(sys, "argv", [str(SCRIPT), "https://fixture.invalid/repo",
                                          "--skill", name, "--json"])
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with pytest.raises(SystemExit) as result:
                runpy.run_path(str(SCRIPT), run_name="__main__")
        assert not list(tmp_path.glob("skill-audit-*"))
        return result.value.code, out.getvalue(), err.getvalue()

    return source, audit


@pytest.mark.parametrize("name", ["target", "skills/group/target"])
def test_selects_actual_skill_and_preserves_findings(checkout, name):
    source, audit = checkout
    skill = make_skill(source / "skills/group/target")
    (skill / "run.sh").write_text("pip install example # auditor:ignore-line\n", encoding="utf-8")
    (source / "unrelated.py").write_text("print(42)\n", encoding="utf-8")
    code, out, _ = audit(name)
    assert code == 2
    assert len(out.splitlines()) == 1
    report = json.loads(out)
    assert report["skill_name"] == "target"
    assert report["stats"]["scripts_scanned"] == 1
    assert any(f["category"] == "DEPS-RUNTIME" for f in report["findings"])


@pytest.mark.parametrize("name", ["../source", "nested/../target", "absolute", "*"])
def test_rejects_nonliteral_or_unconfined_selection(checkout, name):
    source, audit = checkout
    make_skill(source)
    make_skill(source / "target")
    (source / "nested").mkdir()
    code, out, err = audit(str(source) if name == "absolute" else name)
    assert code == 1 and not out and "Invalid remote skill" in err


@pytest.mark.parametrize("kind", ["root-link", "ancestor-link", "manifest-link",
                                  "directory-manifest", "absent-manifest", "file-root"])
def test_rejects_invalid_root_or_manifest(checkout, kind):
    source, audit = checkout
    outside = make_skill(source.parent / "external" / "target")
    target = source / "target"
    name = "target"
    if kind == "root-link":
        target.symlink_to(outside, target_is_directory=True)
    elif kind == "ancestor-link":
        (source / "nested").symlink_to(outside.parent, target_is_directory=True)
        name = "nested/target"
    elif kind == "file-root":
        target.touch()
    else:
        target.mkdir()
        if kind == "manifest-link":
            (target / "SKILL.md").symlink_to(outside / "SKILL.md")
        elif kind == "directory-manifest":
            (target / "SKILL.md").mkdir()
    code, out, err = audit(name)
    assert code == 1 and not out and "Invalid remote skill" in err


def test_duplicate_including_top_level_requires_qualified_path(checkout):
    source, audit = checkout
    make_skill(source / "target")
    make_skill(source / "group/target")
    code, out, err = audit("target")
    assert code == 1 and not out and "ambiguous" in err
    code, out, _ = audit("group/target")
    assert code == 0 and json.loads(out)["skill_name"] == "target"
    code, out, _ = audit("./target")
    assert code == 0 and json.loads(out)["skill_name"] == "target"
