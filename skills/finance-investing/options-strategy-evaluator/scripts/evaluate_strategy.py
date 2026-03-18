import argparse
import json
from pathlib import Path


def payoff_for_leg(leg, price):
    quantity = leg.get("quantity", 1)
    multiplier = 1 if leg["side"] == "long" else -1
    premium_effect = leg["premium"] * quantity * multiplier

    if leg["type"] == "call":
        intrinsic = max(price - leg["strike"], 0) * quantity
    else:
        intrinsic = max(leg["strike"] - price, 0) * quantity

    intrinsic *= multiplier
    return intrinsic - premium_effect


def generate_report(data):
    checkpoints = []
    for price in data["price_checkpoints"]:
        pnl = sum(payoff_for_leg(leg, price) for leg in data["legs"])
        checkpoints.append({"underlying_price": price, "expiry_pnl": round(pnl, 2)})

    net_premium = round(
        sum(
            (-1 if leg["side"] == "long" else 1) * leg["premium"] * leg.get("quantity", 1)
            for leg in data["legs"]
        ),
        2,
    )

    return {
        "strategy_summary": {
            "name": data["strategy_name"],
            "underlying": data["underlying"],
            "net_premium": net_premium,
            "legs": len(data["legs"]),
            "best_checkpoint_pnl": max(item["expiry_pnl"] for item in checkpoints),
            "worst_checkpoint_pnl": min(item["expiry_pnl"] for item in checkpoints),
        },
        "payoff_checkpoints": checkpoints,
        "risk_notes": data.get("risk_notes", []),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate payoff checkpoints for a simple options strategy.")
    parser.add_argument("input_path")
    args = parser.parse_args()
    data = json.loads(Path(args.input_path).read_text(encoding="utf-8"))
    print(json.dumps(generate_report(data), indent=2))


if __name__ == "__main__":
    main()
