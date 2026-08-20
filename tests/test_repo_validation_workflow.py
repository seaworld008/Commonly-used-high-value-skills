import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "repo-validation.yml"
PROVENANCE_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "skills-provenance-ci.yml"


def run_commands(job):
    return [
        step["run"].strip()
        for step in job["steps"]
        if isinstance(step, dict) and "run" in step
    ]


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

        job_commands = run_commands(job)
        commands = "\n".join(job_commands)
        self.assertIn("python -m pip install pyyaml pytest", job_commands)
        self.assertIn("python scripts/audit_skill_portfolio.py --check-policy", commands)
        self.assertIn("python scripts/audit_licenses.py", commands)
        self.assertIn("python scripts/validate_skill_sources.py", commands)
        self.assertIn(
            "python scripts/check_source_coverage.py --min-percent 100",
            commands,
        )
        self.assertIn("python scripts/generate_repo_health_report.py", commands)
        self.assertIn("python scripts/evaluate_repo_health.py", commands)
        self.assertIn("python scripts/refresh_repo_views.py", commands)
        self.assertIn("python scripts/check_readme_sync.py", commands)
        self.assertIn("node --check bin/install-skills.js", commands)
        self.assertIn("npm pack --dry-run --silent", commands)
        self.assertIn("python -m pytest -q tests", job_commands)
        self.assertNotIn("python -m unittest", commands)
        self.assertIn("GITHUB_STEP_SUMMARY", commands)
        self.assertIn("git diff --exit-code", commands)

        upload_steps = [
            step for step in job["steps"] if isinstance(step, dict) and step.get("uses") == "actions/upload-artifact@v4"
        ]
        self.assertTrue(upload_steps, "repo-validation should upload a repo health artifact")

    def test_provenance_workflow_runs_v2_and_full_pytest_suites(self):
        self.assertTrue(PROVENANCE_WORKFLOW_PATH.exists(), "provenance workflow should exist")

        data = yaml.safe_load(PROVENANCE_WORKFLOW_PATH.read_text(encoding="utf-8"))
        self.assertEqual("skills-provenance-ci", data["name"])
        job = data["jobs"]["provenance-checks"]
        self.assertEqual("ubuntu-latest", job["runs-on"])

        job_commands = run_commands(job)
        commands = "\n".join(job_commands)
        self.assertIn("python -m pip install pyyaml pytest", job_commands)
        self.assertIn(
            "python -m pytest -q tests/test_provenance_v2.py",
            job_commands,
        )
        self.assertIn("python -m pytest -q tests", job_commands)
        self.assertNotIn("python3 -m unittest", commands)
        self.assertIn(
            "python3 scripts/provenance_pipeline.py --mode all --config "
            "docs/sources/provenance.config.json",
            job_commands,
        )
        self.assertIn(
            "git diff --exit-code -- docs/sources",
            job_commands,
        )


if __name__ == "__main__":
    unittest.main()
