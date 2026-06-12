#!/usr/bin/env python3
"""Lightweight NL artifact checks inspired by NLPM.

This script is intentionally smaller than upstream NLPM. It gives the curated
skill a practical local checker for common deterministic and semi-deterministic
issues without depending on Claude Code or external packages.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
VERSION = "1.1.0"
VAGUE_TERMS = (
    "appropriate",
    "relevant",
    "as needed",
    "sufficient",
    "adequate",
    "reasonable",
    "properly",
    "correctly",
    "some",
    "several",
    "various",
)
RISKY_COMMAND_PATTERNS = (
    (r"\bcurl\b.*\|\s*(?:sh|bash|pwsh|powershell)\b", "Piped remote script execution"),
    (r"\bInvoke-WebRequest\b.*\|\s*(?:iex|Invoke-Expression)\b", "PowerShell remote script execution"),
    (r"\bchmod\s+777\b", "World-writable permission"),
    (r"\brm\s+-rf\s+(?:/|\$HOME|~)\b", "Broad destructive delete"),
    (r"\b[A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY)\s*=", "Possible inline secret"),
)
PENALTIES = {
    "manifest/json": 25,
    "manifest/path": 20,
    "manifest-disk-diff": 20,
    "manifest/unregistered": 20,
    "skill/frontmatter": 25,
    "skill/name": 20,
    "skill/name-parent": 20,
    "skill/description": 25,
    "skill/trigger-description": 15,
    "skill/line-budget": 8,
    "skill/examples": 10,
    "memory/test-command": 8,
    "memory/project-map": 5,
    "memory/import": 20,
    "security/executable-risk": 20,
    "security/mcp-command": 12,
    "security/hook-command": 12,
    "vague-language": 6,
}


@dataclass
class Finding:
    severity: str
    rule: str
    path: str
    line: int
    message: str
    fix: str


@dataclass
class Artifact:
    path: str
    type: str
    lines: int


@dataclass
class FileScore:
    path: str
    type: str
    score: int
    band: str
    penalties: int
    findings: int


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def iter_files(root: Path):
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def classify(path: Path, root: Path) -> str | None:
    rel_path = rel(path, root)
    parts = rel_path.replace("\\", "/").split("/")
    name = path.name
    if name == "SKILL.md":
        return "skill"
    if name in {"AGENTS.md", "CLAUDE.md", "GEMINI.md"}:
        return "memory"
    if len(parts) >= 2 and parts[0] in {"commands", ".claude"} and name.endswith(".md"):
        if "/commands/shared/" in "/" + rel_path.replace("\\", "/"):
            return "shared-partial"
        if "commands" in parts:
            return "command"
    if len(parts) >= 2 and parts[0] in {"agents", ".claude"} and name.endswith(".md"):
        if "agents" in parts:
            return "agent"
    if "/rules/" in "/" + rel_path.replace("\\", "/") and name.endswith(".md"):
        return "rule"
    if name == "plugin.json":
        return "manifest"
    if name == "marketplace.json":
        return "marketplace"
    if name in {"hooks.json", "settings.json", "settings.local.json"}:
        return "hook-or-settings"
    if name in {".mcp.json", ".lsp.json"}:
        return name.strip(".")
    if path.suffix.lower() in {".md", ".txt"} and any(part in {"prompts", "prompt"} for part in parts):
        return "prompt"
    return None


def discover_artifacts(root: Path) -> list[Artifact]:
    artifacts: list[Artifact] = []
    for path in iter_files(root):
        artifact_type = classify(path, root)
        if artifact_type is None:
            continue
        try:
            line_count = len(read_text(path).splitlines())
        except OSError:
            line_count = 0
        artifacts.append(Artifact(rel(path, root), artifact_type, line_count))
    return sorted(artifacts, key=lambda item: item.path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def frontmatter(text: str) -> dict[str, str] | None:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, flags=re.DOTALL)
    if not match:
        return None
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value:
            fields[key.strip()] = value.strip('"').strip("'")
    return fields


def line_number(text: str, pattern: str) -> int:
    regex = re.compile(pattern, flags=re.IGNORECASE)
    for index, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return index
    return 0


def count_trigger_phrases(description: str) -> int:
    candidates = re.split(r"[,.;]|\bwhen\b|\buse\b|\bor\b", description, flags=re.IGNORECASE)
    return sum(1 for item in candidates if len(item.strip().split()) >= 3)


def check_skill(path: Path, root: Path, findings: list[Finding]) -> None:
    text = read_text(path)
    fm = frontmatter(text)
    rel_path = rel(path, root)
    if fm is None:
        findings.append(Finding("high", "skill/frontmatter", rel_path, 1, "SKILL.md missing YAML frontmatter", "Add name and description frontmatter."))
        return

    name = fm.get("name", "")
    if not name:
        findings.append(Finding("high", "skill/name", rel_path, 1, "SKILL.md missing required name", f"Set name: {path.parent.name}."))
    elif name != path.parent.name:
        findings.append(Finding("high", "skill/name-parent", rel_path, line_number(text, r"^name:"), f"name '{name}' does not match directory '{path.parent.name}'", f"Rename the directory or set name: {path.parent.name}."))

    description = fm.get("description", "")
    if not description:
        findings.append(Finding("high", "skill/description", rel_path, 1, "SKILL.md missing required description", "Add a trigger-oriented description."))
    elif count_trigger_phrases(description) <= 1:
        findings.append(Finding("medium", "skill/trigger-description", rel_path, line_number(text, r"^description:"), "Description looks generic; it has too few trigger phrases", "Name real user intents and adjacent contexts."))

    lines = text.splitlines()
    if len(lines) > 500:
        findings.append(Finding("medium", "skill/line-budget", rel_path, 0, f"Skill has {len(lines)} lines; consider progressive disclosure", "Move detailed tables into references/."))

    if "```" not in text and len(lines) > 80:
        findings.append(Finding("medium", "skill/examples", rel_path, 0, "Long skill has no code or structured example block", "Add concrete examples or templates."))


def check_memory_file(path: Path, root: Path, findings: list[Finding]) -> None:
    text = read_text(path)
    rel_path = rel(path, root)
    lower = text.lower()
    if not any(term in lower for term in ("test", "pytest", "unittest", "npm test", "pnpm test")):
        findings.append(Finding("medium", "memory/test-command", rel_path, 0, "Memory file does not mention how to run tests", "Add the project test command."))
    if not any(term in lower for term in ("build", "run", "start", "dev server", "architecture")):
        findings.append(Finding("low", "memory/project-map", rel_path, 0, "Memory file may lack build/run or architecture guidance", "Add build/run commands and a short project map."))

    for match in re.finditer(r"@([A-Za-z0-9_./\\-]+)", text):
        target = (path.parent / match.group(1)).resolve()
        if not target.exists():
            findings.append(Finding("high", "memory/import", rel_path, text[: match.start()].count("\n") + 1, f"Referenced path @{match.group(1)} does not exist", "Fix or remove the reference."))


def check_vague_terms(path: Path, root: Path, findings: list[Finding]) -> None:
    text = read_text(path)
    rel_path = rel(path, root)
    if path.name == "nl_artifact_check.py":
        return
    hits = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        lower = stripped.lower()
        if "vague term" in lower or "vague quantifier" in lower:
            continue
        if lower.startswith("|") and any(term in lower for term in ("r01", "vague", "empty intensifier")):
            continue
        for term in VAGUE_TERMS:
            pattern = r"\b" + re.escape(term) + r"\b"
            if re.search(pattern, line, flags=re.IGNORECASE):
                hits.append(term)
    if len(hits) >= 3:
        findings.append(Finding("low", "vague-language", rel_path, 0, f"Contains vague terms: {', '.join(sorted(set(hits)))}", "Replace with measurable criteria where these terms affect behavior."))


def check_manifests(root: Path, findings: list[Finding]) -> None:
    for manifest in iter_files(root):
        if manifest.name not in {"plugin.json", "marketplace.json"}:
            continue
        try:
            data = json.loads(read_text(manifest))
        except json.JSONDecodeError as exc:
            findings.append(Finding("high", "manifest/json", rel(manifest, root), exc.lineno, "Manifest is not valid JSON", "Fix JSON syntax."))
            continue
        if not isinstance(data, dict):
            continue
        for key in ("skills", "agents", "commands", "hooks", "mcpServers"):
            value = data.get(key)
            values = [value] if isinstance(value, str) else value if isinstance(value, list) else []
            for item in values:
                if not isinstance(item, str) or item.startswith(("http://", "https://")):
                    continue
                if Path(item).is_absolute():
                    findings.append(Finding("high", "manifest/path", rel(manifest, root), 0, f"{key} path is absolute: {item}", "Use a repository-relative path."))
                    continue
                target = (manifest.parent.parent if manifest.parent.name.startswith(".") else manifest.parent) / item
                if not target.exists():
                    findings.append(Finding("high", "manifest-disk-diff", rel(manifest, root), 0, f"{key} path does not exist: {item}", "Create the file or remove the manifest entry."))


def manifest_declared_files(manifest: Path, key: str, value: object) -> set[Path]:
    values = [value] if isinstance(value, str) else value if isinstance(value, list) else []
    base = manifest.parent.parent if manifest.parent.name.startswith(".") else manifest.parent
    registered: set[Path] = set()
    for item in values:
        if not isinstance(item, str) or item.startswith(("http://", "https://")) or Path(item).is_absolute():
            continue
        target = (base / item).resolve()
        if target.is_dir():
            pattern = "SKILL.md" if key == "skills" else "*.md"
            for child in target.rglob(pattern):
                if not any(part in SKIP_DIRS for part in child.parts):
                    registered.add(child.resolve())
        elif target.is_file():
            registered.add(target.resolve())
    return registered


def check_unregistered_components(root: Path, findings: list[Finding]) -> None:
    for manifest in iter_files(root):
        if manifest.name != "plugin.json":
            continue
        try:
            data = json.loads(read_text(manifest))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        base = manifest.parent.parent if manifest.parent.name.startswith(".") else manifest.parent
        checks = {
            "skills": list(base.rglob("SKILL.md")),
            "agents": list((base / "agents").rglob("*.md")) if (base / "agents").is_dir() else [],
            "commands": list((base / "commands").rglob("*.md")) if (base / "commands").is_dir() else [],
        }
        for key, on_disk in checks.items():
            declared = data.get(key)
            if declared is None:
                continue
            registered = manifest_declared_files(manifest, key, declared)
            for disk_path in on_disk:
                if any(part in SKIP_DIRS for part in disk_path.parts):
                    continue
                if key == "commands" and "shared" in disk_path.parts:
                    continue
                if disk_path.resolve() not in registered:
                    findings.append(Finding(
                        "high",
                        "manifest/unregistered",
                        rel(disk_path, root),
                        0,
                        f"{key[:-1]} exists on disk but is not registered by {rel(manifest, root)}",
                        f"Add {rel(disk_path, base)} to plugin.json `{key}` or include its parent directory.",
                    ))


def check_security_files(root: Path, findings: list[Finding]) -> None:
    for path in iter_files(root):
        rel_path = rel(path, root)
        lower_name = path.name.lower()
        if not (
            path.suffix.lower() in {".sh", ".bash", ".ps1", ".py", ".js", ".ts", ".json", ".toml", ".yaml", ".yml"}
            or lower_name in {"hooks.json", "settings.json", ".mcp.json"}
        ):
            continue
        try:
            text = read_text(path)
        except OSError:
            continue
        for pattern, label in RISKY_COMMAND_PATTERNS:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                findings.append(Finding(
                    "high" if "SECRET" in pattern or "TOKEN" in pattern else "medium",
                    "security/executable-risk",
                    rel_path,
                    text[: match.start()].count("\n") + 1,
                    label,
                    "Review the executable path, pin remote sources, and remove inline secrets or broad destructive commands.",
                ))
        if lower_name in {"hooks.json", "settings.json", ".mcp.json"}:
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue
            serialized = json.dumps(data)
            if re.search(r'"command"\s*:', serialized):
                rule = "security/mcp-command" if lower_name == ".mcp.json" else "security/hook-command"
                findings.append(Finding(
                    "medium",
                    rule,
                    rel_path,
                    0,
                    "Executable command entry present in hook, settings, or MCP config",
                    "Review command arguments, environment exposure, fail-open/fail-closed behavior, and least privilege.",
                ))


def scan(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    check_manifests(root, findings)
    check_unregistered_components(root, findings)
    check_security_files(root, findings)
    for path in iter_files(root):
        if path.name == "SKILL.md":
            check_skill(path, root, findings)
        elif path.name in {"AGENTS.md", "CLAUDE.md", "GEMINI.md"}:
            check_memory_file(path, root, findings)
        if path.suffix.lower() in {".md", ".txt"}:
            check_vague_terms(path, root, findings)
    return findings


def score_band(score: int) -> str:
    if score >= 90:
        return "EXCELLENT"
    if score >= 80:
        return "GOOD"
    if score >= 70:
        return "ADEQUATE"
    if score >= 60:
        return "WEAK"
    return "REWRITE"


def score_files(artifacts: list[Artifact], findings: list[Finding]) -> list[FileScore]:
    by_path: dict[str, list[Finding]] = {}
    for finding in findings:
        by_path.setdefault(finding.path, []).append(finding)
    scores: list[FileScore] = []
    for artifact in artifacts:
        penalties = sum(PENALTIES.get(item.rule, 5) for item in by_path.get(artifact.path, []))
        score = max(0, 100 - penalties)
        scores.append(FileScore(
            artifact.path,
            artifact.type,
            score,
            score_band(score),
            penalties,
            len(by_path.get(artifact.path, [])),
        ))
    return scores


def summary(findings: list[Finding], artifacts: list[Artifact], scores: list[FileScore]) -> dict[str, object]:
    return {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifacts": len(artifacts),
        "average_score": round(sum(item.score for item in scores) / len(scores), 1) if scores else None,
        "high": sum(1 for item in findings if item.severity == "high"),
        "medium": sum(1 for item in findings if item.severity == "medium"),
        "low": sum(1 for item in findings if item.severity == "low"),
    }


def render_markdown(root: Path, artifacts: list[Artifact], findings: list[Finding], scores: list[FileScore]) -> str:
    data = summary(findings, artifacts, scores)
    high = data["high"]
    medium = data["medium"]
    low = data["low"]
    average = data["average_score"]
    decision = "BLOCKED" if high else "PASS WITH FIXES" if medium or low else "PASS"
    lines = [
        "## NL Artifact Audit",
        "",
        "### Decision",
        str(decision),
        "",
        "### Summary",
        f"- Target: `{root}`",
        f"- Artifacts scanned: {data['artifacts']}",
        f"- Average score: {average if average is not None else 'n/a'}",
        f"- Findings: {high} high | {medium} medium | {low} low",
        "",
        "### Inventory",
        "| Type | Count |",
        "|---|---:|",
    ]
    counts: dict[str, int] = {}
    for artifact in artifacts:
        counts[artifact.type] = counts.get(artifact.type, 0) + 1
    for artifact_type, count in sorted(counts.items()):
        lines.append(f"| {artifact_type} | {count} |")

    lines.extend(["", "### Quality Scores", "| File | Type | Score | Band | Findings |", "|---|---|---:|---|---:|"])
    for item in sorted(scores, key=lambda score: (score.score, score.path)):
        lines.append(f"| `{item.path}` | {item.type} | {item.score} | {item.band} | {item.findings} |")

    lines.extend(["", "### Findings", "| Severity | Rule | File | Line | Finding | Fix |", "|---|---|---|---:|---|---|"])
    if findings:
        order = {"high": 0, "medium": 1, "low": 2}
        for item in sorted(findings, key=lambda finding: (order.get(finding.severity, 9), finding.path, finding.rule)):
            line = item.line if item.line else ""
            message = item.message.replace("|", "\\|")
            fix = item.fix.replace("|", "\\|")
            lines.append(f"| {item.severity} | {item.rule} | `{item.path}` | {line} | {message} | {fix} |")
    else:
        lines.append("| - | - | - | - | No findings | - |")

    lines.extend([
        "",
        "### CI Recommendation",
        "- Fail CI on high findings from this script.",
        "- Treat medium and low findings as review items unless the repository opts into `--strict`.",
        "- For Claude Code plugin releases, periodically compare with upstream `nlpm-check` pinned to a reviewed commit.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--markdown", action="store_true", help="Emit an NLPM-style Markdown audit report.")
    parser.add_argument("--output", help="Write JSON or Markdown output to this path instead of stdout.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on any finding, not only high severity.")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    artifacts = discover_artifacts(root)
    findings = scan(root)
    scores = score_files(artifacts, findings)
    summary_data = summary(findings, artifacts, scores)

    if args.markdown:
        output = render_markdown(root, artifacts, findings, scores)
    elif args.json:
        output = json.dumps({
            "summary": summary_data,
            "artifacts": [asdict(item) for item in artifacts],
            "scores": [asdict(item) for item in scores],
            "findings": [asdict(item) for item in findings],
        }, indent=2)
    else:
        output_lines = [f"NL artifact check: {summary_data['high']} high, {summary_data['medium']} medium, {summary_data['low']} low; artifacts {summary_data['artifacts']}; average score {summary_data['average_score']}"]
        for item in findings:
            location = item.path if item.line == 0 else f"{item.path}:{item.line}"
            output_lines.append(f"[{item.severity}] {item.rule} {location}")
            output_lines.append(f"  {item.message}")
            output_lines.append(f"  fix: {item.fix}")
        output = "\n".join(output_lines) + "\n"

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")

    if summary_data["high"] or (args.strict and findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
