from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MAPPING = (
    REPO_ROOT
    / "docs"
    / "sources"
    / "nous-hermes-agent-2026-04.skills.json"
)
SKILL_ROOT = REPO_ROOT / "skills" / "ai-agent-platform" / "hermes-agent"
RELEASE_COMMIT = "fcbd1076a93841fa88855acce810e342a5b78101"
PATH_COMMIT = "89ecaf03d56a27ed8f9259701f359f3878339a2a"
CANONICAL_SHA256 = (
    "f23020e7308ad257bd1740e5f71932aba86bc803155dba530485a243bdcae990"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hermes_entry() -> dict:
    data = json.loads(MAPPING.read_text(encoding="utf-8"))
    return next(
        item
        for item in data["skills"]
        if item.get("normalized_slug") == "hermes-agent"
    )


def test_hermes_is_a_complete_pinned_stable_release_mirror() -> None:
    entry = hermes_entry()
    assert entry["kind"] == "mirror"
    assert entry["sync_mode"] == "replace"
    assert len(entry["origins"]) == 1

    origin = entry["origins"][0]
    tracking = origin["tracking"]
    assert origin["sync_mode"] == "replace"
    assert tracking["channel"] == "latest_release"
    assert tracking["ref"] == "v2026.8.19"
    assert tracking["resolved_commit"] == RELEASE_COMMIT
    assert tracking["path_commit"] == PATH_COMMIT
    assert tracking["content_sha256"] == CANONICAL_SHA256
    assert tracking["license_checkpoint"]["spdx"] == "MIT"
    assert tracking["license_checkpoint"]["resolved_commit"] == RELEASE_COMMIT

    artifacts = {
        (artifact["source"], artifact["target"], artifact["type"])
        for artifact in origin["artifacts"]
    }
    upstream_root = "skills/autonomous-ai-agents/hermes-agent"
    target_root = "skills/ai-agent-platform/hermes-agent"
    assert artifacts == {
        (
            f"{upstream_root}/SKILL.md",
            f"{target_root}/SKILL.md",
            "file",
        ),
        (
            f"{upstream_root}/references",
            f"{target_root}/references",
            "directory",
        ),
        (
            f"{upstream_root}/templates",
            f"{target_root}/templates",
            "directory",
        ),
    }


def test_hermes_managed_inventory_matches_all_22_regular_files() -> None:
    entry = hermes_entry()
    managed = {item["path"]: item for item in entry["managed_files"]}
    disk_files = sorted(path for path in SKILL_ROOT.rglob("*") if path.is_file())

    assert len(disk_files) == 22
    assert sum(path.parent.name == "references" for path in disk_files) == 18
    assert sum(path.parent.name == "templates" for path in disk_files) == 3
    assert not any(path.is_symlink() for path in SKILL_ROOT.rglob("*"))
    assert sha256(SKILL_ROOT / "SKILL.md") == CANONICAL_SHA256

    relative_files = {
        path.relative_to(REPO_ROOT).as_posix() for path in disk_files
    }
    assert set(managed) == relative_files
    for relative, checkpoint in managed.items():
        assert checkpoint["owner"] == "hermes-agent"
        assert checkpoint["mode"] == "100644"
        assert sha256(REPO_ROOT / relative) == checkpoint["sha256"]


def test_hermes_skill_local_sidecar_references_are_closed() -> None:
    content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    references = set(
        re.findall(r"(?:references|templates)/[A-Za-z0-9._-]+", content)
    )

    assert references
    missing = sorted(
        relative
        for relative in references
        if not (SKILL_ROOT / relative).is_file()
    )
    assert missing == []
