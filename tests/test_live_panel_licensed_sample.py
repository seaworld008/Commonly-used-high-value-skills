import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/multimodal-media/live-panel'


def test_distribution_excludes_third_party_illustrations_and_preserves_lineage():
    for name in ['airbnb', 'codex-agents', 'agent-architecture']:
        assert not (SKILL / 'examples' / name / 'config.json').exists()
    mapping = json.loads((ROOT / 'docs/sources/curated-v3.3.0.skills.json').read_text())
    entry = next(e for e in mapping['skills'] if e['normalized_slug'] == 'live-panel')
    assert entry['kind'] == 'snapshot'
    assert entry['sync_mode'] == 'local-only'
    external, local = entry['origins']
    assert external['repo'] == 'ythx-101/live-panel-skill'
    assert external['tracking']['license_checkpoint']['api_spdx'] == 'NOASSERTION'
    assert local['repo'] == 'local-repo/curation'
    assert hashlib.sha256((SKILL / 'LICENSE.txt').read_bytes()).hexdigest() == (
        'a7fe974dec4660c7070064bc2606be65a4e95263bb558132848d1475040954d3'
    )


def test_original_sample_builds_offline_page_without_browser(tmp_path):
    spec = importlib.util.spec_from_file_location('licensed_panel_helpers', SKILL / 'scripts/livepanel.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sample = SKILL / 'examples/service-pipeline/config.json'
    output = tmp_path / 'sample.html'
    cfg = module.build_page(sample, output)
    assert module.canvas(cfg) == (640, 640, 2, 12)
    assert 'simulated' in cfg['credit']['text']
    assert len([e for e in cfg['elements'] if e['type'] == 'box']) == 3
    text = output.read_text()
    assert '<script id="live-config" type="application/json">' in text
    assert "connect-src 'none'" in text
    assert 'No live telemetry or customer data' in text
