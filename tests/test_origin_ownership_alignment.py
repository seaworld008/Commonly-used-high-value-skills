import base64
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts import artifact_set_sync, sync_upstream
from scripts.github_artifact_provider import GitHubArtifactProvider, GitHubUnavailable
from scripts.validate_skill_sources import validate_mapping
from tests.test_sync_upstream import (
    complete_v2_entry,
    external_skill_content,
    git_blob_sha,
)

SKILL_ROOT = "skills/category/demo"
SKILL = f"{SKILL_ROOT}/SKILL.md"
LICENSE = f"{SKILL_ROOT}/LICENSE.upstream.txt"
UPSTREAM_DIR = "upstream/demo"
REPO = "owner/upstream"
COMMIT = "a" * 40


@pytest.fixture
def mapping(tmp_path, monkeypatch):
    content = external_skill_content("demo", REPO)
    (tmp_path / SKILL_ROOT).mkdir(parents=True)
    (tmp_path / SKILL).write_bytes(content)
    license_bytes = (Path(__file__).resolve().parents[1] / "LICENSE").read_bytes()
    (tmp_path / LICENSE).write_bytes(license_bytes)
    entry = complete_v2_entry(
        {
            "normalized_slug": "demo",
            "repo_skill": SKILL,
            "kind": "mirror",
            "origins": [
                {
                    "repo": REPO,
                    "sync_mode": "replace",
                    "tracking": {"channel": "fixed_ref", "ref": COMMIT},
                    "artifacts": [
                        {
                            "source": UPSTREAM_DIR,
                            "target": SKILL_ROOT,
                            "type": "directory",
                        },
                        {"source": "LICENSE", "target": LICENSE, "type": "file"},
                    ],
                }
            ],
        },
        content,
    )
    entry["managed_files"].append(
        {
            "path": LICENSE,
            "owner": "demo",
            "mode": "100644",
            "sha256": hashlib.sha256(license_bytes).hexdigest(),
        }
    )
    path = tmp_path / "docs/sources/demo.skills.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "video": {"url": "https://example.com", "checked_at": "2026-01-01"},
                "official_references": [],
                "skills": [entry],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(sync_upstream, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sync_upstream, "SOURCE_MAPPINGS_DIR", path.parent)
    return path


def provider_for(upstream_files):
    api_root = f"https://api.github.com/repos/{REPO}"
    tree = []
    responses = {
        f"{api_root}/commits/{COMMIT}": {"sha": COMMIT},
        f"{api_root}/git/trees/{COMMIT}?recursive=1": {"tree": tree},
    }
    for path, content in upstream_files.items():
        sha = git_blob_sha(content)
        tree.append({"path": path, "mode": "100644", "type": "blob", "sha": sha})
        responses[f"{api_root}/git/blobs/{sha}"] = {
            "size": len(content),
            "encoding": "base64",
            "content": base64.b64encode(content).decode("ascii"),
        }
    api_get = Mock(side_effect=responses.__getitem__)
    return GitHubArtifactProvider(api_get=api_get), api_get


def snapshot(root):
    return {
        path.relative_to(root): (
            path.stat().st_mode,
            path.read_bytes() if path.is_file() else None,
        )
        for path in root.rglob("*")
    }


@pytest.mark.parametrize(
    "collision", [False, True], ids=["root-license", "colliding-license"]
)
def test_directory_and_root_license_materialization(tmp_path, mapping, collision):
    assert validate_mapping(mapping, tmp_path) == []
    (skill,) = sync_upstream.load_skills_from_source_mappings()
    assert "load_error" not in skill, skill.get("load_error")
    assert skill["upstream_path"] == f"{UPSTREAM_DIR}/SKILL.md"

    content = (tmp_path / SKILL).read_bytes()
    license_bytes = (tmp_path / LICENSE).read_bytes()
    files = {f"{UPSTREAM_DIR}/SKILL.md": content, "LICENSE": license_bytes}
    if collision:
        files[f"{UPSTREAM_DIR}/LICENSE.upstream.txt"] = b"conflicting directory member"
    provider, api_get = provider_for(files)
    args = (skill["repo"], skill["tracking"], skill["artifacts"])
    if collision:
        before = snapshot(tmp_path)
        with pytest.raises(
            GitHubUnavailable, match=f"multiple artifacts claim target {LICENSE}"
        ):
            provider.fetch_artifacts(*args)
        assert not any("/git/blobs/" in call.args[0] for call in api_get.call_args_list)
        assert snapshot(tmp_path) == before
    else:
        inventory = provider.fetch_artifacts(*args)
        assert inventory.files == {SKILL: content, LICENSE: license_bytes}
        assert inventory.modes == {SKILL: "100644", LICENSE: "100644"}


def test_separate_origins_claiming_license_are_rejected(tmp_path, mapping):
    data = json.loads(mapping.read_bytes())
    origins = data["skills"][0]["origins"]
    origin = origins[0]
    # Even two records from the same repository have distinct origin indices.
    origins.append(
        {
            **origin,
            "path": "LICENSE",
            "sync_mode": "archived",
            "artifacts": [origin["artifacts"][1]],
        }
    )
    mapping.write_text(json.dumps(data), encoding="utf-8")

    message = f"managed file {LICENSE!r} must have exactly one artifact owner; found 2"
    assert any(message in error for error in validate_mapping(mapping, tmp_path))
    (skill,) = sync_upstream.load_skills_from_source_mappings()
    assert message in skill["load_error"]


def test_duplicate_declared_target_fails_metadata_validation(tmp_path, mapping):
    data = json.loads(mapping.read_bytes())
    artifacts = data["skills"][0]["origins"][0]["artifacts"]
    artifacts.append({"source": "COPYING", "target": LICENSE, "type": "file"})
    mapping.write_text(json.dumps(data), encoding="utf-8")

    assert any(
        f"duplicate target: {LICENSE}" in error
        for error in validate_mapping(mapping, tmp_path)
    )
    (skill,) = sync_upstream.load_skills_from_source_mappings()
    assert f"duplicate target: {LICENSE}" in skill["load_error"]


def test_duplicate_materialized_payload_fails_before_apply(
    tmp_path, mapping, monkeypatch
):
    entry = json.loads(mapping.read_bytes())["skills"][0]
    payloads = [
        {
            "source": source,
            "target": target,
            "data": content,
            "type": "file",
            "mode": "100644",
        }
        for source, target, content in [
            (f"{UPSTREAM_DIR}/SKILL.md", SKILL, b"updated skill"),
            (f"{UPSTREAM_DIR}/LICENSE.upstream.txt", LICENSE, b"directory member"),
            ("LICENSE", LICENSE, b"root license"),
        ]
    ]
    before = snapshot(tmp_path)
    apply = Mock()
    monkeypatch.setattr(artifact_set_sync, "apply_artifact_set_sync", apply)
    with pytest.raises(
        artifact_set_sync.ArtifactValidationError,
        match=f"duplicate upstream artifact target: {LICENSE}",
    ):
        artifact_set_sync.sync_artifact_set(
            tmp_path, entry, payloads, entry["origins"][0]["tracking"]
        )
    apply.assert_not_called()
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('executable', [False, True])
def test_snapshot_notice_is_not_a_second_update_authority(tmp_path, mapping, executable):
    import copy
    payload = json.loads(mapping.read_text())
    entry = payload['skills'][0]
    entry['kind'], entry['sync_mode'] = 'snapshot', 'local-only'
    primary = entry['origins'][0]
    primary['sync_mode'] = 'local-only'
    primary['artifacts'] = [{'source': UPSTREAM_DIR + '/SKILL.md', 'target': SKILL, 'type': 'file'},
                            {'source': 'LICENSE', 'target': LICENSE, 'type': 'file'}]
    notice = (tmp_path / LICENSE).read_bytes()
    primary['tracking']['license_checkpoint'] = {
        'path': 'LICENSE', 'blob_sha': git_blob_sha(notice),
        'content_sha256': hashlib.sha256(notice).hexdigest(),
        'spdx': 'MIT', 'resolved_commit': primary['tracking']['resolved_commit'],
    }
    secondary = copy.deepcopy(primary)
    secondary['repo'] = 'owner/runtime'
    secondary['path'] = 'LICENSE'
    secondary['sync_mode'] = 'archived'
    secondary['tracking'].update(channel='fixed_ref', ref='b' * 40, resolved_commit='b' * 40,
                                 path_commit='b' * 40)
    secondary['tracking']['license_checkpoint']['resolved_commit'] = 'b' * 40
    target = SKILL_ROOT + ('/extra.py' if executable else '/LICENSE.runtime.txt')
    raw = b'print("runtime")\n' if executable else (tmp_path / LICENSE).read_bytes()
    (tmp_path / target).write_bytes(raw)
    secondary['artifacts'] = [{'source': 'runtime.py' if executable else 'LICENSE',
                              'target': target, 'type': 'file'}]
    entry['origins'].append(secondary)
    entry['managed_files'].append({'path': target, 'owner': 'demo', 'mode': '100644',
                                   'sha256': hashlib.sha256(raw).hexdigest()})
    mapping.write_text(json.dumps(payload))
    loaded, = sync_upstream.load_skills_from_source_mappings()
    if executable:
        assert 'exactly one external origin' in loaded['load_error']
    else:
        assert 'load_error' not in loaded, loaded.get('load_error')
        assert loaded['kind'] == 'snapshot'
        assert loaded['repo'] == REPO
        assert loaded['expected_skip_reason']
