import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "upstream-sync.yml"


class UpstreamSyncWorkflowTests(unittest.TestCase):
    def test_workflow_reconciles_one_canonical_issue(self):
        data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
        job = data["jobs"]["discover-and-sync"]
        steps = job["steps"]

        reconcile = next(
            step
            for step in steps
            if isinstance(step, dict) and step.get("name") == "Reconcile weekly sync issue"
        )
        self.assertEqual("actions/github-script@v7", reconcile["uses"])
        self.assertEqual(
            "steps.discovery.outcome == 'success' && steps.upstream.outcome == 'success'",
            reconcile["if"],
        )

        script = reconcile["with"]["script"]
        self.assertIn("github.rest.issues.create", script)
        self.assertIn("github.rest.issues.update", script)
        self.assertIn("state_reason: 'completed'", script)
        self.assertIn("latest weekly scan found no meaningful", script)
        self.assertNotIn(
            "peter-evans/create-issue-from-file",
            WORKFLOW_PATH.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
