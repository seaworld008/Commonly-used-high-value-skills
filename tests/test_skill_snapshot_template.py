from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "skill_snapshot_template.py"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


def test_generate_template(tmp_path: Path) -> None:
    output = tmp_path / "snapshot.json"
    result = run_script("generate", "--output", str(output))
    assert result.returncode == 0
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert isinstance(data.get("skills"), list)
    assert data["skills"]
    assert "captured_at" in data
    assert "source" in data


def test_generate_from_local_and_validate(tmp_path: Path) -> None:
    output = tmp_path / "snapshot-local.json"
    gen = run_script("generate", "--output", str(output), "--from-local")
    assert gen.returncode == 0

    val = run_script("validate", "--snapshot", str(output))
    assert val.returncode == 0
    assert "valid snapshot" in val.stdout


def test_validate_invalid_snapshot(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"skills": [], "captured_at": "", "source": ""}', encoding="utf-8")

    result = run_script("validate", "--snapshot", str(bad))
    assert result.returncode == 1
    assert "invalid snapshot" in result.stdout
