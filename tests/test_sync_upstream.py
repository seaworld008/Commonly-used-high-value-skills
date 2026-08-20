import importlib.util
import io
import json
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "sync_upstream.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sync_upstream", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SyncUpstreamTests(unittest.TestCase):
    @staticmethod
    def _mapping_fixture(path: Path) -> dict:
        path.write_text(
            json.dumps(
                {
                    "video": {"checked_at": "2026-01-01"},
                    "skills": [
                        {
                            "upstream": {
                                "last_checked_at": "2026-01-01",
                                "last_synced_at": "2026-01-01",
                            }
                        }
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return {
            "name": "demo-skill",
            "category": "ai-workflow",
            "source": "github:owner/repo",
            "repo": "owner/repo",
            "mapping_path": path,
            "mapping_entry_index": 0,
        }

    @staticmethod
    def _run_main_with_equal_result(module, argv: list[str], skill: dict) -> int:
        original_token = module.resolve_github_token
        original_load = module.load_skills_with_upstream
        original_check = module.check_upstream_changes
        module.resolve_github_token = lambda: None
        module.load_skills_with_upstream = lambda **_kwargs: [skill]
        module.check_upstream_changes = lambda checked_skill, _token: {
            "skill": checked_skill,
            "changes": "none",
        }
        try:
            with redirect_stdout(io.StringIO()):
                return module.main(argv)
        finally:
            module.resolve_github_token = original_token
            module.load_skills_with_upstream = original_load
            module.check_upstream_changes = original_check

    @staticmethod
    def _run_main(module, argv: list[str], skills: list[dict], checker):
        original_token = module.resolve_github_token
        original_load = module.load_skills_with_upstream
        original_check = module.check_upstream_changes
        module.resolve_github_token = lambda: None
        module.load_skills_with_upstream = lambda **_kwargs: skills
        module.check_upstream_changes = checker
        stdout = io.StringIO()
        try:
            with redirect_stdout(stdout):
                exit_code = module.main(argv)
        finally:
            module.resolve_github_token = original_token
            module.load_skills_with_upstream = original_load
            module.check_upstream_changes = original_check
        return exit_code, stdout.getvalue()

    def test_check_only_is_strictly_read_only_by_default(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            mapping = Path(tmpdir) / "source.skills.json"
            skill = self._mapping_fixture(mapping)
            before = mapping.read_bytes()
            calls = []
            original_update = module.update_mapping_after_check
            module.update_mapping_after_check = lambda result: calls.append(result)
            try:
                exit_code = self._run_main_with_equal_result(
                    module,
                    ["--check-only", "--allow-v1"],
                    skill,
                )
            finally:
                module.update_mapping_after_check = original_update

            self.assertEqual(0, exit_code)
            self.assertEqual([], calls)
            self.assertEqual(before, mapping.read_bytes())

    def test_check_only_record_check_explicitly_updates_mapping(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            mapping = Path(tmpdir) / "source.skills.json"
            skill = self._mapping_fixture(mapping)
            before = mapping.read_bytes()

            exit_code = self._run_main_with_equal_result(
                module,
                ["--check-only", "--record-check", "--allow-v1"],
                skill,
            )

            self.assertEqual(0, exit_code)
            self.assertNotEqual(before, mapping.read_bytes())
            recorded = json.loads(mapping.read_text(encoding="utf-8"))
            today = module.date.today().isoformat()
            self.assertEqual(today, recorded["video"]["checked_at"])
            self.assertEqual(
                today,
                recorded["skills"][0]["upstream"]["last_checked_at"],
            )
            self.assertEqual(
                today,
                recorded["skills"][0]["upstream"]["last_synced_at"],
            )

    def test_dry_run_with_record_check_remains_read_only(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            mapping = Path(tmpdir) / "source.skills.json"
            skill = self._mapping_fixture(mapping)
            before = mapping.read_bytes()
            calls = []
            original_update = module.update_mapping_after_check
            module.update_mapping_after_check = lambda result: calls.append(result)
            try:
                exit_code = self._run_main_with_equal_result(
                    module,
                    [
                        "--check-only",
                        "--record-check",
                        "--dry-run",
                        "--allow-v1",
                    ],
                    skill,
                )
            finally:
                module.update_mapping_after_check = original_update

            self.assertEqual(0, exit_code)
            self.assertEqual([], calls)
            self.assertEqual(before, mapping.read_bytes())

    def test_record_check_rejects_apply_mode(self):
        module = load_module()

        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                module.main(["--apply", "--record-check"])

        self.assertEqual(2, raised.exception.code)

    def test_apply_success_still_writes_skill_and_mapping(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping = root / "source.skills.json"
            skill = self._mapping_fixture(mapping)
            local_path = root / "SKILL.md"
            local_path.write_text(
                "---\nname: demo-skill\nversion: \"1.0.0\"\n---\n# Old\n",
                encoding="utf-8",
            )
            skill.update(
                {
                    "local_path": local_path,
                    "local_content": local_path.read_text(encoding="utf-8"),
                    "sync_mode": "replace",
                }
            )
            update = {
                "skill": skill,
                "upstream_path": "SKILL.md",
                "upstream_content": "---\nname: demo-skill\n---\n# New\n",
                "changes": "body_changed",
            }

            original_token = module.resolve_github_token
            original_load = module.load_skills_with_upstream
            original_check = module.check_upstream_changes
            original_aux = module.sync_github_auxiliary_files
            module.resolve_github_token = lambda: None
            module.load_skills_with_upstream = lambda **_kwargs: [skill]
            module.check_upstream_changes = lambda _skill, _token: update
            module.sync_github_auxiliary_files = lambda *_args: 0
            try:
                with redirect_stdout(io.StringIO()):
                    exit_code = module.main(["--apply", "--allow-v1"])
            finally:
                module.resolve_github_token = original_token
                module.load_skills_with_upstream = original_load
                module.check_upstream_changes = original_check
                module.sync_github_auxiliary_files = original_aux

            self.assertEqual(0, exit_code)
            self.assertIn("# New", local_path.read_text(encoding="utf-8"))
            recorded = json.loads(mapping.read_text(encoding="utf-8"))
            today = module.date.today().isoformat()
            self.assertEqual(
                today,
                recorded["skills"][0]["upstream"]["last_checked_at"],
            )
            self.assertEqual(
                today,
                recorded["skills"][0]["upstream"]["last_synced_at"],
            )

    def test_apply_dry_run_leaves_skill_and_mapping_unchanged(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping = root / "source.skills.json"
            skill = self._mapping_fixture(mapping)
            local_path = root / "SKILL.md"
            local_path.write_text("# Old\n", encoding="utf-8")
            skill.update(
                {
                    "local_path": local_path,
                    "local_content": "# Old\n",
                    "sync_mode": "replace",
                }
            )
            update = {
                "skill": skill,
                "upstream_path": "SKILL.md",
                "upstream_content": "# New\n",
                "changes": "body_changed",
            }
            mapping_before = mapping.read_bytes()
            skill_before = local_path.read_bytes()

            original_token = module.resolve_github_token
            original_load = module.load_skills_with_upstream
            original_check = module.check_upstream_changes
            original_update_check = module.update_mapping_after_check
            original_update_sync = module.update_mapping_after_sync
            module.resolve_github_token = lambda: None
            module.load_skills_with_upstream = lambda **_kwargs: [skill]
            module.check_upstream_changes = lambda _skill, _token: update
            check_calls = []
            sync_calls = []
            module.update_mapping_after_check = lambda result: check_calls.append(result)
            module.update_mapping_after_sync = lambda result: sync_calls.append(result)
            try:
                with redirect_stdout(io.StringIO()):
                    exit_code = module.main(["--apply", "--dry-run", "--allow-v1"])
            finally:
                module.resolve_github_token = original_token
                module.load_skills_with_upstream = original_load
                module.check_upstream_changes = original_check
                module.update_mapping_after_check = original_update_check
                module.update_mapping_after_sync = original_update_sync

            self.assertEqual(0, exit_code)
            self.assertEqual([], check_calls)
            self.assertEqual([], sync_calls)
            self.assertEqual(mapping_before, mapping.read_bytes())
            self.assertEqual(skill_before, local_path.read_bytes())

    def test_all_unavailable_is_nonzero_and_never_reported_up_to_date(self):
        module = load_module()
        skills = [
            {
                "name": name,
                "category": "ai-workflow",
                "source": f"github:owner/{name}",
                "repo": f"owner/{name}",
            }
            for name in ("one", "two")
        ]

        exit_code, output = self._run_main(
            module,
            ["--check-only"],
            skills,
            lambda _skill, _token: None,
        )

        self.assertEqual(1, exit_code)
        self.assertIn(
            "Summary: total=2 equal=0 changed=0 monitor_review=0 "
            "unavailable=2 rollback=0 expected_skipped=0",
            output,
        )
        self.assertIn("UNEXPECTED UPSTREAM UNAVAILABLE", output)
        self.assertNotIn("up to date", output.lower())
        self.assertNotIn("equal to their authoritative upstream", output)

    def test_partial_unavailable_has_conserved_summary_and_nonzero_exit(self):
        module = load_module()
        skills = [
            {
                "name": "equal",
                "category": "ai-workflow",
                "source": "github:owner/repo",
                "repo": "owner/repo",
                "schema_version": 2,
            },
            {
                "name": "missing",
                "category": "ai-workflow",
                "source": "github:owner/repo",
                "repo": "owner/repo",
                "schema_version": 2,
            },
        ]

        def checker(skill, _token):
            if skill["name"] == "equal":
                return {"skill": skill, "changes": "none"}
            return None

        exit_code, output = self._run_main(
            module,
            ["--check-only"],
            skills,
            checker,
        )

        self.assertEqual(1, exit_code)
        self.assertIn(
            "Summary: total=2 equal=1 changed=0 monitor_review=0 "
            "unavailable=1 rollback=0 expected_skipped=0",
            output,
        )

    def test_summary_categories_are_conserved(self):
        module = load_module()
        names = ("equal", "changed", "monitor", "missing", "rollback")
        skills = [
            {
                "name": name,
                "category": "ai-workflow",
                "source": "github:owner/repo",
                "repo": "owner/repo",
                "schema_version": 2,
                "ref": "main",
                "upstream_path": "SKILL.md",
                "local_path": Path(f"skills/ai-workflow/{name}/SKILL.md"),
                "sync_mode": "monitor" if name == "monitor" else "replace",
            }
            for name in names
        ]

        def checker(skill, _token):
            name = skill["name"]
            if name == "equal":
                return {"skill": skill, "changes": "none"}
            if name in {"changed", "monitor"}:
                return {
                    "skill": skill,
                    "changes": "body_changed",
                    "upstream_path": "SKILL.md",
                    "upstream_content": "# New\n",
                }
            if name == "rollback":
                return {
                    "skill": skill,
                    "changes": "upstream_rollback",
                    "current_commit": "older",
                    "behind_by": 1,
                }
            return None

        exit_code, output = self._run_main(
            module,
            ["--check-only"],
            skills,
            checker,
        )

        self.assertEqual(1, exit_code)
        expected = {
            "total": 5,
            "equal": 1,
            "changed": 1,
            "monitor_review": 1,
            "unavailable": 1,
            "rollback": 1,
            "expected_skipped": 0,
        }
        summary = next(line for line in output.splitlines() if line.startswith("Summary:"))
        observed = {
            key: int(value)
            for key, value in (
                token.split("=", 1)
                for token in summary.removeprefix("Summary: ").split()
            )
        }
        self.assertEqual(expected, observed)
        self.assertEqual(observed["total"], sum(value for key, value in observed.items() if key != "total"))

    def test_v2_apply_update_is_blocked_without_any_write(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping = root / "source.skills.json"
            mapping.write_text('{"schema_version": 2, "sentinel": true}\n', encoding="utf-8")
            local_path = root / "SKILL.md"
            local_path.write_text("# Old\n", encoding="utf-8")
            skill = {
                "name": "demo-skill",
                "category": "ai-workflow",
                "source": "github:owner/repo",
                "repo": "owner/repo",
                "schema_version": 2,
                "sync_mode": "replace",
                "local_path": local_path,
                "local_content": "# Old\n",
                "mapping_path": mapping,
                "mapping_entry_index": 0,
            }
            update = {
                "skill": skill,
                "changes": "body_changed",
                "upstream_path": "SKILL.md",
                "upstream_content": "# New\n",
            }
            mapping_before = mapping.read_bytes()
            skill_before = local_path.read_bytes()
            original_check_write = module.update_mapping_after_check
            original_sync_write = module.update_mapping_after_sync
            original_aux = module.sync_github_auxiliary_files
            module.update_mapping_after_check = lambda _result: self.fail("v2 check writer called")
            module.update_mapping_after_sync = lambda _result: self.fail("v2 sync writer called")
            module.sync_github_auxiliary_files = lambda *_args: self.fail("legacy sibling sync called")
            try:
                exit_code, output = self._run_main(
                    module,
                    ["--apply"],
                    [skill],
                    lambda _skill, _token: update,
                )
            finally:
                module.update_mapping_after_check = original_check_write
                module.update_mapping_after_sync = original_sync_write
                module.sync_github_auxiliary_files = original_aux

            self.assertEqual(2, exit_code)
            self.assertIn("legacy single-file/sibling writer", output)
            self.assertEqual(mapping_before, mapping.read_bytes())
            self.assertEqual(skill_before, local_path.read_bytes())

    def test_v2_record_check_is_blocked_without_legacy_timestamp_write(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            mapping = Path(tmpdir) / "source.skills.json"
            mapping.write_text('{"schema_version": 2, "sentinel": true}\n', encoding="utf-8")
            skill = {
                "name": "demo-skill",
                "category": "ai-workflow",
                "source": "github:owner/repo",
                "repo": "owner/repo",
                "schema_version": 2,
                "mapping_path": mapping,
                "mapping_entry_index": 0,
            }
            before = mapping.read_bytes()
            original_update = module.update_mapping_after_check
            module.update_mapping_after_check = lambda _result: self.fail("legacy v2 writer called")
            try:
                exit_code, output = self._run_main(
                    module,
                    ["--check-only", "--record-check"],
                    [skill],
                    lambda checked, _token: {"skill": checked, "changes": "none"},
                )
            finally:
                module.update_mapping_after_check = original_update

            self.assertEqual(2, exit_code)
            self.assertIn("origin-aware artifact-set writer", output)
            self.assertEqual(before, mapping.read_bytes())

    def test_v1_apply_requires_explicit_allow_v1_and_writes_nothing_by_default(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping = root / "source.skills.json"
            mapping.write_text('{"sentinel": true}\n', encoding="utf-8")
            local_path = root / "SKILL.md"
            local_path.write_text("# Old\n", encoding="utf-8")
            skill = {
                "name": "legacy-skill",
                "category": "ai-workflow",
                "source": "github:legacy/owner",
                "repo": "legacy/owner",
                "schema_version": 1,
                "sync_mode": "replace",
                "local_path": local_path,
                "local_content": "# Old\n",
                "mapping_path": mapping,
                "mapping_entry_index": 0,
            }
            before_mapping = mapping.read_bytes()
            before_skill = local_path.read_bytes()
            exit_code, output = self._run_main(
                module,
                ["--apply"],
                [skill],
                lambda *_args: self.fail("legacy checker must not run by default"),
            )

            self.assertEqual(1, exit_code)
            self.assertIn("explicit --allow-v1", output)
            self.assertEqual(before_mapping, mapping.read_bytes())
            self.assertEqual(before_skill, local_path.read_bytes())

            record_code, record_output = self._run_main(
                module,
                ["--check-only", "--record-check"],
                [skill],
                lambda *_args: self.fail("legacy checker must not run by default"),
            )
            self.assertEqual(1, record_code)
            self.assertIn("explicit --allow-v1", record_output)
            self.assertEqual(before_mapping, mapping.read_bytes())
            self.assertEqual(before_skill, local_path.read_bytes())

    def test_explicit_source_with_zero_matches_is_nonzero_for_check_only(self):
        module = load_module()
        exit_code, output = self._run_main(
            module,
            ["--check-only", "--source", "github:typo/missing"],
            [],
            lambda *_args: self.fail("empty input must not run a check"),
        )

        self.assertEqual(1, exit_code)
        self.assertIn("total=0", output)
        self.assertIn("no active upstream entries matched explicit --source", output)
        self.assertIn("github:typo/missing", output)

    def test_explicit_source_with_zero_matches_is_nonzero_for_apply_dry_run(self):
        module = load_module()
        exit_code, output = self._run_main(
            module,
            [
                "--apply",
                "--dry-run",
                "--source",
                "github:typo/missing",
            ],
            [],
            lambda *_args: self.fail("empty input must not run a check"),
        )

        self.assertEqual(1, exit_code)
        self.assertIn("total=0", output)
        self.assertIn("refusing an empty successful check", output)

    def test_unfiltered_zero_inputs_is_nonzero(self):
        module = load_module()
        exit_code, output = self._run_main(
            module,
            ["--check-only"],
            [],
            lambda *_args: self.fail("empty input must not run a check"),
        )

        self.assertEqual(1, exit_code)
        self.assertIn("no active external upstream entries were discovered", output)

    def test_loads_exact_upstream_paths_from_source_mappings(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            skill = repo / "skills" / "ai-workflow" / "demo-skill"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    name: demo-skill
                    description: Local skill.
                    source: "github:owner/repo"
                    ---

                    # Demo
                    """
                ),
                encoding="utf-8",
            )

            mapping = repo / "docs" / "sources" / "owner-repo.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(
                    {
                        "video": {"url": "https://github.com/owner/repo"},
                        "skills": [
                            {
                                "video_name": "demo-skill",
                                "repo_skill": "skills/ai-workflow/demo-skill/SKILL.md",
                            "upstream": {
                                "repo": "owner/repo",
                                "path": "custom/path/SKILL.md",
                                "ref": "main",
                                "sync_mode": "monitor",
                            },
                        }
                    ],
                    }
                ),
                encoding="utf-8",
            )

            module.REPO_ROOT = repo
            module.SKILLS_DIR = repo / "skills"
            module.SOURCE_MAPPINGS_DIR = repo / "docs" / "sources"
            module.PROVENANCE_FILE = repo / "docs" / "sources" / "in-house.skills.json"

            loaded = module.load_skills_with_upstream(allow_v1=True)

            self.assertEqual(1, len(loaded))
            self.assertEqual("owner/repo", loaded[0]["repo"])
            self.assertEqual("custom/path/SKILL.md", loaded[0]["upstream_path"])
            self.assertEqual("monitor", loaded[0]["sync_mode"])
            self.assertEqual(skill / "SKILL.md", loaded[0]["local_path"])

    def test_default_loader_rejects_missing_string_and_future_schema_versions(self):
        for label, schema_marker in (
            ("missing", None),
            ("string-two", "2"),
            ("future", 3),
        ):
            with self.subTest(schema=label), tempfile.TemporaryDirectory() as tmpdir:
                module = load_module()
                repo = Path(tmpdir)
                repo_skill = "skills/ai-workflow/demo-skill/SKILL.md"
                local_path = repo / repo_skill
                local_path.parent.mkdir(parents=True)
                local_path.write_text("# Demo\n", encoding="utf-8")
                payload = {
                    "skills": [
                        {
                            "video_name": "demo-skill",
                            "normalized_slug": "demo-skill",
                            "status": "verified_in_repo",
                            "repo_skill": repo_skill,
                            "upstream": {
                                "repo": "attacker/legacy",
                                "path": "payload/SKILL.md",
                                "ref": "main",
                                "sync_mode": "replace",
                            },
                        }
                    ]
                }
                if label != "missing":
                    payload["schema_version"] = schema_marker
                mapping = repo / "docs" / "sources" / "source.skills.json"
                mapping.parent.mkdir(parents=True)
                mapping.write_text(json.dumps(payload), encoding="utf-8")
                module.REPO_ROOT = repo
                module.SKILLS_DIR = repo / "skills"
                module.SOURCE_MAPPINGS_DIR = repo / "docs" / "sources"
                module.PROVENANCE_FILE = repo / "docs" / "sources" / "in-house.skills.json"

                loaded = module.load_skills_with_upstream()

                self.assertEqual(1, len(loaded))
                self.assertEqual("", loaded[0]["repo"])
                self.assertIn("strict integer 2 is required", loaded[0]["load_error"])
                self.assertNotIn("attacker/legacy", json.dumps(loaded[0], default=str))

    def test_explicit_allow_v1_loads_headerless_legacy_mapping(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            repo_skill = "skills/ai-workflow/demo-skill/SKILL.md"
            local_path = repo / repo_skill
            local_path.parent.mkdir(parents=True)
            local_path.write_text("---\nname: demo-skill\n---\n# Demo\n", encoding="utf-8")
            mapping = repo / "docs" / "sources" / "legacy.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "video_name": "demo-skill",
                                "repo_skill": repo_skill,
                                "upstream": {
                                    "repo": "legacy/owner",
                                    "path": "legacy/SKILL.md",
                                    "ref": "main",
                                    "sync_mode": "replace",
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            module.REPO_ROOT = repo
            module.SKILLS_DIR = repo / "skills"
            module.SOURCE_MAPPINGS_DIR = repo / "docs" / "sources"
            module.PROVENANCE_FILE = repo / "docs" / "sources" / "in-house.skills.json"

            strict = module.load_skills_with_upstream()
            legacy = module.load_skills_with_upstream(allow_v1=True)

            self.assertIn("strict integer 2 is required", strict[0]["load_error"])
            self.assertEqual(1, legacy[0]["schema_version"])
            self.assertEqual("legacy/owner", legacy[0]["repo"])
            self.assertEqual("legacy/SKILL.md", legacy[0]["upstream_path"])

    def test_v2_directory_artifact_owns_nested_skill_with_null_origin_path(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            repo_skill = "skills/ai-workflow/demo-skill/SKILL.md"
            local_path = repo / repo_skill
            local_path.parent.mkdir(parents=True)
            local_path.write_text("---\nname: demo-skill\n---\n# Demo\n", encoding="utf-8")
            mapping = repo / "docs" / "sources" / "directory.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "skills": [
                            {
                                "video_name": "demo-skill",
                                "normalized_slug": "demo-skill",
                                "status": "verified_in_repo",
                                "kind": "mirror",
                                "repo_skill": repo_skill,
                                "origins": [
                                    {
                                        "repo": "trusted/owner",
                                        "path": None,
                                        "sync_mode": "monitor",
                                        "artifacts": [
                                            {
                                                "type": "directory",
                                                "source": "upstream/demo-skill",
                                                "target": "skills/ai-workflow/demo-skill",
                                            }
                                        ],
                                        "tracking": {
                                            "ref": "main",
                                            "resolved_commit": "reviewed",
                                            "path_commit": "reviewed-path",
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            module.REPO_ROOT = repo
            module.SKILLS_DIR = repo / "skills"
            module.SOURCE_MAPPINGS_DIR = repo / "docs" / "sources"
            module.PROVENANCE_FILE = repo / "docs" / "sources" / "in-house.skills.json"

            loaded = module.load_skills_with_upstream()

            self.assertEqual(1, len(loaded))
            self.assertNotIn("load_error", loaded[0])
            self.assertIsNone(loaded[0]["origin_path"])
            self.assertEqual(
                "upstream/demo-skill/SKILL.md",
                loaded[0]["upstream_path"],
            )

    def test_malformed_mapping_shapes_become_unavailable_without_loader_crash(self):
        payloads = (
            ("null-entry", json.dumps({"schema_version": 2, "skills": [None]})),
            ("non-array", json.dumps({"schema_version": 2, "skills": {}})),
            ("top-level", json.dumps([])),
            ("invalid-json", "{"),
        )
        for label, raw in payloads:
            with self.subTest(shape=label), tempfile.TemporaryDirectory() as tmpdir:
                module = load_module()
                repo = Path(tmpdir)
                mapping = repo / "docs" / "sources" / "malformed.skills.json"
                mapping.parent.mkdir(parents=True)
                mapping.write_text(raw, encoding="utf-8")
                module.REPO_ROOT = repo
                module.SKILLS_DIR = repo / "skills"
                module.SOURCE_MAPPINGS_DIR = repo / "docs" / "sources"
                module.PROVENANCE_FILE = repo / "docs" / "sources" / "in-house.skills.json"

                loaded = module.load_skills_with_upstream()

                self.assertEqual(1, len(loaded))
                self.assertTrue(loaded[0]["load_error"])

    def test_v2_loader_ignores_split_legacy_upstream_and_uses_unique_owner(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            local_path = repo / "skills" / "ai-workflow" / "demo-skill" / "SKILL.md"
            local_path.parent.mkdir(parents=True)
            local_path.write_text("---\nname: demo-skill\n---\n# Demo\n", encoding="utf-8")
            mapping = repo / "docs" / "sources" / "owner-repo.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "skills": [
                            {
                                "video_name": "demo-skill",
                                "normalized_slug": "demo-skill",
                                "status": "verified_in_repo",
                                "kind": "mirror",
                                "repo_skill": "skills/ai-workflow/demo-skill/SKILL.md",
                                "source": "https://github.com/attacker/legacy",
                                "upstream": {
                                    "repo": "attacker/legacy",
                                    "path": "payload/SKILL.md",
                                    "ref": "evil",
                                    "sync_mode": "replace",
                                    "last_synced_commit": "attacker-checkpoint",
                                },
                                "origins": [
                                    {
                                        "repo": "trusted/owner",
                                        "path": "canonical/SKILL.md",
                                        "sync_mode": "monitor",
                                        "artifacts": [
                                            {
                                                "source": "canonical/SKILL.md",
                                                "target": "skills/ai-workflow/demo-skill/SKILL.md",
                                            }
                                        ],
                                        "tracking": {
                                            "ref": "main",
                                            "resolved_commit": "trusted-checkpoint",
                                            "path_commit": "trusted-path-checkpoint",
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            module.REPO_ROOT = repo
            module.SKILLS_DIR = repo / "skills"
            module.SOURCE_MAPPINGS_DIR = repo / "docs" / "sources"
            module.PROVENANCE_FILE = repo / "docs" / "sources" / "in-house.skills.json"

            loaded = module.load_skills_with_upstream()

            self.assertEqual(1, len(loaded))
            self.assertEqual(2, loaded[0]["schema_version"])
            self.assertEqual("trusted/owner", loaded[0]["repo"])
            self.assertEqual("canonical/SKILL.md", loaded[0]["upstream_path"])
            self.assertEqual("main", loaded[0]["ref"])
            self.assertEqual("monitor", loaded[0]["sync_mode"])
            self.assertEqual("trusted-checkpoint", loaded[0]["last_synced_commit"])
            self.assertEqual("trusted-path-checkpoint", loaded[0]["path_commit"])
            self.assertNotIn("attacker", json.dumps(loaded[0], default=str))

    def test_v2_loader_fails_closed_when_target_has_no_owner(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            local_path = repo / "skills" / "ai-workflow" / "demo-skill" / "SKILL.md"
            local_path.parent.mkdir(parents=True)
            local_path.write_text("# Demo\n", encoding="utf-8")
            mapping = repo / "docs" / "sources" / "owner-repo.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "skills": [
                            {
                                "video_name": "demo-skill",
                                "normalized_slug": "demo-skill",
                                "status": "verified_in_repo",
                                "kind": "mirror",
                                "repo_skill": "skills/ai-workflow/demo-skill/SKILL.md",
                                "upstream": {
                                    "repo": "attacker/legacy",
                                    "path": "payload/SKILL.md",
                                },
                                "origins": [
                                    {
                                        "repo": "trusted/owner",
                                        "path": "other/SKILL.md",
                                        "sync_mode": "replace",
                                        "artifacts": [
                                            {
                                                "source": "other/SKILL.md",
                                                "target": "skills/ai-workflow/other/SKILL.md",
                                            }
                                        ],
                                        "tracking": {"ref": "v1.0.0"},
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            module.REPO_ROOT = repo
            module.SKILLS_DIR = repo / "skills"
            module.SOURCE_MAPPINGS_DIR = repo / "docs" / "sources"
            module.PROVENANCE_FILE = repo / "docs" / "sources" / "in-house.skills.json"

            loaded = module.load_skills_with_upstream()

            self.assertEqual(1, len(loaded))
            self.assertEqual("", loaded[0]["repo"])
            self.assertIn("exactly one origin/artifact owner", loaded[0]["load_error"])
            self.assertNotIn("attacker/legacy", json.dumps(loaded[0], default=str))

    def test_v2_loader_fails_closed_when_target_has_multiple_owners(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            repo_skill = "skills/ai-workflow/demo-skill/SKILL.md"
            local_path = repo / repo_skill
            local_path.parent.mkdir(parents=True)
            local_path.write_text("# Demo\n", encoding="utf-8")
            owner = lambda name: {
                "repo": f"trusted/{name}",
                "path": f"{name}/SKILL.md",
                "sync_mode": "replace",
                "artifacts": [
                    {"source": f"{name}/SKILL.md", "target": repo_skill}
                ],
                "tracking": {"ref": "v1.0.0"},
            }
            mapping = repo / "docs" / "sources" / "owners.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "skills": [
                            {
                                "video_name": "demo-skill",
                                "normalized_slug": "demo-skill",
                                "status": "verified_in_repo",
                                "kind": "mirror",
                                "repo_skill": repo_skill,
                                "origins": [owner("one"), owner("two")],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            module.REPO_ROOT = repo
            module.SKILLS_DIR = repo / "skills"
            module.SOURCE_MAPPINGS_DIR = repo / "docs" / "sources"
            module.PROVENANCE_FILE = repo / "docs" / "sources" / "in-house.skills.json"

            loaded = module.load_skills_with_upstream()

            self.assertEqual(1, len(loaded))
            self.assertIn("found 2", loaded[0]["load_error"])

    def test_merge_frontmatter_preserves_local_metadata_and_replaces_body(self):
        module = load_module()

        local = textwrap.dedent(
            """\
            ---
            name: demo-skill
            description: "Old description."
            version: "1.2.3"
            source: "github:owner/repo"
            tags: ["demo"]
            upstream_slug: demo-skill
            ---
            # Old Body

            <!-- LOCAL-CURATION-SUPPLEMENT:START -->
            ## Repository Contract

            Preserve this reviewed local rule.
            <!-- LOCAL-CURATION-SUPPLEMENT:END -->
            """
        )
        upstream = textwrap.dedent(
            """\
            ---
            name: demo-skill
            description: New upstream description.
            ---
            # New Body
            """
        )

        merged = module.merge_frontmatter(local, upstream)

        self.assertIn('description: "New upstream description."', merged)
        self.assertIn('version: "1.2.4"', merged)
        self.assertIn("upstream_slug: demo-skill", merged)
        self.assertIn("# New Body", merged)
        self.assertNotIn("# Old Body", merged)
        self.assertIn("LOCAL-QUALITY-SUPPLEMENT:START", merged)
        self.assertIn("Preserve this reviewed local rule.", merged)

    def test_repository_adaptation_rewrites_addyosmani_shared_references(self):
        module = load_module()

        adapted = module.apply_repository_adaptations(
            "See `../../references/definition-of-done.md`.\n",
            {"repo": "addyosmani/agent-skills"},
        )
        untouched = module.apply_repository_adaptations(
            "See `../../references/definition-of-done.md`.\n",
            {"repo": "owner/repo"},
        )

        self.assertEqual(
            "See `references/definition-of-done.md`.\n",
            adapted,
        )
        self.assertEqual(
            "See `../../references/definition-of-done.md`.\n",
            untouched,
        )

    def test_check_upstream_changes_uses_exact_provenance_path(self):
        module = load_module()
        seen_urls = []

        def fake_fetch(url, token):
            seen_urls.append(url)
            return textwrap.dedent(
                """\
                ---
                name: demo-skill
                description: Remote.
                ---
                # Remote Body
                """
            )

        original_fetch = module.fetch_url
        module.fetch_url = fake_fetch
        try:
            update = module.check_upstream_changes(
                {
                    "name": "demo-skill",
                    "category": "ai-workflow",
                    "repo": "owner/repo",
                    "ref": "dev",
                    "upstream_path": "nested/source.md",
                    "local_content": "# Local Body\n",
                },
                token=None,
            )
        finally:
            module.fetch_url = original_fetch

        self.assertIsNotNone(update)
        self.assertEqual(
            ["https://raw.githubusercontent.com/owner/repo/dev/nested/source.md"],
            seen_urls,
        )

    def test_check_upstream_changes_reports_successful_no_change(self):
        module = load_module()
        local = "---\nname: demo\n---\n# Same Body\n"
        original_fetch = module.fetch_url
        module.fetch_url = lambda _url, _token: local
        try:
            result = module.check_upstream_changes(
                {
                    "name": "demo",
                    "category": "ai-workflow",
                    "repo": "owner/repo",
                    "ref": "main",
                    "upstream_path": "SKILL.md",
                    "local_content": local,
                },
                token=None,
            )
        finally:
            module.fetch_url = original_fetch

        self.assertIsNotNone(result)
        self.assertEqual("none", result["changes"])

    def test_check_upstream_changes_classifies_fetch_failure_as_unavailable(self):
        module = load_module()
        original_fetch = module.fetch_url
        module.fetch_url = lambda *_args, **_kwargs: None
        try:
            result = module.check_upstream_changes(
                {
                    "name": "demo",
                    "category": "ai-workflow",
                    "repo": "owner/repo",
                    "ref": "main",
                    "upstream_path": "SKILL.md",
                    "local_content": "# Local\n",
                },
                token=None,
            )
        finally:
            module.fetch_url = original_fetch

        self.assertIsNotNone(result)
        self.assertEqual("unavailable", result["changes"])
        self.assertIn("SKILL.md", result["reason"])

    def test_check_upstream_changes_compares_repository_adapted_body(self):
        module = load_module()
        local = "# Demo\n\nSee `references/definition-of-done.md`.\n"
        upstream = "# Demo\n\nSee `../../references/definition-of-done.md`.\n"
        original_fetch = module.fetch_url
        module.fetch_url = lambda _url, _token, **_kwargs: upstream
        try:
            result = module.check_upstream_changes(
                {
                    "name": "demo",
                    "category": "ai-workflow",
                    "repo": "addyosmani/agent-skills",
                    "ref": "main",
                    "upstream_path": "skills/demo/SKILL.md",
                    "local_content": local,
                },
                token=None,
            )
        finally:
            module.fetch_url = original_fetch

        self.assertIsNotNone(result)
        self.assertEqual("none", result["changes"])

    def test_monitor_checkpoint_skips_false_positive_for_curated_body(self):
        module = load_module()
        original_commit_sha = module.github_commit_sha
        original_fetch = module.fetch_url
        module.github_commit_sha = lambda _repo, _ref, _token: "reviewed-sha"
        module.fetch_url = lambda *_args, **_kwargs: self.fail(
            "matching monitor checkpoint should not fetch or compare the curated body"
        )
        try:
            result = module.check_upstream_changes(
                {
                    "name": "curated-skill",
                    "category": "ai-workflow",
                    "repo": "owner/repo",
                    "ref": "main",
                    "upstream_path": "README.md",
                    "sync_mode": "monitor",
                    "last_synced_commit": "reviewed-sha",
                    "local_content": "# Original in-house rewrite\n",
                },
                token=None,
            )
        finally:
            module.github_commit_sha = original_commit_sha
            module.fetch_url = original_fetch

        self.assertIsNotNone(result)
        self.assertEqual("none", result["changes"])

    def test_monitor_checkpoint_reports_upstream_rollback_without_body_diff(self):
        module = load_module()
        original_commit_sha = module.github_commit_sha
        original_compare = module.github_compare_relation
        original_fetch = module.fetch_url
        module.github_commit_sha = lambda _repo, _ref, _token: "older-head"
        module.github_compare_relation = lambda *_args, **_kwargs: {
            "status": "behind",
            "ahead_by": 0,
            "behind_by": 42,
        }
        module.fetch_url = lambda *_args, **_kwargs: self.fail(
            "an upstream rollback should not be compared as a body update"
        )
        try:
            result = module.check_upstream_changes(
                {
                    "name": "curated-skill",
                    "category": "ai-workflow",
                    "repo": "owner/repo",
                    "ref": "main",
                    "upstream_path": "README.md",
                    "sync_mode": "monitor",
                    "last_synced_commit": "reviewed-sha",
                    "local_content": "# Original in-house rewrite\n",
                },
                token=None,
            )
        finally:
            module.github_commit_sha = original_commit_sha
            module.github_compare_relation = original_compare
            module.fetch_url = original_fetch

        self.assertIsNotNone(result)
        self.assertEqual("upstream_rollback", result["changes"])
        self.assertEqual("older-head", result["current_commit"])
        self.assertEqual(42, result["behind_by"])

    def test_monitor_ahead_or_diverged_requires_review_even_when_body_is_equal(self):
        module = load_module()
        local = "---\nname: demo\n---\n# Same Body\n"
        for relation_status in ("ahead", "diverged", "identical"):
            with self.subTest(relation=relation_status):
                original_commit_sha = module.github_commit_sha
                original_compare = module.github_compare_relation
                original_fetch = module.fetch_url
                fetch_calls = []
                module.github_commit_sha = lambda *_args: "new-head"
                module.github_compare_relation = lambda *_args: {
                    "status": relation_status,
                    "ahead_by": 1,
                    "behind_by": 0,
                }
                module.fetch_url = lambda *_args, **_kwargs: (
                    fetch_calls.append(True) or local
                )
                try:
                    result = module.check_upstream_changes(
                        {
                            "name": "curated-skill",
                            "category": "ai-workflow",
                            "repo": "owner/repo",
                            "ref": "main",
                            "upstream_path": "SKILL.md",
                            "sync_mode": "monitor",
                            "last_synced_commit": "reviewed-head",
                            "local_content": local,
                        },
                        token=None,
                    )
                finally:
                    module.github_commit_sha = original_commit_sha
                    module.github_compare_relation = original_compare
                    module.fetch_url = original_fetch

                self.assertEqual("monitor_review", result["changes"])
                self.assertEqual(relation_status, result["relation"])
                self.assertEqual([], fetch_calls)

    def test_monitor_compare_resolution_failure_is_unavailable_without_body_equal_fallback(self):
        module = load_module()
        original_commit_sha = module.github_commit_sha
        original_compare = module.github_compare_relation
        original_fetch = module.fetch_url
        module.github_commit_sha = lambda *_args: "new-head"
        module.github_compare_relation = lambda *_args: None
        module.fetch_url = lambda *_args, **_kwargs: self.fail(
            "monitor compare failure must not fall back to body equality"
        )
        try:
            result = module.check_upstream_changes(
                {
                    "name": "curated-skill",
                    "category": "ai-workflow",
                    "repo": "owner/repo",
                    "ref": "main",
                    "upstream_path": "SKILL.md",
                    "sync_mode": "monitor",
                    "last_synced_commit": "reviewed-head",
                    "local_content": "# Same Body\n",
                },
                token=None,
            )
        finally:
            module.github_commit_sha = original_commit_sha
            module.github_compare_relation = original_compare
            module.fetch_url = original_fetch

        self.assertEqual("unavailable", result["changes"])
        self.assertIn("checkpoint relationship", result["reason"])

    def test_monitor_head_resolution_failure_is_unavailable(self):
        module = load_module()
        original_commit_sha = module.github_commit_sha
        original_fetch = module.fetch_url
        module.github_commit_sha = lambda *_args: None
        module.fetch_url = lambda *_args, **_kwargs: self.fail(
            "monitor head failure must not fall back to body equality"
        )
        try:
            result = module.check_upstream_changes(
                {
                    "name": "curated-skill",
                    "category": "ai-workflow",
                    "repo": "owner/repo",
                    "ref": "main",
                    "upstream_path": "SKILL.md",
                    "sync_mode": "monitor",
                    "last_synced_commit": "reviewed-head",
                    "local_content": "# Same Body\n",
                },
                token=None,
            )
        finally:
            module.github_commit_sha = original_commit_sha
            module.fetch_url = original_fetch

        self.assertEqual("unavailable", result["changes"])
        self.assertIn("resolve monitor-only upstream head", result["reason"])

    def test_monitor_without_checkpoint_is_unavailable(self):
        module = load_module()
        original_fetch = module.fetch_url
        module.fetch_url = lambda *_args, **_kwargs: self.fail(
            "monitor without checkpoint must not fall back to body equality"
        )
        try:
            result = module.check_upstream_changes(
                {
                    "name": "curated-skill",
                    "category": "ai-workflow",
                    "repo": "owner/repo",
                    "ref": "main",
                    "upstream_path": "SKILL.md",
                    "sync_mode": "monitor",
                    "last_synced_commit": None,
                    "local_content": "# Same Body\n",
                },
                token=None,
            )
        finally:
            module.fetch_url = original_fetch

        self.assertEqual("unavailable", result["changes"])
        self.assertIn("no reviewed commit checkpoint", result["reason"])

    def test_github_compare_relation_returns_commit_relationship(self):
        module = load_module()
        original_api_get = module.github_api_get
        module.github_api_get = lambda _url, _token: {
            "status": "behind",
            "ahead_by": 0,
            "behind_by": 7,
        }
        try:
            relation = module.github_compare_relation(
                "owner/repo",
                "reviewed-sha",
                "older-head",
                token=None,
            )
        finally:
            module.github_api_get = original_api_get

        self.assertEqual(
            {"status": "behind", "ahead_by": 0, "behind_by": 7},
            relation,
        )

    def test_update_mapping_after_check_only_syncs_equal_body(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            mapping = Path(tmpdir) / "source.skills.json"
            mapping.write_text(
                json.dumps(
                    {
                        "video": {"checked_at": "2026-01-01"},
                        "skills": [
                            {
                                "upstream": {
                                    "last_checked_at": "2026-01-01",
                                    "last_synced_at": "2026-01-01",
                                }
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            base_skill = {"mapping_path": mapping, "mapping_entry_index": 0}

            module.update_mapping_after_check({"skill": base_skill, "changes": "body_changed"})
            changed = json.loads(mapping.read_text(encoding="utf-8"))
            self.assertEqual("2026-01-01", changed["skills"][0]["upstream"]["last_synced_at"])
            self.assertEqual(module.date.today().isoformat(), changed["skills"][0]["upstream"]["last_checked_at"])

            module.update_mapping_after_check({"skill": base_skill, "changes": "none"})
            equal = json.loads(mapping.read_text(encoding="utf-8"))
            self.assertEqual(module.date.today().isoformat(), equal["skills"][0]["upstream"]["last_synced_at"])

    def test_monitor_review_guidance_includes_compare_and_curation_checklist(self):
        module = load_module()

        update = {
            "upstream_path": "README.md",
            "skill": {
                "name": "nlpm-audit",
                "repo": "xiaolai/nlpm",
                "ref": "main",
                "sync_mode": "monitor",
                "last_synced_commit": "abc123",
                "local_path": Path("skills/ai-workflow/nlpm-audit/SKILL.md"),
            },
        }

        guidance = "\n".join(module.monitor_review_guidance(update))

        self.assertIn("nlpm-audit requires manual monitor review", guidance)
        self.assertIn("https://github.com/xiaolai/nlpm/blob/main/README.md", guidance)
        self.assertIn("https://github.com/xiaolai/nlpm/compare/abc123...main", guidance)
        self.assertIn("durable method, install, scoring, CI, security, or compatibility", guidance)
        self.assertIn("update the curated SKILL.md, bump version/updated_at", guidance)
        self.assertIn("record why in provenance verification_attempts or the automation memory", guidance)

    def test_monitor_rollback_guidance_preserves_reviewed_checkpoint(self):
        module = load_module()
        result = {
            "changes": "upstream_rollback",
            "current_commit": "older-head",
            "behind_by": 42,
            "skill": {
                "name": "nlpm-audit",
                "repo": "xiaolai/nlpm",
                "ref": "main",
                "last_synced_commit": "reviewed-sha",
            },
        }

        guidance = "\n".join(module.monitor_rollback_guidance(result))

        self.assertIn("upstream ref moved backward by 42 commits", guidance)
        self.assertIn("Current head: older-head", guidance)
        self.assertIn("Reviewed checkpoint: reviewed-sha", guidance)
        self.assertIn("Do not move the checkpoint backward", guidance)

    def test_quality_supplement_is_not_duplicated(self):
        module = load_module()

        content = textwrap.dedent(
            """\
            ---
            name: compact-skill
            description: Compact.
            ---
            # Compact
            """
        )

        once = module.ensure_quality_floor(content, "compact-skill")
        twice = module.ensure_quality_floor(once, "compact-skill")

        self.assertEqual(once, twice)
        self.assertEqual(1, twice.count("LOCAL-QUALITY-SUPPLEMENT:START"))
        self.assertIn("```text", twice)

    def test_comparable_body_ignores_local_quality_supplement(self):
        module = load_module()

        upstream = "# Compact\n"
        local = module.ensure_quality_floor(
            textwrap.dedent(
                """\
                ---
                name: compact-skill
                description: Compact skill with local supplement.
                ---
                # Compact
                """
            ),
            "compact-skill",
        )

        self.assertEqual(upstream.strip(), module.comparable_body(local))

    def test_comparable_body_ignores_local_curation_supplement(self):
        module = load_module()

        local = textwrap.dedent(
            """\
            ---
            name: curated
            description: Curated.
            ---
            # Compact

            <!-- LOCAL-CURATION-SUPPLEMENT:START -->
            ## Local Review Checklist

            - Keep this repository-specific checklist without treating it as upstream drift.
            <!-- LOCAL-CURATION-SUPPLEMENT:END -->
            """
        )

        self.assertEqual("# Compact", module.comparable_body(local))

    def test_comparable_body_ignores_trailing_whitespace(self):
        module = load_module()

        self.assertEqual(
            "# Body\n\nA line",
            module.comparable_body("# Body   \n\nA line  \n"),
        )

    def test_parse_frontmatter_collapses_folded_scalars(self):
        module = load_module()

        parsed = module.parse_frontmatter(
            textwrap.dedent(
                """\
                ---
                name: folded
                description: >
                  Audit skills for risky behavior
                  before installing them.
                ---
                # Body
                """
            )
        )

        self.assertEqual(
            "Audit skills for risky behavior before installing them.",
            parsed["description"],
        )

    def test_fetch_url_treats_ssl_errors_as_recoverable_fetch_failures(self):
        module = load_module()

        def fake_urlopen(_req, timeout):
            raise module.ssl.SSLError("handshake timed out")

        original_urlopen = module.urllib.request.urlopen
        original_fallback = module.fetch_github_raw_via_api
        module.urllib.request.urlopen = fake_urlopen
        module.fetch_github_raw_via_api = lambda _url, _token: None
        try:
            result = module.fetch_url("https://raw.githubusercontent.com/owner/repo/main/SKILL.md")
        finally:
            module.urllib.request.urlopen = original_urlopen
            module.fetch_github_raw_via_api = original_fallback

        self.assertIsNone(result)

    def test_auxiliary_sync_skips_case_variant_skill_markdown(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            local_dir = Path(tmpdir) / "skills" / "developer-engineering" / "graphify"
            local_dir.mkdir(parents=True)
            canonical = local_dir / "SKILL.md"
            canonical.write_text("# Canonical\n", encoding="utf-8")

            def fake_api_get(_url, _token):
                return [
                    {
                        "type": "file",
                        "name": "skill.md",
                        "download_url": "https://example.test/skill.md",
                    },
                    {
                        "type": "file",
                        "name": "helper.py",
                        "download_url": "https://example.test/helper.py",
                    },
                ]

            def fake_fetch_url(url, _token):
                if url.endswith("helper.py"):
                    return "print('helper')\n"
                return "# Lowercase upstream skill\n"

            original_api_get = module.github_api_get
            original_fetch_url = module.fetch_url
            module.github_api_get = fake_api_get
            module.fetch_url = fake_fetch_url
            try:
                synced = module.sync_github_auxiliary_files(
                    {
                        "repo": "owner/repo",
                        "ref": "main",
                        "local_path": canonical,
                    },
                    "graphify/skill-codex.md",
                    token=None,
                )
            finally:
                module.github_api_get = original_api_get
                module.fetch_url = original_fetch_url

            self.assertEqual(1, synced)
            self.assertEqual("# Canonical\n", canonical.read_text(encoding="utf-8"))
            lowercase_skill = local_dir / "skill.md"
            if lowercase_skill.exists():
                self.assertTrue(lowercase_skill.samefile(canonical))
            self.assertEqual("print('helper')\n", (local_dir / "helper.py").read_text(encoding="utf-8"))

    def test_auxiliary_sync_recurses_into_reference_directories(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            local_dir = Path(tmpdir) / "skills" / "knowledge" / "lark-shared"
            local_dir.mkdir(parents=True)
            canonical = local_dir / "SKILL.md"
            canonical.write_text("# Canonical\n", encoding="utf-8")

            def fake_api_get(url, _token):
                if "/contents/lark-shared?" in url:
                    return [
                        {
                            "type": "dir",
                            "name": "references",
                            "url": "https://api.example.test/references",
                        }
                    ]
                if url == "https://api.example.test/references":
                    return [
                        {
                            "type": "file",
                            "name": "identity.md",
                            "download_url": "https://example.test/identity.md",
                        }
                    ]
                return []

            original_api_get = module.github_api_get
            original_fetch_url = module.fetch_url
            module.github_api_get = fake_api_get
            module.fetch_url = lambda _url, _token: "# Identity\n"
            try:
                synced = module.sync_github_auxiliary_files(
                    {
                        "repo": "owner/repo",
                        "ref": "main",
                        "local_path": canonical,
                    },
                    "lark-shared/SKILL.md",
                    token=None,
                )
            finally:
                module.github_api_get = original_api_get
                module.fetch_url = original_fetch_url

            self.assertEqual(1, synced)
            self.assertEqual(
                "# Identity\n",
                (local_dir / "references" / "identity.md").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
