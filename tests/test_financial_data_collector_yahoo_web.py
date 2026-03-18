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
    / "yahoo_web_api.py"
)
ASSET_ROOT = (
    REPO_ROOT
    / "skills"
    / "finance-investing"
    / "financial-data-collector"
    / "assets"
)


def load_module():
    spec = importlib.util.spec_from_file_location("yahoo_web_api", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FinancialDataCollectorYahooWebTests(unittest.TestCase):
    def test_parse_quote_summary_payload(self):
        module = load_module()
        payload = json.loads((ASSET_ROOT / "sample_yahoo_quote_summary.json").read_text(encoding="utf-8"))
        report = module.parse_quote_summary("AAPL", payload, [2023, 2024])

        self.assertEqual("Apple Inc.", report["company_name"])
        self.assertEqual(225.17, report["market_data"]["current_price"])
        self.assertEqual(15117.0, report["market_data"]["shares_outstanding_millions"])
        self.assertEqual(2024, max(int(year) for year in report["income_statement"]))
        self.assertEqual(391035.0, report["income_statement"]["2024"]["revenue"])
        self.assertEqual(-9447.0, report["cash_flow"]["2024"]["capex"])
        self.assertEqual(7662.0, report["balance_sheet"]["2024"]["current_assets"])
        self.assertEqual(8.1, report["analyst_estimates"]["revenue_growth_next_year_pct"])

    def test_parse_treasury_chart_payload(self):
        module = load_module()
        payload = json.loads((ASSET_ROOT / "sample_yahoo_tnx_chart.json").read_text(encoding="utf-8"))
        self.assertEqual(0.0431, module.parse_treasury_chart(payload))


if __name__ == "__main__":
    unittest.main()
