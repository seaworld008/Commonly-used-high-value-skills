import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills/developer-engineering/graphify"
MAPPING_PATH = REPO_ROOT / "docs/sources/graphify-2026-04.skills.json"
EXPECTED_RELATIVE_FILES = {
    "SKILL.md",
    "EXTENDED.md",
    "LICENSE.upstream.txt",
    "scripts/validate_semantic_chunks.py",
    "references/add-watch.md",
    "references/exports.md",
    "references/extraction-spec.md",
    "references/github-and-merge.md",
    "references/hooks.md",
    "references/query.md",
    "references/transcribe.md",
    "references/update.md",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_graphify_preserves_official_references_with_curated_entry_and_excerpt() -> None:
    actual = {
        path.relative_to(SKILL_ROOT).as_posix()
        for path in SKILL_ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    assert actual == EXPECTED_RELATIVE_FILES
    assert {path.relative_to(SKILL_ROOT).as_posix() for path in SKILL_ROOT.rglob("*.py")} == {"scripts/validate_semantic_chunks.py"}


def test_graphify_release_mapping_has_single_owner_and_exact_hashes() -> None:
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    entry = mapping["skills"][0]
    origin = entry["origins"][0]

    assert entry["normalized_slug"] == "graphify"
    assert entry["kind"] == "overlay"
    assert entry["sync_mode"] == "monitor"
    assert len(entry["origins"]) == 2
    assert origin["sync_mode"] == "monitor"
    local = entry["origins"][1]
    assert local["repo"] == "local-repo/curation"
    assert local["sync_mode"] == "local-only"
    assert local["artifacts"] == [{
        "source": "skills/developer-engineering/graphify/EXTENDED.md",
        "target": "skills/developer-engineering/graphify/EXTENDED.md",
        "type": "file",
    }, {
        "source": "skills/developer-engineering/graphify/scripts/validate_semantic_chunks.py",
        "target": "skills/developer-engineering/graphify/scripts/validate_semantic_chunks.py",
        "type": "file",
    }]
    assert origin["tracking"]["channel"] == "latest_release"
    assert origin["tracking"]["ref"].startswith("v")
    reviewed = next(
        attempt
        for attempt in reversed(mapping["verification_attempts"])
        if attempt["method"] == "commit-aware-manual-monitor-review"
        and attempt["target"].startswith(f"{origin['repo']}@")
        and attempt["result"] == "success"
    )
    assert reviewed["method"] == "commit-aware-manual-monitor-review"
    assert reviewed["result"] == "success"
    reviewed_commit = reviewed["target"].rsplit("@", 1)[1]
    assert origin["tracking"]["resolved_commit"] == reviewed_commit
    assert origin["tracking"]["license_checkpoint"] == {
        "path": "LICENSE",
        "blob_sha": "d645695673349e3947e8e5ae42332d0ac3164cd7",
        "content_sha256": (
            "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"
        ),
        "spdx": "Apache-2.0",
        "resolved_commit": reviewed_commit,
        "api_spdx": "NOASSERTION",
    }

    claims = origin["artifacts"]
    assert claims == [
        {
            "source": "graphify/skill-codex.md",
            "target": "skills/developer-engineering/graphify/SKILL.md",
            "type": "file",
        },
        {
            "source": "graphify/skills/codex/references",
            "target": "skills/developer-engineering/graphify/references",
            "type": "directory",
        },
        {"source": "LICENSE", "target": "skills/developer-engineering/graphify/LICENSE.upstream.txt", "type": "file"},
    ]

    managed = {item["path"]: item for item in entry["managed_files"]}
    expected_paths = {
        f"skills/developer-engineering/graphify/{path}"
        for path in EXPECTED_RELATIVE_FILES
    }
    assert set(managed) == expected_paths
    assert len(managed) == 12
    assert all(item["owner"] == "graphify" for item in managed.values())
    assert all(item["mode"] == "100644" for item in managed.values())
    for relative_path in EXPECTED_RELATIVE_FILES:
        repo_path = f"skills/developer-engineering/graphify/{relative_path}"
        assert managed[repo_path]["sha256"] == _sha256(REPO_ROOT / repo_path)

    skill_hash = managed["skills/developer-engineering/graphify/SKILL.md"]["sha256"]
    assert origin["tracking"]["content_sha256"] == skill_hash


def test_graphify_curated_references_match_reviewed_hashes() -> None:
    expected_hashes = {
        "add-watch.md": "50a05e49cf382441afb8cbeb7fb68018c5458e7e2db35f01b61d199ba5b73772",
        "exports.md": "a026e8d155223b1a3ac70e0db5cf3f728a1088ac226fd33de28f82c53a878fcf",
        "extraction-spec.md": "95dbfd11ad0d5d416f30303837b108476959c4a4a05afd3ec7cde628ffa9ecab",
        "github-and-merge.md": "e5ebd90c7686f50363ff7a535556bc2f596d4c47ec1e6c8b95e11e36a0dfea2b",
        "hooks.md": "c3141e7124be8d1f0e96ff3895220a1b6318a644c4c6a60120e4aa6b1cd92d4a",
        "query.md": "03d7ea695923c08a695421e20b6fb9d98f55976b62dfb066eea062f9393b2db0",
        "transcribe.md": "ceda4b469c0d34361552c0902e5d3a8f34516175791bd18e3bed71d98dc31971",
        "update.md": "bd76847bfc68d44c1e6f2e8ad8fce10a1208ecb7e6134c6cbbd74634c1489294",
    }
    assert {
        path.name: _sha256(path)
        for path in sorted((SKILL_ROOT / "references").glob("*.md"))
    } == expected_hashes
