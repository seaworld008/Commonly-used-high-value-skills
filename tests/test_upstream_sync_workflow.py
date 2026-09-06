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

        discovery = next(
            step
            for step in steps
            if isinstance(step, dict)
            and step.get("name") == "Discover new skills from external sources"
        )
        self.assertEqual(
            "${{ secrets.GITHUB_TOKEN }}",
            discovery["env"]["GITHUB_TOKEN"],
        )

        reconcile = next(
            step
            for step in steps
            if isinstance(step, dict) and step.get("name") == "Reconcile weekly sync issue"
        )
        self.assertEqual("actions/github-script@3a2844b7e9c422d3c10d287c895573f7108da1b3", reconcile["uses"])
        self.assertEqual(
            "always()",
            reconcile["if"],
        )
        self.assertEqual(
            "${{ steps.report.outputs.needs_attention }}",
            reconcile["env"]["NEEDS_ATTENTION"],
        )
        self.assertEqual(
            "${{ steps.report.outputs.sync_state }}",
            reconcile["env"]["SYNC_STATE"],
        )
        self.assertEqual(
            "${{ steps.report.outcome }}",
            reconcile["env"]["REPORT_OUTCOME"],
        )

        script = reconcile["with"]["script"]
        self.assertIn("github.rest.issues.create", script)
        self.assertIn("github.rest.issues.update", script)
        self.assertIn("state_reason: 'completed'", script)
        self.assertIn("latest weekly scan completed with state", script)
        self.assertIn("issue.title === title", script)
        self.assertNotIn("issue.title.startsWith(title)", script)
        self.assertIn("if (syncState !== 'complete')", script)
        self.assertIn(
            "process.env.REPORT_OUTCOME === 'success'",
            script,
        )
        self.assertIn("const reportExists = fs.existsSync", script)
        self.assertIn("const report = reportExists", script)
        self.assertNotIn(
            "reportSucceeded && fs.existsSync(process.env.REPORT_PATH)",
            script,
        )
        self.assertIn(": 'failed'", script)
        degraded_branch, complete_branches = script.split(
            "} else if (needsAttention) {", 1
        )
        self.assertNotIn("state: 'closed'", degraded_branch)
        self.assertIn("state: 'closed'", complete_branches)
        self.assertNotIn(
            "peter-evans/create-issue-from-file",
            WORKFLOW_PATH.read_text(encoding="utf-8"),
        )

        enforce = next(
            step
            for step in steps
            if isinstance(step, dict)
            and step.get("name") == "Enforce sync automation state"
        )
        self.assertEqual("always()", enforce["if"])
        self.assertEqual(
            "${{ steps.report.outcome }}",
            enforce["env"]["REPORT_OUTCOME"],
        )
        self.assertIn('REPORT_OUTCOME" != "success', enforce["run"])
        self.assertIn("degraded)", enforce["run"])
        self.assertIn("exit 1", enforce["run"])


if __name__ == "__main__":
    unittest.main()
