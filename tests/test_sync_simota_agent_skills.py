import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import sync_simota_agent_skills as sync_simota


class SyncSimotaAgentSkillsTests(unittest.TestCase):
    def test_retains_local_snapshot_when_selected_upstream_skill_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_dir = root / "upstream"
            source_dir.mkdir()
            local_skill = root / "repo/skills/ai-agent-platform/arena/SKILL.md"
            local_skill.parent.mkdir(parents=True)
            local_skill.write_text("# Arena\n", encoding="utf-8")
            mapping = root / "repo" / sync_simota.SOURCE_MAPPING_REL
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "normalized_slug": "arena",
                                "repo_skill": "skills/ai-agent-platform/arena/SKILL.md",
                                "notes": "Original note.",
                                "upstream": {
                                    "repo": sync_simota.SOURCE_REPO,
                                    "path": "arena/SKILL.md",
                                    "last_synced_commit": "abc123",
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(
                sync_simota,
                "SELECTED_SKILLS",
                {"ai-agent-platform": [("arena", "Arena description.")]},
            ):
                entries, missing = sync_simota.import_selected(
                    source_dir,
                    root / "repo",
                    apply=False,
                )

            self.assertEqual(missing, ["arena"])
            self.assertEqual(entries[0]["upstream"]["sync_mode"], "local-only")
            self.assertEqual(entries[0]["upstream"]["availability"], "missing")
            self.assertEqual(entries[0]["upstream"]["last_synced_commit"], "abc123")
            self.assertIn("Retained from the last permissively licensed", entries[0]["notes"])

    def test_missing_upstream_without_local_snapshot_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_dir = root / "upstream"
            source_dir.mkdir()

            with patch.object(
                sync_simota,
                "SELECTED_SKILLS",
                {"ai-agent-platform": [("arena", "Arena description.")]},
            ):
                with self.assertRaisesRegex(FileNotFoundError, "no retained local snapshot"):
                    sync_simota.import_selected(source_dir, root / "repo", apply=False)

    def test_apply_preserves_local_quality_supplements_missing_upstream(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_skill = root / "upstream/builder"
            source_skill.mkdir(parents=True)
            source_skill.joinpath("SKILL.md").write_text(
                "---\nname: builder\ndescription: Build production code.\n---\n# Builder\n",
                encoding="utf-8",
            )
            destination = root / "repo/skills/developer-engineering/builder"
            supplement = destination / "references/local-quality-supplement.md"
            supplement.parent.mkdir(parents=True)
            supplement.write_text("# Local supplement\n", encoding="utf-8")

            with patch.object(
                sync_simota,
                "SELECTED_SKILLS",
                {"developer-engineering": [("builder", "Builder description.")]},
            ):
                entries, missing = sync_simota.import_selected(
                    root / "upstream",
                    root / "repo",
                    apply=True,
                )

            self.assertEqual(len(entries), 1)
            self.assertEqual(missing, [])
            self.assertTrue(supplement.exists())
            skill_text = destination.joinpath("SKILL.md").read_text(encoding="utf-8")
            self.assertIn("# Builder", skill_text)
            self.assertIn('zh_description: "Builder description."', skill_text)
            self.assertIn("## Local Execution Contract", skill_text)
            self.assertIn("```yaml", skill_text)

    def test_apply_ignores_upstream_symlinks_without_following_them(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_skill = root / "upstream/builder"
            source_skill.mkdir(parents=True)
            source_skill.joinpath("SKILL.md").write_text(
                "---\nname: builder\ndescription: Build production code.\n---\n# Builder\n",
                encoding="utf-8",
            )
            external = root / "upstream/_common"
            external.mkdir()
            external.joinpath("sentinel.md").write_text(
                "must not be copied\n",
                encoding="utf-8",
            )
            source_skill.joinpath("_common").symlink_to(
                external,
                target_is_directory=True,
            )

            with patch.object(
                sync_simota,
                "SELECTED_SKILLS",
                {"developer-engineering": [("builder", "Builder description.")]},
            ):
                entries, missing = sync_simota.import_selected(
                    root / "upstream",
                    root / "repo",
                    apply=True,
                )

            destination = root / "repo/skills/developer-engineering/builder"
            self.assertEqual(len(entries), 1)
            self.assertEqual(missing, [])
            self.assertFalse(destination.joinpath("_common").exists())
            self.assertFalse(destination.joinpath("_common").is_symlink())

    def test_source_mapping_is_written_under_requested_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo_root = Path(temp) / "repo"
            sync_simota.write_source_mapping([], repo_root)

            mapping = repo_root / sync_simota.SOURCE_MAPPING_REL
            self.assertTrue(mapping.exists())
            self.assertEqual(json.loads(mapping.read_text(encoding="utf-8"))["skills"], [])

    def test_apply_preflight_rejects_provenance_v2_downgrade(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo_root = Path(temp) / "repo"
            mapping = repo_root / sync_simota.SOURCE_MAPPING_REL
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps({"schema_version": 2, "skills": []}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "refusing to downgrade"):
                sync_simota.require_legacy_mapping_for_apply(repo_root)


if __name__ == "__main__":
    unittest.main()
