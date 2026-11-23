"""Unit tests for bilingual and singular section recognition in lint_skill_quality."""

from pathlib import Path
from scripts.lint_skill_quality import lint_skill


def _write_skill(tmp_path: Path, headings: str) -> Path:
    body = "\n".join([f"line {i}" for i in range(1, 55)])
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        f"""---
name: sample-check
description: "Use when verifying lint_skill section recognition across English and Chinese skills."
version: "1.0.0"
tags: [test]
quality: 2
---

# Sample Check

{headings}

```bash
echo ok
```

{body}
""",
        encoding="utf-8",
    )
    return skill


def test_lint_accepts_chinese_scenario_and_workflow_headings(tmp_path):
    skill = _write_skill(tmp_path, "## 适用场景\n\n## 工作流")
    result = lint_skill(skill, min_lines=50)
    assert result["status"] == "PASS"
    assert result["warnings"] == []


def test_lint_accepts_singular_example_and_common_patterns(tmp_path):
    skill_ex = _write_skill(tmp_path, "## Trigger Details\n\n## Example")
    assert lint_skill(skill_ex, min_lines=50)["status"] == "PASS"

    skill_cp = _write_skill(tmp_path, "## Scope\n\n## Common Patterns: Safe Edits")
    assert lint_skill(skill_cp, min_lines=50)["status"] == "PASS"


def test_lint_still_warns_on_generic_unrecognized_headings(tmp_path):
    skill = _write_skill(tmp_path, "## Notes\n\n## Details")
    result = lint_skill(skill, min_lines=50)
    assert result["status"] == "WARN"
    assert "missing sections" in result["warnings"]
