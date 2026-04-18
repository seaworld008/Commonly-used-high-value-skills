from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "generate_repo_health_report.py"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


class GenerateRepoHealthReportTests(unittest.TestCase):
    def test_repo_health_report_generation(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            tmp_dir = Path(tmp)
            json_output = tmp_dir / "repo-health.json"
            md_output = tmp_dir / "repo-health.md"

            result = run_script("--output-json", str(json_output), "--output-md", str(md_output))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json_output.exists())
            self.assertTrue(md_output.exists())

            payload = json.loads(json_output.read_text(encoding="utf-8"))
            markdown = md_output.read_text(encoding="utf-8")

            self.assertIn("skills_total", payload)
            self.assertIn("license_audit", payload)
            self.assertIn("dead_links", payload)
            self.assertIn("refresh_queue", payload)
            self.assertIn("# Repo Health Report", markdown)
            self.assertIn("## License Audit", markdown)


if __name__ == "__main__":
    unittest.main()
