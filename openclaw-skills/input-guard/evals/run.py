#!/usr/bin/env python3
"""
Input Guard Eval Runner — Runs test cases against the scanner and reports results.

Usage:
    python3 evals/run.py                      # Pattern-only tests
    python3 evals/run.py --llm                # Include LLM tests for evasive cases
    python3 evals/run.py --llm --verbose      # Show full details
    python3 evals/run.py --category evasive   # Run only evasive test cases
    python3 evals/run.py --id emerald-box     # Run a single test by id
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

EVALS_DIR = Path(__file__).parent
PROJECT_DIR = EVALS_DIR.parent
CASES_FILE = EVALS_DIR / "cases.json"
SCRIPTS_DIR = PROJECT_DIR / "scripts"
SCAN_PY = SCRIPTS_DIR / "scan.py"
ENV_FILE = PROJECT_DIR / ".env"

SEVERITY_ORDER = {"SAFE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def load_env():
    """Load .env file into os.environ (simple parser, no dependency)."""
    if not ENV_FILE.exists():
        return
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if value and key not in os.environ:
                os.environ[key] = value


def load_cases(filter_category=None, filter_id=None):
    with open(CASES_FILE) as f:
        cases = json.load(f)

    if filter_id:
        cases = [c for c in cases if filter_id in c["id"]]
    if filter_category:
        cases = [c for c in cases if c["category"] == filter_category]

    return cases


def run_scan(text, flags=None):
    """Run scan.py and return parsed JSON result."""
    load_env()
    cmd = [sys.executable, str(SCAN_PY), "--json"]
    if flags:
        cmd.extend(flags)
    cmd.append(text)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    stdout = result.stdout.strip()

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"severity": "ERROR", "score": -1, "error": stdout or result.stderr}


def check_severity_in_range(actual, min_sev, max_sev):
    """Check if actual severity falls within [min_sev, max_sev]."""
    actual_val = SEVERITY_ORDER.get(actual, -1)
    min_val = SEVERITY_ORDER.get(min_sev, 0)
    max_val = SEVERITY_ORDER.get(max_sev, 4)
    return min_val <= actual_val <= max_val


def run_evals(cases, use_llm=False, verbose=False):
    """Run all test cases and return results."""
    results = []
    total = 0
    passed = 0
    failed = 0
    errors = 0
    llm_tests = 0
    llm_passed = 0
    llm_failed = 0

    for case in cases:
        case_id = case["id"]
        category = case["category"]
        description = case["description"]

        # --- Pattern test ---
        if category != "evasive":
            total += 1
            min_sev = case["expected_min_severity"]
            max_sev = case["expected_max_severity"]

            start = time.time()
            result = run_scan(case["text"])
            elapsed = int((time.time() - start) * 1000)

            actual_sev = result.get("severity", "ERROR")

            if actual_sev == "ERROR":
                status = "ERROR"
                errors += 1
            elif check_severity_in_range(actual_sev, min_sev, max_sev):
                status = "PASS"
                passed += 1
            else:
                status = "FAIL"
                failed += 1

            emoji = {"PASS": "✅", "FAIL": "❌", "ERROR": "💥"}[status]
            print(f"  {emoji} {case_id}: {actual_sev} (expected {min_sev}-{max_sev}) [{elapsed}ms]")

            if verbose or status != "PASS":
                if status == "FAIL":
                    print(f"       Text: \"{case['text'][:80]}...\"")
                if verbose:
                    print(f"       Score: {result.get('score', '?')} | Findings: {len(result.get('findings', []))}")

            results.append({
                "id": case_id, "mode": "pattern", "status": status,
                "expected": f"{min_sev}-{max_sev}", "actual": actual_sev,
                "score": result.get("score"), "elapsed_ms": elapsed,
            })

        # --- Evasive test (pattern expected to miss, LLM should catch) ---
        elif category == "evasive":
            # First: verify patterns DON'T catch it (expected behavior)
            total += 1
            pattern_expected = case.get("pattern_expected", "SAFE")

            start = time.time()
            result = run_scan(case["text"])
            elapsed = int((time.time() - start) * 1000)
            actual_sev = result.get("severity", "ERROR")

            if actual_sev == pattern_expected:
                status = "PASS"
                passed += 1
                emoji = "✅"
            elif SEVERITY_ORDER.get(actual_sev, 0) > SEVERITY_ORDER.get(pattern_expected, 0):
                # Patterns caught it — even better than expected
                status = "PASS+"
                passed += 1
                emoji = "🎯"
            else:
                status = "FAIL"
                failed += 1
                emoji = "❌"

            print(f"  {emoji} {case_id} [pattern]: {actual_sev} (expected {pattern_expected}) [{elapsed}ms]")

            results.append({
                "id": case_id, "mode": "pattern", "status": status,
                "expected": pattern_expected, "actual": actual_sev,
                "score": result.get("score"), "elapsed_ms": elapsed,
            })

            # Then: test with LLM if requested
            if use_llm:
                llm_tests += 1
                llm_min = case.get("llm_expected_min_severity", "MEDIUM")
                llm_max = case.get("llm_expected_max_severity", "CRITICAL")

                start = time.time()
                llm_result = run_scan(case["text"], flags=["--llm"])
                elapsed = int((time.time() - start) * 1000)
                llm_actual = llm_result.get("severity", "ERROR")

                if llm_actual == "ERROR":
                    llm_status = "ERROR"
                    errors += 1
                elif check_severity_in_range(llm_actual, llm_min, llm_max):
                    llm_status = "PASS"
                    llm_passed += 1
                else:
                    llm_status = "FAIL"
                    llm_failed += 1

                emoji = {"PASS": "✅", "FAIL": "❌", "ERROR": "💥"}[llm_status]
                print(f"  {emoji} {case_id} [llm]:     {llm_actual} (expected {llm_min}-{llm_max}) [{elapsed}ms]")

                if verbose:
                    llm_data = llm_result.get("llm", {})
                    print(f"       Model: {llm_data.get('model', '?')} | Confidence: {llm_data.get('confidence', '?')}")
                    print(f"       Reasoning: {llm_data.get('reasoning', 'N/A')[:120]}")

                results.append({
                    "id": case_id, "mode": "llm", "status": llm_status,
                    "expected": f"{llm_min}-{llm_max}", "actual": llm_actual,
                    "score": llm_result.get("score"), "elapsed_ms": elapsed,
                })

    return results, total, passed, failed, errors, llm_tests, llm_passed, llm_failed


def main():
    parser = argparse.ArgumentParser(description="Input Guard Eval Runner")
    parser.add_argument("--llm", action="store_true", help="Run LLM tests for evasive cases")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--category", "-c", help="Filter by category (safe, pattern, evasive)")
    parser.add_argument("--id", help="Filter by case id (substring match)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    cases = load_cases(filter_category=args.category, filter_id=args.id)

    if not cases:
        print("No test cases found.")
        sys.exit(1)

    print(f"\n🧪 Input Guard Evals — {len(cases)} test cases")
    if args.llm:
        print("   LLM mode: ON (evasive cases will test pattern + LLM)")
    print(f"   Scanner: {SCAN_PY}")
    print()

    # Group by category
    categories = {}
    for case in cases:
        cat = case["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(case)

    all_results = []
    total_all = passed_all = failed_all = errors_all = 0
    llm_total = llm_pass = llm_fail = 0

    for cat_name, cat_cases in categories.items():
        label = {"safe": "🟢 Safe Content", "pattern": "🔴 Pattern Detection", "evasive": "🧠 Evasive Attacks"}
        print(f"── {label.get(cat_name, cat_name)} ({len(cat_cases)} cases) ──")

        results, total, passed, failed, errors, lt, lp, lf = run_evals(
            cat_cases, use_llm=args.llm, verbose=args.verbose
        )
        all_results.extend(results)
        total_all += total
        passed_all += passed
        failed_all += failed
        errors_all += errors
        llm_total += lt
        llm_pass += lp
        llm_fail += lf
        print()

    # Summary
    print("═" * 50)
    print(f"  Pattern tests: {passed_all}/{total_all} passed", end="")
    if failed_all:
        print(f" ({failed_all} failed)", end="")
    if errors_all:
        print(f" ({errors_all} errors)", end="")
    print()

    if llm_total:
        print(f"  LLM tests:     {llm_pass}/{llm_total} passed", end="")
        if llm_fail:
            print(f" ({llm_fail} failed)", end="")
        print()

    overall_pass = failed_all == 0 and errors_all == 0 and llm_fail == 0
    print(f"\n  {'✅ ALL TESTS PASSED' if overall_pass else '❌ SOME TESTS FAILED'}")
    print("═" * 50)

    if args.json:
        print(json.dumps(all_results, indent=2))

    sys.exit(0 if overall_pass else 1)


if __name__ == "__main__":
    main()
