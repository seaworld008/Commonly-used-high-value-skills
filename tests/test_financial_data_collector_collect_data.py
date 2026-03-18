import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = (
    REPO_ROOT / "skills" / "finance-investing" / "financial-data-collector" / "scripts"
)
SCRIPT_PATH = SCRIPT_DIR / "collect_data.py"


def load_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location("collect_data", SCRIPT_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if sys.path and sys.path[0] == str(SCRIPT_DIR):
            sys.path.pop(0)


class FinancialDataCollectorCollectDataTests(unittest.TestCase):
    def test_auto_engine_defaults_to_yahoo_web(self):
        module = load_module()
        self.assertEqual("yfinance", module.resolve_engine("auto", yfinance_available=True))
        with self.assertRaises(RuntimeError):
            module.resolve_engine("auto", yfinance_available=False)

    def test_yfinance_engine_requires_optional_dependency(self):
        module = load_module()
        with self.assertRaises(RuntimeError):
            module.resolve_engine("yfinance", yfinance_available=False)

    def test_infer_available_years_prefers_actual_financial_statement_years(self):
        module = load_module()

        class FakeColumn:
            def __init__(self, year):
                self.year = year

        class FakeFinancials:
            empty = False
            columns = [FakeColumn(2023), FakeColumn(2024), FakeColumn(2025), FakeColumn(2026)]

        class FakeTicker:
            financials = FakeFinancials()

        years = module.infer_available_years_from_yfinance(
            FakeTicker(), years_requested=2, fallback_latest_full_year=2025
        )
        self.assertEqual([2025, 2026], years)


if __name__ == "__main__":
    unittest.main()
