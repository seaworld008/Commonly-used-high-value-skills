import argparse
import json
from pathlib import Path


def generate_report(data):
    periods = data["periods"]
    portfolio_path = []
    cumulative = 1.0
    benchmark = 1.0
    peak = 1.0
    max_drawdown = 0.0
    positive_months = 0
    turnover_total = 0.0
    transaction_cost_bps = data.get("transaction_cost_bps", 0.0)

    for period in periods:
        factor_return = period["long_return"] - period["short_return"]
        period_cost = period.get("turnover", 0.0) * (transaction_cost_bps / 10000)
        net_factor_return = factor_return - period_cost
        cumulative *= 1 + net_factor_return
        benchmark *= 1 + period["benchmark_return"]
        turnover_total += period.get("turnover", 0.0)
        if factor_return > 0:
            positive_months += 1
        peak = max(peak, cumulative)
        max_drawdown = min(max_drawdown, cumulative / peak - 1)
        portfolio_path.append(
            {
                "period": period["period"],
                "factor_return": round(factor_return, 4),
                "net_factor_return": round(net_factor_return, 4),
                "cumulative_index": round(cumulative, 4),
            }
        )

    performance_summary = {
        "period_count": len(periods),
        "cumulative_return": round(cumulative - 1, 4),
        "benchmark_return": round(benchmark - 1, 4),
        "hit_rate": round(positive_months / len(periods), 4) if periods else 0.0,
        "max_drawdown": round(max_drawdown, 4),
    }

    return {
        "performance_summary": performance_summary,
        "portfolio_path": portfolio_path,
        "turnover": round(turnover_total / len(periods), 4) if periods else 0.0,
    }


def main():
    parser = argparse.ArgumentParser(description="Backtest a simple factor spread series.")
    parser.add_argument("input_path")
    args = parser.parse_args()
    data = json.loads(Path(args.input_path).read_text(encoding="utf-8"))
    print(json.dumps(generate_report(data), indent=2))


if __name__ == "__main__":
    main()
