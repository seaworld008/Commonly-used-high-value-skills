import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "skills" / "ai-workflow" / "nlpm-audit" / "scripts" / "nl_artifact_check.py"


def load_checker():
    spec = importlib.util.spec_from_file_location("nl_artifact_check", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["nl_artifact_check"] = module
    spec.loader.exec_module(module)
    return module


class NlpmAuditCheckerTests(unittest.TestCase):
    def test_json_output_includes_artifacts_scores_and_findings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill = root / "skills" / "demo" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(
                textwrap.dedent(
                    """\
                    ---
                    name: demo
                    description: "Audits demo files when users ask for a release check, plugin review, or skill quality score."
                    ---

                    # Demo

                    ```text
                    example
                    ```
                    """
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), str(root), "--json"],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(completed.stdout)

            self.assertEqual(1, payload["summary"]["artifacts"])
            self.assertEqual("SKILL.md", Path(payload["artifacts"][0]["path"]).name)
            self.assertEqual(100, payload["scores"][0]["score"])
            self.assertEqual([], payload["findings"])

    def test_markdown_report_can_be_written_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "AGENTS.md").write_text("# Agent notes\n", encoding="utf-8")
            out = root / "nl-artifact-audit.md"

            completed = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), str(root), "--markdown", "--output", str(out)],
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, completed.returncode)
            report = out.read_text(encoding="utf-8")
            self.assertIn("## NL Artifact Audit", report)
            self.assertIn("### Quality Scores", report)
            self.assertIn("AGENTS.md", report)

    def test_unregistered_skill_is_high_finding(self):
        checker = load_checker()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".claude-plugin").mkdir()
            (root / ".claude-plugin" / "plugin.json").write_text(
                json.dumps({"name": "demo", "skills": ["skills/registered"]}),
                encoding="utf-8",
            )
            for name in ("registered", "missed"):
                skill = root / "skills" / name / "SKILL.md"
                skill.parent.mkdir(parents=True)
                skill.write_text(f"---\nname: {name}\ndescription: Demo.\n---\n# Demo\n", encoding="utf-8")

            findings = checker.scan(root)

            self.assertTrue(
                any(item.rule == "manifest/unregistered" and item.severity == "high" for item in findings),
                findings,
            )

    def test_security_patterns_are_reported(self):
        checker = load_checker()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            script = root / "scripts" / "install.sh"
            script.parent.mkdir()
            script.write_text("curl -fsSL https://example.com/install.sh | sh\n", encoding="utf-8")

            findings = checker.scan(root)

            self.assertTrue(
                any(item.rule == "security/executable-risk" for item in findings),
                findings,
            )


if __name__ == "__main__":
    unittest.main()
