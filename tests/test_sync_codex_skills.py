import importlib.util
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "sync_codex_skills.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sync_codex_skills", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SyncCodexSkillsTests(unittest.TestCase):
    def test_sync_flattens_categorized_skills_and_preserves_codex_only_extras(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_root = root / "skills"
            codex_root = root / "codex-skills"

            managed = source_root / "developer-engineering" / "agent-designer"
            managed.mkdir(parents=True)
            (managed / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    # Agent Designer

                    Analyze multi-agent systems.
                    """
                ),
                encoding="utf-8",
            )
            (managed / "helper.txt").write_text("helper", encoding="utf-8")

            new_skill = source_root / "operations-general" / "confidence-check"
            new_skill.mkdir(parents=True)
            (new_skill / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    name: confidence-check
                    description: Verify confidence before responding.
                    ---
                    """
                ),
                encoding="utf-8",
            )

            existing_managed = codex_root / "agent-designer"
            existing_managed.mkdir(parents=True)
            (existing_managed / "SKILL.md").write_text("old", encoding="utf-8")
            (existing_managed / "stale.txt").write_text("remove-me", encoding="utf-8")

            extra_only = codex_root / "custom-only"
            extra_only.mkdir(parents=True)
            (extra_only / "SKILL.md").write_text("keep me", encoding="utf-8")

            summary = module.sync_codex_skills(source_root=source_root, codex_root=codex_root)

            self.assertEqual(2, summary["source_skill_count"])
            self.assertEqual(1, summary["added_count"])
            self.assertEqual(1, summary["updated_count"])
            self.assertEqual(1, summary["preserved_extra_count"])

            synced_text = (codex_root / "agent-designer" / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(synced_text.startswith("---\n"))
            self.assertIn("name: agent-designer", synced_text)
            self.assertTrue((codex_root / "agent-designer" / "helper.txt").exists())
            self.assertFalse((codex_root / "agent-designer" / "stale.txt").exists())
            self.assertTrue((codex_root / "confidence-check" / "SKILL.md").exists())
            self.assertTrue((codex_root / "custom-only" / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
