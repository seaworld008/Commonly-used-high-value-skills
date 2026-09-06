import hashlib
import json
import stat
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def canonical_files(root: Path) -> list[Path]:
    """Match source inventory semantics after local Python compilation."""
    return [
        path
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.relative_to(root).parts
        and path.suffix not in {".pyc", ".pyo"}
    ]


def test_canonical_files_ignore_bytecode_but_not_unmanaged_source(tmp_path):
    (tmp_path / "SKILL.md").write_text("# Skill\n")
    (tmp_path / "extra.txt").write_text("Must remain visible to inventory checks.\n")
    (tmp_path / "module.pyc").write_bytes(b"bytecode-fixture")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "module.cpython-313.pyc").write_bytes(b"bytecode-fixture")
    assert {path.name for path in canonical_files(tmp_path)} == {"SKILL.md", "extra.txt"}


MAPPING_PATH = REPO_ROOT / "docs/sources/larksuite-cli-2026-05.skills.json"
REVIEWED_COMMIT = "7fd6ef3c07182257ce776cdc5a614e122d5bd4b3"
AUGUST_31_REVIEWED_COMMIT = "6646386e0996b1ff5df640bccff834a20bcb203b"
AUGUST_24_REVIEWED_COMMIT = "56ad837c3d8f4c49d6b9725a3530c37408533ead"
PREVIOUS_REVIEWED_COMMIT = "ca35f6061616d4f47681368bbbef03be28193dc9"
INITIAL_REVIEWED_COMMIT = "755daa4de3ea12785c43a15244ffb8f012122c13"
EXPECTED_COUNTS = {
    "lark-approval": 17,
    "lark-attendance": 1,
    "lark-base": 31,
    "lark-calendar": 13,
    "lark-contact": 4,
    "lark-doc": 44,
    "lark-drive": 61,
    "lark-event": 8,
    "lark-im": 60,
    "lark-mail": 34,
    "lark-markdown": 6,
    "lark-meeting": 27,
    "lark-okr": 19,
    "lark-openapi-explorer": 1,
    "lark-shared": 7,
    "lark-sheets": 28,
    "lark-skill-maker": 1,
    "lark-slides": 50,
    "lark-task": 18,
    "lark-whiteboard": 31,
    "lark-wiki": 14,
    "lark-workflow-meeting-summary": 1,
    "lark-workflow-standup-report": 1,
}
EXPECTED_PATH_COMMITS = {
    "lark-approval": "0d5334a0cdfdf18b0313ba051befb2848493ecda",
    "lark-attendance": "69ae326d01a9163ca22408c746e052003cf0af2c",
    "lark-base": "ac0f243e5b2f6d2fe9e90868d5ba1c5896433e13",
    "lark-calendar": "6956ac2eab2040b6edea0f9aac43567b08ded326",
    "lark-contact": "87be09ef5f227c7b63d5eba40649544b5bec0133",
    "lark-doc": "fe8ce4675b3d5ccf795e1dfa61a22c90ba7ca194",
    "lark-drive": "59f6ad490054b219714cc09e77fcb3dc137b8168",
    "lark-event": "fcdef499bb23739b720c665d49875a9957c97d48",
    "lark-im": "7fd6ef3c07182257ce776cdc5a614e122d5bd4b3",
    "lark-mail": "0cf8ae81c18526289ee8bdf371e4d3de639d097a",
    "lark-markdown": "62f270afd68c9d98ceb9d10ca9216f802a5f54c3",
    "lark-meeting": "688de5cda3862394e185444ea01ebadf3f7ffb7a",
    "lark-okr": "baf9640bec9eddb658ec351956553b8fa0bad6cb",
    "lark-openapi-explorer": "83dfb068ad8bb4052787d80ca415118a20849b85",
    "lark-shared": "327874c8f4af85586af97ddda6f1ac4bd168e79a",
    "lark-sheets": "c6c040c2c5b93a1b4feede8d3d977b8ae3d2b2a5",
    "lark-skill-maker": "83dfb068ad8bb4052787d80ca415118a20849b85",
    "lark-slides": "36cd24aa73bca42ea8df124d6556d94ca7c86b59",
    "lark-task": "e525beb8d6ddecbde68ea3b2df292f1d70a66fa5",
    "lark-whiteboard": "27ab8fbea3e6f2b07e93a26bc635e0e52023d7a0",
    "lark-wiki": "6e2cad7221755d3668b350f186b862d64e0cba97",
    "lark-workflow-meeting-summary": "e525beb8d6ddecbde68ea3b2df292f1d70a66fa5",
    "lark-workflow-standup-report": "049ddf771b435e86a4f5a71e616336ec44341160"
}

LOCAL_OVERLAYS = {
    "lark-approval": {
        "skills/knowledge-and-pm-integrations/lark-approval/"
        "references/lark-approval-instance-form-control-parameters.md",
    },
    "lark-mail": {
        "skills/knowledge-and-pm-integrations/lark-mail/"
        "references/lark-mail-html.md",
    },
    "lark-meeting": {
        "skills/knowledge-and-pm-integrations/lark-meeting/"
        "references/vc-domain-boundaries.md",
    },
    "lark-okr": {
        "skills/knowledge-and-pm-integrations/lark-okr/"
        "references/lark-okr-indicator-update.md",
        "skills/knowledge-and-pm-integrations/lark-okr/"
        "references/lark-okr-indicators.md",
        "skills/knowledge-and-pm-integrations/lark-okr/"
        "references/lark-okr-progress-list.md",
    },
    "lark-slides": {
        "skills/knowledge-and-pm-integrations/lark-slides/"
        "references/visual-planning.md",
    },
}
LOCAL_OVERLAY_DATES = {"lark-meeting": "2026-08-24"}


def _mode(path: Path) -> str:
    return "100755" if stat.S_IMODE(path.stat().st_mode) & 0o111 else "100644"


def test_lark_complete_directory_mirrors_are_exact_and_owned() -> None:
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    entries = {entry["normalized_slug"]: entry for entry in mapping["skills"]}
    assert set(entries) == set(EXPECTED_COUNTS)

    for slug, expected_count in EXPECTED_COUNTS.items():
        entry = entries[slug]
        origin = entry["origins"][0]
        source_root = f"skills/{slug}"
        target_root = f"skills/knowledge-and-pm-integrations/{slug}"
        canonical_root = REPO_ROOT / target_root

        assert entry["kind"] == (
            "overlay" if slug in LOCAL_OVERLAYS else "mirror"
        )
        assert entry["sync_mode"] == "monitor"
        assert len(entry["origins"]) == (
            2 if slug in LOCAL_OVERLAYS else 1
        )
        assert origin["path"] == source_root
        assert origin["sync_mode"] == "monitor"
        if slug in LOCAL_OVERLAYS:
            local_targets = LOCAL_OVERLAYS[slug]
            claimed_targets = {
                artifact["target"] for artifact in origin["artifacts"]
            }
            assert local_targets.isdisjoint(claimed_targets)
            assert len(claimed_targets) == expected_count - len(local_targets)
            local_origin = entry["origins"][1]
            assert local_origin == {
                "repo": "local-repo/curation",
                "path": target_root,
                "license": None,
                "sync_mode": "local-only",
                "artifacts": [
                    {
                        "source": local_target,
                        "target": local_target,
                        "type": "file",
                    }
                    for local_target in sorted(local_targets)
                ],
                "tracking": {
                    "channel": "local",
                    "ref": "local",
                    "resolved_commit": None,
                    "path_commit": None,
                    "content_sha256": None,
                    "last_checked_at": LOCAL_OVERLAY_DATES.get(
                        slug, "2026-08-20"
                    ),
                    "last_synced_at": LOCAL_OVERLAY_DATES.get(
                        slug, "2026-08-20"
                    ),
                },
            }
        else:
            assert origin["artifacts"] == [
                {
                    "source": source_root,
                    "target": target_root,
                    "type": "directory",
                }
            ]
        assert origin["tracking"]["channel"] == "default_branch"
        assert origin["tracking"]["ref"] == "main"
        assert entry["upstream"]["last_synced_commit"] == REVIEWED_COMMIT
        assert entry["upstream"]["path_commit"] == EXPECTED_PATH_COMMITS[slug]
        assert origin["tracking"]["resolved_commit"] == REVIEWED_COMMIT
        assert origin["tracking"]["path_commit"] == EXPECTED_PATH_COMMITS[slug]

        actual = {
            path.relative_to(REPO_ROOT).as_posix(): path
            for path in canonical_files(canonical_root)
        }
        managed = {item["path"]: item for item in entry["managed_files"]}
        assert len(actual) == expected_count
        assert set(actual) == set(managed)
        for repo_path, path in actual.items():
            record = managed[repo_path]
            assert record["owner"] == slug
            assert record["mode"] == _mode(path)
            assert record["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_lark_license_lineage_is_locked_to_reviewed_commit() -> None:
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    expected = {
        "path": "LICENSE",
        "blob_sha": "2b8bbb5e9c46b1abc3a5ac68ee190baf046ba968",
        "content_sha256": (
            "c969fc7e3af68e6bf40b0d8dd9c3dcc377eb685a2139535b203b39fdcad739ee"
        ),
        "spdx": "MIT",
        "resolved_commit": REVIEWED_COMMIT,
        "api_spdx": "MIT",
    }
    for entry in mapping["skills"]:
        assert entry["origins"][0]["tracking"]["license_checkpoint"] == expected


def test_lark_whitespace_adaptations_are_scoped_and_clean() -> None:
    adapted = {
        "skills/knowledge-and-pm-integrations/lark-calendar/SKILL.md",
        *{
            path
            for paths in LOCAL_OVERLAYS.values()
            for path in paths
        },
    }
    for repo_path in adapted:
        lines = (REPO_ROOT / repo_path).read_text(encoding="utf-8").splitlines()
        assert all(line == line.rstrip() for line in lines)

    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    attempts = mapping["verification_attempts"]
    assert len(attempts) == 6
    assert attempts[0]["target"] == (
        f"larksuite/cli@{INITIAL_REVIEWED_COMMIT}"
    )
    assert "whitespace-only" in attempts[0]["evidence"]
    assert attempts[1]["target"] == (
        "larksuite/cli@"
        f"{INITIAL_REVIEWED_COMMIT}.."
        f"{PREVIOUS_REVIEWED_COMMIT}"
    )
    assert "outside the 25 declared artifact sets" in attempts[1]["evidence"]
    assert attempts[2]["target"] == (
        f"larksuite/cli@{PREVIOUS_REVIEWED_COMMIT}..{AUGUST_24_REVIEWED_COMMIT}"
    )
    assert "Merged lark-minutes, lark-vc, and lark-vc-agent" in (
        attempts[2]["evidence"]
    )
    assert attempts[3]["target"] == f"larksuite/cli@{AUGUST_24_REVIEWED_COMMIT}"
    assert "Explicit reviewer checkpoint" in attempts[3]["evidence"]
    assert attempts[4]["target"] == f"larksuite/cli@{AUGUST_31_REVIEWED_COMMIT}"
    assert "Explicit reviewer checkpoint" in attempts[4]["evidence"]
    assert attempts[5]["target"] == f"larksuite/cli@{REVIEWED_COMMIT}"
    assert attempts[5]["result"] == "success"
