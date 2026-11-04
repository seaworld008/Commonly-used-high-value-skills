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
RELEASE_COMMIT = "b200f5bc60e31588ba2cb60e288029c4a54ba5fa"
PATH_COMMIT = "0aab6dcf8b7869acbab06507c34881b53036c09a"
CANONICAL_SHA256 = (
    "d4eeaea682f76a2bf8a482a7241b3875ad2ad7a96a440e218174400c7b043750"
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
    assert tracking["ref"] == "v0.22.7"
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


def test_hermes_managed_inventory_matches_all_23_regular_files() -> None:
    entry = hermes_entry()
    managed = {item["path"]: item for item in entry["managed_files"]}
    disk_files = sorted(path for path in SKILL_ROOT.rglob("*") if path.is_file())

    assert len(disk_files) == 23
    assert sum(path.parent.name == "references" for path in disk_files) == 19
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
