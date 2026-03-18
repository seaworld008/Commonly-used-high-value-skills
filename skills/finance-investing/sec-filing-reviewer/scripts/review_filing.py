import argparse
import json
from pathlib import Path


RISK_TERMS = {
    "material weakness": "controls",
    "substantial doubt": "liquidity",
    "going concern": "liquidity",
    "investigation": "regulatory",
    "restatement": "reporting",
    "litigation": "legal",
}


def generate_report(data):
    sections = data["sections"]
    flags = []
    follow_up = []

    for section in sections:
        lowered = section["text"].lower()
        for term, category in RISK_TERMS.items():
            if term in lowered:
                flags.append(
                    {
                        "section": section["name"],
                        "category": category,
                        "trigger": term,
                    }
                )
                follow_up.append(f"Review {section['name']} for {category} disclosure tied to '{term}'.")

    return {
        "sections_reviewed": len(sections),
        "risk_flags": flags,
        "follow_up_questions": follow_up or ["No critical disclosure triggers found in the sample review."],
    }


def main():
    parser = argparse.ArgumentParser(description="Review structured filing sections for risk triggers.")
    parser.add_argument("input_path")
    args = parser.parse_args()
    data = json.loads(Path(args.input_path).read_text(encoding="utf-8"))
    print(json.dumps(generate_report(data), indent=2))


if __name__ == "__main__":
    main()
