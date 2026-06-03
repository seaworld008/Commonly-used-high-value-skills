import importlib.util
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_readme_sync.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_readme_sync", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CheckReadmeSyncTests(unittest.TestCase):
    def test_current_root_readmes_match_skill_tree(self):
        module = load_module()

        tree = module.actual_skill_tree(REPO_ROOT)
        errors = []
        errors.extend(
            module.validate_readme(
                readme_path=REPO_ROOT / "README.md",
                category_re=module.CN_CATEGORY_RE,
                total_re=module.CN_TOTAL_RE,
                overview_re=module.CN_OVERVIEW_RE,
                expected_tree=tree,
            )
        )
        errors.extend(
            module.validate_readme(
                readme_path=REPO_ROOT / "README.en.md",
                category_re=module.EN_CATEGORY_RE,
                total_re=module.EN_TOTAL_RE,
                overview_re=module.EN_OVERVIEW_RE,
                expected_tree=tree,
            )
        )
        expected_category_count = len(tree)
        expected_skill_count = sum(len(skills) for skills in tree.values())
        errors.extend(
            module.validate_catalog(
                catalog_path=REPO_ROOT / "docs" / "catalog.json",
                expected_category_count=expected_category_count,
                expected_skill_count=expected_skill_count,
            )
        )
        errors.extend(
            module.validate_banner(
                banner_path=REPO_ROOT / ".github" / "assets" / "repo-banner.svg",
                expected_category_count=expected_category_count,
                expected_skill_count=expected_skill_count,
            )
        )

        self.assertEqual([], errors)

    def test_detects_missing_english_skill(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            skill_dir = repo / "skills" / "developer-engineering" / "demo-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: demo-skill\n---\n", encoding="utf-8")
            readme = repo / "README.en.md"
            readme.write_text(
                textwrap.dedent(
                    """\
                    [![Skills](https://img.shields.io/badge/Skills-1-7c3aed)](./skills/)
                    This repository currently contains **1 categories / 1 skills**.
                    ## Skill Overview (by category, 1 categories / 1 skills)

                    <a id="cat-developer-engineering"></a>
                    ### 1. Developer Engineering (developer-engineering, 1)
                    """
                ),
                encoding="utf-8",
            )

            errors = module.validate_readme(
                readme_path=readme,
                category_re=module.EN_CATEGORY_RE,
                total_re=module.EN_TOTAL_RE,
                overview_re=module.EN_OVERVIEW_RE,
                expected_tree=module.actual_skill_tree(repo),
            )

            self.assertTrue(errors)
            self.assertIn("demo-skill", errors[0])

    def test_detects_stale_english_overview_count(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            skill_dir = repo / "skills" / "developer-engineering" / "demo-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: demo-skill\n---\n", encoding="utf-8")
            readme = repo / "README.en.md"
            readme.write_text(
                textwrap.dedent(
                    """\
                    [![Skills](https://img.shields.io/badge/Skills-1-7c3aed)](./skills/)
                    This repository currently contains **1 categories / 1 skills**.
                    ## Skill Overview (by category, 1 categories / 293 skills)

                    <a id="cat-developer-engineering"></a>
                    ### 1. Developer Engineering (developer-engineering, 1)
                    - [`demo-skill`](./skills/developer-engineering/demo-skill/)
                    """
                ),
                encoding="utf-8",
            )

            errors = module.validate_readme(
                readme_path=readme,
                category_re=module.EN_CATEGORY_RE,
                total_re=module.EN_TOTAL_RE,
                overview_re=module.EN_OVERVIEW_RE,
                expected_tree=module.actual_skill_tree(repo),
            )

            self.assertIn("README.en.md: overview skill count 293 != 1", errors)

    def test_detects_stale_banner_count(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            banner = Path(tmpdir) / "repo-banner.svg"
            banner.write_text(
                "<svg><text>293 skills · 16 categories · upstream sync</text>"
                "<text>\n      293\n    </text></svg>",
                encoding="utf-8",
            )

            errors = module.validate_banner(
                banner_path=banner,
                expected_category_count=16,
                expected_skill_count=296,
            )

            self.assertIn("repo-banner.svg: banner skill count 293 != 296", errors)


if __name__ == "__main__":
    unittest.main()
