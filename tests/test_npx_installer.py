import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "bin" / "install-skills.js"
PACKAGE_JSON = REPO_ROOT / "package.json"


class NpxInstallerTests(unittest.TestCase):
    def test_package_exposes_installer_bin_and_skill_files(self):
        data = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))

        self.assertEqual("common-high-value-skills", data["name"])
        self.assertEqual("bin/install-skills.js", data["bin"]["high-value-skills"])
        self.assertIn("skills/", data["files"])
        self.assertNotIn("openclaw-skills/", data["files"])

    def test_installer_help_and_target_listing_work(self):
        help_result = subprocess.run(
            ["node", str(INSTALLER), "--help"],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertIn("high-value-skills install", help_result.stdout)

        targets_result = subprocess.run(
            ["node", str(INSTALLER), "list-targets"],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertIn("agents-project", targets_result.stdout)
        self.assertIn("codex", targets_result.stdout)
        self.assertIn("openclaw", targets_result.stdout)

    def test_installer_flattens_categorized_skills_to_custom_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source" / "developer-engineering" / "sample-skill"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text(
                "---\nname: sample-skill\ndescription: test skill\n---\n\n# Sample\n",
                encoding="utf-8",
            )
            (source / "references").mkdir()
            (source / "references" / "note.md").write_text("reference\n", encoding="utf-8")
            dest = root / "installed"

            result = subprocess.run(
                [
                    "node",
                    str(INSTALLER),
                    "install",
                    "--target",
                    "custom",
                    "--source-root",
                    str(root / "source"),
                    "--dir",
                    str(dest),
                ],
                cwd=REPO_ROOT,
                check=True,
                text=True,
                capture_output=True,
            )

            self.assertIn("Installed 1 skills", result.stdout)
            self.assertTrue((dest / "sample-skill" / "SKILL.md").exists())
            self.assertTrue((dest / "sample-skill" / "references" / "note.md").exists())


if __name__ == "__main__":
    unittest.main()
