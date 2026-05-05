import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ingest_skill.py"


def load_module():
    spec = importlib.util.spec_from_file_location("ingest_skill", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IngestSkillTests(unittest.TestCase):
    def write_skill(self, root: Path, frontmatter: str) -> Path:
        skill_dir = root / "skills" / "developer-engineering" / "sample-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(frontmatter + "\n# Sample\n", encoding="utf-8")
        return skill_dir

    def test_external_ingest_rejects_missing_license(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = self.write_skill(
                Path(tmpdir),
                "---\nname: sample-skill\ndescription: Sample\n---",
            )
            with mock.patch.object(module, "fetch_github_repo_license", return_value=None):
                ok = module.ingest_one(
                    skill_dir,
                    source="github:owner/repo",
                    source_url="https://github.com/owner/repo",
                    dry_run=True,
                )

            self.assertFalse(ok)

    def test_external_ingest_adds_detected_permissive_license(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = self.write_skill(
                Path(tmpdir),
                "---\nname: sample-skill\ndescription: Sample\n---",
            )
            with mock.patch.object(module, "fetch_github_repo_license", return_value="MIT"):
                ok = module.ingest_one(
                    skill_dir,
                    source="github:owner/repo",
                    source_url="https://github.com/owner/repo",
                    dry_run=False,
                )

            content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(ok)
            self.assertIn("license: MIT", content)
            self.assertIn('source: "github:owner/repo"', content)

    def test_in_house_ingest_does_not_require_license(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = self.write_skill(
                Path(tmpdir),
                "---\nname: sample-skill\ndescription: Sample\n---",
            )
            ok = module.ingest_one(
                skill_dir,
                source="in-house",
                source_url="",
                dry_run=True,
            )

            self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
