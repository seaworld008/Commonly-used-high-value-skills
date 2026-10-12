import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class VerifiedReleaseWorkflowTests(unittest.TestCase):
    def test_release_requires_exact_sha_security_gates_and_draft_verification(self):
        workflow = (ROOT / ".github/workflows/publish-release.yml").read_text(encoding="utf-8")
        self.assertIn("paths:\n      - package.json", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("actions: read", workflow)
        self.assertIn("security-events: read", workflow)
        self.assertIn("Require zero open Code Scanning alerts", workflow)
        self.assertIn("code-scanning/alerts", workflow)
        self.assertIn("refs/heads/main", workflow)
        self.assertLess(workflow.index("Require zero open Code Scanning alerts"), workflow.index("Build archives and checksum manifest"))
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        for name in ("Repository Validation", "skills-provenance-ci", "CodeQL"):
            self.assertIn(name, workflow)
        self.assertIn("python scripts/validate_repository.py --refresh", workflow)
        self.assertIn("git diff --exit-code", workflow)
        self.assertIn("gh release create", workflow)
        self.assertIn("--draft", workflow)
        self.assertIn("gh release download", workflow)
        self.assertIn("sha256sum --check SHA256SUMS", workflow)
        self.assertIn("gh release edit", workflow)
        self.assertLess(workflow.index("gh release download"), workflow.index("gh release edit"))
        self.assertIn("persist-credentials: false", workflow)


if __name__ == "__main__":
    unittest.main()
