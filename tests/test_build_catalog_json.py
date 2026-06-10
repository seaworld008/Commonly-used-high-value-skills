import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_catalog_json.py"


def load_module():
    scripts_dir = str(SCRIPT_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("build_catalog_json", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BuildCatalogJsonTests(unittest.TestCase):
    def test_resolve_generated_at_preserves_existing_value(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "catalog.json"
            output_path.write_text(
                json.dumps({"generated_at": "2026-06-08"}),
                encoding="utf-8",
            )

            self.assertEqual(
                "2026-06-08",
                module.resolve_generated_at(output_path),
            )


if __name__ == "__main__":
    unittest.main()
