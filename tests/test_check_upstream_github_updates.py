from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_upstream_github_updates.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_upstream_github_updates", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CheckUpstreamGitHubUpdatesTests(unittest.TestCase):
    def test_equal_adapted_body_is_not_reported_when_commit_sha_differs(self):
        module = load_module()
        skill = {
            "name": "demo",
            "repo": "owner/repo",
            "ref": "main",
            "sync_mode": "replace",
            "upstream_path": "skills/demo/SKILL.md",
            "last_synced_commit": "repository-head-checkpoint",
        }

        original_check = module.check_upstream_changes
        original_latest = module.github_latest_path_commit
        module.check_upstream_changes = lambda _skill, _token: {
            "changes": "none",
            "upstream_path": "skills/demo/SKILL.md",
        }
        module.github_latest_path_commit = lambda *_args: (
            "different-path-commit",
            "2026-08-18T00:00:00Z",
            None,
        )
        try:
            result = module.online_result(skill, token="token")
        finally:
            module.check_upstream_changes = original_check
            module.github_latest_path_commit = original_latest

        self.assertFalse(result["needs_update"])
        self.assertEqual("none", result["change_type"])
        self.assertEqual("different-path-commit", result["latest_commit"])

    def test_monitor_rollback_is_not_reported_as_update(self):
        module = load_module()
        skill = {
            "name": "curated",
            "repo": "owner/repo",
            "ref": "main",
            "sync_mode": "monitor",
            "last_synced_commit": "reviewed-checkpoint",
        }

        original_check = module.check_upstream_changes
        module.check_upstream_changes = lambda _skill, _token: {
            "changes": "upstream_rollback",
            "current_commit": "older-head",
        }
        try:
            result = module.online_result(skill, token="token")
        finally:
            module.check_upstream_changes = original_check

        self.assertFalse(result["needs_update"])
        self.assertEqual("upstream_rollback", result["change_type"])
        self.assertEqual("older-head", result["latest_commit"])

    def test_main_accepts_absolute_output_path(self):
        module = load_module()
        original_load = module.load_skills_with_upstream
        original_argv = sys.argv
        module.load_skills_with_upstream = lambda: []
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                output = Path(tmpdir) / "upstream.json"
                sys.argv = [
                    "check_upstream_github_updates.py",
                    "--write-json",
                    str(output),
                ]
                self.assertEqual(0, module.main())
                self.assertEqual(0, json.loads(output.read_text())["total_checked"])
        finally:
            module.load_skills_with_upstream = original_load
            sys.argv = original_argv


if __name__ == "__main__":
    unittest.main()
