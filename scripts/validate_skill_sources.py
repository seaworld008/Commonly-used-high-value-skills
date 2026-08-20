#!/usr/bin/env python3
"""Validate skill source mapping JSON files against repository skill files.

Default behavior validates all `docs/sources/*.skills.json` mappings.
"""
from __future__ import annotations

import argparse
import json
import re
import stat
from pathlib import Path, PurePosixPath

try:
    from provenance_v2 import (
        ACTIVE_STATUSES,
        COMMIT_RE,
        DATE_RE as V2_DATE_RE,
        EXTERNAL_KINDS,
        SCHEMA_VERSION,
        SHA256_RE,
        UNKNOWN_LICENSE_VALUES,
        VALID_CHANNELS,
        VALID_KINDS,
        VALID_SYNC_MODES,
        discover_source_mappings,
        github_repo,
        infer_channel,
        is_local_repo,
        is_local_source,
        normalize_sync_mode,
        parse_frontmatter,
        safe_relative_path,
        sha256_file,
    )
except ModuleNotFoundError:  # pragma: no cover - import path used by unit tests
    from scripts.provenance_v2 import (
        ACTIVE_STATUSES,
        COMMIT_RE,
        DATE_RE as V2_DATE_RE,
        EXTERNAL_KINDS,
        SCHEMA_VERSION,
        SHA256_RE,
        UNKNOWN_LICENSE_VALUES,
        VALID_CHANNELS,
        VALID_KINDS,
        VALID_SYNC_MODES,
        discover_source_mappings,
        github_repo,
        infer_channel,
        is_local_repo,
        is_local_source,
        normalize_sync_mode,
        parse_frontmatter,
        safe_relative_path,
        sha256_file,
    )

REQUIRED_TOP = {"video", "official_references", "skills"}
REQUIRED_SKILL_KEYS = {"video_name", "normalized_slug", "status", "repo_skill", "source", "notes"}
VALID_STATUS = {
    "verified_in_repo",
    "verified_not_in_repo",
    "not_a_skill",
    "unverified_slug",
    "in_house",
    "retired",
}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URL_RE = re.compile(r"^https?://")


def parse_name_from_skill_md(path: Path) -> str | None:
    return parse_frontmatter(path).get("name")


def _repository_file_issues(
    repo_root: Path,
    relative_path: str,
) -> tuple[Path, list[str]]:
    """Inspect a repository-owned file without following manifest symlinks."""
    candidate = repo_root / relative_path
    issues: list[str] = []

    resolved_root = repo_root.resolve()
    try:
        resolved_candidate = candidate.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        issues.append(f"cannot be resolved safely: {exc}")
    else:
        if not resolved_candidate.is_relative_to(resolved_root):
            issues.append("resolves outside the repository root")

    current = repo_root
    relative_parts = PurePosixPath(relative_path.replace("\\", "/")).parts
    for part in relative_parts[:-1]:
        current = current / part
        try:
            component_stat = current.lstat()
        except FileNotFoundError:
            break
        except OSError as exc:
            issues.append(f"parent component {current} cannot be inspected: {exc}")
            break
        if stat.S_ISLNK(component_stat.st_mode):
            issues.append(f"parent component {current} is a symlink")
            break
        if not stat.S_ISDIR(component_stat.st_mode):
            issues.append(f"parent component {current} is not a directory")
            break

    try:
        candidate_stat = candidate.lstat()
    except FileNotFoundError:
        issues.append("is missing")
    except OSError as exc:
        issues.append(f"cannot be inspected: {exc}")
    else:
        if stat.S_ISLNK(candidate_stat.st_mode):
            issues.append("must not be a symlink")
        elif not stat.S_ISREG(candidate_stat.st_mode):
            issues.append("must be a regular file")

    return candidate, issues


def _safe_repository_file(repo_root: Path, relative_path: str) -> Path | None:
    candidate, issues = _repository_file_issues(repo_root, relative_path)
    return None if issues else candidate


def _canonical_repo_skill_path(item: dict) -> PurePosixPath | None:
    """Return the trusted canonical path for an active repository skill.

    A safe relative path is not sufficient here: provenance entries may only
    claim the canonical four-segment skill entrypoint.  Keeping this predicate
    centralized prevents dependency and containment checks from accepting a
    different repository file merely because it happens to exist.
    """
    if item.get("status") not in ACTIVE_STATUSES:
        return None
    slug = item.get("normalized_slug")
    repo_skill = item.get("repo_skill")
    if (
        not isinstance(slug, str)
        or not slug
        or not isinstance(repo_skill, str)
        or not safe_relative_path(repo_skill)
    ):
        return None
    path = PurePosixPath(repo_skill)
    if (
        len(path.parts) != 4
        or path.parts[0] != "skills"
        or path.parts[2] != slug
        or path.parts[3] != "SKILL.md"
    ):
        return None
    return path


def _active_canonical_skill_available(item: dict, repo_root: Path) -> bool:
    """Whether an entry is an active, canonical, locally available skill."""
    repo_skill = _canonical_repo_skill_path(item)
    if repo_skill is None:
        return False
    return _safe_repository_file(repo_root, repo_skill.as_posix()) is not None


def _validate_top(
    data: dict,
    mapping: Path,
    errors: list[str],
    *,
    allow_v1: bool,
) -> None:
    missing_top = REQUIRED_TOP - set(data.keys())
    if missing_top:
        errors.append(f"{mapping}: missing top-level keys: {sorted(missing_top)}")

    video = data.get("video", {})
    checked = video.get("checked_at")
    if checked and not DATE_RE.match(str(checked)):
        errors.append(f"{mapping}: video.checked_at should be YYYY-MM-DD")

    version = data.get("schema_version")
    if version != SCHEMA_VERSION and not (
        allow_v1 and version in {None, 1}
    ):
        errors.append(
            f"{mapping}: schema_version must be {SCHEMA_VERSION}; "
            f"got {version!r}"
        )


def _validate_verification_attempts(data: dict, mapping: Path, errors: list[str]) -> None:
    attempts = data.get("verification_attempts", [])
    if attempts and not isinstance(attempts, list):
        errors.append(f"{mapping}: verification_attempts must be an array")
        return
    for i, item in enumerate(attempts, 1):
        d = item.get("date")
        if d and not DATE_RE.match(str(d)):
            errors.append(f"{mapping}: verification_attempts[{i}].date must be YYYY-MM-DD")




def _validate_upstream(item: dict, mapping: Path, idx: int, errors: list[str]) -> None:
    upstream = item.get("upstream")
    if upstream is None:
        return
    if not isinstance(upstream, dict):
        errors.append(f"{mapping}: skills[{idx}] upstream must be an object")
        return

    for key in ("last_checked_at", "last_synced_at"):
        val = upstream.get(key)
        if val and not DATE_RE.match(str(val)):
            errors.append(f"{mapping}: skills[{idx}] upstream.{key} must be YYYY-MM-DD")

    repo = upstream.get("repo")
    if repo and "/" not in str(repo):
        errors.append(f"{mapping}: skills[{idx}] upstream.repo should look like owner/repo")


def _validate_tracking(
    tracking: object,
    mapping: Path,
    idx: int,
    origin_idx: int,
    *,
    local: bool,
    errors: list[str],
) -> None:
    label = f"{mapping}: skills[{idx}].origins[{origin_idx}].tracking"
    if not isinstance(tracking, dict):
        errors.append(f"{label} must be an object")
        return

    required = {
        "channel",
        "ref",
        "resolved_commit",
        "path_commit",
        "content_sha256",
        "last_checked_at",
        "last_synced_at",
    }
    missing = required - set(tracking)
    if missing:
        errors.append(f"{label} missing keys: {sorted(missing)}")

    channel = tracking.get("channel")
    if channel not in VALID_CHANNELS:
        errors.append(f"{label}.channel invalid: {channel!r}")
    elif local and channel != "local":
        errors.append(f"{label}.channel must be 'local' for a local origin")
    elif not local and channel == "local":
        errors.append(f"{label}.channel cannot be 'local' for an external origin")

    ref = tracking.get("ref")
    if not isinstance(ref, str) or not ref:
        errors.append(f"{label}.ref must be a non-empty string")

    for key in ("resolved_commit", "path_commit"):
        value = tracking.get(key)
        if value is not None and (
            not isinstance(value, str) or not COMMIT_RE.fullmatch(value)
        ):
            errors.append(f"{label}.{key} must be a full Git commit hash or null")

    content_hash = tracking.get("content_sha256")
    if content_hash is not None and (
        not isinstance(content_hash, str) or not SHA256_RE.fullmatch(content_hash)
    ):
        errors.append(f"{label}.content_sha256 must be a SHA-256 hash or null")

    for key in ("last_checked_at", "last_synced_at"):
        value = tracking.get(key)
        if value and not V2_DATE_RE.fullmatch(str(value)):
            errors.append(f"{label}.{key} must be YYYY-MM-DD or null")


def _validate_artifacts(
    artifacts: object,
    mapping: Path,
    idx: int,
    origin_idx: int,
    errors: list[str],
) -> None:
    label = f"{mapping}: skills[{idx}].origins[{origin_idx}].artifacts"
    if not isinstance(artifacts, list):
        errors.append(f"{label} must be an array")
        return
    seen_targets: set[str] = set()
    for artifact_idx, artifact in enumerate(artifacts, 1):
        item_label = f"{label}[{artifact_idx}]"
        if not isinstance(artifact, dict):
            errors.append(f"{item_label} must be an object")
            continue
        missing = {"source", "target"} - set(artifact)
        if missing:
            errors.append(f"{item_label} missing keys: {sorted(missing)}")
            continue
        for key in ("source", "target"):
            if not safe_relative_path(artifact.get(key)):
                errors.append(f"{item_label}.{key} must be a safe relative path")
        artifact_type = artifact.get("type", "file")
        if artifact_type not in {"file", "directory"}:
            errors.append(f"{item_label}.type must be 'file' or 'directory'")
        target = artifact.get("target")
        if isinstance(target, str):
            if target in seen_targets:
                errors.append(f"{label} has duplicate target: {target}")
            seen_targets.add(target)


def _artifact_owns_repo_skill(artifact: object, repo_skill: str) -> bool:
    if not isinstance(artifact, dict):
        return False
    target = artifact.get("target")
    if not safe_relative_path(target) or not safe_relative_path(repo_skill):
        return False
    target_path = PurePosixPath(str(target))
    repo_skill_path = PurePosixPath(repo_skill)
    if artifact.get("type", "file") == "directory":
        return (
            repo_skill_path == target_path
            or target_path in repo_skill_path.parents
        )
    return target_path == repo_skill_path


def _validate_origin(
    origin: object,
    mapping: Path,
    idx: int,
    origin_idx: int,
    *,
    kind: str,
    status: str | None,
    entry_sync_mode: object,
    legacy_sync_mode: object,
    errors: list[str],
) -> None:
    label = f"{mapping}: skills[{idx}].origins[{origin_idx}]"
    if not isinstance(origin, dict):
        errors.append(f"{label} must be an object")
        return

    required = {"repo", "path", "license", "sync_mode", "artifacts", "tracking"}
    missing = required - set(origin)
    if missing:
        errors.append(f"{label} missing keys: {sorted(missing)}")

    repo = origin.get("repo")
    if not isinstance(repo, str) or "/" not in repo:
        errors.append(f"{label}.repo must look like owner/repo")
        local = False
    else:
        local = is_local_repo(repo)

    origin_path = origin.get("path")
    if origin_path is not None and not safe_relative_path(origin_path):
        errors.append(f"{label}.path must be a safe relative path or null")

    if kind in EXTERNAL_KINDS and local:
        errors.append(f"{label} must be an external origin for kind {kind}")
    if kind == "in_house" and not local:
        errors.append(f"{label} must be local for kind in_house")

    license_value = origin.get("license")
    if not local and (
        not isinstance(license_value, str)
        or license_value.strip().lower() in UNKNOWN_LICENSE_VALUES
    ):
        errors.append(f"{label}.license must declare an external origin license")

    sync_mode = origin.get("sync_mode")
    if sync_mode not in VALID_SYNC_MODES:
        errors.append(f"{label}.sync_mode invalid: {sync_mode!r}")
    else:
        if sync_mode != entry_sync_mode:
            errors.append(
                f"{label}.sync_mode must match entry sync_mode "
                f"{entry_sync_mode!r}"
            )
        if legacy_sync_mode is not None and sync_mode != legacy_sync_mode:
            errors.append(
                f"{label}.sync_mode must match legacy upstream.sync_mode "
                f"{legacy_sync_mode!r}"
            )

    _validate_artifacts(origin.get("artifacts"), mapping, idx, origin_idx, errors)
    tracking = origin.get("tracking")
    _validate_tracking(
        tracking,
        mapping,
        idx,
        origin_idx,
        local=local,
        errors=errors,
    )
    if not local and isinstance(tracking, dict):
        channel = tracking.get("channel")
        ref = tracking.get("ref")
        if (
            isinstance(ref, str)
            and channel in VALID_CHANNELS
            and channel != infer_channel(ref, repo)
        ):
            errors.append(
                f"{label}.tracking.channel {channel!r} conflicts with "
                f"ref {ref!r}"
            )
    if sync_mode in VALID_SYNC_MODES:
        expected_mode = normalize_sync_mode(
            kind=kind,
            tracking=tracking,
            repo=repo if isinstance(repo, str) else None,
            requested_mode=sync_mode,
            status=status,
        )
        if sync_mode != expected_mode:
            errors.append(
                f"{label}.sync_mode {sync_mode!r} violates release-channel "
                f"policy; expected {expected_mode!r}"
            )


def _validate_legacy_owner_consistency(
    item: dict,
    mapping: Path,
    idx: int,
    origins: list,
    errors: list[str],
) -> None:
    """Require one origin/artifact owner and align its legacy projection."""
    repo_skill = item.get("repo_skill")
    if not isinstance(repo_skill, str) or not safe_relative_path(repo_skill):
        return

    owners: list[tuple[int, dict, int, dict]] = []
    for origin_idx, origin in enumerate(origins, 1):
        if not isinstance(origin, dict):
            continue
        artifacts = origin.get("artifacts")
        if not isinstance(artifacts, list):
            continue
        for artifact_idx, artifact in enumerate(artifacts, 1):
            if (
                isinstance(artifact, dict)
                and _artifact_owns_repo_skill(artifact, repo_skill)
            ):
                owners.append((origin_idx, origin, artifact_idx, artifact))

    label = f"{mapping}: skills[{idx}]"
    if len(owners) != 1:
        errors.append(
            f"{label} repo_skill must have exactly one responsible "
            f"origin/artifact; found {len(owners)}"
        )
        return

    origin_idx, origin, artifact_idx, artifact = owners[0]
    owner_label = (
        f"{label}.origins[{origin_idx}].artifacts[{artifact_idx}]"
    )
    upstream = item.get("upstream")
    if not isinstance(upstream, dict):
        errors.append(f"{label}.upstream is required for the repo_skill owner")
        return
    tracking = origin.get("tracking")
    if not isinstance(tracking, dict):
        return

    repo = origin.get("repo")
    local = isinstance(repo, str) and is_local_repo(repo)
    expected_path = origin.get("path") if local else artifact.get("source")
    comparisons = (
        ("repo", upstream.get("repo"), repo),
        ("path", upstream.get("path"), expected_path),
        ("ref", upstream.get("ref"), tracking.get("ref")),
        ("sync_mode", upstream.get("sync_mode"), origin.get("sync_mode")),
        (
            "last_checked_at",
            upstream.get("last_checked_at"),
            tracking.get("last_checked_at"),
        ),
        (
            "last_synced_at",
            upstream.get("last_synced_at"),
            tracking.get("last_synced_at"),
        ),
    )
    for field, legacy_value, owner_value in comparisons:
        if legacy_value != owner_value:
            errors.append(
                f"{label}.upstream.{field} must match responsible owner "
                f"{owner_value!r}; got {legacy_value!r}"
            )

    if local:
        expected_directory = PurePosixPath(repo_skill).parent.as_posix()
        if origin.get("path") != expected_directory:
            errors.append(
                f"{owner_label} local origin path must be repo_skill "
                f"directory {expected_directory!r}"
            )
        if artifact.get("source") != repo_skill:
            errors.append(
                f"{owner_label}.source must match local repo_skill "
                f"{repo_skill!r}"
            )

    legacy_commit = upstream.get("last_synced_commit")
    if legacy_commit not in {None, ""} and (
        legacy_commit != tracking.get("resolved_commit")
    ):
        errors.append(
            f"{label}.upstream.last_synced_commit must match responsible "
            "owner resolved_commit"
        )


def _validate_composition(
    item: dict,
    mapping: Path,
    idx: int,
    *,
    kind: str,
    errors: list[str],
) -> None:
    composition = item.get("composition")
    label = f"{mapping}: skills[{idx}].composition"
    if composition is None:
        if kind == "composite":
            errors.append(f"{label} is required for kind composite")
        return
    if not isinstance(composition, dict):
        errors.append(f"{label} must be an object")
        return

    depends_on = composition.get("depends_on")
    dependency_lock = composition.get("dependency_lock")
    dependency_ids: list[str] = []
    source_package_ids: set[str] = set()
    if not isinstance(depends_on, list):
        errors.append(f"{label}.depends_on must be an array")
        depends_on = []
    else:
        for dep_idx, dependency in enumerate(depends_on, 1):
            dep_label = f"{label}.depends_on[{dep_idx}]"
            if not isinstance(dependency, dict):
                errors.append(f"{dep_label} must be an object")
                continue
            selectors = [
                key for key in ("skill", "source_package") if dependency.get(key)
            ]
            if len(selectors) != 1:
                errors.append(
                    f"{dep_label} must declare exactly one of skill or source_package"
                )
                continue
            selector = selectors[0]
            value = dependency.get(selector)
            role = dependency.get("role")
            if not isinstance(value, str) or not value:
                errors.append(f"{dep_label}.{selector} must be a non-empty string")
                continue
            canonical_value = value
            if selector == "source_package":
                canonical_value = value.lower()
                source_package_ids.add(canonical_value)
                if "/" not in value:
                    errors.append(
                        f"{dep_label}.source_package must look like owner/repo"
                    )
                if value != value.strip() or value != canonical_value:
                    errors.append(
                        f"{dep_label}.source_package must use canonical "
                        "lowercase owner/repo form"
                    )
            if not isinstance(role, str) or not role:
                errors.append(f"{dep_label}.role must be a non-empty string")
            dependency_ids.append(canonical_value)
    if len(dependency_ids) != len(set(dependency_ids)):
        errors.append(f"{label}.depends_on must not contain duplicate dependencies")
    if kind == "composite" and not depends_on:
        errors.append(f"{label}.depends_on must not be empty for kind composite")

    if not isinstance(dependency_lock, dict):
        errors.append(f"{label}.dependency_lock must be an object")
        return

    normalized_lock_ids: list[str] = []
    for dependency_id in dependency_lock:
        normalized_id = dependency_id
        if isinstance(dependency_id, str):
            lowered_id = dependency_id.lower()
            if lowered_id in source_package_ids:
                normalized_id = lowered_id
                if dependency_id != lowered_id:
                    errors.append(
                        f"{label}.dependency_lock key {dependency_id!r} must "
                        "use canonical lowercase source_package form"
                    )
        normalized_lock_ids.append(normalized_id)
    if len(normalized_lock_ids) != len(set(normalized_lock_ids)):
        errors.append(
            f"{label}.dependency_lock must not contain case-insensitive "
            "duplicate source_package keys"
        )
    if set(normalized_lock_ids) != set(dependency_ids):
        errors.append(
            f"{label}.dependency_lock keys must exactly match depends_on"
        )
    for slug, content_hash in dependency_lock.items():
        if (
            not isinstance(content_hash, str)
            or not SHA256_RE.fullmatch(content_hash)
        ):
            errors.append(
                f"{label}.dependency_lock[{slug!r}] must be a SHA-256 hash"
            )


def _validate_frontmatter_semantics(
    item: dict,
    path: Path,
    mapping: Path,
    idx: int,
    *,
    kind: str,
    origins: list,
    errors: list[str],
) -> None:
    frontmatter = parse_frontmatter(path)
    source = frontmatter.get("source")
    label = f"{mapping}: skills[{idx}]"

    if kind == "in_house" and not is_local_source(source):
        errors.append(
            f"{label} frontmatter source={source!r} conflicts with kind in_house"
        )
    if kind in EXTERNAL_KINDS and is_local_source(source):
        errors.append(
            f"{label} frontmatter source={source!r} conflicts with external kind {kind}"
        )

    external_repos = {
        str(origin.get("repo")).lower()
        for origin in origins
        if isinstance(origin, dict) and not is_local_repo(origin.get("repo"))
    }
    for field_name, field_value in (
        ("source", source),
        ("source_url", frontmatter.get("source_url")),
        ("mapping source", item.get("source")),
    ):
        declared_repo = github_repo(field_value)
        if declared_repo and external_repos and declared_repo not in external_repos:
            errors.append(
                f"{label} {field_name} repository {declared_repo} "
                f"is not declared by origins"
            )

    if kind in EXTERNAL_KINDS:
        frontmatter_license = (frontmatter.get("license") or "").strip()
        if frontmatter_license.lower() in UNKNOWN_LICENSE_VALUES:
            errors.append(f"{label} external SKILL.md must declare a license")
        origin_licenses = {
            str(origin.get("license")).strip().lower()
            for origin in origins
            if isinstance(origin, dict) and not is_local_repo(origin.get("repo"))
        }
        if (
            frontmatter_license
            and len(origin_licenses) == 1
            and frontmatter_license.lower() not in origin_licenses
        ):
            errors.append(
                f"{label} frontmatter license {frontmatter_license!r} "
                "does not match its origin license"
            )


def _validate_v2_entry(
    item: dict,
    mapping: Path,
    idx: int,
    repo_root: Path,
    errors: list[str],
) -> None:
    kind = item.get("kind")
    if kind not in VALID_KINDS:
        errors.append(f"{mapping}: skills[{idx}] invalid kind: {kind!r}")
        return

    entry_sync_mode = item.get("sync_mode")
    if entry_sync_mode not in VALID_SYNC_MODES:
        errors.append(
            f"{mapping}: skills[{idx}].sync_mode invalid: "
            f"{entry_sync_mode!r}"
        )
    upstream = item.get("upstream")
    legacy_sync_mode = (
        upstream.get("sync_mode") if isinstance(upstream, dict) else None
    )
    if isinstance(upstream, dict):
        if legacy_sync_mode not in VALID_SYNC_MODES:
            errors.append(
                f"{mapping}: skills[{idx}].upstream.sync_mode invalid: "
                f"{legacy_sync_mode!r}"
            )
        elif legacy_sync_mode != entry_sync_mode:
            errors.append(
                f"{mapping}: skills[{idx}].upstream.sync_mode must match "
                f"entry sync_mode {entry_sync_mode!r}"
            )

    origins = item.get("origins")
    if not isinstance(origins, list):
        errors.append(f"{mapping}: skills[{idx}].origins must be an array")
        origins = []
    if kind in EXTERNAL_KINDS and not origins:
        errors.append(
            f"{mapping}: skills[{idx}].origins must not be empty for kind {kind}"
        )
    artifact_file_targets: set[str] = set()
    artifact_directory_targets: set[str] = set()
    for origin_idx, origin in enumerate(origins, 1):
        _validate_origin(
            origin,
            mapping,
            idx,
            origin_idx,
            kind=kind,
            status=item.get("status"),
            entry_sync_mode=entry_sync_mode,
            legacy_sync_mode=legacy_sync_mode,
            errors=errors,
        )
        if isinstance(origin, dict) and isinstance(origin.get("artifacts"), list):
            for artifact in origin["artifacts"]:
                if isinstance(artifact, dict) and isinstance(
                    artifact.get("target"), str
                ):
                    target = artifact["target"]
                    if artifact.get("type", "file") == "directory":
                        artifact_directory_targets.add(target)
                    else:
                        artifact_file_targets.add(target)

    _validate_legacy_owner_consistency(
        item,
        mapping,
        idx,
        origins,
        errors,
    )

    managed_files = item.get("managed_files")
    if not isinstance(managed_files, list):
        errors.append(f"{mapping}: skills[{idx}].managed_files must be an array")
    else:
        managed_paths: list[str] = []
        managed_by_path: dict[str, dict] = {}
        expected_owner = item.get("normalized_slug")
        for managed_idx, managed in enumerate(managed_files, 1):
            label = (
                f"{mapping}: skills[{idx}].managed_files[{managed_idx}]"
            )
            if not isinstance(managed, dict):
                errors.append(f"{label} must be an object")
                continue
            missing = {"path", "sha256", "owner"} - set(managed)
            if missing:
                errors.append(f"{label} missing keys: {sorted(missing)}")
            path_value = managed.get("path")
            if not safe_relative_path(path_value):
                errors.append(f"{label}.path must be a safe relative path")
            elif isinstance(path_value, str):
                managed_paths.append(path_value)
                managed_by_path[path_value] = managed
                candidate, file_issues = _repository_file_issues(
                    repo_root,
                    path_value,
                )
                for issue in file_issues:
                    errors.append(
                        f"{mapping}: skills[{idx}] managed file "
                        f"{path_value!r} {issue}"
                    )
                if not file_issues:
                    expected_hash = managed.get("sha256")
                    current_hash = sha256_file(candidate)
                    if expected_hash != current_hash:
                        errors.append(
                            f"{mapping}: skills[{idx}] managed file "
                            f"{path_value!r} sha256 does not match "
                            "repository content"
                        )
            content_hash = managed.get("sha256")
            if (
                not isinstance(content_hash, str)
                or not SHA256_RE.fullmatch(content_hash)
            ):
                errors.append(f"{label}.sha256 must be a SHA-256 hash")
            owner = managed.get("owner")
            if not isinstance(owner, str) or not owner:
                errors.append(f"{label}.owner must be a non-empty string")
            elif (
                isinstance(expected_owner, str)
                and expected_owner
                and owner != expected_owner
            ):
                errors.append(
                    f"{label}.owner must match normalized_slug "
                    f"{expected_owner!r}"
                )

        if len(managed_paths) != len(set(managed_paths)):
            errors.append(
                f"{mapping}: skills[{idx}].managed_files must not contain duplicates"
            )

        managed_targets = set(managed_paths)
        for target in sorted(artifact_file_targets - managed_targets):
            errors.append(
                f"{mapping}: skills[{idx}] artifact target {target!r} "
                "must be listed in managed_files"
            )
        for target in sorted(managed_targets):
            if target in artifact_file_targets:
                continue
            target_path = PurePosixPath(target.replace("\\", "/"))
            covered_by_directory = any(
                PurePosixPath(directory.replace("\\", "/"))
                in target_path.parents
                for directory in artifact_directory_targets
            )
            if not covered_by_directory:
                errors.append(
                    f"{mapping}: skills[{idx}] managed file {target!r} "
                    "must be covered by an exact file artifact or a parent "
                    "directory artifact"
                )

        canonical_repo_skill = _canonical_repo_skill_path(item)
        canonical_root = (
            canonical_repo_skill.parent
            if canonical_repo_skill is not None
            else None
        )
        all_targets = (
            artifact_file_targets
            | artifact_directory_targets
            | managed_targets
        )
        if canonical_root is not None:
            for target in sorted(all_targets):
                if not safe_relative_path(target):
                    continue
                target_path = PurePosixPath(target.replace("\\", "/"))
                if not target_path.is_relative_to(canonical_root):
                    errors.append(
                        f"{mapping}: skills[{idx}] managed/artifact target "
                        f"{target!r} must stay within {canonical_root.as_posix()!r}"
                    )
        elif item.get("status") in ACTIVE_STATUSES and all_targets:
            errors.append(
                f"{mapping}: skills[{idx}] managed/artifact containment "
                "cannot be validated because repo_skill is not canonical"
            )

    _validate_composition(item, mapping, idx, kind=kind, errors=errors)

    canonical_repo_skill = _canonical_repo_skill_path(item)
    if canonical_repo_skill is not None:
        skill_path = _safe_repository_file(
            repo_root,
            canonical_repo_skill.as_posix(),
        )
        if skill_path is not None:
            _validate_frontmatter_semantics(
                item,
                skill_path,
                mapping,
                idx,
                kind=kind,
                origins=origins,
                errors=errors,
            )


def validate_mapping(
    mapping_path: Path,
    repo_root: Path,
    *,
    allow_v1: bool = False,
) -> list[str]:
    errors: list[str] = []
    data = json.loads(mapping_path.read_text(encoding="utf-8"))

    _validate_top(data, mapping_path, errors, allow_v1=allow_v1)
    _validate_verification_attempts(data, mapping_path, errors)

    skills = data.get("skills", [])
    if not isinstance(skills, list) or not skills:
        errors.append(f"{mapping_path}: skills must be a non-empty array")
        return errors

    is_v2 = data.get("schema_version") == SCHEMA_VERSION
    for idx, item in enumerate(skills, 1):
        if not isinstance(item, dict):
            errors.append(f"{mapping_path}: skills[{idx}] must be an object")
            continue
        missing = REQUIRED_SKILL_KEYS - set(item.keys())
        if missing:
            errors.append(f"{mapping_path}: skills[{idx}] missing keys: {sorted(missing)}")
            continue

        status = item["status"]
        slug = item["normalized_slug"]
        repo_skill = item["repo_skill"]
        source = item["source"]

        if status not in VALID_STATUS:
            errors.append(f"{mapping_path}: skills[{idx}] invalid status: {status}")
        if source and not URL_RE.match(str(source)):
            errors.append(f"{mapping_path}: skills[{idx}] source must be http/https URL")
        _validate_upstream(item, mapping_path, idx, errors)

        if status in ACTIVE_STATUSES:
            if not slug:
                errors.append(f"{mapping_path}: skills[{idx}] {status} must have normalized_slug")
            if not repo_skill:
                errors.append(f"{mapping_path}: skills[{idx}] {status} must have repo_skill")
            elif not safe_relative_path(repo_skill):
                errors.append(
                    f"{mapping_path}: skills[{idx}] repo_skill must be a safe "
                    "relative path"
                )
            elif _canonical_repo_skill_path(item) is None:
                errors.append(
                    f"{mapping_path}: skills[{idx}] repo_skill must match "
                    "canonical POSIX path "
                    "skills/<category>/<normalized_slug>/SKILL.md; "
                    f"got {repo_skill!r}"
                )
            else:
                path, path_issues = _repository_file_issues(
                    repo_root,
                    str(repo_skill),
                )
                for issue in path_issues:
                    if issue == "is missing":
                        errors.append(
                            f"{mapping_path}: skills[{idx}] repo_skill does "
                            f"not exist: {repo_skill}"
                        )
                    else:
                        errors.append(
                            f"{mapping_path}: skills[{idx}] repo_skill "
                            f"{repo_skill!r} {issue}"
                        )
                if not path_issues:
                    parsed_name = parse_name_from_skill_md(path)
                    if parsed_name != slug:
                        errors.append(
                            f"{mapping_path}: skills[{idx}] slug mismatch: "
                            f"normalized_slug={slug}, SKILL.md name={parsed_name}, "
                            f"file={repo_skill}"
                        )

        if status == "retired" and repo_skill is not None:
            errors.append(
                f"{mapping_path}: skills[{idx}] retired entries must set repo_skill to null"
            )

        if status in {"not_a_skill", "unverified_slug"} and slug is not None:
            errors.append(
                f"{mapping_path}: skills[{idx}] status {status} should keep normalized_slug as null until verified"
            )

        if is_v2:
            _validate_v2_entry(item, mapping_path, idx, repo_root, errors)

    return errors


def _entry_content_sha256(item: dict, repo_root: Path) -> str | None:
    if item.get("kind") not in {"in_house", "composite"}:
        origins = item.get("origins")
        if isinstance(origins, list):
            for origin in origins:
                if not isinstance(origin, dict):
                    continue
                tracking = origin.get("tracking")
                if not isinstance(tracking, dict):
                    continue
                content_hash = tracking.get("content_sha256")
                if (
                    isinstance(content_hash, str)
                    and SHA256_RE.fullmatch(content_hash)
                ):
                    return content_hash.lower()

    repo_skill = item.get("repo_skill")
    if isinstance(repo_skill, str) and safe_relative_path(repo_skill):
        skill_path = _safe_repository_file(repo_root, repo_skill)
        if skill_path is not None:
            return sha256_file(skill_path)
    origins = item.get("origins")
    if isinstance(origins, list):
        for origin in origins:
            if not isinstance(origin, dict):
                continue
            tracking = origin.get("tracking")
            if not isinstance(tracking, dict):
                continue
            content_hash = tracking.get("content_sha256")
            if isinstance(content_hash, str) and SHA256_RE.fullmatch(content_hash):
                return content_hash.lower()
    return None


def _composition_skill_dependencies(item: dict) -> list[str]:
    composition = item.get("composition")
    if not isinstance(composition, dict):
        return []
    dependencies = composition.get("depends_on")
    if not isinstance(dependencies, list):
        return []
    return [
        str(dependency["skill"])
        for dependency in dependencies
        if isinstance(dependency, dict)
        and isinstance(dependency.get("skill"), str)
        and dependency.get("skill")
    ]


def _composition_source_package_dependencies(item: dict) -> list[str]:
    composition = item.get("composition")
    if not isinstance(composition, dict):
        return []
    dependencies = composition.get("depends_on")
    if not isinstance(dependencies, list):
        return []
    return [
        str(dependency["source_package"]).lower()
        for dependency in dependencies
        if isinstance(dependency, dict)
        and isinstance(dependency.get("source_package"), str)
        and dependency.get("source_package")
    ]


def _origin_content_sha256(origin: dict) -> str | None:
    tracking = origin.get("tracking")
    if not isinstance(tracking, dict):
        return None
    content_hash = tracking.get("content_sha256")
    if isinstance(content_hash, str) and SHA256_RE.fullmatch(content_hash):
        return content_hash.lower()
    return None


def _find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    state: dict[str, int] = {}
    stack: list[str] = []
    stack_indexes: dict[str, int] = {}

    def visit(node: str) -> list[str] | None:
        state[node] = 1
        stack_indexes[node] = len(stack)
        stack.append(node)
        for dependency in graph.get(node, []):
            if dependency not in graph:
                continue
            if state.get(dependency, 0) == 0:
                cycle = visit(dependency)
                if cycle:
                    return cycle
            elif state.get(dependency) == 1:
                start = stack_indexes[dependency]
                return stack[start:] + [dependency]
        stack.pop()
        stack_indexes.pop(node, None)
        state[node] = 2
        return None

    for node in graph:
        if state.get(node, 0) == 0:
            cycle = visit(node)
            if cycle:
                return cycle
    return None


def validate_repository_mappings(
    mapping_paths: list[Path], repo_root: Path
) -> list[str]:
    """Validate claims and composition dependencies across all mappings."""
    errors: list[str] = []
    path_claims: dict[str, list[str]] = {}
    slug_claims: dict[str, list[str]] = {}
    managed_claims: dict[str, list[str]] = {}
    entries_by_slug: dict[str, tuple[dict, Path, int]] = {}
    bundle_origins_by_repo: dict[
        str, list[tuple[dict, dict, Path, int]]
    ] = {}
    unavailable_bundle_origins_by_repo: dict[
        str, list[tuple[dict, dict, Path, int]]
    ] = {}
    v2_composites: list[tuple[str, dict, Path, int]] = []

    for mapping_path in mapping_paths:
        if not mapping_path.is_file():
            continue
        try:
            data = json.loads(mapping_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        is_v2 = data.get("schema_version") == SCHEMA_VERSION
        skills = data.get("skills")
        if not isinstance(skills, list):
            continue
        for idx, item in enumerate(skills, 1):
            if not isinstance(item, dict):
                continue
            status = item.get("status")
            slug = item.get("normalized_slug")
            repo_skill = item.get("repo_skill")
            claim = f"{mapping_path}:skills[{idx}]"
            if status in ACTIVE_STATUSES:
                if isinstance(repo_skill, str) and safe_relative_path(repo_skill):
                    path_claims.setdefault(repo_skill, []).append(claim)
                if isinstance(slug, str) and slug:
                    slug_claims.setdefault(slug, []).append(claim)
                if data.get("schema_version") == SCHEMA_VERSION:
                    managed_files = item.get("managed_files")
                    if isinstance(managed_files, list):
                        for managed_file in managed_files:
                            if (
                                isinstance(managed_file, dict)
                                and isinstance(managed_file.get("path"), str)
                                and safe_relative_path(managed_file["path"])
                            ):
                                managed_claims.setdefault(
                                    managed_file["path"], []
                                ).append(claim)
            canonical_available = _active_canonical_skill_available(
                item,
                repo_root,
            )
            if isinstance(slug, str) and slug and canonical_available:
                entries_by_slug.setdefault(slug, (item, mapping_path, idx))
                if is_v2 and item.get("kind") == "composite":
                    v2_composites.append((slug, item, mapping_path, idx))
            if is_v2 and item.get("kind") == "bundle":
                bundle_available = status in {
                    "verified_not_in_repo",
                    "verified_in_repo",
                }
                bundle_index = (
                    bundle_origins_by_repo
                    if bundle_available
                    else unavailable_bundle_origins_by_repo
                )
                origins = item.get("origins")
                if isinstance(origins, list):
                    for origin in origins:
                        if not isinstance(origin, dict):
                            continue
                        repo = origin.get("repo")
                        if isinstance(repo, str) and repo:
                            bundle_index.setdefault(
                                repo.lower(), []
                            ).append((item, origin, mapping_path, idx))

    for repo_skill, claims in sorted(path_claims.items()):
        if len(claims) > 1:
            errors.append(
                f"duplicate active repo_skill claim {repo_skill!r}: "
                + ", ".join(claims)
            )
    for slug, claims in sorted(slug_claims.items()):
        if len(claims) > 1:
            errors.append(
                f"duplicate active normalized_slug claim {slug!r}: "
                + ", ".join(claims)
            )
    for managed_file, claims in sorted(managed_claims.items()):
        if len(claims) > 1:
            errors.append(
                f"duplicate active managed file claim {managed_file!r}: "
                + ", ".join(claims)
            )

    graph: dict[str, list[str]] = {}
    for slug, item, mapping_path, idx in v2_composites:
        skill_dependencies = _composition_skill_dependencies(item)
        source_package_dependencies = (
            _composition_source_package_dependencies(item)
        )
        graph[slug] = skill_dependencies
        composition = item.get("composition")
        dependency_lock = (
            composition.get("dependency_lock")
            if isinstance(composition, dict)
            and isinstance(composition.get("dependency_lock"), dict)
            else {}
        )
        source_package_lock = {
            str(lock_id).lower(): content_hash
            for lock_id, content_hash in dependency_lock.items()
        }
        for dependency in skill_dependencies:
            if dependency not in entries_by_slug:
                errors.append(
                    f"{mapping_path}: skills[{idx}].composition missing skill "
                    f"dependency: {dependency} (unavailable or non-canonical)"
                )
                continue
            locked_hash = dependency_lock.get(dependency)
            if locked_hash is None:
                continue
            dependency_item = entries_by_slug[dependency][0]
            current_hash = _entry_content_sha256(dependency_item, repo_root)
            if current_hash is None:
                errors.append(
                    f"{mapping_path}: skills[{idx}].composition cannot resolve "
                    f"content hash for dependency {dependency}"
                )
            elif current_hash.lower() != str(locked_hash).lower():
                errors.append(
                    f"{mapping_path}: skills[{idx}] composite {slug} is stale: "
                    f"dependency {dependency} advanced from {locked_hash} "
                    f"to {current_hash}"
                )
        for dependency in source_package_dependencies:
            candidates = bundle_origins_by_repo.get(dependency, [])
            if not candidates:
                if unavailable_bundle_origins_by_repo.get(dependency):
                    errors.append(
                        f"{mapping_path}: skills[{idx}].composition unavailable "
                        f"source_package bundle: {dependency}"
                    )
                else:
                    errors.append(
                        f"{mapping_path}: skills[{idx}].composition missing "
                        f"source_package bundle: {dependency}"
                    )
                continue
            if len(candidates) > 1:
                locations = ", ".join(
                    f"{candidate_mapping}:skills[{candidate_idx}]"
                    for _, _, candidate_mapping, candidate_idx in candidates
                )
                errors.append(
                    f"{mapping_path}: skills[{idx}].composition ambiguous "
                    f"source_package bundle {dependency}: {locations}"
                )
                continue
            _, origin, _, _ = candidates[0]
            current_hash = _origin_content_sha256(origin)
            if current_hash is None:
                errors.append(
                    f"{mapping_path}: skills[{idx}].composition cannot resolve "
                    f"content hash for source_package {dependency}"
                )
                continue
            locked_hash = source_package_lock.get(dependency)
            if not isinstance(locked_hash, str) or not SHA256_RE.fullmatch(
                locked_hash
            ):
                continue
            if current_hash != locked_hash.lower():
                errors.append(
                    f"{mapping_path}: skills[{idx}] composite {slug} is stale: "
                    f"source_package {dependency} advanced from {locked_hash} "
                    f"to {current_hash}"
                )

    cycle = _find_cycle(graph)
    if cycle:
        errors.append("composition dependency cycle: " + " -> ".join(cycle))
    return errors


def discover_mappings(repo_root: Path, mapping: str | None) -> list[Path]:
    if mapping:
        return [repo_root / mapping]
    return discover_source_mappings(repo_root / "docs/sources")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mapping",
        default=None,
        help="Specific mapping file to validate (default: validate all docs/sources/*.skills.json)",
    )
    parser.add_argument(
        "--allow-v1",
        action="store_true",
        help="Explicitly allow legacy mappings without schema_version=2",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    mappings = discover_mappings(repo_root, args.mapping)
    if not mappings:
        print("No mapping files found under docs/sources/*.skills.json")
        return 1

    all_errors: list[str] = []
    for m in mappings:
        if not m.exists():
            all_errors.append(f"Mapping not found: {m}")
            continue
        all_errors.extend(
            validate_mapping(m, repo_root, allow_v1=args.allow_v1)
        )
    all_errors.extend(validate_repository_mappings(mappings, repo_root))

    if all_errors:
        print("Validation failed:")
        for err in all_errors:
            print(f"- {err}")
        return 1

    print("Validation passed:")
    for m in mappings:
        print(f"- {m.relative_to(repo_root)}")
    print("- all verified entries have valid repo_skill and frontmatter name alignment")
    print("- active provenance claims are unique")
    if any(
        json.loads(m.read_text(encoding="utf-8")).get("schema_version")
        == SCHEMA_VERSION
        for m in mappings
        if m.is_file()
    ):
        print("- provenance v2 origins, artifacts, licenses, and dependency DAG are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
