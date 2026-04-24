import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_repo_banner.py"


def load_module():
    spec = importlib.util.spec_from_file_location("generate_repo_banner", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GenerateRepoBannerTests(unittest.TestCase):
    def test_banner_uses_catalog_counts_and_featured_categories(self):
        module = load_module()
        catalog = {
            "total_skills": 123,
            "total_categories": 9,
            "categories": [
                {"name": "developer-engineering", "count": 31},
                {"name": "ai-workflow", "count": 29},
                {"name": "engineering-workflow-automation", "count": 12},
            ],
        }

        svg = module.render_banner(catalog)

        self.assertIn("123 skills · 9 categories · upstream sync", svg)
        self.assertIn("Developer Engineering", svg)
        self.assertIn("31 skills", svg)
        self.assertIn("AI Workflow", svg)
        self.assertIn("29 skills", svg)
        self.assertIn("Workflow Automation", svg)
        self.assertIn("12 skills", svg)
        self.assertIn("Auto-synced", svg)
        self.assertIn("From catalog", svg)
        self.assertNotIn("source-driven updates", svg)
        ET.fromstring(svg)

    def test_generate_banner_from_catalog_writes_valid_svg(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            catalog_path = tmp / "catalog.json"
            output_path = tmp / "repo-banner.svg"
            catalog_path.write_text(
                json.dumps(
                    {
                        "total_skills": 1,
                        "total_categories": 1,
                        "categories": [{"name": "ai-workflow", "count": 1}],
                    }
                ),
                encoding="utf-8",
            )

            module.generate_banner_from_catalog(catalog_path, output_path)

            content = output_path.read_text(encoding="utf-8")
            self.assertIn("1 skills · 1 categories · upstream sync", content)
            self.assertIn("1 skill", content)
            ET.parse(output_path)


if __name__ == "__main__":
    unittest.main()
