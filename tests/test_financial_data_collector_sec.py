import importlib.util
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPO_ROOT
    / "skills"
    / "finance-investing"
    / "financial-data-collector"
    / "scripts"
    / "sec_api.py"
)
ASSET_ROOT = (
    REPO_ROOT
    / "skills"
    / "finance-investing"
    / "financial-data-collector"
    / "assets"
)


def load_module():
    spec = importlib.util.spec_from_file_location("sec_api", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FinancialDataCollectorSecTests(unittest.TestCase):
    def test_resolve_ticker_to_cik_and_parse_sec_payloads(self):
        module = load_module()
        tickers = json.loads((ASSET_ROOT / "sample_sec_company_tickers.json").read_text(encoding="utf-8"))
        submissions = json.loads((ASSET_ROOT / "sample_sec_submissions.json").read_text(encoding="utf-8"))
        companyfacts = json.loads((ASSET_ROOT / "sample_sec_companyfacts.json").read_text(encoding="utf-8"))

        report = module.build_report_from_sec("AAPL", tickers, submissions, companyfacts)

        self.assertEqual("0000320193", report["resolved_cik"])
        self.assertEqual("0000320193", report["submissions"]["cik"])
        self.assertEqual("2024-11-01", report["submissions"]["latest_10k"]["filing_date"])
        self.assertEqual("2025-08-01", report["submissions"]["latest_10q"]["filing_date"])
        self.assertEqual("Apple Inc.", report["companyfacts"]["company_name"])
        latest = report["companyfacts"]["latest_facts"]
        self.assertEqual(391035.0, latest["revenue_millions"])
        self.assertEqual(15_117.0, latest["shares_outstanding_millions"])
        self.assertEqual(1.05, latest["current_ratio"])

    def test_companyfacts_parser_handles_missing_concepts(self):
        module = load_module()
        payload = {"entityName": "Demo Co", "facts": {"us-gaap": {}}}
        parsed = module.parse_companyfacts(payload)
        self.assertEqual("Demo Co", parsed["company_name"])
        self.assertIsNone(parsed["latest_facts"]["revenue_millions"])
        self.assertEqual("sec companyfacts", parsed["_source"])


if __name__ == "__main__":
    unittest.main()
