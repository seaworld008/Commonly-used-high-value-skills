"""Regression checks for durable portfolio curation, not upstream wording."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(category: str, skill: str) -> str:
    return (ROOT / "skills" / category / skill / "SKILL.md").read_text()


def test_repository_sizing_does_not_override_system_python_protection():
    content = canonical("developer-engineering", "codebase-inspection")
    assert "--break-system-packages" not in content
    assert "python3 -m venv" in content
    assert "LOCAL-CURATION-SUPPLEMENT:START" in content
    assert "denominator" in content
    assert "skills/software-development/codebase-inspection/SKILL.md" in content


def test_mcporter_requires_schema_trust_and_write_reconciliation():
    content = canonical("ai-agent-platform", "mcporter")
    assert "LOCAL-CURATION-SUPPLEMENT:START" in content
    assert "discovery can launch a local stdio" in content
    assert "do not guess tools or required arguments" in content
    assert "Never retry a timed-out write blindly" in content
    assert "isError" in content


def test_obsidian_preserves_scope_and_concurrent_edits():
    content = canonical("knowledge-and-pm-integrations", "obsidian")
    assert "LOCAL-QUALITY-SUPPLEMENT:START" in content
    assert "LOCAL-CURATION-SUPPLEMENT:START" in content
    assert "after resolving symlinks" in content
    assert "Re-read before writing" in content
    assert "Frontmatter still parses" in content
    assert "do not claim a rendered result" in content


def test_runbook_does_not_erase_external_lineage_when_upstream_disappears():
    content = (ROOT / "docs" / "repo-maintenance-runbook.md").read_text()
    assert "或改为 `source: in-house`" not in content
    assert "不能因此改成 `in-house`" in content
    assert "中文化、扩写和结构重写仍须保留原许可证与来源" in content


def test_replanning_does_not_replace_an_unfinished_plan():
    content = canonical("ai-workflow", "planning-and-task-breakdown")
    assert "Preserve incomplete plans" in content
    assert "never bulk-close another plan" in content
