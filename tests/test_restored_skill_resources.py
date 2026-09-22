"""Exercise restored executable contracts without network or user data."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESTORED = (
    "agent-hub", "security-pen-testing", "information-security-manager-iso27001",
    "landing-page-generator", "saas-metrics-coach", "senior-architect",
    "skill-security-auditor", "arxiv",
)


REQUIRED_SIDECARS = {
    "skill-security-auditor": [
        "references/threat-model.md",
        "scripts/skill_security_auditor.py"
    ],
    "information-security-manager-iso27001": [
        "references/incident-response.md",
        "references/iso27001-controls.md",
        "references/risk-assessment-guide.md",
        "scripts/compliance_checker.py",
        "scripts/risk_assessment.py"
    ],
    "landing-page-generator": [
        "references/conversion-patterns.md",
        "references/copy-frameworks.md",
        "references/landing-page-patterns.md",
        "references/seo-checklist.md",
        "scripts/landing_page_scaffolder.py"
    ],
    "security-pen-testing": [
        "references/attack_patterns.md",
        "references/owasp_top_10_checklist.md",
        "references/responsible_disclosure.md",
        "scripts/dependency_auditor.py",
        "scripts/pentest_report_generator.py",
        "scripts/vulnerability_scanner.py"
    ],
    "agent-hub": [
        "references/agent-templates.md",
        "references/coordination-strategies.md",
        "references/dag-patterns.md",
        "scripts/board_manager.py",
        "scripts/dag_analyzer.py",
        "scripts/dry_run.py",
        "scripts/hub_init.py",
        "scripts/result_ranker.py",
        "scripts/session_manager.py"
    ],
    "senior-architect": [
        "references/architecture_patterns.md",
        "references/system_design_workflows.md",
        "references/tech_decision_guide.md",
        "scripts/architecture_diagram_generator.py",
        "scripts/dependency_analyzer.py",
        "scripts/project_architect.py"
    ],
    "saas-metrics-coach": [
        "assets/input-template.md",
        "references/benchmarks.md",
        "references/formulas.md",
        "scripts/metrics_calculator.py",
        "scripts/quick_ratio_calculator.py",
        "scripts/unit_economics_simulator.py"
    ]
}


def skill_dir(name):
    return next((ROOT / "skills").glob(f"*/{name}"))


def module_at(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", RESTORED)
def test_restored_skills_ship_executable_helpers_and_license(name):
    directory = skill_dir(name)
    scripts = list((directory / "scripts").glob("*.py"))
    assert scripts, f"{name} advertises scripts but none are bundled"
    for relative in REQUIRED_SIDECARS.get(name, ["scripts/search_arxiv.py"]):
        assert (directory / relative).is_file(), relative
    assert (directory / "LICENSE.upstream.txt").is_file()
    for script in scripts:
        result = subprocess.run([sys.executable, str(script), "--help"],
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, (script, result.stderr)
        assert "usage" in result.stdout.lower() or "usage" in result.stderr.lower()


def test_saas_quick_ratio_calculates_growth_and_loss_from_inputs():
    script = skill_dir("saas-metrics-coach") / "scripts/quick_ratio_calculator.py"
    result = subprocess.run([sys.executable, str(script), "--new-mrr", "10000",
                             "--expansion", "2000", "--churned", "3000",
                             "--contraction", "500", "--json"],
                            capture_output=True, text=True, check=True, timeout=10)
    data = json.loads(result.stdout)
    assert data["quick_ratio"] == pytest.approx(12000 / 3500)
    assert data["components"]["lost_mrr"] == 3500


def test_agenthub_cleanup_preserves_dirty_worktrees_and_other_sessions(monkeypatch, capsys):
    module = module_at(skill_dir("agent-hub") / "scripts/session_manager.py")
    monkeypatch.setattr(module, "load_config", lambda _: {"task": "example"})
    monkeypatch.setattr(module, "run_git", lambda *args: (
        "worktree /tmp/owned\nbranch refs/heads/hub/demo/one\n\n"
        "worktree /tmp/other\nbranch refs/heads/archive/hub/demo/two\n\n"
        "worktree /tmp/longer\nbranch refs/heads/hub/demo-extra/one\n"))
    calls = []
    def reject_dirty(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=128, stderr="contains modified files")
    monkeypatch.setattr(module.subprocess, "run", reject_dirty)
    module.cleanup_session("demo")
    assert calls == [["git", "worktree", "remove", "/tmp/owned"]]
    assert "Preserved worktree" in capsys.readouterr().err


def test_arxiv_helper_parses_atom_response_without_network(monkeypatch, capsys):
    module = module_at(skill_dir("arxiv") / "scripts/search_arxiv.py")
    from io import BytesIO
    payload = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry>
    <id>http://arxiv.org/abs/2402.03300v2</id><title>Fixture paper</title>
    <published>2024-02-05</published><updated>2024-03-05</updated>
    <author><name>Example Author</name></author><summary>Fixture abstract</summary>
    <category term="cs.AI"/></entry></feed>'''
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *a, **k: BytesIO(payload))
    module.search(query="test paper")
    assert "Fixture paper" in capsys.readouterr().out
