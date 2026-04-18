from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "evaluate_repo_health.py"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


class EvaluateRepoHealthTests(unittest.TestCase):
    def test_evaluate_repo_health_passes_on_current_state(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            output = Path(tmp) / "repo-health-eval.md"
            result = run_script("--output-md", str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.exists())
            text = output.read_text(encoding="utf-8")
            self.assertIn("Overall status", text)
            self.assertIn("PASS", text)


if __name__ == "__main__":
    unittest.main()
