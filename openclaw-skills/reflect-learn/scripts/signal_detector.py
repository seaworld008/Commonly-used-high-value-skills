#!/usr/bin/env python3
"""
Signal Detector for Reflect Skill

Detects correction signals and learning opportunities in conversation text.
Classifies signals by confidence level (HIGH, MEDIUM, LOW) and category.

Usage:
    python signal_detector.py --input conversation.txt
    python signal_detector.py --test  # Run self-tests
"""

import re
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Confidence(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Category(Enum):
    CODE_STYLE = "Code Style"
    ARCHITECTURE = "Architecture"
    PROCESS = "Process"
    DOMAIN = "Domain"
    TOOLS = "Tools"
    SECURITY = "Security"
    NEW_SKILL = "New Skill"
    UNKNOWN = "Unknown"


@dataclass
class Signal:
    """A detected signal from conversation."""
    signal: str
    confidence: Confidence
    source_quote: str
    category: Category
    line_number: Optional[int] = None


# High confidence patterns - explicit corrections
HIGH_PATTERNS = [
    # Negative directives
    (r"\b(never|don't|do not|stop doing|wrong|not like that|incorrect)\b", "correction"),
    (r"\b(should not|shouldn't|must not|mustn't)\b", "prohibition"),
    # Positive directives
    (r"\b(always|must|required|the rule is|correct way)\b", "requirement"),
    # Frustration markers
    (r"(I already told you|again\?|not again|how many times)", "frustration"),
    # Explicit rules
    (r"(the rule is|you should know|remember that|don't forget)", "explicit_rule"),
]

# Medium confidence patterns - approved approaches
MEDIUM_PATTERNS = [
    (r"\b(perfect|exactly|that's right|yes, like that|correct)\b", "approval"),
    (r"\b(good|great job|well done|nice|excellent)\b", "positive_feedback"),
    (r"\b(keep doing|continue with|stick with)\b", "continuation"),
]

# Low confidence patterns - observations
LOW_PATTERNS = [
    (r"\b(maybe|perhaps|might want to|consider)\b", "suggestion"),
    (r"\b(seems like|appears to|looks like)\b", "observation"),
    (r"\b(interesting|good idea|could work)\b", "tentative"),
]

# Category detection patterns
CATEGORY_PATTERNS = {
    Category.CODE_STYLE: [
        r"\b(naming|convention|style|format|indent|case|camelCase|snake_case|PascalCase)\b",
        r"\b(variable|function|class|method|parameter)\s+name",
        r"\b(TypeScript|JavaScript|Python|Go|Rust|Java)\b",
        r"\b(var|const|let|type|interface|enum)\b",
        r"\b(semicolon|quote|string|bracket|brace)\b",
    ],
    Category.ARCHITECTURE: [
        r"\b(pattern|architecture|design|structure|module|component)\b",
        r"\b(separation|coupling|cohesion|dependency|layer)\b",
    ],
    Category.PROCESS: [
        r"\b(workflow|process|step|procedure|protocol)\b",
        r"\b(commit|branch|merge|review|deploy)\b",
    ],
    Category.DOMAIN: [
        r"\b(business|domain|logic|rule|requirement)\b",
        r"\b(customer|user|client|account|order)\b",
    ],
    Category.TOOLS: [
        r"\b(tool|cli|command|terminal|shell|git|npm|docker)\b",
        r"\b(config|setting|environment|variable)\b",
    ],
    Category.SECURITY: [
        r"\b(security|vulnerability|exploit|injection|xss|csrf)\b",
        r"\b(password|secret|credential|token|key)\s+(expos|leak|hardcod)",
        r"\b(validation|sanitiz|escap|encrypt|hash)\b",
        r"\b(OWASP|CVE|RLS|row.level.security)\b",
    ],
    Category.NEW_SKILL: [
        r"\b(workaround|trick|hack|solution|fix|debug)\b",
        r"\b(error|bug|issue|problem)\s+(was|is|fixed|solved)\b",
        r"(took|spent)\s+\d+\s*(min|hour|day)",  # Time investment indicates non-trivial
    ],
}


def detect_confidence(text: str) -> tuple[Confidence, str]:
    """Detect confidence level from text patterns."""
    text_lower = text.lower()

    # Check high confidence patterns
    for pattern, pattern_type in HIGH_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return Confidence.HIGH, pattern_type

    # Check medium confidence patterns
    for pattern, pattern_type in MEDIUM_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return Confidence.MEDIUM, pattern_type

    # Check low confidence patterns
    for pattern, pattern_type in LOW_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return Confidence.LOW, pattern_type

    return Confidence.LOW, "observation"


def detect_category(text: str) -> Category:
    """Detect category from text content."""
    text_lower = text.lower()

    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return category

    return Category.UNKNOWN


def extract_quote(text: str, max_length: int = 100) -> str:
    """Extract a representative quote from the text."""
    # Clean up the text
    text = text.strip()

    # If short enough, return as-is
    if len(text) <= max_length:
        return text

    # Try to find a sentence boundary
    sentences = re.split(r'[.!?]', text)
    if sentences and len(sentences[0]) <= max_length:
        return sentences[0].strip() + "..."

    # Truncate at word boundary
    truncated = text[:max_length].rsplit(' ', 1)[0]
    return truncated + "..."


def extract_learning(text: str) -> str:
    """Extract the core learning from the text."""
    # Remove common prefixes
    prefixes = [
        r"^(you should|always|never|don't|do not|stop|remember to)\s+",
        r"^(the rule is|note that|keep in mind)\s+",
    ]

    result = text.strip()
    for prefix in prefixes:
        result = re.sub(prefix, "", result, flags=re.IGNORECASE)

    # Capitalize first letter
    if result:
        result = result[0].upper() + result[1:]

    return result


def detect_signals(conversation: str) -> list[Signal]:
    """
    Detect all signals in a conversation.

    Args:
        conversation: Full conversation text

    Returns:
        List of detected signals with confidence and category
    """
    signals = []

    # Split into lines for line number tracking
    lines = conversation.split('\n')

    for line_num, line in enumerate(lines, 1):
        # Skip empty lines
        if not line.strip():
            continue

        # Detect confidence
        confidence, pattern_type = detect_confidence(line)

        # Detect category
        category = detect_category(line)

        # Include signal if:
        # 1. We found a HIGH or MEDIUM confidence pattern
        # 2. OR we detected a specific category (even with LOW confidence)
        # 3. OR it's a NEW_SKILL category (workarounds, fixes)
        if pattern_type == "observation" and confidence == Confidence.LOW:
            # For generic observations, only include if we detected a specific category
            if category == Category.UNKNOWN:
                continue

        # Extract the learning
        learning = extract_learning(line)

        # Extract quote
        quote = extract_quote(line)

        signal = Signal(
            signal=learning,
            confidence=confidence,
            source_quote=quote,
            category=category,
            line_number=line_num
        )

        signals.append(signal)

    # Deduplicate similar signals
    signals = deduplicate_signals(signals)

    return signals


def deduplicate_signals(signals: list[Signal]) -> list[Signal]:
    """Remove duplicate or very similar signals."""
    seen = set()
    unique = []

    for signal in signals:
        # Create a normalized key
        key = signal.signal.lower().strip()
        key = re.sub(r'\s+', ' ', key)

        if key not in seen:
            seen.add(key)
            unique.append(signal)

    return unique


def format_signals_table(signals: list[Signal]) -> str:
    """Format signals as a markdown table."""
    if not signals:
        return "No signals detected."

    lines = [
        "| # | Signal | Confidence | Source Quote | Category |",
        "|---|--------|------------|--------------|----------|",
    ]

    for i, signal in enumerate(signals, 1):
        lines.append(
            f"| {i} | {signal.signal} | {signal.confidence.value} | "
            f"\"{signal.source_quote}\" | {signal.category.value} |"
        )

    return '\n'.join(lines)


def run_tests():
    """Run self-tests to verify pattern matching."""
    test_cases = [
        # High confidence - explicit directives
        ("Never use var in TypeScript", Confidence.HIGH, Category.CODE_STYLE),
        ("You should always validate inputs", Confidence.HIGH, Category.UNKNOWN),
        ("Stop doing that, it's wrong", Confidence.HIGH, Category.UNKNOWN),
        ("I already told you about this", Confidence.HIGH, Category.UNKNOWN),

        # Medium confidence - approvals
        ("Perfect, that's exactly what I wanted", Confidence.MEDIUM, Category.UNKNOWN),
        ("Yes, like that is correct", Confidence.MEDIUM, Category.UNKNOWN),
        ("Keep doing it this way", Confidence.MEDIUM, Category.UNKNOWN),

        # Category detection with implicit LOW confidence (detected by category only)
        # These don't have HIGH triggers but should be detected by category
        ("Use snake_case for Python variables", Confidence.LOW, Category.CODE_STYLE),
        ("The architecture should use dependency injection", Confidence.LOW, Category.ARCHITECTURE),

        # High confidence with category
        ("Always run tests before commit", Confidence.HIGH, Category.PROCESS),

        # New skill detection
        ("This workaround fixed the issue after 2 hours", Confidence.LOW, Category.NEW_SKILL),

        # Combined: HIGH confidence + category
        ("Never use var, always use const or let", Confidence.HIGH, Category.CODE_STYLE),
        ("The architecture must follow clean separation", Confidence.HIGH, Category.ARCHITECTURE),
    ]

    passed = 0
    failed = 0

    for text, expected_conf, expected_cat in test_cases:
        signals = detect_signals(text)

        if not signals:
            print(f"FAIL: No signal detected for: {text}")
            failed += 1
            continue

        signal = signals[0]

        conf_match = signal.confidence == expected_conf
        cat_match = signal.category == expected_cat or expected_cat == Category.UNKNOWN

        if conf_match and cat_match:
            print(f"PASS: {text}")
            passed += 1
        else:
            print(f"FAIL: {text}")
            print(f"  Expected: {expected_conf.value}, {expected_cat.value}")
            print(f"  Got: {signal.confidence.value}, {signal.category.value}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """CLI entry point."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description='Detect signals in conversation')
    parser.add_argument('--input', '-i', help='Input file to analyze')
    parser.add_argument('--test', action='store_true', help='Run self-tests')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    if args.test:
        success = run_tests()
        sys.exit(0 if success else 1)

    if not args.input:
        # Read from stdin
        text = sys.stdin.read()
    else:
        with open(args.input, 'r') as f:
            text = f.read()

    signals = detect_signals(text)

    if args.json:
        output = [
            {
                'signal': s.signal,
                'confidence': s.confidence.value,
                'source_quote': s.source_quote,
                'category': s.category.value,
                'line_number': s.line_number
            }
            for s in signals
        ]
        print(json.dumps(output, indent=2))
    else:
        print(format_signals_table(signals))


if __name__ == '__main__':
    main()
