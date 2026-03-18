import importlib.util
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPO_ROOT
    / "skills"
    / "finance-investing"
    / "portfolio-risk-manager"
    / "scripts"
    / "build_optimizer_inputs.py"
)
ASSET_PATH = (
    REPO_ROOT
    / "skills"
    / "finance-investing"
    / "portfolio-risk-manager"
    / "assets"
    / "sample_returns.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("build_optimizer_inputs", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PortfolioRiskOptimizerInputsTests(unittest.TestCase):
    def test_generate_report_builds_expected_returns_covariance_and_seed_weights(self):
        module = load_module()
        data = json.loads(ASSET_PATH.read_text(encoding="utf-8"))

        report = module.generate_report(data)

        self.assertEqual(["AAPL", "MSFT", "NOVO", "SPGI"], report["assets"])
        self.assertIn("AAPL", report["expected_returns"])
        self.assertIn("MSFT", report["covariance_matrix"]["AAPL"])
        self.assertAlmostEqual(0.25, report["seed_weights"]["equal_weight"]["AAPL"], places=6)
        self.assertAlmostEqual(
            1.0,
            sum(report["seed_weights"]["inverse_volatility"].values()),
            places=5,
        )


if __name__ == "__main__":
    unittest.main()
