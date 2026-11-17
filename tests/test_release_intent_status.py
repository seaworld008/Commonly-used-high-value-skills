"""Execute the real release preflight against isolated local release intents."""
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('status,success', [
    ('ready', True), ('absent', True), ('blocked_pending_provenance', False),
    ('pending', False), ('', False), (None, False), (False, False), (0, False),
])
def test_actual_release_preflight_honors_source_hold(tmp_path, status, success):
    workflow = (ROOT / '.github/workflows/publish-release.yml').read_text()
    program = re.search(r"          python - <<'PY'\n(.*?)\n          PY", workflow, re.S).group(1)
    program = '\n'.join(line[10:] if line.startswith(' ' * 10) else line
                        for line in program.splitlines())
    (tmp_path / 'package.json').write_text(json.dumps({'version': '6.1.0'}))
    releases = tmp_path / 'docs/releases'
    releases.mkdir(parents=True)
    metadata = {'tag': 'v6.1.0', 'package_version': '6.1.0', 'canonical_skills': 1}
    if status != 'absent':
        metadata['publication_status'] = status
    (releases / 'v6.1.0.json').write_text(json.dumps(metadata))
    (releases / 'v6.1.0.md').write_text('Local release notes.\n')
    skill = tmp_path / 'skills/category/example'
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text('# Example\n')
    result = subprocess.run([sys.executable, '-c', program], cwd=tmp_path,
                            capture_output=True, text=True)
    assert (result.returncode == 0) is success, result.stdout + result.stderr
    assert ('Release intent:' in result.stdout) is success
    if not success:
        assert 'blocks publication' in result.stderr
