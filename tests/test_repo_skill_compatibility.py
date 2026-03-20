import re
import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def find_skill_files(root: Path):
    return sorted(
        path
        for path in root.rglob("SKILL.md")
        if ".git" not in path.parts and "__pycache__" not in path.parts
    )


def validate_skill_file(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", text, re.DOTALL)
    if not match:
        return "missing YAML frontmatter"
    try:
        data = yaml.safe_load(match.group(1))
    except Exception as exc:
        return f"invalid YAML: {exc}"
    if not isinstance(data, dict):
        return "frontmatter is not a mapping"
    for key in ("name", "description"):
        if key not in data:
            return f"missing key: {key}"
    return None


class RepoSkillCompatibilityTests(unittest.TestCase):
    def test_source_skills_tree_is_codex_compatible(self):
        errors = []
        for path in find_skill_files(REPO_ROOT / "skills"):
            issue = validate_skill_file(path)
            if issue:
                errors.append(f"{path}: {issue}")
        self.assertEqual([], errors)

    def test_openclaw_export_tree_is_codex_compatible(self):
        errors = []
        for path in find_skill_files(REPO_ROOT / "openclaw-skills"):
            issue = validate_skill_file(path)
            if issue:
                errors.append(f"{path}: {issue}")
        self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
