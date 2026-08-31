"""Cross-mapping upgrades require reviewed compatibility and crash recovery."""
import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.test_sync_upstream import complete_v2_entry, load_module, mock_license_checkpoint


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fixture(root):
    module = load_module()
    module.REPO_ROOT = root
    module.SOURCE_MAPPINGS_DIR = root / "docs/sources"
    module.SOURCE_MAPPINGS_DIR.mkdir(parents=True)
    target = "skills/ai-workflow/demo/SKILL.md"
    main = root / target
    main.parent.mkdir(parents=True)
    old = b"---\nname: demo\nsource: github:owner/repo\nlicense: MIT\n---\n# Old\n"
    main.write_bytes(old)
    artifacts = [{"source": "SKILL.md", "target": target, "type": "file"}]
    entry = complete_v2_entry({
        "normalized_slug": "demo", "kind": "mirror", "sync_mode": "replace",
        "repo_skill": target, "origins": [{
            "repo": "owner/repo", "path": "SKILL.md", "license": "MIT",
            "sync_mode": "replace", "artifacts": artifacts,
            "tracking": {"channel": "latest_release", "ref": "v1.0.0",
                         "resolved_commit": "a" * 40, "path_commit": "a" * 40,
                         "content_sha256": sha(old)},
        }],
    }, old)
    owner = module.SOURCE_MAPPINGS_DIR / "z-owner.skills.json"
    owner.write_text(json.dumps({"schema_version": 2, "video": {}, "official_references": [], "skills": [entry]}))
    composite_target = "skills/ai-workflow/workflow/SKILL.md"
    composite = root / composite_target
    composite.parent.mkdir(parents=True)
    content = b"---\nname: workflow\nsource: in-house\n---\n# Reviewed workflow\n"
    composite.write_bytes(content)
    dependent = {
        "normalized_slug": "workflow", "video_name": "workflow",
        "kind": "composite", "status": "in_house", "notes": "Reviewed fixture.",
        "source": "https://github.com/local-repo/in-house", "sync_mode": "local-only",
        "repo_skill": composite_target,
        "origins": [{
            "repo": "local-repo/in-house", "path": "skills/ai-workflow/workflow",
            "license": "MIT", "sync_mode": "local-only",
            "artifacts": [{"source": composite_target, "target": composite_target, "type": "file"}],
            "tracking": {"channel": "local", "ref": "local",
                         "resolved_commit": None, "path_commit": None,
                         "last_checked_at": "2026-08-31", "last_synced_at": "2026-08-31",
                         "content_sha256": sha(content)},
        }],
        "managed_files": [{"path": composite_target, "sha256": sha(content),
                           "owner": "workflow", "mode": "100644"}],
        "composition": {"depends_on": [{"skill": "demo", "role": "runtime"}],
                        "dependency_lock": {"demo": sha(old)}},
        "upstream": {"repo": "local-repo/in-house", "path": "skills/ai-workflow/workflow",
                     "ref": "local", "sync_mode": "local-only",
                     "last_checked_at": "2026-08-31", "last_synced_at": "2026-08-31",
                     "last_synced_commit": None},
    }
    dependency = module.SOURCE_MAPPINGS_DIR / "a-dependent.skills.json"
    dependency.write_text(json.dumps({"schema_version": 2, "video": {}, "official_references": [], "skills": [dependent]}))
    skill = {
        "name": "demo", "schema_version": 2, "repo": "owner/repo",
        "repo_skill": target, "sync_mode": "replace",
        "tracking": {"channel": "latest_release", "ref": "v1.0.0"},
        "artifacts": artifacts, "mapping_path": owner, "mapping_entry_index": 0,
        "origin_index": 0, "local_path": main,
        "mapping_fingerprint": module._entry_origin_fingerprint(entry, 0),
    }
    update = {
        "skill": skill, "changes": "artifact_changed",
        "current_commit": "b" * 40, "path_commit": "b" * 40,
        "resolved_ref": "v2.0.0", "license_evidence": mock_license_checkpoint(),
        "upstream_files": {target: b"---\nname: demo\n---\n# New\n"},
        "source_blobs": {"SKILL.md": "1" * 40},
        "upstream_modes": {target: "100644"},
    }
    return module, update, {"workflow": sha(content)}, [main, owner, dependency]


def assert_consistent(module, paths):
    main, owner, dependency = paths
    owner_data = json.loads(owner.read_text())
    dependent_data = json.loads(dependency.read_text())
    assert owner_data["skills"][0]["origins"][0]["tracking"]["content_sha256"] == sha(main.read_bytes())
    assert dependent_data["skills"][0]["composition"]["dependency_lock"]["demo"] == sha(main.read_bytes())
    module._validate_candidate_mappings({owner: owner_data, dependency: dependent_data})


def test_reviewed_composite_and_owner_commit_together(tmp_path):
    from scripts.export_openclaw_skills import normalize_skill_markdown
    module, update, approvals, paths = fixture(tmp_path)
    module.apply_v2_update(update, reviewed_dependents=approvals)
    assert b"# New" in paths[0].read_bytes()
    assert normalize_skill_markdown("demo", paths[0].read_text()) == paths[0].read_text()
    assert_consistent(module, paths)


@pytest.mark.parametrize("approval", [None, {"workflow": "f" * 64}])
def test_missing_or_stale_review_preserves_every_byte(tmp_path, approval):
    module, update, _, paths = fixture(tmp_path)
    before = [path.read_bytes() for path in paths]
    with pytest.raises(RuntimeError, match="requires explicit review"):
        module.apply_v2_update(update, reviewed_dependents=approval)
    assert [path.read_bytes() for path in paths] == before


def test_existing_stale_dependency_lock_is_not_silently_repaired(tmp_path):
    module, update, approvals, paths = fixture(tmp_path)
    document = json.loads(paths[2].read_text())
    document["skills"][0]["composition"]["dependency_lock"]["demo"] = "f" * 64
    paths[2].write_text(json.dumps(document))
    before = [path.read_bytes() for path in paths]
    with pytest.raises(RuntimeError, match="stale baseline"):
        module.apply_v2_update(update, reviewed_dependents=approvals)
    assert [path.read_bytes() for path in paths] == before


def test_direct_skill_recovery_refuses_pending_mapping_batch(tmp_path):
    module, _, _, _ = fixture(tmp_path)
    pending = tmp_path / ".hvs-transactions/pending"
    pending.mkdir(parents=True)
    engine = module._load_artifact_engine()
    with pytest.raises(engine.ArtifactRecoveryError, match="durable mapping batch"):
        with engine.skill_advisory_lock(tmp_path, "skills/ai-workflow/demo"):
            pytest.fail("must not recover artifacts ahead of mappings")


def test_dependent_edit_after_candidate_validation_preserves_user_change(tmp_path):
    module, update, approvals, paths = fixture(tmp_path)
    before = [path.read_bytes() for path in paths]
    validate = module._validate_candidate_mappings
    dependent = tmp_path / "skills/ai-workflow/workflow/SKILL.md"

    def edit_after_validation(prepared):
        validate(prepared)
        dependent.write_bytes(b"User's concurrent edit must survive\n")

    with patch.object(module, "_validate_candidate_mappings", side_effect=edit_after_validation):
        with pytest.raises(RuntimeError, match="changed before atomic replacement"):
            module.apply_v2_update(update, reviewed_dependents=approvals)
    assert [path.read_bytes() for path in paths] == before
    assert dependent.read_bytes() == b"User's concurrent edit must survive\n"


def test_same_mapping_owner_and_composite_are_supported(tmp_path):
    module, update, approvals, paths = fixture(tmp_path)
    owner_data = json.loads(paths[1].read_text())
    dependent_data = json.loads(paths[2].read_text())
    owner_data["skills"].extend(dependent_data["skills"])
    paths[1].write_text(json.dumps(owner_data))
    paths[2].unlink()
    module.apply_v2_update(update, reviewed_dependents=approvals)
    result = json.loads(paths[1].read_text())
    assert result["skills"][1]["composition"]["dependency_lock"]["demo"] == sha(paths[0].read_bytes())
    module._validate_candidate_mappings({paths[1]: result})


@pytest.mark.parametrize("replacement_number", [1, 2])
def test_mapping_batch_exception_rolls_back_tree_and_both_mappings(tmp_path, replacement_number):
    module, update, approvals, paths = fixture(tmp_path)
    before = [path.read_bytes() for path in paths]
    writer = module._atomic_write_json_batch_locked
    count = 0

    def fail(event, path):
        nonlocal count
        if event == "after_replace":
            count += 1
            if count == replacement_number:
                raise RuntimeError("injected mapping fault")

    def inject(*args, **kwargs):
        return writer(*args, **{**kwargs, "fault_injector": fail})

    with patch.object(module, "_atomic_write_json_batch_locked", side_effect=inject):
        with pytest.raises(RuntimeError):
            module.apply_v2_update(update, reviewed_dependents=approvals)
    assert [path.read_bytes() for path in paths] == before
    assert_consistent(module, paths)


@pytest.mark.skipif(not hasattr(os, "fork"), reason="POSIX transaction contract")
@pytest.mark.parametrize("event", ["prepared", "authority", "first_mapping", "last_mapping", "before_commit"])
def test_hard_exit_recovers_mapping_batch_before_artifact_authority(tmp_path, event):
    module, update, approvals, paths = fixture(tmp_path)
    before = [path.read_bytes() for path in paths]
    engine = module._load_artifact_engine()
    pid = os.fork()
    if pid == 0:
        def exit_now(*args, **kwargs):
            os._exit(77)

        if event in {"prepared", "authority", "before_commit"}:
            if event == "prepared":
                module._validate_candidate_mappings = exit_now
            elif event == "authority":
                module.atomic_write_json_batch = exit_now
            else:
                engine.ArtifactTransaction.commit = exit_now
        else:
            original = module._atomic_write_json_batch_locked
            count = [0]

            def fault(name, path):
                if name == "after_replace":
                    count[0] += 1
                    if count[0] == (1 if event == "first_mapping" else 2):
                        os._exit(77)

            def inject(*args, **kwargs):
                return original(*args, **{**kwargs, "fault_injector": fault})
            module._atomic_write_json_batch_locked = inject
        try:
            module.apply_v2_update(update, reviewed_dependents=approvals)
        finally:
            os._exit(78)
    _, status = os.waitpid(pid, 0)
    assert os.waitstatus_to_exitcode(status) == 77
    # The public skill lock also recovers the tree journal. Use the same
    # global -> mapping -> skill recovery ordering as the coordinator.
    with module.durable_batch_lock_and_recover(tmp_path):
        with engine.skill_advisory_lock(tmp_path, "skills/ai-workflow/demo"):
            pass
    assert_consistent(module, paths)
    if event in {"last_mapping", "before_commit"}:
        assert b"# New" in paths[0].read_bytes()
    else:
        assert [path.read_bytes() for path in paths] == before
    assert not (tmp_path / ".hvs-transactions/pending").exists()
