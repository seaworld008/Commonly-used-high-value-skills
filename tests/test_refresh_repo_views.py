import importlib.util
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "refresh_repo_views.py"


def load_module():
    spec = importlib.util.spec_from_file_location("refresh_repo_views", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RefreshRepoViewsTests(unittest.TestCase):
    def test_refresh_repo_views_generates_category_readmes_and_openclaw_export(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            skills_root = repo / "skills"
            output_root = repo / "openclaw-skills"

            skill_a = skills_root / "developer-engineering" / "demo-skill"
            skill_b = skills_root / "finance-investing" / "finance-skill"
            skill_a.mkdir(parents=True)
            skill_b.mkdir(parents=True)

            (skill_a / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    name: demo-skill
                    description: Use when demo engineering help is needed.
                    ---

                    # Demo Skill
                    """
                ),
                encoding="utf-8",
            )
            (skill_b / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    # Finance Skill

                    ## Overview

                    Analyze finance workflows quickly.
                    """
                ),
                encoding="utf-8",
            )

            summary = module.refresh_repo_views(repo_root=repo, scripts_root=REPO_ROOT / "scripts")

            self.assertEqual(2, summary["source_skill_count"])
            self.assertEqual(2, summary["exported_skill_count"])
            self.assertEqual(2, summary["category_readme_count"])
            self.assertTrue((skills_root / "developer-engineering" / "README.md").exists())
            self.assertTrue((skills_root / "finance-investing" / "README.md").exists())
            self.assertTrue((output_root / "demo-skill" / "SKILL.md").exists())
            self.assertTrue((output_root / "finance-skill" / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
