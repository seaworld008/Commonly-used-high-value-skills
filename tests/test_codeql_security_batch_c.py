import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROLLBACK_GENERATOR = (
    REPO_ROOT
    / "skills/developer-engineering/migration-architect/scripts/rollback_generator.py"
)
TRANSCRIPT_FIXER = (
    REPO_ROOT
    / "skills/office-white-collar/transcript-fixer/scripts/fix_transcript_enhanced.py"
)
SECRET_SCANNER = (
    REPO_ROOT
    / "skills/developer-engineering/repomix-safe-mixer/scripts/scan_secrets.py"
)
SAFE_PACK = (
    REPO_ROOT
    / "skills/developer-engineering/repomix-safe-mixer/scripts/safe_pack.py"
)
DEPENDENCY_SCANNER = (
    REPO_ROOT
    / "skills/developer-engineering/dependency-auditor/scripts/dep_scanner.py"
)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class CodeQLSecurityBatchCTests(unittest.TestCase):
    def test_rollback_output_is_redacted_and_private_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            migration = root / "migration.json"
            migration.write_text(
                json.dumps(
                    {
                        "migration_id": "security-regression",
                        "migration_type": "database",
                        "phases": [],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "runbook.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROLLBACK_GENERATOR),
                    "--input",
                    str(migration),
                    "--output",
                    str(output),
                    "--format",
                    "json",
                ],
                check=True,
                text=True,
                capture_output=True,
            )

            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("[REDACTED]", data["data_recovery_plan"]["backup_location"])
            for contact in data["emergency_contacts"]:
                self.assertEqual("[REDACTED]", contact["primary_phone"])
                self.assertEqual("[REDACTED]", contact["email"])
                self.assertEqual("[REDACTED]", contact["backup_contact"])
            self.assertEqual(0o600, stat.S_IMODE(output.stat().st_mode))
            self.assertNotIn("incident.commander@company.com", result.stdout)

            console = subprocess.run(
                [
                    sys.executable,
                    str(ROLLBACK_GENERATOR),
                    "--input",
                    str(migration),
                    "--format",
                    "both",
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertIn("[REDACTED]", console.stdout)
            self.assertNotIn("incident.commander@company.com", console.stdout)
            self.assertNotIn("/backups/pre_migration_", console.stdout)

            requested_json = root / "text-only.json"
            text_only = subprocess.run(
                [
                    sys.executable,
                    str(ROLLBACK_GENERATOR),
                    "--input",
                    str(migration),
                    "--output",
                    str(requested_json),
                    "--format",
                    "text",
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            derived_text = root / "text-only.txt"
            self.assertFalse(requested_json.exists())
            self.assertTrue(derived_text.is_file())
            self.assertEqual(0o600, stat.S_IMODE(derived_text.stat().st_mode))
            self.assertIn("[REDACTED]", derived_text.read_text(encoding="utf-8"))
            self.assertIn(str(derived_text), text_only.stdout)
            self.assertNotIn("incident.commander@company.com", text_only.stdout)

    def test_rollback_sensitive_output_requires_file_and_never_reaches_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            migration = root / "migration.json"
            migration.write_text(
                json.dumps(
                    {
                        "migration_id": "security-regression",
                        "migration_type": "database",
                        "phases": [],
                    }
                ),
                encoding="utf-8",
            )

            rejected = subprocess.run(
                [
                    sys.executable,
                    str(ROLLBACK_GENERATOR),
                    "--input",
                    str(migration),
                    "--format",
                    "json",
                    "--include-sensitive",
                ],
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(0, rejected.returncode)
            self.assertIn("--include-sensitive requires --output", rejected.stderr)
            self.assertNotIn("incident.commander@company.com", rejected.stdout)

            output = root / "sensitive.json"
            accepted = subprocess.run(
                [
                    sys.executable,
                    str(ROLLBACK_GENERATOR),
                    "--input",
                    str(migration),
                    "--output",
                    str(output),
                    "--format",
                    "json",
                    "--include-sensitive",
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                "incident.commander@company.com",
                data["emergency_contacts"][0]["email"],
            )
            self.assertEqual(0o600, stat.S_IMODE(output.stat().st_mode))
            self.assertNotIn("incident.commander@company.com", accepted.stdout)

    def test_transcript_key_discovery_never_reads_shell_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            secret = "super-secret-api-key-1234567890"
            (home / ".zshrc").write_text(
                "\n".join(
                    [
                        "export ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic",
                        f"export ANTHROPIC_AUTH_TOKEN={secret}",
                    ]
                ),
                encoding="utf-8",
            )
            script_dir = TRANSCRIPT_FIXER.parent
            program = (
                "import sys;"
                f"sys.path.insert(0, {str(script_dir)!r});"
                "import fix_transcript_enhanced as module;"
                "assert not module.find_glm_api_key()"
            )
            result = subprocess.run(
                [sys.executable, "-c", program],
                env={
                    **os.environ,
                    "HOME": str(home),
                    "GLM_API_KEY": "",
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
                check=True,
                text=True,
                capture_output=True,
            )

            combined = result.stdout + result.stderr
            self.assertNotIn(str(home / ".zshrc"), combined)
            self.assertNotIn(secret, combined)
            self.assertNotIn(secret[:4], combined)
            self.assertNotIn(secret[-4:], combined)

    def test_secret_scanner_json_and_reports_never_emit_secret_material(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secret = "AKIA1234567890ABCDEF"
            (root / "credentials.py").write_text(
                f'API_KEY = "{secret}"\n', encoding="utf-8"
            )

            scan = subprocess.run(
                [sys.executable, str(SECRET_SCANNER), str(root), "--json"],
                text=True,
                capture_output=True,
            )
            self.assertEqual(1, scan.returncode)
            self.assertNotIn(secret, scan.stdout + scan.stderr)
            findings = json.loads(scan.stdout)
            self.assertEqual(
                {"file", "line", "type", "match", "context"},
                set(findings[0]),
            )
            self.assertEqual("[REDACTED]", findings[0]["match"])
            self.assertEqual("[REDACTED]", findings[0]["context"])

            pack = subprocess.run(
                [sys.executable, str(SAFE_PACK), str(root)],
                text=True,
                capture_output=True,
            )
            self.assertEqual(1, pack.returncode)
            self.assertNotIn(secret, pack.stdout + pack.stderr)
            self.assertIn("credentials.py:1", pack.stdout)

    def test_yarn_lock_parser_uses_deterministic_line_records(self):
        module = load_module("dependency_scanner_security_test", DEPENDENCY_SCANNER)
        with tempfile.TemporaryDirectory() as tmp:
            lockfile = Path(tmp) / "yarn.lock"
            lockfile.write_text(
                "\n".join(
                    [
                        "# yarn lockfile v1",
                        "",
                        "left-pad@^1.3.0:",
                        '  version "1.3.0"',
                        '  resolved "https://registry.example/left-pad.tgz"',
                        "",
                        '"@scope/pkg@^2.0.0", "@scope/pkg@~2.1.0":',
                        '  version "2.2.0"',
                        "",
                        "malformed:",
                        "\t" * 10000,
                    ]
                ),
                encoding="utf-8",
            )

            dependencies = module.DependencyScanner()._parse_yarn_lock(lockfile)
            self.assertEqual(
                [("left-pad", "1.3.0"), ("@scope/pkg", "2.2.0")],
                [(item.name, item.version) for item in dependencies],
            )


if __name__ == "__main__":
    unittest.main()
