import json
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


class ProvenancePipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.script_path = cls.root / "scripts" / "provenance_pipeline.py"

    def load_module(self):
        spec = importlib.util.spec_from_file_location("provenance_pipeline", self.script_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Failed to load module from {self.script_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_config_has_required_keys(self):
        cfg = json.loads((self.root / "docs/sources/provenance.config.json").read_text(encoding="utf-8"))
        self.assertIn("coverage_min_percent", cfg)
        self.assertIn("stale_days", cfg)
        self.assertIn("paths", cfg)
        for key in [
            "in_house_mapping",
            "refresh_queue",
            "catalog",
            "bulk_plan",
            "sources_index",
            "upstream_check",
        ]:
            self.assertIn(key, cfg["paths"])

    def test_quick_pipeline_runs(self):
        result = subprocess.run(
            [
                sys.executable,
                "scripts/provenance_pipeline.py",
                "--mode",
                "quick",
                "--config",
                "docs/sources/provenance.config.json",
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            self.fail(f"quick pipeline failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")

    def test_resolve_python_cmd_uses_current_interpreter(self):
        module = self.load_module()
        cmd = module.resolve_python_cmd()
        self.assertTrue(cmd)
        self.assertEqual(Path(sys.executable).name.lower(), Path(cmd[0]).name.lower())


if __name__ == "__main__":
    unittest.main()
