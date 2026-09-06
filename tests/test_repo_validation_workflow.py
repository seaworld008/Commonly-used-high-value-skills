import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "repo-validation.yml"
PROVENANCE_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "skills-provenance-ci.yml"
CODEQL_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "codeql.yml"


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
        self.assertIn(
            "python -m pip install pyyaml pytest jsonschema",
            job_commands,
        )
        self.assertIn("python scripts/audit_skill_portfolio.py --check-policy", commands)
        self.assertIn("python scripts/audit_skill_instructions.py", commands)
        self.assertIn("python scripts/lint_skill_quality.py --min-lines 50 --strict", commands)
        self.assertIn("python scripts/audit_licenses.py", commands)
        self.assertIn("python scripts/validate_skill_sources.py", commands)
        self.assertIn(
            "python scripts/reconcile_artifact_inventory.py "
            "--offline --check-clean --quiet",
            commands,
        )
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
            step for step in job["steps"] if isinstance(step, dict) and step.get("uses") == "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
        ]
        self.assertTrue(upload_steps, "repo-validation should upload a repo health artifact")

    def test_provenance_workflow_runs_only_focused_tests_and_pipeline(self):
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
        self.assertNotIn("python -m pytest -q tests", job_commands)
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

    def test_repo_validation_is_the_only_workflow_running_full_pytest(self):
        full_suite_command = "python -m pytest -q tests"
        owners = []

        for workflow_path in sorted((REPO_ROOT / ".github" / "workflows").glob("*.y*ml")):
            data = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
            for job in (data.get("jobs") or {}).values():
                if full_suite_command in run_commands(job):
                    owners.append(workflow_path.name)

        self.assertEqual(["repo-validation.yml"], owners)

    def test_codeql_workflow_has_parallel_extended_security_gate(self):
        self.assertTrue(CODEQL_WORKFLOW_PATH.exists(), "CodeQL workflow should exist")

        data = yaml.safe_load(CODEQL_WORKFLOW_PATH.read_text(encoding="utf-8"))
        self.assertEqual("CodeQL", data["name"])

        trigger_block = data.get("on", data.get(True))
        self.assertEqual(["main"], trigger_block["push"]["branches"])
        self.assertEqual(["main"], trigger_block["pull_request"]["branches"])
        self.assertEqual(
            {"contents": "read", "security-events": "write"},
            data["permissions"],
        )

        job = data["jobs"]["analyze"]
        self.assertEqual("ubuntu-latest", job["runs-on"])
        self.assertFalse(job["strategy"]["fail-fast"])
        self.assertEqual(
            {"actions", "javascript-typescript", "python"},
            set(job["strategy"]["matrix"]["language"]),
        )

        uses_steps = {
            step["uses"]: step
            for step in job["steps"]
            if isinstance(step, dict) and "uses" in step
        }
        self.assertIn("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", uses_steps)
        self.assertIn("github/codeql-action/init@cdf488f595d80d6e07e03d4674febd5ab45fa938", uses_steps)
        self.assertIn("github/codeql-action/analyze@cdf488f595d80d6e07e03d4674febd5ab45fa938", uses_steps)

        init_inputs = uses_steps["github/codeql-action/init@cdf488f595d80d6e07e03d4674febd5ab45fa938"]["with"]
        self.assertEqual("${{ matrix.language }}", init_inputs["languages"])
        self.assertEqual("none", init_inputs["build-mode"])
        self.assertEqual("security-extended", init_inputs["queries"])
        self.assertIn('paths-ignore:\n  - "openclaw-skills/**"', init_inputs["config"])

        analyze_inputs = uses_steps["github/codeql-action/analyze@cdf488f595d80d6e07e03d4674febd5ab45fa938"]["with"]
        self.assertEqual(
            "/language:${{ matrix.language }}",
            analyze_inputs["category"],
        )


if __name__ == "__main__":
    unittest.main()
