"""Offline integration of declared nested licenses with real provider and sync."""
from __future__ import annotations

import base64
import copy
import hashlib
from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts.github_artifact_provider import GitHubArtifactProvider, GitHubUnavailable
from tests.test_sync_upstream import complete_v2_entry, git_blob_sha, load_module

REPO = "example/nested-skills"
OLD = "a" * 40
CURRENT = "b" * 40
LICENSE_PATH = "skills/docx/LICENSE.txt"
SOURCE = "skills/docx/SKILL.md"
TARGET = "skills/office-white-collar/demo/SKILL.md"
APACHE = (
    Path(__file__).resolve().parents[1]
    / "skills/developer-engineering/mcp-builder/LICENSE.txt"
).read_bytes()
BODY = b"---\nname: demo\nsource: github:example/nested-skills\nlicense: Apache-2.0\n---\n# Demo\n"


def blob_response(raw):
    return {
        "sha": git_blob_sha(raw), "size": len(raw), "encoding": "base64",
        "content": base64.b64encode(raw).decode("ascii"),
    }


def tree_entry(path, raw, **overrides):
    return {
        "path": path, "type": "blob", "mode": "100644",
        "sha": git_blob_sha(raw), "size": len(raw), **overrides,
    }


def checkpoint(path=LICENSE_PATH, commit=OLD):
    return {
        "path": path, "blob_sha": git_blob_sha(APACHE),
        "content_sha256": hashlib.sha256(APACHE).hexdigest(),
        "spdx": "Apache-2.0", "resolved_commit": commit,
    }


class ImmutableAPI:
    """Only explicit synthetic immutable API responses; never uses the network."""

    def __init__(self, error_type=GitHubUnavailable):
        self.responses = {}
        self.calls = []
        self.error_type = error_type

    def add(self, repo, suffix, response):
        self.responses[f"https://api.github.com/repos/{repo}/{suffix}"] = response

    def snapshot(self, commit, files, repo=REPO):
        self.add(repo, f"git/trees/{commit}?recursive=1", {
            "truncated": False,
            "tree": [tree_entry(path, raw) for path, raw in files.items()],
        })
        for raw in files.values():
            self.add(repo, f"git/blobs/{git_blob_sha(raw)}", blob_response(raw))

    def root_license(self, commit=CURRENT):
        self.add(REPO, f"license?ref={commit}", {
            **blob_response(APACHE), "path": "LICENSE",
            "license": {"spdx_id": "Apache-2.0"},
        })

    def __call__(self, url):
        self.calls.append(url)
        if url not in self.responses:
            raise self.error_type(f"synthetic HTTP 404: {url}")
        return copy.deepcopy(self.responses[url])


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("offline test attempted real network")
    monkeypatch.setattr("urllib.request.urlopen", forbidden)


@pytest.fixture
def sync_case(tmp_path, monkeypatch):
    module = load_module()
    module.REPO_ROOT = tmp_path
    monkeypatch.setattr(module, "resolve_github_token", Mock(side_effect=AssertionError("credentials")))
    local = tmp_path / TARGET
    local.parent.mkdir(parents=True)
    local.write_bytes(BODY)
    artifacts = [{"source": SOURCE, "target": TARGET, "type": "file"}]
    tracking = {
        "channel": "default_branch", "ref": "main", "resolved_commit": OLD,
        "path_commit": OLD, "content_sha256": hashlib.sha256(BODY).hexdigest(),
        "license_checkpoint": checkpoint(),
    }
    entry = complete_v2_entry({
        "normalized_slug": "demo", "kind": "overlay", "sync_mode": "monitor",
        "repo_skill": TARGET, "origins": [{
            "repo": REPO, "path": "skills/docx", "license": "Apache-2.0",
            "sync_mode": "monitor", "tracking": tracking, "artifacts": artifacts,
        }],
    }, BODY)
    skill = {
        "schema_version": 2, "name": "demo", "category": "office-white-collar",
        "source": f"github:{REPO}", "repo": REPO, "license": "Apache-2.0",
        "repo_skill": TARGET, "local_path": local, "sync_mode": "monitor",
        "origin_path": "skills/docx", "upstream_path": SOURCE,
        "tracking": copy.deepcopy(entry["origins"][0]["tracking"]),
        "last_synced_commit": OLD, "artifacts": artifacts,
        "managed_files": entry["managed_files"],
        "mapping_entry_index": 0, "origin_index": 0,
        "mapping_fingerprint": module._entry_origin_fingerprint(entry, 0),
    }
    api = ImmutableAPI(error_type=module.GitHubProviderError)
    api.snapshot(CURRENT, {LICENSE_PATH: APACHE, SOURCE: BODY})
    api.add(REPO, "commits/main", {"sha": CURRENT})
    api.add(REPO, f"compare/{OLD}...{CURRENT}", {"status": "ahead", "ahead_by": 1})
    api.add(REPO, f"commits?sha={CURRENT}&path=skills%2Fdocx&per_page=1", [{"sha": CURRENT}])
    # The loader supports CLI and package imports. Inject its own public
    # provider type so failures use the same declared exception namespace.
    provider = module.GitHubArtifactProvider(api_get=api)
    monkeypatch.setattr(module, "_provider_for", lambda _token: provider)
    monkeypatch.setattr(module, "load_skills_with_upstream", lambda **_kwargs: [skill])
    return module, skill, entry, api, provider


def test_nested_apache_without_root_license_is_monitor_only_and_refreshable(sync_case):
    module, skill, entry, api, provider = sync_case
    result = module.check_upstream_changes(skill, None)
    assert result["changes"] == "monitor_review"
    assert result["license_evidence"] == checkpoint(commit=CURRENT)
    assert result["upstream_files"] == {TARGET: BODY}
    assert not any("/license?" in url for url in api.calls)
    assert provider._license_cache == {}
    # Refresh records current license evidence without advancing the body review.
    data = {"skills": [copy.deepcopy(entry)]}
    module._record_v2_result(data, result, synced=False)
    observed = data["skills"][0]["origins"][0]["tracking"]
    assert observed["license_checkpoint"] == checkpoint(commit=CURRENT)
    assert observed["resolved_commit"] == OLD
    apply = Mock(side_effect=AssertionError("monitor source must not apply"))
    module.apply_v2_update = apply
    assert module.main(["--apply"]) == 2
    apply.assert_not_called()
    assert skill["local_path"].read_bytes() == BODY


def test_reviewed_fixed_ref_refresh_uses_only_that_immutable_commit(sync_case):
    module, skill, _entry, api, _provider = sync_case
    skill["tracking"].update(channel="fixed_ref", ref=CURRENT, resolved_commit=CURRENT)
    skill["tracking"]["license_checkpoint"] = checkpoint(commit=CURRENT)
    api.add(REPO, f"commits/{CURRENT}", {"sha": CURRENT})
    result = module.check_upstream_changes(skill, None)
    assert result["changes"] == "none"
    assert result["license_evidence"] == checkpoint(commit=CURRENT)
    assert not any("commits/main" in url or "/license?" in url for url in api.calls)


def test_nested_path_is_part_of_source_fingerprint(sync_case):
    module, skill, entry, _api, _provider = sync_case
    result = module.check_upstream_changes(skill, None)
    data = {"skills": [copy.deepcopy(entry)]}
    data["skills"][0]["origins"][0]["tracking"]["license_checkpoint"]["path"] = "skills/pdf/LICENSE.txt"
    with pytest.raises(RuntimeError, match="changed after upstream check"):
        module._record_v2_result(data, result, synced=False)


@pytest.mark.parametrize("failure", [
    "deleted", "renamed", "restrictive", "unknown", "partial", "invalid-utf8",
    "canonical-drift",
    "symlink", "gitlink", "directory", "bad-mode", "bad-sha",
    "bad-base64", "wrong-hash", "wrong-size", "bool-size", "missing-size",
    "tree-size-mismatch", "tree-bool-size", "tree-missing-size",
])
def test_invalid_current_nested_license_blocks_fetch_refresh_and_apply(sync_case, failure):
    module, skill, _entry, api, provider = sync_case
    # A valid old checkpoint and permissive current root cannot rescue this path.
    api.snapshot(OLD, {LICENSE_PATH: APACHE})
    provider.license_evidence_at_path(REPO, OLD, LICENSE_PATH)
    api.calls.clear()
    api.root_license()
    tree = api.responses[f"https://api.github.com/repos/{REPO}/git/trees/{CURRENT}?recursive=1"]["tree"]
    item = tree[0]
    blob = api.responses[f"https://api.github.com/repos/{REPO}/git/blobs/{git_blob_sha(APACHE)}"]
    if failure == "deleted":
        tree.remove(item)
    elif failure == "renamed":
        item["path"] = "skills/other/LICENSE.txt"
    elif failure in {"restrictive", "unknown", "partial", "invalid-utf8", "canonical-drift"}:
        raw = {
            "restrictive": APACHE + b"\nAdditional terms: commercial use forbidden.\n",
            "unknown": b"All rights reserved. Proprietary license.\n",
            "partial": APACHE[:1000], "invalid-utf8": b"\xff" + APACHE,
            "canonical-drift": APACHE.replace(b"\n", b"\r\n"),
        }[failure]
        item.update(tree_entry(LICENSE_PATH, raw))
        api.add(REPO, f"git/blobs/{git_blob_sha(raw)}", blob_response(raw))
    elif failure in {"symlink", "gitlink", "directory", "bad-mode"}:
        mode, kind = {
            "symlink": ("120000", "blob"), "gitlink": ("160000", "commit"),
            "directory": ("040000", "tree"), "bad-mode": ("100600", "blob"),
        }[failure]
        item.update(mode=mode, type=kind)
    elif failure == "bad-sha":
        item["sha"] = "not-a-sha"
    elif failure == "bad-base64":
        blob["content"] = "@@@="
    elif failure == "wrong-hash":
        item["sha"] = "c" * 40
        api.add(REPO, "git/blobs/" + "c" * 40, blob)
    elif failure == "wrong-size":
        blob["size"] += 1
    elif failure == "bool-size":
        blob["size"] = True
    elif failure == "missing-size":
        blob.pop("size")
    elif failure == "tree-size-mismatch":
        item["size"] += 1
    elif failure == "tree-bool-size":
        item["size"] = True
    elif failure == "tree-missing-size":
        item.pop("size")
    # Clear the valid content-addressed cache only to exercise corrupt transport.
    if failure in {"bad-base64", "wrong-size", "bool-size", "missing-size"}:
        provider._blob_cache.clear()
        provider._json_cache.pop(f"https://api.github.com/repos/{REPO}/git/blobs/{git_blob_sha(APACHE)}", None)
    result = module.check_upstream_changes(skill, None)
    assert result["changes"] == "unavailable", result
    assert "upstream_files" not in result
    module.record_v2_checks([result])
    apply = Mock(side_effect=AssertionError("unavailable must not apply"))
    module.apply_v2_update = apply
    assert module.main(["--apply"]) == 1
    apply.assert_not_called()
    assert skill["local_path"].read_bytes() == BODY
    assert not any("/license?" in url or OLD in url for url in api.calls)
    assert not any(f"git/blobs/{git_blob_sha(BODY)}" in url for url in api.calls)
    if failure == "canonical-drift":
        assert "immutable license evidence changed" in result["reason"]
    else:
        assert (REPO, CURRENT, LICENSE_PATH) not in provider._path_license_cache


def test_cache_is_scoped_by_repo_commit_path_and_separate_from_root():
    api = ImmutableAPI()
    second_path = "skills/pdf/LICENSE.txt"
    other_repo = "example/another-repo"
    changed = APACHE.replace(b"\n", b"\r\n")
    api.snapshot(OLD, {LICENSE_PATH: APACHE, second_path: changed})
    api.snapshot(CURRENT, {LICENSE_PATH: changed})
    api.snapshot(OLD, {LICENSE_PATH: changed}, repo=other_repo)
    api.add(other_repo, f"git/trees/{CURRENT}?recursive=1", {"tree": []})
    api.root_license(OLD)
    provider = GitHubArtifactProvider(api_get=api)
    keys = [(REPO, OLD, LICENSE_PATH), (REPO, OLD, second_path),
            (REPO, CURRENT, LICENSE_PATH), (other_repo, OLD, LICENSE_PATH)]
    evidence = [provider.license_evidence_at_path(*key) for key in keys]
    assert [item.path for item in evidence] == [key[2] for key in keys]
    assert [item.resolved_commit for item in evidence] == [key[1] for key in keys]
    assert evidence[0].content_sha256 != evidence[1].content_sha256
    assert evidence[0].content_sha256 != evidence[2].content_sha256
    calls = list(api.calls)
    assert [provider.license_evidence_at_path(*key) for key in keys] == evidence
    assert api.calls == calls
    assert provider.license_evidence(REPO, OLD).path == "LICENSE"
    assert set(provider._path_license_cache) == set(keys)
    assert set(provider._license_cache) == {(REPO, OLD)}
    with pytest.raises(GitHubUnavailable):
        provider.license_evidence_at_path(other_repo, CURRENT, LICENSE_PATH)
    with pytest.raises(GitHubUnavailable):
        provider.license_evidence_at_path(REPO, CURRENT, second_path)


@pytest.mark.parametrize("path", ["../LICENSE", "/LICENSE", "skills//LICENSE", "skills/./LICENSE", "skills/../LICENSE", "skills\\LICENSE", "skills/LICENSE\n", "", None])
def test_unsafe_paths_fail_before_api(path):
    api = Mock(side_effect=AssertionError("invalid paths must not reach API"))
    with pytest.raises(GitHubUnavailable, match="invalid license path"):
        GitHubArtifactProvider(api_get=api).license_evidence_at_path(REPO, CURRENT, path)
    api.assert_not_called()


@pytest.mark.parametrize("commit", ["main", "b" * 39, None])
def test_nonimmutable_refs_fail_before_api(commit):
    api = Mock(side_effect=AssertionError("mutable refs must not reach API"))
    with pytest.raises(GitHubUnavailable, match="full immutable commit"):
        GitHubArtifactProvider(api_get=api).license_evidence_at_path(REPO, commit, LICENSE_PATH)
    api.assert_not_called()


@pytest.mark.parametrize("declared_root", [False, True])
@pytest.mark.parametrize("root_present", [False, True])
def test_undeclared_nested_path_keeps_root_api_route(sync_case, declared_root, root_present):
    module, skill, _entry, api, provider = sync_case
    if declared_root:
        skill["tracking"]["license_checkpoint"] = checkpoint(path="LICENSE")
    else:
        skill["tracking"].pop("license_checkpoint")
    if root_present:
        api.root_license()
    result = module.check_upstream_changes(skill, None)
    assert result["changes"] == ("monitor_review" if root_present else "unavailable")
    assert any(f"/license?ref={CURRENT}" in url for url in api.calls)
    assert provider._path_license_cache == {}
    assert not any(f"git/blobs/{git_blob_sha(APACHE)}" in url for url in api.calls)
    if root_present:
        assert result["license_evidence"]["path"] == "LICENSE"
    else:
        assert not any("git/trees/" in url for url in api.calls)


def test_complete_reviewed_apache_variants_reject_legal_text_changes():
    from pathlib import Path
    from scripts.github_artifact_provider import GitHubArtifactProvider
    text = (Path(__file__).resolve().parents[1] /
            'skills/developer-engineering/mcp-builder/LICENSE.txt').read_text()
    variants = [text.replace('Copyright [yyyy] [name of copyright owner]',
                             'Copyright 2026 Anthropic, PBC.'),
                text.split('APPENDIX:', 1)[0]]
    for variant in variants:
        assert GitHubArtifactProvider._detect_license_spdx(variant.encode()) == ('Apache-2.0',)
        assert GitHubArtifactProvider._detect_license_spdx(
            (variant + '\nRedistribution is prohibited.\n').encode()) == ()
        assert GitHubArtifactProvider._detect_license_spdx(
            variant.replace('Grant of Patent License', 'No Patent License').encode()) == ()


def test_package_sync_catches_provider_errors_with_both_import_styles():
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    code = r'''
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "scripts"))
import github_artifact_provider  # A host exposes the script import path first.
from scripts import sync_upstream
from scripts.github_artifact_provider import GitHubArtifactProvider
provider = GitHubArtifactProvider(api_get=lambda _: (_ for _ in ()).throw(AssertionError("no I/O")))
try:
    provider.license_evidence_at_path("owner/repo", "a" * 40, "../LICENSE")
except sync_upstream.GitHubProviderError:
    pass
else:
    raise AssertionError("invalid path was not rejected")
'''
    result = subprocess.run([sys.executable, '-c', code], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
