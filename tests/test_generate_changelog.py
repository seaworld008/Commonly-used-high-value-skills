import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "generate_changelog.py"
spec = importlib.util.spec_from_file_location("generate_changelog", SCRIPT)
changelog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(changelog)

HISTORY = """# Changelog / 更新日志

人工维护的双语说明。

## [Unreleased]

### Removed / 移除

- 保留人工维护的退役记录。

## [2.0.0] - 2026-08-20

完整发布说明，不可覆盖。

## [2026-03-27]

早期历史。

[2.0.0]: https://example.com/compare/v1...v2
"""


class PreserveHistoryTests(unittest.TestCase):
    def test_only_inserts_managed_block_in_unreleased(self):
        result = changelog.update_unreleased(HISTORY, "自动更新内容")
        start = result.index(changelog.AUTO_START)
        end = result.index(changelog.AUTO_END) + len(changelog.AUTO_END) + 2
        self.assertEqual(result[:start] + result[end:], HISTORY)
        self.assertLess(start, result.index("## [2.0.0]"))

    def test_replaces_only_managed_block_and_is_idempotent(self):
        first = changelog.update_unreleased(HISTORY, "旧自动内容")
        second = changelog.update_unreleased(first, "新自动内容")
        self.assertNotIn("旧自动内容", second)
        self.assertEqual(changelog.update_unreleased(second, "新自动内容"), second)
        self.assertIn("完整发布说明，不可覆盖。", second)

    def test_rejects_ambiguous_or_out_of_section_markers(self):
        invalid = [
            HISTORY.replace("## [Unreleased]", "## [Unknown]"),
            HISTORY + "\n## [Unreleased]\n",
            HISTORY + changelog.AUTO_START,
            HISTORY + changelog.AUTO_END,
            HISTORY + changelog.AUTO_START + changelog.AUTO_END,
            HISTORY.replace(
                "### Removed / 移除", changelog.AUTO_END + changelog.AUTO_START
            ),
            HISTORY.replace(
                "### Removed / 移除",
                changelog.AUTO_START + changelog.AUTO_END + changelog.AUTO_START + changelog.AUTO_END,
            ),
        ]
        for text in invalid:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    changelog.update_unreleased(text, "new")


class GenerateChangelogTests(unittest.TestCase):
    def git(self, root: Path, *args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()

    def test_last_tag_uses_exclusive_tag_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.git(root, "init", "-q")
            self.git(root, "config", "user.name", "Test")
            self.git(root, "config", "user.email", "test@example.com")
            (root / "before.txt").write_text("before\n", encoding="utf-8")
            self.git(root, "add", ".")
            self.git(root, "commit", "-qm", "feat: before tag")
            self.git(root, "tag", "v1.0.0")
            (root / "after.txt").write_text("after\n", encoding="utf-8")
            self.git(root, "add", ".")
            self.git(root, "commit", "-qm", "fix: after tag")

            result = subprocess.run(
                [
                    "python",
                    str(SCRIPT),
                    "--since",
                    "last-tag",
                    "--dry-run",
                ],
                cwd=root,
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertIn("Revision range: `v1.0.0..HEAD`", result.stdout)
            self.assertIn("after tag", result.stdout)
            self.assertNotIn("before tag", result.stdout)

    def test_explicit_ref_is_converted_to_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.git(root, "init", "-q")
            self.git(root, "config", "user.name", "Test")
            self.git(root, "config", "user.email", "test@example.com")
            (root / "a").write_text("a", encoding="utf-8")
            self.git(root, "add", ".")
            self.git(root, "commit", "-qm", "chore: base")
            base = self.git(root, "rev-parse", "HEAD")
            (root / "b").write_text("b", encoding="utf-8")
            self.git(root, "add", ".")
            self.git(root, "commit", "-qm", "feat: current")

            result = subprocess.run(
                ["python", str(SCRIPT), "--since", base, "--dry-run"],
                cwd=root,
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertIn(f"Revision range: `{base}..HEAD`", result.stdout)
            self.assertIn("current", result.stdout)

    def test_preserve_mode_keeps_history_and_ignores_changelog_only_commits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.git(root, "init", "-q")
            self.git(root, "config", "user.name", "Test")
            self.git(root, "config", "user.email", "test@example.com")
            output = root / "CHANGELOG.md"
            output.write_text(HISTORY, encoding="utf-8")
            self.git(root, "add", ".")
            self.git(root, "commit", "-qm", "chore: base")
            self.git(root, "tag", "v2.0.0")
            (root / "code.txt").write_text("code", encoding="utf-8")
            self.git(root, "add", ".")
            self.git(root, "commit", "-qm", "fix: preserve | history")
            command = [
                sys.executable, str(SCRIPT), "--since", "last-tag", "--preserve-history"
            ]
            subprocess.run(command, cwd=root, check=True, capture_output=True, text=True)
            first = output.read_text(encoding="utf-8")
            self.assertIn("保留人工维护的退役记录。", first)
            self.assertIn("完整发布说明，不可覆盖。", first)
            self.assertIn("preserve | history", first)
            self.assertIn("#### [", first)
            self.assertIn("##### Fixed", first)
            self.git(root, "add", "CHANGELOG.md")
            self.git(root, "commit", "-qm", "chore: refresh CHANGELOG.md")
            subprocess.run(command, cwd=root, check=True, capture_output=True, text=True)
            self.assertEqual(first, output.read_text(encoding="utf-8"))

    def test_preserve_mode_refuses_missing_history_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--preserve-history"],
                cwd=tmp, capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((Path(tmp) / "CHANGELOG.md").exists())

    def test_git_failure_does_not_report_success_or_write_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "CHANGELOG.md"
            output.write_text(HISTORY, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--since", "1 month ago", "--preserve-history"],
                cwd=root, capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Git command failed", result.stderr)
            self.assertEqual(HISTORY, output.read_text(encoding="utf-8"))

    def test_empty_range_replaces_stale_managed_entries_but_keeps_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.git(root, "init", "-q")
            self.git(root, "config", "user.name", "Test")
            self.git(root, "config", "user.email", "test@example.com")
            output = root / "CHANGELOG.md"
            output.write_text(changelog.update_unreleased(HISTORY, "stale automatic entry"), encoding="utf-8")
            self.git(root, "add", ".")
            self.git(root, "commit", "-qm", "chore: base")
            self.git(root, "tag", "v2.0.0")
            subprocess.run(
                [sys.executable, str(SCRIPT), "--preserve-history"],
                cwd=root, check=True, capture_output=True, text=True,
            )
            result = output.read_text(encoding="utf-8")
            self.assertNotIn("stale automatic entry", result)
            self.assertIn("No categorized changes", result)
            self.assertIn("完整发布说明，不可覆盖。", result)

    def test_workflow_uses_history_mode_and_quotes_input_via_env(self):
        workflow = (REPO_ROOT / ".github/workflows/changelog.yml").read_text(encoding="utf-8")
        self.assertIn("--preserve-history", workflow)
        self.assertIn('default: "last-tag"', workflow)
        self.assertIn('--since "$CHANGELOG_SINCE"', workflow)
        for line in workflow.splitlines():
            if line.lstrip().startswith("run:"):
                self.assertNotIn("${{", line)


if __name__ == "__main__":
    unittest.main()
