import importlib.util
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FINANCE_ROOT = REPO_ROOT / "skills" / "finance-investing"
OFFICE_ROOT = REPO_ROOT / "skills" / "office-white-collar"

EXPECTED_FINANCE_SKILLS = {
    "financial-analyst",
    "financial-data-collector",
    "comps-valuation-analyst",
    "earnings-call-analyzer",
    "sec-filing-reviewer",
    "portfolio-risk-manager",
    "factor-backtester",
    "stock-screener-builder",
    "macro-regime-monitor",
    "options-strategy-evaluator",
    "event-driven-tracker",
    "investment-memo-writer",
    "saas-metrics-coach",
}

SCRIPT_CASES = [
    {
        "skill": "comps-valuation-analyst",
        "script": "scripts/calculate_comps.py",
        "asset": "assets/sample_comps_input.json",
        "expected_keys": {"valuation_summary", "company_results", "peer_statistics"},
    },
    {
        "skill": "earnings-call-analyzer",
        "script": "scripts/analyze_earnings_call.py",
        "asset": "assets/sample_earnings_call.json",
        "expected_keys": {"summary", "signal_counts", "management_tone"},
    },
    {
        "skill": "sec-filing-reviewer",
        "script": "scripts/review_filing.py",
        "asset": "assets/sample_filing_sections.json",
        "expected_keys": {"sections_reviewed", "risk_flags", "follow_up_questions"},
    },
    {
        "skill": "portfolio-risk-manager",
        "script": "scripts/portfolio_risk.py",
        "asset": "assets/sample_portfolio.json",
        "expected_keys": {"portfolio_summary", "risk_metrics", "exposure_breakdown"},
    },
    {
        "skill": "factor-backtester",
        "script": "scripts/backtest_factor.py",
        "asset": "assets/sample_factor_data.json",
        "expected_keys": {"performance_summary", "portfolio_path", "turnover"},
    },
    {
        "skill": "stock-screener-builder",
        "script": "scripts/screen_stocks.py",
        "asset": "assets/sample_universe.json",
        "expected_keys": {"matches", "match_count", "active_filters"},
    },
    {
        "skill": "macro-regime-monitor",
        "script": "scripts/classify_regime.py",
        "asset": "assets/sample_macro_data.json",
        "expected_keys": {"current_regime", "regime_scorecard", "watch_items"},
    },
    {
        "skill": "options-strategy-evaluator",
        "script": "scripts/evaluate_strategy.py",
        "asset": "assets/sample_options_strategy.json",
        "expected_keys": {"strategy_summary", "payoff_checkpoints", "risk_notes"},
    },
    {
        "skill": "event-driven-tracker",
        "script": "scripts/track_events.py",
        "asset": "assets/sample_events.json",
        "expected_keys": {"upcoming_events", "event_summary", "priority_items"},
    },
    {
        "skill": "investment-memo-writer",
        "script": "scripts/build_memo.py",
        "asset": "assets/sample_thesis.json",
        "expected_keys": {"memo_markdown", "recommendation", "key_monitoring_items"},
    },
]


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FinanceInvestingSkillsTests(unittest.TestCase):
    def test_finance_category_contains_expected_skills(self):
        self.assertTrue(FINANCE_ROOT.exists(), "finance-investing category should exist")
        discovered = {
            item.name for item in FINANCE_ROOT.iterdir() if item.is_dir() and (item / "SKILL.md").exists()
        }
        self.assertEqual(EXPECTED_FINANCE_SKILLS, discovered)

    def test_old_category_no_longer_contains_migrated_finance_skills(self):
        self.assertFalse((OFFICE_ROOT / "financial-analyst").exists())
        self.assertFalse((OFFICE_ROOT / "financial-data-collector").exists())

    def test_new_finance_scripts_generate_expected_output_shape(self):
        for case in SCRIPT_CASES:
            with self.subTest(skill=case["skill"]):
                skill_root = FINANCE_ROOT / case["skill"]
                self.assertTrue((skill_root / "SKILL.md").exists())
                self.assertTrue((skill_root / "references").exists())
                self.assertTrue((skill_root / "assets").exists())
                self.assertTrue((skill_root / "scripts").exists())

                module = load_module(skill_root / case["script"])
                data = json.loads((skill_root / case["asset"]).read_text(encoding="utf-8"))
                result = module.generate_report(data)

                self.assertIsInstance(result, dict)
                self.assertTrue(case["expected_keys"].issubset(result.keys()))
                if case["skill"] == "portfolio-risk-manager":
                    self.assertIn("top_5_concentration", result["portfolio_summary"])
                    self.assertIn("max_sector_weight", result["risk_metrics"])
                if case["skill"] == "factor-backtester":
                    self.assertIn("max_drawdown", result["performance_summary"])
                    self.assertIn("net_factor_return", result["portfolio_path"][0])
                if case["skill"] == "options-strategy-evaluator":
                    self.assertIn("best_checkpoint_pnl", result["strategy_summary"])
                    self.assertIn("worst_checkpoint_pnl", result["strategy_summary"])


if __name__ == "__main__":
    unittest.main()
