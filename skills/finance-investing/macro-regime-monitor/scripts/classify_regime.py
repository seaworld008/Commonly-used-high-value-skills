import argparse
import json
from pathlib import Path


def score_indicator(current, previous, direction):
    if current == previous:
        return 0
    if direction == "up_is_risk":
        return 1 if current > previous else -1
    return 1 if current < previous else -1


def generate_report(data):
    inflation_score = score_indicator(
        data["inflation"]["current"], data["inflation"]["previous"], "up_is_risk"
    )
    growth_score = score_indicator(
        data["growth"]["current"], data["growth"]["previous"], "down_is_risk"
    )
    spreads_score = score_indicator(
        data["credit_spreads"]["current"], data["credit_spreads"]["previous"], "up_is_risk"
    )
    liquidity_score = score_indicator(
        data["liquidity"]["current"], data["liquidity"]["previous"], "down_is_risk"
    )

    total_score = inflation_score + growth_score + spreads_score + liquidity_score
    if total_score <= -2:
        current_regime = "risk-on disinflation"
    elif total_score >= 2:
        current_regime = "risk-off tightening"
    else:
        current_regime = "mixed transition"

    return {
        "current_regime": current_regime,
        "regime_scorecard": {
            "inflation_score": inflation_score,
            "growth_score": growth_score,
            "credit_spreads_score": spreads_score,
            "liquidity_score": liquidity_score,
            "total_score": total_score,
        },
        "watch_items": data.get("watch_items", []),
    }


def main():
    parser = argparse.ArgumentParser(description="Classify a macro regime from simple indicator deltas.")
    parser.add_argument("input_path")
    args = parser.parse_args()
    data = json.loads(Path(args.input_path).read_text(encoding="utf-8"))
    print(json.dumps(generate_report(data), indent=2))


if __name__ == "__main__":
    main()
