import importlib.util
import json
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "sync_addyosmani_agent_skills.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sync_addyosmani_agent_skills", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SyncAddyOsmaniAgentSkillsTests(unittest.TestCase):
    def test_sync_imports_upstream_skills_moves_existing_and_writes_mapping(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            upstream = root / "upstream"
            repo = root / "repo"
            upstream.mkdir()
            repo.mkdir()

            upstream_skill = upstream / "skills" / "test-driven-development"
            upstream_skill.mkdir(parents=True)
            (upstream_skill / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    name: test-driven-development
                    description: Drives development with tests.
                    ---

                    # Test Driven Development

                    Write the test first.
                    """
                ),
                encoding="utf-8",
            )
            (upstream_skill / "example.md").write_text("example", encoding="utf-8")
            (upstream / "references").mkdir()
            (upstream / "references" / "testing-patterns.md").write_text("patterns", encoding="utf-8")
            (upstream / "agents").mkdir()
            (upstream / "agents" / "code-reviewer.md").write_text("reviewer", encoding="utf-8")
            (upstream / "docs").mkdir()
            (upstream / "docs" / "getting-started.md").write_text("start", encoding="utf-8")

            local_skill = repo / "skills" / "task-understanding-decomposition" / "writing-plans"
            local_skill.mkdir(parents=True)
            (local_skill / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    name: writing-plans
                    description: Write plans.
                    ---

                    # Writing Plans
                    """
                ),
                encoding="utf-8",
            )

            mapping = repo / "docs" / "sources" / "obra-superpowers-2026-04.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(
                    {
                        "video": {"url": "https://github.com/obra/superpowers"},
                        "skills": [
                            {
                                "video_name": "writing-plans",
                                "repo_skill": "skills/task-understanding-decomposition/writing-plans/SKILL.md",
                                "upstream": {"repo": "obra/superpowers"},
                            },
                            {
                                "video_name": "test-driven-development",
                                "repo_skill": "skills/developer-engineering/test-driven-development/SKILL.md",
                                "upstream": {"repo": "obra/superpowers"},
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            summary = module.sync_agent_skills(
                repo_root=repo,
                upstream_root=upstream,
                commit="abc123",
                today="2026-04-24",
            )

            self.assertEqual(1, summary["imported_count"])
            self.assertEqual(1, summary["moved_count"])
            imported = repo / "skills" / "ai-workflow" / "test-driven-development"
            self.assertTrue((imported / "SKILL.md").exists())
            self.assertTrue((imported / "example.md").exists())
            self.assertTrue((imported / "references" / "testing-patterns.md").exists())

            skill_text = (imported / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("source: \"github:addyosmani/agent-skills\"", skill_text)
            self.assertIn("upstream_slug: test-driven-development", skill_text)

            self.assertFalse(local_skill.exists())
            self.assertTrue((repo / "skills" / "ai-workflow" / "writing-plans" / "SKILL.md").exists())

            updated_mapping = json.loads(mapping.read_text(encoding="utf-8"))
            self.assertEqual(1, len(updated_mapping["skills"]))
            self.assertEqual(
                "skills/ai-workflow/writing-plans/SKILL.md",
                updated_mapping["skills"][0]["repo_skill"],
            )

            addy_mapping = json.loads((repo / module.MAPPING_FILE).read_text(encoding="utf-8"))
            self.assertEqual("https://github.com/addyosmani/agent-skills", addy_mapping["video"]["url"])
            self.assertEqual("abc123", addy_mapping["skills"][0]["upstream"]["last_synced_commit"])


if __name__ == "__main__":
    unittest.main()
