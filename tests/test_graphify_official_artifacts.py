import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills/developer-engineering/graphify"
MAPPING_PATH = REPO_ROOT / "docs/sources/graphify-2026-04.skills.json"
EXPECTED_RELATIVE_FILES = {
    "SKILL.md",
    "EXTENDED.md",
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
        if path.is_file()
    }
    assert actual == EXPECTED_RELATIVE_FILES
    assert not any(path.suffix in {".py", ".pyc"} for path in SKILL_ROOT.rglob("*"))


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
    ]

    managed = {item["path"]: item for item in entry["managed_files"]}
    expected_paths = {
        f"skills/developer-engineering/graphify/{path}"
        for path in EXPECTED_RELATIVE_FILES
    }
    assert set(managed) == expected_paths
    assert len(managed) == 10
    assert all(item["owner"] == "graphify" for item in managed.values())
    assert all(item["mode"] == "100644" for item in managed.values())
    for relative_path in EXPECTED_RELATIVE_FILES:
        repo_path = f"skills/developer-engineering/graphify/{relative_path}"
        assert managed[repo_path]["sha256"] == _sha256(REPO_ROOT / repo_path)

    skill_hash = managed["skills/developer-engineering/graphify/SKILL.md"]["sha256"]
    assert origin["tracking"]["content_sha256"] == skill_hash


def test_graphify_references_match_reviewed_release_hashes() -> None:
    expected_hashes = {
        "add-watch.md": "b3f67570240582689c2834b4831917550c2d1aaf042148868c39dcbf387ce3fd",
        "exports.md": "ee47fae477f106d8aed38798c58493b5a7f060a0d9d2581ce6132302827bc14b",
        "extraction-spec.md": "32d7decad42d58129c6694ea4e4ce1f72a531bc5161827d2095787e9448735e9",
        "github-and-merge.md": "e5ebd90c7686f50363ff7a535556bc2f596d4c47ec1e6c8b95e11e36a0dfea2b",
        "hooks.md": "b9a4e9f66813c6fc720589f1071d1a03c95756ab7101447e14e57291fe7844e5",
        "query.md": "e563ddcb1e155aa230f107e5ef9380bc1249c5cd8241128de7ed8a7bd9c20cf5",
        "transcribe.md": "676a1e39aa6d43cdfcc416ec56616e36f7bad74066a82bd33a9485515b9a865c",
        "update.md": "661f559b3ff4f3db7ba47bc2ba1c7e19f1c1d66a36f647e49221eecb174f2228",
    }
    assert {
        path.name: _sha256(path)
        for path in sorted((SKILL_ROOT / "references").glob("*.md"))
    } == expected_hashes
