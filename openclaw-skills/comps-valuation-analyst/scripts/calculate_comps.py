import argparse
import json
import math
import statistics
from pathlib import Path


def median(values):
    numeric = [value for value in values if value is not None]
    if not numeric:
        return None
    return statistics.median(numeric)


def is_finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def positive_median(values):
    return median([value for value in values if is_finite_number(value) and value > 0])


def generate_report(data):
    """Return null prices with unavailable_reasons when a method lacks valid inputs."""
    subject = data["subject_company"]
    peers = data["peers"]

    peer_stats = {
        "median_ev_ebitda": positive_median([peer.get("ev_ebitda") for peer in peers]),
        "median_pe": positive_median([peer.get("pe_ratio") for peer in peers]),
        "median_ev_sales": positive_median([peer.get("ev_sales") for peer in peers]),
        "peer_count": len(peers),
    }

    net_debt = subject.get("net_debt")
    shares_outstanding = subject.get("shares_outstanding")

    implied_prices = {}
    unavailable_reasons = {}
    for method, stat, metric in (
        ("ev_ebitda", "median_ev_ebitda", "ebitda"),
        ("pe_ratio", "median_pe", "eps"),
        ("ev_sales", "median_ev_sales", "revenue"),
    ):
        reasons = []
        multiple = peer_stats[stat]
        value = subject.get(metric)
        if multiple is None:
            reasons.append(f"No positive peer {method} multiples available")
        if not is_finite_number(value) or value <= 0:
            reasons.append(f"{metric} must be a known positive number")
        if method != "pe_ratio":
            if not is_finite_number(net_debt):
                reasons.append("net_debt is missing or invalid; cash/debt cannot be assumed zero")
            if not is_finite_number(shares_outstanding) or shares_outstanding <= 0:
                reasons.append("shares_outstanding must be a known positive number")

        if reasons:
            implied_prices[method] = None
            unavailable_reasons[method] = reasons
        elif method == "pe_ratio":
            implied_prices[method] = round(multiple * value, 2)
        else:
            implied_prices[method] = round((multiple * value - net_debt) / shares_outstanding, 2)

    valid_prices = [value for value in implied_prices.values() if value is not None]

    valuation_summary = {
        "ticker": subject["ticker"],
        "current_price": subject["current_price"],
        "implied_price_range": implied_prices,
        "average_implied_price": round(sum(valid_prices) / len(valid_prices), 2)
        if valid_prices
        else None,
        "unavailable_reasons": unavailable_reasons,
    }

    return {
        "valuation_summary": valuation_summary,
        "company_results": {
            "subject_company": subject,
            "peer_tickers": [peer["ticker"] for peer in peers],
        },
        "peer_statistics": peer_stats,
    }


def main():
    parser = argparse.ArgumentParser(description="Run simple comparable-company valuation analysis.")
    parser.add_argument("input_path")
    args = parser.parse_args()
    data = json.loads(Path(args.input_path).read_text(encoding="utf-8"))
    print(json.dumps(generate_report(data), indent=2))


if __name__ == "__main__":
    main()
