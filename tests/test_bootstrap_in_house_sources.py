import hashlib
import importlib.util
import json
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "bootstrap_in_house_sources.py"


def load_module():
    spec = importlib.util.spec_from_file_location("bootstrap_in_house_sources", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BootstrapInHouseSourcesTests(unittest.TestCase):
    def test_build_mapping_preserves_existing_external_sources(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            existing_skill = repo / "skills" / "developer-engineering" / "systematic-debugging"
            local_only_skill = repo / "skills" / "operations-general" / "summary-helper"
            existing_skill.mkdir(parents=True)
            local_only_skill.mkdir(parents=True)

            (existing_skill / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    name: systematic-debugging
                    description: Systematic debugging.
                    ---
                    """
                ),
                encoding="utf-8",
            )
            (local_only_skill / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    name: summary-helper
                    description: Internal helper.
                    ---
                    """
                ),
                encoding="utf-8",
            )
            cache_dir = local_only_skill / "__pycache__"
            cache_dir.mkdir()
            (cache_dir / "helper.cpython-313.pyc").write_bytes(b"cache")

            existing_payload = {
                "video": {"url": "https://example.com", "checked_at": "2026-03-01"},
                "official_references": [],
                "skills": [
                    {
                        "video_name": "systematic-debugging",
                        "normalized_slug": "systematic-debugging",
                        "status": "verified_in_repo",
                        "repo_skill": "skills/developer-engineering/systematic-debugging/SKILL.md",
                        "source": "https://github.com/obra/superpowers",
                        "notes": "Tracked from upstream.",
                        "upstream": {
                            "repo": "obra/superpowers",
                            "path": "systematic-debugging/SKILL.md",
                            "ref": "main",
                            "last_checked_at": "2026-03-20",
                            "last_synced_at": "2026-03-20",
                            "last_synced_commit": "abc123",
                        },
                    }
                ],
            }

            payload = module.build_in_house_mapping(
                repo_root=repo,
                repo_url="https://github.com/example/repo",
                existing_payload=existing_payload,
                today="2026-03-27",
            )

            skills = {item["video_name"]: item for item in payload["skills"]}
            self.assertEqual(2, payload["schema_version"])
            self.assertEqual("verified_in_repo", skills["systematic-debugging"]["status"])
            self.assertEqual("https://github.com/obra/superpowers", skills["systematic-debugging"]["source"])
            self.assertEqual("obra/superpowers", skills["systematic-debugging"]["upstream"]["repo"])
            self.assertEqual("in_house", skills["summary-helper"]["status"])
            self.assertEqual("in_house", skills["summary-helper"]["kind"])
            self.assertEqual(
                "local-repo/in-house",
                skills["summary-helper"]["origins"][0]["repo"],
            )
            self.assertEqual(
                [
                    {
                        "path": "skills/operations-general/summary-helper/SKILL.md",
                        "sha256": hashlib.sha256(
                            (local_only_skill / "SKILL.md").read_bytes()
                        ).hexdigest(),
                        "owner": "summary-helper",
                    }
                ],
                skills["summary-helper"]["managed_files"],
            )
            self.assertEqual(
                "https://github.com/example/repo",
                skills["summary-helper"]["source"],
            )
            self.assertEqual(
                "2026-03-20",
                skills["systematic-debugging"]["upstream"]["last_checked_at"],
            )
            self.assertEqual(
                "2026-03-20",
                skills["systematic-debugging"]["origins"][0]["tracking"][
                    "last_checked_at"
                ],
            )

    def test_rerun_refreshes_local_hash_dates_and_complete_managed_targets(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            skill_root = (
                repo / "skills" / "operations-general" / "summary-helper"
            )
            skill_root.mkdir(parents=True)
            skill_md = skill_root / "SKILL.md"
            skill_md.write_text(
                "---\n"
                "name: summary-helper\n"
                "source: in-house\n"
                "---\n"
                "# First revision\n",
                encoding="utf-8",
            )

            first = module.build_in_house_mapping(
                repo_root=repo,
                repo_url="https://github.com/example/repo",
                today="2026-03-27",
            )
            first_entry = first["skills"][0]
            first_hash = first_entry["origins"][0]["tracking"][
                "content_sha256"
            ]

            skill_md.write_text(
                skill_md.read_text(encoding="utf-8") + "\nUpdated locally.\n",
                encoding="utf-8",
            )
            reference = skill_root / "references" / "guide.md"
            reference.parent.mkdir()
            reference.write_text("# Guide\n", encoding="utf-8")

            second = module.build_in_house_mapping(
                repo_root=repo,
                repo_url="https://github.com/example/repo",
                existing_payload=first,
                today="2026-03-28",
            )
            entry = second["skills"][0]
            tracking = entry["origins"][0]["tracking"]
            current_hash = hashlib.sha256(skill_md.read_bytes()).hexdigest()

            self.assertNotEqual(first_hash, current_hash)
            self.assertEqual(current_hash, tracking["content_sha256"])
            self.assertEqual("2026-03-28", tracking["last_checked_at"])
            self.assertEqual("2026-03-28", tracking["last_synced_at"])

            expected_targets = {
                "skills/operations-general/summary-helper/SKILL.md",
                "skills/operations-general/summary-helper/references/guide.md",
            }
            managed = {item["path"]: item for item in entry["managed_files"]}
            artifacts = {
                item["target"] for item in entry["origins"][0]["artifacts"]
            }
            self.assertEqual(expected_targets, set(managed))
            self.assertEqual(expected_targets, artifacts)
            for target, record in managed.items():
                self.assertEqual(
                    hashlib.sha256((repo / target).read_bytes()).hexdigest(),
                    record["sha256"],
                )
                self.assertEqual("summary-helper", record["owner"])

    def test_cross_day_scan_only_syncs_when_local_skill_content_changes(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            skill_root = (
                repo / "skills" / "operations-general" / "summary-helper"
            )
            skill_root.mkdir(parents=True)
            skill_md = skill_root / "SKILL.md"
            skill_md.write_text(
                "---\nname: summary-helper\nsource: in-house\n---\n# Initial\n",
                encoding="utf-8",
            )

            first = module.build_in_house_mapping(
                repo_root=repo,
                repo_url="https://github.com/example/repo",
                today="2026-03-27",
            )
            unchanged = module.build_in_house_mapping(
                repo_root=repo,
                repo_url="https://github.com/example/repo",
                existing_payload=first,
                today="2026-03-28",
            )
            unchanged_entry = unchanged["skills"][0]
            unchanged_tracking = unchanged_entry["origins"][0]["tracking"]
            self.assertEqual("2026-03-28", unchanged_tracking["last_checked_at"])
            self.assertEqual("2026-03-27", unchanged_tracking["last_synced_at"])
            self.assertEqual(
                "2026-03-28",
                unchanged_entry["upstream"]["last_checked_at"],
            )
            self.assertEqual(
                "2026-03-27",
                unchanged_entry["upstream"]["last_synced_at"],
            )

            reference = skill_root / "references" / "guide.md"
            reference.parent.mkdir()
            reference.write_text("# Sidecar only\n", encoding="utf-8")
            sidecar_only = module.build_in_house_mapping(
                repo_root=repo,
                repo_url="https://github.com/example/repo",
                existing_payload=unchanged,
                today="2026-03-29",
            )
            sidecar_entry = sidecar_only["skills"][0]
            self.assertEqual(
                "2026-03-27",
                sidecar_entry["origins"][0]["tracking"]["last_synced_at"],
            )

            skill_md.write_text(
                skill_md.read_text(encoding="utf-8") + "\nChanged.\n",
                encoding="utf-8",
            )
            changed = module.build_in_house_mapping(
                repo_root=repo,
                repo_url="https://github.com/example/repo",
                existing_payload=sidecar_only,
                today="2026-03-30",
            )
            changed_entry = changed["skills"][0]
            changed_tracking = changed_entry["origins"][0]["tracking"]
            self.assertEqual("2026-03-30", changed_tracking["last_checked_at"])
            self.assertEqual("2026-03-30", changed_tracking["last_synced_at"])
            self.assertEqual(
                "2026-03-30",
                changed_entry["upstream"]["last_synced_at"],
            )

    def test_load_existing_payload_returns_none_for_missing_file(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            payload = module.load_existing_payload(Path(tmpdir) / "missing.json")
            self.assertIsNone(payload)

    def test_verification_attempts_are_idempotent_for_same_scan(self):
        module = load_module()

        existing_payload = {
            "verification_attempts": [
                {
                    "date": "2026-03-27",
                    "method": "local-scan",
                    "target": "skills/*/*/SKILL.md",
                    "result": "success",
                    "evidence": "Merged provenance for 2 local skills",
                }
            ]
        }

        attempts = module.build_verification_attempts(
            existing_payload=existing_payload,
            today="2026-03-27",
            skill_count=2,
        )

        self.assertEqual(1, len(attempts))

    def test_official_references_drop_placeholder_repository(self):
        module = load_module()

        references = module.build_official_references(
            {
                "official_references": [
                    {
                        "name": "placeholder",
                        "url": module.PLACEHOLDER_REPO_URL,
                        "purpose": "stale bootstrap default",
                    }
                ]
            },
            "https://github.com/seaworld008/Commonly-used-high-value-skills",
        )

        self.assertEqual(1, len(references))
        self.assertEqual(
            "https://github.com/seaworld008/Commonly-used-high-value-skills",
            references[0]["url"],
        )


if __name__ == "__main__":
    unittest.main()
