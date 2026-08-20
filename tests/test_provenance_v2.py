import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
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
migrator = load_script("migrate_provenance_v2")


def write_skill(
    root: Path,
    slug: str,
    *,
    source: str = "github:owner/upstream",
    source_url: str = "https://github.com/owner/upstream",
    license_name: str | None = "MIT",
) -> str:
    rel = f"skills/category/{slug}/SKILL.md"
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    license_line = f"license: {license_name}\n" if license_name is not None else ""
    path.write_text(
        "---\n"
        f"name: {slug}\n"
        f"source: {source}\n"
        f'source_url: "{source_url}"\n'
        f"{license_line}"
        "---\n"
        f"# {slug}\n",
        encoding="utf-8",
    )
    return rel


def legacy_entry(slug: str, repo_skill: str, *, in_house: bool = False) -> dict:
    if in_house:
        return {
            "video_name": slug,
            "normalized_slug": slug,
            "status": "in_house",
            "repo_skill": repo_skill,
            "source": "https://github.com/example/skills",
            "notes": "Local source of truth.",
            "upstream": {
                "repo": "local-repo/in-house",
                "path": str(Path(repo_skill).parent),
                "ref": "main",
                "last_checked_at": "2026-08-20",
                "last_synced_at": "2026-08-20",
                "last_synced_commit": None,
            },
        }
    return {
        "video_name": slug,
        "normalized_slug": slug,
        "status": "verified_in_repo",
        "repo_skill": repo_skill,
        "source": f"https://github.com/owner/upstream/tree/main/{slug}",
        "notes": "External mirror.",
        "upstream": {
            "repo": "owner/upstream",
            "path": f"skills/{slug}/SKILL.md",
            "ref": "main",
            "last_checked_at": "2026-08-20",
            "last_synced_at": "2026-08-20",
            "last_synced_commit": "a" * 40,
        },
    }


def payload(entries: list[dict], *, v2: bool = False) -> dict:
    result = {
        "video": {
            "url": "https://example.com",
            "checked_at": "2026-08-20",
        },
        "official_references": [],
        "skills": entries,
    }
    if v2:
        result["schema_version"] = 2
    return result


class ProvenanceV2MigrationTests(unittest.TestCase):
    def test_schema_document_and_bundle_discovery_use_the_public_contract(self):
        schema = json.loads(
            (REPO_ROOT / "scripts/provenance_v2.schema.json").read_text(
                encoding="utf-8"
            )
        )
        channels = schema["$defs"]["tracking"]["properties"]["channel"]["enum"]
        self.assertIn("schema_version", schema["required"])
        self.assertEqual(sorted(provenance.VALID_CHANNELS), sorted(channels))
        self.assertIn(
            "sync_mode",
            schema["$defs"]["v2Entry"]["allOf"][1]["required"],
        )
        self.assertEqual(
            "#/$defs/sha256",
            schema["$defs"]["managedFile"]["properties"]["sha256"]["$ref"],
        )
        self.assertEqual(
            "#/$defs/sha256",
            schema["$defs"]["composition"]["properties"]["dependency_lock"][
                "additionalProperties"
            ]["$ref"],
        )
        self.assertEqual(
            "#/$defs/nullableSha256",
            schema["$defs"]["tracking"]["properties"]["content_sha256"]["$ref"],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            sources = Path(tmpdir)
            skill_mapping = sources / "one.skills.json"
            bundle_mapping = sources / "two.bundle.json"
            ignored = sources / "other.json"
            for path in (skill_mapping, bundle_mapping, ignored):
                path.write_text("{}", encoding="utf-8")
            self.assertEqual(
                [skill_mapping, bundle_mapping],
                provenance.discover_source_mappings(sources),
            )

    def test_migration_is_additive_and_uses_repo_relative_targets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            rel = write_skill(root, "example")
            original_entry = legacy_entry("example", rel)
            original = payload([original_entry])

            migrated = provenance.migrate_payload(original, root)

            self.assertEqual(2, migrated["schema_version"])
            entry = migrated["skills"][0]
            for key, value in original_entry.items():
                if key != "upstream":
                    self.assertEqual(value, entry[key])
            for key, value in original_entry["upstream"].items():
                self.assertEqual(value, entry["upstream"][key])
            self.assertEqual("mirror", entry["kind"])
            self.assertEqual(
                [
                    {
                        "path": rel,
                        "sha256": provenance.sha256_file(root / rel),
                        "owner": "example",
                    }
                ],
                entry["managed_files"],
            )
            self.assertEqual(rel, entry["origins"][0]["artifacts"][0]["target"])
            self.assertEqual(
                "default_branch", entry["origins"][0]["tracking"]["channel"]
            )
            self.assertEqual("monitor", entry["sync_mode"])
            self.assertEqual("monitor", entry["origins"][0]["sync_mode"])
            self.assertEqual("monitor", entry["upstream"]["sync_mode"])
            self.assertEqual("MIT", entry["origins"][0]["license"])

    def test_release_channel_migration_is_idempotent_and_syncs_all_modes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            rel = write_skill(root, "example")
            original = payload([legacy_entry("example", rel)])

            once = provenance.migrate_payload(original, root)
            twice = provenance.migrate_payload(once, root)

            self.assertEqual(once, twice)
            entry = twice["skills"][0]
            self.assertEqual("monitor", entry["sync_mode"])
            self.assertEqual("monitor", entry["upstream"]["sync_mode"])
            self.assertEqual("monitor", entry["origins"][0]["sync_mode"])

    def test_latest_release_and_pinned_fixed_ref_keep_replace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            entries = []
            for slug, ref in (
                ("release", "v1.2.3"),
                ("fixed", "a" * 40),
            ):
                rel = write_skill(root, slug)
                entry = legacy_entry(slug, rel)
                entry["upstream"]["ref"] = ref
                entries.append(entry)

            migrated = provenance.migrate_payload(payload(entries), root)
            for entry in migrated["skills"]:
                self.assertEqual("replace", entry["sync_mode"])
                self.assertEqual("replace", entry["upstream"]["sync_mode"])
                self.assertEqual("replace", entry["origins"][0]["sync_mode"])

            fixed_tracking = migrated["skills"][1]["origins"][0]["tracking"]
            self.assertEqual("fixed_ref", fixed_tracking["channel"])
            self.assertTrue(
                provenance.is_immutable_fixed_ref(
                    fixed_tracking,
                    migrated["skills"][1]["origins"][0]["repo"],
                )
            )

    def test_prerelease_and_movable_fixed_aliases_are_monitor_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            entries = []
            for slug, ref in (
                ("prerelease", "v2.0.0-rc.1"),
                ("alpha", "v2.0.0-alpha.1"),
                ("beta", "v2.0.0-beta.2"),
                ("preview", "v3.0.0-preview"),
                ("nightly", "nightly-2026-08-20"),
                ("movable", "stable"),
                ("release-alias", "release-1.x"),
                ("major-alias", "v8"),
                ("mismatched-commit", "b" * 40),
            ):
                rel = write_skill(root, slug)
                entry = legacy_entry(slug, rel)
                entry["upstream"]["ref"] = ref
                entries.append(entry)

            migrated = provenance.migrate_payload(payload(entries), root)
            by_slug = {
                entry["normalized_slug"]: entry
                for entry in migrated["skills"]
            }
            for slug in (
                "prerelease",
                "alpha",
                "beta",
                "preview",
                "nightly",
            ):
                self.assertEqual(
                    "canary",
                    by_slug[slug]["origins"][0]["tracking"]["channel"],
                )
            for entry in migrated["skills"]:
                self.assertEqual("monitor", entry["sync_mode"])
                self.assertEqual("monitor", entry["upstream"]["sync_mode"])
                self.assertEqual("monitor", entry["origins"][0]["sync_mode"])

    def test_migration_cli_is_dry_run_until_write_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            rel = write_skill(root, "example")
            mapping = root / "docs/sources/example.skills.json"
            mapping.parent.mkdir(parents=True)
            original = payload([legacy_entry("example", rel)])
            mapping.write_text(json.dumps(original), encoding="utf-8")
            before = mapping.read_bytes()

            self.assertEqual(
                0,
                migrator.main(
                    [
                        "--repo-root",
                        str(root),
                        "--mapping",
                        "docs/sources/example.skills.json",
                    ]
                ),
            )
            self.assertEqual(before, mapping.read_bytes())

            self.assertEqual(
                0,
                migrator.main(
                    [
                        "--repo-root",
                        str(root),
                        "--mapping",
                        "docs/sources/example.skills.json",
                        "--write",
                    ]
                ),
            )
            loaded = json.loads(mapping.read_text(encoding="utf-8"))
            self.assertEqual(2, loaded["schema_version"])
            self.assertIn("upstream", loaded["skills"][0])

    def test_atomic_writer_ignores_hostile_precreated_symlink_and_keeps_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping = root / "example.skills.json"
            mapping.write_text('{"old": true}\n', encoding="utf-8")
            mapping.chmod(0o640)
            external = root / "external.json"
            external.write_text("do not overwrite\n", encoding="utf-8")
            hostile_temporary = root / f".{mapping.name}.hostile.tmp"
            hostile_temporary.symlink_to(external)

            with mock.patch.object(
                provenance.tempfile,
                "_get_candidate_names",
                return_value=iter(("hostile", "safe")),
            ):
                provenance.atomic_write_json(mapping, {"schema_version": 2})

            self.assertEqual(
                {"schema_version": 2},
                json.loads(mapping.read_text(encoding="utf-8")),
            )
            self.assertEqual("do not overwrite\n", external.read_text(encoding="utf-8"))
            self.assertTrue(hostile_temporary.is_symlink())
            self.assertFalse((root / f".{mapping.name}.safe.tmp").exists())
            self.assertEqual(0o640, os.stat(mapping).st_mode & 0o777)

    def test_managed_digest_refresh_is_explicit_and_updates_matching_origin_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            rel = write_skill(root, "example")
            mapping = root / "docs/sources/example.skills.json"
            mapping.parent.mkdir(parents=True)
            migrated = provenance.migrate_payload(
                payload([legacy_entry("example", rel)]),
                root,
            )
            entry = migrated["skills"][0]
            original_digest = entry["managed_files"][0]["sha256"]
            original_tracking = deepcopy(entry["origins"][0]["tracking"])
            unrelated_origin = deepcopy(entry["origins"][0])
            unrelated_origin["artifacts"][0]["target"] = (
                "skills/category/example/references/other.md"
            )
            unrelated_origin["tracking"]["content_sha256"] = "f" * 64
            entry["origins"].append(unrelated_origin)
            mapping.write_text(json.dumps(migrated), encoding="utf-8")

            # Simulate a canonical normalizer or a manual edit after mapping.
            skill_path = root / rel
            skill_path.write_text(
                skill_path.read_text(encoding="utf-8") + "\nNormalized.\n",
                encoding="utf-8",
            )
            current_digest = provenance.sha256_file(skill_path)
            self.assertNotEqual(original_digest, current_digest)

            # Ordinary migration is intentionally not an implicit checkpoint.
            self.assertEqual(
                0,
                migrator.main(
                    [
                        "--repo-root",
                        str(root),
                        "--mapping",
                        "docs/sources/example.skills.json",
                        "--write",
                    ]
                ),
            )
            unchanged = json.loads(mapping.read_text(encoding="utf-8"))
            self.assertEqual(
                original_digest,
                unchanged["skills"][0]["managed_files"][0]["sha256"],
            )
            self.assertEqual(
                original_tracking,
                unchanged["skills"][0]["origins"][0]["tracking"],
            )

            # Explicit refresh reports the drift but remains read-only without
            # --write.
            before_refresh = mapping.read_bytes()
            report = io.StringIO()
            with redirect_stdout(report):
                self.assertEqual(
                    0,
                    migrator.main(
                        [
                            "--repo-root",
                            str(root),
                            "--mapping",
                            "docs/sources/example.skills.json",
                            "--refresh-managed-digests",
                        ]
                    ),
                )
            self.assertIn("would refresh managed digests", report.getvalue())
            self.assertEqual(before_refresh, mapping.read_bytes())

            self.assertEqual(
                0,
                migrator.main(
                    [
                        "--repo-root",
                        str(root),
                        "--mapping",
                        "docs/sources/example.skills.json",
                        "--refresh-managed-digests",
                        "--write",
                    ]
                ),
            )
            refreshed = json.loads(mapping.read_text(encoding="utf-8"))
            refreshed_entry = refreshed["skills"][0]
            self.assertEqual(
                current_digest,
                refreshed_entry["managed_files"][0]["sha256"],
            )
            matching_tracking = refreshed_entry["origins"][0]["tracking"]
            self.assertEqual(current_digest, matching_tracking["content_sha256"])
            for field in (
                "resolved_commit",
                "path_commit",
                "last_checked_at",
                "last_synced_at",
            ):
                self.assertEqual(original_tracking[field], matching_tracking[field])
            self.assertEqual(
                "f" * 64,
                refreshed_entry["origins"][1]["tracking"]["content_sha256"],
            )

    def test_managed_digest_refresh_preserves_missing_file_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            rel = write_skill(root, "example")
            mapping = root / "docs/sources/example.skills.json"
            mapping.parent.mkdir(parents=True)
            migrated = provenance.migrate_payload(
                payload([legacy_entry("example", rel)]),
                root,
            )
            old_digest = migrated["skills"][0]["managed_files"][0]["sha256"]
            old_tracking_digest = migrated["skills"][0]["origins"][0]["tracking"][
                "content_sha256"
            ]
            mapping.write_text(json.dumps(migrated), encoding="utf-8")
            (root / rel).unlink()

            self.assertEqual(
                0,
                migrator.main(
                    [
                        "--repo-root",
                        str(root),
                        "--mapping",
                        "docs/sources/example.skills.json",
                        "--refresh-managed-digests",
                        "--write",
                    ]
                ),
            )
            refreshed = json.loads(mapping.read_text(encoding="utf-8"))
            entry = refreshed["skills"][0]
            self.assertEqual(old_digest, entry["managed_files"][0]["sha256"])
            self.assertEqual(
                old_tracking_digest,
                entry["origins"][0]["tracking"]["content_sha256"],
            )
            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(
                any("repo_skill does not exist" in error for error in errors)
            )

    def test_string_managed_files_are_additively_migrated_to_owned_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            rel = write_skill(root, "example")
            entry = legacy_entry("example", rel)
            entry["kind"] = "mirror"
            entry["managed_files"] = [rel]
            entry["origins"] = [
                provenance.build_origin(
                    entry,
                    frontmatter=provenance.parse_frontmatter(root / rel),
                    skill_path=root / rel,
                    repo_root=root,
                )
            ]

            migrated = provenance.migrate_payload(payload([entry]), root)

            self.assertEqual(
                {
                    "path": rel,
                    "sha256": provenance.sha256_file(root / rel),
                    "owner": "example",
                },
                migrated["skills"][0]["managed_files"][0],
            )

    def test_safe_relative_path_requires_canonical_posix_form(self):
        self.assertTrue(provenance.safe_relative_path("references/guide.md"))
        for invalid in (
            "",
            " ",
            ".",
            "./",
            "./references/guide.md",
            "references/./guide.md",
            "references//guide.md",
            "references/guide.md/",
            "references\\guide.md",
            "../guide.md",
            "references/../guide.md",
            "/references/guide.md",
            "C:/references/guide.md",
        ):
            with self.subTest(invalid=invalid):
                self.assertFalse(provenance.safe_relative_path(invalid))


class ProvenanceV2ValidationTests(unittest.TestCase):
    def make_migrated_mapping(
        self, root: Path, slug: str = "example", *, in_house: bool = False
    ) -> tuple[Path, dict]:
        source = "in-house" if in_house else "github:owner/upstream"
        source_url = (
            "https://github.com/example/skills"
            if in_house
            else "https://github.com/owner/upstream"
        )
        rel = write_skill(
            root,
            slug,
            source=source,
            source_url=source_url,
            license_name="MIT",
        )
        data = provenance.migrate_payload(
            payload([legacy_entry(slug, rel, in_house=in_house)]), root
        )
        mapping = root / f"{slug}.skills.json"
        mapping.write_text(json.dumps(data), encoding="utf-8")
        return mapping, data

    def make_bundle_mapping(
        self,
        root: Path,
        *,
        suffix: str = "gsd",
        repo: str = "open-gsd/gsd-core",
        content_hash: str | None = "a" * 64,
    ) -> tuple[Path, dict]:
        commit = "b" * 40
        entry = {
            "video_name": f"{suffix} bundle",
            "normalized_slug": f"{suffix}-bundle",
            "status": "verified_not_in_repo",
            "repo_skill": None,
            "source": f"https://github.com/{repo}",
            "notes": "Explicit-only managed bundle fixture.",
            "upstream": {
                "repo": repo,
                "path": None,
                "ref": "v1.0.0",
                "sync_mode": "replace",
                "last_checked_at": "2026-08-20",
                "last_synced_at": "2026-08-20",
                "last_synced_commit": commit,
            },
            "kind": "bundle",
            "sync_mode": "replace",
            "origins": [
                {
                    "repo": repo,
                    "path": None,
                    "license": "MIT",
                    "sync_mode": "replace",
                    "artifacts": [],
                    "tracking": {
                        "channel": "latest_release",
                        "ref": "v1.0.0",
                        "resolved_commit": commit,
                        "path_commit": commit,
                        "content_sha256": content_hash,
                        "last_checked_at": "2026-08-20",
                        "last_synced_at": "2026-08-20",
                    },
                }
            ],
            "managed_files": [],
        }
        data = payload([entry], v2=True)
        mapping = root / f"{suffix}.bundle.json"
        mapping.write_text(json.dumps(data), encoding="utf-8")
        return mapping, data

    def test_valid_v2_mirror_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, _ = self.make_migrated_mapping(root)
            self.assertEqual([], validator.validate_mapping(mapping, root))

    def test_active_repo_skill_requires_exact_canonical_posix_entrypoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, data = self.make_migrated_mapping(root)
            invalid_paths = (
                "skills/category/example/nested/SKILL.md",
                "skills/category/example/README.md",
                "skills/category/different/SKILL.md",
                "other/category/example/SKILL.md",
            )

            for invalid_path in invalid_paths:
                with self.subTest(repo_skill=invalid_path):
                    case = deepcopy(data)
                    case["skills"][0]["repo_skill"] = invalid_path
                    mapping.write_text(json.dumps(case), encoding="utf-8")

                    errors = validator.validate_mapping(mapping, root)

                    self.assertTrue(
                        any(
                            "repo_skill must match canonical POSIX path" in error
                            for error in errors
                        ),
                        errors,
                    )
                    self.assertTrue(
                        any(
                            "managed/artifact containment cannot be validated"
                            in error
                            for error in errors
                        ),
                        errors,
                    )

    def test_inactive_bundle_with_null_repo_skill_remains_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, _ = self.make_bundle_mapping(root)
            self.assertEqual([], validator.validate_mapping(mapping, root))

    def test_v1_requires_explicit_compatibility_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            rel = write_skill(root, "example")
            mapping = root / "legacy.skills.json"
            mapping.write_text(
                json.dumps(payload([legacy_entry("example", rel)])),
                encoding="utf-8",
            )

            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(
                any("schema_version must be 2" in error for error in errors)
            )
            self.assertEqual(
                [],
                validator.validate_mapping(mapping, root, allow_v1=True),
            )

    def test_external_origin_requires_explicit_license_and_sync_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, data = self.make_migrated_mapping(root)
            origin = data["skills"][0]["origins"][0]
            origin["license"] = None
            origin.pop("sync_mode")
            mapping.write_text(json.dumps(data), encoding="utf-8")

            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(any("missing keys" in error for error in errors))
            self.assertTrue(
                any("external origin license" in error for error in errors)
            )
            self.assertTrue(any("sync_mode invalid" in error for error in errors))

    def test_default_and_canary_channels_reject_replace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, data = self.make_migrated_mapping(root)
            entry = data["skills"][0]
            entry["sync_mode"] = "replace"
            entry["upstream"]["sync_mode"] = "replace"
            entry["origins"][0]["sync_mode"] = "replace"
            mapping.write_text(json.dumps(data), encoding="utf-8")

            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(
                any("violates release-channel policy" in error for error in errors)
            )

            entry["origins"][0]["tracking"]["channel"] = "canary"
            entry["origins"][0]["tracking"]["ref"] = "next"
            mapping.write_text(json.dumps(data), encoding="utf-8")
            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(
                any("violates release-channel policy" in error for error in errors)
            )

    def test_latest_release_and_fixed_ref_allow_replace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, data = self.make_migrated_mapping(root)
            entry = data["skills"][0]
            for mode_holder in (entry, entry["upstream"], entry["origins"][0]):
                mode_holder["sync_mode"] = "replace"
            tracking = entry["origins"][0]["tracking"]
            tracking["channel"] = "latest_release"
            tracking["ref"] = "v1.2.3"
            entry["upstream"]["ref"] = "v1.2.3"
            mapping.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual([], validator.validate_mapping(mapping, root))

    def test_latest_release_requires_resolved_and_path_commits_for_replace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, data = self.make_migrated_mapping(root)
            entry = data["skills"][0]
            for mode_holder in (entry, entry["upstream"], entry["origins"][0]):
                mode_holder["sync_mode"] = "replace"
            tracking = entry["origins"][0]["tracking"]
            tracking["channel"] = "latest_release"
            tracking["ref"] = "v1.2.3"
            entry["upstream"]["ref"] = "v1.2.3"

            for missing_key in ("resolved_commit", "path_commit"):
                case = deepcopy(data)
                case_tracking = case["skills"][0]["origins"][0]["tracking"]
                case_tracking[missing_key] = None
                mapping.write_text(json.dumps(case), encoding="utf-8")
                errors = validator.validate_mapping(mapping, root)
                self.assertTrue(
                    any(
                        "violates release-channel policy" in error
                        for error in errors
                    ),
                    errors,
                )
                self.assertFalse(
                    provenance.replacement_allowed(
                        "mirror",
                        case_tracking,
                        case["skills"][0]["origins"][0]["repo"],
                    )
                )

            tracking["channel"] = "fixed_ref"
            tracking["ref"] = "a" * 40
            entry["upstream"]["ref"] = "a" * 40
            mapping.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual([], validator.validate_mapping(mapping, root))

    def test_replace_requires_content_hash_for_release_and_fixed_commit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, original = self.make_migrated_mapping(root)
            for channel, ref in (
                ("latest_release", "v1.2.3"),
                ("fixed_ref", "a" * 40),
            ):
                with self.subTest(channel=channel):
                    data = deepcopy(original)
                    entry = data["skills"][0]
                    for holder in (
                        entry,
                        entry["upstream"],
                        entry["origins"][0],
                    ):
                        holder["sync_mode"] = "replace"
                    tracking = entry["origins"][0]["tracking"]
                    tracking["channel"] = channel
                    tracking["ref"] = ref
                    tracking["content_sha256"] = None
                    entry["upstream"]["ref"] = ref
                    mapping.write_text(json.dumps(data), encoding="utf-8")

                    errors = validator.validate_mapping(mapping, root)
                    self.assertTrue(
                        any(
                            "violates release-channel policy" in error
                            for error in errors
                        ),
                        errors,
                    )
                    self.assertFalse(
                        provenance.replacement_allowed(
                            "mirror",
                            tracking,
                            entry["origins"][0]["repo"],
                        )
                    )

    def test_validator_rejects_entry_origin_and_legacy_mode_disagreement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, data = self.make_migrated_mapping(root)
            data["skills"][0]["sync_mode"] = "replace"
            mapping.write_text(json.dumps(data), encoding="utf-8")

            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(
                any("upstream.sync_mode must match entry" in error for error in errors)
            )
            self.assertTrue(
                any("must match entry sync_mode" in error for error in errors)
            )

    def test_repo_skill_requires_exactly_one_responsible_origin_artifact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, data = self.make_migrated_mapping(root)
            entry = data["skills"][0]
            owner_artifact = deepcopy(entry["origins"][0]["artifacts"][0])
            entry["origins"][0]["artifacts"].append(owner_artifact)
            mapping.write_text(json.dumps(data), encoding="utf-8")

            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(
                any(
                    "exactly one responsible origin/artifact; found 2" in error
                    for error in errors
                ),
                errors,
            )

            entry["origins"][0]["artifacts"] = []
            mapping.write_text(json.dumps(data), encoding="utf-8")
            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(
                any(
                    "exactly one responsible origin/artifact; found 0" in error
                    for error in errors
                ),
                errors,
            )

    def test_external_legacy_projection_must_match_responsible_owner(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, data = self.make_migrated_mapping(root)
            entry = data["skills"][0]

            mutations = (
                ("repo", "different/upstream", "upstream.repo"),
                ("path", "wrong/SKILL.md", "upstream.path"),
                ("ref", "master", "upstream.ref"),
                ("last_checked_at", "2026-08-19", "upstream.last_checked_at"),
                ("last_synced_at", "2026-08-19", "upstream.last_synced_at"),
                (
                    "last_synced_commit",
                    "b" * 40,
                    "upstream.last_synced_commit",
                ),
            )
            for field, value, expected_message in mutations:
                with self.subTest(field=field):
                    case = deepcopy(data)
                    case["skills"][0]["upstream"][field] = value
                    mapping.write_text(json.dumps(case), encoding="utf-8")
                    errors = validator.validate_mapping(mapping, root)
                    self.assertTrue(
                        any(expected_message in error for error in errors),
                        errors,
                    )

    def test_local_legacy_projection_uses_origin_directory_and_dates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, data = self.make_migrated_mapping(
                root,
                in_house=True,
            )
            entry = data["skills"][0]
            entry["upstream"]["path"] = entry["repo_skill"]
            entry["upstream"]["last_checked_at"] = "2026-08-19"
            entry["origins"][0]["artifacts"][0]["source"] = (
                "skills/category/example/other.md"
            )
            mapping.write_text(json.dumps(data), encoding="utf-8")

            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(any("upstream.path" in error for error in errors), errors)
            self.assertTrue(
                any("upstream.last_checked_at" in error for error in errors),
                errors,
            )
            self.assertTrue(
                any(".source must match local repo_skill" in error for error in errors),
                errors,
            )

    def test_all_external_origins_require_matching_channel_and_ref(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, data = self.make_migrated_mapping(root)
            entry = data["skills"][0]
            entry["kind"] = "snapshot"
            for holder in (entry, entry["upstream"], entry["origins"][0]):
                holder["sync_mode"] = "local-only"
            tracking = entry["origins"][0]["tracking"]
            tracking["channel"] = "fixed_ref"
            tracking["ref"] = "main"
            mapping.write_text(json.dumps(data), encoding="utf-8")

            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(
                any("tracking.channel 'fixed_ref' conflicts" in error for error in errors),
                errors,
            )

    def test_frontmatter_source_must_match_external_kind(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            rel = write_skill(
                root,
                "example",
                source="in-house",
                source_url="https://github.com/example/skills",
            )
            data = provenance.migrate_payload(
                payload([legacy_entry("example", rel)]), root
            )
            mapping = root / "example.skills.json"
            mapping.write_text(json.dumps(data), encoding="utf-8")

            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(
                any("conflicts with external kind mirror" in error for error in errors)
            )

    def test_managed_and_artifact_paths_cannot_escape(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, data = self.make_migrated_mapping(root)
            data["skills"][0]["managed_files"] = [
                {
                    "path": "../outside",
                    "sha256": None,
                    "owner": "example",
                }
            ]
            data["skills"][0]["origins"][0]["artifacts"][0]["target"] = "/tmp/file"
            mapping.write_text(json.dumps(data), encoding="utf-8")

            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(any(".path must be a safe relative path" in error for error in errors))
            self.assertTrue(any(".target must be a safe relative path" in error for error in errors))

    def test_canonical_managed_files_are_owned_contained_and_match_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, data = self.make_migrated_mapping(root)
            entry = data["skills"][0]
            entry["managed_files"].append(
                {
                    "path": "README.md",
                    "sha256": None,
                    "owner": "wrong-owner",
                }
            )
            mapping.write_text(json.dumps(data), encoding="utf-8")

            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(
                any(
                    "must be covered by an exact file artifact" in error
                    for error in errors
                )
            )
            self.assertTrue(
                any("must stay within" in error for error in errors)
            )
            self.assertTrue(
                any("owner must match normalized_slug" in error for error in errors)
            )

    def test_directory_artifact_covers_only_explicit_managed_descendants(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, data = self.make_migrated_mapping(root)
            entry = data["skills"][0]
            references_root = "skills/category/example/references"
            guide = f"{references_root}/guide.md"
            guide_path = root / guide
            guide_path.parent.mkdir(parents=True)
            guide_path.write_text("guide\n", encoding="utf-8")
            entry["origins"][0]["artifacts"].append(
                {
                    "source": "skills/example/references",
                    "target": references_root,
                    "type": "directory",
                }
            )
            entry["managed_files"].append(
                {
                    "path": guide,
                    "sha256": provenance.sha256_file(guide_path),
                    "owner": "example",
                }
            )
            mapping.write_text(json.dumps(data), encoding="utf-8")

            self.assertEqual([], validator.validate_mapping(mapping, root))

            orphan = "skills/category/example/assets/orphan.md"
            orphan_path = root / orphan
            orphan_path.parent.mkdir(parents=True)
            orphan_path.write_text("orphan\n", encoding="utf-8")
            entry["managed_files"].append(
                {
                    "path": orphan,
                    "sha256": provenance.sha256_file(orphan_path),
                    "owner": "example",
                }
            )
            mapping.write_text(json.dumps(data), encoding="utf-8")

            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(
                any(
                    "must be covered by an exact file artifact" in error
                    for error in errors
                ),
                errors,
            )

    def test_managed_sidecar_missing_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, data = self.make_migrated_mapping(root)
            entry = data["skills"][0]
            sidecar = "skills/category/example/references/missing.md"
            entry["origins"][0]["artifacts"].append(
                {"source": "references/missing.md", "target": sidecar, "type": "file"}
            )
            entry["managed_files"].append(
                {"path": sidecar, "sha256": "0" * 64, "owner": "example"}
            )
            mapping.write_text(json.dumps(data), encoding="utf-8")

            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(
                any("managed file" in error and "is missing" in error for error in errors),
                errors,
            )

    def test_managed_terminal_symlink_is_rejected_without_reading_target(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, data = self.make_migrated_mapping(root)
            external = root.parent / f"{root.name}-external.md"
            external.write_text("external sentinel\n", encoding="utf-8")
            self.addCleanup(external.unlink, missing_ok=True)
            sidecar = "skills/category/example/references/link.md"
            sidecar_path = root / sidecar
            sidecar_path.parent.mkdir(parents=True)
            sidecar_path.symlink_to(external)
            entry = data["skills"][0]
            entry["origins"][0]["artifacts"].append(
                {"source": "references/link.md", "target": sidecar, "type": "file"}
            )
            entry["managed_files"].append(
                {"path": sidecar, "sha256": "0" * 64, "owner": "example"}
            )
            mapping.write_text(json.dumps(data), encoding="utf-8")

            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(
                any("must not be a symlink" in error for error in errors),
                errors,
            )
            self.assertTrue(
                any("resolves outside the repository root" in error for error in errors),
                errors,
            )
            self.assertEqual("external sentinel\n", external.read_text(encoding="utf-8"))

    def test_managed_non_regular_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, data = self.make_migrated_mapping(root)
            sidecar = "skills/category/example/references/not-a-file"
            (root / sidecar).mkdir(parents=True)
            entry = data["skills"][0]
            entry["origins"][0]["artifacts"].append(
                {"source": "references/not-a-file", "target": sidecar, "type": "file"}
            )
            entry["managed_files"].append(
                {"path": sidecar, "sha256": "0" * 64, "owner": "example"}
            )
            mapping.write_text(json.dumps(data), encoding="utf-8")

            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(
                any("must be a regular file" in error for error in errors),
                errors,
            )

    def test_managed_parent_symlink_is_rejected_even_when_target_is_inside_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping, data = self.make_migrated_mapping(root)
            real_references = root / "real-references"
            real_references.mkdir()
            real_sidecar = real_references / "guide.md"
            real_sidecar.write_text("guide\n", encoding="utf-8")
            skill_root = root / "skills/category/example"
            (skill_root / "references").symlink_to(real_references, target_is_directory=True)
            sidecar = "skills/category/example/references/guide.md"
            entry = data["skills"][0]
            entry["origins"][0]["artifacts"].append(
                {"source": "references/guide.md", "target": sidecar, "type": "file"}
            )
            entry["managed_files"].append(
                {
                    "path": sidecar,
                    "sha256": provenance.sha256_file(real_sidecar),
                    "owner": "example",
                }
            )
            mapping.write_text(json.dumps(data), encoding="utf-8")

            errors = validator.validate_mapping(mapping, root)
            self.assertTrue(
                any("parent component" in error and "is a symlink" in error for error in errors),
                errors,
            )

    def test_duplicate_active_claims_fail_across_mappings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            rel = write_skill(root, "example")
            first = root / "first.skills.json"
            second = root / "second.skills.json"
            first.write_text(
                json.dumps(payload([legacy_entry("example", rel)])),
                encoding="utf-8",
            )
            second.write_text(
                json.dumps(payload([legacy_entry("example", rel)])),
                encoding="utf-8",
            )

            errors = validator.validate_repository_mappings([first, second], root)
            self.assertTrue(
                any("duplicate active repo_skill claim" in error for error in errors)
            )
            self.assertTrue(
                any(
                    "duplicate active normalized_slug claim" in error
                    for error in errors
                )
            )

    def test_duplicate_managed_file_claims_fail_across_mappings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mappings: list[Path] = []
            for slug in ("first", "second"):
                mapping, data = self.make_migrated_mapping(root, slug)
                data["skills"][0]["managed_files"].append(
                    {
                        "path": "skills/shared/reference.md",
                        "sha256": None,
                        "owner": slug,
                    }
                )
                mapping.write_text(json.dumps(data), encoding="utf-8")
                mappings.append(mapping)

            errors = validator.validate_repository_mappings(mappings, root)
            self.assertTrue(
                any(
                    "duplicate active managed file claim" in error
                    for error in errors
                )
            )

    def test_composition_checks_skill_dependencies_but_allows_source_package(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dependency_mapping, dependency_data = self.make_migrated_mapping(
                root, "dependency"
            )
            composite_mapping, composite_data = self.make_migrated_mapping(
                root, "composite", in_house=True
            )
            composite = composite_data["skills"][0]
            composite["kind"] = "composite"
            dependency_hash = provenance.sha256_file(
                root / dependency_data["skills"][0]["repo_skill"]
            )
            bundle_hash = "c" * 64
            bundle_mapping, _ = self.make_bundle_mapping(
                root,
                content_hash=bundle_hash,
            )
            composite["composition"] = {
                "depends_on": [
                    {"skill": "dependency", "role": "knowledge graph"},
                    {
                        "source_package": "open-gsd/gsd-core",
                        "role": "planning runtime",
                    },
                ],
                "dependency_lock": {
                    "dependency": dependency_hash,
                    "open-gsd/gsd-core": bundle_hash,
                },
            }
            composite_mapping.write_text(
                json.dumps(composite_data), encoding="utf-8"
            )

            per_mapping_errors = validator.validate_mapping(
                composite_mapping, root
            )
            repository_errors = validator.validate_repository_mappings(
                [dependency_mapping, bundle_mapping, composite_mapping], root
            )
            self.assertEqual([], per_mapping_errors)
            self.assertEqual([], repository_errors)

    def test_source_package_dependency_requires_a_unique_bundle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            composite_mapping, composite_data = self.make_migrated_mapping(
                root, "composite", in_house=True
            )
            entry = composite_data["skills"][0]
            entry["kind"] = "composite"
            entry["composition"] = {
                "depends_on": [
                    {
                        "source_package": "open-gsd/gsd-core",
                        "role": "planning runtime",
                    }
                ],
                "dependency_lock": {"open-gsd/gsd-core": "a" * 64},
            }
            composite_mapping.write_text(
                json.dumps(composite_data), encoding="utf-8"
            )

            missing_errors = validator.validate_repository_mappings(
                [composite_mapping], root
            )
            self.assertTrue(
                any(
                    "missing source_package bundle: open-gsd/gsd-core" in error
                    for error in missing_errors
                ),
                missing_errors,
            )

            first_bundle, _ = self.make_bundle_mapping(
                root, suffix="first", content_hash="a" * 64
            )
            second_bundle, _ = self.make_bundle_mapping(
                root, suffix="second", content_hash="a" * 64
            )
            duplicate_errors = validator.validate_repository_mappings(
                [first_bundle, second_bundle, composite_mapping], root
            )
            self.assertTrue(
                any(
                    "ambiguous source_package bundle open-gsd/gsd-core"
                    in error
                    for error in duplicate_errors
                ),
                duplicate_errors,
            )

    def test_source_package_identifiers_and_lock_keys_are_canonical_lowercase(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            composite_mapping, composite_data = self.make_migrated_mapping(
                root, "composite", in_house=True
            )
            entry = composite_data["skills"][0]
            entry["kind"] = "composite"
            entry["composition"] = {
                "depends_on": [
                    {
                        "source_package": "Open-GSD/GSD-Core",
                        "role": "uppercase variant",
                    },
                    {
                        "source_package": "open-gsd/gsd-core",
                        "role": "canonical variant",
                    },
                ],
                "dependency_lock": {
                    "Open-GSD/GSD-Core": "a" * 64,
                    "open-gsd/gsd-core": "a" * 64,
                },
            }
            composite_mapping.write_text(
                json.dumps(composite_data), encoding="utf-8"
            )

            errors = validator.validate_mapping(composite_mapping, root)
            self.assertTrue(
                any(
                    "source_package must use canonical lowercase" in error
                    for error in errors
                ),
                errors,
            )
            self.assertTrue(
                any(
                    "depends_on must not contain duplicate dependencies" in error
                    for error in errors
                ),
                errors,
            )
            self.assertTrue(
                any(
                    "dependency_lock key 'Open-GSD/GSD-Core' must use "
                    "canonical lowercase" in error
                    for error in errors
                ),
                errors,
            )
            self.assertTrue(
                any(
                    "case-insensitive duplicate source_package keys" in error
                    for error in errors
                ),
                errors,
            )

            entry["composition"] = {
                "depends_on": [
                    {
                        "source_package": "open-gsd/gsd-core",
                        "role": "planning runtime",
                    }
                ],
                "dependency_lock": {"Open-GSD/GSD-Core": "a" * 64},
            }
            composite_mapping.write_text(
                json.dumps(composite_data), encoding="utf-8"
            )
            errors = validator.validate_mapping(composite_mapping, root)
            self.assertTrue(
                any(
                    "dependency_lock key 'Open-GSD/GSD-Core' must use "
                    "canonical lowercase" in error
                    for error in errors
                ),
                errors,
            )

    def test_source_package_lookup_is_case_insensitive_for_bundle_origin(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bundle_mapping, _ = self.make_bundle_mapping(
                root,
                repo="Open-GSD/GSD-Core",
                content_hash="a" * 64,
            )
            composite_mapping, composite_data = self.make_migrated_mapping(
                root, "composite", in_house=True
            )
            entry = composite_data["skills"][0]
            entry["kind"] = "composite"
            entry["composition"] = {
                "depends_on": [
                    {
                        "source_package": "open-gsd/gsd-core",
                        "role": "planning runtime",
                    }
                ],
                "dependency_lock": {"open-gsd/gsd-core": "a" * 64},
            }
            composite_mapping.write_text(
                json.dumps(composite_data), encoding="utf-8"
            )

            self.assertEqual(
                [],
                validator.validate_repository_mappings(
                    [bundle_mapping, composite_mapping],
                    root,
                ),
            )

    def test_source_package_dependency_rejects_null_lock(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            composite_mapping, composite_data = self.make_migrated_mapping(
                root, "composite", in_house=True
            )
            entry = composite_data["skills"][0]
            entry["kind"] = "composite"
            entry["composition"] = {
                "depends_on": [
                    {
                        "source_package": "open-gsd/gsd-core",
                        "role": "planning runtime",
                    }
                ],
                "dependency_lock": {"open-gsd/gsd-core": None},
            }
            composite_mapping.write_text(
                json.dumps(composite_data), encoding="utf-8"
            )

            errors = validator.validate_mapping(composite_mapping, root)
            self.assertTrue(
                any(
                    "dependency_lock['open-gsd/gsd-core'] must be a SHA-256 hash"
                    in error
                    for error in errors
                ),
                errors,
            )

    def test_source_package_dependency_requires_bundle_content_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bundle_mapping, _ = self.make_bundle_mapping(
                root, content_hash=None
            )
            composite_mapping, composite_data = self.make_migrated_mapping(
                root, "composite", in_house=True
            )
            entry = composite_data["skills"][0]
            entry["kind"] = "composite"
            entry["composition"] = {
                "depends_on": [
                    {
                        "source_package": "open-gsd/gsd-core",
                        "role": "planning runtime",
                    }
                ],
                "dependency_lock": {"open-gsd/gsd-core": "a" * 64},
            }
            composite_mapping.write_text(
                json.dumps(composite_data), encoding="utf-8"
            )

            errors = validator.validate_repository_mappings(
                [bundle_mapping, composite_mapping], root
            )
            self.assertTrue(
                any(
                    "cannot resolve content hash for source_package "
                    "open-gsd/gsd-core" in error
                    for error in errors
                ),
                errors,
            )

    def test_source_package_dependency_detects_stale_and_matching_locks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            current_hash = "c" * 64
            bundle_mapping, _ = self.make_bundle_mapping(
                root, content_hash=current_hash
            )
            composite_mapping, composite_data = self.make_migrated_mapping(
                root, "composite", in_house=True
            )
            entry = composite_data["skills"][0]
            entry["kind"] = "composite"
            entry["composition"] = {
                "depends_on": [
                    {
                        "source_package": "open-gsd/gsd-core",
                        "role": "planning runtime",
                    }
                ],
                "dependency_lock": {"open-gsd/gsd-core": "0" * 64},
            }
            composite_mapping.write_text(
                json.dumps(composite_data), encoding="utf-8"
            )

            stale_errors = validator.validate_repository_mappings(
                [bundle_mapping, composite_mapping], root
            )
            self.assertTrue(
                any(
                    "source_package open-gsd/gsd-core advanced" in error
                    for error in stale_errors
                ),
                stale_errors,
            )

            entry["composition"]["dependency_lock"][
                "open-gsd/gsd-core"
            ] = current_hash
            composite_mapping.write_text(
                json.dumps(composite_data), encoding="utf-8"
            )
            self.assertEqual(
                [],
                validator.validate_repository_mappings(
                    [bundle_mapping, composite_mapping], root
                ),
            )

    def test_missing_skill_dependency_and_cycles_fail(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            paths: list[Path] = []
            for slug, dependency in (("alpha", "beta"), ("beta", "alpha")):
                mapping, data = self.make_migrated_mapping(
                    root, slug, in_house=True
                )
                entry = data["skills"][0]
                entry["kind"] = "composite"
                entry["composition"] = {
                    "depends_on": [
                        {"skill": dependency, "role": "workflow dependency"}
                    ],
                    "dependency_lock": {dependency: "0" * 64},
                }
                mapping.write_text(json.dumps(data), encoding="utf-8")
                paths.append(mapping)

            errors = validator.validate_repository_mappings(paths, root)
            self.assertTrue(
                any("composition dependency cycle" in error for error in errors)
            )

            beta_data = json.loads(paths[1].read_text(encoding="utf-8"))
            beta_data["skills"][0]["composition"] = {
                "depends_on": [{"skill": "missing", "role": "missing role"}],
                "dependency_lock": {"missing": "0" * 64},
            }
            paths[1].write_text(json.dumps(beta_data), encoding="utf-8")
            errors = validator.validate_repository_mappings(paths, root)
            self.assertTrue(
                any("missing skill dependency: missing" in error for error in errors)
            )

    def test_skill_dependency_resolves_only_active_canonical_available_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dependency_mapping, dependency_data = self.make_migrated_mapping(
                root, "dependency"
            )
            composite_mapping, composite_data = self.make_migrated_mapping(
                root, "composite", in_house=True
            )
            composite = composite_data["skills"][0]
            composite["kind"] = "composite"
            composite["composition"] = {
                "depends_on": [
                    {"skill": "dependency", "role": "workflow dependency"}
                ],
                "dependency_lock": {"dependency": "a" * 64},
            }
            composite_mapping.write_text(
                json.dumps(composite_data), encoding="utf-8"
            )

            retired = deepcopy(dependency_data)
            retired_entry = retired["skills"][0]
            retired_entry["status"] = "retired"
            retired_entry["repo_skill"] = None
            dependency_mapping.write_text(
                json.dumps(retired), encoding="utf-8"
            )
            errors = validator.validate_repository_mappings(
                [dependency_mapping, composite_mapping],
                root,
            )
            self.assertTrue(
                any(
                    "missing skill dependency: dependency "
                    "(unavailable or non-canonical)" in error
                    for error in errors
                ),
                errors,
            )

            malformed = deepcopy(dependency_data)
            malformed["skills"][0]["repo_skill"] = (
                "skills/category/not-dependency/SKILL.md"
            )
            dependency_mapping.write_text(
                json.dumps(malformed), encoding="utf-8"
            )
            errors = validator.validate_repository_mappings(
                [dependency_mapping, composite_mapping],
                root,
            )
            self.assertTrue(
                any(
                    "missing skill dependency: dependency "
                    "(unavailable or non-canonical)" in error
                    for error in errors
                ),
                errors,
            )

            (root / dependency_data["skills"][0]["repo_skill"]).unlink()
            dependency_mapping.write_text(
                json.dumps(dependency_data), encoding="utf-8"
            )
            errors = validator.validate_repository_mappings(
                [dependency_mapping, composite_mapping],
                root,
            )
            self.assertTrue(
                any(
                    "missing skill dependency: dependency "
                    "(unavailable or non-canonical)" in error
                    for error in errors
                ),
                errors,
            )

    def test_source_package_dependency_rejects_retired_bundle_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bundle_mapping, bundle_data = self.make_bundle_mapping(root)
            bundle_data["skills"][0]["status"] = "retired"
            bundle_mapping.write_text(json.dumps(bundle_data), encoding="utf-8")

            composite_mapping, composite_data = self.make_migrated_mapping(
                root, "composite", in_house=True
            )
            composite = composite_data["skills"][0]
            composite["kind"] = "composite"
            composite["composition"] = {
                "depends_on": [
                    {
                        "source_package": "open-gsd/gsd-core",
                        "role": "planning runtime",
                    }
                ],
                "dependency_lock": {"open-gsd/gsd-core": "a" * 64},
            }
            composite_mapping.write_text(
                json.dumps(composite_data), encoding="utf-8"
            )

            errors = validator.validate_repository_mappings(
                [bundle_mapping, composite_mapping],
                root,
            )
            self.assertTrue(
                any(
                    "unavailable source_package bundle: open-gsd/gsd-core"
                    in error
                    for error in errors
                ),
                errors,
            )

    def test_dependency_lock_detects_stale_composite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dependency_mapping, _ = self.make_migrated_mapping(root, "dependency")
            composite_mapping, composite_data = self.make_migrated_mapping(
                root, "composite", in_house=True
            )
            entry = composite_data["skills"][0]
            entry["kind"] = "composite"
            entry["composition"] = {
                "depends_on": [{"skill": "dependency", "role": "workflow"}],
                "dependency_lock": {"dependency": "0" * 64},
            }
            composite_mapping.write_text(
                json.dumps(composite_data), encoding="utf-8"
            )

            errors = validator.validate_repository_mappings(
                [dependency_mapping, composite_mapping], root
            )
            self.assertTrue(any("composite composite is stale" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
