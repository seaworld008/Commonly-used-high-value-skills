import importlib.util
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TAGS_LINE = re.compile(r"^tags:\s*(.*)$", re.MULTILINE)


def load_enrich_module():
    path = REPO_ROOT / "scripts" / "enrich_frontmatter.py"
    spec = importlib.util.spec_from_file_location("enrich_frontmatter", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillPackageHygieneTests(unittest.TestCase):
    def test_skill_packages_do_not_ship_hook_session_logs(self):
        offenders = [
            str(path.relative_to(REPO_ROOT))
            for root in ("skills", "openclaw-skills")
            for path in (REPO_ROOT / root).rglob("scripts/logs/*")
        ]
        self.assertEqual([], offenders)

    def test_canonical_tags_are_yaml_lists(self):
        offenders = []
        for skill in sorted((REPO_ROOT / "skills").glob("*/*/SKILL.md")):
            frontmatter = skill.read_text(encoding="utf-8").split("\n---", 1)[0]
            match = TAGS_LINE.search(frontmatter)
            if match is None or not match.group(1).startswith("["):
                offenders.append(str(skill.relative_to(REPO_ROOT)))
        self.assertEqual([], offenders)

    def test_unwrap_quoted_tags(self):
        unwrap = load_enrich_module().unwrap_quoted_tags
        self.assertEqual('["a", "b"]', unwrap("'[\"a\", \"b\"]'"))
        self.assertEqual("[a, b]", unwrap('"[a, b]"'))
        self.assertEqual('["a"]', unwrap('["a"]'))
        self.assertEqual("'[it''s]'", unwrap("'[it''s]'"))


if __name__ == "__main__":
    unittest.main()
