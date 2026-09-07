#!/usr/bin/env python3
"""Read-only instruction audit; policy limits are repository choices, not model limits.

Scan every canonical entry and its Markdown resources without executing them.
This catches concrete regressions, not semantic correctness or model performance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
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
    "unconditional_merge_gate": re.compile(r"Merge step is always Ask First|Ask First on MERGE", re.I),
}

# Review hints deliberately do not fail CI: an approval may protect a real boundary,
# and a code block may be either an executable prompt template or a counterexample.
REVIEW_HINTS = {
    "approval_scope": re.compile(r"always.*(?:approval|confirm|ask first)|every state-changing step is a proposal|必须反复确认", re.I),
    "verification_scope": re.compile(r"every change|regardless of.*(?:skill|simplicity)|每次.*全量", re.I),
    "host_dependency": re.compile(r"AskUserQuestion|TodoWrite|context: fork|disable-model-invocation|\$ARGUMENTS|spawn_agent"),
}


def regular_files(directory: Path):
    """Inventory actual files, never follow symlinked files or directories."""
    if directory.is_symlink():
        return
    for parent, directories, files in os.walk(directory, followlinks=False):
        # Match the installer: interpreter caches are runtime outputs, not bundled
        # artifacts. Including them makes the report change after running tests.
        directories[:] = sorted(d for d in directories if d != "__pycache__" and not (Path(parent) / d).is_symlink())
        for name in sorted(files):
            path = Path(parent) / name
            if not path.is_symlink() and path.is_file():
                yield path


def inspect_resource(path: Path, root: Path) -> dict:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8") if b"\x00" not in data else None
    except UnicodeDecodeError:
        text = None
    markdown = path.suffix.lower() == ".md"
    findings, hints = [], []
    if text is not None:
        if markdown:
            for line, value in prose_lines(text):
                for rule, pattern in RULES.items():
                    if pattern.search(value):
                        findings.append({"rule": rule, "path": path.relative_to(root).as_posix(), "line": line})
        for line, value in enumerate(text.splitlines(), 1):
            for rule, pattern in REVIEW_HINTS.items():
                if pattern.search(value):
                    hints.append({"rule": rule, "line": line})
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data), "kind": "markdown" if markdown else "text" if text is not None else "binary",
        "findings": findings, "review_hints": hints,
        "semantic_review": "not_assessed",
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
    if re.match(r"(?:>\s*Skill Type:|Name:.*\bTier:|Tier:\s*POWERFUL)", description):
        findings.append({"rule": "metadata_as_description", "path": path.relative_to(root).as_posix(), "line": 1})
    if len(text.splitlines()) > ENTRY_LINE_LIMIT:
        findings.append({"rule": "entry_budget", "path": path.relative_to(root).as_posix(), "line": 1})
    resources = [inspect_resource(p, root) for p in sorted(regular_files(path.parent))]
    for resource in resources:
        findings.extend(resource["findings"])
    return {
        "name": path.parent.name,
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
        "entry_lines": len(text.splitlines()),
        "entry_chars": len(text),
        "description_chars": len(description),
        "markdown_resources": sum(r["kind"] == "markdown" for r in resources),
        "resources": resources,
        "findings": findings,
    }


def audit(root: Path) -> dict:
    paths = sorted(p for p in (root / "skills").glob("*/*/SKILL.md")
                   if not any(part.is_symlink() for part in (p, p.parent, p.parent.parent)))
    skills = [inspect_skill(path, root) for path in paths]
    # Shared entrypoints and maintenance workflows sit outside the skill tree.
    shared = [root / name for name in ("AGENTS.md", "CLAUDE.md", "docs/maintenance-workflow.md", "docs/astra-skill-guidance.md", "docs/cross-agent-compatibility.md")]
    shared.extend(regular_files(root / ".github" / "workflows"))
    for parent, directories, names in os.walk(root, followlinks=False):
        directories[:] = sorted(d for d in directories if d not in {".git", "skills", "openclaw-skills", "node_modules", ".venv", "__pycache__"} and not (Path(parent)/d).is_symlink())
        shared.extend(Path(parent)/name for name in names if name.lower() in {"agents.md", "agents.override.md", "claude.md", "gemini.md"})
    repository_files = [inspect_resource(p, root) for p in sorted(set(shared)) if p.is_file() and not p.is_symlink()]
    return {
        "schema_version": 1,
        "scope": "canonical skills and all bundled files, shared instructions and CI workflows; static checks only",
        "limits": {"description_chars": DESCRIPTION_LIMIT, "entry_lines": ENTRY_LINE_LIMIT},
        "summary": {
            "skills": len(skills),
            "findings": sum(len(item["findings"]) for item in skills + repository_files),
            "files": sum(len(item["resources"]) for item in skills) + len(repository_files),
            "review_hints": sum(len(r["review_hints"]) for item in skills for r in item["resources"]) + sum(len(r["review_hints"]) for r in repository_files),
            "entry_chars": sum(item["entry_chars"] for item in skills),
            "description_chars": sum(item["description_chars"] for item in skills),
        },
        "skills": skills,
        "repository_files": repository_files,
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
        for item in report["skills"] + report["repository_files"]:
            for finding in item["findings"]:
                print(f"{finding['path']}:{finding['line']}: {finding['rule']}")
        print(json.dumps(report["summary"], ensure_ascii=False))
    return int(not report["summary"]["skills"] or bool(report["summary"]["findings"]))


if __name__ == "__main__":
    raise SystemExit(main())
