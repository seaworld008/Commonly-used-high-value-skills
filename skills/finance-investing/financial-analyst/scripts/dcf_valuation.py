#!/usr/bin/env python3
"""
DCF Valuation Model

Discounted Cash Flow enterprise and equity valuation with WACC calculation,
terminal value estimation, and two-way sensitivity analysis.

Uses standard library only (math, statistics) - NO numpy/pandas/scipy.

Usage:
    python dcf_valuation.py valuation_data.json
    python dcf_valuation.py valuation_data.json --format json
    python dcf_valuation.py valuation_data.json --projection-years 7
"""

import argparse
import json
import math
import sys
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero."""
    if denominator == 0 or denominator is None:
        return default
    return numerator / denominator


def is_finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:  # An integer outside the model's floating-point range.
        return False


def finite_result(value: float, field: str) -> float:
    if not is_finite_number(value):
        raise ValueError(f"{field} exceeds the numeric range")
    return value


def perpetuity_unavailable_reason(wacc: float, growth: float) -> Optional[str]:
    """Require an ordinary economic perpetuity and a convergent discounted series.

    Its geometric ratio is (1 + growth) / (1 + wacc), with absolute value < 1.
    Growth below -100% alternates cash-flow signs and is outside this model even
    when that series converges. At exactly -100%, all future cash flows are zero.
    """
    if not is_finite_number(wacc) or wacc <= -1:
        return "WACC must be finite and greater than -1; perpetuity values are unavailable"
    if not is_finite_number(growth):
        return "terminal_growth_rate must be finite; perpetuity values are unavailable"
    # For growth >= -1, convergence is exactly WACC > growth. Compare rates
    # directly so adding 1 does not erase a small, valid rate difference.
    if wacc <= growth or (growth < -1 and abs(1 + growth) >= 1 + wacc):
        return (
            "Discounted perpetuity series does not converge; requires abs(1 + "
            "terminal_growth_rate) < 1 + WACC and WACC must exceed "
            "terminal_growth_rate; perpetuity values are unavailable"
        )
    if growth < -1:
        return (
            "terminal_growth_rate below -100% implies alternating cash-flow signs; "
            "ordinary economic perpetuity is not estimable (requires growth >= -1)"
        )
    return None


class DCFModel:
    """Discounted Cash Flow valuation model."""

    def __init__(self) -> None:
        """Initialize the DCF model."""
        self.historical: Dict[str, Any] = {}
        self.assumptions: Dict[str, Any] = {}
        self.wacc: float = 0.0
        self.projected_revenue: List[float] = []
        self.projected_fcf: List[float] = []
        self.projection_years: int = 5
        self.terminal_value_perpetuity: Optional[float] = None
        self.terminal_value_exit_multiple: Optional[float] = None
        self.enterprise_value_perpetuity: Optional[float] = None
        self.enterprise_value_exit_multiple: Optional[float] = None
        self.equity_value_perpetuity: Optional[float] = None
        self.equity_value_exit_multiple: Optional[float] = None
        self.value_per_share_perpetuity: Optional[float] = None
        self.value_per_share_exit_multiple: Optional[float] = None
        self.unavailable_reasons: Dict[str, str] = {}

    def set_historical_financials(self, historical: Dict[str, Any]) -> None:
        """Set historical financial data."""
        self.historical = historical

    def set_assumptions(self, assumptions: Dict[str, Any]) -> None:
        """Set projection assumptions."""
        self.assumptions = assumptions
        self.projection_years = assumptions.get("projection_years", 5)

    def calculate_wacc(self) -> float:
        """Calculate Weighted Average Cost of Capital via CAPM."""
        wacc_inputs = self.assumptions.get("wacc_inputs", {})

        risk_free_rate = wacc_inputs.get("risk_free_rate", 0.04)
        equity_risk_premium = wacc_inputs.get("equity_risk_premium", 0.06)
        beta = wacc_inputs.get("beta", 1.0)
        cost_of_debt = wacc_inputs.get("cost_of_debt", 0.05)
        tax_rate = wacc_inputs.get("tax_rate", 0.25)
        debt_weight = wacc_inputs.get("debt_weight", 0.30)
        equity_weight = wacc_inputs.get("equity_weight", 0.70)

        # CAPM: Cost of Equity = Risk-Free Rate + Beta * Equity Risk Premium
        cost_of_equity = risk_free_rate + beta * equity_risk_premium

        # WACC = (E/V * Re) + (D/V * Rd * (1 - T))
        after_tax_cost_of_debt = cost_of_debt * (1 - tax_rate)
        self.wacc = (equity_weight * cost_of_equity) + (
            debt_weight * after_tax_cost_of_debt
        )

        return self.wacc

    def project_cash_flows(self) -> Tuple[List[float], List[float]]:
        """Project revenue and free cash flow over the projection period."""
        base_revenue = self.historical.get("revenue", [])
        if not isinstance(base_revenue, (list, tuple)) or not base_revenue:
            raise ValueError("Historical revenue data is required")

        last_revenue = base_revenue[-1]
        if not is_finite_number(last_revenue) or last_revenue < 0:
            raise ValueError("Latest historical revenue must be finite and nonnegative")
        if type(self.projection_years) is not int or self.projection_years <= 0:
            raise ValueError("projection_years must be a positive integer")

        revenue_growth_rates = self.assumptions.get("revenue_growth_rates", [])
        fcf_margins = self.assumptions.get("fcf_margins", [])
        for field, values in (("revenue_growth_rates", revenue_growth_rates), ("fcf_margins", fcf_margins)):
            if not isinstance(values, (list, tuple)):
                raise ValueError(f"{field} must be a sequence of numbers")

        # Apply defaults only for years without an explicit assumption.
        default_growth = self.assumptions.get("default_revenue_growth", 0.05)
        default_fcf_margin = self.assumptions.get("default_fcf_margin", 0.10)

        revenues = []
        cash_flows = []
        current_revenue = last_revenue

        for year in range(self.projection_years):
            growth = (
                revenue_growth_rates[year]
                if year < len(revenue_growth_rates)
                else default_growth
            )
            fcf_margin = (
                fcf_margins[year]
                if year < len(fcf_margins)
                else default_fcf_margin
            )

            if not is_finite_number(growth) or growth < -1:
                raise ValueError(f"Year {year + 1} revenue growth must be finite and at least -1")
            if not is_finite_number(fcf_margin):
                raise ValueError(f"Year {year + 1} FCF margin must be a finite number")

            current_revenue = finite_result(current_revenue * (1 + growth), f"Year {year + 1} projected revenue")
            fcf = finite_result(current_revenue * fcf_margin, f"Year {year + 1} projected FCF")

            revenues.append(current_revenue)
            cash_flows.append(fcf)

        self.projected_revenue = revenues
        self.projected_fcf = cash_flows
        return self.projected_revenue, self.projected_fcf

    def _finite_exit_value(self, value: float, field: str) -> Optional[float]:
        if is_finite_number(value):
            return value
        self.unavailable_reasons["exit_multiple"] = f"Exit multiple {field} exceeds the numeric range"
        return None

    def calculate_terminal_value(self) -> Tuple[Optional[float], Optional[float]]:
        """Calculate terminal value using both perpetuity growth and exit multiple."""
        if not self.projected_fcf:
            raise ValueError("Must project cash flows before terminal value")

        terminal_fcf = self.projected_fcf[-1]
        terminal_growth = self.assumptions.get("terminal_growth_rate", 0.025)
        exit_multiple = self.assumptions.get("exit_ev_ebitda_multiple", 12.0)

        # Perpetuity growth method: TV = FCF * (1+g) / (WACC - g)
        if not is_finite_number(self.wacc) or self.wacc <= -1:
            raise ValueError("WACC must be finite and greater than -1")
        if not is_finite_number(terminal_growth):
            raise ValueError("terminal_growth_rate must be a finite number")
        self.unavailable_reasons.pop("perpetuity_growth", None)
        reason = perpetuity_unavailable_reason(self.wacc, terminal_growth)
        if reason is None:
            self.terminal_value_perpetuity = finite_result(
                terminal_fcf * (1 + terminal_growth) / (self.wacc - terminal_growth),
                "Perpetuity terminal value",
            )
        else:
            self.terminal_value_perpetuity = None
            self.unavailable_reasons["perpetuity_growth"] = reason

        # Exit multiple method: TV = Terminal EBITDA * Exit Multiple
        terminal_revenue = self.projected_revenue[-1]
        ebitda_margin = self.assumptions.get("terminal_ebitda_margin", 0.20)
        self.unavailable_reasons.pop("exit_multiple", None)
        self.terminal_value_exit_multiple = None
        if not is_finite_number(exit_multiple) or exit_multiple <= 0:
            self.unavailable_reasons["exit_multiple"] = "exit_ev_ebitda_multiple must be finite and positive"
        elif not is_finite_number(ebitda_margin) or ebitda_margin <= 0:
            self.unavailable_reasons["exit_multiple"] = "terminal_ebitda_margin must be finite and positive"
        else:
            terminal_ebitda = terminal_revenue * ebitda_margin
            if not is_finite_number(terminal_ebitda) or terminal_ebitda <= 0:
                self.unavailable_reasons["exit_multiple"] = "Projected terminal EBITDA must be finite and positive"
            else:
                self.terminal_value_exit_multiple = self._finite_exit_value(
                    terminal_ebitda * exit_multiple, "terminal value"
                )

        return self.terminal_value_perpetuity, self.terminal_value_exit_multiple

    def calculate_enterprise_value(self) -> Tuple[Optional[float], Optional[float]]:
        """Calculate enterprise value by discounting projected FCFs and terminal value."""
        if not self.projected_fcf:
            raise ValueError("Must project cash flows first")

        # Discount projected FCFs
        pv_fcf = 0.0
        for i, fcf in enumerate(self.projected_fcf):
            discount_factor = (1 + self.wacc) ** (i + 1)
            pv_fcf += fcf / discount_factor

        # Discount terminal values
        terminal_discount = (1 + self.wacc) ** self.projection_years

        self.enterprise_value_perpetuity = (
            finite_result(pv_fcf + self.terminal_value_perpetuity / terminal_discount, "Perpetuity enterprise value")
            if self.terminal_value_perpetuity is not None else None
        )
        self.enterprise_value_exit_multiple = (
            self._finite_exit_value(
                pv_fcf + self.terminal_value_exit_multiple / terminal_discount, "enterprise value"
            )
            if self.terminal_value_exit_multiple is not None else None
        )

        return self.enterprise_value_perpetuity, self.enterprise_value_exit_multiple

    def _equity_input_issues(self) -> Dict[str, str]:
        issues = {}
        if not is_finite_number(self.historical.get("net_debt")):
            issues["net_debt"] = (
                "net_debt is missing or invalid; equity and per-share values are unavailable "
                "(cash/debt cannot be assumed zero)"
            )
        shares = self.historical.get("shares_outstanding")
        if not is_finite_number(shares) or shares <= 0:
            issues["shares_outstanding"] = (
                "shares_outstanding must be a known positive number; per-share values are unavailable"
            )
        return issues

    def calculate_equity_value(self) -> Tuple[Optional[float], Optional[float]]:
        """Calculate equity value from enterprise value."""
        net_debt = self.historical.get("net_debt")
        shares_outstanding = self.historical.get("shares_outstanding")
        issues = self._equity_input_issues()
        for field in ("net_debt", "shares_outstanding"):
            self.unavailable_reasons.pop(field, None)
        self.unavailable_reasons.update(issues)

        self.equity_value_perpetuity = (
            finite_result(self.enterprise_value_perpetuity - net_debt, "Perpetuity equity value")
            if self.enterprise_value_perpetuity is not None and "net_debt" not in issues
            else None
        )
        self.equity_value_exit_multiple = (
            self._finite_exit_value(self.enterprise_value_exit_multiple - net_debt, "equity value")
            if self.enterprise_value_exit_multiple is not None and "net_debt" not in issues
            else None
        )

        self.value_per_share_perpetuity = (
            finite_result(self.equity_value_perpetuity / shares_outstanding, "Perpetuity per-share value")
            if self.equity_value_perpetuity is not None and "shares_outstanding" not in issues
            else None
        )
        self.value_per_share_exit_multiple = (
            self._finite_exit_value(self.equity_value_exit_multiple / shares_outstanding, "per-share value")
            if self.equity_value_exit_multiple is not None and "shares_outstanding" not in issues
            else None
        )

        return self.equity_value_perpetuity, self.equity_value_exit_multiple

    def sensitivity_analysis(
        self,
        wacc_range: Optional[List[float]] = None,
        growth_range: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Two-way sensitivity analysis: WACC vs terminal growth rate.

        Returns a table of enterprise values using nested lists (no numpy).
        """
        if wacc_range is None:
            base_wacc = self.wacc
            wacc_range = [
                round(base_wacc - 0.02, 4),
                round(base_wacc - 0.01, 4),
                round(base_wacc, 4),
                round(base_wacc + 0.01, 4),
                round(base_wacc + 0.02, 4),
            ]

        if growth_range is None:
            base_growth = self.assumptions.get("terminal_growth_rate", 0.025)
            growth_range = [
                round(base_growth - 0.01, 4),
                round(base_growth - 0.005, 4),
                round(base_growth, 4),
                round(base_growth + 0.005, 4),
                round(base_growth + 0.01, 4),
            ]

        rows = len(wacc_range)
        cols = len(growth_range)

        # Initialize sensitivity table as nested lists
        ev_table = [[None] * cols for _ in range(rows)]
        share_price_table = [[None] * cols for _ in range(rows)]
        issues = self._equity_input_issues()
        reasons = dict(issues)
        perpetuity_reasons = []

        terminal_fcf = self.projected_fcf[-1] if self.projected_fcf else 0

        for i, wacc_val in enumerate(wacc_range):
            for j, growth_val in enumerate(growth_range):
                reason = perpetuity_unavailable_reason(wacc_val, growth_val)
                if reason is not None:
                    if reason not in perpetuity_reasons:
                        perpetuity_reasons.append(reason)
                    continue

                # Recalculate PV of projected FCFs with this WACC
                pv_fcf = 0.0
                for k, fcf in enumerate(self.projected_fcf):
                    pv_fcf += fcf / ((1 + wacc_val) ** (k + 1))

                # Terminal value with this growth rate
                tv = (terminal_fcf * (1 + growth_val)) / (wacc_val - growth_val)
                pv_tv = tv / ((1 + wacc_val) ** self.projection_years)

                ev = finite_result(pv_fcf + pv_tv, "Sensitivity enterprise value")
                ev_table[i][j] = round(ev, 2)

                if not issues:
                    equity = ev - self.historical["net_debt"]
                    price = finite_result(equity / self.historical["shares_outstanding"], "Sensitivity per-share value")
                    share_price_table[i][j] = round(price, 2)

        if perpetuity_reasons:
            reasons["perpetuity_growth"] = "; ".join(perpetuity_reasons)

        return {
            "wacc_values": wacc_range,
            "growth_values": growth_range,
            "enterprise_value_table": ev_table,
            "share_price_table": share_price_table,
            "unavailable_reasons": reasons,
        }

    def run_full_valuation(self) -> Dict[str, Any]:
        """Run DCF; unavailable methods/values are null with unavailable_reasons.

        Invalid economic growth or nonconvergence disables perpetuity growth.
        Growth == -100% gives zero terminal cash flow. Invalid exit multiples or
        terminal EBITDA disable the exit method. Both use the same projected FCFs.
        Missing net debt blocks equity values; missing positive shares blocks only
        per-share values. Sensitivity tables follow the same null convention.
        """
        self.calculate_wacc()
        self.project_cash_flows()
        self.calculate_terminal_value()
        self.calculate_enterprise_value()
        self.calculate_equity_value()
        sensitivity = self.sensitivity_analysis()

        return {
            "wacc": self.wacc,
            "projected_revenue": self.projected_revenue,
            "projected_fcf": self.projected_fcf,
            "terminal_value": {
                "perpetuity_growth": self.terminal_value_perpetuity,
                "exit_multiple": self.terminal_value_exit_multiple,
            },
            "enterprise_value": {
                "perpetuity_growth": self.enterprise_value_perpetuity,
                "exit_multiple": self.enterprise_value_exit_multiple,
            },
            "equity_value": {
                "perpetuity_growth": self.equity_value_perpetuity,
                "exit_multiple": self.equity_value_exit_multiple,
            },
            "value_per_share": {
                "perpetuity_growth": self.value_per_share_perpetuity,
                "exit_multiple": self.value_per_share_exit_multiple,
            },
            "sensitivity_analysis": sensitivity,
            "unavailable_reasons": dict(self.unavailable_reasons),
        }

    def format_text(self, results: Dict[str, Any]) -> str:
        """Format valuation results as human-readable text."""
        lines: List[str] = []
        lines.append("=" * 70)
        lines.append("DCF VALUATION ANALYSIS")
        lines.append("=" * 70)

        def fmt_money(val: Optional[float]) -> str:
            if val is None:
                return "N/A"
            if val == float("inf"):
                return "N/A (WACC <= growth)"
            if abs(val) >= 1e9:
                return f"${val / 1e9:,.2f}B"
            if abs(val) >= 1e6:
                return f"${val / 1e6:,.2f}M"
            if abs(val) >= 1e3:
                return f"${val / 1e3:,.1f}K"
            return f"${val:,.2f}"

        def fmt_price(val: Optional[float]) -> str:
            return f"${val:,.2f}" if val is not None else "N/A"

        lines.append(f"\n--- WACC ---")
        lines.append(f"  Weighted Average Cost of Capital: {results['wacc'] * 100:.2f}%")

        lines.append(f"\n--- REVENUE PROJECTIONS ---")
        for i, rev in enumerate(results["projected_revenue"], 1):
            lines.append(f"  Year {i}: {fmt_money(rev)}")

        lines.append(f"\n--- FREE CASH FLOW PROJECTIONS ---")
        for i, fcf in enumerate(results["projected_fcf"], 1):
            lines.append(f"  Year {i}: {fmt_money(fcf)}")

        lines.append(f"\n--- TERMINAL VALUE ---")
        lines.append(
            f"  Perpetuity Growth Method: "
            f"{fmt_money(results['terminal_value']['perpetuity_growth'])}"
        )
        lines.append(
            f"  Exit Multiple Method:     "
            f"{fmt_money(results['terminal_value']['exit_multiple'])}"
        )

        lines.append(f"\n--- ENTERPRISE VALUE ---")
        lines.append(
            f"  Perpetuity Growth Method: "
            f"{fmt_money(results['enterprise_value']['perpetuity_growth'])}"
        )
        lines.append(
            f"  Exit Multiple Method:     "
            f"{fmt_money(results['enterprise_value']['exit_multiple'])}"
        )

        lines.append(f"\n--- EQUITY VALUE ---")
        lines.append(
            f"  Perpetuity Growth Method: "
            f"{fmt_money(results['equity_value']['perpetuity_growth'])}"
        )
        lines.append(
            f"  Exit Multiple Method:     "
            f"{fmt_money(results['equity_value']['exit_multiple'])}"
        )

        lines.append(f"\n--- VALUE PER SHARE ---")
        vps = results["value_per_share"]
        lines.append(f"  Perpetuity Growth Method: {fmt_price(vps['perpetuity_growth'])}")
        lines.append(f"  Exit Multiple Method:     {fmt_price(vps['exit_multiple'])}")

        if results.get("unavailable_reasons"):
            lines.append("\n--- UNAVAILABLE REASONS ---")
            for field, reason in results["unavailable_reasons"].items():
                lines.append(f"  {field}: {reason}")

        # Sensitivity table
        sens = results["sensitivity_analysis"]
        lines.append(f"\n--- SENSITIVITY ANALYSIS (Enterprise Value) ---")
        lines.append(f"  WACC vs Terminal Growth Rate")
        for field, reason in sens.get("unavailable_reasons", {}).items():
            lines.append(f"  {field}: {reason}")
        lines.append("")

        header = "  {:>10s}".format("WACC \\ g")
        for g in sens["growth_values"]:
            header += f"  {g * 100:>8.1f}%"
        lines.append(header)
        lines.append("  " + "-" * (10 + 10 * len(sens["growth_values"])))

        for i, w in enumerate(sens["wacc_values"]):
            row = f"  {w * 100:>9.1f}%"
            for j in range(len(sens["growth_values"])):
                val = sens["enterprise_value_table"][i][j]
                if val == float("inf"):
                    row += f"  {'N/A':>8s}"
                else:
                    row += f"  {fmt_money(val):>8s}"
            lines.append(row)

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DCF Valuation Model - Enterprise and equity valuation"
    )
    parser.add_argument(
        "input_file",
        help="Path to JSON file with valuation data",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--projection-years",
        type=int,
        default=None,
        help="Number of projection years (overrides input file)",
    )

    args = parser.parse_args()

    try:
        with open(args.input_file, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{args.input_file}' not found.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{args.input_file}': {e}", file=sys.stderr)
        sys.exit(1)

    model = DCFModel()
    model.set_historical_financials(data.get("historical", {}))

    assumptions = data.get("assumptions", {})
    if args.projection_years is not None:
        assumptions["projection_years"] = args.projection_years
    model.set_assumptions(assumptions)

    try:
        results = model.run_full_valuation()
        if args.format == "json":
            print(json.dumps(results, indent=2, allow_nan=False))
        else:
            print(model.format_text(results))
    except (ValueError, ArithmeticError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
