import argparse
import json
import math
from collections import defaultdict
from pathlib import Path


def generate_report(data):
    holdings = data["holdings"]
    weighted_beta = sum(item["weight"] * item.get("beta", 1.0) for item in holdings)
    weighted_vol = math.sqrt(sum((item["weight"] * item.get("volatility", 0.0)) ** 2 for item in holdings))

    sector_weights = defaultdict(float)
    region_weights = defaultdict(float)
    for item in holdings:
        sector_weights[item["sector"]] += item["weight"]
        region_weights[item["region"]] += item["weight"]

    top_position = max(holdings, key=lambda item: item["weight"])
    top_5_concentration = round(
        sum(item["weight"] for item in sorted(holdings, key=lambda item: item["weight"], reverse=True)[:5]),
        3,
    )
    max_sector_weight = round(max(sector_weights.values()), 3) if sector_weights else 0.0
    portfolio_summary = {
        "portfolio_name": data["portfolio_name"],
        "holding_count": len(holdings),
        "top_position": top_position["ticker"],
        "top_5_concentration": top_5_concentration,
    }
    risk_metrics = {
        "weighted_beta": round(weighted_beta, 3),
        "naive_portfolio_volatility": round(weighted_vol, 3),
        "cash_weight": round(data.get("cash_weight", 0.0), 3),
        "max_sector_weight": max_sector_weight,
    }
    exposure_breakdown = {
        "sector_weights": dict(sorted(sector_weights.items())),
        "region_weights": dict(sorted(region_weights.items())),
    }

    return {
        "portfolio_summary": portfolio_summary,
        "risk_metrics": risk_metrics,
        "exposure_breakdown": exposure_breakdown,
    }


def main():
    parser = argparse.ArgumentParser(description="Calculate lightweight portfolio risk metrics.")
    parser.add_argument("input_path")
    args = parser.parse_args()
    data = json.loads(Path(args.input_path).read_text(encoding="utf-8"))
    print(json.dumps(generate_report(data), indent=2))


if __name__ == "__main__":
    main()
