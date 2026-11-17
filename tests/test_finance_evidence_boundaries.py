"""Offline regression checks for missing evidence and invalid valuation inputs."""

import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


FINANCE = Path(__file__).resolve().parents[1] / "skills" / "finance-investing"
COMPS_PATH = FINANCE / "comps-valuation-analyst" / "scripts" / "calculate_comps.py"
DCF_PATH = FINANCE / "financial-analyst" / "scripts" / "dcf_valuation.py"
COLLECT_PATH = FINANCE / "financial-data-collector" / "scripts" / "collect_data.py"


def load_script(path):
    # collect_data imports its sibling, but does not load optional dependencies.
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


@pytest.fixture
def comps_data():
    return json.loads((COMPS_PATH.parent.parent / "assets/sample_comps_input.json").read_text())


@pytest.fixture
def dcf_data():
    sample = DCF_PATH.parent.parent / "assets/sample_financial_data.json"
    return json.loads(sample.read_text())["dcf_valuation"]


def run_dcf(data):
    model = load_script(DCF_PATH).DCFModel()
    model.set_historical_financials(data["historical"])
    model.set_assumptions(data["assumptions"])
    return model, model.run_full_valuation()


@pytest.mark.parametrize("ebitda", [None, 0, -100])
def test_comps_nonpositive_ebitda_skips_only_that_method(comps_data, ebitda):
    comps_data["subject_company"]["ebitda"] = ebitda
    summary = load_script(COMPS_PATH).generate_report(comps_data)["valuation_summary"]
    prices = summary["implied_price_range"]
    assert prices["ev_ebitda"] is None
    assert "ebitda" in " ".join(summary["unavailable_reasons"]["ev_ebitda"]).lower()
    assert prices["pe_ratio"] == 47.59
    assert prices["ev_sales"] == 36.72
    assert summary["average_implied_price"] == 42.16


@pytest.mark.parametrize("shares", [None, 0, -1])
def test_comps_requires_positive_shares_for_ev_methods(comps_data, shares):
    comps_data["subject_company"]["shares_outstanding"] = shares
    summary = load_script(COMPS_PATH).generate_report(comps_data)["valuation_summary"]
    assert summary["implied_price_range"] == {
        "ev_ebitda": None, "pe_ratio": 47.59, "ev_sales": None,
    }
    for method in ("ev_ebitda", "ev_sales"):
        assert any("shares_outstanding" in reason for reason in summary["unavailable_reasons"][method])
    assert summary["average_implied_price"] == 47.59


@pytest.mark.parametrize("field", ["net_debt", "shares_outstanding"])
def test_comps_omitted_fields_are_not_defaulted(comps_data, field):
    del comps_data["subject_company"][field]
    summary = load_script(COMPS_PATH).generate_report(comps_data)["valuation_summary"]
    assert summary["implied_price_range"]["ev_ebitda"] is None
    assert summary["implied_price_range"]["ev_sales"] is None
    assert summary["unavailable_reasons"]


def test_comps_null_net_debt_keeps_pe_valuation(comps_data):
    comps_data["subject_company"]["net_debt"] = None
    summary = load_script(COMPS_PATH).generate_report(comps_data)["valuation_summary"]
    assert summary["implied_price_range"] == {
        "ev_ebitda": None, "pe_ratio": 47.59, "ev_sales": None,
    }
    assert summary["average_implied_price"] == 47.59


@pytest.mark.parametrize("metric,method", [("eps", "pe_ratio"), ("revenue", "ev_sales")])
@pytest.mark.parametrize("value", [None, 0, -1])
def test_comps_other_nonpositive_metrics_are_unavailable(comps_data, metric, method, value):
    comps_data["subject_company"][metric] = value
    summary = load_script(COMPS_PATH).generate_report(comps_data)["valuation_summary"]
    assert summary["implied_price_range"][method] is None
    assert summary["unavailable_reasons"][method]
    assert summary["implied_price_range"]["ev_ebitda"] == 24.05


@pytest.mark.parametrize("net_debt", [0, -100, 900])
def test_comps_known_zero_debt_and_net_cash_remain_valid(comps_data, net_debt):
    comps_data["subject_company"]["net_debt"] = net_debt
    summary = load_script(COMPS_PATH).generate_report(comps_data)["valuation_summary"]
    # The four valid EV/EBITDA peers have median 11.15.
    assert summary["implied_price_range"]["ev_ebitda"] == round((620 * 11.15 - net_debt) / 250, 2)
    assert not summary["unavailable_reasons"]


@pytest.mark.parametrize("field", ["ev_ebitda", "pe_ratio", "ev_sales"])
def test_comps_no_valid_peer_multiple_is_unavailable(comps_data, field):
    for peer, value in zip(comps_data["peers"], [None, 0, -2, -3]):
        peer[field] = value
    result = load_script(COMPS_PATH).generate_report(comps_data)
    method = "pe_ratio" if field == "pe_ratio" else field
    assert result["valuation_summary"]["implied_price_range"][method] is None
    assert result["valuation_summary"]["unavailable_reasons"][method]


def test_comps_empty_peers_has_no_average(comps_data):
    comps_data["peers"] = []
    summary = load_script(COMPS_PATH).generate_report(comps_data)["valuation_summary"]
    assert all(value is None for value in summary["implied_price_range"].values())
    assert summary["average_implied_price"] is None
    assert len(summary["unavailable_reasons"]) == 3


def test_comps_ignores_invalid_peers_in_an_otherwise_valid_method(comps_data):
    for peer, value in zip(comps_data["peers"], [None, 0, -5, 10]):
        peer["ev_ebitda"] = value
    result = load_script(COMPS_PATH).generate_report(comps_data)
    assert result["peer_statistics"]["median_ev_ebitda"] == 10
    assert result["valuation_summary"]["implied_price_range"]["ev_ebitda"] == 21.2


@pytest.mark.parametrize("growth", [0.08, 0.09])
def test_dcf_invalid_perpetuity_keeps_exit_method(dcf_data, growth):
    dcf_data["assumptions"]["wacc_inputs"] = {
        "risk_free_rate": 0.08, "equity_risk_premium": 0, "equity_weight": 1, "debt_weight": 0,
    }
    dcf_data["assumptions"]["terminal_growth_rate"] = growth
    model, result = run_dcf(dcf_data)
    for field in ("terminal_value", "enterprise_value", "equity_value", "value_per_share"):
        assert result[field]["perpetuity_growth"] is None
        assert result[field]["exit_multiple"] > 0
    assert "WACC" in result["unavailable_reasons"]["perpetuity_growth"]
    assert "WACC" in model.format_text(result)
    assert "N/A" in model.format_text(result)
    # Both the API and JSON output must contain null, never Infinity.
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("shares", [None, 0, -1])
def test_dcf_missing_or_invalid_shares_keeps_enterprise_and_equity(dcf_data, shares):
    dcf_data["historical"]["shares_outstanding"] = shares
    model, result = run_dcf(dcf_data)
    assert all(value is None for value in result["value_per_share"].values())
    assert all(value > 0 for value in result["equity_value"].values())
    assert all(value is None for row in result["sensitivity_analysis"]["share_price_table"] for value in row)
    assert "shares_outstanding" in result["unavailable_reasons"]
    assert "N/A" in model.format_text(result)


@pytest.mark.parametrize("field", ["net_debt", "shares_outstanding"])
@pytest.mark.parametrize("omitted", [True, False])
def test_dcf_missing_equity_inputs_are_not_defaulted(dcf_data, field, omitted):
    if omitted:
        del dcf_data["historical"][field]
    else:
        dcf_data["historical"][field] = None
    model, result = run_dcf(dcf_data)
    assert result["enterprise_value"]["perpetuity_growth"] > 0
    assert all(value is None for value in result["value_per_share"].values())
    if field == "net_debt":
        assert all(value is None for value in result["equity_value"].values())
    sensitivity = result["sensitivity_analysis"]
    assert all(value is None for row in sensitivity["share_price_table"] for value in row)
    assert field in sensitivity["unavailable_reasons"]
    assert field in result["unavailable_reasons"]
    assert "N/A" in model.format_text(result)


@pytest.mark.parametrize("net_debt", [0, -100, 7000000])
def test_dcf_known_zero_debt_and_net_cash_remain_valid(dcf_data, net_debt):
    dcf_data["historical"]["net_debt"] = net_debt
    model, result = run_dcf(dcf_data)
    for method in ("perpetuity_growth", "exit_multiple"):
        assert result["equity_value"][method] == pytest.approx(result["enterprise_value"][method] - net_debt)
        assert result["value_per_share"][method] == pytest.approx(result["equity_value"][method] / 10000000)
    assert not result["unavailable_reasons"]
    assert "N/A" not in model.format_text(result)


def test_dcf_sensitivity_invalid_cell_is_null_with_reason(dcf_data):
    model, _ = run_dcf(dcf_data)
    result = model.sensitivity_analysis(wacc_range=[0.02, 0.08], growth_range=[0.02, 0.03])
    assert result["enterprise_value_table"][0] == [None, None]
    assert result["share_price_table"][0] == [None, None]
    assert result["enterprise_value_table"][1][0] > 0
    assert result["unavailable_reasons"]
    json.dumps(result, allow_nan=False)


def test_dcf_empty_history_is_an_input_error(dcf_data):
    dcf_data["historical"] = {}
    with pytest.raises(ValueError, match="Historical revenue data is required"):
        run_dcf(dcf_data)


def test_dcf_reused_model_clears_old_unavailability(dcf_data):
    dcf_data["assumptions"]["terminal_growth_rate"] = 0.2
    del dcf_data["historical"]["net_debt"]
    model, invalid = run_dcf(dcf_data)
    assert invalid["unavailable_reasons"]
    model.historical["net_debt"] = 0
    model.assumptions["terminal_growth_rate"] = 0.025
    valid = model.run_full_valuation()
    assert not valid["unavailable_reasons"]
    assert valid["value_per_share"]["perpetuity_growth"] > 0
    assert invalid["unavailable_reasons"]  # A prior report is an independent snapshot.


@pytest.mark.parametrize("growth", [None, float("nan"), float("inf")])
def test_dcf_invalid_growth_is_an_explicit_input_error(dcf_data, growth):
    dcf_data["assumptions"]["terminal_growth_rate"] = growth
    with pytest.raises(ValueError, match="terminal_growth_rate"):
        run_dcf(dcf_data)


class FakeFrame:
    """Small DataFrame protocol exercising the real alias lookup offline."""

    def __init__(self, fields, year=2025):
        self.fields = fields
        self.index = list(fields)
        self.columns = [SimpleNamespace(year=year)]
        self.empty = not fields
        self.loc = self

    def __getitem__(self, key):
        field, _ = key
        return self.fields[field]


def balance_sheet(fields, year=2025):
    module = load_script(COLLECT_PATH)
    module.pd = SimpleNamespace(notna=lambda value: value is not None and not math.isnan(value))
    return module.collect_balance_sheet(SimpleNamespace(balance_sheet=FakeFrame(fields)), year)[str(year)]


@pytest.mark.parametrize("fields,missing", [
    ({"Long Term Debt": 100, "Cash And Cash Equivalents": 20, "Short Term Investments": 5}, "short_term_debt"),
    ({"Current Debt": 10, "Cash And Cash Equivalents": 20, "Short Term Investments": 5}, "long_term_debt"),
    ({"Total Debt": 100, "Cash And Cash Equivalents": 20}, "short_investments"),
    ({"Total Debt": 100, "Short Term Investments": 5}, "cash"),
    ({"Total Assets": 100}, "total_debt"),
])
def test_collector_partial_components_do_not_invent_net_debt(fields, missing):
    result = balance_sheet(fields)
    assert result["net_debt"] is None
    assert missing in json.dumps(result["_missing_fields"])
    assert "yfinance" in json.dumps(result["_missing_fields"])


@pytest.mark.parametrize("debt,cash,investments", [(0, 0, 0), (100, 20, 5), (0, 20, 5)])
def test_collector_complete_components_preserve_zero_and_net_cash(debt, cash, investments):
    result = balance_sheet({
        "Long Term Debt": debt, "Current Debt": 0,
        "Cash And Cash Equivalents": cash, "Short Term Investments": investments,
    })
    assert result["total_debt"] == debt
    assert result["cash_and_equivalents"] == cash + investments
    assert result["net_debt"] == debt - cash - investments
    assert not result["_missing_fields"]


@pytest.mark.parametrize("total_debt", [0, 100])
def test_collector_disclosed_totals_take_priority(total_debt):
    result = balance_sheet({
        "Total Debt": total_debt, "Long Term Debt": 999, "Current Debt": 999,
        "Cash Cash Equivalents And Short Term Investments": 25,
        "Cash And Cash Equivalents": 900, "Short Term Investments": 900,
    })
    assert result["total_debt"] == total_debt
    assert result["cash_and_equivalents"] == 25
    assert result["net_debt"] == total_debt - 25
    assert not result["_missing_fields"]


def test_collector_disclosed_zero_totals_need_no_components():
    result = balance_sheet({
        "Total Debt": 0, "Cash Cash Equivalents And Short Term Investments": 0,
    })
    assert result["total_debt"] == result["cash_and_equivalents"] == result["net_debt"] == 0
    assert not result["_missing_fields"]


@pytest.mark.parametrize("fails", [False, True])
def test_collector_missing_balance_sheet_or_fetch_error_has_reason(fails):
    class FakeTicker:
        @property
        def balance_sheet(self):
            if fails:
                raise RuntimeError("offline fixture failure")
            return None

    result = load_script(COLLECT_PATH).collect_balance_sheet(FakeTicker(), 2025)["2025"]
    for field in ("total_debt", "cash_and_equivalents", "net_debt"):
        assert result[field] is None
        assert "yfinance" in result["_missing_fields"][field]


@pytest.mark.parametrize("fields,year", [({}, 2025), ({"Total Debt": float("nan")}, 2025), ({"Total Debt": 100}, 2024)])
def test_collector_empty_nan_or_missing_year_returns_null_and_reason(fields, year):
    result = balance_sheet(fields, year)
    for key in ("total_debt", "cash_and_equivalents", "net_debt"):
        assert result[key] is None
        assert result["_missing_fields"][key]


@pytest.mark.parametrize("invalid", [False, True])
def test_existing_sample_clis_support_text_json_and_null(tmp_path, dcf_data, comps_data, invalid):
    if invalid:
        dcf_data["assumptions"]["terminal_growth_rate"] = 0.2
        del dcf_data["historical"]["shares_outstanding"]
        comps_data["subject_company"]["ebitda"] = -100
        del comps_data["subject_company"]["net_debt"]
    dcf_input = tmp_path / "dcf.json"
    dcf_input.write_text(json.dumps(dcf_data))
    comps_input = tmp_path / "comps.json"
    comps_input.write_text(json.dumps(comps_data))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    commands = [
        [sys.executable, str(DCF_PATH), str(dcf_input)],
        [sys.executable, str(DCF_PATH), str(dcf_input), "--format", "json"],
        [sys.executable, str(COMPS_PATH), str(comps_input)],
    ]
    outputs = [subprocess.run(command, capture_output=True, text=True, env=env, check=True).stdout for command in commands]
    assert "DCF VALUATION ANALYSIS" in outputs[0]
    dcf_result, comps_result = map(json.loads, outputs[1:])
    if invalid:
        assert "N/A" in outputs[0]
        assert dcf_result["value_per_share"]["perpetuity_growth"] is None
        assert comps_result["valuation_summary"]["implied_price_range"]["ev_ebitda"] is None
    else:
        assert dcf_result["wacc"] == pytest.approx(0.086575)
        assert dcf_result["value_per_share"]["perpetuity_growth"] == pytest.approx(13.897515874028999)
        assert comps_result["valuation_summary"]["implied_price_range"] == {
            "ev_ebitda": 24.05, "pe_ratio": 47.59, "ev_sales": 36.72,
        }


@pytest.mark.parametrize("growth", [None, 0.025])
def test_dcf_cli_input_error_has_no_normal_report(tmp_path, dcf_data, growth):
    if growth is None:
        dcf_data["assumptions"]["terminal_growth_rate"] = None
        expected = "terminal_growth_rate"
    else:
        dcf_data["historical"] = {}
        expected = "Historical revenue data is required"
    input_path = tmp_path / "invalid-dcf.json"
    input_path.write_text(json.dumps(dcf_data))
    result = subprocess.run(
        [sys.executable, str(DCF_PATH), str(input_path), "--format", "json"],
        capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "Error:" in result.stderr and expected in result.stderr
