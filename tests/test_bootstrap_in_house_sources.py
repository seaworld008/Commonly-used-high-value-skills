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
            self.assertEqual("verified_in_repo", skills["systematic-debugging"]["status"])
            self.assertEqual("https://github.com/obra/superpowers", skills["systematic-debugging"]["source"])
            self.assertEqual("obra/superpowers", skills["systematic-debugging"]["upstream"]["repo"])
            self.assertEqual("in_house", skills["summary-helper"]["status"])
            self.assertEqual(
                "https://github.com/example/repo",
                skills["summary-helper"]["source"],
            )

    def test_load_existing_payload_returns_none_for_missing_file(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            payload = module.load_existing_payload(Path(tmpdir) / "missing.json")
            self.assertIsNone(payload)


if __name__ == "__main__":
    unittest.main()
