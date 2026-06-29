#!/usr/bin/env python3
"""Audit the full skill portfolio and rank weak or risky skills.

This script is intentionally stricter than lint_skill_quality.py. The linter
answers "is this skill acceptable to commit?" while this audit answers "is this
skill strong enough to keep in a curated high-value portfolio?"
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILLS_DIR = REPO_ROOT / "skills"
DEFAULT_JSON = REPO_ROOT / "docs" / "sources" / "reports" / "skill-quality-audit.json"
DEFAULT_MARKDOWN = REPO_ROOT / "docs" / "sources" / "reports" / "skill-quality-audit.md"


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}

    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip().strip("'").strip('"')
    return data


def strip_frontmatter(text: str) -> str:
    return re.sub(r"^---.*?---\s*", "", text, count=1, flags=re.DOTALL)


def normalize_quality(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        return int(str(raw).strip())
    except ValueError:
        return None


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9_\u4e00-\u9fff]+", text))


@dataclass
class SkillAudit:
    name: str
    category: str
    path: str
    score: int
    action: str
    reasons: list[str]
    line_count: int
    word_count: int
    quality: int | None
    source: str
    license: str
    has_zh_description: bool
    code_blocks: int
    heading_count: int
    has_references: bool
    has_scripts: bool


def audit_skill(skill_md: Path) -> SkillAudit:
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(text)
    body = strip_frontmatter(text)
    name = fm.get("name", skill_md.parent.name)
    category = skill_md.parent.parent.name
    quality = normalize_quality(fm.get("quality"))
    line_count = len(text.splitlines())
    body_words = word_count(body)
    code_blocks = body.count("```") // 2
    headings = re.findall(r"^##\s+(.+)$", body, re.MULTILINE)
    heading_count = len(headings)
    source = fm.get("source", "")
    license_name = fm.get("license", "")
    has_zh_description = bool(fm.get("zh_description"))
    has_references = (skill_md.parent / "references").exists() or (skill_md.parent / "reference").exists()
    has_scripts = (skill_md.parent / "scripts").exists()

    score = 100
    reasons: list[str] = []

    required = ["name", "description", "zh_description", "version", "source", "tags", "quality"]
    missing = [key for key in required if not fm.get(key)]
    if missing:
        score -= min(24, 4 * len(missing))
        reasons.append(f"missing frontmatter: {', '.join(missing)}")

    description = fm.get("description", "")
    if len(description) < 80:
        score -= 8
        reasons.append("description is too short for reliable auto-selection")
    has_trigger_phrase = bool(
        re.search(
            r"\b(use when|use (?:this )?skill when|use it when|use for|use before|used when|triggers?|when users?)\b",
            description,
            re.IGNORECASE,
        )
        or re.search(r"(用于|当用户|适用于|需要|如果)", description)
    )
    if not has_trigger_phrase:
        score -= 8
        reasons.append("description lacks explicit trigger conditions")

    if line_count < 80:
        score -= 20
        reasons.append("body is thin (<80 lines)")
    elif line_count < 120:
        score -= 8
        reasons.append("body is moderate depth (<120 lines)")

    if body_words < 450:
        score -= 12
        reasons.append("low instructional word count")

    if heading_count < 4:
        score -= 8
        reasons.append("few structured sections")

    if code_blocks == 0:
        score -= 8
        reasons.append("no concrete code or command examples")

    if quality is not None:
        if quality >= 4 and line_count < 100:
            score -= 12
            reasons.append("quality tier appears inflated for length")
        if quality <= 2 and line_count >= 160:
            score -= 4
            reasons.append("quality tier may be stale or understated")
    else:
        score -= 8
        reasons.append("quality is not parseable")

    if source.startswith("github:") and not license_name:
        score -= 20
        reasons.append("external source lacks explicit license")

    if "<!-- LOCAL-QUALITY-SUPPLEMENT:START -->" in text:
        score -= 4
        reasons.append("depends on local quality supplement")

    if not has_references and not has_scripts and line_count < 160:
        score -= 5
        reasons.append("no auxiliary references or scripts")

    score = max(0, min(100, score))
    if score < 55:
        action = "replace_or_archive"
    elif score < 70:
        action = "improve"
    elif score < 82:
        action = "review"
    else:
        action = "keep"

    return SkillAudit(
        name=name,
        category=category,
        path=str(skill_md.relative_to(REPO_ROOT)),
        score=score,
        action=action,
        reasons=reasons,
        line_count=line_count,
        word_count=body_words,
        quality=quality,
        source=source,
        license=license_name,
        has_zh_description=has_zh_description,
        code_blocks=code_blocks,
        heading_count=heading_count,
        has_references=has_references,
        has_scripts=has_scripts,
    )


def build_summary(audits: list[SkillAudit]) -> dict[str, Any]:
    by_action: dict[str, int] = {}
    by_category: dict[str, dict[str, int]] = {}
    for audit in audits:
        by_action[audit.action] = by_action.get(audit.action, 0) + 1
        cat = by_category.setdefault(audit.category, {})
        cat[audit.action] = cat.get(audit.action, 0) + 1

    scores = [audit.score for audit in audits]
    return {
        "generated_at": date.today().isoformat(),
        "total_skills": len(audits),
        "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "min_score": min(scores) if scores else 0,
        "max_score": max(scores) if scores else 0,
        "by_action": dict(sorted(by_action.items())),
        "by_category": dict(sorted(by_category.items())),
    }


def write_markdown(path: Path, summary: dict[str, Any], audits: list[SkillAudit]) -> None:
    weak = [audit for audit in audits if audit.action in {"replace_or_archive", "improve"}]
    review = [audit for audit in audits if audit.action == "review"]
    lines = [
        "# Skill Portfolio Audit",
        "",
        f"- Generated: {summary['generated_at']}",
        f"- Total skills: {summary['total_skills']}",
        f"- Average score: {summary['average_score']}",
        f"- Action mix: {summary['by_action']}",
        "",
        "## Highest Priority",
        "",
        "| Score | Action | Skill | Category | Reasons |",
        "|---:|---|---|---|---|",
    ]
    for audit in weak[:80]:
        reasons = "; ".join(audit.reasons[:4]) or "No specific issue recorded"
        lines.append(
            f"| {audit.score} | {audit.action} | `{audit.name}` | `{audit.category}` | {reasons} |"
        )

    lines.extend(
        [
            "",
            "## Review Queue",
            "",
            "| Score | Skill | Category | Reasons |",
            "|---:|---|---|---|",
        ]
    )
    for audit in review[:80]:
        reasons = "; ".join(audit.reasons[:3]) or "Review for portfolio fit"
        lines.append(f"| {audit.score} | `{audit.name}` | `{audit.category}` | {reasons} |")

    lines.extend(
        [
            "",
            "## Method",
            "",
            "Scores combine frontmatter completeness, trigger clarity, body depth, structure, examples, source/license metadata, and local-maintenance risk.",
            "The output is a triage baseline: low scores require human review before deletion or replacement.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit all curated skills for portfolio quality.")
    parser.add_argument("--skills-dir", type=Path, default=DEFAULT_SKILLS_DIR)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    skill_files = sorted(args.skills_dir.glob("*/*/SKILL.md"))
    audits = sorted((audit_skill(path) for path in skill_files), key=lambda item: (item.score, item.name))
    summary = build_summary(audits)

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(
            {
                "summary": summary,
                "skills": [asdict(audit) for audit in audits],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_markdown(args.markdown_output, summary, audits)

    print(f"Wrote audit JSON: {args.json_output}")
    print(f"Wrote audit report: {args.markdown_output}")
    print(f"Audited {summary['total_skills']} skills; average score {summary['average_score']}")
    print(f"Action mix: {summary['by_action']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
