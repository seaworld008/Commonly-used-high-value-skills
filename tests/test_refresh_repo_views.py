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
    def test_update_root_readmes_refreshes_all_cn_counters(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            readme = repo / "README.md"
            readme_en = repo / "README.en.md"

            readme.write_text(
                textwrap.dedent(
                    """\
                    [![Skills](https://img.shields.io/badge/Skills-1-7c3aed)](./skills/)
                    当前共 **1 个分类 / 1 个技能**。
                    ## 技能总览（按分类，1 类 / 1 技能）
                    以下 **不计入** 上方的 `1 类 / 1 技能` 统计。
                    """
                ),
                encoding="utf-8",
            )
            readme_en.write_text(
                textwrap.dedent(
                    """\
                    [![Skills](https://img.shields.io/badge/Skills-1-7c3aed)](./skills/)
                    This repository currently contains **1 categories / 1 skills**.
                    """
                ),
                encoding="utf-8",
            )

            module.update_root_readmes(repo, category_count=15, skill_count=139)

            cn_updated = readme.read_text(encoding="utf-8")
            en_updated = readme_en.read_text(encoding="utf-8")

            self.assertIn("Skills-139-7c3aed", cn_updated)
            self.assertIn("当前共 **15 个分类 / 139 个技能**。", cn_updated)
            self.assertIn("## 技能总览（按分类，15 类 / 139 技能）", cn_updated)
            self.assertIn("`15 类 / 139 技能`", cn_updated)
            self.assertIn("Skills-139-7c3aed", en_updated)
            self.assertIn(
                "This repository currently contains **15 categories / 139 skills**.",
                en_updated,
            )

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
