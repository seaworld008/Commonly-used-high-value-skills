import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


DATE_FORMAT = "%Y-%m-%d"


def generate_report(data):
    as_of = datetime.strptime(data["as_of"], DATE_FORMAT).date()
    events = []
    for item in data["events"]:
        event_date = datetime.strptime(item["date"], DATE_FORMAT).date()
        days_until = (event_date - as_of).days
        enriched = dict(item)
        enriched["days_until"] = days_until
        events.append(enriched)

    events.sort(key=lambda item: (item["days_until"], -item["importance"]))
    type_counts = Counter(item["type"] for item in events)
    priority_items = [
        item for item in events if item["importance"] >= 4 and 0 <= item["days_until"] <= 14
    ]

    return {
        "upcoming_events": events,
        "event_summary": {
            "event_count": len(events),
            "type_counts": dict(type_counts),
        },
        "priority_items": priority_items,
    }


def main():
    parser = argparse.ArgumentParser(description="Track and prioritize upcoming market events.")
    parser.add_argument("input_path")
    args = parser.parse_args()
    data = json.loads(Path(args.input_path).read_text(encoding="utf-8"))
    print(json.dumps(generate_report(data), indent=2))


if __name__ == "__main__":
    main()
