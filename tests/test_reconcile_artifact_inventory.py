import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = REPO_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


provenance = load_script("provenance_v2")
validator = load_script("validate_skill_sources")
inventory = load_script("reconcile_artifact_inventory")
openclaw_export = load_script("export_openclaw_skills")

COMMIT = "a" * 40
ROOT_TREE = "b" * 40
MAIN_BLOB = "1" * 40
EXACT_BLOB = "2" * 40
UNAVAILABLE_BLOB = "3" * 40


def write_skill(root: Path, slug: str = "demo") -> str:
    relative = f"skills/category/{slug}/SKILL.md"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"name: {slug}\n"
        "description: Test skill\n"
        "zh_description: 测试技能\n"
        "version: 1.0.0\n"
        "author: tester\n"
        "source: github:owner/upstream\n"
        'source_url: "https://github.com/owner/upstream"\n'
        "license: MIT\n"
        "tags: [test]\n"
        'created_at: "2026-08-20"\n'
        'updated_at: "2026-08-20"\n'
        "quality: 2\n"
        "complexity: beginner\n"
        "---\n"
        "# Demo\n",
        encoding="utf-8",
    )
    return relative


def make_entry(root: Path, slug: str = "demo") -> dict:
    repo_skill = f"skills/category/{slug}/SKILL.md"
    content_hash = provenance.sha256_file(root / repo_skill)
    return {
        "video_name": slug,
        "normalized_slug": slug,
        "status": "verified_in_repo",
        "repo_skill": repo_skill,
        "source": "https://github.com/owner/upstream/tree/main/upstream/demo",
        "notes": "External test mirror.",
        "kind": "mirror",
        "sync_mode": "monitor",
        "upstream": {
            "repo": "owner/upstream",
            "path": "upstream/demo/SKILL.md",
            "ref": "main",
            "sync_mode": "monitor",
            "last_checked_at": "2026-08-20",
            "last_synced_at": "2026-08-20",
            "last_synced_commit": COMMIT,
        },
        "origins": [
            {
                "repo": "owner/upstream",
                "path": "upstream/demo/SKILL.md",
                "license": "MIT",
                "sync_mode": "monitor",
                "artifacts": [
                    {
                        "source": "upstream/demo/SKILL.md",
                        "target": repo_skill,
                        "type": "file",
                    }
                ],
                "tracking": {
                    "channel": "default_branch",
                    "ref": "main",
                    "resolved_commit": COMMIT,
                    "path_commit": COMMIT,
                    "content_sha256": content_hash,
                    "last_checked_at": "2026-08-20",
                    "last_synced_at": "2026-08-20",
                },
            }
        ],
        "managed_files": [
            {
                "path": repo_skill,
                "sha256": content_hash,
                "owner": slug,
                "mode": "100644",
            }
        ],
    }


def make_payload(entry: dict) -> dict:
    return {
        "schema_version": 2,
        "video": {"url": "https://example.com", "checked_at": "2026-08-20"},
        "official_references": [],
        "skills": [entry],
    }


def write_tree_fixture(
    cache: inventory.GitHubObjectCache,
    entries: list[dict],
) -> None:
    normalized_entries = [
        (
            {**entry, "mode": entry.get("mode", "100644")}
            if entry.get("type") == "blob"
            else dict(entry)
        )
        for entry in entries
    ]
    path = cache.tree_cache_path("owner/upstream", COMMIT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "sha": COMMIT,
                "truncated": False,
                "tree": normalized_entries,
            }
        ),
        encoding="utf-8",
    )


def write_blob_fixture(
    cache: inventory.GitHubObjectCache,
    object_sha: str,
    content: bytes,
) -> None:
    path = cache.blob_cache_path("owner/upstream", object_sha)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def online_tree_responder(entries: list[dict]):
    normalized_entries = [
        (
            {**entry, "mode": entry.get("mode", "100644")}
            if entry.get("type") == "blob"
            else dict(entry)
        )
        for entry in entries
    ]

    def respond(endpoint: str, *, fields: dict[str, str] | None = None):
        if endpoint == f"repos/owner/upstream/git/commits/{COMMIT}":
            return {"sha": COMMIT, "tree": {"sha": ROOT_TREE}}
        if endpoint == f"repos/owner/upstream/git/trees/{ROOT_TREE}":
            if fields != {"recursive": "1"}:
                raise AssertionError(f"missing recursive tree request: {fields!r}")
            return {
                "sha": ROOT_TREE,
                "truncated": False,
                "tree": normalized_entries,
            }
        raise AssertionError(f"unexpected GitHub endpoint: {endpoint}")

    return respond


class ArtifactInventoryTests(unittest.TestCase):
    def test_repository_managed_files_are_present_in_git_index(self):
        try:
            tracked_output = subprocess.check_output(
                ["git", "ls-files", "--cached", "-z", "--", "skills"],
                cwd=REPO_ROOT,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            self.skipTest("repository Git index is unavailable")

        tracked = {
            value.decode("utf-8")
            for value in tracked_output.split(b"\0")
            if value
        }
        managed: set[str] = set()
        source_root = REPO_ROOT / "docs" / "sources"
        mapping_paths = sorted(source_root.glob("*.skills.json"))
        mapping_paths.extend(sorted(source_root.glob("*.bundle.json")))
        for mapping_path in mapping_paths:
            payload = json.loads(mapping_path.read_text(encoding="utf-8"))
            for entry in payload.get("skills", []):
                if not isinstance(entry, dict):
                    continue
                for record in entry.get("managed_files", []):
                    if isinstance(record, dict) and isinstance(
                        record.get("path"), str
                    ):
                        managed.add(record["path"])

        missing = sorted(managed - tracked)
        self.assertEqual(
            [],
            missing,
            "Every managed artifact must be committed to the Git index; "
            "fresh checkouts cannot rely on ignored or untracked files.",
        )

    def test_openclaw_export_contains_every_canonical_skill_file_in_git_index(
        self,
    ):
        try:
            tracked_output = subprocess.check_output(
                [
                    "git",
                    "ls-files",
                    "--cached",
                    "-z",
                    "--",
                    "openclaw-skills",
                ],
                cwd=REPO_ROOT,
            )
            canonical_output = subprocess.check_output(
                ["git", "ls-files", "--cached", "-z", "--", "skills"],
                cwd=REPO_ROOT,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            self.skipTest("repository Git index is unavailable")

        tracked = {
            value.decode("utf-8")
            for value in tracked_output.split(b"\0")
            if value
        }
        missing: list[str] = []
        mismatched: list[str] = []
        canonical_paths = sorted(
            value.decode("utf-8")
            for value in canonical_output.split(b"\0")
            if value
        )
        for canonical_relative in canonical_paths:
            parts = Path(canonical_relative).parts
            if len(parts) < 4:
                continue
            skill_root = Path(*parts[:3])
            if not (REPO_ROOT / skill_root / "SKILL.md").is_file():
                continue
            relative = Path(*parts[3:])
            if any(part in openclaw_export.IGNORED_NAMES for part in relative.parts):
                continue
            export_relative = (
                Path("openclaw-skills") / parts[2] / relative
            ).as_posix()
            canonical = REPO_ROOT / canonical_relative
            exported = REPO_ROOT / export_relative
            if (
                canonical.is_symlink()
                or export_relative not in tracked
                or not exported.is_file()
            ):
                missing.append(export_relative)
                continue
            expected = canonical.read_bytes()
            if canonical.name == openclaw_export.SKILL_FILENAME:
                expected = openclaw_export.normalize_skill_markdown(
                    canonical.parent.name,
                    canonical.read_text(encoding="utf-8"),
                ).encode("utf-8")
            if expected != exported.read_bytes():
                mismatched.append(export_relative)

        self.assertEqual(
            [],
            missing,
            "Every canonical skill artifact must exist in the tracked "
            "OpenClaw export.",
        )
        self.assertEqual(
            [],
            mismatched,
            "Tracked OpenClaw sidecars must be byte-identical and SKILL.md "
            "files must match the canonical OpenClaw normalization.",
        )

    def test_cached_blob_must_match_declared_git_oid_and_size(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_skill(root)
            entry = make_entry(root)
            target = "skills/category/demo/references/forged.bin"
            content = b"locally exact but cache key is forged"
            (root / target).parent.mkdir(parents=True)
            (root / target).write_bytes(content)
            forged_oid = "2" * 40
            cache = inventory.GitHubObjectCache(root / "cache", offline=True)
            write_tree_fixture(
                cache,
                [
                    {
                        "path": "upstream/demo/references/forged.bin",
                        "type": "blob",
                        "sha": forged_oid,
                        "size": len(content),
                    }
                ],
            )
            write_blob_fixture(cache, forged_oid, content)

            inspection = inventory.inspect_entry(
                entry,
                repo_root=root,
                cache=cache,
            )
            proposal = next(
                item for item in inspection["unowned"] if item["target"] == target
            )
            self.assertEqual("unavailable", proposal["classification"])
            self.assertIn("object id", proposal["reason"])

    def test_forged_offline_tree_with_valid_blob_oid_cannot_authorize_external(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_skill(root)
            entry = make_entry(root)
            target = "skills/category/demo/references/forged.md"
            content = b"local bytes with a valid Git object id\n"
            (root / target).parent.mkdir(parents=True)
            (root / target).write_bytes(content)
            object_sha = inventory._git_blob_oid(content, "sha1")
            cache = inventory.GitHubObjectCache(root / "cache", offline=True)
            write_tree_fixture(
                cache,
                [
                    {
                        "path": "upstream/demo/references/forged.md",
                        "type": "blob",
                        "sha": object_sha,
                        "size": len(content),
                    }
                ],
            )

            inspection = inventory.inspect_entry(
                entry,
                repo_root=root,
                cache=cache,
            )
            proposal = next(
                item for item in inspection["unowned"] if item["target"] == target
            )

            self.assertEqual("unavailable", proposal["classification"])
            self.assertIn("cannot authorize", proposal["reason"])
            self.assertEqual(
                "offline_authority_forbidden",
                proposal["checked_sources"][0]["result"],
            )

    def test_tree_ignores_symlink_git_mode_120000(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            content = b"references/outside.md"
            object_sha = inventory._git_blob_oid(content, "sha1")
            cache = inventory.GitHubObjectCache(root / "cache", offline=True)
            write_tree_fixture(
                cache,
                [
                    {
                        "path": "upstream/demo/link.md",
                        "type": "blob",
                        "mode": "120000",
                        "sha": object_sha,
                        "size": len(content),
                    }
                ],
            )

            self.assertEqual(
                {},
                cache.get_tree("owner/upstream", COMMIT),
            )

    def test_online_tree_ignores_forged_disk_cache_and_binds_commit_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_skill(root)
            entry = make_entry(root)
            target = "skills/category/demo/references/forged.md"
            content = b"forged cached lineage\n"
            (root / target).parent.mkdir(parents=True)
            (root / target).write_bytes(content)
            object_sha = inventory._git_blob_oid(content, "sha1")
            cache = inventory.GitHubObjectCache(root / "cache", offline=False)
            write_tree_fixture(
                cache,
                [
                    {
                        "path": "upstream/demo/references/forged.md",
                        "type": "blob",
                        "sha": object_sha,
                        "size": len(content),
                    }
                ],
            )

            with mock.patch.object(
                cache,
                "_gh_json",
                side_effect=online_tree_responder([]),
            ) as fetch:
                inspection = inventory.inspect_entry(
                    entry,
                    repo_root=root,
                    cache=cache,
                )

            proposal = next(
                item for item in inspection["unowned"] if item["target"] == target
            )
            self.assertEqual("local_overlay", proposal["classification"])
            self.assertEqual(2, fetch.call_count)
            self.assertEqual(
                f"repos/owner/upstream/git/commits/{COMMIT}",
                fetch.call_args_list[0].args[0],
            )
            self.assertEqual(
                f"repos/owner/upstream/git/trees/{ROOT_TREE}",
                fetch.call_args_list[1].args[0],
            )

    def test_online_tree_commit_binding_mismatch_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_skill(root)
            entry = make_entry(root)
            target = "skills/category/demo/references/untrusted.md"
            (root / target).parent.mkdir(parents=True)
            (root / target).write_bytes(b"local\n")
            cache = inventory.GitHubObjectCache(root / "cache", offline=False)

            with mock.patch.object(
                cache,
                "_gh_json",
                return_value={
                    "sha": "c" * 40,
                    "tree": {"sha": ROOT_TREE},
                },
            ):
                inspection = inventory.inspect_entry(
                    entry,
                    repo_root=root,
                    cache=cache,
                )

            proposal = next(
                item for item in inspection["unowned"] if item["target"] == target
            )
            self.assertEqual("unavailable", proposal["classification"])
            self.assertIn("commit/root-tree binding", proposal["reason"])

    def test_api_blob_requires_strict_base64_oid_and_size(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            content = b"valid bytes"
            oid = inventory._git_blob_oid(content, "sha1")
            cache = inventory.GitHubObjectCache(Path(tmpdir))
            with mock.patch.object(
                cache,
                "_gh_json",
                return_value={
                    "sha": oid,
                    "size": len(content),
                    "encoding": "base64",
                    "content": "%%%not-base64%%%",
                },
            ):
                with self.assertRaisesRegex(
                    inventory.SourceUnavailable,
                    "base64",
                ):
                    cache.get_blob("owner/upstream", oid, expected_size=len(content))

            bad_oid = "3" * 40
            with mock.patch.object(
                cache,
                "_gh_json",
                return_value={
                    "sha": bad_oid,
                    "size": len(content),
                    "encoding": "base64",
                    "content": "dmFsaWQgYnl0ZXM=",
                },
            ):
                with self.assertRaisesRegex(
                    inventory.SourceUnavailable,
                    "object id",
                ):
                    cache.get_blob(
                        "owner/upstream",
                        bad_oid,
                        expected_size=len(content),
                    )

    def test_cache_ancestor_symlink_is_never_followed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cache_root = root / "cache"
            outside = root / "outside"
            outside.mkdir()
            content = b"outside cache bytes"
            oid = inventory._git_blob_oid(content, "sha1")
            outside_blob_dir = outside / "owner__upstream"
            outside_blob_dir.mkdir()
            (outside_blob_dir / f"{oid}.bin").write_bytes(content)
            (cache_root / "blobs").mkdir(parents=True)
            (cache_root / "blobs/owner__upstream").symlink_to(
                outside_blob_dir,
                target_is_directory=True,
            )
            cache = inventory.GitHubObjectCache(cache_root, offline=True)

            with self.assertRaisesRegex(inventory.SourceUnavailable, "symlink"):
                cache.get_blob(
                    "owner/upstream",
                    oid,
                    expected_size=len(content),
                )

    def test_exact_binary_and_local_overlay_are_classified_by_expected_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_skill = write_skill(root)
            entry = make_entry(root)
            exact_target = "skills/category/demo/references/exact.bin"
            overlay_target = "skills/category/demo/src/runtime.py"
            exact_bytes = b"\x00\xffbinary\n"
            overlay_bytes = b"same bytes elsewhere"
            exact_blob = inventory._git_blob_oid(exact_bytes, "sha1")
            (root / exact_target).parent.mkdir(parents=True)
            (root / exact_target).write_bytes(exact_bytes)
            (root / overlay_target).parent.mkdir(parents=True)
            (root / overlay_target).write_bytes(overlay_bytes)

            cache = inventory.GitHubObjectCache(
                root / "cache",
                offline=False,
            )
            trusted_entries = [
                {
                    "path": "upstream/demo/SKILL.md",
                    "type": "blob",
                    "sha": MAIN_BLOB,
                    "size": 0,
                },
                {
                    "path": "upstream/demo/references/exact.bin",
                    "type": "blob",
                    "sha": exact_blob,
                    "size": len(exact_bytes),
                },
                # A repository-wide hash match outside the declared official
                # skill root must not be attributed to that origin.
                {
                    "path": "src/runtime.py",
                    "type": "blob",
                    "sha": UNAVAILABLE_BLOB,
                    "size": len(overlay_bytes),
                },
            ]

            with mock.patch.object(
                cache,
                "_gh_json",
                side_effect=online_tree_responder(trusted_entries),
            ):
                report = inventory.inspect_entry(
                    entry,
                    repo_root=root,
                    cache=cache,
                )
            by_target = {item["target"]: item for item in report["unowned"]}

            self.assertEqual(
                "external_exact",
                by_target[exact_target]["classification"],
            )
            self.assertEqual("100644", by_target[exact_target]["mode"])
            self.assertEqual(
                "upstream/demo/references/exact.bin",
                by_target[exact_target]["source"],
            )
            self.assertEqual(
                "local_overlay",
                by_target[overlay_target]["classification"],
            )
            self.assertEqual("100644", by_target[overlay_target]["mode"])
            self.assertEqual(overlay_target, by_target[overlay_target]["source"])
            self.assertIn(repo_skill, report["actual_files"])

    def test_external_exact_requires_matching_blob_bytes_and_tree_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_skill(root)
            entry = make_entry(root)
            target = "skills/category/demo/references/executable.sh"
            content = b"#!/bin/sh\nexit 0\n"
            target_path = root / target
            target_path.parent.mkdir(parents=True)
            target_path.write_bytes(content)
            target_path.chmod(0o755)
            object_sha = inventory._git_blob_oid(content, "sha1")
            source = "upstream/demo/references/executable.sh"

            mismatched_cache = inventory.GitHubObjectCache(
                root / "mismatch-cache",
                offline=False,
            )
            with mock.patch.object(
                mismatched_cache,
                "_gh_json",
                side_effect=online_tree_responder(
                    [
                        {
                            "path": source,
                            "type": "blob",
                            "mode": "100644",
                            "sha": object_sha,
                            "size": len(content),
                        }
                    ]
                ),
            ):
                mismatched = inventory.inspect_entry(
                    entry,
                    repo_root=root,
                    cache=mismatched_cache,
                )
            proposal = next(
                item for item in mismatched["unowned"] if item["target"] == target
            )
            self.assertEqual("local_overlay", proposal["classification"])
            self.assertEqual("100755", proposal["mode"])
            self.assertEqual(
                "mode_mismatch",
                proposal["checked_sources"][0]["result"],
            )

            matching_cache = inventory.GitHubObjectCache(
                root / "matching-cache",
                offline=False,
            )
            with mock.patch.object(
                matching_cache,
                "_gh_json",
                side_effect=online_tree_responder(
                    [
                        {
                            "path": source,
                            "type": "blob",
                            "mode": "100755",
                            "sha": object_sha,
                            "size": len(content),
                        }
                    ]
                ),
            ):
                matching = inventory.inspect_entry(
                    entry,
                    repo_root=root,
                    cache=matching_cache,
                )
            proposal = next(
                item for item in matching["unowned"] if item["target"] == target
            )
            self.assertEqual("external_exact", proposal["classification"])
            self.assertEqual("100755", proposal["mode"])

    def test_blob_404_is_unavailable_instead_of_becoming_local_overlay(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_skill(root)
            entry = make_entry(root)
            target = "skills/category/demo/references/missing.bin"
            (root / target).parent.mkdir(parents=True)
            (root / target).write_bytes(b"local")
            cache = inventory.GitHubObjectCache(root / "cache", offline=True)
            write_tree_fixture(
                cache,
                [
                    {
                        "path": "upstream/demo/references/missing.bin",
                        "type": "blob",
                        "sha": UNAVAILABLE_BLOB,
                        "size": len(b"local"),
                    }
                ],
            )

            report = inventory.inspect_entry(entry, repo_root=root, cache=cache)

            self.assertEqual("unavailable", report["unowned"][0]["classification"])
            self.assertIn("offline cache miss", report["unowned"][0]["reason"])

    def test_transformed_standalone_entrypoint_does_not_claim_package_siblings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_skill(root)
            entry = make_entry(root)
            origin = entry["origins"][0]
            origin["path"] = "graphify/skill-codex.md"
            origin["artifacts"][0]["source"] = "graphify/skill-codex.md"
            entry["upstream"]["path"] = "graphify/skill-codex.md"
            target = "skills/category/demo/runtime.py"
            content = b"package snapshot"
            (root / target).write_bytes(content)
            object_sha = inventory._git_blob_oid(content, "sha1")
            cache = inventory.GitHubObjectCache(root / "cache", offline=True)
            write_tree_fixture(
                cache,
                [
                    {
                        "path": "graphify/runtime.py",
                        "type": "blob",
                        "sha": object_sha,
                        "size": len(content),
                    }
                ],
            )

            report = inventory.inspect_entry(entry, repo_root=root, cache=cache)

            self.assertEqual("local_overlay", report["unowned"][0]["classification"])
            self.assertEqual(target, report["unowned"][0]["source"])

    def test_live_tree_404_is_reported_as_source_unavailable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = inventory.GitHubObjectCache(Path(tmpdir))
            completed = mock.Mock(
                returncode=1,
                stdout=b"",
                stderr=b"gh: Not Found (HTTP 404)",
            )
            with mock.patch.object(inventory.subprocess, "run", return_value=completed):
                with self.assertRaisesRegex(inventory.SourceUnavailable, "404"):
                    cache.get_tree("owner/upstream", COMMIT)

    def test_symlinks_and_cache_artifacts_are_never_scanned(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_skill = write_skill(root)
            skill_root = (root / repo_skill).parent
            (skill_root / ".DS_Store").write_bytes(b"ignored")
            cache_dir = skill_root / "__pycache__"
            cache_dir.mkdir()
            (cache_dir / "module.pyc").write_bytes(b"ignored")
            external = root / "outside.txt"
            external.write_text("outside", encoding="utf-8")
            (skill_root / "linked.txt").symlink_to(external)
            linked_dir = skill_root / "linked-dir"
            linked_dir.symlink_to(root, target_is_directory=True)

            actual, issues = inventory._iter_regular_skill_files(root, repo_skill)

            self.assertEqual([repo_skill], actual)
            self.assertEqual(2, len(issues))
            self.assertEqual({"symlink"}, {issue["issue"] for issue in issues})

            entry = make_entry(root)
            entry["managed_files"].append(
                {
                    "path": "skills/category/demo/linked.txt",
                    "sha256": "f" * 64,
                    "owner": "demo",
                    "mode": "100644",
                }
            )
            mapping = root / "docs/sources/example.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(make_payload(entry), indent=2) + "\n",
                encoding="utf-8",
            )
            before = mapping.read_bytes()
            report = inventory.reconcile_mappings(
                [mapping],
                repo_root=root,
                cache=inventory.GitHubObjectCache(root / "cache", offline=True),
                write=True,
            )
            self.assertEqual(before, mapping.read_bytes())
            self.assertEqual(2, report["summary"]["scan_errors"])
            self.assertEqual(1, report["summary"]["stale_managed"])
            self.assertEqual(1, report["summary"]["write_blocked_entries"])

    def test_skill_ancestor_symlink_is_rejected_without_scanning_outside(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "repo"
            root.mkdir()
            outside = Path(tmpdir) / "outside"
            repo_skill = write_skill(outside)
            secret = outside / "skills/category/demo/secret.txt"
            secret.write_text("must not be scanned", encoding="utf-8")
            (root / "skills").symlink_to(
                outside / "skills",
                target_is_directory=True,
            )

            actual, issues = inventory._iter_regular_skill_files(root, repo_skill)

            self.assertEqual([], actual)
            self.assertTrue(issues)
            self.assertIn("symlink", {item["issue"] for item in issues})
            self.assertNotIn(
                "secret.txt",
                json.dumps(issues, ensure_ascii=False),
            )

    def test_directory_artifact_missing_managed_is_still_exactly_classified(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_skill(root)
            entry = make_entry(root)
            entry["origins"][0]["artifacts"] = [
                {
                    "source": "upstream/demo",
                    "target": "skills/category/demo",
                    "type": "directory",
                },
                {
                    "source": "upstream/demo/SKILL.md",
                    "target": "skills/category/demo/SKILL.md",
                    "type": "file",
                }
            ]
            target = "skills/category/demo/references/exact.bin"
            content = b"\x00directory sidecar\xff"
            (root / target).parent.mkdir(parents=True)
            (root / target).write_bytes(content)
            object_sha = inventory._git_blob_oid(content, "sha1")
            cache = inventory.GitHubObjectCache(root / "cache", offline=False)
            trusted_entries = [
                {
                    "path": "upstream/demo/references/exact.bin",
                    "type": "blob",
                    "sha": object_sha,
                    "size": len(content),
                }
            ]

            with mock.patch.object(
                cache,
                "_gh_json",
                side_effect=online_tree_responder(trusted_entries),
            ):
                inspection = inventory.inspect_entry(
                    entry,
                    repo_root=root,
                    cache=cache,
                )
            by_target = {
                item["target"]: item for item in inspection["unowned"]
            }

            self.assertIn(target, inspection["missing_managed"])
            self.assertEqual([], inspection["ownership_conflicts"])
            self.assertEqual("external_exact", by_target[target]["classification"])
            self.assertEqual(
                "owner/upstream",
                by_target[target]["declared_owner"]["repo"],
            )
            updated, changed, blocked = inventory.apply_entry_reconciliation(
                entry,
                inspection,
                repo_root=root,
                today="2026-08-20",
            )
            self.assertTrue(changed)
            self.assertIsNone(blocked)
            self.assertEqual(
                entry["origins"][0]["artifacts"],
                updated["origins"][0]["artifacts"],
            )
            self.assertIn(
                target,
                {managed["path"] for managed in updated["managed_files"]},
            )

    def test_directory_artifact_content_mismatch_blocks_owner_reassignment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_skill(root)
            entry = make_entry(root)
            entry["origins"][0]["artifacts"] = [
                {
                    "source": "upstream/demo",
                    "target": "skills/category/demo",
                    "type": "directory",
                }
            ]
            target = "skills/category/demo/references/drifted.bin"
            (root / target).parent.mkdir(parents=True)
            (root / target).write_bytes(b"local bytes")
            upstream_bytes = b"different upstream bytes"
            upstream_oid = inventory._git_blob_oid(upstream_bytes, "sha1")
            cache = inventory.GitHubObjectCache(root / "cache", offline=True)
            write_tree_fixture(
                cache,
                [
                    {
                        "path": "upstream/demo/references/drifted.bin",
                        "type": "blob",
                        "sha": upstream_oid,
                        "size": len(upstream_bytes),
                    }
                ],
            )
            write_blob_fixture(cache, upstream_oid, upstream_bytes)

            inspection = inventory.inspect_entry(entry, repo_root=root, cache=cache)
            proposal = next(
                item for item in inspection["unowned"] if item["target"] == target
            )
            self.assertEqual("local_overlay", proposal["classification"])
            self.assertFalse(proposal["declared_owner"]["local"])

            updated, changed, blocked = inventory.apply_entry_reconciliation(
                entry,
                inspection,
                repo_root=root,
                today="2026-08-20",
            )
            self.assertFalse(changed)
            self.assertEqual(entry, updated)
            self.assertIn("declared owner mismatch", blocked)

    def test_managed_hash_mismatch_and_stale_record_block_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_skill = write_skill(root)
            entry = make_entry(root)
            (root / repo_skill).write_text("changed after checkpoint\n", encoding="utf-8")
            entry["managed_files"].append(
                {
                    "path": "skills/category/demo/removed.txt",
                    "sha256": "e" * 64,
                    "owner": "demo",
                    "mode": "100644",
                }
            )
            mapping = root / "docs/sources/example.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(make_payload(entry), indent=2) + "\n",
                encoding="utf-8",
            )
            before = mapping.read_bytes()

            report = inventory.reconcile_mappings(
                [mapping],
                repo_root=root,
                cache=inventory.GitHubObjectCache(root / "cache", offline=True),
                write=True,
            )

            self.assertEqual(before, mapping.read_bytes())
            self.assertEqual(1, report["summary"]["hash_mismatches"])
            self.assertEqual(1, report["summary"]["stale_managed"])
            self.assertEqual(1, report["summary"]["write_blocked_entries"])
            reason = report["entries"][0]["write_blocked_reason"]
            self.assertIn("managed hash mismatch", reason)
            self.assertIn("stale managed file", reason)

    def test_scandir_error_is_reported_and_blocks_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_skill(root)
            entry = make_entry(root)
            mapping = root / "docs/sources/example.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(make_payload(entry), indent=2) + "\n",
                encoding="utf-8",
            )
            before = mapping.read_bytes()

            with mock.patch.object(
                inventory.os,
                "scandir",
                side_effect=PermissionError("denied"),
            ):
                report = inventory.reconcile_mappings(
                    [mapping],
                    repo_root=root,
                    cache=inventory.GitHubObjectCache(root / "cache", offline=True),
                    write=True,
                )

            self.assertEqual(before, mapping.read_bytes())
            self.assertEqual(1, report["summary"]["scan_errors"])
            issue = report["entries"][0]["scan_errors"][0]
            self.assertEqual("io_error", issue["issue"])
            self.assertEqual("scandir", issue["operation"])
            self.assertIn("scan/read error", report["entries"][0]["write_blocked_reason"])

    def test_managed_file_read_error_is_reported_and_blocks_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_skill(root)
            entry = make_entry(root)
            mapping = root / "docs/sources/example.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(make_payload(entry), indent=2) + "\n",
                encoding="utf-8",
            )
            before = mapping.read_bytes()

            with mock.patch.object(
                inventory,
                "_regular_file_snapshot",
                side_effect=PermissionError("read denied"),
            ):
                report = inventory.reconcile_mappings(
                    [mapping],
                    repo_root=root,
                    cache=inventory.GitHubObjectCache(root / "cache", offline=True),
                    write=True,
                )

            self.assertEqual(before, mapping.read_bytes())
            self.assertEqual(1, report["summary"]["scan_errors"])
            issue = report["entries"][0]["scan_errors"][0]
            self.assertEqual("hash_managed_file", issue["operation"])
            self.assertIn("read denied", issue["detail"])
            self.assertEqual(1, report["summary"]["write_blocked_entries"])

    def test_managed_mode_drift_is_reported_and_blocks_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_skill = write_skill(root)
            entry = make_entry(root)
            (root / repo_skill).chmod(0o755)
            mapping = root / "docs/sources/example.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(make_payload(entry), indent=2) + "\n",
                encoding="utf-8",
            )
            before = mapping.read_bytes()

            report = inventory.reconcile_mappings(
                [mapping],
                repo_root=root,
                cache=inventory.GitHubObjectCache(
                    root / "cache",
                    offline=True,
                ),
                write=True,
            )

            self.assertEqual(before, mapping.read_bytes())
            self.assertEqual([repo_skill], report["entries"][0]["mode_mismatches"])
            self.assertEqual(1, report["summary"]["mode_mismatches"])
            self.assertEqual(1, report["summary"]["write_blocked_entries"])
            self.assertIn(
                "managed mode mismatch",
                report["entries"][0]["write_blocked_reason"],
            )

    def test_mode_change_during_secure_read_is_a_toctou_scan_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_skill = write_skill(root)
            entry = make_entry(root)
            skill_path = root / repo_skill
            changed = False
            real_read = inventory.os.read

            def chmod_during_read(descriptor: int, size: int) -> bytes:
                nonlocal changed
                chunk = real_read(descriptor, size)
                if chunk and not changed:
                    skill_path.chmod(0o755)
                    changed = True
                return chunk

            with mock.patch.object(
                inventory.os,
                "read",
                side_effect=chmod_during_read,
            ):
                inspection = inventory.inspect_entry(
                    entry,
                    repo_root=root,
                    cache=inventory.GitHubObjectCache(
                        root / "cache",
                        offline=True,
                    ),
                )

            self.assertTrue(changed)
            self.assertTrue(inspection["scan_errors"])
            self.assertIn(
                "changed while reading",
                inspection["scan_errors"][0]["detail"],
            )

    def test_dry_run_is_read_only_and_write_is_atomic_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_skill = write_skill(root)
            entry = make_entry(root)
            exact_target = "skills/category/demo/references/exact.bin"
            overlay_target = "skills/category/demo/LOCAL.md"
            exact_bytes = b"\x00exact\xff"
            exact_blob = inventory._git_blob_oid(exact_bytes, "sha1")
            (root / exact_target).parent.mkdir(parents=True)
            (root / exact_target).write_bytes(exact_bytes)
            (root / overlay_target).write_text("local supplement\n", encoding="utf-8")
            mapping = root / "docs/sources/example.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(make_payload(entry), indent=2) + "\n",
                encoding="utf-8",
            )
            before = mapping.read_bytes()

            cache_dir = root / "cache"
            cache = inventory.GitHubObjectCache(cache_dir, offline=True)
            write_tree_fixture(
                cache,
                [
                    {
                        "path": "upstream/demo/references/exact.bin",
                        "type": "blob",
                        "sha": exact_blob,
                        "size": len(exact_bytes),
                    }
                ],
            )
            write_blob_fixture(cache, exact_blob, exact_bytes)
            report_path = root / "dry-run.json"

            self.assertEqual(
                0,
                inventory.main(
                    [
                        "--repo-root",
                        str(root),
                        "--mapping",
                        "docs/sources/example.skills.json",
                        "--cache-dir",
                        str(cache_dir),
                        "--offline",
                        "--output",
                        str(report_path),
                    ]
                ),
            )
            self.assertEqual(before, mapping.read_bytes())
            dry_report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(0, dry_report["summary"]["external_exact"])
            self.assertEqual(1, dry_report["summary"]["local_overlay"])
            self.assertEqual(1, dry_report["summary"]["unavailable"])
            self.assertEqual(
                1,
                inventory.main(
                    [
                        "--repo-root",
                        str(root),
                        "--mapping",
                        "docs/sources/example.skills.json",
                        "--cache-dir",
                        str(cache_dir),
                        "--offline",
                        "--check-clean",
                        "--output",
                        str(root / "dirty-check.json"),
                    ]
                ),
            )

            self.assertEqual(
                1,
                inventory.main(
                    [
                        "--repo-root",
                        str(root),
                        "--mapping",
                        "docs/sources/example.skills.json",
                        "--cache-dir",
                        str(cache_dir),
                        "--offline",
                        "--write",
                        "--output",
                        str(root / "write.json"),
                    ]
                ),
            )
            self.assertEqual(before, mapping.read_bytes())

            online_cache = inventory.GitHubObjectCache(
                cache_dir,
                offline=False,
            )
            trusted_entries = [
                {
                    "path": "upstream/demo/references/exact.bin",
                    "type": "blob",
                    "sha": exact_blob,
                    "size": len(exact_bytes),
                }
            ]
            with mock.patch.object(
                online_cache,
                "_gh_json",
                side_effect=online_tree_responder(trusted_entries),
            ):
                online_report = inventory.reconcile_mappings(
                    [mapping],
                    repo_root=root,
                    cache=online_cache,
                    write=True,
                    today="2026-08-20",
                )
            self.assertEqual(1, online_report["summary"]["mappings_changed"])

            written = json.loads(mapping.read_text(encoding="utf-8"))
            written_entry = written["skills"][0]
            self.assertEqual("overlay", written_entry["kind"])
            self.assertEqual("monitor", written_entry["sync_mode"])
            local_origin = next(
                origin
                for origin in written_entry["origins"]
                if origin["repo"] == inventory.LOCAL_OVERLAY_REPO
            )
            self.assertIsNone(local_origin["license"])
            self.assertEqual("local-only", local_origin["sync_mode"])
            self.assertEqual(
                [{"source": overlay_target, "target": overlay_target, "type": "file"}],
                local_origin["artifacts"],
            )
            self.assertEqual(
                {repo_skill, exact_target, overlay_target},
                {
                    managed["path"]
                    for managed in written_entry["managed_files"]
                },
            )
            self.assertEqual(
                {"100644"},
                {
                    managed["mode"]
                    for managed in written_entry["managed_files"]
                },
            )
            self.assertEqual([], validator.validate_mapping(mapping, root))
            self.assertEqual(
                0,
                inventory.main(
                    [
                        "--repo-root",
                        str(root),
                        "--mapping",
                        "docs/sources/example.skills.json",
                        "--cache-dir",
                        str(cache_dir),
                        "--offline",
                        "--check-clean",
                        "--output",
                        str(root / "clean-check.json"),
                    ]
                ),
            )

            once = mapping.read_bytes()
            second_report = inventory.reconcile_mappings(
                [mapping],
                repo_root=root,
                cache=inventory.GitHubObjectCache(cache_dir, offline=True),
                write=True,
                today="2026-08-20",
            )
            self.assertEqual(once, mapping.read_bytes())
            self.assertEqual(0, second_report["summary"]["mappings_changed"])

    def test_unavailable_entry_blocks_write_without_partial_managed_claims(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_skill(root)
            entry = make_entry(root)
            target = "skills/category/demo/unavailable.txt"
            (root / target).write_text("local", encoding="utf-8")
            mapping = root / "docs/sources/example.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(make_payload(entry), indent=2) + "\n",
                encoding="utf-8",
            )
            before = mapping.read_bytes()
            cache = inventory.GitHubObjectCache(root / "cache", offline=True)

            report = inventory.reconcile_mappings(
                [mapping],
                repo_root=root,
                cache=cache,
                write=True,
            )

            self.assertEqual(before, mapping.read_bytes())
            self.assertEqual(1, report["summary"]["unavailable"])
            self.assertEqual(1, report["summary"]["write_blocked_entries"])
            report_path = root / "blocked-write-report.json"
            self.assertEqual(
                1,
                inventory.main(
                    [
                        "--repo-root",
                        str(root),
                        "--mapping",
                        "docs/sources/example.skills.json",
                        "--cache-dir",
                        str(root / "cache"),
                        "--offline",
                        "--write",
                        "--output",
                        str(report_path),
                    ]
                ),
            )
            self.assertEqual(before, mapping.read_bytes())
            self.assertGreater(
                json.loads(report_path.read_text(encoding="utf-8"))["summary"][
                    "write_blocked_entries"
                ],
                0,
            )

    def test_write_honors_shared_mapping_lock_before_first_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_skill(root)
            entry = make_entry(root)
            mapping = root / "docs/sources/example.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(make_payload(entry), indent=2) + "\n",
                encoding="utf-8",
            )
            before = mapping.read_bytes()
            worker = r"""
import sys
from pathlib import Path
from scripts.reconcile_artifact_inventory import (
    GitHubObjectCache,
    reconcile_mappings,
)

root = Path(sys.argv[1])
mapping = Path(sys.argv[2])
reconcile_mappings(
    [mapping],
    repo_root=root,
    cache=GitHubObjectCache(root / "cache", offline=True),
    write=True,
    lock_timeout=0.0,
)
"""
            from scripts.sync_upstream import mapping_advisory_lock

            with mapping_advisory_lock(mapping, timeout=0.0):
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        worker,
                        str(root),
                        str(mapping),
                    ],
                    cwd=REPO_ROOT,
                    env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                )

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("already active", completed.stderr)
            self.assertEqual(before, mapping.read_bytes())
            self.assertEqual(
                [],
                [
                    path.name
                    for path in mapping.parent.iterdir()
                    if path.name.startswith(".example.skills.json.")
                ],
            )

    def test_write_rejects_symlinked_mapping_ancestor_without_outside_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "repo"
            outside = Path(tmpdir) / "outside"
            root.mkdir()
            outside_sources = outside / "sources"
            outside_sources.mkdir(parents=True)
            mapping = root / "docs/sources/example.skills.json"
            (root / "docs").mkdir()
            (root / "docs/sources").symlink_to(
                outside_sources,
                target_is_directory=True,
            )
            outside_mapping = outside_sources / mapping.name
            outside_mapping.write_text(
                json.dumps(make_payload({}), indent=2) + "\n",
                encoding="utf-8",
            )
            before = outside_mapping.read_bytes()

            with self.assertRaises(inventory.ReconciliationWriteError):
                inventory.reconcile_mappings(
                    [mapping],
                    repo_root=root,
                    cache=inventory.GitHubObjectCache(
                        root / "cache",
                        offline=True,
                    ),
                    write=True,
                    lock_timeout=0.0,
                )

            self.assertEqual(before, outside_mapping.read_bytes())
            self.assertEqual(
                [mapping.name],
                sorted(path.name for path in outside_sources.iterdir()),
            )

    def test_write_is_all_or_none_when_any_entry_has_debt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_skill(root, "safe")
            safe = make_entry(root, "safe")
            safe_sidecar = "skills/category/safe/LOCAL.md"
            (root / safe_sidecar).write_text("safe overlay\n", encoding="utf-8")
            safe_mapping = root / "docs/sources/safe.skills.json"
            safe_mapping.parent.mkdir(parents=True)
            safe_mapping.write_text(
                json.dumps(make_payload(safe), indent=2) + "\n",
                encoding="utf-8",
            )

            write_skill(root, "blocked")
            blocked = make_entry(root, "blocked")
            blocked_sidecar = "skills/category/blocked/unavailable.txt"
            (root / blocked_sidecar).write_text("blocked\n", encoding="utf-8")
            blocked_mapping = root / "docs/sources/blocked.skills.json"
            blocked_mapping.write_text(
                json.dumps(make_payload(blocked), indent=2) + "\n",
                encoding="utf-8",
            )
            before = {
                safe_mapping: safe_mapping.read_bytes(),
                blocked_mapping: blocked_mapping.read_bytes(),
            }
            cache = inventory.GitHubObjectCache(root / "cache", offline=True)

            report = inventory.reconcile_mappings(
                [safe_mapping, blocked_mapping],
                repo_root=root,
                cache=cache,
                write=True,
            )

            self.assertEqual(before[safe_mapping], safe_mapping.read_bytes())
            self.assertEqual(before[blocked_mapping], blocked_mapping.read_bytes())
            self.assertEqual(0, report["summary"]["mappings_changed"])
            self.assertGreater(report["summary"]["write_blocked_entries"], 0)

    def test_classification_checkpoint_blocks_toctou_adoption(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_skill(root)
            entry = make_entry(root)
            target = "skills/category/demo/references/exact.bin"
            original = b"upstream exact"
            (root / target).parent.mkdir(parents=True)
            (root / target).write_bytes(original)
            object_sha = inventory._git_blob_oid(original, "sha1")
            cache = inventory.GitHubObjectCache(root / "cache", offline=False)
            trusted_entries = [
                {
                    "path": "upstream/demo/references/exact.bin",
                    "type": "blob",
                    "sha": object_sha,
                    "size": len(original),
                }
            ]
            mapping = root / "docs/sources/example.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(make_payload(entry), indent=2) + "\n",
                encoding="utf-8",
            )
            before = mapping.read_bytes()
            original_apply = inventory.apply_entry_reconciliation
            mutated = False

            def mutate_after_classification(*args, **kwargs):
                nonlocal mutated
                result = original_apply(*args, **kwargs)
                if not mutated:
                    mutated = True
                    replacement = root / f"{target}.replacement"
                    replacement.write_bytes(b"user bytes after classification")
                    os.replace(replacement, root / target)
                return result

            with (
                mock.patch.object(
                    cache,
                    "_gh_json",
                    side_effect=online_tree_responder(trusted_entries),
                ),
                mock.patch.object(
                    inventory,
                    "apply_entry_reconciliation",
                    side_effect=mutate_after_classification,
                ),
            ):
                report = inventory.reconcile_mappings(
                    [mapping],
                    repo_root=root,
                    cache=cache,
                    write=True,
                )

            self.assertEqual(before, mapping.read_bytes())
            self.assertEqual(
                b"user bytes after classification",
                (root / target).read_bytes(),
            )
            self.assertEqual(0, report["summary"]["mappings_changed"])
            self.assertGreater(report["summary"]["write_blocked_entries"], 0)

    def test_cross_mapping_commit_failure_rolls_back_every_mapping(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mappings = []
            for slug in ("one", "two"):
                write_skill(root, slug)
                entry = make_entry(root, slug)
                sidecar = f"skills/category/{slug}/LOCAL.md"
                (root / sidecar).write_text(
                    f"{slug} overlay\n",
                    encoding="utf-8",
                )
                mapping = root / f"docs/sources/{slug}.skills.json"
                mapping.parent.mkdir(parents=True, exist_ok=True)
                mapping.write_text(
                    json.dumps(make_payload(entry), indent=2) + "\n",
                    encoding="utf-8",
                )
                mappings.append(mapping)
            before = {path: path.read_bytes() for path in mappings}
            cache = inventory.GitHubObjectCache(root / "cache", offline=False)
            real_replace = inventory.os.replace
            failed = False

            def fail_second_stage(source, destination, *args, **kwargs):
                nonlocal failed
                source_path = Path(source)
                destination_path = Path(destination)
                if (
                    not failed
                    and destination_path.name == mappings[1].name
                    and ".inventory-stage-" in source_path.name
                ):
                    failed = True
                    raise OSError("injected second mapping replace failure")
                return real_replace(source, destination, *args, **kwargs)

            with (
                mock.patch.object(
                    cache,
                    "_gh_json",
                    side_effect=online_tree_responder([]),
                ),
                mock.patch.object(
                    inventory.os,
                    "replace",
                    side_effect=fail_second_stage,
                ),
            ):
                report = inventory.reconcile_mappings(
                    mappings,
                    repo_root=root,
                    cache=cache,
                    write=True,
                )

            self.assertEqual(0, report["summary"]["mappings_changed"])
            self.assertIn("injected", report["summary"]["write_error"])
            for path in mappings:
                self.assertEqual(before[path], path.read_bytes())

    def test_cross_mapping_hard_exit_recovers_all_before_on_next_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mappings = []
            for slug in ("one", "two"):
                write_skill(root, slug)
                entry = make_entry(root, slug)
                sidecar = f"skills/category/{slug}/LOCAL.md"
                (root / sidecar).write_text(
                    f"{slug} overlay\n",
                    encoding="utf-8",
                )
                mapping = root / f"docs/sources/{slug}.skills.json"
                mapping.parent.mkdir(parents=True, exist_ok=True)
                mapping.write_text(
                    json.dumps(make_payload(entry), indent=2) + "\n",
                    encoding="utf-8",
                )
                mappings.append(mapping)
            before = {path: path.read_bytes() for path in mappings}
            worker = r"""
import os
import sys
from pathlib import Path
from scripts import reconcile_artifact_inventory as inventory

root = Path(sys.argv[1])
mappings = [Path(value) for value in sys.argv[2:]]
commit = "a" * 40
root_tree = "b" * 40
cache = inventory.GitHubObjectCache(root / "cache", offline=False)

def respond(endpoint, *, fields=None):
    if endpoint == f"repos/owner/upstream/git/commits/{commit}":
        return {"sha": commit, "tree": {"sha": root_tree}}
    if endpoint == f"repos/owner/upstream/git/trees/{root_tree}":
        return {"sha": root_tree, "truncated": False, "tree": []}
    raise AssertionError(endpoint)

cache._gh_json = respond
real_replace = inventory.os.replace

def hard_exit_after_first_install(source, destination, *args, **kwargs):
    real_replace(source, destination, *args, **kwargs)
    if (
        Path(destination).name == mappings[0].name
        and ".inventory-stage-" in Path(source).name
    ):
        os._exit(73)

inventory.os.replace = hard_exit_after_first_install
inventory.reconcile_mappings(
    mappings,
    repo_root=root,
    cache=cache,
    write=True,
    lock_timeout=0.0,
)
"""
            completed = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    worker,
                    str(root),
                    *(str(path) for path in mappings),
                ],
                cwd=REPO_ROOT,
                env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            self.assertEqual(73, completed.returncode, completed.stderr)
            self.assertNotEqual(before[mappings[0]], mappings[0].read_bytes())
            self.assertEqual(before[mappings[1]], mappings[1].read_bytes())
            self.assertTrue(
                (root / ".hvs-transactions/pending/journal.json").is_file()
            )

            report = inventory.reconcile_mappings(
                mappings,
                repo_root=root,
                cache=inventory.GitHubObjectCache(
                    root / "cache",
                    offline=True,
                ),
                write=True,
                lock_timeout=0.0,
            )

            self.assertGreater(report["summary"]["write_blocked_entries"], 0)
            for path in mappings:
                self.assertEqual(before[path], path.read_bytes())
            self.assertFalse((root / ".hvs-transactions/pending").exists())
            self.assertEqual(
                [],
                [
                    path.name
                    for path in mappings[0].parent.iterdir()
                    if ".inventory-stage-" in path.name
                ],
            )

    def test_detached_mapping_parent_never_overwrites_concurrent_active_tree(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_skill(root)
            entry = make_entry(root)
            sidecar = "skills/category/demo/LOCAL.md"
            (root / sidecar).write_text("local overlay\n", encoding="utf-8")
            mapping = root / "docs/sources/example.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(make_payload(entry), indent=2) + "\n",
                encoding="utf-8",
            )
            before = mapping.read_bytes()
            detached = root / "docs/sources-detached"
            cache = inventory.GitHubObjectCache(root / "cache", offline=False)
            original_assert = inventory._assert_active_mapping_parent
            detached_once = False

            def detach_after_identity_check(*args, **kwargs):
                nonlocal detached_once
                original_assert(*args, **kwargs)
                if detached_once:
                    return
                detached_once = True
                mapping.parent.rename(detached)
                mapping.parent.mkdir()
                mapping.write_bytes(before)

            with (
                mock.patch.object(
                    cache,
                    "_gh_json",
                    side_effect=online_tree_responder([]),
                ),
                mock.patch.object(
                    inventory,
                    "_assert_active_mapping_parent",
                    side_effect=detach_after_identity_check,
                ),
            ):
                report = inventory.reconcile_mappings(
                    [mapping],
                    repo_root=root,
                    cache=cache,
                    write=True,
                    lock_timeout=0.0,
                )

            self.assertEqual(0, report["summary"]["mappings_changed"])
            self.assertIn(
                "parent changed concurrently",
                report["summary"]["write_error"],
            )
            self.assertEqual(before, mapping.read_bytes())
            self.assertNotEqual(
                before,
                (detached / mapping.name).read_bytes(),
            )
            self.assertFalse((root / ".hvs-transactions/pending").exists())

    def test_snapshot_local_supplement_keeps_snapshot_update_policy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_skill(root)
            entry = make_entry(root)
            entry["kind"] = "snapshot"
            entry["sync_mode"] = "local-only"
            entry["upstream"]["sync_mode"] = "local-only"
            entry["origins"][0]["sync_mode"] = "local-only"
            target = "skills/category/demo/LOCAL.md"
            (root / target).write_text("snapshot supplement\n", encoding="utf-8")
            cache = inventory.GitHubObjectCache(root / "cache", offline=True)
            write_tree_fixture(cache, [])
            inspection = inventory.inspect_entry(entry, repo_root=root, cache=cache)

            updated, changed, blocked = inventory.apply_entry_reconciliation(
                entry,
                inspection,
                repo_root=root,
                today="2026-08-20",
            )

            self.assertTrue(changed)
            self.assertIsNone(blocked)
            self.assertEqual("snapshot", updated["kind"])
            self.assertEqual("local-only", updated["sync_mode"])
            self.assertEqual("local-only", updated["origins"][0]["sync_mode"])
            self.assertEqual(
                inventory.LOCAL_OVERLAY_REPO,
                updated["origins"][1]["repo"],
            )
            self.assertEqual("local-only", updated["origins"][1]["sync_mode"])

    def test_validator_accepts_curated_overlay_and_rejects_duplicate_origin_owner(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_skill = write_skill(root)
            entry = make_entry(root)
            overlay_target = "skills/category/demo/LOCAL.md"
            (root / overlay_target).write_text("local\n", encoding="utf-8")
            entry["kind"] = "overlay"
            entry["origins"].append(
                inventory._local_overlay_origin(
                    entry,
                    [
                        {
                            "source": overlay_target,
                            "target": overlay_target,
                            "type": "file",
                        }
                    ],
                    today="2026-08-20",
                )
            )
            entry["managed_files"].append(
                {
                    "path": overlay_target,
                    "sha256": provenance.sha256_file(root / overlay_target),
                    "owner": "demo",
                    "mode": "100644",
                }
            )
            mapping = root / "docs/sources/example.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(make_payload(entry), indent=2) + "\n",
                encoding="utf-8",
            )
            self.assertEqual([], validator.validate_mapping(mapping, root))

            duplicated = deepcopy(entry)
            duplicated["origins"][1]["artifacts"].append(
                {
                    "source": repo_skill,
                    "target": repo_skill,
                    "type": "file",
                }
            )
            mapping.write_text(
                json.dumps(make_payload(duplicated), indent=2) + "\n",
                encoding="utf-8",
            )
            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(
                any("repo_skill must have exactly one" in error for error in errors),
                errors,
            )

            local_only_owner = deepcopy(entry)
            local_only_owner["origins"][0]["artifacts"] = []
            local_only_owner["origins"][1]["artifacts"].append(
                {
                    "source": repo_skill,
                    "target": repo_skill,
                    "type": "file",
                }
            )
            mapping.write_text(
                json.dumps(make_payload(local_only_owner), indent=2) + "\n",
                encoding="utf-8",
            )
            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(
                any("external repo_skill must be owned" in error for error in errors),
                errors,
            )

    def test_schema_pins_local_overlay_contract(self):
        schema = json.loads(
            (REPO_ROOT / "scripts/provenance_v2.schema.json").read_text(
                encoding="utf-8"
            )
        )
        conditional = schema["$defs"]["origin"]["allOf"][0]
        self.assertEqual(
            "local-repo/curation",
            conditional["if"]["properties"]["repo"]["const"],
        )
        properties = conditional["then"]["properties"]
        self.assertEqual("null", properties["license"]["type"])
        self.assertEqual("local-only", properties["sync_mode"]["const"])
        tracking = properties["tracking"]["allOf"][1]["properties"]
        self.assertEqual("local", tracking["channel"]["const"])
        self.assertEqual("local", tracking["ref"]["const"])

    def test_migration_preserves_mixed_origin_ownership_and_modes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_skill = write_skill(root)
            entry = make_entry(root)
            overlay_target = "skills/category/demo/LOCAL.md"
            (root / overlay_target).write_text("local\n", encoding="utf-8")
            entry["kind"] = "overlay"
            entry["origins"].append(
                inventory._local_overlay_origin(
                    entry,
                    [
                        {
                            "source": overlay_target,
                            "target": overlay_target,
                            "type": "file",
                        }
                    ],
                    today="2026-08-20",
                )
            )
            entry["managed_files"].append(
                {
                    "path": overlay_target,
                    "sha256": provenance.sha256_file(root / overlay_target),
                    "owner": "demo",
                    "mode": "100644",
                }
            )

            migrated = provenance.migrate_payload(
                make_payload(entry),
                root,
                local_tracking_date="2026-08-21",
                refresh_managed_digests=True,
            )
            migrated_entry = migrated["skills"][0]
            external_origin, local_origin = migrated_entry["origins"]

            self.assertEqual("monitor", migrated_entry["sync_mode"])
            self.assertEqual("monitor", external_origin["sync_mode"])
            self.assertEqual("local-only", local_origin["sync_mode"])
            self.assertEqual(
                [
                    {
                        "source": overlay_target,
                        "target": overlay_target,
                        "type": "file",
                    }
                ],
                local_origin["artifacts"],
            )
            self.assertEqual("local", local_origin["tracking"]["ref"])
            self.assertIsNone(local_origin["tracking"]["resolved_commit"])
            self.assertIsNone(local_origin["tracking"]["path_commit"])
            self.assertIsNone(local_origin["tracking"]["content_sha256"])
            self.assertEqual(
                {repo_skill, overlay_target},
                {
                    managed["path"]
                    for managed in migrated_entry["managed_files"]
                },
            )

    def test_migration_never_drops_missing_external_evidence_from_overlay(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_skill(root)
            entry = make_entry(root)
            missing_target = "skills/category/demo/references/missing.md"
            entry["kind"] = "overlay"
            entry["origins"][0]["artifacts"].append(
                {
                    "source": "skills/demo/references/missing.md",
                    "target": missing_target,
                    "type": "file",
                }
            )
            entry["managed_files"].append(
                {
                    "path": missing_target,
                    "sha256": "f" * 64,
                    "owner": "demo",
                    "mode": "100644",
                }
            )
            entry["origins"].append(
                inventory._local_overlay_origin(
                    entry,
                    [],
                    today="2026-08-20",
                )
            )

            migrated = provenance.migrate_payload(
                make_payload(entry),
                root,
                local_tracking_date="2026-08-21",
                refresh_managed_digests=True,
            )

            managed = {
                item["path"]: item
                for item in migrated["skills"][0]["managed_files"]
            }
            self.assertIn(missing_target, managed)
            self.assertEqual("f" * 64, managed[missing_target]["sha256"])


if __name__ == "__main__":
    unittest.main()
