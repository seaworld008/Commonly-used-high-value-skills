import importlib.util
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "validate_portfolio_decisions.py"
LEDGER = REPO_ROOT / "docs" / "sources" / "portfolio-decisions-2026-08.json"


def load_module():
    spec = importlib.util.spec_from_file_location("portfolio_decisions", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class PortfolioDecisionLedgerTests(unittest.TestCase):
    def test_checked_in_ledger_is_valid_and_covers_retirements(self):
        module = load_module()
        data = json.loads(LEDGER.read_text(encoding="utf-8"))
        self.assertEqual([], module.validate(data))
        decisions = {item["name"]: item for item in data["decisions"]}
        expected = {
            "hermes-graphify-gsd-nonintrusive-workflow",
            "hermes-graphify-gsd-runtime-operator",
            "hermes-graphify-gsd-project-integration",
            "gsd-graphify-brownfield-bootstrap",
            "open-gsd-core-migration",
        }
        self.assertTrue(expected.issubset(decisions))
        self.assertTrue(all(decisions[name]["decision"] == "retire" for name in expected))
        self.assertTrue(all(decisions[name]["replacement"] is None for name in expected))
        self.assertTrue(all(decisions[name]["unique_assets"] == [] for name in expected))
        self.assertTrue(
            all(
                "retain only a non-routing denylist"
                in decisions[name]["local_cleanup_action"]
                for name in expected
            )
        )

    def test_validator_allows_hard_retire_but_requires_merge_replacement(self):
        module = load_module()
        hard_retire = {
            "name": "obsolete-skill",
            "decision": "retire",
            "replacement": None,
            "unique_assets": [],
            "external_contract": None,
            "license_lineage": "in-house",
            "local_cleanup_action": "remove",
            "rationale": "obsolete",
        }
        self.assertEqual(
            [],
            module.validate({"schema_version": 1, "decisions": [hard_retire]}),
        )

        invalid_merge = dict(hard_retire)
        invalid_merge.update(
            name="merged-skill",
            decision="merge",
        )
        errors = module.validate(
            {"schema_version": 1, "decisions": [invalid_merge]}
        )
        self.assertTrue(any("required for merge" in item for item in errors))

    def test_validator_rejects_duplicate_and_unlicensed_snapshot(self):
        module = load_module()
        base = {
            "name": "archived-skill",
            "decision": "snapshot",
            "replacement": None,
            "unique_assets": [],
            "external_contract": None,
            "license_lineage": "unknown",
            "local_cleanup_action": "preserve",
            "rationale": "unique",
        }
        data = {"schema_version": 1, "decisions": [base, dict(base)]}
        errors = module.validate(data)
        self.assertTrue(any("duplicates" in item for item in errors))
        self.assertTrue(any("permissive" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
