import argparse
import json
import statistics
from pathlib import Path


def median(values):
    numeric = [value for value in values if value is not None]
    if not numeric:
        return None
    return statistics.median(numeric)


def generate_report(data):
    subject = data["subject_company"]
    peers = data["peers"]

    peer_stats = {
        "median_ev_ebitda": median([peer.get("ev_ebitda") for peer in peers]),
        "median_pe": median([peer.get("pe_ratio") for peer in peers]),
        "median_ev_sales": median([peer.get("ev_sales") for peer in peers]),
        "peer_count": len(peers),
    }

    ebitda = subject.get("ebitda")
    eps = subject.get("eps")
    revenue = subject.get("revenue")
    net_debt = subject.get("net_debt", 0)
    shares_outstanding = subject.get("shares_outstanding", 1)

    implied_prices = {}
    if peer_stats["median_ev_ebitda"] is not None and ebitda is not None:
        enterprise_value = peer_stats["median_ev_ebitda"] * ebitda
        equity_value = enterprise_value - net_debt
        implied_prices["ev_ebitda"] = round(equity_value / shares_outstanding, 2)
    if peer_stats["median_pe"] is not None and eps is not None:
        implied_prices["pe_ratio"] = round(peer_stats["median_pe"] * eps, 2)
    if peer_stats["median_ev_sales"] is not None and revenue is not None:
        enterprise_value = peer_stats["median_ev_sales"] * revenue
        equity_value = enterprise_value - net_debt
        implied_prices["ev_sales"] = round(equity_value / shares_outstanding, 2)

    valuation_summary = {
        "ticker": subject["ticker"],
        "current_price": subject["current_price"],
        "implied_price_range": implied_prices,
        "average_implied_price": round(sum(implied_prices.values()) / len(implied_prices), 2)
        if implied_prices
        else None,
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
