"""Sync preflight preserves strict archived font sidecars without licensing code."""
import copy
import hashlib
import pytest
import tests.test_scoped_font_license as fixtures
from scripts import sync_upstream as sync


@pytest.fixture
def case(monkeypatch):
    item = fixtures.ScopedFontLicenseTests()
    item.setUp()
    monkeypatch.setattr(sync, "REPO_ROOT", item.root.resolve())
    item.code["tracking"]["content_sha256"] = hashlib.sha256((item.root / fixtures.SKILL / "SKILL.md").read_bytes()).hexdigest()
    item.font["sync_mode"] = "archived"
    item.font["tracking"].update(channel="fixed_ref", ref=fixtures.COMMIT)
    yield item
    item.doCleanups()


def test_archived_font_sidecar_passes_sync_preflight(case):
    errors = sync._v2_sync_entry_errors(case.entry)
    assert not errors, errors
    assert "OFL-1.1" not in sync.PERMISSIVE_LICENSES


@pytest.mark.parametrize("mutation", ["code", "directory", "notice", "checkpoint", "active", "symlink"])
def test_invalid_font_scope_never_licenses_a_sync_origin(case, mutation):
    if mutation == "code":
        case.put("fonts/execute.py", b"raise RuntimeError('never execute')\n")
        case.font["artifacts"].append({"source":"execute.py", "target": fixtures.SKILL + "/fonts/execute.py", "type":"file"})
        case.refresh_managed()
    if mutation == "directory": case.font["artifacts"][0]["type"] = "directory"
    if mutation == "notice": case.put("fonts/Fixture-OFL.txt", b"OFL-1.1 metadata alone is not a grant\n"); case.refresh_managed()
    if mutation == "checkpoint": case.font["tracking"]["license_checkpoint"]["resolved_commit"] = "b" * 40
    if mutation == "active": case.font["sync_mode"] = "monitor"; case.font["tracking"].update(channel="default_branch", ref="main")
    if mutation == "symlink":
        target = case.root / fixtures.SKILL / "fonts/Fixture.ttf"
        target.unlink(); target.symlink_to(case.root / fixtures.SKILL / "LICENSE.txt")
    errors = sync._v2_sync_entry_errors(case.entry)
    assert any("permitted external license" in message for message in errors), errors
