from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def mapping(name: str) -> dict:
    return json.loads(
        (ROOT / "docs" / "sources" / name).read_text(encoding="utf-8")
    )


def entry(data: dict, slug: str) -> dict:
    return next(
        item for item in data["skills"] if item["normalized_slug"] == slug
    )


def assert_managed_inventory(item: dict) -> None:
    for managed in item["managed_files"]:
        path = ROOT / managed["path"]
        assert path.is_file()
        assert not path.is_symlink()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == managed["sha256"]


def test_using_superpowers_tracks_current_complete_reference_set() -> None:
    item = entry(
        mapping("obra-superpowers-2026-04.skills.json"),
        "using-superpowers",
    )
    origin = item["origins"][0]
    references = ROOT / "skills" / "ai-workflow" / "using-superpowers" / "references"

    assert origin["tracking"]["resolved_commit"] == (
        "b36e0829c6d0140e93cfef2ca599b1b07d4a7797"
    )
    assert {path.name for path in references.glob("*.md")} == {
        "antigravity-tools.md",
        "codex-tools.md",
        "gemini-tools.md",
        "hermes-tools.md",
        "pi-tools.md",
    }
    assert origin["artifacts"][1]["type"] == "directory"
    assert_managed_inventory(item)


def test_reviewed_monitor_checkpoints_advance_without_body_churn() -> None:
    cases = (
        (
            "addyosmani-agent-skills-2026-04.skills.json",
            "api-and-interface-design",
            "5a5ea45e806f82273549fd85e60adb95d55f510d",
        ),
        (
            "firebase-agent-skills-2026-07.skills.json",
            "firebase-security-rules-auditor",
            "073edf7bb747c27b9c911a9126adaa5bc4648fdc",
        ),
        (
            "xiaolai-nlpm-2026-06.skills.json",
            "nlpm-audit",
            "38defa93f1a7ac85cbf971a62f9fbf1b372aaa61",
        ),
    )
    for mapping_name, slug, commit in cases:
        item = entry(mapping(mapping_name), slug)
        tracking = item["origins"][0]["tracking"]
        assert tracking["resolved_commit"] == commit
        assert tracking["license_checkpoint"]["resolved_commit"] == commit
        assert_managed_inventory(item)


def test_license_drift_is_frozen_at_permissive_immutable_snapshots() -> None:
    reclassified = mapping("reclassified-external-skills-2026-08.skills.json")
    guizang = entry(
        mapping("op7418-guizang-ppt-skill-2026-04.skills.json"),
        "guizang-ppt-skill",
    )
    cases = (
        (
            entry(reclassified, "docker-expert"),
            "e2b6ad15c704e47819b0e2393d04b42a9dcf4fc5",
            "MIT",
        ),
        (
            entry(reclassified, "vercel-react-best-practices"),
            "b8caa260a420a73042e35521de4b5c8baf6446cc",
            "MIT",
        ),
        (
            entry(reclassified, "vercel-react-view-transitions"),
            "b8caa260a420a73042e35521de4b5c8baf6446cc",
            "MIT",
        ),
        (
            guizang,
            "72837a8513d1145d800095fc3909d6d3057994b8",
            "MIT",
        ),
    )
    for item, commit, license_name in cases:
        origin = next(
            origin
            for origin in item["origins"]
            if not origin["repo"].startswith("local-repo/")
        )
        tracking = origin["tracking"]
        assert item["kind"] == "snapshot"
        assert item["sync_mode"] == "archived"
        assert origin["sync_mode"] == "archived"
        assert tracking["channel"] == "fixed_ref"
        assert tracking["ref"] == commit
        assert tracking["resolved_commit"] == commit
        assert tracking["license_checkpoint"]["spdx"] == license_name
        assert tracking["license_checkpoint"]["resolved_commit"] == commit
        assert_managed_inventory(item)
