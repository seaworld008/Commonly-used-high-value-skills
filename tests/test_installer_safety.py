"""Exercise installer failures only in disposable directories, never client homes."""
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "bin/install-skills.js"


def fixture(tmp_path):
    source = tmp_path / "source/category/sample-skill"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text("# shipped\n", encoding="utf-8")
    dest = tmp_path / "installed"
    command = ["node", str(INSTALLER), "install", "--target", "custom",
               "--source-root", str(tmp_path / "source"), "--dir", str(dest)]
    return source, dest, command


def run(command, **kwargs):
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, **kwargs)


@pytest.mark.parametrize("owned", [False, True])
def test_replacement_archives_user_content(tmp_path, owned):
    source, dest, command = fixture(tmp_path)
    if owned:
        assert run(command).returncode == 0
    else:
        (dest / "sample-skill").mkdir(parents=True)
    current = dest / "sample-skill/SKILL.md"
    current.write_text("# user customization\n", encoding="utf-8")
    dry = run([*command, "--dry-run"])
    assert dry.returncode == 0, dry.stderr
    assert current.read_text() == "# user customization\n"
    assert not (tmp_path / ".high-value-skills-backups").exists()
    result = run(command)
    assert result.returncode == 0, result.stderr
    assert current.read_text() == "# shipped\n"
    backups = list((tmp_path / ".high-value-skills-backups").rglob("SKILL.md"))
    assert len(backups) == 1
    assert backups[0].read_text() == "# user customization\n"
    assert "Archived replacements: 1" in result.stdout


@pytest.mark.parametrize("alias", [False, True])
def test_overlapping_destination_is_rejected_before_write(tmp_path, alias):
    source, dest, command = fixture(tmp_path)
    target = source.parent
    if alias:
        target = tmp_path / "alias"
        try:
            target.symlink_to(source.parent, target_is_directory=True)
        except OSError:
            pytest.skip("directory symlinks unavailable")
    original = (source / "SKILL.md").read_bytes()
    command[-1] = str(target)
    result = run(command)
    assert result.returncode != 0
    assert "overlap" in result.stderr.lower()
    assert (source / "SKILL.md").read_bytes() == original
    assert not (source.parent / ".high-value-skills-manifest.json").exists()


def test_duplicate_skill_names_fail_before_creating_destination(tmp_path):
    source, dest, command = fixture(tmp_path)
    duplicate = tmp_path / "source/other/sample-skill"
    duplicate.mkdir(parents=True)
    (duplicate / "SKILL.md").write_text("# conflicting\n")
    result = run(command)
    assert result.returncode != 0
    assert "duplicate" in result.stderr.lower()
    assert not dest.exists()


def test_copy_failure_leaves_previous_install_and_manifest_intact(tmp_path):
    source, dest, command = fixture(tmp_path)
    assert run(command).returncode == 0
    manifest = dest / ".high-value-skills-manifest.json"
    before = manifest.read_bytes()
    (source / "SKILL.md").write_text("# upgrade\n")
    # Inject an OS copy failure, not a fake implementation of the installer.
    hook = tmp_path / "copy-failure.cjs"
    hook.write_text("require('fs').cpSync = () => { throw new Error('injected copy failure'); };\n")
    result = run(["node", "--require", str(hook), *command[1:]])
    assert result.returncode != 0
    assert "injected copy failure" in result.stderr
    assert (dest / "sample-skill/SKILL.md").read_text() == "# shipped\n"
    assert manifest.read_bytes() == before
    assert not list(dest.glob(".high-value-skills-stage-*"))


def test_final_rename_failure_restores_previous_tree(tmp_path):
    source, dest, command = fixture(tmp_path)
    assert run(command).returncode == 0
    before = (dest / ".high-value-skills-manifest.json").read_bytes()
    (source / "SKILL.md").write_text("# new release\n")
    hook = tmp_path / "rename-failure.cjs"
    hook.write_text("const fs = require('fs'); const old = fs.renameSync; fs.renameSync = (a,b) => { if (require('path').basename(a) === 'next') throw new Error('injected rename failure'); return old(a,b); };\n")
    result = run(["node", "--require", str(hook), *command[1:]])
    assert result.returncode != 0
    assert (dest / "sample-skill/SKILL.md").read_text() == "# shipped\n"
    assert (dest / ".high-value-skills-manifest.json").read_bytes() == before
    assert not list(dest.glob(".high-value-skills-stage-*"))


def test_bad_later_source_fails_preflight_without_partial_install(tmp_path):
    source, dest, command = fixture(tmp_path)
    bad = tmp_path / "source/category/z-bad-skill"
    bad.mkdir()
    (bad / "SKILL.md").write_text("# bad\n")
    try:
        (bad / "linked").symlink_to(source / "SKILL.md")
    except OSError:
        pytest.skip("symlinks unavailable")
    result = run(command)
    assert result.returncode != 0
    assert not dest.exists()


def test_source_category_alias_cannot_hide_destination_overlap(tmp_path):
    source, dest, command = fixture(tmp_path)
    real = tmp_path / "external-category"
    source.parent.rename(real)
    try:
        source.parent.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    command[-1] = str(real)
    result = run(command)
    assert result.returncode != 0
    assert "overlap" in result.stderr.lower()
    assert not (real / ".high-value-skills-manifest.json").exists()
