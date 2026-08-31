import base64
import hashlib
import importlib.util
import io
import json
import tempfile
import textwrap
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

from scripts.github_artifact_provider import (
    ArtifactInventory,
    GitHubArtifactProvider,
    GitHubUnavailable,
    LicenseEvidence,
    ResolvedRef,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "sync_upstream.py"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()


def external_skill_content(slug: str, repo: str) -> bytes:
    return (
        "---\n"
        f"name: {slug}\n"
        f"source: github:{repo}\n"
        f"source_url: https://github.com/{repo}\n"
        "license: MIT\n"
        "---\n"
        f"# {slug}\n"
    ).encode("utf-8")


def mock_license_evidence(
    commit: str = "b" * 40,
    *,
    spdx: str = "MIT",
    api_spdx: str | None = None,
) -> LicenseEvidence:
    return LicenseEvidence(
        path="LICENSE",
        blob_sha="e" * 40,
        content_sha256=hashlib.sha256(spdx.encode("utf-8")).hexdigest(),
        resolved_commit=commit,
        spdx_candidates=(spdx,),
        api_spdx=spdx if api_spdx is None else api_spdx,
    )


def mock_license_checkpoint(
    commit: str = "b" * 40,
    *,
    spdx: str = "MIT",
    api_spdx: str | None = None,
) -> dict:
    evidence = mock_license_evidence(
        commit,
        spdx=spdx,
        api_spdx=api_spdx,
    )
    return {
        "path": evidence.path,
        "blob_sha": evidence.blob_sha,
        "content_sha256": evidence.content_sha256,
        "spdx": spdx,
        "resolved_commit": commit,
        "api_spdx": evidence.api_spdx,
    }


def complete_v2_entry(entry: dict, content: bytes) -> dict:
    """Fill strict v2 sync fields for focused loader fixtures."""
    entry = json.loads(json.dumps(entry))
    slug = entry["normalized_slug"]
    external_repo = next(
        str(origin["repo"])
        for origin in entry["origins"]
        if not str(origin.get("repo", "")).startswith("local-repo/")
    )
    entry.setdefault("video_name", slug)
    entry.setdefault("status", "verified_in_repo")
    entry.setdefault("source", f"https://github.com/{external_repo}")
    entry.setdefault("notes", "Strict v2 synchronization fixture.")
    entry.setdefault("sync_mode", entry["origins"][0]["sync_mode"])
    entry.setdefault(
        "managed_files",
        [
            {
                "path": entry["repo_skill"],
                "sha256": hashlib.sha256(content).hexdigest(),
                "owner": slug,
                "mode": "100644",
            }
        ],
    )
    for origin in entry["origins"]:
        origin.setdefault("path", origin.get("artifacts", [{}])[0].get("source"))
        origin.setdefault(
            "license",
            None if str(origin.get("repo", "")).startswith("local-repo/") else "MIT",
        )
        tracking = origin.setdefault("tracking", {})
        tracking.setdefault(
            "channel",
            "local"
            if str(origin.get("repo", "")).startswith("local-repo/")
            else "default_branch",
        )
        tracking.setdefault("ref", "local" if tracking["channel"] == "local" else "main")
        if not isinstance(tracking.get("resolved_commit"), str) or len(
            tracking["resolved_commit"]
        ) not in {40, 64}:
            tracking["resolved_commit"] = "a" * 40
        if not isinstance(tracking.get("path_commit"), str) or len(
            tracking["path_commit"]
        ) not in {40, 64}:
            tracking["path_commit"] = "b" * 40
        tracking.setdefault(
            "content_sha256", hashlib.sha256(content).hexdigest()
        )
        tracking.setdefault("last_checked_at", "2026-01-01")
        tracking.setdefault("last_synced_at", "2026-01-01")
    external = next(
        origin
        for origin in entry["origins"]
        if not str(origin.get("repo", "")).startswith("local-repo/")
    )
    tracking = external["tracking"]
    entry.setdefault(
        "upstream",
        {
            "repo": external["repo"],
            "path": external["path"],
            "ref": tracking["ref"],
            "sync_mode": external["sync_mode"],
            "last_checked_at": tracking["last_checked_at"],
            "last_synced_at": tracking["last_synced_at"],
            "last_synced_commit": tracking["resolved_commit"],
            "path_commit": tracking["path_commit"],
        },
    )
    return entry


def load_module():
    spec = importlib.util.spec_from_file_location("sync_upstream", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SyncUpstreamTests(unittest.TestCase):
    @staticmethod
    def _open_fd_count() -> int:
        fd_root = Path("/dev/fd")
        if not fd_root.exists():
            raise unittest.SkipTest("/dev/fd is unavailable")
        return len(list(fd_root.iterdir()))

    @staticmethod
    def _install_post_stage_metadata_attack(
        module,
        *,
        root: Path,
        replacement_kind: str,
        selector,
    ):
        """Replace a staged name on its first caller-side metadata check."""
        real_secure = module._secure_temporary_metadata
        call_counts: dict[Path, int] = {}
        foreign: list[Path] = []
        sentinel = b"foreign-post-stage-occupant"
        symlink_target = root / "foreign-target"
        symlink_target.write_bytes(sentinel)

        def attack(path, directory_fd):
            candidate = Path(path)
            if selector(candidate):
                call_counts[candidate] = call_counts.get(candidate, 0) + 1
                # The stage helper performs two pinned checks.  The third call
                # is the first fallible caller-side check after it returns.
                if call_counts[candidate] == 3:
                    candidate.unlink()
                    if replacement_kind == "regular":
                        candidate.write_bytes(sentinel)
                    elif replacement_kind == "symlink":
                        candidate.symlink_to(symlink_target)
                    elif replacement_kind != "missing":
                        raise AssertionError(
                            f"unknown replacement kind: {replacement_kind}"
                        )
                    foreign.append(candidate)
            return real_secure(path, directory_fd)

        module._secure_temporary_metadata = attack
        return real_secure, foreign, sentinel

    def _assert_foreign_stage_state(
        self,
        foreign: list[Path],
        replacement_kind: str,
        sentinel: bytes,
    ) -> None:
        self.assertEqual(1, len(foreign))
        path = foreign[0]
        if replacement_kind == "missing":
            self.assertFalse(path.exists())
            self.assertFalse(path.is_symlink())
            return
        self.assertTrue(path.exists())
        if replacement_kind == "symlink":
            self.assertTrue(path.is_symlink())
        else:
            self.assertEqual(sentinel, path.read_bytes())
        path.unlink()

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
            root = Path(tmpdir)
            module.REPO_ROOT = root
            mapping = root / "source.skills.json"
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
            root = Path(tmpdir)
            module.REPO_ROOT = root
            mapping = root / "source.skills.json"
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
            module.REPO_ROOT = root
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

    def test_legacy_apply_uses_global_mapping_skill_lock_order(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            mapping = root / "source.skills.json"
            skill = self._mapping_fixture(mapping)
            local_path = (
                root
                / "skills"
                / "ai-workflow"
                / "demo-skill"
                / "SKILL.md"
            )
            local_path.parent.mkdir(parents=True)
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
            events: list[str] = []

            @contextmanager
            def global_guard(path):
                self.assertEqual(root, path)
                events.append("global-enter")
                yield object()
                events.append("global-exit")

            @contextmanager
            def mapping_lock(path):
                self.assertEqual(mapping, path)
                events.append("mapping-enter")
                yield
                events.append("mapping-exit")

            @contextmanager
            def skill_lock(repo_root, skill_root, *, timeout):
                self.assertEqual(root, repo_root)
                self.assertEqual(
                    "skills/ai-workflow/demo-skill",
                    skill_root,
                )
                self.assertEqual(10.0, timeout)
                events.append("skill-enter")
                yield
                events.append("skill-exit")

            original_global = module.durable_batch_lock_and_recover
            original_mapping = module.mapping_advisory_lock
            original_engine = module._load_artifact_engine
            original_aux = module.sync_github_auxiliary_files
            module.durable_batch_lock_and_recover = global_guard
            module.mapping_advisory_lock = mapping_lock
            module._load_artifact_engine = lambda: SimpleNamespace(
                skill_advisory_lock=skill_lock
            )
            module.sync_github_auxiliary_files = lambda *_args: 0
            try:
                self.assertEqual(0, module.apply_legacy_update(update, None))
            finally:
                module.durable_batch_lock_and_recover = original_global
                module.mapping_advisory_lock = original_mapping
                module._load_artifact_engine = original_engine
                module.sync_github_auxiliary_files = original_aux

            self.assertEqual(
                [
                    "global-enter",
                    "mapping-enter",
                    "skill-enter",
                    "skill-exit",
                    "mapping-exit",
                    "global-exit",
                ],
                events,
            )
            self.assertIn("# New", local_path.read_text(encoding="utf-8"))

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

    def test_v2_apply_rejects_incomplete_mapping_without_any_write(self):
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

            self.assertEqual(1, exit_code)
            self.assertIn("FAILED", output)
            self.assertEqual(mapping_before, mapping.read_bytes())
            self.assertEqual(skill_before, local_path.read_bytes())

    def test_v2_record_check_rejects_incomplete_observation_without_write(self):
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

            self.assertEqual(1, exit_code)
            self.assertIn("Failed to record check atomically", output)
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

    def test_real_v2_mapping_scope_includes_active_external_snapshots(self):
        module = load_module()

        loaded = module.load_skills_with_upstream()
        snapshots = [
            skill for skill in loaded if skill.get("kind") == "snapshot"
        ]

        self.assertEqual(149, len(loaded))
        self.assertEqual(25, len(snapshots))
        self.assertTrue(
            all(skill.get("expected_skip_reason") for skill in snapshots)
        )

    def test_snapshot_is_expected_skipped_without_network(self):
        module = load_module()
        module._ACTIVE_ARTIFACT_PROVIDER = SimpleNamespace(
            resolve_tracking=lambda *_args: self.fail(
                "snapshot must not resolve a network ref"
            )
        )
        skill = {
            "name": "archived-value",
            "schema_version": 2,
            "kind": "snapshot",
            "repo": "owner/repo",
            "expected_skip_reason": "licensed snapshot",
        }

        result = module.check_upstream_changes(skill, None)

        self.assertEqual("expected_skipped", result["changes"])
        self.assertEqual("licensed snapshot", result["reason"])

    def test_snapshot_only_main_keeps_token_and_provider_fully_lazy(self):
        module = load_module()
        skill = {
            "name": "archived-value",
            "schema_version": 2,
            "kind": "snapshot",
            "repo": "owner/repo",
            "source": "github:owner/repo",
            "expected_skip_reason": "licensed snapshot",
        }
        original_load = module.load_skills_with_upstream
        original_resolve = module.resolve_github_token
        original_provider = module.GitHubArtifactProvider
        module.load_skills_with_upstream = lambda **_kwargs: [skill]
        module.resolve_github_token = lambda: self.fail(
            "snapshot-only run must not resolve credentials"
        )
        module.GitHubArtifactProvider = lambda *_args, **_kwargs: self.fail(
            "snapshot-only run must not construct a provider"
        )
        try:
            with redirect_stdout(io.StringIO()):
                exit_code = module.main(["--check-only"])
        finally:
            module.load_skills_with_upstream = original_load
            module.resolve_github_token = original_resolve
            module.GitHubArtifactProvider = original_provider

        self.assertEqual(0, exit_code)

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
                                "sync_mode": "monitor",
                                "repo_skill": repo_skill,
                                "origins": [
                                    {
                                        "repo": "trusted/owner",
                                        "path": None,
                                        "license": "MIT",
                                        "sync_mode": "monitor",
                                        "artifacts": [
                                            {
                                                "type": "directory",
                                                "source": "upstream/demo-skill",
                                                "target": "skills/ai-workflow/demo-skill",
                                            }
                                        ],
                                        "tracking": {
                                            "channel": "default_branch",
                                            "ref": "main",
                                            "resolved_commit": "a" * 40,
                                            "path_commit": "b" * 40,
                                            "content_sha256": hashlib.sha256(
                                                local_path.read_bytes()
                                            ).hexdigest(),
                                            "last_checked_at": "2026-01-01",
                                            "last_synced_at": "2026-01-01",
                                        },
                                    }
                                ],
                                "managed_files": [
                                    {
                                        "path": repo_skill,
                                        "sha256": hashlib.sha256(
                                            local_path.read_bytes()
                                        ).hexdigest(),
                                        "owner": "demo-skill",
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
                                "sync_mode": "monitor",
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
                                        "license": "MIT",
                                        "sync_mode": "monitor",
                                        "artifacts": [
                                            {
                                                "source": "canonical/SKILL.md",
                                                "target": "skills/ai-workflow/demo-skill/SKILL.md",
                                            }
                                        ],
                                        "tracking": {
                                            "channel": "default_branch",
                                            "ref": "main",
                                            "resolved_commit": "a" * 40,
                                            "path_commit": "b" * 40,
                                            "content_sha256": hashlib.sha256(
                                                local_path.read_bytes()
                                            ).hexdigest(),
                                            "last_checked_at": "2026-01-01",
                                            "last_synced_at": "2026-01-01",
                                        },
                                    }
                                ],
                                "managed_files": [
                                    {
                                        "path": "skills/ai-workflow/demo-skill/SKILL.md",
                                        "sha256": hashlib.sha256(
                                            local_path.read_bytes()
                                        ).hexdigest(),
                                        "owner": "demo-skill",
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
            self.assertEqual("a" * 40, loaded[0]["last_synced_commit"])
            self.assertEqual("b" * 40, loaded[0]["path_commit"])
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
                                "sync_mode": "replace",
                                "repo_skill": "skills/ai-workflow/demo-skill/SKILL.md",
                                "upstream": {
                                    "repo": "attacker/legacy",
                                    "path": "payload/SKILL.md",
                                },
                                "origins": [
                                    {
                                        "repo": "trusted/owner",
                                        "path": "other/SKILL.md",
                                        "license": "MIT",
                                        "sync_mode": "replace",
                                        "artifacts": [
                                            {
                                                "source": "other/SKILL.md",
                                                "target": "skills/ai-workflow/other/SKILL.md",
                                            }
                                        ],
                                        "tracking": {
                                            "channel": "latest_release",
                                            "ref": "v1.0.0",
                                            "resolved_commit": "a" * 40,
                                            "path_commit": "b" * 40,
                                            "content_sha256": hashlib.sha256(
                                                local_path.read_bytes()
                                            ).hexdigest(),
                                            "last_checked_at": "2026-01-01",
                                            "last_synced_at": "2026-01-01",
                                        },
                                    }
                                ],
                                "managed_files": [
                                    {
                                        "path": "skills/ai-workflow/demo-skill/SKILL.md",
                                        "sha256": hashlib.sha256(
                                            local_path.read_bytes()
                                        ).hexdigest(),
                                        "owner": "demo-skill",
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
            self.assertIn("exactly one artifact owner", loaded[0]["load_error"])
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
                "license": "MIT",
                "sync_mode": "replace",
                "artifacts": [
                    {"source": f"{name}/SKILL.md", "target": repo_skill}
                ],
                "tracking": {
                    "channel": "latest_release",
                    "ref": "v1.0.0",
                    "resolved_commit": "a" * 40,
                    "path_commit": "b" * 40,
                    "content_sha256": hashlib.sha256(
                        local_path.read_bytes()
                    ).hexdigest(),
                    "last_checked_at": "2026-01-01",
                    "last_synced_at": "2026-01-01",
                },
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
                                "sync_mode": "replace",
                                "repo_skill": repo_skill,
                                "origins": [owner("one"), owner("two")],
                                "managed_files": [
                                    {
                                        "path": repo_skill,
                                        "sha256": hashlib.sha256(
                                            local_path.read_bytes()
                                        ).hexdigest(),
                                        "owner": "demo-skill",
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

        self.assertIn("description: New upstream description.", merged)
        self.assertIn('version: "1.2.4"', merged)
        self.assertIn("upstream_slug: demo-skill", merged)
        self.assertIn("# New Body", merged)
        self.assertNotIn("# Old Body", merged)
        self.assertIn("LOCAL-QUALITY-SUPPLEMENT:START", merged)
        self.assertIn("Preserve this reviewed local rule.", merged)

    def test_frontmatter_authority_detects_and_applies_permission_revocation(self):
        module = load_module()
        local = textwrap.dedent(
            """\
            ---
            name: demo
            description: Upstream-owned description.
            zh_description: 本地中文说明
            version: "1.2.3"
            author: local-curator
            source: github:owner/repo
            source_url: https://github.com/owner/repo
            license: MIT
            tags: [demo]
            created_at: "2026-01-01"
            updated_at: "2026-01-01"
            quality: 4
            complexity: advanced
            upstream_slug: upstream-demo
            allowed-tools: Bash Read
            compatibility: old-runtime
            disable-model-invocation: true
            user-invocable: true
            argument-hint: old-argument
            ---
            # Same body
            """
        )
        upstream = textwrap.dedent(
            """\
            ---
            name: demo
            description: Upstream-owned description.
            source: github:attacker/ignored
            version: "99.0.0"
            compatibility: new-runtime
            disable-model-invocation: false
            user-invocable: false
            argument-hint: new-argument
            ---
            # Same body
            """
        )

        self.assertFalse(
            module._main_artifact_equal({}, local.encode(), upstream.encode())
        )
        merged = module.merge_frontmatter(local, upstream)

        self.assertNotIn("allowed-tools:", merged)
        self.assertIn("compatibility: new-runtime", merged)
        self.assertIn("disable-model-invocation: false", merged)
        self.assertIn("user-invocable: false", merged)
        self.assertIn("argument-hint: new-argument", merged)
        self.assertIn("source: github:owner/repo", merged)
        self.assertNotIn("github:attacker/ignored", merged)
        self.assertEqual("本地中文说明", module.parse_frontmatter(merged)["zh_description"])
        self.assertIn("upstream_slug: upstream-demo", merged)
        self.assertIn('version: "1.2.4"', merged)

        local_authority_only = local.replace(
            "source: github:owner/repo",
            "source: github:local/changed",
        ).replace('version: "1.2.3"', 'version: "7.8.9"')
        self.assertTrue(
            module._main_artifact_equal(
                {},
                local.encode(),
                local_authority_only.encode(),
            )
        )

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
            root = Path(tmpdir)
            module.REPO_ROOT = root
            mapping = root / "source.skills.json"
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

    def test_github_provider_resolves_stable_release_and_fetches_binary_directory_once(self):
        commit = "c" * 40
        skill_data = b"# Skill\n"
        binary_data = b"\x00\xff\x10"
        skill_blob = git_blob_sha(skill_data)
        binary_blob = git_blob_sha(binary_data)
        calls = {}

        def fake_api(url):
            calls[url] = calls.get(url, 0) + 1
            if url.endswith("/releases/latest"):
                return {
                    "tag_name": "v2.0.0",
                    "draft": False,
                    "prerelease": False,
                }
            if url.endswith("/commits/v2.0.0"):
                return {"sha": commit}
            if url.endswith(f"/git/trees/{commit}?recursive=1"):
                return {
                    "truncated": False,
                    "tree": [
                        {
                            "path": "package/SKILL.md",
                            "type": "blob",
                            "mode": "100644",
                            "sha": skill_blob,
                        },
                        {
                            "path": "package/assets/logo.bin",
                            "type": "blob",
                            "mode": "100755",
                            "sha": binary_blob,
                        },
                    ],
                }
            if url.endswith(f"/git/blobs/{skill_blob}"):
                return {
                    "encoding": "base64",
                    "content": base64.b64encode(skill_data).decode(),
                    "size": len(skill_data),
                }
            if url.endswith(f"/git/blobs/{binary_blob}"):
                return {
                    "encoding": "base64",
                    "content": base64.b64encode(binary_data).decode(),
                    "size": len(binary_data),
                }
            raise AssertionError(url)

        provider = GitHubArtifactProvider(api_get=fake_api)
        tracking = {"channel": "latest_release", "ref": "latest"}
        artifacts = [
            {
                "type": "file",
                "source": "package/SKILL.md",
                "target": "skills/ai/demo/SKILL.md",
            },
            {
                "type": "directory",
                "source": "package/assets",
                "target": "skills/ai/demo/static",
            },
        ]

        first = provider.fetch_artifacts("owner/repo", tracking, artifacts)
        second = provider.fetch_artifacts("owner/repo", tracking, artifacts)

        self.assertEqual("v2.0.0", first.resolved.ref)
        self.assertEqual(commit, first.resolved.commit)
        self.assertEqual(
            b"\x00\xff\x10",
            first.files["skills/ai/demo/static/logo.bin"],
        )
        self.assertEqual(
            {
                "skills/ai/demo/SKILL.md": "100644",
                "skills/ai/demo/static/logo.bin": "100755",
            },
            first.modes,
        )
        self.assertEqual(first, second)
        self.assertTrue(all(count == 1 for count in calls.values()), calls)

    def test_github_provider_rejects_symlink_mode_for_file_artifact(self):
        commit = "c" * 40
        symlink_payload = b"../outside"
        symlink_blob = git_blob_sha(symlink_payload)

        def fake_api(url):
            if url.endswith(f"/commits/{commit}"):
                return {"sha": commit}
            if url.endswith(f"/git/trees/{commit}?recursive=1"):
                return {
                    "truncated": False,
                    "tree": [
                        {
                            "path": "package/SKILL.md",
                            "type": "blob",
                            "mode": "120000",
                            "sha": symlink_blob,
                            "size": len(symlink_payload),
                        }
                    ],
                }
            raise AssertionError(url)

        provider = GitHubArtifactProvider(api_get=fake_api)
        with self.assertRaisesRegex(
            GitHubUnavailable,
            "requires manual review.*120000",
        ):
            provider.fetch_artifacts(
                "owner/repo",
                {"channel": "fixed_ref", "ref": commit},
                [
                    {
                        "source": "package/SKILL.md",
                        "target": "skills/ai/demo/SKILL.md",
                    }
                ],
            )

    def test_github_provider_allows_unrelated_symlink_outside_declared_source(self):
        commit = "c" * 40
        skill_payload = b"# Security Pen Testing\n"
        skill_blob = git_blob_sha(skill_payload)
        unrelated_symlink_payload = b"../../../engineering-team/skills/a11y-audit"
        unrelated_symlink_blob = git_blob_sha(unrelated_symlink_payload)
        source = "engineering-team/skills/security-pen-testing/SKILL.md"

        def fake_api(url):
            if url.endswith(f"/commits/{commit}"):
                return {"sha": commit}
            if url.endswith(f"/git/trees/{commit}?recursive=1"):
                return {
                    "truncated": False,
                    "tree": [
                        {
                            "path": source,
                            "type": "blob",
                            "mode": "100644",
                            "sha": skill_blob,
                            "size": len(skill_payload),
                        },
                        {
                            "path": ".codex/skills/a11y-audit",
                            "type": "blob",
                            "mode": "120000",
                            "sha": unrelated_symlink_blob,
                            "size": len(unrelated_symlink_payload),
                        },
                    ],
                }
            if url.endswith(f"/git/blobs/{skill_blob}"):
                return {
                    "encoding": "base64",
                    "content": base64.b64encode(skill_payload).decode(),
                    "size": len(skill_payload),
                }
            raise AssertionError(url)

        provider = GitHubArtifactProvider(api_get=fake_api)
        inventory = provider.fetch_artifacts(
            "alirezarezvani/claude-skills",
            {"channel": "fixed_ref", "ref": commit},
            [
                {
                    "source": source,
                    "target": (
                        "skills/security-and-reliability/"
                        "security-pen-testing/SKILL.md"
                    ),
                }
            ],
        )

        self.assertEqual(
            skill_payload,
            inventory.files[
                "skills/security-and-reliability/"
                "security-pen-testing/SKILL.md"
            ],
        )

    def test_github_provider_directory_fails_closed_on_special_or_unknown_entry(self):
        commit = "c" * 40
        regular_payload = b"regular"
        regular_blob = git_blob_sha(regular_payload)
        cases = (
            ("symlink", "blob", "120000"),
            ("gitlink", "commit", "160000"),
            ("unknown-mode", "blob", "100600"),
            ("missing-mode", "blob", None),
            ("unknown-type", "mystery", "100644"),
        )

        for name, item_type, mode in cases:
            with self.subTest(name=name):
                def fake_api(url):
                    if url.endswith(f"/commits/{commit}"):
                        return {"sha": commit}
                    if url.endswith(f"/git/trees/{commit}?recursive=1"):
                        return {
                            "truncated": False,
                            "tree": [
                                {
                                    "path": "package/assets/regular.bin",
                                    "type": "blob",
                                    "mode": "100644",
                                    "sha": regular_blob,
                                    "size": len(regular_payload),
                                },
                                {
                                    "path": f"package/assets/{name}",
                                    "type": item_type,
                                    "mode": mode,
                                    "sha": "d" * 40,
                                },
                            ],
                        }
                    raise AssertionError(url)

                provider = GitHubArtifactProvider(api_get=fake_api)
                with self.assertRaisesRegex(
                    GitHubUnavailable,
                    "requires manual review",
                ):
                    provider.fetch_artifacts(
                        "owner/repo",
                        {"channel": "fixed_ref", "ref": commit},
                        [
                            {
                                "type": "directory",
                                "source": "package/assets",
                                "target": "skills/ai/demo/assets",
                            }
                        ],
                    )

    def test_github_provider_fixed_ref_requires_full_commit(self):
        provider = GitHubArtifactProvider(
            api_get=lambda _url: self.fail("short fixed ref must not hit network")
        )
        with self.assertRaises(GitHubUnavailable):
            provider.resolve_tracking(
                "owner/repo",
                {"channel": "fixed_ref", "ref": "v1.0.0"},
            )

    def test_github_provider_truncated_tree_falls_back_to_nonrecursive_git_trees(self):
        commit = "c" * 40
        blob_data = b"# Skill\n"
        blob = git_blob_sha(blob_data)

        def fake_api(url):
            if url.endswith(f"/commits/{commit}"):
                return {"sha": commit}
            if url.endswith(f"/git/trees/{commit}?recursive=1"):
                return {"truncated": True, "tree": []}
            if url.endswith(f"/git/trees/{commit}"):
                return {
                    "truncated": False,
                    "tree": [
                        {
                            "path": "package",
                            "type": "tree",
                            "mode": "040000",
                            "sha": "d" * 40,
                        }
                    ],
                }
            if url.endswith(f"/git/trees/{'d' * 40}"):
                return {
                    "truncated": False,
                    "tree": [
                        {
                            "path": "SKILL.md",
                            "type": "blob",
                            "mode": "100644",
                            "sha": blob,
                            "size": len(blob_data),
                        }
                    ],
                }
            if url.endswith(f"/git/blobs/{blob}"):
                return {
                    "encoding": "base64",
                    "content": base64.b64encode(blob_data).decode(),
                    "size": len(blob_data),
                }
            raise AssertionError(url)

        provider = GitHubArtifactProvider(api_get=fake_api)
        inventory = provider.fetch_artifacts(
            "owner/repo",
            {"channel": "fixed_ref", "ref": commit},
            [
                {
                    "source": "package/SKILL.md",
                    "target": "skills/ai/demo/SKILL.md",
                }
            ],
        )

        self.assertEqual(
            b"# Skill\n", inventory.files["skills/ai/demo/SKILL.md"]
        )
        self.assertEqual(
            "100644", inventory.modes["skills/ai/demo/SKILL.md"]
        )

    def test_github_provider_truncated_walk_preserves_but_does_not_descend_special_objects(self):
        commit = "c" * 40
        package_tree = "d" * 40
        blob_data = b"# Skill\n"
        blob = git_blob_sha(blob_data)

        def fake_api(url):
            if url.endswith(f"/commits/{commit}"):
                return {"sha": commit}
            if url.endswith(f"/git/trees/{commit}?recursive=1"):
                return {"truncated": True, "tree": []}
            if url.endswith(f"/git/trees/{commit}"):
                return {
                    "truncated": False,
                    "tree": [
                        {
                            "path": "package",
                            "type": "tree",
                            "mode": "040000",
                            "sha": package_tree,
                        },
                        {
                            "path": "unrelated-symlink",
                            "type": "blob",
                            "mode": "120000",
                            "sha": "e" * 40,
                        },
                        {
                            "path": "unrelated-submodule",
                            "type": "commit",
                            "mode": "160000",
                            "sha": "f" * 40,
                        },
                    ],
                }
            if url.endswith(f"/git/trees/{package_tree}"):
                return {
                    "truncated": False,
                    "tree": [
                        {
                            "path": "SKILL.md",
                            "type": "blob",
                            "mode": "100644",
                            "sha": blob,
                            "size": len(blob_data),
                        }
                    ],
                }
            if url.endswith(f"/git/blobs/{blob}"):
                return {
                    "encoding": "base64",
                    "content": base64.b64encode(blob_data).decode(),
                    "size": len(blob_data),
                }
            raise AssertionError(
                f"special Git objects must not be traversed or fetched: {url}"
            )

        provider = GitHubArtifactProvider(api_get=fake_api)
        inventory = provider.fetch_artifacts(
            "owner/repo",
            {"channel": "fixed_ref", "ref": commit},
            [
                {
                    "source": "package/SKILL.md",
                    "target": "skills/ai/demo/SKILL.md",
                }
            ],
        )

        self.assertEqual(
            b"# Skill\n", inventory.files["skills/ai/demo/SKILL.md"]
        )
        tree = provider.tree("owner/repo", commit)
        self.assertEqual("120000", tree["unrelated-symlink"]["mode"])
        self.assertEqual("160000", tree["unrelated-submodule"]["mode"])

    def test_github_provider_nested_truncated_tree_fails_closed(self):
        commit = "c" * 40
        child = "d" * 40

        def fake_api(url):
            if url.endswith(f"/commits/{commit}"):
                return {"sha": commit}
            if url.endswith(f"/git/trees/{commit}?recursive=1"):
                return {"truncated": True, "tree": []}
            if url.endswith(f"/git/trees/{commit}"):
                return {
                    "truncated": False,
                    "tree": [
                        {
                            "path": "package",
                            "type": "tree",
                            "mode": "040000",
                            "sha": child,
                        }
                    ],
                }
            if url.endswith(f"/git/trees/{child}"):
                return {"truncated": True, "tree": []}
            raise AssertionError(url)

        provider = GitHubArtifactProvider(api_get=fake_api)
        with self.assertRaisesRegex(
            GitHubUnavailable, "complete non-recursive Git tree unavailable"
        ):
            provider.tree("owner/repo", commit)

    def test_github_provider_rejects_unsafe_identifiers_and_encodes_path_query(self):
        seen = []

        def fake_api(url):
            seen.append(url)
            if "/commits?" in url:
                return [{"sha": "c" * 40}]
            return {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
            }

        provider = GitHubArtifactProvider(api_get=fake_api)
        with self.assertRaisesRegex(GitHubUnavailable, "repository slug"):
            provider.resolve_commit("owner/repo/extra", "main")
        with self.assertRaisesRegex(GitHubUnavailable, "safe paths"):
            provider.fetch_artifacts(
                "owner/repo",
                {"channel": "fixed_ref", "ref": "a" * 40},
                [{"source": "../SKILL.md", "target": "skills/demo/SKILL.md"}],
            )

        with self.assertRaisesRegex(
            GitHubUnavailable, "base and head must be full commit"
        ):
            provider.compare("owner/repo", "base/branch", "head?value")
        provider.compare("owner/repo", "a" * 40, "b" * 40)
        self.assertTrue(
            seen[-1].endswith(
                f"/compare/{'a' * 40}...{'b' * 40}"
            ),
            seen[-1],
        )
        with self.assertRaisesRegex(
            GitHubUnavailable, "query ref must be a full commit"
        ):
            provider.path_commit("owner/repo", "main", "path/SKILL.md")
        self.assertEqual(
            "c" * 40,
            provider.path_commit(
                "owner/repo",
                "d" * 40,
                "dir/space name.md?x",
            ),
        )
        self.assertIn(
            f"sha={'d' * 40}&path=dir%2Fspace+name.md%3Fx&per_page=1",
            seen[-1],
        )

    def test_github_provider_strict_blob_base64_size_and_hash_validation(self):
        valid = b"binary\x00payload"
        valid_sha = git_blob_sha(valid)
        cases = (
            (
                "base64",
                valid_sha,
                {
                    "encoding": "base64",
                    "content": "@@@=",
                    "size": len(valid),
                },
                "invalid base64",
            ),
            (
                "size",
                valid_sha,
                {
                    "encoding": "base64",
                    "content": base64.b64encode(valid).decode(),
                    "size": len(valid) + 1,
                },
                "size mismatch",
            ),
            (
                "hash",
                "a" * 40,
                {
                    "encoding": "base64",
                    "content": base64.b64encode(valid).decode(),
                    "size": len(valid),
                },
                "hash mismatch",
            ),
        )
        for label, sha, response, message in cases:
            with self.subTest(case=label):
                provider = GitHubArtifactProvider(
                    api_get=lambda _url, response=response: response
                )
                with self.assertRaisesRegex(GitHubUnavailable, message):
                    provider.blob("owner/repo", sha)

        whitespace_content = "\n ".join(
            [
                base64.b64encode(valid).decode()[:8],
                base64.b64encode(valid).decode()[8:],
            ]
        )
        provider = GitHubArtifactProvider(
            api_get=lambda _url: {
                "encoding": "base64",
                "content": whitespace_content,
                "size": len(valid),
            }
        )
        self.assertEqual(valid, provider.blob("owner/repo", valid_sha))

    def test_commit_bound_license_evidence_is_binary_strict_and_text_classified(self):
        # Graphify's NOASSERTION license bytes normalize exactly to GitHub's
        # canonical Apache-2.0 template.
        apache = (
            REPO_ROOT
            / "skills"
            / "developer-engineering"
            / "mcp-builder"
            / "LICENSE.txt"
        ).read_bytes()
        apache_sha = git_blob_sha(apache)
        commit = "a" * 40
        seen = []

        def response(**overrides):
            value = {
                "path": "LICENSE",
                "sha": apache_sha,
                "size": len(apache),
                "encoding": "base64",
                "content": base64.b64encode(apache).decode("ascii"),
                "license": {"spdx_id": "NOASSERTION"},
            }
            value.update(overrides)
            return value

        def fake_api(url):
            seen.append(url)
            return response()

        provider = GitHubArtifactProvider(api_get=fake_api)
        evidence = provider.license_evidence("owner/repo", commit)

        self.assertTrue(
            seen[-1].endswith(f"/license?ref={commit}"),
            seen[-1],
        )
        self.assertEqual("LICENSE", evidence.path)
        self.assertEqual(apache_sha, evidence.blob_sha)
        self.assertEqual(hashlib.sha256(apache).hexdigest(), evidence.content_sha256)
        self.assertEqual(("Apache-2.0",), evidence.spdx_candidates)
        self.assertEqual("NOASSERTION", evidence.api_spdx)
        self.assertEqual(evidence, provider.license_evidence("owner/repo", commit))
        self.assertEqual(1, len(seen))

        invalid_cases = (
            ("path", response(path="../LICENSE"), "license path"),
            ("base64", response(content="@@@="), "base64 license"),
            ("size", response(size=len(apache) + 1), "size mismatch"),
            ("hash", response(sha="b" * 40), "blob hash mismatch"),
        )
        for label, payload, expected in invalid_cases:
            with self.subTest(case=label):
                strict_provider = GitHubArtifactProvider(
                    api_get=lambda _url, payload=payload: payload
                )
                with self.assertRaisesRegex(GitHubUnavailable, expected):
                    strict_provider.license_evidence("owner/repo", commit)

        with self.assertRaisesRegex(
            GitHubUnavailable, "full immutable commit"
        ):
            provider.license_evidence("owner/repo", "main")

        spoofed = (
            b"This work is not licensed under Apache License Version 2.0.",
            (
                b"Permission is hereby granted, free of charge, to any person "
                b"obtaining a copy"
            ),
            (
                b"Redistribution and use in source and binary forms are "
                b"permitted, including the forbidden advertising clause."
            ),
        )
        for raw in spoofed:
            with self.subTest(spoof=raw[:24]):
                self.assertEqual(
                    (),
                    GitHubArtifactProvider._detect_license_spdx(raw),
                )

    def test_license_evidence_requires_unique_stable_declared_spdx(self):
        module = load_module()
        evidence = mock_license_evidence(
            spdx="Apache-2.0",
            api_spdx="NOASSERTION",
        )
        checkpoint, error = module._validate_license_evidence(
            {"license": "Apache-2.0", "tracking": {}},
            evidence,
        )
        self.assertIsNone(error)
        self.assertEqual("Apache-2.0", checkpoint["spdx"])
        public_checkpoint, public_error = module.validate_license_evidence(
            "Apache-2.0",
            evidence,
        )
        self.assertIsNone(public_error)
        self.assertEqual(
            module.license_checkpoint(evidence),
            public_checkpoint,
        )

        _checkpoint, mismatch = module._validate_license_evidence(
            {"license": "MIT", "tracking": {}},
            evidence,
        )
        self.assertIn("does not match origin.license", mismatch)

        ambiguous = LicenseEvidence(
            path="LICENSE",
            blob_sha="e" * 40,
            content_sha256="f" * 64,
            resolved_commit="b" * 40,
            spdx_candidates=("Apache-2.0", "MIT"),
            api_spdx="NOASSERTION",
        )
        _checkpoint, ambiguity = module._validate_license_evidence(
            {"license": "Apache-2.0", "tracking": {}},
            ambiguous,
        )
        self.assertIn("2 canonical SPDX matches", ambiguity)

        explicit_api = LicenseEvidence(
            path="LICENSE",
            blob_sha="e" * 40,
            content_sha256="f" * 64,
            resolved_commit="b" * 40,
            spdx_candidates=(),
            api_spdx="MIT",
        )
        explicit_checkpoint, explicit_error = (
            module.validate_license_evidence("MIT", explicit_api)
        )
        self.assertIsNone(explicit_error)
        self.assertEqual("MIT", explicit_checkpoint["spdx"])

        previous = mock_license_checkpoint(
            spdx="Apache-2.0",
            api_spdx="NOASSERTION",
        )
        previous["content_sha256"] = "0" * 64
        _checkpoint, changed = module._validate_license_evidence(
            {
                "license": "Apache-2.0",
                "tracking": {"license_checkpoint": previous},
            },
            evidence,
        )
        self.assertIn("evidence changed", changed)

    def test_v2_license_checkpoint_rejects_api_spdx_conflict(self):
        module = load_module()
        content = external_skill_content("demo", "owner/repo")
        entry = complete_v2_entry(
            {
                "normalized_slug": "demo",
                "kind": "overlay",
                "sync_mode": "monitor",
                "repo_skill": "skills/ai-workflow/demo/SKILL.md",
                "origins": [
                    {
                        "repo": "owner/repo",
                        "path": "upstream/SKILL.md",
                        "license": "MIT",
                        "sync_mode": "monitor",
                        "artifacts": [
                            {
                                "source": "upstream/SKILL.md",
                                "target": (
                                    "skills/ai-workflow/demo/SKILL.md"
                                ),
                                "type": "file",
                            }
                        ],
                    }
                ],
            },
            content,
        )
        tracking = entry["origins"][0]["tracking"]
        tracking["license_checkpoint"] = mock_license_checkpoint(
            tracking["resolved_commit"],
            spdx="MIT",
            api_spdx="Apache-2.0",
        )

        errors = module._v2_sync_entry_errors(entry)

        self.assertTrue(
            any("api_spdx conflicts" in error for error in errors),
            errors,
        )

    def test_v2_monitor_same_reviewed_checkpoint_ignores_curated_divergence(self):
        for channel, sync_mode in (
            ("default_branch", "replace"),
            ("canary", "replace"),
            ("fixed_ref", "monitor"),
            ("latest_release", "monitor"),
        ):
            with self.subTest(channel=channel, sync_mode=sync_mode):
                module = load_module()
                checkpoint = "a" * 40
                path_checkpoint = "c" * 40
                refreshed_path_checkpoint = "d" * 40
                upstream = b"# Upstream body intentionally differs\n"

                class Provider:
                    def resolve_tracking(self, _repo, _tracking):
                        return ResolvedRef(channel, "reviewed-ref", checkpoint)

                    def license_evidence(self, _repo, commit):
                        self.assertEqual(checkpoint, commit)
                        return mock_license_evidence(commit)

                    def compare(self, *_args):
                        self.fail(
                            "an exact reviewed checkpoint must not be compared"
                        )

                    def fetch_artifacts(self, _repo, _tracking, _artifacts):
                        return ArtifactInventory(
                            {
                                (
                                    "skills/ai-workflow/curated-demo/"
                                    "SKILL.md"
                                ): upstream
                            },
                            {"upstream/SKILL.md": "1" * 40},
                            {
                                (
                                    "skills/ai-workflow/curated-demo/"
                                    "SKILL.md"
                                ): "100644"
                            },
                            ResolvedRef(
                                channel, "reviewed-ref", checkpoint
                            ),
                        )

                    def path_commit(self, _repo, ref, path):
                        self.assertEqual(checkpoint, ref)
                        self.assertEqual("upstream", path)
                        return refreshed_path_checkpoint

                provider = Provider()
                provider.assertEqual = self.assertEqual
                provider.fail = self.fail
                module._ACTIVE_ARTIFACT_PROVIDER = provider
                skill = {
                    "schema_version": 2,
                    "name": "curated-demo",
                    "repo": "owner/repo",
                    "license": "MIT",
                    "repo_skill": "skills/ai-workflow/curated-demo/SKILL.md",
                    "upstream_path": "upstream/SKILL.md",
                    "origin_path": "upstream",
                    "tracking": {
                        "channel": channel,
                        "ref": "reviewed-ref",
                        "resolved_commit": checkpoint,
                        "path_commit": path_checkpoint,
                        "content_sha256": "1" * 64,
                        "license_checkpoint": mock_license_checkpoint(
                            checkpoint
                        ),
                    },
                    "sync_mode": sync_mode,
                    "last_synced_commit": checkpoint,
                    "artifacts": [
                        {
                            "source": "upstream/SKILL.md",
                            "target": (
                                "skills/ai-workflow/curated-demo/SKILL.md"
                            ),
                            "type": "file",
                        }
                    ],
                    "managed_files": [
                        {
                            "path": (
                                "skills/ai-workflow/curated-demo/SKILL.md"
                            ),
                            # This intentionally describes locally curated
                            # bytes rather than an upstream mirror.
                            "sha256": "2" * 64,
                        }
                    ],
                }

                result = module.check_upstream_changes(skill, None)

                self.assertEqual("none", result["changes"])
                self.assertEqual(checkpoint, result["current_commit"])
                self.assertEqual(
                    refreshed_path_checkpoint, result["path_commit"]
                )
                self.assertEqual("identical", result["relation"])
                self.assertEqual(
                    ["skills/ai-workflow/curated-demo/SKILL.md"],
                    result["changed_files"],
                )
                self.assertEqual(
                    mock_license_checkpoint(checkpoint),
                    result["license_evidence"],
                )
                self.assertIn("upstream_files", result)

    def test_v2_monitor_same_checkpoint_missing_artifact_is_unavailable(self):
        module = load_module()
        checkpoint = "a" * 40

        class Provider:
            def resolve_tracking(self, _repo, _tracking):
                return ResolvedRef("default_branch", "main", checkpoint)

            def license_evidence(self, _repo, commit):
                return mock_license_evidence(commit)

            def fetch_artifacts(self, *_args):
                raise module.ArtifactNotFound(["missing/SKILL.md"])

            def moved_candidates(self, *_args, **_kwargs):
                return {}

            def path_commit(self, *_args):
                self.fail("a missing artifact has no valid path checkpoint")

        provider = Provider()
        provider.fail = self.fail
        module._ACTIVE_ARTIFACT_PROVIDER = provider
        result = module.check_upstream_changes(
            {
                "schema_version": 2,
                "name": "curated-demo",
                "repo": "owner/repo",
                "license": "MIT",
                "repo_skill": (
                    "skills/ai-workflow/curated-demo/SKILL.md"
                ),
                "upstream_path": "missing/SKILL.md",
                "origin_path": "missing",
                "tracking": {
                    "channel": "default_branch",
                    "ref": "main",
                    "resolved_commit": checkpoint,
                    "path_commit": "c" * 40,
                    "content_sha256": "1" * 64,
                },
                "sync_mode": "monitor",
                "last_synced_commit": checkpoint,
                "artifacts": [
                    {
                        "source": "missing/SKILL.md",
                        "target": (
                            "skills/ai-workflow/curated-demo/SKILL.md"
                        ),
                        "type": "file",
                    }
                ],
            },
            None,
        )

        self.assertEqual("unavailable", result["changes"])
        self.assertIn("missing/SKILL.md", result["reason"])
        self.assertEqual({}, result["moved_candidates"])

    def test_v2_monitor_same_checkpoint_still_rejects_license_drift(self):
        module = load_module()
        checkpoint = "a" * 40

        class Provider:
            def resolve_tracking(self, _repo, _tracking):
                return ResolvedRef("default_branch", "main", checkpoint)

            def license_evidence(self, _repo, commit):
                evidence = mock_license_evidence(commit)
                return LicenseEvidence(
                    path=evidence.path,
                    blob_sha=evidence.blob_sha,
                    content_sha256="0" * 64,
                    resolved_commit=evidence.resolved_commit,
                    spdx_candidates=evidence.spdx_candidates,
                    api_spdx=evidence.api_spdx,
                )

            def fetch_artifacts(self, *_args):
                self.fail("license drift must fail before artifact fetch")

        provider = Provider()
        provider.fail = self.fail
        module._ACTIVE_ARTIFACT_PROVIDER = provider
        result = module.check_upstream_changes(
            {
                "schema_version": 2,
                "name": "curated-demo",
                "repo": "owner/repo",
                "license": "MIT",
                "tracking": {
                    "channel": "default_branch",
                    "ref": "main",
                    "resolved_commit": checkpoint,
                    "path_commit": "c" * 40,
                    "content_sha256": "1" * 64,
                    "license_checkpoint": mock_license_checkpoint(
                        checkpoint
                    ),
                },
                "sync_mode": "monitor",
                "last_synced_commit": checkpoint,
                "artifacts": [
                    {
                        "source": "upstream/SKILL.md",
                        "target": (
                            "skills/ai-workflow/curated-demo/SKILL.md"
                        ),
                        "type": "file",
                    }
                ],
            },
            None,
        )

        self.assertEqual("unavailable", result["changes"])
        self.assertIn("license evidence changed", result["reason"])

    def test_v2_monitor_different_checkpoint_always_requires_review(self):
        for relation_status in ("ahead", "diverged", "identical"):
            with self.subTest(relation=relation_status), tempfile.TemporaryDirectory() as tmpdir:
                module = load_module()
                root = Path(tmpdir)
                module.REPO_ROOT = root
                target = "skills/ai-workflow/curated-demo/SKILL.md"
                local = b"---\nname: curated-demo\n---\n# Same body\n"
                local_path = root / target
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_bytes(local)

                class Provider:
                    def resolve_tracking(self, _repo, _tracking):
                        return ResolvedRef(
                            "default_branch", "main", "b" * 40
                        )

                    def license_evidence(self, _repo, commit):
                        return mock_license_evidence(commit)

                    def compare(self, _repo, base, head):
                        self.assertEqual("a" * 40, base)
                        self.assertEqual("b" * 40, head)
                        return {
                            "status": relation_status,
                            "ahead_by": 1,
                            "behind_by": 0,
                        }

                    def fetch_artifacts(self, _repo, _tracking, _artifacts):
                        return ArtifactInventory(
                            {target: local},
                            {"upstream/SKILL.md": "1" * 40},
                            {target: "100644"},
                            ResolvedRef(
                                "default_branch", "main", "b" * 40
                            ),
                        )

                    def path_commit(self, _repo, ref, _path):
                        self.assertEqual("b" * 40, ref)
                        return "d" * 40

                provider = Provider()
                provider.assertEqual = self.assertEqual
                module._ACTIVE_ARTIFACT_PROVIDER = provider
                result = module.check_upstream_changes(
                    {
                        "schema_version": 2,
                        "name": "curated-demo",
                        "repo": "owner/repo",
                        "license": "MIT",
                        "repo_skill": target,
                        "upstream_path": "upstream/SKILL.md",
                        "origin_path": "upstream",
                        "tracking": {
                            "channel": "default_branch",
                            "ref": "main",
                            "resolved_commit": "a" * 40,
                            "path_commit": "c" * 40,
                            "content_sha256": hashlib.sha256(local).hexdigest(),
                            "license_checkpoint": mock_license_checkpoint(
                                "a" * 40
                            ),
                        },
                        "sync_mode": "monitor",
                        "last_synced_commit": "a" * 40,
                        "artifacts": [
                            {
                                "source": "upstream/SKILL.md",
                                "target": target,
                                "type": "file",
                            }
                        ],
                        "managed_files": [
                            {
                                "path": target,
                                "sha256": hashlib.sha256(local).hexdigest(),
                            }
                        ],
                    },
                    None,
                )

                self.assertEqual("monitor_review", result["changes"])
                self.assertEqual(relation_status, result["relation"])
                self.assertEqual([], result["changed_files"])
                self.assertEqual("d" * 40, result["path_commit"])

    def test_v2_sidecar_only_change_on_default_branch_requires_monitor_review(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            module.SKILLS_DIR = root / "skills"
            main_target = "skills/ai-workflow/demo/SKILL.md"
            side_target = "skills/ai-workflow/demo/references/guide.bin"
            for relative, raw in (
                (main_target, b"---\nname: demo\n---\n# Same\n"),
                (side_target, b"\x00old"),
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)

            class Provider:
                def resolve_tracking(self, _repo, _tracking):
                    return ResolvedRef("default_branch", "main", "b" * 40)

                def license_evidence(self, _repo, commit):
                    return mock_license_evidence(commit)

                def compare(self, *_args):
                    return {"status": "ahead", "ahead_by": 1, "behind_by": 0}

                def fetch_artifacts(self, _repo, _tracking, _artifacts):
                    return ArtifactInventory(
                        {
                            main_target: b"---\nname: demo\n---\n# Same\n",
                            side_target: b"\x00new",
                        },
                        {"upstream/SKILL.md": "1" * 40, "upstream/guide.bin": "2" * 40},
                        {
                            main_target: "100644",
                            side_target: "100644",
                        },
                        ResolvedRef("default_branch", "main", "b" * 40),
                    )

                def path_commit(self, _repo, ref, _path):
                    if ref != "b" * 40:
                        raise AssertionError("path query was not commit-pinned")
                    return "d" * 40

            module._ACTIVE_ARTIFACT_PROVIDER = Provider()
            skill = {
                "schema_version": 2,
                "name": "demo",
                "repo": "owner/repo",
                "license": "MIT",
                "repo_skill": main_target,
                "origin_path": "upstream",
                "tracking": {
                    "channel": "default_branch",
                    "ref": "main",
                    "resolved_commit": "a" * 40,
                    "path_commit": "a" * 40,
                    "content_sha256": "1" * 64,
                },
                "sync_mode": "monitor",
                "last_synced_commit": "a" * 40,
                "artifacts": [
                    {
                        "source": "upstream",
                        "target": "skills/ai-workflow/demo",
                        "type": "directory",
                    }
                ],
                "managed_files": [
                    {"path": main_target},
                    {"path": side_target},
                ],
            }

            result = module.check_upstream_changes(skill, None)

            self.assertEqual("monitor_review", result["changes"])
            self.assertEqual([side_target], result["changed_files"])
            self.assertEqual([], result["added_files"])
            self.assertEqual("d" * 40, result["path_commit"])

    def test_stable_frontmatter_only_change_is_not_equal_or_recorded_as_synced(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            module.SKILLS_DIR = root / "skills"
            module.SOURCE_MAPPINGS_DIR = root / "docs" / "sources"
            repo_skill = "skills/ai-workflow/demo/SKILL.md"
            upstream_path = "upstream/SKILL.md"
            local = (
                "---\n"
                "name: demo\n"
                "description: A sufficiently detailed original description.\n"
                "source: github:owner/repo\n"
                "source_url: https://github.com/owner/repo\n"
                "license: MIT\n"
                'version: "1.0.0"\n'
                'updated_at: "2026-01-01"\n'
                "---\n"
                "# Same body\n"
            ).encode("utf-8")
            upstream = (
                "---\n"
                "name: demo\n"
                "description: A materially revised upstream description.\n"
                'version: "9.9.9"\n'
                'updated_at: "2099-01-01"\n'
                "---\n"
                "# Same body\n"
            ).encode("utf-8")
            local_path = root / repo_skill
            local_path.parent.mkdir(parents=True)
            local_path.write_bytes(local)
            entry = complete_v2_entry(
                {
                    "normalized_slug": "demo",
                    "kind": "mirror",
                    "sync_mode": "replace",
                    "repo_skill": repo_skill,
                    "origins": [
                        {
                            "repo": "owner/repo",
                            "path": upstream_path,
                            "license": "MIT",
                            "sync_mode": "replace",
                            "artifacts": [
                                {
                                    "source": upstream_path,
                                    "target": repo_skill,
                                    "type": "file",
                                }
                            ],
                            "tracking": {
                                "channel": "latest_release",
                                "ref": "v1.0.0",
                                "resolved_commit": "a" * 40,
                                "path_commit": "c" * 40,
                                "content_sha256": hashlib.sha256(
                                    local
                                ).hexdigest(),
                            },
                        }
                    ],
                },
                local,
            )
            mapping = (
                module.SOURCE_MAPPINGS_DIR / "frontmatter.skills.json"
            )
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "video": {},
                        "official_references": [],
                        "skills": [entry],
                    }
                ),
                encoding="utf-8",
            )

            class Provider:
                def resolve_tracking(self, _repo, _tracking):
                    return ResolvedRef(
                        "latest_release", "v2.0.0", "b" * 40
                    )

                def license_evidence(self, _repo, commit):
                    return mock_license_evidence(commit)

                def compare(self, *_args):
                    return {
                        "status": "ahead",
                        "ahead_by": 1,
                        "behind_by": 0,
                    }

                def fetch_artifacts(self, _repo, _tracking, _artifacts):
                    return ArtifactInventory(
                        {repo_skill: upstream},
                        {upstream_path: "f" * 40},
                        {repo_skill: "100644"},
                        ResolvedRef(
                            "latest_release", "v2.0.0", "b" * 40
                        ),
                    )

                def path_commit(self, _repo, ref, _path):
                    if ref != "b" * 40:
                        raise AssertionError(
                            "path query was not pinned to the resolved commit"
                        )
                    return "d" * 40

            module._ACTIVE_ARTIFACT_PROVIDER = Provider()
            skill = module._v2_loaded_skill(entry, mapping, 0)
            self.assertIsNotNone(skill)

            result = module.check_upstream_changes(skill, None)

            self.assertEqual("artifact_changed", result["changes"])
            self.assertEqual([repo_skill], result["changed_files"])
            self.assertEqual("f" * 40, result["main_source_blob"])
            module.record_v2_checks([result])
            recorded = json.loads(mapping.read_text(encoding="utf-8"))
            tracking = recorded["skills"][0]["origins"][0]["tracking"]
            self.assertEqual("v1.0.0", tracking["ref"])
            self.assertEqual("a" * 40, tracking["resolved_commit"])
            self.assertEqual("c" * 40, tracking["path_commit"])
            self.assertEqual(
                hashlib.sha256(local).hexdigest(),
                tracking["content_sha256"],
            )
            self.assertEqual(
                module.date.today().isoformat(),
                tracking["last_checked_at"],
            )
            self.assertEqual(
                mock_license_checkpoint(),
                tracking["license_checkpoint"],
            )

            metadata_noise = upstream.replace(
                b"A materially revised upstream description.",
                b"A sufficiently detailed original description.",
            )
            self.assertTrue(
                module._main_artifact_equal(skill, local, metadata_noise)
            )
            self.assertFalse(
                module._main_artifact_equal(
                    skill,
                    local,
                    upstream.replace(b"name: demo", b"name: renamed-demo"),
                )
            )

    def test_main_artifact_equal_ignores_equivalent_scalar_quote_style(self):
        module = load_module()
        local = (
            "---\n"
            "name: demo\n"
            "description: 'A quoted scalar.'\n"
            "platforms: [linux, macos]\n"
            "---\n"
            "# Same body\n"
        ).encode("utf-8")
        upstream = (
            "---\n"
            "name: demo\n"
            'description: "A quoted scalar."\n'
            "platforms: [linux, macos]\n"
            "---\n"
            "# Same body\n"
        ).encode("utf-8")

        self.assertTrue(module._main_artifact_equal({}, local, upstream))

        stringified_collection = local.replace(
            b"platforms: [linux, macos]",
            b"platforms: '[linux, macos]'",
        )
        self.assertFalse(
            module._main_artifact_equal({}, stringified_collection, upstream)
        )

    def test_v2_binary_change_on_stable_release_is_auto_syncable(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            main_target = "skills/ai-workflow/demo/SKILL.md"
            binary_target = "skills/ai-workflow/demo/assets/data.bin"
            for relative, raw in (
                (main_target, b"# Same\n"),
                (binary_target, b"\x00old"),
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)

            class Provider:
                def resolve_tracking(self, _repo, _tracking):
                    return ResolvedRef("latest_release", "v2", "a" * 40)

                def license_evidence(self, _repo, commit):
                    return mock_license_evidence(commit)

                def fetch_artifacts(self, _repo, _tracking, _artifacts):
                    return ArtifactInventory(
                        {
                            main_target: b"# Same\n",
                            binary_target: b"\x00\xffnew",
                        },
                        {"src/SKILL.md": "1" * 40, "src/data.bin": "2" * 40},
                        {
                            main_target: "100644",
                            binary_target: "100644",
                        },
                        ResolvedRef("latest_release", "v2", "a" * 40),
                    )

                def path_commit(self, _repo, ref, _path):
                    if ref != "a" * 40:
                        raise AssertionError("path query was not commit-pinned")
                    return "b" * 40

            module._ACTIVE_ARTIFACT_PROVIDER = Provider()
            skill = {
                "schema_version": 2,
                "name": "demo",
                "repo": "owner/repo",
                "license": "MIT",
                "repo_skill": main_target,
                "origin_path": "src",
                "tracking": {"channel": "latest_release", "ref": "latest"},
                "sync_mode": "replace",
                "last_synced_commit": "a" * 40,
                "artifacts": [
                    {
                        "source": "src",
                        "target": "skills/ai-workflow/demo",
                        "type": "directory",
                    }
                ],
                "managed_files": [
                    {"path": main_target},
                    {"path": binary_target},
                ],
            }

            result = module.check_upstream_changes(skill, None)

            self.assertEqual("artifact_changed", result["changes"])
            self.assertEqual([binary_target], result["changed_files"])
            self.assertEqual(b"\x00\xffnew", result["upstream_files"][binary_target])
            self.assertEqual("b" * 40, result["path_commit"])

    def test_overlay_local_origin_sidecar_is_never_classified_for_external_prune(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            main_target = "skills/ai-workflow/demo/SKILL.md"
            local_overlay = "skills/ai-workflow/demo/references/local-policy.md"
            for relative, raw in (
                (main_target, b"# Same\n"),
                (local_overlay, b"# Local policy\n"),
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            managed = [
                {"path": main_target},
                {"path": local_overlay},
            ]
            skill = {
                "repo_skill": main_target,
                "artifacts": [
                    {
                        "source": "upstream",
                        "target": "skills/ai-workflow/demo",
                        "type": "directory",
                    }
                ],
                "other_origin_artifacts": [
                    {
                        "source": "curation/local-policy.md",
                        "target": local_overlay,
                        "type": "file",
                    }
                ],
                "managed_files": managed,
            }

            changed, added, removed = module._artifact_diff(
                skill,
                {main_target: b"# Same\n"},
                {main_target: "100644"},
            )

            self.assertEqual([], changed)
            self.assertEqual([], added)
            self.assertEqual([], removed)

    def test_artifact_diff_uses_external_ownership_not_incidental_disk_state(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            main_target = "skills/ai-workflow/demo/SKILL.md"
            newly_desired = "skills/ai-workflow/demo/references/new.md"
            formerly_owned = "skills/ai-workflow/demo/references/old.md"
            for relative, raw in (
                (main_target, b"# Same\n"),
                # Same bytes must not silently grant ownership.
                (newly_desired, b"# Existing identical bytes\n"),
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            skill = {
                "repo_skill": main_target,
                "artifacts": [
                    {
                        "source": "upstream/SKILL.md",
                        "target": main_target,
                        "type": "file",
                    },
                    {
                        "source": "upstream/old.md",
                        "target": formerly_owned,
                        "type": "file",
                    },
                ],
                "other_origin_artifacts": [],
                "managed_files": [
                    {
                        "path": main_target,
                        "sha256": hashlib.sha256(b"# Same\n").hexdigest(),
                    },
                    {
                        "path": formerly_owned,
                        "sha256": hashlib.sha256(b"# Old\n").hexdigest(),
                    },
                ],
            }

            changed, added, removed = module._artifact_diff(
                skill,
                {
                    main_target: b"# Same\n",
                    newly_desired: b"# Existing identical bytes\n",
                },
                {
                    main_target: "100644",
                    newly_desired: "100644",
                },
            )

            self.assertEqual([], changed)
            self.assertEqual([newly_desired], added)
            # Removed remains an inventory delta even though disk is missing.
            self.assertEqual([formerly_owned], removed)

    def test_artifact_diff_reports_mode_only_change(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            target = "skills/ai-workflow/demo/SKILL.md"
            body = b"# Same\n"
            path = root / target
            path.parent.mkdir(parents=True)
            path.write_bytes(body)
            path.chmod(0o644)
            skill = {
                "repo_skill": target,
                "artifacts": [
                    {
                        "source": "upstream/SKILL.md",
                        "target": target,
                        "type": "file",
                    }
                ],
                "other_origin_artifacts": [],
                "managed_files": [
                    {
                        "path": target,
                        "sha256": hashlib.sha256(body).hexdigest(),
                        "mode": "100644",
                    }
                ],
            }

            changed, added, removed = module._artifact_diff(
                skill,
                {target: body},
                {target: "100755"},
            )

            self.assertEqual([target], changed)
            self.assertEqual([], added)
            self.assertEqual([], removed)

    def test_v2_missing_source_reports_exact_blob_move_candidates_without_guessing(self):
        module = load_module()

        class Provider:
            def resolve_tracking(self, _repo, _tracking):
                return ResolvedRef("default_branch", "main", "b" * 40)

            def license_evidence(self, _repo, commit):
                return mock_license_evidence(commit)

            def compare(self, *_args):
                return {"status": "ahead", "ahead_by": 1, "behind_by": 0}

            def fetch_artifacts(self, *_args):
                raise module.ArtifactNotFound(["old/SKILL.md"])

            def moved_candidates(self, *_args, **_kwargs):
                return {"old/SKILL.md": ["new/location/SKILL.md"]}

        module._ACTIVE_ARTIFACT_PROVIDER = Provider()
        result = module.check_upstream_changes(
            {
                "schema_version": 2,
                "name": "demo",
                "repo": "owner/repo",
                "license": "MIT",
                "tracking": {
                    "channel": "default_branch",
                    "ref": "main",
                    "resolved_commit": "a" * 40,
                    "path_commit": "a" * 40,
                    "content_sha256": "1" * 64,
                },
                "sync_mode": "monitor",
                "last_synced_commit": "a" * 40,
                "artifacts": [
                    {
                        "source": "old/SKILL.md",
                        "target": "skills/ai/demo/SKILL.md",
                    }
                ],
            },
            None,
        )

        self.assertEqual("unavailable", result["changes"])
        self.assertEqual(
            {"old/SKILL.md": ["new/location/SKILL.md"]},
            result["moved_candidates"],
        )
        self.assertNotIn("upstream_files", result)

    def test_v2_monitor_without_complete_checkpoint_is_unavailable_fail_closed(self):
        module = load_module()
        module._ACTIVE_ARTIFACT_PROVIDER = SimpleNamespace(
            resolve_tracking=lambda *_args: self.fail(
                "incomplete monitor checkpoint must not hit network"
            )
        )

        result = module.check_upstream_changes(
            {
                "schema_version": 2,
                "name": "demo",
                "repo": "owner/repo",
                "tracking": {
                    "channel": "default_branch",
                    "ref": "main",
                    "resolved_commit": None,
                    "path_commit": None,
                    "content_sha256": None,
                },
                "sync_mode": "monitor",
            },
            None,
        )

        self.assertEqual("unavailable", result["changes"])
        self.assertIn("complete reviewed checkpoint", result["reason"])
        self.assertIn("resolved_commit", result["reason"])

    def test_manual_and_snapshot_policy_skip_only_after_v2_structure_validation(self):
        for kind, mode, damage in (
            ("overlay", "manual", "tracking"),
            ("snapshot", "local-only", "license"),
        ):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmpdir:
                module = load_module()
                root = Path(tmpdir)
                repo_skill = "skills/ai-workflow/demo/SKILL.md"
                local_path = root / repo_skill
                local_path.parent.mkdir(parents=True)
                local_path.write_text(
                    "---\nname: demo\n---\n# Demo\n", encoding="utf-8"
                )
                entry = complete_v2_entry(
                    {
                        "video_name": "demo",
                        "normalized_slug": "demo",
                        "status": "verified_in_repo",
                        "kind": kind,
                        "sync_mode": mode,
                        "repo_skill": repo_skill,
                        "origins": [
                            {
                                "repo": "owner/repo",
                                "path": "upstream/SKILL.md",
                                "sync_mode": mode,
                                "artifacts": [
                                    {
                                        "source": "upstream/SKILL.md",
                                        "target": repo_skill,
                                        "type": "file",
                                    }
                                ],
                            }
                        ],
                    },
                    local_path.read_bytes(),
                )
                if damage == "tracking":
                    del entry["origins"][0]["tracking"]["content_sha256"]
                else:
                    del entry["origins"][0]["license"]
                mapping = root / "docs" / "sources" / "invalid.skills.json"
                mapping.parent.mkdir(parents=True)
                mapping.write_text(
                    json.dumps({"schema_version": 2, "skills": [entry]}),
                    encoding="utf-8",
                )
                module.REPO_ROOT = root
                module.SKILLS_DIR = root / "skills"
                module.SOURCE_MAPPINGS_DIR = root / "docs" / "sources"

                loaded = module.load_skills_with_upstream()

                self.assertEqual(1, len(loaded))
                self.assertIn("invalid v2 sync entry", loaded[0]["load_error"])
                self.assertNotIn("expected_skip_reason", loaded[0])

    def test_record_v2_check_updates_observation_but_not_managed_content(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping = root / "docs" / "sources" / "source.skills.json"
            mapping.parent.mkdir(parents=True)
            module.REPO_ROOT = root
            module.SKILLS_DIR = root / "skills"
            module.SOURCE_MAPPINGS_DIR = mapping.parent
            repo_skill = "skills/ai-workflow/demo/SKILL.md"
            local = root / repo_skill
            local.parent.mkdir(parents=True)
            content = external_skill_content("demo", "owner/repo")
            local.write_bytes(content)
            entry = complete_v2_entry(
                {
                    "normalized_slug": "demo",
                    "kind": "overlay",
                    "sync_mode": "monitor",
                    "repo_skill": repo_skill,
                    "origins": [
                        {
                            "repo": "owner/repo",
                            "path": "upstream/SKILL.md",
                            "license": "MIT",
                            "sync_mode": "monitor",
                            "artifacts": [
                                {
                                    "source": "upstream/SKILL.md",
                                    "target": repo_skill,
                                    "type": "file",
                                }
                            ],
                        }
                    ],
                },
                content,
            )
            old_content = hashlib.sha256(content).hexdigest()
            old_managed = json.loads(json.dumps(entry["managed_files"]))
            old_path_commit = entry["origins"][0]["tracking"]["path_commit"]
            mapping.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "video": {"checked_at": "2026-01-01"},
                        "official_references": [],
                        "skills": [entry],
                    }
                ),
                encoding="utf-8",
            )
            skill = {
                "schema_version": 2,
                "repo": "owner/repo",
                "repo_skill": repo_skill,
                "mapping_path": mapping,
                "mapping_entry_index": 0,
                "origin_index": 0,
                "mapping_fingerprint": module._entry_origin_fingerprint(
                    entry, 0
                ),
            }
            module.record_v2_checks(
                [
                    {
                        "skill": skill,
                        "changes": "monitor_review",
                        "resolved_ref": "main",
                        "current_commit": "b" * 40,
                        "path_commit": "b" * 40,
                        "license_evidence": mock_license_checkpoint(),
                    }
                ]
            )

            recorded = json.loads(mapping.read_text(encoding="utf-8"))
            entry = recorded["skills"][0]
            tracking = entry["origins"][0]["tracking"]
            self.assertEqual("a" * 40, tracking["resolved_commit"])
            self.assertEqual(old_path_commit, tracking["path_commit"])
            self.assertEqual("2026-01-01", tracking["last_synced_at"])
            self.assertEqual("a" * 40, entry["upstream"]["last_synced_commit"])
            self.assertEqual(old_content, tracking["content_sha256"])
            self.assertEqual(old_managed, entry["managed_files"])

    def test_record_v2_monitor_review_advances_checkpoint_and_records_evidence(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping = root / "docs" / "sources" / "source.skills.json"
            mapping.parent.mkdir(parents=True)
            module.REPO_ROOT = root
            module.SKILLS_DIR = root / "skills"
            module.SOURCE_MAPPINGS_DIR = mapping.parent
            repo_skill = "skills/ai-workflow/demo/SKILL.md"
            local = root / repo_skill
            local.parent.mkdir(parents=True)
            content = external_skill_content("demo", "owner/repo")
            local.write_bytes(content)
            entry = complete_v2_entry(
                {
                    "normalized_slug": "demo",
                    "kind": "overlay",
                    "sync_mode": "monitor",
                    "repo_skill": repo_skill,
                    "origins": [
                        {
                            "repo": "owner/repo",
                            "path": "upstream/SKILL.md",
                            "license": "MIT",
                            "sync_mode": "monitor",
                            "artifacts": [
                                {
                                    "source": "upstream/SKILL.md",
                                    "target": repo_skill,
                                    "type": "file",
                                }
                            ],
                        }
                    ],
                },
                content,
            )
            mapping.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "video": {"checked_at": "2026-01-01"},
                        "official_references": [],
                        "skills": [entry],
                    }
                ),
                encoding="utf-8",
            )
            skill = {
                "schema_version": 2,
                "name": "demo",
                "repo": "owner/repo",
                "repo_skill": repo_skill,
                "mapping_path": mapping,
                "mapping_entry_index": 0,
                "origin_index": 0,
                "sync_mode": "monitor",
                "tracking": {"channel": "default_branch"},
                "mapping_fingerprint": module._entry_origin_fingerprint(entry, 0),
            }

            module.record_v2_monitor_reviews(
                [
                    {
                        "skill": skill,
                        "changes": "monitor_review",
                        "resolved_ref": "main",
                        "current_commit": "b" * 40,
                        "path_commit": "b" * 40,
                        "license_evidence": mock_license_checkpoint(),
                    }
                ]
            )

            recorded = json.loads(mapping.read_text(encoding="utf-8"))
            tracking = recorded["skills"][0]["origins"][0]["tracking"]
            self.assertEqual("b" * 40, tracking["resolved_commit"])
            self.assertEqual("b" * 40, tracking["path_commit"])
            self.assertEqual(
                hashlib.sha256(content).hexdigest(),
                tracking["content_sha256"],
            )
            self.assertEqual(
                "commit-aware-manual-monitor-review",
                recorded["verification_attempts"][-1]["method"],
            )

    def test_record_batch_locks_mapping_and_preserves_other_skill_updates(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping = root / "docs" / "sources" / "source.skills.json"
            mapping.parent.mkdir(parents=True)
            module.REPO_ROOT = root
            module.SKILLS_DIR = root / "skills"
            module.SOURCE_MAPPINGS_DIR = root / "docs" / "sources"

            def entry(slug):
                repo_skill = f"skills/ai-workflow/{slug}/SKILL.md"
                local = root / repo_skill
                local.parent.mkdir(parents=True)
                content = external_skill_content(slug, f"owner/{slug}")
                local.write_bytes(content)
                value = complete_v2_entry(
                    {
                        "normalized_slug": slug,
                        "kind": "overlay",
                        "sync_mode": "monitor",
                        "repo_skill": repo_skill,
                        "notes": f"initial-{slug}",
                        "origins": [
                            {
                                "repo": f"owner/{slug}",
                                "path": f"{slug}/SKILL.md",
                                "license": "MIT",
                                "sync_mode": "monitor",
                                "artifacts": [
                                    {
                                        "source": f"{slug}/SKILL.md",
                                        "target": repo_skill,
                                        "type": "file",
                                    }
                                ],
                            }
                        ],
                    },
                    content,
                )
                value["source"] = f"https://github.com/owner/{slug}"
                return value

            entries = [entry("one"), entry("two")]
            mapping.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "video": {},
                        "official_references": [],
                        "skills": entries,
                    }
                ),
                encoding="utf-8",
            )
            skills = [
                {
                    "name": value["normalized_slug"],
                    "schema_version": 2,
                    "repo": value["origins"][0]["repo"],
                    "repo_skill": value["repo_skill"],
                    "mapping_path": mapping,
                    "mapping_entry_index": index,
                    "origin_index": 0,
                    "mapping_fingerprint": module._entry_origin_fingerprint(
                        value, 0
                    ),
                }
                for index, value in enumerate(entries)
            ]
            # An unrelated field change made after checking must survive.
            current = json.loads(mapping.read_text(encoding="utf-8"))
            current["skills"][1]["notes"] = "concurrent-unrelated-update"
            mapping.write_text(json.dumps(current), encoding="utf-8")

            module.record_v2_checks(
                [
                    {
                        "skill": skill,
                        "changes": "monitor_review",
                        "resolved_ref": "main",
                        "current_commit": "b" * 40,
                        "path_commit": "b" * 40,
                        "license_evidence": mock_license_checkpoint(),
                    }
                    for skill in skills
                ]
            )

            recorded = json.loads(mapping.read_text(encoding="utf-8"))
            self.assertEqual(
                "concurrent-unrelated-update",
                recorded["skills"][1]["notes"],
            )
            self.assertTrue(
                all(
                    value["origins"][0]["tracking"]["last_checked_at"]
                    == module.date.today().isoformat()
                    for value in recorded["skills"]
                )
            )

    def test_record_batch_rejects_stale_selected_origin_fingerprint(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping = root / "docs" / "sources" / "source.skills.json"
            mapping.parent.mkdir(parents=True)
            module.REPO_ROOT = root
            module.SKILLS_DIR = root / "skills"
            module.SOURCE_MAPPINGS_DIR = mapping.parent
            repo_skill = "skills/ai-workflow/demo/SKILL.md"
            local = root / repo_skill
            local.parent.mkdir(parents=True)
            content = external_skill_content("demo", "owner/repo")
            local.write_bytes(content)
            entry = complete_v2_entry(
                {
                    "normalized_slug": "demo",
                    "kind": "overlay",
                    "sync_mode": "monitor",
                    "repo_skill": repo_skill,
                    "origins": [
                        {
                            "repo": "owner/repo",
                            "path": "old/SKILL.md",
                            "license": "MIT",
                            "sync_mode": "monitor",
                            "artifacts": [
                                {
                                    "source": "old/SKILL.md",
                                    "target": repo_skill,
                                    "type": "file",
                                }
                            ],
                        }
                    ],
                },
                content,
            )
            skill = {
                "name": "demo",
                "schema_version": 2,
                "repo": "owner/repo",
                "repo_skill": repo_skill,
                "mapping_path": mapping,
                "mapping_entry_index": 0,
                "origin_index": 0,
                "mapping_fingerprint": module._entry_origin_fingerprint(
                    entry, 0
                ),
            }
            entry["origins"][0]["path"] = "new/SKILL.md"
            mapping.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "video": {},
                        "official_references": [],
                        "skills": [entry],
                    }
                ),
                encoding="utf-8",
            )
            before = mapping.read_bytes()

            with self.assertRaisesRegex(
                RuntimeError, "changed after upstream check"
            ):
                module.record_v2_checks(
                    [
                        {
                            "skill": skill,
                            "changes": "monitor_review",
                            "resolved_ref": "main",
                            "current_commit": "b" * 40,
                            "path_commit": "b" * 40,
                        }
                    ]
                )

            self.assertEqual(before, mapping.read_bytes())

    def test_record_check_recovers_post_mapping_hard_exit_before_reread(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            module.SKILLS_DIR = root / "skills"
            module.SOURCE_MAPPINGS_DIR = root / "docs" / "sources"
            repo_skill = "skills/ai-workflow/demo/SKILL.md"
            skill_path = root / repo_skill
            skill_path.parent.mkdir(parents=True)
            old_content = external_skill_content("demo", "owner/repo")
            new_content = old_content.replace(b"# demo", b"# updated demo")
            skill_path.write_bytes(old_content)
            entry = complete_v2_entry(
                {
                    "normalized_slug": "demo",
                    "kind": "mirror",
                    "sync_mode": "replace",
                    "repo_skill": repo_skill,
                    "origins": [
                        {
                            "repo": "owner/repo",
                            "path": "upstream/SKILL.md",
                            "license": "MIT",
                            "sync_mode": "replace",
                            "artifacts": [
                                {
                                    "source": "upstream/SKILL.md",
                                    "target": repo_skill,
                                    "type": "file",
                                }
                            ],
                            "tracking": {
                                "channel": "latest_release",
                                "ref": "v1.0.0",
                            },
                        }
                    ],
                },
                old_content,
            )
            before_data = {
                "schema_version": 2,
                "video": {},
                "official_references": [],
                "skills": [entry],
            }
            mapping = (
                root / "docs" / "sources" / "source.skills.json"
            )
            mapping.parent.mkdir(parents=True)
            mapping.write_bytes(module.serialize_mapping_json(before_data))
            checked_skill = {
                "name": "demo",
                "schema_version": 2,
                "repo": "owner/repo",
                "repo_skill": repo_skill,
                "mapping_path": mapping,
                "mapping_entry_index": 0,
                "origin_index": 0,
                "mapping_fingerprint": module._entry_origin_fingerprint(
                    entry, 0
                ),
            }

            after_data = json.loads(json.dumps(before_data))
            after_entry = after_data["skills"][0]
            new_digest = hashlib.sha256(new_content).hexdigest()
            after_entry["managed_files"][0]["sha256"] = new_digest
            after_tracking = after_entry["origins"][0]["tracking"]
            after_tracking["content_sha256"] = new_digest
            after_tracking["resolved_commit"] = "c" * 40
            after_tracking["path_commit"] = "d" * 40
            after_tracking["ref"] = "v2.0.0"
            after_path = mapping.with_suffix(".after")
            after_bytes = module.serialize_mapping_json(after_data)
            after_path.write_bytes(after_bytes)

            worker = r"""
import hashlib
import os
import sys
from pathlib import Path
from scripts.artifact_set_sync import (
    plan_artifact_set_sync,
    prepare_artifact_set_sync,
)

root = Path(sys.argv[1])
mapping = Path(sys.argv[2])
after_path = Path(sys.argv[3])
skill = "skills/ai-workflow/demo/SKILL.md"
old = (root / skill).read_bytes()
new = old.replace(b"# demo", b"# updated demo")
entry = {
    "normalized_slug": "demo",
    "repo_skill": skill,
    "kind": "mirror",
    "origins": [{
        "artifacts": [{
            "source": "upstream/SKILL.md",
            "target": skill,
            "type": "file",
        }],
    }],
    "managed_files": [{
        "path": skill,
        "sha256": hashlib.sha256(old).hexdigest(),
        "owner": "demo",
        "mode": "100644",
    }],
}
plan = plan_artifact_set_sync(
    root,
    entry,
    [{
        "source": "upstream/SKILL.md",
        "target": skill,
        "type": "file",
        "data": new,
        "mode": "100644",
    }],
    {"resolved_commit": "c" * 40},
)
transaction = prepare_artifact_set_sync(plan)
before_sha = hashlib.sha256(mapping.read_bytes()).hexdigest()
after_sha = hashlib.sha256(after_path.read_bytes()).hexdigest()
transaction.bind_authority(
    mapping.relative_to(root).as_posix(),
    before_sha,
    after_sha,
)
os.replace(after_path, mapping)
directory_fd = os.open(
    mapping.parent,
    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
)
os.fsync(directory_fd)
os.close(directory_fd)
os._exit(73)
"""
            import subprocess
            import sys

            completed = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    worker,
                    str(root),
                    str(mapping),
                    str(after_path),
                ],
                cwd=REPO_ROOT,
                env={
                    **__import__("os").environ,
                    "PYTHONPATH": str(REPO_ROOT),
                },
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(73, completed.returncode, completed.stderr)

            from scripts.artifact_set_sync import (
                skill_transaction_journal_path,
            )

            journal = skill_transaction_journal_path(
                root,
                "skills/ai-workflow/demo",
            )
            self.assertTrue(journal.exists())
            with self.assertRaisesRegex(
                RuntimeError, "changed after upstream check"
            ):
                module.record_v2_checks(
                    [
                        {
                            "skill": checked_skill,
                            "changes": "none",
                            "resolved_ref": "v1.0.0",
                            "current_commit": "b" * 40,
                            "path_commit": "b" * 40,
                            "license_evidence": mock_license_checkpoint(),
                        }
                    ]
                )

            self.assertEqual(after_bytes, mapping.read_bytes())
            self.assertEqual(new_content, skill_path.read_bytes())
            self.assertFalse(journal.exists())

    def test_record_check_rejects_symlinked_mapping_ancestor(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            repo_skill = "skills/ai-workflow/demo/SKILL.md"
            skill_path = root / repo_skill
            skill_path.parent.mkdir(parents=True)
            content = external_skill_content("demo", "owner/repo")
            skill_path.write_bytes(content)
            entry = complete_v2_entry(
                {
                    "normalized_slug": "demo",
                    "kind": "overlay",
                    "sync_mode": "monitor",
                    "repo_skill": repo_skill,
                    "origins": [
                        {
                            "repo": "owner/repo",
                            "path": "upstream/SKILL.md",
                            "license": "MIT",
                            "sync_mode": "monitor",
                            "artifacts": [
                                {
                                    "source": "upstream/SKILL.md",
                                    "target": repo_skill,
                                    "type": "file",
                                }
                            ],
                        }
                    ],
                },
                content,
            )
            outside = root / "outside"
            sources = outside / "sources"
            sources.mkdir(parents=True)
            mapping = root / "docs" / "sources" / "source.skills.json"
            (root / "docs").symlink_to(outside, target_is_directory=True)
            outside_mapping = sources / mapping.name
            outside_mapping.write_text(
                json.dumps({"schema_version": 2, "skills": [entry]}),
                encoding="utf-8",
            )
            before = outside_mapping.read_bytes()
            checked_skill = {
                "schema_version": 2,
                "repo": "owner/repo",
                "repo_skill": repo_skill,
                "mapping_path": mapping,
                "mapping_entry_index": 0,
                "origin_index": 0,
                "mapping_fingerprint": module._entry_origin_fingerprint(
                    entry, 0
                ),
            }

            with self.assertRaises((OSError, RuntimeError)):
                module.record_v2_checks(
                    [
                        {
                            "skill": checked_skill,
                            "changes": "monitor_review",
                            "current_commit": "b" * 40,
                            "path_commit": "b" * 40,
                            "license_evidence": mock_license_checkpoint(),
                        }
                    ]
                )

            self.assertEqual(before, outside_mapping.read_bytes())
            self.assertEqual([], list(sources.glob(".*.tmp")))

    def test_v2_authority_fingerprint_and_revalidation_cover_revocation_fields(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            repo_skill = "skills/ai-workflow/demo/SKILL.md"
            local = root / repo_skill
            local.parent.mkdir(parents=True)
            content = external_skill_content("demo", "owner/repo")
            local.write_bytes(content)
            entry = complete_v2_entry(
                {
                    "normalized_slug": "demo",
                    "kind": "mirror",
                    "sync_mode": "replace",
                    "repo_skill": repo_skill,
                    "origins": [
                        {
                            "repo": "owner/repo",
                            "path": "upstream/SKILL.md",
                            "license": "MIT",
                            "sync_mode": "replace",
                            "artifacts": [
                                {
                                    "source": "upstream/SKILL.md",
                                    "target": repo_skill,
                                    "type": "file",
                                }
                            ],
                            "tracking": {
                                "channel": "latest_release",
                                "ref": "v1.0.0",
                            },
                        }
                    ],
                },
                content,
            )
            fingerprint = module._entry_origin_fingerprint(entry, 0)

            mutations = (
                ("kind", lambda value: value.__setitem__("kind", "snapshot")),
                ("status", lambda value: value.__setitem__("status", "retired")),
                (
                    "entry sync mode",
                    lambda value: value.__setitem__("sync_mode", "monitor"),
                ),
                (
                    "origin repo",
                    lambda value: value["origins"][0].__setitem__(
                        "repo", "owner/revoked"
                    ),
                ),
                (
                    "origin path",
                    lambda value: value["origins"][0].__setitem__(
                        "path", "moved/SKILL.md"
                    ),
                ),
                (
                    "origin license",
                    lambda value: value["origins"][0].__setitem__(
                        "license", None
                    ),
                ),
                (
                    "origin sync mode",
                    lambda value: value["origins"][0].__setitem__(
                        "sync_mode", "archived"
                    ),
                ),
                (
                    "artifact authority",
                    lambda value: value["origins"][0]["artifacts"][0].__setitem__(
                        "source", "replacement/SKILL.md"
                    ),
                ),
                (
                    "tracking channel",
                    lambda value: value["origins"][0]["tracking"].__setitem__(
                        "channel", "default_branch"
                    ),
                ),
                (
                    "tracking ref",
                    lambda value: value["origins"][0]["tracking"].__setitem__(
                        "ref", "v2.0.0"
                    ),
                ),
                (
                    "managed ownership",
                    lambda value: value["managed_files"][0].__setitem__(
                        "owner", "revoked"
                    ),
                ),
            )
            for label, mutate in mutations:
                with self.subTest(field=label):
                    candidate = json.loads(json.dumps(entry))
                    mutate(candidate)
                    self.assertNotEqual(
                        fingerprint,
                        module._entry_origin_fingerprint(candidate, 0),
                    )

            checked_skill = {
                "schema_version": 2,
                "repo": "owner/repo",
                "mapping_entry_index": 0,
                "origin_index": 0,
                "mapping_fingerprint": fingerprint,
            }
            revoked = json.loads(json.dumps(entry))
            revoked["status"] = "retired"
            with self.assertRaisesRegex(
                RuntimeError, "authority is no longer valid|no longer active"
            ):
                module._v2_entry_and_origin(
                    {"skills": [revoked]},
                    checked_skill,
                    for_apply=True,
                )

            without_fingerprint = dict(checked_skill)
            without_fingerprint.pop("mapping_fingerprint")
            with self.assertRaisesRegex(RuntimeError, "fingerprint"):
                module._v2_entry_and_origin(
                    {"skills": [entry]},
                    without_fingerprint,
                    for_apply=True,
                )

            monitor = json.loads(json.dumps(entry))
            monitor["kind"] = "overlay"
            monitor["sync_mode"] = "monitor"
            monitor["origins"][0]["sync_mode"] = "monitor"
            monitor["origins"][0]["tracking"]["channel"] = "default_branch"
            monitor["origins"][0]["tracking"]["ref"] = "main"
            monitor_skill = {
                **checked_skill,
                "mapping_fingerprint": module._entry_origin_fingerprint(
                    monitor, 0
                ),
            }
            with self.assertRaisesRegex(
                RuntimeError, "no longer permits automatic stable apply"
            ):
                module._v2_entry_and_origin(
                    {"skills": [monitor]},
                    monitor_skill,
                    for_apply=True,
                )

    def test_mapping_advisory_lock_rejects_second_writer(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            mapping = Path(tmpdir) / "source.skills.json"
            mapping.write_text("{}\n", encoding="utf-8")
            with module.mapping_advisory_lock(mapping):
                with self.assertRaises(module.MappingLockError):
                    with module.mapping_advisory_lock(mapping, timeout=0):
                        self.fail("second mapping writer acquired the lock")
            for invalid in (True, -1, float("nan"), float("inf")):
                with self.subTest(timeout=invalid), self.assertRaises(
                    ValueError
                ):
                    with module.mapping_advisory_lock(
                        mapping, timeout=invalid
                    ):
                        self.fail("invalid timeout acquired mapping lock")

    def test_apply_rejects_payload_targets_claimed_by_other_origin_scopes(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            main_target = "skills/ai-workflow/demo/SKILL.md"
            exact_target = (
                "skills/ai-workflow/demo/references/curated.md"
            )
            nested_target = (
                "skills/ai-workflow/demo/templates/nested/config.bin"
            )
            main_path = root / main_target
            main_path.parent.mkdir(parents=True)
            old_main = external_skill_content("demo", "owner/repo")
            main_path.write_bytes(old_main)
            selected_artifacts = [
                {
                    "source": "package",
                    "target": "skills/ai-workflow/demo",
                    "type": "directory",
                }
            ]
            other_artifacts = [
                {
                    "source": exact_target,
                    "target": exact_target,
                    "type": "file",
                },
                {
                    "source": "skills/ai-workflow/demo/templates",
                    "target": "skills/ai-workflow/demo/templates",
                    "type": "directory",
                },
            ]
            entry = complete_v2_entry(
                {
                    "normalized_slug": "demo",
                    "kind": "overlay",
                    "sync_mode": "replace",
                    "repo_skill": main_target,
                    "origins": [
                        {
                            "repo": "owner/repo",
                            "path": "package",
                            "license": "MIT",
                            "sync_mode": "replace",
                            "artifacts": selected_artifacts,
                            "tracking": {
                                "channel": "latest_release",
                                "ref": "v1.0.0",
                            },
                        },
                        {
                            "repo": "local-repo/curation",
                            "path": (
                                "skills/ai-workflow/demo/references"
                            ),
                            "license": None,
                            "sync_mode": "manual",
                            "artifacts": other_artifacts,
                            "tracking": {
                                "channel": "local",
                                "ref": "local",
                            },
                        },
                    ],
                },
                old_main,
            )
            mapping = root / "docs" / "sources" / "source.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "video": {},
                        "official_references": [],
                        "skills": [entry],
                    }
                ),
                encoding="utf-8",
            )
            skill = {
                "name": "demo",
                "schema_version": 2,
                "repo": "owner/repo",
                "repo_skill": main_target,
                "sync_mode": "replace",
                "tracking": {
                    "channel": "latest_release",
                    "ref": "v1.0.0",
                },
                "artifacts": selected_artifacts,
                "mapping_path": mapping,
                "mapping_entry_index": 0,
                "origin_index": 0,
                "local_path": main_path,
                "mapping_fingerprint": module._entry_origin_fingerprint(
                    entry, 0
                ),
            }
            update = {
                "skill": skill,
                "changes": "artifact_changed",
                "current_commit": "b" * 40,
                "path_commit": "c" * 40,
                "resolved_ref": "v2.0.0",
                "license_evidence": mock_license_checkpoint(),
                "upstream_files": {
                    main_target: b"---\nname: demo\n---\n# New\n",
                    exact_target: b"upstream exact",
                    nested_target: b"\x00upstream nested",
                },
                "source_blobs": {
                    "package/SKILL.md": "1" * 40,
                    "package/references/curated.md": "2" * 40,
                    "package/templates/nested/config.bin": "3" * 40,
                },
                "upstream_modes": {
                    main_target: "100644",
                    exact_target: "100644",
                    nested_target: "100644",
                },
            }
            plan_calls = []
            original_engine_loader = module._load_artifact_engine
            module._load_artifact_engine = lambda: SimpleNamespace(
                plan_artifact_set_sync=lambda *_args, **_kwargs: plan_calls.append(
                    True
                )
            )
            try:
                with self.assertRaisesRegex(
                    RuntimeError, "collide with another origin scope"
                ) as raised:
                    module.apply_v2_update(update)
            finally:
                module._load_artifact_engine = original_engine_loader

            self.assertIn(exact_target, str(raised.exception))
            self.assertIn(nested_target, str(raised.exception))
            self.assertEqual([], plan_calls)
            self.assertEqual(
                [exact_target, nested_target],
                module._other_origin_target_conflicts(
                    entry,
                    selected_origin_index=0,
                    desired_targets={
                        exact_target,
                        nested_target,
                        "skills/ai-workflow/demo/other.txt",
                    },
                ),
            )

    def test_candidate_mapping_gate_rejects_repository_unique_claim_conflict(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            module.SKILLS_DIR = root / "skills"
            module.SOURCE_MAPPINGS_DIR = root / "docs" / "sources"
            repo_skill = "skills/ai-workflow/demo/SKILL.md"
            local = root / repo_skill
            local.parent.mkdir(parents=True)
            content = external_skill_content("demo", "owner/repo")
            local.write_bytes(content)
            entry = complete_v2_entry(
                {
                    "normalized_slug": "demo",
                    "kind": "mirror",
                    "sync_mode": "replace",
                    "repo_skill": repo_skill,
                    "origins": [
                        {
                            "repo": "owner/repo",
                            "path": "upstream/SKILL.md",
                            "license": "MIT",
                            "sync_mode": "replace",
                            "artifacts": [
                                {
                                    "source": "upstream/SKILL.md",
                                    "target": repo_skill,
                                    "type": "file",
                                }
                            ],
                            "tracking": {
                                "channel": "latest_release",
                                "ref": "v1.0.0",
                            },
                        }
                    ],
                },
                content,
            )
            data = {
                "schema_version": 2,
                "video": {},
                "official_references": [],
                "skills": [entry],
            }
            module.SOURCE_MAPPINGS_DIR.mkdir(parents=True)
            candidate = module.SOURCE_MAPPINGS_DIR / "candidate.skills.json"
            duplicate = module.SOURCE_MAPPINGS_DIR / "duplicate.skills.json"
            candidate.write_text(json.dumps(data), encoding="utf-8")
            duplicate.write_text(json.dumps(data), encoding="utf-8")
            before = candidate.read_bytes()

            with self.assertRaisesRegex(
                RuntimeError,
                "candidate mapping failed full provenance validation.*"
                "duplicate|unique|claimed",
            ):
                module._validate_candidate_mappings({candidate: data})

            self.assertEqual(before, candidate.read_bytes())
            self.assertEqual(
                [],
                list(module.SOURCE_MAPPINGS_DIR.glob(".*.validation.skills.json")),
            )

    def test_v2_apply_commits_artifact_set_and_mapping_in_one_transaction(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            main_target = "skills/ai-workflow/demo/SKILL.md"
            side_target = "skills/ai-workflow/demo/assets/data.bin"
            main_path = root / main_target
            side_path = root / side_target
            main_path.parent.mkdir(parents=True, exist_ok=True)
            side_path.parent.mkdir(parents=True, exist_ok=True)
            old_main = (
                "---\nname: demo\nsource: github:owner/repo\n"
                "source_url: https://github.com/owner/repo\n"
                "license: MIT\nversion: \"1.0.0\"\n"
                "updated_at: \"2026-01-01\"\n---\n# Old\n"
            ).encode()
            old_side = b"\x00old"
            main_path.write_bytes(old_main)
            side_path.write_bytes(old_side)
            artifacts = [
                {
                    "source": "package",
                    "target": "skills/ai-workflow/demo",
                    "type": "directory",
                },
            ]
            mapping = root / "docs" / "sources" / "source.skills.json"
            mapping.parent.mkdir(parents=True)
            module.SOURCE_MAPPINGS_DIR = mapping.parent
            entry = complete_v2_entry(
                {
                    "normalized_slug": "demo",
                    "kind": "mirror",
                    "sync_mode": "replace",
                    "repo_skill": main_target,
                    "origins": [
                        {
                            "repo": "owner/repo",
                            "path": "package",
                            "license": "MIT",
                            "sync_mode": "replace",
                            "artifacts": artifacts,
                            "tracking": {
                                "channel": "latest_release",
                                "ref": "v1.0.0",
                                "resolved_commit": "a" * 40,
                                "path_commit": "a" * 40,
                                "content_sha256": hashlib.sha256(
                                    old_main
                                ).hexdigest(),
                            },
                        }
                    ],
                },
                old_main,
            )
            entry["managed_files"].append(
                {
                    "path": side_target,
                    "sha256": hashlib.sha256(old_side).hexdigest(),
                    "owner": "demo",
                    "mode": "100644",
                }
            )
            mapping.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "video": {},
                        "official_references": [],
                        "skills": [entry],
                    }
                ),
                encoding="utf-8",
            )
            skill = {
                "name": "demo",
                "schema_version": 2,
                "repo": "owner/repo",
                "repo_skill": main_target,
                "sync_mode": "replace",
                "tracking": {
                    "channel": "latest_release",
                    "ref": "v1.0.0",
                },
                "artifacts": artifacts,
                "mapping_path": mapping,
                "mapping_entry_index": 0,
                "origin_index": 0,
                "local_path": main_path,
                "mapping_fingerprint": module._entry_origin_fingerprint(
                    entry, 0
                ),
            }
            update = {
                "skill": skill,
                "changes": "artifact_changed",
                "current_commit": "b" * 40,
                "path_commit": "a" * 40,
                "resolved_ref": "v2.0.0",
                "license_evidence": mock_license_checkpoint(),
                "upstream_files": {
                    main_target: b"---\nname: demo\n---\n# New\n",
                    side_target: b"\x00\xffnew",
                },
                "source_blobs": {
                    "package/SKILL.md": "1" * 40,
                    "package/assets/data.bin": "2" * 40,
                },
                "upstream_modes": {
                    main_target: "100644",
                    side_target: "100755",
                },
            }

            result = module.apply_v2_update(update)

            self.assertTrue(result.applied)
            self.assertIn("# New", main_path.read_text(encoding="utf-8"))
            self.assertEqual(b"\x00\xffnew", side_path.read_bytes())
            self.assertEqual(0o755, side_path.stat().st_mode & 0o777)
            recorded = json.loads(mapping.read_text(encoding="utf-8"))
            entry = recorded["skills"][0]
            tracking = entry["origins"][0]["tracking"]
            self.assertEqual("v2.0.0", tracking["ref"])
            self.assertEqual("b" * 40, tracking["resolved_commit"])
            self.assertEqual("a" * 40, tracking["path_commit"])
            self.assertEqual(
                hashlib.sha256(main_path.read_bytes()).hexdigest(),
                tracking["content_sha256"],
            )
            self.assertEqual(
                mock_license_checkpoint(),
                tracking["license_checkpoint"],
            )
            self.assertEqual(
                {main_target, side_target},
                {item["path"] for item in entry["managed_files"]},
            )
            self.assertEqual(
                "100755",
                next(
                    item
                    for item in entry["managed_files"]
                    if item["path"] == side_target
                )["mode"],
            )
            self.assertEqual(artifacts, entry["origins"][0]["artifacts"])
            self.assertEqual("v2.0.0", entry["upstream"]["ref"])

    def test_v2_apply_commits_mode_repair_when_mapping_is_already_authoritative(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            module.SKILLS_DIR = root / "skills"
            module.SOURCE_MAPPINGS_DIR = root / "docs" / "sources"
            target = "skills/ai-workflow/demo/SKILL.md"
            local = root / target
            local.parent.mkdir(parents=True)
            content = external_skill_content("demo", "owner/repo")
            local.write_bytes(content)
            local.chmod(0o644)
            commit = "a" * 40
            today = module.date.today().isoformat()
            artifacts = [
                {
                    "source": "package/SKILL.md",
                    "target": target,
                    "type": "file",
                }
            ]
            entry = complete_v2_entry(
                {
                    "normalized_slug": "demo",
                    "kind": "mirror",
                    "sync_mode": "replace",
                    "repo_skill": target,
                    "origins": [
                        {
                            "repo": "owner/repo",
                            "path": "package/SKILL.md",
                            "license": "MIT",
                            "sync_mode": "replace",
                            "artifacts": artifacts,
                            "tracking": {
                                "channel": "latest_release",
                                "ref": "v1.0.0",
                                "resolved_commit": commit,
                                "path_commit": commit,
                                "content_sha256": hashlib.sha256(
                                    content
                                ).hexdigest(),
                                "last_checked_at": today,
                                "last_synced_at": today,
                                "license_checkpoint": (
                                    mock_license_checkpoint(commit)
                                ),
                            },
                        }
                    ],
                },
                content,
            )
            entry["managed_files"][0]["mode"] = "100755"
            entry["upstream"].update(
                {
                    "ref": "v1.0.0",
                    "path_commit": commit,
                    "last_checked_at": today,
                    "last_synced_at": today,
                    "last_synced_commit": commit,
                }
            )
            payload = {
                "schema_version": 2,
                "video": {"checked_at": today},
                "official_references": [],
                "skills": [entry],
            }
            mapping = module.SOURCE_MAPPINGS_DIR / "source.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_bytes(module.serialize_mapping_json(payload))
            before = mapping.read_bytes()
            skill = {
                "name": "demo",
                "schema_version": 2,
                "repo": "owner/repo",
                "repo_skill": target,
                "sync_mode": "replace",
                "tracking": {
                    "channel": "latest_release",
                    "ref": "v1.0.0",
                },
                "artifacts": artifacts,
                "mapping_path": mapping,
                "mapping_entry_index": 0,
                "origin_index": 0,
                "local_path": local,
                "mapping_fingerprint": module._entry_origin_fingerprint(
                    entry, 0
                ),
            }
            update = {
                "skill": skill,
                "changes": "artifact_changed",
                "current_commit": commit,
                "path_commit": commit,
                "resolved_ref": "v1.0.0",
                "license_evidence": mock_license_checkpoint(commit),
                "upstream_files": {target: content},
                "source_blobs": {"package/SKILL.md": "1" * 40},
                "upstream_modes": {target: "100755"},
            }
            original_merge = module.merge_frontmatter
            module.merge_frontmatter = lambda local_text, _upstream: local_text
            try:
                result = module.apply_v2_update(update)
            finally:
                module.merge_frontmatter = original_merge

            self.assertTrue(result.applied)
            self.assertEqual(0o755, local.stat().st_mode & 0o777)
            self.assertEqual(before, mapping.read_bytes())

    def test_v2_mapping_write_failure_rolls_back_prepared_artifact_tree(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            module.SKILLS_DIR = root / "skills"
            main_target = "skills/ai-workflow/demo/SKILL.md"
            main_path = root / main_target
            main_path.parent.mkdir(parents=True)
            old_main = (
                b"---\nname: demo\nsource: github:owner/repo\n"
                b"source_url: https://github.com/owner/repo\nlicense: MIT\n"
                b"version: \"1.0.0\"\n---\n# Old\n"
            )
            main_path.write_bytes(old_main)
            artifacts = [
                {
                    "source": "package/SKILL.md",
                    "target": main_target,
                    "type": "file",
                }
            ]
            mapping = root / "docs" / "sources" / "source.skills.json"
            mapping.parent.mkdir(parents=True)
            module.SOURCE_MAPPINGS_DIR = mapping.parent
            entry = complete_v2_entry(
                {
                    "normalized_slug": "demo",
                    "kind": "mirror",
                    "sync_mode": "replace",
                    "repo_skill": main_target,
                    "origins": [
                        {
                            "repo": "owner/repo",
                            "path": "package/SKILL.md",
                            "license": "MIT",
                            "sync_mode": "replace",
                            "artifacts": artifacts,
                            "tracking": {
                                "channel": "latest_release",
                                "ref": "v1.0.0",
                                "resolved_commit": "a" * 40,
                                "path_commit": "a" * 40,
                                "content_sha256": hashlib.sha256(
                                    old_main
                                ).hexdigest(),
                            },
                        }
                    ],
                },
                old_main,
            )
            payload = {
                "schema_version": 2,
                "video": {},
                "official_references": [],
                "skills": [entry],
            }
            mapping.write_text(json.dumps(payload), encoding="utf-8")
            mapping_before = mapping.read_bytes()
            skill = {
                "name": "demo",
                "schema_version": 2,
                "repo": "owner/repo",
                "repo_skill": main_target,
                "sync_mode": "replace",
                "tracking": {
                    "channel": "latest_release",
                    "ref": "v1.0.0",
                },
                "artifacts": artifacts,
                "mapping_path": mapping,
                "mapping_entry_index": 0,
                "origin_index": 0,
                "local_path": main_path,
                "mapping_fingerprint": module._entry_origin_fingerprint(
                    entry, 0
                ),
            }
            update = {
                "skill": skill,
                "changes": "artifact_changed",
                "current_commit": "b" * 40,
                "path_commit": "a" * 40,
                "resolved_ref": "v2.0.0",
                "license_evidence": mock_license_checkpoint(),
                "upstream_files": {
                    main_target: b"---\nname: demo\n---\n# New\n"
                },
                "source_blobs": {"package/SKILL.md": "1" * 40},
                "upstream_modes": {main_target: "100644"},
            }
            original_writer = module.atomic_write_json
            def fail_before_replace(path, data, **kwargs):
                return original_writer(
                    path,
                    data,
                    **kwargs,
                    fault_injector=lambda event: (
                        (_ for _ in ()).throw(OSError("mapping disk full"))
                        if event == "after_temp_fsync"
                        else None
                    ),
                )

            module.atomic_write_json = fail_before_replace
            try:
                with self.assertRaises(module.AtomicMappingWriteError) as raised:
                    module.apply_v2_update(update)
            finally:
                module.atomic_write_json = original_writer

            self.assertFalse(raised.exception.replaced)
            self.assertEqual(old_main, main_path.read_bytes())
            self.assertEqual(mapping_before, mapping.read_bytes())

            def fail_after_replace(path, data, **kwargs):
                return original_writer(
                    path,
                    data,
                    **kwargs,
                    fault_injector=lambda event: (
                        (_ for _ in ()).throw(
                            OSError("mapping directory fsync failed")
                        )
                        if event == "after_replace"
                        else None
                    ),
                )

            module.atomic_write_json = fail_after_replace
            try:
                with self.assertRaises(
                    module.AtomicMappingWriteError
                ) as raised_after:
                    module.apply_v2_update(update)
            finally:
                module.atomic_write_json = original_writer

            self.assertTrue(raised_after.exception.replaced)
            self.assertIn("# New", main_path.read_text(encoding="utf-8"))
            recorded = json.loads(mapping.read_text(encoding="utf-8"))
            self.assertEqual(
                "b" * 40,
                recorded["skills"][0]["origins"][0]["tracking"][
                    "resolved_commit"
                ],
            )

    def test_atomic_mapping_writer_rejects_symlink_and_nonregular_targets(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            real = root / "real.json"
            real.write_text("{}\n", encoding="utf-8")
            symlink = root / "mapping.json"
            symlink.symlink_to(real)
            with self.assertRaises(module.AtomicMappingWriteError) as symlink_error:
                module.atomic_write_json(symlink, {"safe": True})
            self.assertFalse(symlink_error.exception.replaced)
            self.assertEqual("{}\n", real.read_text(encoding="utf-8"))

            symlink.unlink()
            symlink.symlink_to(root / "missing.json")
            with self.assertRaises(
                module.AtomicMappingWriteError
            ) as broken_symlink_error:
                module.atomic_write_json(symlink, {"safe": True})
            self.assertFalse(broken_symlink_error.exception.replaced)

            symlink.unlink()
            symlink.mkdir()
            with self.assertRaises(module.AtomicMappingWriteError) as dir_error:
                module.atomic_write_json(symlink, {"safe": True})
            self.assertFalse(dir_error.exception.replaced)

            symlink.rmdir()
            symlink.write_text('{"old": true}\n', encoding="utf-8")

            def swap_temp_inode(event):
                if event != "after_temp_fsync":
                    return
                candidates = list(root.glob(".mapping.json.*.tmp"))
                self.assertEqual(1, len(candidates))
                candidates[0].unlink()
                candidates[0].symlink_to(real)

            with self.assertRaises(module.AtomicMappingWriteError) as inode_error:
                module.atomic_write_json(
                    symlink,
                    {"safe": True},
                    fault_injector=swap_temp_inode,
                )
            self.assertFalse(inode_error.exception.replaced)
            self.assertEqual(
                '{"old": true}\n', symlink.read_text(encoding="utf-8")
            )
            foreign = list(root.glob(".mapping.json.*.tmp"))
            self.assertEqual(1, len(foreign))
            self.assertTrue(foreign[0].is_symlink())
            foreign[0].unlink()

            sentinel = b"concurrent-regular-occupant"

            def swap_temp_for_regular(event):
                if event != "after_temp_fsync":
                    return
                candidates = list(root.glob(".mapping.json.*.tmp"))
                self.assertEqual(1, len(candidates))
                candidates[0].unlink()
                candidates[0].write_bytes(sentinel)

            with self.assertRaises(module.AtomicMappingWriteError):
                module.atomic_write_json(
                    symlink,
                    {"safe": True},
                    fault_injector=swap_temp_for_regular,
                )
            foreign = list(root.glob(".mapping.json.*.tmp"))
            self.assertEqual(1, len(foreign))
            self.assertEqual(sentinel, foreign[0].read_bytes())
            foreign[0].unlink()

    def test_stage_helper_pins_created_inode_before_parent_validation(self):
        for replacement_kind in ("regular", "symlink"):
            with self.subTest(replacement_kind=replacement_kind):
                module = load_module()
                with tempfile.TemporaryDirectory() as tmpdir:
                    root = Path(tmpdir)
                    module.REPO_ROOT = root
                    mapping = root / "mapping.json"
                    mapping.write_text(
                        '{"value": "old"}\n',
                        encoding="utf-8",
                    )
                    sentinel = b"foreign-pre-pin-occupant"
                    symlink_target = root / "foreign-target"
                    symlink_target.write_bytes(sentinel)
                    foreign: list[Path] = []
                    real_validate_parent = module._validate_mapping_parent

                    def replace_during_parent_validation(path, identity):
                        real_validate_parent(path, identity)
                        if foreign:
                            return
                        candidates = list(
                            root.glob(".mapping.json.*.tmp")
                        )
                        if not candidates:
                            return
                        self.assertEqual(1, len(candidates))
                        candidate = candidates[0]
                        candidate.unlink()
                        if replacement_kind == "symlink":
                            candidate.symlink_to(symlink_target)
                        else:
                            candidate.write_bytes(sentinel)
                        foreign.append(candidate)

                    module._validate_mapping_parent = (
                        replace_during_parent_validation
                    )
                    try:
                        with self.assertRaises(
                            module.AtomicMappingWriteError
                        ) as raised:
                            module.atomic_write_json(
                                mapping,
                                {"value": "new"},
                            )
                    finally:
                        module._validate_mapping_parent = real_validate_parent

                    self.assertFalse(raised.exception.replaced)
                    self.assertEqual(
                        b'{"value": "old"}\n',
                        mapping.read_bytes(),
                    )
                    self.assertEqual(1, len(foreign))
                    self.assertTrue(foreign[0].exists())
                    if replacement_kind == "symlink":
                        self.assertTrue(foreign[0].is_symlink())
                    else:
                        self.assertEqual(sentinel, foreign[0].read_bytes())
                    foreign[0].unlink()

    def test_atomic_mapping_post_stage_failures_do_not_leak_fds(self):
        module = load_module()
        for replacement_kind in ("regular", "symlink", "missing"):
            with self.subTest(replacement_kind=replacement_kind):
                baseline_fds = self._open_fd_count()
                for _iteration in range(12):
                    with tempfile.TemporaryDirectory() as tmpdir:
                        root = Path(tmpdir)
                        module.REPO_ROOT = root
                        mapping = root / "mapping.json"
                        original = b'{"value": "old"}\n'
                        mapping.write_bytes(original)
                        real_secure, foreign, sentinel = (
                            self._install_post_stage_metadata_attack(
                                module,
                                root=root,
                                replacement_kind=replacement_kind,
                                selector=lambda path: path.name.endswith(
                                    ".tmp"
                                ),
                            )
                        )
                        try:
                            with self.assertRaises(
                                module.AtomicMappingWriteError
                            ) as raised:
                                module.atomic_write_json(
                                    mapping,
                                    {"value": "new"},
                                )
                        finally:
                            module._secure_temporary_metadata = real_secure

                        self.assertFalse(raised.exception.replaced)
                        self.assertEqual(original, mapping.read_bytes())
                        self._assert_foreign_stage_state(
                            foreign,
                            replacement_kind,
                            sentinel,
                        )
                    self.assertEqual(
                        baseline_fds,
                        self._open_fd_count(),
                    )

    def test_atomic_mapping_writer_cas_preserves_concurrent_mapping_change(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            mapping = root / "mapping.skills.json"
            mapping.write_text('{"value": "old"}\n', encoding="utf-8")
            snapshot = module.capture_mapping_snapshot(mapping)
            concurrent = b'{"value": "concurrent"}\n'

            def modify_mapping(event):
                if event == "after_temp_fsync":
                    mapping.write_bytes(concurrent)

            with self.assertRaises(
                module.AtomicMappingWriteError
            ) as raised:
                module.atomic_write_json(
                    mapping,
                    {"value": "new"},
                    expected_snapshot=snapshot,
                    fault_injector=modify_mapping,
                )

            self.assertFalse(raised.exception.replaced)
            self.assertEqual(concurrent, mapping.read_bytes())

    def test_atomic_mapping_writer_rejects_detached_parent_after_replace(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            sources = root / "docs" / "sources"
            sources.mkdir(parents=True)
            mapping = sources / "mapping.skills.json"
            before = b'{"value": "old"}\n'
            racer = b'{"value": "racer"}\n'
            mapping.write_bytes(before)
            detached = root / "detached-sources"

            def detach_parent(event):
                if event != "after_replace":
                    return
                sources.rename(detached)
                sources.mkdir()
                (sources / mapping.name).write_bytes(racer)

            with self.assertRaises(
                module.AtomicMappingWriteError
            ) as raised:
                module.atomic_write_json(
                    mapping,
                    {"value": "new"},
                    fault_injector=detach_parent,
                )

            self.assertTrue(raised.exception.replaced)
            self.assertEqual(racer, mapping.read_bytes())
            self.assertEqual(
                module.serialize_mapping_json({"value": "new"}),
                (detached / mapping.name).read_bytes(),
            )
            self.assertEqual([], list(detached.glob(".*.tmp")))

    def test_mapping_batch_rollback_never_overwrites_concurrent_occupant(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            first = root / "first.skills.json"
            second = root / "second.skills.json"
            first.write_text('{"value": "old-one"}\n', encoding="utf-8")
            second.write_text('{"value": "old-two"}\n', encoding="utf-8")
            concurrent = b'{"value": "concurrent"}\n'

            def replace_then_modify(event, path):
                if event == "after_replace" and path == first:
                    first.write_bytes(concurrent)
                    raise OSError("concurrent writer occupied first mapping")

            with self.assertRaises(
                module.AtomicMappingBatchError
            ) as raised:
                module.atomic_write_json_batch(
                    {
                        first: {"value": "new-one"},
                        second: {"value": "new-two"},
                    },
                    fault_injector=replace_then_modify,
                )

            self.assertFalse(raised.exception.rollback_succeeded)
            self.assertEqual(concurrent, first.read_bytes())
            self.assertEqual(
                b'{"value": "old-two"}\n',
                second.read_bytes(),
            )
            self.assertTrue(raised.exception.recovery_paths)
            self.assertTrue(
                any(
                    b'{"value": "old-one"}' in recovery.read_bytes()
                    for recovery in raised.exception.recovery_paths
                )
            )

    def test_atomic_mapping_batch_rolls_back_first_when_second_replace_fails(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            first = root / "first.skills.json"
            second = root / "second.skills.json"
            first.write_text('{"value": "old-one"}\n', encoding="utf-8")
            second.write_text('{"value": "old-two"}\n', encoding="utf-8")
            originals = {first: first.read_bytes(), second: second.read_bytes()}

            def fail_second(event, path):
                if event == "after_replace" and path == second:
                    raise OSError("second mapping replace fault")

            with self.assertRaises(
                module.AtomicMappingBatchError
            ) as raised:
                module.atomic_write_json_batch(
                    {
                        first: {"value": "new-one"},
                        second: {"value": "new-two"},
                    },
                    fault_injector=fail_second,
                )

            self.assertTrue(raised.exception.rollback_succeeded)
            self.assertEqual(originals[first], first.read_bytes())
            self.assertEqual(originals[second], second.read_bytes())

    def test_mapping_batch_pins_staged_inode_and_preserves_foreign_occupant(self):
        for replacement_kind in ("regular", "symlink"):
            with self.subTest(replacement_kind=replacement_kind):
                module = load_module()
                with tempfile.TemporaryDirectory() as tmpdir:
                    root = Path(tmpdir)
                    module.REPO_ROOT = root
                    first = root / "first.skills.json"
                    second = root / "second.skills.json"
                    first.write_text(
                        '{"value": "old-one"}\n', encoding="utf-8"
                    )
                    second.write_text(
                        '{"value": "old-two"}\n', encoding="utf-8"
                    )
                    originals = {
                        first: first.read_bytes(),
                        second: second.read_bytes(),
                    }
                    sentinel = b"foreign-batch-temporary"
                    symlink_target = root / "foreign-target"
                    symlink_target.write_bytes(sentinel)
                    foreign: list[Path] = []

                    def replace_staged_name(event, path):
                        if (
                            event != "after_stage"
                            or path != first
                            or foreign
                        ):
                            return
                        candidates = list(
                            root.glob(".first.skills.json.*.tmp")
                        )
                        self.assertEqual(1, len(candidates))
                        candidate = candidates[0]
                        candidate.unlink()
                        if replacement_kind == "symlink":
                            candidate.symlink_to(symlink_target)
                        else:
                            candidate.write_bytes(sentinel)
                        foreign.append(candidate)

                    with self.assertRaises(
                        module.AtomicMappingBatchError
                    ) as raised:
                        module.atomic_write_json_batch(
                            {
                                first: {"value": "new-one"},
                                second: {"value": "new-two"},
                            },
                            fault_injector=replace_staged_name,
                        )

                    self.assertTrue(raised.exception.rollback_succeeded)
                    self.assertEqual(originals[first], first.read_bytes())
                    self.assertEqual(originals[second], second.read_bytes())
                    self.assertEqual(1, len(foreign))
                    self.assertTrue(foreign[0].exists())
                    if replacement_kind == "symlink":
                        self.assertTrue(foreign[0].is_symlink())
                    else:
                        self.assertEqual(sentinel, foreign[0].read_bytes())
                    foreign[0].unlink()

    def test_mapping_batch_post_stage_failures_do_not_leak_fds(self):
        module = load_module()
        for replacement_kind in ("regular", "symlink", "missing"):
            with self.subTest(replacement_kind=replacement_kind):
                baseline_fds = self._open_fd_count()
                for _iteration in range(12):
                    with tempfile.TemporaryDirectory() as tmpdir:
                        root = Path(tmpdir)
                        module.REPO_ROOT = root
                        mapping = root / "mapping.skills.json"
                        original = b'{"value": "old"}\n'
                        mapping.write_bytes(original)
                        real_secure, foreign, sentinel = (
                            self._install_post_stage_metadata_attack(
                                module,
                                root=root,
                                replacement_kind=replacement_kind,
                                selector=lambda path: path.name.endswith(
                                    ".tmp"
                                ),
                            )
                        )
                        try:
                            with self.assertRaises(
                                module.AtomicMappingBatchError
                            ) as raised:
                                module._atomic_write_json_batch_locked(
                                    {mapping: {"value": "new"}},
                                )
                        finally:
                            module._secure_temporary_metadata = real_secure

                        self.assertTrue(
                            raised.exception.rollback_succeeded
                        )
                        self.assertEqual(original, mapping.read_bytes())
                        self._assert_foreign_stage_state(
                            foreign,
                            replacement_kind,
                            sentinel,
                        )
                    self.assertEqual(
                        baseline_fds,
                        self._open_fd_count(),
                    )

    def test_atomic_mapping_batch_surfaces_recovery_files_when_rollback_fails(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            first = root / "first.skills.json"
            second = root / "second.skills.json"
            first.write_text('{"value": "old-one"}\n', encoding="utf-8")
            second.write_text('{"value": "old-two"}\n', encoding="utf-8")

            def fail_second(event, path):
                if event == "after_replace" and path == second:
                    raise OSError("forward fault")

            real_replace = module.os.replace

            def fail_rollback(source, target, **kwargs):
                if str(source).endswith(".rollback.tmp"):
                    raise OSError("rollback fault")
                return real_replace(source, target, **kwargs)

            module.os.replace = fail_rollback
            try:
                with self.assertRaises(
                    module.AtomicMappingBatchError
                ) as raised:
                    module.atomic_write_json_batch(
                        {
                            first: {"value": "new-one"},
                            second: {"value": "new-two"},
                        },
                        fault_injector=fail_second,
                    )
            finally:
                module.os.replace = real_replace

            self.assertFalse(raised.exception.rollback_succeeded)
            self.assertTrue(raised.exception.recovery_paths)
            self.assertTrue(
                all(path.is_file() for path in raised.exception.recovery_paths)
            )

    def test_batch_rollback_temp_pin_preserves_foreign_occupant(self):
        for replacement_kind in ("regular", "symlink"):
            with self.subTest(replacement_kind=replacement_kind):
                module = load_module()
                with tempfile.TemporaryDirectory() as tmpdir:
                    root = Path(tmpdir)
                    module.REPO_ROOT = root
                    first = root / "first.skills.json"
                    second = root / "second.skills.json"
                    first.write_text(
                        '{"value": "old-one"}\n', encoding="utf-8"
                    )
                    second.write_text(
                        '{"value": "old-two"}\n', encoding="utf-8"
                    )
                    sentinel = b"foreign-rollback-temporary"
                    symlink_target = root / "foreign-target"
                    symlink_target.write_bytes(sentinel)
                    foreign: list[Path] = []

                    def fail_second(event, path):
                        if event == "after_replace" and path == second:
                            raise OSError("force rollback")

                    real_pin = module._pin_temporary_inode

                    def replace_after_pin(path, directory_fd):
                        descriptor, metadata = real_pin(path, directory_fd)
                        candidate = Path(path)
                        if (
                            candidate.name.endswith(".rollback.tmp")
                            and not foreign
                        ):
                            candidate.unlink()
                            if replacement_kind == "symlink":
                                candidate.symlink_to(symlink_target)
                            else:
                                candidate.write_bytes(sentinel)
                            foreign.append(candidate)
                        return descriptor, metadata

                    module._pin_temporary_inode = replace_after_pin
                    try:
                        with self.assertRaises(
                            module.AtomicMappingBatchError
                        ) as raised:
                            module.atomic_write_json_batch(
                                {
                                    first: {"value": "new-one"},
                                    second: {"value": "new-two"},
                                },
                                fault_injector=fail_second,
                            )
                    finally:
                        module._pin_temporary_inode = real_pin

                    self.assertFalse(raised.exception.rollback_succeeded)
                    self.assertTrue(raised.exception.recovery_paths)
                    self.assertEqual(1, len(foreign))
                    self.assertTrue(foreign[0].exists())
                    if replacement_kind == "symlink":
                        self.assertTrue(foreign[0].is_symlink())
                    else:
                        self.assertEqual(sentinel, foreign[0].read_bytes())
                    foreign[0].unlink()

    def test_batch_rollback_post_stage_failures_do_not_leak_fds(self):
        module = load_module()
        for replacement_kind in ("regular", "symlink", "missing"):
            with self.subTest(replacement_kind=replacement_kind):
                baseline_fds = self._open_fd_count()
                for _iteration in range(12):
                    with tempfile.TemporaryDirectory() as tmpdir:
                        root = Path(tmpdir)
                        module.REPO_ROOT = root
                        first = root / "first.skills.json"
                        second = root / "second.skills.json"
                        first_original = b'{"value": "old-one"}\n'
                        second_original = b'{"value": "old-two"}\n'
                        first.write_bytes(first_original)
                        second.write_bytes(second_original)

                        def fail_after_second_replace(event, path):
                            if event == "after_replace" and path == second:
                                raise OSError("force rollback")

                        real_secure, foreign, sentinel = (
                            self._install_post_stage_metadata_attack(
                                module,
                                root=root,
                                replacement_kind=replacement_kind,
                                selector=lambda path: (
                                    path.name.startswith(
                                        ".second.skills.json."
                                    )
                                    and path.name.endswith(".rollback.tmp")
                                ),
                            )
                        )
                        try:
                            with self.assertRaises(
                                module.AtomicMappingBatchError
                            ) as raised:
                                module._atomic_write_json_batch_locked(
                                    {
                                        first: {"value": "new-one"},
                                        second: {"value": "new-two"},
                                    },
                                    fault_injector=fail_after_second_replace,
                                )
                        finally:
                            module._secure_temporary_metadata = real_secure

                        self.assertFalse(
                            raised.exception.rollback_succeeded
                        )
                        self.assertEqual(first_original, first.read_bytes())
                        self.assertFalse(second.is_symlink())
                        self.assertNotEqual(sentinel, second.read_bytes())
                        self._assert_foreign_stage_state(
                            foreign,
                            replacement_kind,
                            sentinel,
                        )
                    self.assertEqual(
                        baseline_fds,
                        self._open_fd_count(),
                    )

    def test_private_recovery_pin_preserves_foreign_occupant(self):
        for replacement_kind in ("regular", "symlink"):
            with self.subTest(replacement_kind=replacement_kind):
                module = load_module()
                with tempfile.TemporaryDirectory() as tmpdir:
                    root = Path(tmpdir)
                    module.REPO_ROOT = root
                    mapping = root / "mapping.skills.json"
                    mapping.write_text(
                        '{"value": "old"}\n', encoding="utf-8"
                    )
                    sentinel = b"foreign-private-recovery"
                    symlink_target = root / "foreign-target"
                    symlink_target.write_bytes(sentinel)
                    foreign: list[Path] = []
                    real_pin = module._pin_temporary_inode

                    def replace_after_pin(path, directory_fd):
                        descriptor, metadata = real_pin(path, directory_fd)
                        candidate = Path(path)
                        if (
                            candidate.name.endswith(".recovery.json")
                            and not foreign
                        ):
                            candidate.unlink()
                            if replacement_kind == "symlink":
                                candidate.symlink_to(symlink_target)
                            else:
                                candidate.write_bytes(sentinel)
                            foreign.append(candidate)
                        return descriptor, metadata

                    module._pin_temporary_inode = replace_after_pin
                    try:
                        with self.assertRaisesRegex(
                            RuntimeError,
                            "temporary inode changed|temporary is unsafe",
                        ):
                            module._stage_private_mapping_recovery(
                                mapping,
                                b'{"value": "recovery"}\n',
                            )
                    finally:
                        module._pin_temporary_inode = real_pin

                    self.assertEqual(1, len(foreign))
                    self.assertTrue(foreign[0].exists())
                    if replacement_kind == "symlink":
                        self.assertTrue(foreign[0].is_symlink())
                    else:
                        self.assertEqual(sentinel, foreign[0].read_bytes())
                    foreign[0].unlink()

    def test_mapping_batch_rejects_detached_parent_after_replace(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            sources = root / "docs" / "sources"
            sources.mkdir(parents=True)
            mapping = sources / "mapping.skills.json"
            mapping.write_text('{"value": "old"}\n', encoding="utf-8")
            detached = root / "detached-sources"
            racer = b'{"value": "racer"}\n'

            def detach_parent(event, path):
                if event != "after_replace" or path != mapping:
                    return
                sources.rename(detached)
                sources.mkdir()
                (sources / mapping.name).write_bytes(racer)

            with self.assertRaises(
                module.AtomicMappingBatchError
            ) as raised:
                module.atomic_write_json_batch(
                    {mapping: {"value": "new"}},
                    fault_injector=detach_parent,
                )

            self.assertFalse(raised.exception.rollback_succeeded)
            self.assertEqual(racer, mapping.read_bytes())
            self.assertTrue(raised.exception.recovery_paths)

    def test_mapping_batch_rollback_rejects_detached_parent_and_recovers(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            sources = root / "docs" / "sources"
            sources.mkdir(parents=True)
            mapping = sources / "mapping.skills.json"
            original = b'{"value": "old"}\n'
            racer = b'{"value": "racer"}\n'
            mapping.write_bytes(original)
            detached = root / "detached-sources"

            def fail_forward(event, path):
                if event == "after_replace" and path == mapping:
                    raise OSError("force rollback")

            real_replace = module.os.replace

            def detach_after_rollback(source, target, **kwargs):
                result = real_replace(source, target, **kwargs)
                if str(source).endswith(".rollback.tmp"):
                    sources.rename(detached)
                    sources.mkdir()
                    (sources / mapping.name).write_bytes(racer)
                return result

            module.os.replace = detach_after_rollback
            try:
                with self.assertRaises(
                    module.AtomicMappingBatchError
                ) as raised:
                    module.atomic_write_json_batch(
                        {mapping: {"value": "new"}},
                        fault_injector=fail_forward,
                    )
            finally:
                module.os.replace = real_replace

            self.assertFalse(raised.exception.rollback_succeeded)
            self.assertEqual(racer, mapping.read_bytes())
            self.assertEqual(original, (detached / mapping.name).read_bytes())
            self.assertTrue(raised.exception.recovery_paths)
            self.assertTrue(
                all(path.is_file() for path in raised.exception.recovery_paths)
            )
            self.assertTrue(
                any(
                    path.read_bytes() == original
                    for path in raised.exception.recovery_paths
                )
            )

    def test_candidate_validation_cleanup_uses_pinned_parent_inode(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            module.REPO_ROOT = root
            sources = root / "docs" / "sources"
            sources.mkdir(parents=True)
            module.SOURCE_MAPPINGS_DIR = sources
            mapping = sources / "mapping.skills.json"
            mapping.write_text('{"schema_version": 2}\n', encoding="utf-8")
            detached = root / "detached-sources"
            sentinel = b"do-not-delete"

            original_validate = module.validate_provenance_mapping
            original_repository_validate = module.validate_repository_mappings
            module.validate_provenance_mapping = lambda *_args, **_kwargs: []

            def detach_during_validation(paths, _root):
                staged = next(
                    path
                    for path in paths
                    if path.name.endswith(".validation.skills.json")
                )
                sources.rename(detached)
                sources.mkdir()
                (sources / staged.name).write_bytes(sentinel)
                return []

            module.validate_repository_mappings = detach_during_validation
            try:
                with self.assertRaisesRegex(
                    RuntimeError, "cleanup failed safely"
                ):
                    module._validate_candidate_mappings(
                        {mapping: {"schema_version": 2}}
                    )
            finally:
                module.validate_provenance_mapping = original_validate
                module.validate_repository_mappings = (
                    original_repository_validate
                )

            self.assertEqual(
                [sentinel],
                [
                    path.read_bytes()
                    for path in sources.glob(
                        ".*.validation.skills.json"
                    )
                ],
            )
            self.assertEqual(
                [],
                list(detached.glob(".*.validation.skills.json")),
            )

    def test_candidate_validation_pins_temp_and_preserves_foreign_occupant(self):
        for replacement_kind in ("regular", "symlink"):
            with self.subTest(replacement_kind=replacement_kind):
                module = load_module()
                with tempfile.TemporaryDirectory() as tmpdir:
                    root = Path(tmpdir)
                    module.REPO_ROOT = root
                    sources = root / "docs" / "sources"
                    sources.mkdir(parents=True)
                    module.SOURCE_MAPPINGS_DIR = sources
                    mapping = sources / "mapping.skills.json"
                    mapping.write_text(
                        '{"schema_version": 2}\n',
                        encoding="utf-8",
                    )
                    sentinel = b"foreign-validation-temporary"
                    symlink_target = root / "foreign-target"
                    symlink_target.write_bytes(sentinel)
                    foreign: list[Path] = []
                    original_validate = module.validate_provenance_mapping
                    original_repository_validate = (
                        module.validate_repository_mappings
                    )

                    def replace_validation_temp(path, *_args, **_kwargs):
                        candidate = Path(path)
                        candidate.unlink()
                        if replacement_kind == "symlink":
                            candidate.symlink_to(symlink_target)
                        else:
                            candidate.write_bytes(sentinel)
                        foreign.append(candidate)
                        return []

                    module.validate_provenance_mapping = (
                        replace_validation_temp
                    )
                    module.validate_repository_mappings = (
                        lambda *_args, **_kwargs: []
                    )
                    try:
                        with self.assertRaisesRegex(
                            RuntimeError,
                            "temporary inode changed|temporary is unsafe",
                        ):
                            module._validate_candidate_mappings(
                                {mapping: {"schema_version": 2}}
                            )
                    finally:
                        module.validate_provenance_mapping = original_validate
                        module.validate_repository_mappings = (
                            original_repository_validate
                        )

                    self.assertEqual(1, len(foreign))
                    self.assertTrue(foreign[0].exists())
                    if replacement_kind == "symlink":
                        self.assertTrue(foreign[0].is_symlink())
                    else:
                        self.assertEqual(sentinel, foreign[0].read_bytes())
                    foreign[0].unlink()

    def test_candidate_post_stage_failures_do_not_leak_fds(self):
        module = load_module()
        original_validate = module.validate_provenance_mapping
        original_repository_validate = module.validate_repository_mappings
        module.validate_provenance_mapping = lambda *_args, **_kwargs: []
        module.validate_repository_mappings = lambda *_args, **_kwargs: []
        try:
            for replacement_kind in ("regular", "symlink", "missing"):
                with self.subTest(replacement_kind=replacement_kind):
                    baseline_fds = self._open_fd_count()
                    for _iteration in range(12):
                        with tempfile.TemporaryDirectory() as tmpdir:
                            root = Path(tmpdir)
                            module.REPO_ROOT = root
                            sources = root / "docs" / "sources"
                            sources.mkdir(parents=True)
                            module.SOURCE_MAPPINGS_DIR = sources
                            mapping = sources / "mapping.skills.json"
                            original = b'{"schema_version": 2}\n'
                            mapping.write_bytes(original)
                            real_secure, foreign, sentinel = (
                                self._install_post_stage_metadata_attack(
                                    module,
                                    root=root,
                                    replacement_kind=replacement_kind,
                                    selector=lambda path: path.name.endswith(
                                        ".validation.skills.json"
                                    ),
                                )
                            )
                            try:
                                with self.assertRaises(
                                    (RuntimeError, FileNotFoundError)
                                ):
                                    module._validate_candidate_mappings(
                                        {mapping: {"schema_version": 2}}
                                    )
                            finally:
                                module._secure_temporary_metadata = (
                                    real_secure
                                )

                            self.assertEqual(original, mapping.read_bytes())
                            self._assert_foreign_stage_state(
                                foreign,
                                replacement_kind,
                                sentinel,
                            )
                        self.assertEqual(
                            baseline_fds,
                            self._open_fd_count(),
                        )
        finally:
            module.validate_provenance_mapping = original_validate
            module.validate_repository_mappings = original_repository_validate

    def test_report_json_exposes_degraded_state_and_conserved_counts(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "report.json"
            skill = {
                "name": "demo",
                "category": "ai-workflow",
                "source": "github:owner/repo",
                "repo": "owner/repo",
                "schema_version": 2,
            }
            exit_code, _output = self._run_main(
                module,
                ["--check-only", "--report-json", str(report_path)],
                [skill],
                lambda checked, _token: {
                    "skill": checked,
                    "changes": "monitor_review",
                    "current_commit": "a" * 40,
                },
            )

            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(2, exit_code)
            self.assertEqual("degraded", report["state"])
            self.assertEqual(
                report["summary"]["total"],
                sum(
                    report["summary"][key]
                    for key in (
                        "equal",
                        "changed",
                        "monitor_review",
                        "unavailable",
                        "rollback",
                        "expected_skipped",
                    )
                ),
            )

    def test_report_json_exposes_complete_and_failed_states(self):
        for label, checker, expected_code, expected_state in (
            (
                "complete",
                lambda checked, _token: {
                    "skill": checked,
                    "changes": "none",
                },
                0,
                "complete",
            ),
            (
                "failed",
                lambda _checked, _token: None,
                1,
                "failed",
            ),
        ):
            with self.subTest(state=label), tempfile.TemporaryDirectory() as tmpdir:
                module = load_module()
                report_path = Path(tmpdir) / "report.json"
                skill = {
                    "name": "demo",
                    "category": "ai-workflow",
                    "source": "github:owner/repo",
                    "repo": "owner/repo",
                    "schema_version": 2,
                }
                exit_code, _output = self._run_main(
                    module,
                    ["--check-only", "--report-json", str(report_path)],
                    [skill],
                    checker,
                )
                report = json.loads(report_path.read_text(encoding="utf-8"))
                self.assertEqual(expected_code, exit_code)
                self.assertEqual(expected_state, report["state"])


if __name__ == "__main__":
    unittest.main()
