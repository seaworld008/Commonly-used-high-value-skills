import argparse
import json
from pathlib import Path


POSITIVE_TERMS = {"beat", "strong", "accelerate", "improve", "confidence", "momentum"}
CAUTION_TERMS = {"headwind", "pressure", "softness", "uncertain", "slowdown", "risk"}
GUIDANCE_TERMS = {"guidance", "outlook", "forecast", "expect", "range"}
CAPEX_TERMS = {"capex", "investment", "capacity", "buildout"}


def count_terms(text, terms):
    lowered = text.lower()
    return sum(lowered.count(term) for term in terms)


def generate_report(data):
    segments = data["segments"]
    combined_text = " ".join(segment["text"] for segment in segments)

    positive_count = count_terms(combined_text, POSITIVE_TERMS)
    caution_count = count_terms(combined_text, CAUTION_TERMS)
    guidance_count = count_terms(combined_text, GUIDANCE_TERMS)
    capex_count = count_terms(combined_text, CAPEX_TERMS)

    if positive_count >= caution_count + 2:
        management_tone = "constructive"
    elif caution_count > positive_count:
        management_tone = "cautious"
    else:
        management_tone = "balanced"

    summary = (
        f"{data['company']} management tone is {management_tone}. "
        f"Guidance references: {guidance_count}. Capex references: {capex_count}."
    )

    return {
        "summary": summary,
        "signal_counts": {
            "positive": positive_count,
            "caution": caution_count,
            "guidance": guidance_count,
            "capex": capex_count,
        },
        "management_tone": management_tone,
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze a structured earnings-call transcript.")
    parser.add_argument("input_path")
    args = parser.parse_args()
    data = json.loads(Path(args.input_path).read_text(encoding="utf-8"))
    print(json.dumps(generate_report(data), indent=2))


if __name__ == "__main__":
    main()
