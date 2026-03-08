import importlib.util
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "export_openclaw_skills.py"


def load_export_module():
    spec = importlib.util.spec_from_file_location("export_openclaw_skills", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load exporter from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExportOpenClawSkillsTests(unittest.TestCase):
    def test_export_flattens_skill_tree_and_synthesizes_frontmatter(self):
        module = load_export_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source_root = tmp / "skills"
            output_root = tmp / "openclaw-skills"

            skill_dir = source_root / "developer-engineering" / "demo-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "notes.txt").write_text("supporting text\n", encoding="utf-8")
            (skill_dir / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    # Demo Skill

                    Automates demo workflow for local testing.

                    ## Usage

                    Use this skill when a demo task needs repeatable setup.
                    """
                ),
                encoding="utf-8",
            )

            exported = module.export_openclaw_skills(source_root, output_root)

            self.assertEqual(["demo-skill"], [item.name for item in exported])
            exported_skill = output_root / "demo-skill"
            self.assertTrue((exported_skill / "notes.txt").exists())

            exported_skill_md = (exported_skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(exported_skill_md.startswith("---\n"))
            self.assertIn("name: demo-skill", exported_skill_md)
            self.assertIn("description: Automates demo workflow for local testing.", exported_skill_md)
            self.assertIn("# Demo Skill", exported_skill_md)

    def test_export_preserves_extra_frontmatter_blocks(self):
        module = load_export_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source_root = tmp / "skills"
            output_root = tmp / "openclaw-skills"

            skill_dir = source_root / "knowledge-and-pm-integrations" / "metadata-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    name: metadata-skill
                    description: |
                      Manage remote systems with extra context.
                    metadata:
                      openclaw:
                        requires:
                          env:
                            - API_KEY
                    ---

                    # Metadata Skill

                    Example body.
                    """
                ),
                encoding="utf-8",
            )

            module.export_openclaw_skills(source_root, output_root)

            exported_skill_md = (output_root / "metadata-skill" / "SKILL.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("name: metadata-skill", exported_skill_md)
            self.assertIn("description: Manage remote systems with extra context.", exported_skill_md)
            self.assertIn("metadata:", exported_skill_md)
            self.assertIn("API_KEY", exported_skill_md)
            self.assertIn("# Metadata Skill", exported_skill_md)

    def test_export_quotes_yaml_unsafe_scalars(self):
        module = load_export_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source_root = tmp / "skills"
            output_root = tmp / "openclaw-skills"

            api_skill = source_root / "developer-engineering" / "api-design-reviewer"
            api_skill.mkdir(parents=True)
            (api_skill / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    # API Design Reviewer

                    **Maintainer:** Claude Skills Team

                    Review API designs for consistency.
                    """
                ),
                encoding="utf-8",
            )

            competitor_skill = source_root / "operations-general" / "competitors-analysis"
            competitor_skill.mkdir(parents=True)
            (competitor_skill / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    name: competitors-analysis
                    description: 'Analyze competitor repositories with evidence-based approach.'
                    context: fork
                    agent: general-purpose
                    argument-hint: [product-name] [competitor-url]
                    ---

                    # Competitors Analysis

                    Compare products with repository evidence.
                    """
                ),
                encoding="utf-8",
            )

            module.export_openclaw_skills(source_root, output_root)

            api_text = (output_root / "api-design-reviewer" / "SKILL.md").read_text(encoding="utf-8")
            competitor_text = (output_root / "competitors-analysis" / "SKILL.md").read_text(
                encoding="utf-8"
            )

            self.assertIn("description: 'Maintainer: Claude Skills Team.'", api_text)
            self.assertIn("argument-hint: '[product-name] [competitor-url]'", competitor_text)

    def test_export_forces_name_to_match_directory_for_openclaw_compatibility(self):
        module = load_export_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source_root = tmp / "skills"
            output_root = tmp / "openclaw-skills"

            skill_dir = source_root / "task-understanding-decomposition" / "reflect-learn"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    name: reflect
                    description: Learn from conversation corrections.
                    ---

                    # Reflect Learn
                    """
                ),
                encoding="utf-8",
            )

            module.export_openclaw_skills(source_root, output_root)

            exported_skill_md = (output_root / "reflect-learn" / "SKILL.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("name: reflect-learn", exported_skill_md)


if __name__ == "__main__":
    unittest.main()
