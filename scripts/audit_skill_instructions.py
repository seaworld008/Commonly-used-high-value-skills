#!/usr/bin/env python3
"""Read-only instruction audit; policy limits are repository choices, not model limits.

Scan every canonical entry and its Markdown resources without executing them.
This catches concrete regressions, not semantic correctness or model performance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import yaml

DESCRIPTION_LIMIT = 240
ENTRY_LINE_LIMIT = 500
RULES = {
    "probability_trigger": re.compile(r"(?:even (?:a|an) )?1% chance.*skill", re.I),
    "universal_invocation": re.compile(r"requiring skill invocation before ANY response", re.I),
    "model_authoring_override": re.compile(r"Author for Opus [\d.]+ defaults", re.I),
    "foreign_engine_override": re.compile(r"Author for the executing engine.*bind only on Opus", re.I),
    "missing_shared_protocol": re.compile(r"Spine contracts.*in effect on every run", re.I),
    "unconditional_design_gate": re.compile(r"This applies to EVERY project regardless of perceived simplicity", re.I),
    "message_bound_verification": re.compile(r"haven't run the verification command in this message", re.I),
}


def prose_lines(text: str):
    """Skip fenced examples while retaining source line numbers and real prose."""
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            yield number, line


def inspect_skill(path: Path, root: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    findings = []
    match = re.match(r"\A---\s*\n(.*?)\n---(?:\n|$)", text, re.S)
    metadata = {}
    try:
        parsed = yaml.safe_load(match.group(1)) if match else None
        if not isinstance(parsed, dict):
            raise ValueError("missing mapping frontmatter")
        metadata = parsed
    except (yaml.YAMLError, ValueError):
        findings.append({"rule": "frontmatter", "path": path.relative_to(root).as_posix(), "line": 1})
    description = metadata.get("description", "")
    if not isinstance(description, str) or not description.strip():
        findings.append({"rule": "missing_description", "path": path.relative_to(root).as_posix(), "line": 1})
        description = ""
    if len(description) > DESCRIPTION_LIMIT:
        findings.append({"rule": "description_budget", "path": path.relative_to(root).as_posix(), "line": 1})
    if description.startswith("Tags:"):
        findings.append({"rule": "tags_as_description", "path": path.relative_to(root).as_posix(), "line": 1})
    if len(text.splitlines()) > ENTRY_LINE_LIMIT:
        findings.append({"rule": "entry_budget", "path": path.relative_to(root).as_posix(), "line": 1})
    resources = sorted(p for p in path.parent.rglob("*.md") if not p.is_symlink())
    for resource in resources:
        # Do not follow symlinked directories into unrelated workspace data.
        if any((path.parent / parent).is_symlink()
               for parent in resource.relative_to(path.parent).parents):
            continue
        for line, value in prose_lines(resource.read_text(encoding="utf-8")):
            for rule, pattern in RULES.items():
                if pattern.search(value):
                    findings.append({"rule": rule, "path": resource.relative_to(root).as_posix(), "line": line})
    return {
        "name": path.parent.name,
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
        "entry_lines": len(text.splitlines()),
        "entry_chars": len(text),
        "description_chars": len(description),
        "markdown_resources": len(resources),
        "findings": findings,
    }


def audit(root: Path) -> dict:
    paths = sorted(p for p in (root / "skills").glob("*/*/SKILL.md")
                   if not any(part.is_symlink() for part in (p, p.parent, p.parent.parent)))
    skills = [inspect_skill(path, root) for path in paths]
    return {
        "schema_version": 1,
        "scope": "canonical entries and bundled Markdown; static checks only",
        "limits": {"description_chars": DESCRIPTION_LIMIT, "entry_lines": ENTRY_LINE_LIMIT},
        "summary": {
            "skills": len(skills),
            "findings": sum(len(item["findings"]) for item in skills),
            "entry_chars": sum(item["entry_chars"] for item in skills),
            "description_chars": sum(item["description_chars"] for item in skills),
        },
        "skills": skills,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true", help="Print deterministic JSON; never write repository files")
    args = parser.parse_args(argv)
    report = audit(args.repo_root.resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in report["skills"]:
            for finding in item["findings"]:
                print(f"{finding['path']}:{finding['line']}: {finding['rule']}")
        print(json.dumps(report["summary"], ensure_ascii=False))
    return int(not report["summary"]["skills"] or bool(report["summary"]["findings"]))


if __name__ == "__main__":
    raise SystemExit(main())
