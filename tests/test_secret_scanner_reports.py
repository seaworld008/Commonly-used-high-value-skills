"""Report boundaries use harmless sentinels, never credential-shaped fixtures."""
import contextlib
import importlib.util
import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills/developer-engineering/repomix-safe-mixer/scripts/scan_secrets.py"
)
SENTINEL = "non-sensitive-regression-marker"


def load_scanner():
    spec = importlib.util.spec_from_file_location("scanner_report_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SecretScannerReportTests(unittest.TestCase):
    def test_text_report_does_not_echo_rule_metadata(self):
        scanner = load_scanner()
        finding = scanner.SecretFinding("src/config.py", 7, SENTINEL)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            scanner.print_report([finding], Path("project"))
        self.assertNotIn(SENTINEL, output.getvalue())
        self.assertIn("src/config.py", output.getvalue())
        self.assertIn("Line 7: potential credential", output.getvalue())
        self.assertIn("Match: [REDACTED]", output.getvalue())

    def test_text_and_json_cli_redact_matches_and_keep_detection_exit_code(self):
        for json_mode in (False, True):
            with self.subTest(json_mode=json_mode), tempfile.TemporaryDirectory() as tmp:
                scanner = load_scanner()
                root = Path(tmp)
                (root / "input.py").write_text(f'value = "{SENTINEL}"\n', encoding="utf-8")
                output, errors = io.StringIO(), io.StringIO()
                argv = [str(SCRIPT), str(root)] + (["--json"] if json_mode else [])
                with (
                    patch.object(scanner, "SECRET_PATTERNS", {"regression_rule": re.escape(SENTINEL)}),
                    patch.object(scanner.sys, "argv", argv),
                    contextlib.redirect_stdout(output),
                    contextlib.redirect_stderr(errors),
                    self.assertRaises(SystemExit) as exit_context,
                ):
                    scanner.main()
                self.assertEqual(1, exit_context.exception.code)
                self.assertNotIn(SENTINEL, output.getvalue() + errors.getvalue())
                self.assertIn("[REDACTED]", output.getvalue())
                if json_mode:
                    self.assertEqual(
                        [{
                            "file": "input.py", "line": 1, "type": "regression_rule",
                            "match": "[REDACTED]", "context": "[REDACTED]",
                        }],
                        json.loads(output.getvalue()),
                    )
                else:
                    self.assertIn("Line 1: potential credential", output.getvalue())
                    self.assertNotIn("regression_rule", output.getvalue())

    def test_clean_cli_keeps_success_exit_code(self):
        for json_mode in (False, True):
            with self.subTest(json_mode=json_mode), tempfile.TemporaryDirectory() as tmp:
                scanner = load_scanner()
                output = io.StringIO()
                argv = [str(SCRIPT), tmp] + (["--json"] if json_mode else [])
                with (
                    patch.object(scanner.sys, "argv", argv),
                    contextlib.redirect_stdout(output),
                    self.assertRaises(SystemExit) as exit_context,
                ):
                    scanner.main()
                self.assertEqual(0, exit_context.exception.code)
                if json_mode:
                    self.assertEqual([], json.loads(output.getvalue()))
                else:
                    self.assertIn("No secrets detected!", output.getvalue())
