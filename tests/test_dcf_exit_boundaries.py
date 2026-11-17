"""Exercise the DCF exit method and its shared projections through both entry points."""

import json
from pathlib import Path
import runpy
import subprocess
import sys

import pytest


SKILL = Path(__file__).resolve().parents[1] / "skills/finance-investing/financial-analyst"
SCRIPT = SKILL / "scripts/dcf_valuation.py"
VALUES = ("terminal_value", "enterprise_value", "equity_value", "value_per_share")


@pytest.fixture
def data():
    return json.loads((SKILL / "assets/sample_financial_data.json").read_text())["dcf_valuation"]


@pytest.fixture
def model(data):
    model = runpy.run_path(str(SCRIPT))["DCFModel"]()
    model.set_historical_financials(data["historical"])
    model.set_assumptions(data["assumptions"])
    return model


def run_cli(data, tmp_path):
    path = tmp_path / "dcf.json"
    path.write_text(json.dumps(data))
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path), "--format", "json"], capture_output=True, text=True
    )


def reject_nonstandard_number(token):
    pytest.fail(f"Nonstandard JSON number in CLI output: {token}")


@pytest.mark.parametrize("field", ["exit_ev_ebitda_multiple", "terminal_ebitda_margin"])
@pytest.mark.parametrize("value", [-12, 0, True, None, "12", float("nan"), float("inf"), -float("inf"), 10**400])
def test_invalid_exit_input_is_isolated_and_recoverable(model, field, value):
    initial = model.run_full_valuation()
    original = model.assumptions[field]
    model.assumptions[field] = value
    result = model.run_full_valuation()
    for name in VALUES:
        assert result[name] == {"exit_multiple": None, "perpetuity_growth": initial[name]["perpetuity_growth"]}
    assert result["sensitivity_analysis"] == initial["sensitivity_analysis"]
    assert field in result["unavailable_reasons"]["exit_multiple"]
    json.dumps(result, allow_nan=False)
    model.assumptions[field] = original
    assert model.run_full_valuation() == initial


@pytest.mark.parametrize("multiple", [12, -12, float("nan"), float("inf"), -float("inf")])
def test_cli_emits_strict_json_for_valid_and_invalid_exit(data, tmp_path, multiple):
    data["assumptions"]["exit_ev_ebitda_multiple"] = multiple
    proc = run_cli(data, tmp_path)
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout, parse_constant=reject_nonstandard_number)
    assert result["value_per_share"]["perpetuity_growth"] == pytest.approx(13.897515874028999)
    if multiple == 12:
        assert result["value_per_share"]["exit_multiple"] == pytest.approx(14.234526342695439)
        assert result["unavailable_reasons"] == {}
    else:
        assert all(result[name]["exit_multiple"] is None for name in VALUES)
        assert "exit_ev_ebitda_multiple" in result["unavailable_reasons"]["exit_multiple"]


@pytest.mark.parametrize("field,value,message", [
    ("revenue", [-1], "revenue"),
    ("revenue", [True], "revenue"),
    ("revenue", [float("inf")], "revenue"),
    ("projection_years", True, "projection_years"),
    ("projection_years", 0, "projection_years"),
    ("projection_years", 1.5, "projection_years"),
    ("revenue_growth_rates", None, "revenue_growth_rates"),
    ("revenue_growth_rates", [-1.01], "growth"),
    ("revenue_growth_rates", [float("nan")], "growth"),
    ("revenue_growth_rates", [1e308], "projected revenue"),
    ("fcf_margins", [True], "FCF margin"),
    ("fcf_margins", ["0.2"], "FCF margin"),
    ("fcf_margins", [1e308], "projected FCF"),
    ("default_revenue_growth", float("inf"), "growth"),
    ("default_fcf_margin", float("nan"), "FCF margin"),
])
def test_invalid_shared_projections_raise_input_errors(model, field, value, message):
    if field == "revenue":
        model.historical[field] = value
    else:
        model.set_assumptions({
            **model.assumptions, "revenue_growth_rates": [], "fcf_margins": [], field: value,
        })
    with pytest.raises(ValueError, match=message):
        model.run_full_valuation()


def test_cli_rejects_nonfinite_shared_projection(data, tmp_path):
    data["assumptions"]["fcf_margins"] = [float("nan")]
    proc = run_cli(data, tmp_path)
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert "FCF margin" in proc.stderr


def test_zero_terminal_revenue_only_disables_exit_method(model):
    model.assumptions["revenue_growth_rates"][-1] = -1
    model.assumptions["fcf_margins"][0] = -0.1
    result = model.run_full_valuation()
    assert result["projected_fcf"][0] < 0
    assert result["terminal_value"] == {"exit_multiple": None, "perpetuity_growth": 0}
    assert result["enterprise_value"]["perpetuity_growth"] > 0
    assert "EBITDA" in result["unavailable_reasons"]["exit_multiple"]


@pytest.mark.parametrize("field", ["exit_ev_ebitda_multiple", "terminal_ebitda_margin"])
def test_exit_calculation_overflow_preserves_perpetuity(model, field):
    model.assumptions[field] = 1e308
    result = model.run_full_valuation()
    assert result["value_per_share"]["perpetuity_growth"] == pytest.approx(13.897515874028999)
    assert all(result[name]["exit_multiple"] is None for name in VALUES)
    assert result["unavailable_reasons"]["exit_multiple"]
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("first_unavailable", ["enterprise_value", "equity_value", "value_per_share"])
def test_exit_overflow_only_blocks_dependent_values(model, first_unavailable):
    model.assumptions["exit_ev_ebitda_multiple"] = 1e301
    if first_unavailable == "enterprise_value":
        model.assumptions["wacc_inputs"] = {
            "risk_free_rate": -0.1, "equity_risk_premium": 0, "equity_weight": 1, "debt_weight": 0,
        }
        model.assumptions["terminal_growth_rate"] = -0.2
    elif first_unavailable == "equity_value":
        model.historical["net_debt"] = -1.1e308
    else:
        model.historical["shares_outstanding"] = 0.01
    result = model.run_full_valuation()
    boundary = VALUES.index(first_unavailable)
    assert all(result[name]["exit_multiple"] > 0 for name in VALUES[:boundary])
    assert all(result[name]["exit_multiple"] is None for name in VALUES[boundary:])
    assert result["value_per_share"]["perpetuity_growth"] > 0
    assert result["unavailable_reasons"]["exit_multiple"]
    json.dumps(result, allow_nan=False)


def test_overflow_in_shared_per_share_inputs_is_an_explicit_error(data, model, tmp_path):
    data["historical"]["shares_outstanding"] = 1e-310
    with pytest.raises(ValueError, match="per-share"):
        model.run_full_valuation()
    proc = run_cli(data, tmp_path)
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert "per-share" in proc.stderr
