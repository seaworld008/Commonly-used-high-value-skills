from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest import mock
from urllib.parse import urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("browser_foundations_test", ROOT / "scripts/check_browser_foundations.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    tree = {"sha": "a" * 40, "tree": [
        {"type": "blob", "path": "skill-data/core/SKILL.md", "sha": "b" * 40, "mode": "100644"},
        {"type": "blob", "path": "README.md", "sha": "c" * 40, "mode": "100644"},
    ]}
    target = {"id": "browser", "repo": "owner/browser", "paths": ["skill-data/core"],
              "reviewed_tree_digest": module.tree_digest(tree, ["skill-data/core"]),
              "package": "agent-browser", "reviewed_version": "0.43.0", "reviewed_release": "v0.43.0"}

    def fetch(url, token):
        if "git/trees" in url:
            return tree
        if urlsplit(url).hostname == "registry.npmjs.org":
            assert token is None
            return {"version": "0.43.0"}
        return {"tag_name": "v0.43.0"}
    return tree, target, fetch


def test_new_release_is_detected_even_when_pinned_skill_content_is_unchanged():
    tree, target, fetch = fixture()
    def newer(url, token):
        if "releases/latest" in url:
            return {"tag_name": "v0.44.0"}
        return fetch(url, token)
    row = module.check_target(target, "secret", newer)
    assert row["state"] == "review_required"
    assert "v0.44.0" in row["reasons"][0]


def test_tree_hash_covers_added_removed_files_and_modes_but_not_unrelated_changes():
    tree, target, fetch = fixture()
    original = target["reviewed_tree_digest"]
    tree["tree"][1]["sha"] = "d" * 40
    assert module.tree_digest(tree, target["paths"]) == original
    tree["tree"][0]["mode"] = "100755"
    assert module.tree_digest(tree, target["paths"]) != original
    tree["tree"] = tree["tree"][1:]
    assert module.check_target(target, fetch=fetch)["state"] == "unavailable"


def test_failure_and_truncated_tree_never_claim_current_or_leak_endpoint_data():
    tree, target, fetch = fixture()
    tree["truncated"] = True
    assert module.check_target(target, fetch=fetch)["state"] == "unavailable"
    def failed(*args):
        raise OSError("access-bearing URL should not appear")
    payload = module.check_policy({"targets": [target]}, fetch=failed)
    assert payload["state"] == "failed"
    assert "access-bearing" not in json.dumps(payload)


def test_reports_require_all_targets_and_consistent_summary():
    _, target, fetch = fixture()
    policy = {"targets": [target]}
    payload = module.check_policy(policy, fetch=fetch)
    assert module.validate_report(payload, policy) == "complete"
    for invalid in [dict(payload, rows=[]), dict(payload, state="degraded"),
                    dict(payload, rows=payload["rows"] * 2),
                    dict(payload, generated_at="2020-01-01T00:00:00+00:00")]:
        with pytest.raises(ValueError):
            module.validate_report(invalid, policy)


def test_priority_sort_keeps_other_sources_in_their_existing_order():
    skills = [{"name": name} for name in ["other-b", "playwright", "other-a", "agent-browser"]]
    assert [s["name"] for s in module.prioritize(skills)] == ["agent-browser", "playwright", "other-b", "other-a"]


@pytest.mark.parametrize("status", [1, 2])
def test_bulk_apply_stops_before_any_sync_or_pipeline_when_foundations_need_work(tmp_path, status):
    spec = importlib.util.spec_from_file_location("bulk_browser_test", ROOT / "scripts/sync_all_upstream_skills.py")
    bulk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bulk)
    with mock.patch.object(bulk, "run", return_value=status) as run:
        assert bulk.main(["--apply", "--run-pipeline", "--repo-root", str(tmp_path)]) == status
    assert len(run.call_args_list) == 1


def test_foundation_failure_reaches_weekly_report_and_prevents_all_fresh_message(tmp_path):
    spec = importlib.util.spec_from_file_location("report_browser_test", ROOT / "scripts/generate_sync_report.py")
    report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(report)
    output = tmp_path / "report.md"
    # Missing foundation report must not be ignored even if ordinary checks are healthy.
    with mock.patch.object(report, "validate_discovery", return_value="complete"), \
         mock.patch.object(report, "validate_upstream", return_value="complete"), \
         mock.patch.object(report, "_read_json", side_effect=[({}, None), ({}, None), ({}, "missing foundation report")]):
        report.main(["--foundation", str(tmp_path / "missing.json"), "--output", str(output)])
    text = output.read_text(encoding="utf-8")
    assert "`failed`" in text
    assert "All skills are up to date" not in text
