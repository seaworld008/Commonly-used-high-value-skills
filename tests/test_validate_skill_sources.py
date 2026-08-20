import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = REPO_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def retired_mapping(repo_skill=None):
    return {
        "video": {"url": "https://example.com", "checked_at": "2026-07-27"},
        "official_references": [],
        "skills": [
            {
                "video_name": "Legacy helper",
                "normalized_slug": "legacy-helper",
                "status": "retired",
                "repo_skill": repo_skill,
                "source": "https://example.com/legacy-helper",
                "notes": "Consolidated into current-helper.",
            }
        ],
    }


class ValidateSkillSourcesTests(unittest.TestCase):
    def test_retired_mapping_is_valid_without_live_repo_path(self):
        generic = load_script("validate_skill_sources")
        video = load_script("validate_openclaw_video_sources")

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping = root / "retired.skills.json"
            mapping.write_text(json.dumps(retired_mapping()), encoding="utf-8")

            self.assertEqual(
                [],
                generic.validate_mapping(mapping, root, allow_v1=True),
            )
            self.assertEqual([], video.validate(mapping, root))

    def test_retired_mapping_rejects_live_repo_path(self):
        generic = load_script("validate_skill_sources")
        video = load_script("validate_openclaw_video_sources")

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping = root / "retired.skills.json"
            mapping.write_text(
                json.dumps(retired_mapping("skills/category/legacy-helper/SKILL.md")),
                encoding="utf-8",
            )

            generic_errors = generic.validate_mapping(
                mapping,
                root,
                allow_v1=True,
            )
            video_errors = video.validate(mapping, root)
            self.assertTrue(any("must set repo_skill to null" in item for item in generic_errors))
            self.assertTrue(any("must set repo_skill to null" in item for item in video_errors))


if __name__ == "__main__":
    unittest.main()
