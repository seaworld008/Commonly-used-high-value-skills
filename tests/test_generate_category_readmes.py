import importlib.util
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_category_readmes.py"


def load_module():
    spec = importlib.util.spec_from_file_location("generate_category_readmes", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load generator from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GenerateCategoryReadmesTests(unittest.TestCase):
    def test_generate_category_readme_from_skill_tree(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            skills_root = tmp / "skills"
            category_dir = skills_root / "finance-investing"
            rich_skill = category_dir / "financial-data-collector"
            simple_skill = category_dir / "comps-valuation-analyst"
            rich_skill.mkdir(parents=True)
            simple_skill.mkdir(parents=True)

            (rich_skill / "scripts").mkdir()
            (rich_skill / "references").mkdir()
            (simple_skill / "scripts").mkdir()

            (rich_skill / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    name: financial-data-collector
                    description: Use when collecting structured public-market and filing data.
                    ---

                    # Financial Data Collector
                    """
                ),
                encoding="utf-8",
            )

            (simple_skill / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    # Comps Valuation Analyst

                    Build a comparable-company valuation quickly for public equities.
                    """
                ),
                encoding="utf-8",
            )

            module.generate_category_readmes(skills_root)

            readme_text = (category_dir / "README.md").read_text(encoding="utf-8")
            self.assertIn("# 金融投资 / Finance Investing", readme_text)
            self.assertIn("[financial-data-collector](./financial-data-collector/)", readme_text)
            self.assertIn("Use when collecting structured public-market and filing data.", readme_text)
            self.assertIn("[comps-valuation-analyst](./comps-valuation-analyst/)", readme_text)
            self.assertIn("Build a comparable-company valuation quickly", readme_text)

    def test_body_description_skips_metadata_markers(self):
        module = load_module()
        body = textwrap.dedent(
            """\
            # Example Skill

            **Tier:** POWERFUL
            **Category:** Engineering

            ---

            Useful skill summary line.

            ## Workflow
            """
        )
        self.assertEqual("Useful skill summary line.", module.derive_description_from_body(body))


if __name__ == "__main__":
    unittest.main()
