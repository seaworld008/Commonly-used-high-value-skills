import argparse
import json
from pathlib import Path


def passes_filters(stock, filters):
    for key, rule in filters.items():
        value = stock.get(key)
        if value is None:
            return False
        if "min" in rule and value < rule["min"]:
            return False
        if "max" in rule and value > rule["max"]:
            return False
    return True


def generate_report(data):
    filters = data["filters"]
    matches = [stock for stock in data["universe"] if passes_filters(stock, filters)]
    matches.sort(key=lambda item: (-item.get("quality_score", 0), item["ticker"]))

    return {
        "matches": matches,
        "match_count": len(matches),
        "active_filters": filters,
    }


def main():
    parser = argparse.ArgumentParser(description="Screen a stock universe with JSON filter rules.")
    parser.add_argument("input_path")
    args = parser.parse_args()
    data = json.loads(Path(args.input_path).read_text(encoding="utf-8"))
    print(json.dumps(generate_report(data), indent=2))


if __name__ == "__main__":
    main()
