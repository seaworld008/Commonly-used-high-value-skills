"""Run the real Node CLI against checkout, npm-pack contents and nested resources."""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
BLOB = "https://github.com/seaworld008/Commonly-used-high-value-skills/blob/main/"
MANIFEST = ".high-value-skills-manifest.json"
pytestmark = pytest.mark.skipif(NODE is None, reason="Node is required")


def write(root, relative, text):
    file = root / relative
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8", newline="")
    return file


def run(repo, dest, target="custom", *options):
    result = subprocess.run(
        [NODE, str(repo / "bin/install-skills.js"), "install", "--target", target,
         "--dir", str(dest), *options],
        cwd=repo, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def snapshot(root):
    return {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def assert_inventory(dest):
    manifest = json.loads((dest / MANIFEST).read_text())
    for name, entry in manifest["skills"].items():
        assert entry["owner"] == name
        assert {f["path"] for f in entry["files"]} == {
            p.relative_to(dest / name).as_posix() for p in (dest / name).rglob("*") if p.is_file()
        }
        tree = hashlib.sha256()
        for file in entry["files"]:
            installed = dest / name / file["path"]
            assert file["sha256"] == hashlib.sha256(installed.read_bytes()).hexdigest()
            assert file["mode"] == f"{installed.stat().st_mode & 0o777:03o}"
            assert file["owner"] == name
            tree.update(f'{file["path"]}\0{file["sha256"]}\0{file["mode"]}\n'.encode())
        assert tree.hexdigest() == entry["source_digest"]


@pytest.fixture(scope="module")
def npm_package(tmp_path_factory):
    """Rebuild exactly npm's file inventory, rather than pretending exports are bundled."""
    if shutil.which("npm") is None:
        pytest.skip("npm is required to inspect the package inventory")
    temporary = tmp_path_factory.mktemp("npm-resource-package")
    empty_config = write(temporary, "empty.npmrc", "")
    global_config = write(temporary, "global.npmrc", "")
    env = {**os.environ, "npm_config_cache": str(temporary / "npm-cache"),
           "npm_config_userconfig": str(empty_config), "npm_config_globalconfig": str(global_config),
           "npm_config_update_notifier": "false"}
    packed = subprocess.run(["npm", "pack", "--dry-run", "--json", "--ignore-scripts"],
                            cwd=ROOT, env=env, capture_output=True, text=True)
    assert packed.returncode == 0, packed.stderr
    inventory = json.loads(packed.stdout)[0]["files"]
    paths = {file["path"] for file in inventory}
    assert not any(p.startswith("openclaw-skills/") for p in paths)
    assert "skills/product-design/landing-page-generator/SKILL.md" in paths
    assert "skills/growth-operations-xiaohongshu/compete/SKILL.md" in paths
    assert not any(".data" in Path(p).parts for p in paths)
    repo = temporary / "package"
    for relative in sorted(paths):
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    return repo


@pytest.mark.parametrize("target", ["openclaw", "codex", "claude", "cursor", "custom"])
def test_npm_fallback_and_canonical_installs_relocate_real_compete_link(npm_package, tmp_path, target):
    dest = tmp_path / "installed"
    source = npm_package / "skills/product-design/landing-page-generator/SKILL.md"
    before = source.read_bytes()
    run(npm_package, dest, target, "--skill", "landing-page-generator,compete")
    text = (dest / "landing-page-generator/SKILL.md").read_text()
    assert "[Compete](../compete/SKILL.md)" in text
    assert (dest / "landing-page-generator" / "../compete/SKILL.md").resolve().is_file()
    assert {p.name for p in dest.iterdir() if p.is_dir()} == {"landing-page-generator", "compete"}
    # Canonical frontmatter is copied, not subjected to OpenClaw normalization.
    assert text.split("---", 2)[1] == source.read_text().split("---", 2)[1]
    assert source.read_bytes() == before
    assert_inventory(dest)
    installed = snapshot(tmp_path)
    for _ in range(2):
        dry = run(npm_package, dest, target, "--skill", "landing-page-generator,compete", "--dry-run")
        assert "Added: 0, Updated: 0, Unchanged: 2" in dry
        assert snapshot(tmp_path) == installed


def test_checkout_openclaw_uses_repaired_export_without_second_transform(tmp_path):
    dest = tmp_path / "installed"
    run(ROOT, dest, "openclaw", "--skill", "landing-page-generator,compete")
    entry = dest / "landing-page-generator/SKILL.md"
    assert "[Compete](../compete/SKILL.md)" in entry.read_text()
    assert (entry.parent / "../compete/SKILL.md").resolve().is_file()
    for name in ("landing-page-generator", "compete"):
        for installed in (dest / name).rglob("*"):
            if installed.is_file():
                assert installed.read_bytes() == (ROOT / "openclaw-skills" / name /
                                                   installed.relative_to(dest / name)).read_bytes()
    assert_inventory(dest)


@pytest.fixture
def resource_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "bin").mkdir(parents=True)
    for name in ("install-skills.js", "npm-command.js"):
        shutil.copy2(ROOT / "bin" / name, repo / "bin" / name)
    write(repo, "package.json", '{"name":"resource-fixture","version":"1.0.0"}')
    write(repo, "skills/design/landing/SKILL.md", '''---
name: landing
description: Keep canonical metadata.
allowed-tools: Read, Write
---
中文前缀 [Compete](../../growth/compete/SKILL.md?q=a%20b#research "On demand")
[Own](<references/my guide.md#own> 'Own title')
[Encoded own](./references/my%20guide.md?x=1#own)
[Anchor](#local) [Query](?mode=read#local)
[Repository](../../../docs/sources/provenance.json#lock "Source")
[Unbundled docs](../../../docs/not-shipped.md?view=raw#part)
[Unknown](../../../absent.md)
[Outside](../../../../outside.md)
[Web](https://example.com/a?q=b#part "Web")
[Protocol relative](//example.com/a) [Mail](mailto:team@example.com)
[Template]({{project}}/notes.md)
![Image](../../growth/compete/assets/chart%20one.svg?raw=1#view (Chart title))
`[inline](../../growth/compete/SKILL.md)`
`` [inline with ` tick](../../growth/compete/SKILL.md) ``
````markdown
[example](../../growth/compete/SKILL.md)
```
[still example](../../growth/compete/SKILL.md)
````
~~~markdown
[tilde](../../growth/compete/SKILL.md)
~~~
''')
    write(repo, "skills/design/landing/references/my guide.md", '''# Own
[Resource](../../../growth/compete/references/a%20b(1).md#detail "Data")
[Angle](<../../../growth/compete/references/a b(1).md?mode=read#detail> 'Angle title')
[Escaped](../../../growth/compete/references/a%20b\\(1\\).md)
[Alias][other]
[other]: <../../../growth/compete/SKILL.md#research> 'Reference title'
''')
    write(repo, "skills/design/landing/references/deeper/nested.MARKDOWN",
          '[Deep](../../../../growth/compete/SKILL.md#research)\r\n')
    write(repo, "skills/growth/compete/SKILL.md", '# Research\n[Own](references/a%20b(1).md)\n')
    write(repo, "skills/growth/compete/references/a b(1).md", '# Detail\n[Cycle](../SKILL.md)\n')
    write(repo, "skills/growth/compete/assets/chart one.svg", '<svg/>')
    # Also discover a skill in an unrelated category that is never selected.
    write(repo, "skills/unrelated/optional/SKILL.md", '# Optional\n')
    write(repo, "skills/design/landing/references/optional.md",
          '[Dependency](../../../unrelated/optional/SKILL.md)\n')
    write(repo, "docs/sources/provenance.json", '{}')
    binary = repo / "skills/design/landing/raw.bin"
    binary.write_bytes(b"\xff\x00[example](../../growth/compete/SKILL.md)")
    script = write(repo, "skills/design/landing/scripts/helper.sh", "#!/bin/sh\nexit 0\n")
    script.chmod(0o755)
    return repo


def test_nested_resources_syntax_inventory_dry_run_and_backup(resource_repo, tmp_path):
    repo = resource_repo
    dest = tmp_path / "installed"
    original = snapshot(repo)
    selected = ("--skill", "landing,compete")
    dry = run(repo, dest, "custom", *selected, "--dry-run")
    assert "Added: 2" in dry and not dest.exists()
    run(repo, dest, "custom", *selected)
    entry = dest / "landing/SKILL.md"
    text = entry.read_text()
    assert '[Compete](../compete/SKILL.md?q=a%20b#research "On demand")' in text
    for unchanged in ("[Own](<references/my guide.md#own> 'Own title')",
                      "[Encoded own](./references/my%20guide.md?x=1#own)",
                      '[Anchor](#local) [Query](?mode=read#local)',
                      '[Web](https://example.com/a?q=b#part "Web")',
                      '[Protocol relative](//example.com/a) [Mail](mailto:team@example.com)',
                      '[Unknown](../../../absent.md)', '[Outside](../../../../outside.md)',
                      '[Template]({{project}}/notes.md)'):
        assert unchanged in text
    source_text = (repo / "skills/design/landing/SKILL.md").read_text()
    assert text[text.index('`[inline]'):] == source_text[source_text.index('`[inline]'):]
    assert f'{BLOB}docs/sources/provenance.json#lock "Source"' in text
    assert f'{BLOB}docs/not-shipped.md?view=raw#part' in text
    assert '![Image](../compete/assets/chart%20one.svg?raw=1#view (Chart title))' in text
    assert (dest / "landing" / "../compete/assets/chart one.svg").resolve().is_file()
    nested = (dest / "landing/references/my guide.md").read_text()
    assert '(../../compete/references/a%20b(1).md#detail "Data")' in nested
    assert "(<../../compete/references/a%20b(1).md?mode=read#detail> 'Angle title')" in nested
    assert '[Escaped](../../compete/references/a%20b(1).md)' in nested
    assert "[other]: <../../compete/SKILL.md#research> 'Reference title'" in nested
    target = urlsplit('../../compete/references/a%20b(1).md#detail')
    assert ((dest / "landing/references") / unquote(target.path)).resolve().is_file()
    assert (dest / "landing/references/deeper/nested.MARKDOWN").read_bytes() == (
        b'[Deep](../../../compete/SKILL.md#research)\r\n')
    assert '[Dependency](../../optional/SKILL.md)' in (dest / "landing/references/optional.md").read_text()
    assert not (dest / "optional").exists()
    assert (dest / "landing/raw.bin").read_bytes() == (repo / "skills/design/landing/raw.bin").read_bytes()
    assert snapshot(repo) == original
    assert_inventory(dest)
    before_dry = snapshot(tmp_path)
    for _ in range(2):
        assert "Added: 0, Updated: 0, Unchanged: 2" in run(repo, dest, "custom", *selected, "--dry-run")
        assert snapshot(tmp_path) == before_dry
    user_bytes = entry.read_bytes() + b"\nUser customization\n"
    entry.write_bytes(user_bytes)
    before_update = snapshot(tmp_path)
    dry = run(repo, dest, "custom", *selected, "--dry-run")
    assert "Updated: 1, Unchanged: 1" in dry and "Archived replacements: 1" in dry
    assert snapshot(tmp_path) == before_update
    output = run(repo, dest, "custom", *selected)
    assert "Archived replacements: 1" in output
    backups = list((tmp_path / ".high-value-skills-backups").rglob("landing/SKILL.md"))
    assert len(backups) == 1 and backups[0].read_bytes() == user_bytes
    assert entry.read_text() == text
    assert_inventory(dest)


def test_unselected_cross_category_skill_stays_an_explicit_dependency(resource_repo, tmp_path):
    dest = tmp_path / "installed"
    run(resource_repo, dest, "custom", "--category", "design", "--skill", "landing")
    assert "[Compete](../compete/SKILL.md?" in (dest / "landing/SKILL.md").read_text()
    assert not (dest / "compete").exists()
    assert set(json.loads((dest / MANIFEST).read_text())["skills"]) == {"landing"}
    assert_inventory(dest)


def test_transformed_staging_still_rejects_unexpected_bytes(resource_repo, tmp_path):
    dest = tmp_path / "installed"
    selected = ("--skill", "landing,compete")
    run(resource_repo, dest, "custom", *selected)
    previous = snapshot(dest)
    source = resource_repo / "skills/design/landing/SKILL.md"
    source.write_bytes(source.read_bytes() + b"\nSource update\n")
    hook = write(tmp_path, "tamper.cjs", '''const fs = require("fs");
const path = require("path");
const copy = fs.cpSync;
fs.cpSync = (source, dest, options) => {
  copy(source, dest, options);
  fs.appendFileSync(path.join(dest, "SKILL.md"), "\\nUnexpected staged bytes\\n");
};
''')
    result = subprocess.run(
        [NODE, "--require", str(hook), str(resource_repo / "bin/install-skills.js"),
         "install", "--target", "custom", "--dir", str(dest), *selected],
        cwd=resource_repo, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "Staged skill failed inventory verification" in result.stderr
    assert snapshot(dest) == previous
    assert not list(dest.glob(".high-value-skills-stage-*"))
    assert not (tmp_path / ".high-value-skills-backups").exists()
