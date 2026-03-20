import importlib.util
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "normalize_codex_skills.py"


def load_module():
    spec = importlib.util.spec_from_file_location("normalize_codex_skills", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NormalizeCodexSkillsTests(unittest.TestCase):
    def test_normalizes_recursive_skill_tree_in_place(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "skills"
            broken_skill = root / "agent-designer"
            nested_skill = root / "skill-tester" / "assets" / "sample-skill"
            yaml_broken = root / "competitors-analysis"
            broken_skill.mkdir(parents=True)
            nested_skill.mkdir(parents=True)
            yaml_broken.mkdir(parents=True)

            (broken_skill / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    # Agent Designer

                    Analyze agent systems.
                    """
                ),
                encoding="utf-8",
            )

            (nested_skill / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    # Sample Skill

                    ---

                    Broken sample skill body.
                    """
                ),
                encoding="utf-8",
            )

            (yaml_broken / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    name: competitors-analysis
                    description: Bad yaml: because colon breaks parsing
                    context: fork
                    ---

                    # Competitors Analysis
                    """
                ),
                encoding="utf-8",
            )

            summary = module.normalize_codex_skill_tree(root)

            self.assertEqual(3, summary["normalized_count"])
            self.assertEqual(3, summary["skill_file_count"])

            normalized_text = (broken_skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(normalized_text.startswith("---\n"))
            self.assertIn("name: agent-designer", normalized_text)

            nested_text = (nested_skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("name: sample-skill", nested_text)

            yaml_text = (yaml_broken / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("name: competitors-analysis", yaml_text)
            self.assertIn("context: fork", yaml_text)


if __name__ == "__main__":
    unittest.main()
