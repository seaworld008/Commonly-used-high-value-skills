from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "audit_skill_freshness.py"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


def test_audit_script_basic_run() -> None:
    result = run_script()
    assert result.returncode == 0
    assert "skills scanned:" in result.stdout
    assert "pinned clawhub versions found:" in result.stdout


def test_audit_script_snapshot_mode(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(
        json.dumps({"skills": ["agent-browser", "non-existent-skill"]}),
        encoding="utf-8",
    )

    result = run_script("--snapshot", str(snapshot))
    assert result.returncode == 0
    assert "snapshot skills: 2" in result.stdout
    assert "missing in repo vs snapshot:" in result.stdout
    assert "- non-existent-skill" in result.stdout
