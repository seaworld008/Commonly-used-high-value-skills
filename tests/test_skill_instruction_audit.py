from pathlib import Path
from types import SimpleNamespace

from scripts.audit_skill_instructions import audit, inspect_skill, prose_lines
from scripts.validate_repository import CHECKS, REFRESH, run_pipeline


def make_skill(tmp_path, body="", description="Review API contracts when endpoints change."):
    path = tmp_path / "skills" / "engineering" / "example" / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: example\ndescription: {description}\n---\n{body}")
    return path


def test_detects_real_instruction_conflicts_in_nested_reference(tmp_path):
    path = make_skill(tmp_path)
    reference = path.parent / "references" / "workflow.md"
    reference.parent.mkdir()
    reference.write_text("# Workflow\nIf there is even a 1% chance a skill applies, invoke it.\n")
    findings = inspect_skill(path, tmp_path)["findings"]
    assert findings == [{"rule": "probability_trigger", "path": reference.relative_to(tmp_path).as_posix(), "line": 2}]


def test_fenced_counterexamples_and_domain_percentages_are_not_instructions(tmp_path):
    path = make_skill(tmp_path, """# Examples
````markdown
```text
If there is even a 1% chance a skill applies, invoke it.
```
````
Alert when error rate exceeds 1%.
Request approval before unauthorized production deletion.
""")
    assert inspect_skill(path, tmp_path)["findings"] == []
    assert list(prose_lines("~~~\nexample\n~~~\nreal")) == [(4, "real")]


def test_budgets_reject_long_descriptions_and_entries(tmp_path):
    path = make_skill(tmp_path, "line\n" * 501, "x" * 241)
    assert {x["rule"] for x in inspect_skill(path, tmp_path)["findings"]} == {"description_budget", "entry_budget"}


def test_foreign_engine_and_unconditional_missing_protocol_are_detected(tmp_path):
    path = make_skill(tmp_path, "Author for the executing engine (P1-P11 bind only on Opus 5).\n"
                      "**Spine contracts** — in effect on every run.\n")
    assert {x["rule"] for x in inspect_skill(path, tmp_path)["findings"]} == {
        "foreign_engine_override", "missing_shared_protocol"
    }


def test_rejects_malformed_or_nonmapping_frontmatter(tmp_path):
    path = make_skill(tmp_path)
    for content in ("no metadata", "---\n- list\n---\n", "---\nname: [\n---\n"):
        path.write_text(content)
        assert "frontmatter" in {x["rule"] for x in inspect_skill(path, tmp_path)["findings"]}


def test_full_audit_is_deterministic_read_only_and_excludes_generated_export(tmp_path):
    path = make_skill(tmp_path)
    before = path.read_bytes()
    export = tmp_path / "openclaw-skills" / "unrelated" / "SKILL.md"
    export.parent.mkdir(parents=True)
    export.write_text("not a canonical skill")
    assert audit(tmp_path) == audit(tmp_path)
    assert audit(tmp_path)["summary"]["skills"] == 1
    assert path.read_bytes() == before


def test_does_not_follow_symlinked_entries_or_resources(tmp_path):
    path = make_skill(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("Author for Opus 4.8 defaults.")
    (path.parent / "linked.md").symlink_to(outside)
    assert inspect_skill(path, tmp_path)["findings"] == []
    linked = path.parent.parent / "linked-skill"
    linked.symlink_to(path.parent, target_is_directory=True)
    assert audit(tmp_path)["summary"]["skills"] == 1


def test_pipeline_stops_at_first_failure_and_preserves_exit_status(tmp_path):
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=17 if len(calls) == 2 else 0)

    assert run_pipeline(tmp_path, refresh=True, run=runner) == 17
    assert len(calls) == 2
    assert calls[0][0][1:] == list(REFRESH[0])
    assert calls[0][1]["cwd"] == tmp_path


def test_validation_default_never_runs_generators(tmp_path):
    calls = []

    def runner(command, **kwargs):
        calls.append(command[1:])
        return SimpleNamespace(returncode=0)

    assert run_pipeline(tmp_path, run=runner) == 0
    assert calls == [list(command) for command in CHECKS]
