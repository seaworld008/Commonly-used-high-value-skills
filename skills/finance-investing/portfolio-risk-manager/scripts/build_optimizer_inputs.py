import argparse
import json
import math
from pathlib import Path


def mean(values):
    return sum(values) / len(values) if values else 0.0


def covariance(series_a, series_b):
    avg_a = mean(series_a)
    avg_b = mean(series_b)
    if len(series_a) < 2 or len(series_b) < 2:
        return 0.0
    paired = zip(series_a, series_b)
    return sum((a - avg_a) * (b - avg_b) for a, b in paired) / (len(series_a) - 1)


def variance(series):
    return covariance(series, series)


def normalize(weights):
    total = sum(weights.values())
    if total == 0:
        return {key: 0.0 for key in weights}
    return {key: round(value / total, 6) for key, value in weights.items()}


def generate_report(data):
    returns = data["returns"]
    assets = list(returns.keys())
    expected_returns = {asset: round(mean(series), 6) for asset, series in returns.items()}

    covariance_matrix = {}
    inverse_vol_weights = {}
    for asset in assets:
        covariance_matrix[asset] = {}
        vol = math.sqrt(max(variance(returns[asset]), 0.0))
        inverse_vol_weights[asset] = 1 / vol if vol > 0 else 0.0
        for other in assets:
            covariance_matrix[asset][other] = round(covariance(returns[asset], returns[other]), 8)

    equal_weight = round(1 / len(assets), 6) if assets else 0.0
    optimizer_ready = {
        "assets": assets,
        "expected_returns": expected_returns,
        "covariance_matrix": covariance_matrix,
        "seed_weights": {
            "equal_weight": {asset: equal_weight for asset in assets},
            "inverse_volatility": normalize(inverse_vol_weights),
        },
    }
    return optimizer_ready


def main():
    parser = argparse.ArgumentParser(description="Build optimizer-ready expected return and covariance inputs.")
    parser.add_argument("input_path")
    args = parser.parse_args()
    data = json.loads(Path(args.input_path).read_text(encoding="utf-8"))
    print(json.dumps(generate_report(data), indent=2))


if __name__ == "__main__":
    main()
