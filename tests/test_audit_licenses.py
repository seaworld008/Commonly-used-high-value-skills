import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "audit_licenses.py"


class AuditLicensesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("audit_licenses", SCRIPT_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.module = module

    def test_summary_matches_current_audit_shape(self):
        rows = self.module.audit()
        payload = self.module.summarize(rows)
        self.assertEqual(len(rows), payload["total"])
        self.assertEqual(payload["missing"], sum(1 for row in rows if row["status"] == "MISSING"))
        self.assertEqual(payload["unknown"], sum(1 for row in rows if row["status"] == "UNKNOWN"))
        self.assertEqual(payload["ok"], sum(1 for row in rows if row["status"] == "OK"))

    def test_report_writers_emit_expected_files(self):
        rows = self.module.audit()
        payload = self.module.summarize(rows)
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            rel_dir = Path(tmp).relative_to(REPO_ROOT)
            json_path = rel_dir / "license-audit.json"
            md_path = rel_dir / "license-audit.md"
            self.module.write_json_report(payload, str(json_path))
            self.module.write_markdown_report(payload, str(md_path))

            written_json = json.loads((REPO_ROOT / json_path).read_text(encoding="utf-8"))
            written_md = (REPO_ROOT / md_path).read_text(encoding="utf-8")

            self.assertEqual(payload["total"], written_json["total"])
            self.assertIn("# License Audit Report", written_md)
            self.assertIn("Total skills", written_md)


if __name__ == "__main__":
    unittest.main()
