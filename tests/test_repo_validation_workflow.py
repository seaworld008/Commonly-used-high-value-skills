import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "repo-validation.yml"


class RepoValidationWorkflowTests(unittest.TestCase):
    def test_repo_validation_workflow_exists_and_has_expected_steps(self):
        self.assertTrue(WORKFLOW_PATH.exists(), "repo-validation workflow should exist")

        data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
        self.assertEqual("Repository Validation", data["name"])
        trigger_block = data.get("on", data.get(True))
        self.assertIsNotNone(trigger_block)
        self.assertIn("push", trigger_block)
        self.assertIn("pull_request", trigger_block)

        job = data["jobs"]["validate"]
        self.assertEqual("ubuntu-latest", job["runs-on"])

        commands = "\n".join(
            step.get("run", "")
            for step in job["steps"]
            if isinstance(step, dict) and "run" in step
        )
        self.assertIn("python scripts/audit_licenses.py", commands)
        self.assertIn("python scripts/generate_repo_health_report.py", commands)
        self.assertIn("python scripts/evaluate_repo_health.py", commands)
        self.assertIn("python scripts/refresh_repo_views.py", commands)
        self.assertIn("GITHUB_STEP_SUMMARY", commands)
        self.assertIn("python -m unittest", commands)
        self.assertIn("git diff --exit-code", commands)

        upload_steps = [
            step for step in job["steps"] if isinstance(step, dict) and step.get("uses") == "actions/upload-artifact@v4"
        ]
        self.assertTrue(upload_steps, "repo-validation should upload a repo health artifact")


if __name__ == "__main__":
    unittest.main()
