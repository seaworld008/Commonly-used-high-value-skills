import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "dead-links.yml"


class DeadLinksWorkflowTests(unittest.TestCase):
    def test_dead_links_workflow_has_summary_and_artifact(self):
        self.assertTrue(WORKFLOW_PATH.exists(), "dead-links workflow should exist")

        data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
        self.assertEqual("Dead Link Check", data["name"])

        job = data["jobs"]["check"]
        self.assertEqual("ubuntu-latest", job["runs-on"])

        commands = "\n".join(
            step.get("run", "")
            for step in job["steps"]
            if isinstance(step, dict) and "run" in step
        )
        self.assertIn("python scripts/check_dead_links.py", commands)
        self.assertIn("GITHUB_STEP_SUMMARY", commands)

        upload_steps = [
            step for step in job["steps"] if isinstance(step, dict) and step.get("uses") == "actions/upload-artifact@v4"
        ]
        self.assertTrue(upload_steps, "dead-links workflow should upload an artifact")


if __name__ == "__main__":
    unittest.main()
