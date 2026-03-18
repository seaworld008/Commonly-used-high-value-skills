import argparse
import json
from pathlib import Path


def generate_report(data):
    memo_markdown = "\n".join(
        [
            f"# {data['company']} Investment Memo",
            "",
            f"## Recommendation",
            data["recommendation"],
            "",
            "## Thesis",
            "\n".join(f"- {item}" for item in data["thesis_points"]),
            "",
            "## Catalysts",
            "\n".join(f"- {item}" for item in data["catalysts"]),
            "",
            "## Risks",
            "\n".join(f"- {item}" for item in data["risks"]),
            "",
            "## Monitoring",
            "\n".join(f"- {item}" for item in data["monitoring_items"]),
        ]
    )

    return {
        "memo_markdown": memo_markdown,
        "recommendation": data["recommendation"],
        "key_monitoring_items": data["monitoring_items"],
    }


def main():
    parser = argparse.ArgumentParser(description="Build an investment memo from structured thesis inputs.")
    parser.add_argument("input_path")
    args = parser.parse_args()
    data = json.loads(Path(args.input_path).read_text(encoding="utf-8"))
    print(json.dumps(generate_report(data), indent=2))


if __name__ == "__main__":
    main()
