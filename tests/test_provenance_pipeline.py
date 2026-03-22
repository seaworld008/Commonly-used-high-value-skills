import json
import subprocess
import unittest
from pathlib import Path


class ProvenancePipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

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
                "python3",
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


if __name__ == "__main__":
    unittest.main()
