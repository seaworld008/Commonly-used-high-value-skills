"""The documented preflight checks presence without disclosing the credential."""
import os
from pathlib import Path
import re
import subprocess
import pytest

GUIDE = Path(__file__).resolve().parents[1] / "skills/office-white-collar/transcript-fixer/references/workflow_guide.md"

@pytest.mark.parametrize("trace", [False, True])
@pytest.mark.parametrize("key,expected", [("synthetic-preflight-marker-only", 0), ("", 1)])
def test_documented_preflight_never_prints_key(key, expected, trace):
    section = GUIDE.read_text().split("**Quick validation**:", 1)[1]
    command = re.search(r"```bash\n(.*?)\n```", section, re.S).group(1)
    result = subprocess.run(["sh", *(["-x"] if trace else []), "-c", "uv() { return 0; }; " + command],
                            env={**os.environ, "GLM_API_KEY": key}, capture_output=True, text=True)
    assert result.returncode == expected
    output = result.stdout + result.stderr
    assert "synthetic-preflight-marker-only" not in output
    assert result.stdout == ""
