"""Packaging/provenance contracts; these do not claim model-behavior evaluation."""
import hashlib
import json
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/task-understanding-decomposition/grill-me"
PIN = "6acc160e4e0cd062dbbbd7a1b26ae92855edf07e"
UPSTREAM_BLOBS = {
    "references/upstream-grill-me.md": "9470cfcfe231a35e46494cddbacdd395991afb1e",
    "references/upstream-grilling.md": "95bd01ee9049a7e08120d54af9cd6ceeef282335",
    "LICENSE.upstream.txt": "f1dd2c09108dde1a5f56097cee8461b3ea834499",
}


def test_grill_me_is_discoverable_and_installs_its_complete_dependency(tmp_path):
    dest = tmp_path / "installed"
    result = subprocess.run(
        ["node", str(ROOT / "bin/install-skills.js"), "install", "--target", "custom",
         "--dir", str(dest), "--skill", "grill-me"],
        cwd=ROOT, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert (dest / "grill-me/SKILL.md").is_file()
    for source in SKILL.rglob("*"):
        if source.is_file():
            assert (dest / "grill-me" / source.relative_to(SKILL)).read_bytes() == source.read_bytes()
    names = [p.name for p in dest.iterdir() if p.is_dir()]
    assert names == ["grill-me"], "No separate grilling installation should be required"


def test_grill_me_retains_exact_licensed_upstream_evidence():
    assert SKILL.is_dir()
    for relative, expected in UPSTREAM_BLOBS.items():
        raw = (SKILL / relative).read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        assert actual == expected, relative
    fm = yaml.safe_load((SKILL / "SKILL.md").read_text().split("---", 2)[1])
    assert fm["name"] == "grill-me"
    assert fm["disable-model-invocation"] is True
    assert fm["source"] == "github:mattpocock/skills"
    assert fm["license"] == "MIT"


def test_grill_me_has_one_complete_pinned_provenance_claim():
    claims = []
    for path in (ROOT / "docs/sources").glob("*.skills.json"):
        claims.extend(e for e in json.loads(path.read_text()).get("skills", [])
                      if e.get("normalized_slug") == "grill-me")
    assert len(claims) == 1
    entry = claims[0]
    assert entry["kind"] == "overlay" and entry["sync_mode"] == "monitor"
    origin = next(o for o in entry["origins"] if o["repo"] == "mattpocock/skills")
    assert origin["tracking"]["resolved_commit"] == PIN
    assert origin["tracking"]["license_checkpoint"]["spdx"] == "MIT"
    declared = {f["path"]: f for f in entry["managed_files"]}
    actual = {p.relative_to(ROOT).as_posix() for p in SKILL.rglob("*") if p.is_file()}
    assert set(declared) == actual
    for name in actual:
        assert declared[name]["sha256"] == hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
