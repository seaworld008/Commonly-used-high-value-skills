#!/usr/bin/env python3
"""Shared helpers for the additive provenance schema v2.

Schema v2 deliberately keeps the legacy mapping fields.  Existing consumers may
continue reading ``status``, ``source`` and ``upstream`` while newer consumers
use ``kind`` and ``origins`` for complete artifact-set provenance.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = 2

VALID_KINDS = {
    "mirror",
    "overlay",
    "composite",
    "bundle",
    "snapshot",
    "in_house",
    "reference_only",
}
EXTERNAL_KINDS = {"mirror", "overlay", "bundle", "snapshot"}
ACTIVE_EXTERNAL_KINDS = {"mirror", "overlay", "bundle"}
VALID_SYNC_MODES = {"replace", "monitor", "local-only", "archived", "manual"}
VALID_CHANNELS = {
    "latest_release",
    "default_branch",
    "canary",
    "fixed_ref",
    "local",
}
ACTIVE_STATUSES = {"verified_in_repo", "in_house"}
LOCAL_SOURCE_VALUES = {"", "in-house", "in_house", "local"}
UNKNOWN_LICENSE_VALUES = {
    "",
    "unknown",
    "unlicensed",
    "none",
    "noassertion",
    "proprietary",
}

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---(?:\s*\n|$)", re.DOTALL)
GITHUB_REPO_RE = re.compile(
    r"(?:github\.com/|^github:)([^/\s]+/[^/\s#?]+)", re.IGNORECASE
)
COMMIT_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$", re.IGNORECASE)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_frontmatter(path: Path) -> dict[str, str]:
    """Parse the scalar fields used by provenance without requiring PyYAML."""
    text = path.read_text(encoding="utf-8", errors="replace")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}

    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]
        fields[key.strip()] = value
    return fields


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def github_repo(value: str | None) -> str | None:
    """Return a normalized ``owner/repo`` from a GitHub source declaration."""
    if not value:
        return None
    match = GITHUB_REPO_RE.search(value.strip())
    if not match:
        return None
    result = match.group(1).rstrip("/")
    if result.lower().endswith(".git"):
        result = result[:-4]
    return result.lower()


def is_local_repo(repo: str | None) -> bool:
    return not repo or repo.startswith("local-repo/")


def is_local_source(source: str | None) -> bool:
    value = (source or "").strip().lower()
    return value in LOCAL_SOURCE_VALUES or value.startswith("local-")


def safe_relative_path(value: object) -> bool:
    """Whether a path is already in canonical relative POSIX form."""
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\\" in value
        or re.match(r"^[A-Za-z]:/", value)
        or value.startswith("/")
    ):
        return False
    components = value.split("/")
    if any(component in {"", ".", ".."} for component in components):
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and path.as_posix() == value


def infer_channel(ref: str | None, repo: str | None) -> str:
    if is_local_repo(repo):
        return "local"
    normalized = (ref or "").lower()
    if normalized in {"main", "master", "trunk", "head"}:
        return "default_branch"
    if re.search(
        r"(?:^|[._/+\-])"
        r"(?:alpha|beta|canary|dev|edge|nightly|next|pre|preview|rc|snapshot)"
        r"(?:$|[._/+\-]|\d)",
        normalized,
    ):
        return "canary"
    if re.fullmatch(r"v?\d+(?:\.\d+){1,3}(?:\+[0-9a-z.-]+)?", normalized):
        return "latest_release"
    return "fixed_ref"


def infer_kind(item: dict[str, Any]) -> str:
    """Infer a conservative v2 kind from a legacy entry."""
    existing = item.get("kind")
    if existing in VALID_KINDS:
        return str(existing)

    status = item.get("status")
    upstream = item.get("upstream") if isinstance(item.get("upstream"), dict) else {}
    repo = upstream.get("repo")
    mode = upstream.get("sync_mode")
    if status == "in_house" or (isinstance(repo, str) and is_local_repo(repo)):
        return "in_house"
    if status not in ACTIVE_STATUSES:
        return "reference_only"
    if mode in {"archived", "local-only"}:
        return "snapshot"
    if mode in {"monitor", "manual"}:
        return "overlay"
    return "mirror"


def infer_sync_mode(item: dict[str, Any], kind: str) -> str:
    mode = item.get("sync_mode")
    if mode in VALID_SYNC_MODES:
        return str(mode)
    upstream = item.get("upstream") if isinstance(item.get("upstream"), dict) else {}
    mode = upstream.get("sync_mode")
    if mode in VALID_SYNC_MODES:
        return str(mode)
    if kind == "in_house":
        return "local-only"
    if kind in {"overlay", "composite", "reference_only"}:
        return "monitor"
    if kind == "snapshot":
        return "local-only"
    return "replace"


def is_immutable_fixed_ref(
    tracking: object,
    repo: str | None,
) -> bool:
    """Whether a fixed-ref origin has a complete immutable checkpoint.

    A tag-like fixed ref is accepted only when both repository and path
    checkpoints are pinned.  Branch aliases such as ``main`` and ``next`` are
    rejected even if a caller labels them ``fixed_ref``.
    """
    if not isinstance(tracking, dict) or tracking.get("channel") != "fixed_ref":
        return False
    ref = tracking.get("ref")
    resolved_commit = tracking.get("resolved_commit")
    if (
        not isinstance(ref, str)
        or not COMMIT_RE.fullmatch(ref)
        or not isinstance(resolved_commit, str)
        or not COMMIT_RE.fullmatch(resolved_commit)
        or ref.lower() != resolved_commit.lower()
    ):
        return False
    path_commit = tracking.get("path_commit")
    content_hash = tracking.get("content_sha256")
    return (
        isinstance(path_commit, str)
        and bool(COMMIT_RE.fullmatch(path_commit))
        and isinstance(content_hash, str)
        and bool(SHA256_RE.fullmatch(content_hash))
    )


def replacement_allowed(
    kind: str,
    tracking: object,
    repo: str | None,
) -> bool:
    """Return whether an origin may be updated without a review checkpoint."""
    if kind not in {"mirror", "bundle"} or not isinstance(tracking, dict):
        return False
    channel = tracking.get("channel")
    ref = tracking.get("ref")
    if channel == "latest_release":
        return (
            isinstance(ref, str)
            and infer_channel(ref, repo) == "latest_release"
            and all(
                isinstance(tracking.get(key), str)
                and COMMIT_RE.fullmatch(str(tracking[key]))
                for key in ("resolved_commit", "path_commit")
            )
            and isinstance(tracking.get("content_sha256"), str)
            and bool(
                SHA256_RE.fullmatch(str(tracking["content_sha256"]))
            )
        )
    return is_immutable_fixed_ref(tracking, repo)


def normalize_sync_mode(
    *,
    kind: str,
    tracking: object,
    repo: str | None,
    requested_mode: str | None,
    status: str | None = None,
) -> str:
    """Apply the stable-release-first update policy to one origin."""
    local = is_local_repo(repo)
    mode = (
        requested_mode
        if requested_mode in VALID_SYNC_MODES
        else ("replace" if kind in {"mirror", "bundle"} else "monitor")
    )

    if status == "retired":
        return "archived"
    if kind in {"snapshot", "reference_only"}:
        return "archived" if mode == "archived" else "local-only"
    if kind == "in_house" or local:
        return "local-only"

    channel = tracking.get("channel") if isinstance(tracking, dict) else None
    if channel in {"default_branch", "canary"}:
        return "monitor"
    if kind in {"overlay", "composite"}:
        return "monitor"
    if mode == "replace" and replacement_allowed(kind, tracking, repo):
        return "replace"
    return "monitor"


def _requested_sync_mode(item: dict[str, Any], kind: str) -> str:
    """Choose the most conservative declared legacy/v2 mode."""
    modes: list[str] = []
    for value in (item.get("sync_mode"),):
        if value in VALID_SYNC_MODES:
            modes.append(str(value))
    upstream = item.get("upstream")
    if isinstance(upstream, dict) and upstream.get("sync_mode") in VALID_SYNC_MODES:
        modes.append(str(upstream["sync_mode"]))
    origins = item.get("origins")
    if isinstance(origins, list):
        modes.extend(
            str(origin["sync_mode"])
            for origin in origins
            if isinstance(origin, dict)
            and origin.get("sync_mode") in VALID_SYNC_MODES
        )

    if "archived" in modes:
        return "archived"
    if any(mode in {"monitor", "manual"} for mode in modes):
        return "monitor"
    if "local-only" in modes:
        return "local-only"
    if "replace" in modes:
        return "replace"
    return infer_sync_mode(item, kind)


def _normalize_entry_sync_modes(item: dict[str, Any], kind: str) -> None:
    """Keep origin, v2 entry, and legacy upstream modes policy-identical."""
    requested = _requested_sync_mode(item, kind)
    origins = item.get("origins")
    proposals: list[str] = []
    if isinstance(origins, list):
        for origin in origins:
            if not isinstance(origin, dict):
                continue
            tracking = origin.get("tracking")
            proposals.append(
                normalize_sync_mode(
                    kind=kind,
                    tracking=tracking,
                    repo=origin.get("repo"),
                    requested_mode=requested,
                    status=item.get("status"),
                )
            )

    if not proposals:
        upstream = (
            item.get("upstream")
            if isinstance(item.get("upstream"), dict)
            else {}
        )
        tracking = {
            "channel": infer_channel(upstream.get("ref"), upstream.get("repo")),
            "ref": upstream.get("ref"),
            "resolved_commit": upstream.get("last_synced_commit"),
            "path_commit": upstream.get("last_synced_commit"),
        }
        proposals.append(
            normalize_sync_mode(
                kind=kind,
                tracking=tracking,
                repo=upstream.get("repo"),
                requested_mode=requested,
                status=item.get("status"),
            )
        )

    if "monitor" in proposals:
        normalized = "monitor"
    elif "archived" in proposals:
        normalized = "archived"
    elif "local-only" in proposals:
        normalized = "local-only"
    else:
        normalized = "replace"

    item["sync_mode"] = normalized
    if isinstance(origins, list):
        for origin in origins:
            if isinstance(origin, dict):
                origin["sync_mode"] = normalized
    upstream = item.get("upstream")
    if isinstance(upstream, dict):
        upstream["sync_mode"] = normalized


def _artifact_target(item: dict[str, Any]) -> str | None:
    repo_skill = item.get("repo_skill")
    if not isinstance(repo_skill, str) or not repo_skill:
        return None
    return Path(repo_skill).as_posix()


def _managed_owner(item: dict[str, Any]) -> str:
    """Return the stable owner id used to authorize future pruning."""
    for key in ("normalized_slug", "video_name"):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return "unresolved"


def _skill_artifact_paths(
    item: dict[str, Any],
    repo_root: Path,
) -> list[str]:
    """Return every regular file contained by a canonical skill directory."""
    target = _artifact_target(item)
    if target is None or not safe_relative_path(target):
        return []
    skill_path = repo_root / target
    if not skill_path.is_file():
        return []
    skill_root = skill_path.parent
    return [
        path.relative_to(repo_root).as_posix()
        for path in sorted(skill_root.rglob("*"))
        if path.is_file()
        and not path.is_symlink()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
        and path.name != ".DS_Store"
    ]


def _local_artifacts(
    item: dict[str, Any],
    repo_root: Path,
) -> list[dict[str, str]]:
    return [
        {
            "source": path,
            "target": path,
            "type": "file",
        }
        for path in _skill_artifact_paths(item, repo_root)
    ]


def _managed_file(
    path: str,
    *,
    item: dict[str, Any],
    repo_root: Path,
    existing: dict[str, Any] | None = None,
    refresh_hash: bool,
) -> dict[str, Any]:
    """Build a prune-safe managed file record.

    Existing metadata remains additive for external origins.  Local origins
    explicitly refresh their hash so a bootstrap never carries a stale
    ownership checkpoint forward.
    """
    record = deepcopy(existing) if isinstance(existing, dict) else {}
    record["path"] = path
    if refresh_hash:
        record["owner"] = _managed_owner(item)
    else:
        record.setdefault("owner", _managed_owner(item))
    candidate = repo_root / path
    if refresh_hash or "sha256" not in record:
        record["sha256"] = (
            sha256_file(candidate)
            if candidate.is_file() and not candidate.is_symlink()
            else None
        )
    return record


def _migrate_managed_files(
    item: dict[str, Any],
    repo_root: Path,
    *,
    local_targets: list[str] | None,
) -> list[dict[str, Any]]:
    existing_by_path: dict[str, dict[str, Any]] = {}
    existing_paths: list[str] = []
    existing = item.get("managed_files")
    if isinstance(existing, list):
        for managed in existing:
            if isinstance(managed, str):
                path = managed
                record = None
            elif isinstance(managed, dict) and isinstance(managed.get("path"), str):
                path = managed["path"]
                record = managed
            else:
                continue
            if path not in existing_paths:
                existing_paths.append(path)
            if record is not None:
                existing_by_path[path] = record

    targets = local_targets if local_targets is not None else existing_paths
    if local_targets is None and not targets:
        target = _artifact_target(item)
        targets = [target] if target else []

    return [
        _managed_file(
            path,
            item=item,
            repo_root=repo_root,
            existing=existing_by_path.get(path),
            refresh_hash=local_targets is not None,
        )
        for path in targets
    ]


def _artifact_covers_target(artifact: object, target: str) -> bool:
    """Whether an artifact declaration owns ``target``.

    File artifacts must match exactly.  Directory artifacts also cover files
    below their declared target directory.
    """
    if not isinstance(artifact, dict):
        return False
    artifact_target = artifact.get("target")
    if (
        not isinstance(artifact_target, str)
        or not safe_relative_path(artifact_target)
        or not safe_relative_path(target)
    ):
        return False

    declared = PurePosixPath(artifact_target.replace("\\", "/"))
    requested = PurePosixPath(target.replace("\\", "/"))
    if artifact.get("type", "file") == "directory":
        return requested == declared or declared in requested.parents
    return requested == declared


def _refresh_declared_managed_digests(
    item: dict[str, Any],
    repo_root: Path,
) -> None:
    """Refresh hashes without changing the declared artifact inventory.

    Missing, unsafe, and symlinked paths deliberately retain their prior
    checkpoint so validation can continue reporting them as invalid instead of
    silently replacing evidence with ``null``.
    """
    managed_files = item.get("managed_files")
    if not isinstance(managed_files, list):
        return

    repo_skill = _artifact_target(item)
    repo_skill_digest: str | None = None
    for managed in managed_files:
        if not isinstance(managed, dict):
            continue
        path = managed.get("path")
        if not safe_relative_path(path):
            continue
        candidate = repo_root / str(path)
        if not candidate.is_file() or candidate.is_symlink():
            continue
        digest = sha256_file(candidate)
        managed["sha256"] = digest
        if path == repo_skill:
            repo_skill_digest = digest

    if repo_skill_digest is None or repo_skill is None:
        return
    origins = item.get("origins")
    if not isinstance(origins, list):
        return
    for origin in origins:
        if not isinstance(origin, dict):
            continue
        artifacts = origin.get("artifacts")
        if not isinstance(artifacts, list) or not any(
            _artifact_covers_target(artifact, repo_skill)
            for artifact in artifacts
        ):
            continue
        tracking = origin.get("tracking")
        if isinstance(tracking, dict):
            tracking["content_sha256"] = repo_skill_digest


def _refresh_local_origin(
    origin: dict[str, Any],
    item: dict[str, Any],
    repo_root: Path,
    *,
    tracking_date: str | None,
) -> dict[str, Any]:
    """Refresh repository-local facts without changing external checkpoints."""
    refreshed = deepcopy(origin)
    artifacts = _local_artifacts(item, repo_root)
    refreshed["artifacts"] = artifacts

    upstream = item.get("upstream") if isinstance(item.get("upstream"), dict) else {}
    target = _artifact_target(item)
    if target is not None:
        refreshed["path"] = PurePosixPath(target).parent.as_posix()
    refreshed["sync_mode"] = "local-only"
    tracking = deepcopy(refreshed.get("tracking") or {})
    skill_target = target
    skill_path = repo_root / skill_target if skill_target else None
    tracking["channel"] = "local"
    tracking["ref"] = str(upstream.get("ref") or tracking.get("ref") or "local")
    tracking.setdefault("resolved_commit", None)
    tracking.setdefault("path_commit", None)
    previous_content_hash = tracking.get("content_sha256")
    current_content_hash = (
        sha256_file(skill_path)
        if skill_path is not None
        and skill_path.is_file()
        and not skill_path.is_symlink()
        else None
    )
    tracking["content_sha256"] = current_content_hash
    checked_at = (
        tracking_date
        or upstream.get("last_checked_at")
        or tracking.get("last_checked_at")
    )
    previous_synced_at = (
        upstream.get("last_synced_at")
        or tracking.get("last_synced_at")
    )
    content_changed = current_content_hash != previous_content_hash
    synced_at = (
        tracking_date
        if tracking_date and content_changed
        else previous_synced_at
    )
    tracking["last_checked_at"] = checked_at
    tracking["last_synced_at"] = synced_at
    upstream["last_checked_at"] = checked_at
    upstream["last_synced_at"] = synced_at
    refreshed["tracking"] = tracking
    return refreshed


def build_origin(
    item: dict[str, Any],
    *,
    frontmatter: dict[str, str] | None = None,
    skill_path: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any] | None:
    """Build one origin from legacy ``upstream`` fields.

    The returned origin is intentionally complete, including null checkpoints.
    That makes missing upstream resolution visible without discarding legacy
    metadata.
    """
    frontmatter = frontmatter or {}
    upstream = item.get("upstream") if isinstance(item.get("upstream"), dict) else {}
    kind = infer_kind(item)
    repo = upstream.get("repo")
    path = upstream.get("path")

    if not repo and kind == "in_house":
        repo = "local-repo/in-house"
        repo_skill = item.get("repo_skill")
        if isinstance(repo_skill, str):
            path = str(Path(repo_skill).parent.as_posix())
    if not repo and kind == "reference_only":
        return None

    ref = upstream.get("ref")
    synced_commit = upstream.get("last_synced_commit")
    artifact_target = _artifact_target(item)
    artifacts: list[dict[str, str]] = []
    artifact_source = path
    if is_local_repo(repo) and isinstance(item.get("repo_skill"), str):
        artifact_source = item["repo_skill"]
    if is_local_repo(repo) and repo_root is not None:
        artifacts = _local_artifacts(item, repo_root)
    elif artifact_source and artifact_target:
        artifacts.append(
            {
                "source": str(artifact_source),
                "target": artifact_target,
                "type": "file",
            }
        )

    return {
        "repo": repo,
        "path": path,
        "license": frontmatter.get("license") or None,
        "sync_mode": infer_sync_mode(item, kind),
        "artifacts": artifacts,
        "tracking": {
            "channel": infer_channel(ref, repo),
            "ref": ref or ("local" if is_local_repo(repo) else None),
            "resolved_commit": synced_commit,
            "path_commit": synced_commit,
            "content_sha256": (
                sha256_file(skill_path)
                if skill_path is not None and skill_path.is_file()
                else None
            ),
            "last_checked_at": upstream.get("last_checked_at"),
            "last_synced_at": upstream.get("last_synced_at"),
        },
    }


def migrate_entry(
    item: dict[str, Any],
    repo_root: Path,
    *,
    local_tracking_date: str | None = None,
    refresh_managed_digests: bool = False,
) -> dict[str, Any]:
    """Return an additive v2 copy of one legacy skill entry."""
    migrated = deepcopy(item)
    kind = infer_kind(migrated)
    migrated["kind"] = kind

    repo_skill = migrated.get("repo_skill")
    skill_path = (
        repo_root / repo_skill
        if isinstance(repo_skill, str) and repo_skill
        else None
    )
    frontmatter = (
        parse_frontmatter(skill_path)
        if skill_path is not None and skill_path.is_file()
        else {}
    )

    if "origins" not in migrated:
        origin = build_origin(
            migrated,
            frontmatter=frontmatter,
            skill_path=skill_path,
            repo_root=repo_root,
        )
        migrated["origins"] = [origin] if origin else []
    else:
        origins = migrated.get("origins")
        if isinstance(origins, list):
            migrated["origins"] = [
                (
                    _refresh_local_origin(
                        origin,
                        migrated,
                        repo_root,
                        tracking_date=local_tracking_date,
                    )
                    if isinstance(origin, dict) and is_local_repo(origin.get("repo"))
                    else origin
                )
                for origin in origins
            ]

    _normalize_entry_sync_modes(migrated, kind)

    has_local_origin = any(
        isinstance(origin, dict) and is_local_repo(origin.get("repo"))
        for origin in migrated.get("origins", [])
    )
    local_targets = (
        _skill_artifact_paths(migrated, repo_root) if has_local_origin else None
    )
    migrated["managed_files"] = _migrate_managed_files(
        migrated,
        repo_root,
        local_targets=local_targets,
    )
    if refresh_managed_digests:
        _refresh_declared_managed_digests(migrated, repo_root)

    if kind == "composite" and "composition" not in migrated:
        migrated["composition"] = {
            "depends_on": [],
            "dependency_lock": {},
        }
    return migrated


def migrate_payload(
    data: dict[str, Any],
    repo_root: Path,
    *,
    local_tracking_date: str | None = None,
    refresh_managed_digests: bool = False,
) -> dict[str, Any]:
    """Return an additive v2 mapping while preserving every legacy field."""
    migrated = deepcopy(data)
    migrated["schema_version"] = SCHEMA_VERSION
    skills = migrated.get("skills")
    if isinstance(skills, list):
        migrated["skills"] = [
            (
                migrate_entry(
                    item,
                    repo_root,
                    local_tracking_date=local_tracking_date,
                    refresh_managed_digests=refresh_managed_digests,
                )
                if isinstance(item, dict)
                else item
            )
            for item in skills
        ]
    return migrated


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Durably replace JSON through an exclusively-created sibling file.

    ``mkstemp`` avoids the predictable temporary pathname used by the legacy
    writer, so a pre-created symlink cannot redirect the write.  Existing
    destination permissions are retained, and both file contents and the
    containing directory are synced around the atomic rename.
    """
    path = Path(path)
    original_mode: int | None = None
    try:
        destination_stat = path.lstat()
    except FileNotFoundError:
        pass
    else:
        if stat.S_ISLNK(destination_stat.st_mode):
            raise ValueError(f"refusing to replace symlink destination: {path}")
        if not stat.S_ISREG(destination_stat.st_mode):
            raise ValueError(
                f"refusing to replace non-regular destination: {path}"
            )
        original_mode = stat.S_IMODE(destination_stat.st_mode)

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        created_stat = os.fstat(file_descriptor)
        if not stat.S_ISREG(created_stat.st_mode):
            raise RuntimeError(f"temporary path is not a regular file: {temporary}")
        if original_mode is not None:
            os.fchmod(file_descriptor, original_mode)

        handle = os.fdopen(file_descriptor, "w", encoding="utf-8")
        file_descriptor = -1
        with handle:
            handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

        named_stat = temporary.lstat()
        if (
            not stat.S_ISREG(named_stat.st_mode)
            or named_stat.st_dev != created_stat.st_dev
            or named_stat.st_ino != created_stat.st_ino
        ):
            raise RuntimeError(
                f"temporary path changed before atomic replace: {temporary}"
            )

        os.replace(temporary, path)
        directory_fd = os.open(
            path.parent,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if file_descriptor >= 0:
            os.close(file_descriptor)
        temporary.unlink(missing_ok=True)


def discover_source_mappings(sources_dir: Path) -> list[Path]:
    """Discover both skill mappings and managed bundle manifests."""
    return sorted(
        {
            *sources_dir.glob("*.skills.json"),
            *sources_dir.glob("*.bundle.json"),
        }
    )
