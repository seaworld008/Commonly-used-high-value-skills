"""Exercise the offline source scan CLI against isolated filesystem fixtures."""

import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest


SCANNER = (Path(__file__).resolve().parents[1] / "skills/security-and-reliability"
           / "security-pen-testing/scripts/vulnerability_scanner.py")
CLEAN_TEXT = "No vulnerability patterns detected"
MARKER = "PRIVATE_FIXTURE_BODY"

# Inject a filesystem error in the child only. os.walk, the scanner and both
# output formatters run normally, including when the test runner is privileged.
DENY_ACCESS = """
import errno, os, runpy, sys
event, name = sys.argv[1:3]
sys.argv = sys.argv[3:]
def deny(operation, args):
    if operation == event and isinstance(args[0], str) and os.path.basename(args[0]) == name:
        raise PermissionError(errno.EACCES, 'PRIVATE_FIXTURE_BODY', args[0])
sys.addaudithook(deny)
runpy.run_path(sys.argv[0], run_name='__main__')
"""


class SourceScanCompletionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        self.root = self.work / "source"
        self.root.mkdir()

    def cli(self, path, *options, code, deny=None):
        command = [sys.executable, "-B"]
        if deny:
            command.extend(["-c", DENY_ACCESS, *deny])
        result = subprocess.run(
            [*command, str(SCANNER), "--source", str(path), *options],
            capture_output=True, text=True, cwd=self.work, timeout=10,
        )
        self.assertEqual(code, result.returncode, result.stderr)
        self.assertEqual("", result.stderr)
        return result.stdout

    def incomplete(self, root, failed, reason, deny=None):
        raw = self.cli(root, "--json", code=2, deny=deny)
        text = self.cli(root, code=2, deny=deny)
        report = json.loads(raw)
        self.assertEqual("incomplete", report["source_scan"]["status"])
        self.assertIn({"path": str(failed), "reason": reason}, report["source_scan"]["errors"])
        self.assertIn("Source scan incomplete", text)
        self.assertIn(str(failed), text)
        self.assertNotIn(CLEAN_TEXT, text)
        self.assertNotIn(MARKER, text + raw)
        return report

    def test_invalid_roots(self):
        regular = self.root / "regular.py"
        regular.write_text(MARKER, encoding="utf-8")
        for path, error in [(self.root / "missing", "FileNotFoundError"),
                            (regular, "NotADirectoryError")]:
            with self.subTest(path=path):
                report = self.incomplete(path, path, error)
                self.assertEqual([], report["source_findings"])
                self.assertEqual(0, report["source_scan"]["files_scanned"])

    def test_walk_failure_in_subdirectory(self):
        blocked = self.root / "blocked"
        blocked.mkdir()
        (blocked / "hidden.py").write_text(f"eval({MARKER})", encoding="utf-8")
        (self.root / "clean.py").write_text("value = 0", encoding="utf-8")
        report = self.incomplete(self.root, blocked, "PermissionError", ("os.scandir", blocked.name))
        self.assertEqual([], report["source_findings"])
        self.assertEqual(1, report["source_scan"]["files_scanned"])

    def test_partial_read_failure_retains_finding_without_source(self):
        blocked = self.root / "blocked.py"
        blocked.write_text(MARKER, encoding="utf-8")
        (self.root / "matched.py").write_text(f"eval({MARKER})", encoding="utf-8")
        report = self.incomplete(self.root, blocked, "PermissionError", ("open", blocked.name))
        self.assertEqual(1, report["source_scan"]["files_scanned"])
        self.assertEqual(["CMDI-002"], [f["rule_id"] for f in report["source_findings"]])
        self.assertEqual("", report["source_findings"][0]["code_snippet"])

    def test_read_error_after_open(self):
        invalid = self.root / "unreadable.py"
        invalid.write_bytes(MARKER.encode() + b"\xff")
        report = self.incomplete(self.root, invalid, "UnicodeDecodeError")
        self.assertEqual(0, report["source_scan"]["files_scanned"])

    def test_completed_clean_and_matched_directories(self):
        nested = self.root / "nested"
        nested.mkdir()
        path = nested / "sample.py"
        for body, code in [("value = 0", 0), ("eval(value)", 1)]:
            with self.subTest(code=code):
                path.write_text(body, encoding="utf-8")
                report = json.loads(self.cli(self.root, "--json", code=code))
                self.assertEqual({"status": "completed", "files_scanned": 1, "errors": [],
                                  "excluded": []}, report["source_scan"])
                text = self.cli(self.root, code=code)
                if code == 0:
                    self.assertIn(CLEAN_TEXT, text)
                    self.assertEqual([], report["source_findings"])
                else:
                    finding, = report["source_findings"]
                    self.assertIn("[CMDI-002]", text)
                    self.assertEqual("A05:2025 - Injection", finding["owasp_category"])
                    self.assertEqual(body, finding["code_snippet"])

    def test_linked_root_is_rejected(self):
        link = self.work / "linked-root"
        link.symlink_to(self.root, target_is_directory=True)
        self.incomplete(link, link, "NotADirectoryError")

    def test_scan_source_callers_get_arrays_only_on_completion(self):
        scanner = runpy.run_path(str(SCANNER))["VulnerabilityScanner"]()
        self.assertEqual([], scanner.scan_source(str(self.root)))
        (self.root / "matched.py").write_text(f"eval({MARKER})", encoding="utf-8")
        findings = scanner.scan_source(str(self.root))
        self.assertIsInstance(findings, list)
        self.assertEqual(["CMDI-002"], [f.rule_id for f in findings])
        (self.root / "invalid.py").write_bytes(b"\xff")
        with self.assertRaises(OSError) as failure:
            scanner.scan_source(str(self.root))
        self.assertIn("invalid.py", str(failure.exception))
        self.assertNotIn(MARKER, str(failure.exception))

    def test_links_and_special_files_are_excluded(self):
        outside = self.work / "outside"
        outside.mkdir()
        target = outside / "sample.py"
        target.write_text(f"eval({MARKER})", encoding="utf-8")
        (self.root / "linked.py").symlink_to(target)
        (self.root / "linked-dir").symlink_to(outside, target_is_directory=True)
        (self.root / "vendor").mkdir()
        (self.root / "vendor" / "ignored.py").write_text(f"eval({MARKER})", encoding="utf-8")
        (self.root / "notes.txt").write_text(MARKER, encoding="utf-8")
        expected = {"linked.py": "symbolic link", "linked-dir": "symbolic link",
                    "vendor": "excluded directory", "notes.txt": "unsupported extension"}
        if hasattr(os, "mkfifo"):
            os.mkfifo(self.root / "pipe.py")
            expected["pipe.py"] = "not a regular file"
        report = json.loads(self.cli(self.root, "--json", code=0))
        scan = report["source_scan"]
        self.assertEqual("completed", scan["status"])
        self.assertEqual(0, scan["files_scanned"])
        self.assertEqual([], report["source_findings"])
        self.assertEqual(expected, {Path(e["path"]).name: e["reason"] for e in scan["excluded"]})
        text = self.cli(self.root, code=0)
        for name in expected:
            self.assertIn(str(self.root / name), text)
        self.assertIn("No eligible source files", text)
        self.assertNotIn(MARKER, text)


if __name__ == "__main__":
    unittest.main()
