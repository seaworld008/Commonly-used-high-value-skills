from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "evaluate_repo_health.py"
GEN_SCRIPT = REPO_ROOT / "scripts" / "generate_repo_health_report.py"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

def run_generate(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GEN_SCRIPT), *args],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


class EvaluateRepoHealthTests(unittest.TestCase):
    def test_evaluate_repo_health_passes_on_current_state(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            tmp_dir = Path(tmp)
            reports_dir = tmp_dir / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)

            report_json = tmp_dir / "repo-health.json"
            report_md = tmp_dir / "repo-health.md"
            gen = run_generate(
                "--output-json",
                str(report_json),
                "--output-md",
                str(report_md),
                "--reports-dir",
                str(reports_dir),
            )
            self.assertEqual(gen.returncode, 0, gen.stderr)
            self.assertTrue(report_json.exists())

            output = tmp_dir / "repo-health-eval.md"
            result = run_script("--report", str(report_json), "--output-md", str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.exists())
            text = output.read_text(encoding="utf-8")
            self.assertIn("Overall status", text)
            self.assertIn("PASS", text)


if __name__ == "__main__":
    unittest.main()
