#!/usr/bin/env python3
"""Prune-safe, transactional synchronization of one canonical skill artifact set.

This module deliberately has no network or mapping-file responsibilities.  A
caller resolves an upstream ref, downloads and expands its complete file
inventory, then passes the bytes here.  The returned metadata can be committed
to provenance only after the filesystem transaction succeeds.

Ownership is fail-closed:

* an existing file may be replaced or removed only when its current digest
  matches the corresponding ``managed_files`` checkpoint;
* files outside the old managed manifest are copied through unchanged and are
  never silently adopted, overwritten, or removed;
* a user-modified managed file blocks the transaction when the requested
  artifact set would overwrite or remove it.

The complete skill directory is built beside the destination and validated
before a rename-based switch.  A temporary backup allows failures after either
rename to restore the original directory.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import stat
import tempfile
import time
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Iterator, Self

try:  # POSIX advisory locks are released automatically when a process exits.
    import fcntl
except ImportError:  # pragma: no cover - Windows is not used by repository CI.
    fcntl = None  # type: ignore[assignment]

SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
GIT_FILE_MODES = frozenset({"100644", "100755"})


class ArtifactSetSyncError(RuntimeError):
    """Base class for artifact-set planning and application failures."""


class ArtifactValidationError(ArtifactSetSyncError):
    """The entry, manifest, payload, or filesystem shape is unsafe."""


class OwnershipConflictError(ArtifactSetSyncError):
    """The requested change lacks safe overwrite or deletion authority."""

    def __init__(
        self,
        *,
        user_modified: Sequence[str] = (),
        unowned_conflicts: Sequence[str] = (),
    ) -> None:
        self.user_modified = tuple(user_modified)
        self.unowned_conflicts = tuple(unowned_conflicts)
        details: list[str] = []
        if self.user_modified:
            details.append("user_modified=" + ", ".join(self.user_modified))
        if self.unowned_conflicts:
            details.append(
                "unowned_conflicts=" + ", ".join(self.unowned_conflicts)
            )
        super().__init__(
            "artifact-set ownership conflict"
            + (": " + "; ".join(details) if details else "")
        )


class ConcurrentModificationError(ArtifactSetSyncError):
    """The canonical directory changed after its plan was constructed."""

    def __init__(self, paths: Sequence[str]) -> None:
        self.paths = tuple(paths)
        super().__init__(
            "canonical skill changed after planning: " + ", ".join(self.paths)
        )


class ArtifactApplyError(ArtifactSetSyncError):
    """The transaction failed; ``rollback_succeeded`` reports recovery state."""

    def __init__(
        self,
        message: str,
        *,
        rollback_succeeded: bool,
        cause: Exception,
        recovery_path: Path | None = None,
    ) -> None:
        self.rollback_succeeded = rollback_succeeded
        self.cause = cause
        self.recovery_path = recovery_path
        suffix = "rollback succeeded" if rollback_succeeded else "rollback failed"
        recovery = (
            f"; recovery_path={recovery_path}"
            if recovery_path is not None
            else ""
        )
        super().__init__(f"{message} ({suffix}{recovery}): {cause}")


class ArtifactLockError(ArtifactSetSyncError):
    """Another conforming transaction currently owns this canonical skill."""

    def __init__(self, lock_path: Path) -> None:
        self.lock_path = lock_path
        super().__init__(
            f"artifact-set transaction is already active: {lock_path}"
        )


class ArtifactRecoveryError(ArtifactSetSyncError):
    """A durable transaction journal cannot be recovered without authority."""

    def __init__(
        self,
        message: str,
        *,
        recovery_paths: Sequence[Path] = (),
    ) -> None:
        self.recovery_paths = tuple(recovery_paths)
        suffix = (
            "; recovery_paths="
            + ", ".join(str(path) for path in self.recovery_paths)
            if self.recovery_paths
            else ""
        )
        super().__init__(message + suffix)


@dataclass(frozen=True)
class ArtifactPayload:
    """One expanded upstream file.

    ``type`` accepts ``file`` and ``binary``.  Both become provenance
    ``type: file`` entries because binary safety comes from byte-wise hashing,
    not from a separate mapping type.
    """

    source: str
    target: str
    type: str
    data: bytes
    mode: str


@dataclass(frozen=True)
class Drift:
    """A discrepancy between the old ownership checkpoint and local disk."""

    path: str
    kind: str
    expected_sha256: str | None
    actual_sha256: str | None
    expected_mode: str | None = None
    actual_mode: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        result: dict[str, str | None] = {
            "path": self.path,
            "kind": self.kind,
            "expected_sha256": self.expected_sha256,
            "actual_sha256": self.actual_sha256,
        }
        if self.expected_mode is not None or self.actual_mode is not None:
            result["expected_mode"] = self.expected_mode
            result["actual_mode"] = self.actual_mode
        return result


@dataclass(frozen=True)
class SyncPlan:
    """A validated filesystem plan with immutable byte payloads."""

    repo_root: Path
    skill_root: str
    repo_skill: str
    owner: str
    payloads: tuple[ArtifactPayload, ...]
    artifacts: tuple[Mapping[str, str], ...]
    managed_files: tuple[Mapping[str, str], ...]
    checkpoint: Mapping[str, Any]
    content_sha256: str
    changed: tuple[str, ...]
    pruned: tuple[str, ...]
    preserved: tuple[str, ...]
    drift: tuple[Drift, ...]
    user_modified: tuple[str, ...]
    unowned_conflicts: tuple[str, ...]
    owned_targets: tuple[str, ...]
    protected_targets: tuple[str, ...]
    baseline_inventory: Mapping[str, str]
    baseline_modes: Mapping[str, str]
    baseline_root_identity: tuple[int, int] | None

    @property
    def blocked(self) -> bool:
        return bool(self.user_modified or self.unowned_conflicts)

    @property
    def has_filesystem_changes(self) -> bool:
        return bool(self.changed or self.pruned)

    def metadata_patch(self) -> dict[str, Any]:
        """Return JSON-ready provenance fields without mutating an entry."""
        return {
            "artifacts": [dict(item) for item in self.artifacts],
            "managed_files": [dict(item) for item in self.managed_files],
            "tracking": deepcopy(dict(self.checkpoint)),
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class SyncResult:
    """The plan outcome and JSON-ready provenance metadata."""

    artifacts: tuple[Mapping[str, str], ...]
    managed_files: tuple[Mapping[str, str], ...]
    checkpoint: Mapping[str, Any]
    content_sha256: str
    changed: tuple[str, ...]
    pruned: tuple[str, ...]
    preserved: tuple[str, ...]
    drift: tuple[Drift, ...]
    applied: bool
    dry_run: bool

    @property
    def has_filesystem_changes(self) -> bool:
        return bool(self.changed or self.pruned)

    def metadata_patch(self) -> dict[str, Any]:
        """Return JSON-ready origin/entry fields for the mapping caller."""
        return {
            "artifacts": [dict(item) for item in self.artifacts],
            "managed_files": [dict(item) for item in self.managed_files],
            "tracking": deepcopy(dict(self.checkpoint)),
            "content_sha256": self.content_sha256,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.metadata_patch(),
            "changed": list(self.changed),
            "pruned": list(self.pruned),
            "preserved": list(self.preserved),
            "drift": [item.to_dict() for item in self.drift],
            "applied": self.applied,
            "dry_run": self.dry_run,
        }


FaultInjector = Callable[[str], None]


def skill_lock_identity(
    repo_root: str | os.PathLike[str],
    skill_root: str,
) -> str:
    """Return the stable cross-process identity for one canonical skill root."""
    try:
        root = Path(repo_root).resolve(strict=True)
    except (FileNotFoundError, RuntimeError) as exc:
        raise ArtifactValidationError(
            f"repository root does not exist or cannot be resolved: {repo_root}"
        ) from exc
    if not root.is_dir():
        raise ArtifactValidationError(f"repository root is not a directory: {root}")
    if not _safe_relative_posix(skill_root):
        raise ArtifactValidationError(
            f"skill_root is not canonical relative POSIX: {skill_root!r}"
        )
    return hashlib.sha256(
        f"{root}\0{skill_root}".encode("utf-8", errors="surrogateescape")
    ).hexdigest()


def skill_lock_path(
    repo_root: str | os.PathLike[str],
    skill_root: str,
) -> Path:
    """Return the private advisory-lock path shared by engine and ingest."""
    uid = os.getuid() if hasattr(os, "getuid") else 0
    digest = skill_lock_identity(repo_root, skill_root)
    return (
        Path(tempfile.gettempdir())
        / f"high-value-skills-artifact-locks-{uid}"
        / f"{digest}.lock"
    )


def skill_transaction_journal_path(
    repo_root: str | os.PathLike[str],
    skill_root: str,
) -> Path:
    """Return the stable durable-journal path protected by the skill lock."""
    return skill_lock_path(repo_root, skill_root).with_suffix(".journal.json")


def _ensure_private_lock_root(path: Path) -> None:
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ArtifactValidationError(
            f"artifact lock root is not a private directory: {path}"
        )
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise ArtifactValidationError(
            f"artifact lock root is owned by another user: {path}"
        )
    if metadata.st_mode & 0o077:
        try:
            path.chmod(0o700)
        except OSError as exc:
            raise ArtifactValidationError(
                f"artifact lock root is not private: {path}"
            ) from exc


class _SkillLock:
    """Process-crash-safe advisory lock for one canonical skill."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._fd: int | None = None

    def acquire(self, timeout: float) -> None:
        if fcntl is None:  # pragma: no cover - see guarded import above
            raise ArtifactValidationError(
                "artifact transactions require POSIX advisory file locks"
            )
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout < 0
        ):
            raise ArtifactValidationError(
                "lock_timeout must be a finite non-negative number"
            )
        _ensure_private_lock_root(self.path.parent)
        flags = os.O_CREAT | os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(self.path, flags, 0o600)
        except OSError as exc:
            raise ArtifactValidationError(
                f"cannot open artifact lock file safely: {self.path}"
            ) from exc
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise ArtifactValidationError(
                    f"artifact lock path is not a regular file: {self.path}"
                )
            if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
                raise ArtifactValidationError(
                    f"artifact lock file is owned by another user: {self.path}"
                )
            deadline = time.monotonic() + timeout
            while True:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError as exc:
                    if time.monotonic() >= deadline:
                        raise ArtifactLockError(self.path) from exc
                    time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
            os.ftruncate(descriptor, 0)
            os.write(
                descriptor,
                f"pid={os.getpid()}\n".encode("ascii"),
            )
            os.fsync(descriptor)
            self._fd = descriptor
        except Exception:
            os.close(descriptor)
            raise

    def release(self) -> None:
        descriptor = self._fd
        if descriptor is None:
            return
        self._fd = None
        try:
            # Keep the inode stable so waiters can never split across an
            # unlink/recreate race.  Empty stale files carry no lock: flock is
            # released by close, including after process termination.
            os.ftruncate(descriptor, 0)
            os.fsync(descriptor)
            if fcntl is not None:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


@contextmanager
def skill_advisory_lock(
    repo_root: str | os.PathLike[str],
    skill_root: str,
    *,
    timeout: float = 0.0,
    recover_pending: bool = True,
) -> Iterator[_SkillLock]:
    """Acquire the exact skill lock used by artifact transactions.

    Callers that also own a provenance mapping lock must acquire that mapping
    lock first, then enter this context, establishing the global
    ``mapping -> skill`` lock order.  Read-only callers may set
    ``recover_pending=False``; they still serialize on the same lock, but fail
    closed without mutating repository state when a journal is present.
    """
    resolved_root = Path(repo_root).resolve(strict=True)
    pending_batch = resolved_root / ".hvs-transactions" / "pending"
    if recover_pending and os.path.lexists(pending_batch):
        raise ArtifactRecoveryError(
            "recover the repository durable mapping batch before artifact sync",
            recovery_paths=(pending_batch,),
        )
    lock = _SkillLock(skill_lock_path(resolved_root, skill_root))
    lock.acquire(timeout)
    try:
        journal_path = lock.path.with_suffix(".journal.json")
        if recover_pending:
            _recover_pending_transaction(
                resolved_root,
                skill_root,
                journal_path,
            )
        elif os.path.lexists(journal_path):
            raise ArtifactRecoveryError(
                "read-only skill lock found a pending artifact transaction",
                recovery_paths=(journal_path,),
            )
        yield lock
    finally:
        lock.release()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_relative_posix(value: object) -> bool:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or value.startswith("/")
        or "\\" in value
        or re.match(r"^[A-Za-z]:/", value)
    ):
        return False
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and path.as_posix() == value


def _inside(path: str, root: str) -> bool:
    candidate = PurePosixPath(path)
    boundary = PurePosixPath(root)
    return candidate != boundary and boundary in candidate.parents


def _entry_owner(entry: Mapping[str, Any], skill_root: str) -> str:
    for key in ("normalized_slug", "video_name", "name"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return PurePosixPath(skill_root).name


def _coerce_payload(value: ArtifactPayload | Mapping[str, Any]) -> ArtifactPayload:
    if isinstance(value, ArtifactPayload):
        payload = value
    elif isinstance(value, Mapping):
        data = value.get("data")
        if data is None and "bytes" in value:
            data = value["bytes"]
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise ArtifactValidationError(
                "each upstream artifact must contain bytes in 'data' or 'bytes'"
            )
        payload = ArtifactPayload(
            source=value.get("source"),  # type: ignore[arg-type]
            target=value.get("target"),  # type: ignore[arg-type]
            type=value.get("type", "file"),  # type: ignore[arg-type]
            data=bytes(data),
            mode=value.get("mode"),  # type: ignore[arg-type]
        )
    else:
        raise ArtifactValidationError(
            "upstream artifacts must be ArtifactPayload or mapping objects"
        )

    if not _safe_relative_posix(payload.source):
        raise ArtifactValidationError(
            f"artifact source is not canonical relative POSIX: {payload.source!r}"
        )
    if not _safe_relative_posix(payload.target):
        raise ArtifactValidationError(
            f"artifact target is not canonical relative POSIX: {payload.target!r}"
        )
    if payload.type not in {"file", "binary"}:
        detail = (
            " (directory payloads must be expanded first)"
            if payload.type == "directory"
            else ""
        )
        raise ArtifactValidationError(
            f"unsupported artifact type {payload.type!r}{detail}"
        )
    if payload.mode not in GIT_FILE_MODES:
        raise ArtifactValidationError(
            f"artifact mode must be 100644 or 100755: {payload.mode!r}"
        )
    if not isinstance(payload.data, bytes):
        payload = ArtifactPayload(
            payload.source,
            payload.target,
            payload.type,
            bytes(payload.data),
            payload.mode,
        )
    return payload


def _assert_no_symlink_ancestors(repo_root: Path, path: Path) -> None:
    try:
        relative = path.relative_to(repo_root)
    except ValueError as exc:
        raise ArtifactValidationError(
            f"path escapes repository root: {path}"
        ) from exc

    current = repo_root
    for component in relative.parts:
        current = current / component
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise ArtifactValidationError(
                f"symlink or symlink parent is not allowed: {current}"
            )


def _git_mode(metadata: os.stat_result) -> str:
    return "100755" if stat.S_IMODE(metadata.st_mode) & 0o111 else "100644"


def _file_digest_and_mode(path: Path) -> tuple[str, str]:
    """Read content and executable mode from one pinned regular-file inode."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ArtifactValidationError(
            f"cannot open canonical artifact safely: {path}"
        ) from exc
    try:
        opened = os.fstat(descriptor)
        try:
            named_before = path.lstat()
        except OSError as exc:
            raise ArtifactValidationError(
                f"canonical artifact changed while opening: {path}"
            ) from exc
        if (
            not stat.S_ISREG(opened.st_mode)
            or stat.S_ISLNK(named_before.st_mode)
            or not stat.S_ISREG(named_before.st_mode)
            or (opened.st_dev, opened.st_ino)
            != (named_before.st_dev, named_before.st_ino)
        ):
            raise ArtifactValidationError(
                f"canonical artifact is not a pinned regular file: {path}"
            )

        digest = hashlib.sha256()
        for chunk in iter(lambda: os.read(descriptor, 1024 * 1024), b""):
            digest.update(chunk)

        after = os.fstat(descriptor)
        try:
            named_after = path.lstat()
        except OSError as exc:
            raise ArtifactValidationError(
                f"canonical artifact changed while reading: {path}"
            ) from exc
        stable_fields = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
        if any(
            getattr(opened, field) != getattr(after, field)
            for field in stable_fields
        ) or any(
            getattr(after, field) != getattr(named_after, field)
            for field in stable_fields
        ):
            raise ArtifactValidationError(
                f"canonical artifact changed while reading: {path}"
            )
        return digest.hexdigest(), _git_mode(after)
    finally:
        os.close(descriptor)


def _inventory_with_modes(
    repo_root: Path,
    skill_path: Path,
    skill_root: str,
) -> tuple[dict[str, str], dict[str, str]]:
    if not skill_path.exists():
        return {}, {}
    try:
        root_mode = skill_path.lstat().st_mode
    except FileNotFoundError:
        return {}, {}
    if stat.S_ISLNK(root_mode):
        raise ArtifactValidationError(f"skill root is a symlink: {skill_path}")
    if not stat.S_ISDIR(root_mode):
        raise ArtifactValidationError(
            f"skill root must be a directory: {skill_path}"
        )

    inventory: dict[str, str] = {}
    modes: dict[str, str] = {}
    for current, dirs, files in os.walk(skill_path, followlinks=False):
        current_path = Path(current)
        for name in tuple(dirs):
            candidate = current_path / name
            mode = candidate.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise ArtifactValidationError(
                    f"symlink inside canonical skill is not allowed: {candidate}"
                )
            if not stat.S_ISDIR(mode):
                raise ArtifactValidationError(
                    f"non-directory entry in directory list: {candidate}"
                )
        for name in files:
            candidate = current_path / name
            mode = candidate.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise ArtifactValidationError(
                    f"symlink inside canonical skill is not allowed: {candidate}"
                )
            if not stat.S_ISREG(mode):
                raise ArtifactValidationError(
                    f"special file inside canonical skill is not allowed: {candidate}"
                )
            suffix = candidate.relative_to(skill_path).as_posix()
            target = f"{skill_root}/{suffix}"
            digest, git_mode = _file_digest_and_mode(candidate)
            inventory[target] = digest
            modes[target] = git_mode
    return dict(sorted(inventory.items())), dict(sorted(modes.items()))


def _inventory(repo_root: Path, skill_path: Path, skill_root: str) -> dict[str, str]:
    return _inventory_with_modes(repo_root, skill_path, skill_root)[0]


def _state_inventory(
    inventory: Mapping[str, str],
    modes: Mapping[str, str],
) -> dict[str, str]:
    if set(inventory) != set(modes):
        raise ArtifactValidationError("artifact inventory modes are incomplete")
    return {
        path: hashlib.sha256(
            f"{modes[path]}\0{inventory[path]}".encode("ascii")
        ).hexdigest()
        for path in sorted(inventory)
    }


def _directory_identity(path: Path) -> tuple[int, int] | None:
    """Return the directory inode identity without following a symlink."""
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ArtifactValidationError(
            f"canonical skill root is not a regular directory: {path}"
        )
    return metadata.st_dev, metadata.st_ino


def _validate_managed_manifest(
    entry: Mapping[str, Any],
    *,
    owner: str,
    skill_root: str,
) -> dict[str, Mapping[str, str]]:
    raw = entry.get("managed_files")
    if not isinstance(raw, list):
        raise ArtifactValidationError("entry.managed_files must be an array")
    managed: dict[str, Mapping[str, str]] = {}
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ArtifactValidationError(
                f"managed_files[{index}] must be an object"
            )
        path = item.get("path")
        digest = item.get("sha256")
        declared_owner = item.get("owner")
        mode = item.get("mode")
        if not _safe_relative_posix(path) or not _inside(str(path), skill_root):
            raise ArtifactValidationError(
                f"managed_files[{index}].path is outside the skill root: {path!r}"
            )
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise ArtifactValidationError(
                f"managed_files[{index}].sha256 is not SHA-256"
            )
        if declared_owner != owner:
            raise ArtifactValidationError(
                f"managed_files[{index}] owner {declared_owner!r} "
                f"does not match entry owner {owner!r}"
            )
        if mode not in GIT_FILE_MODES:
            raise ArtifactValidationError(
                f"managed_files[{index}].mode must be 100644 or 100755"
            )
        if path in managed:
            raise ArtifactValidationError(f"duplicate managed path: {path}")
        managed[str(path)] = MappingProxyType(
            {
                "path": str(path),
                "sha256": digest.lower(),
                "owner": owner,
                "mode": str(mode),
            }
        )
    return managed


def _validate_scope_target(
    value: object,
    *,
    label: str,
    skill_root: str,
    allow_root: bool = False,
) -> str:
    canonical = _safe_relative_posix(value)
    contained = _inside(str(value), skill_root)
    if not canonical or not (
        contained or (allow_root and str(value) == skill_root)
    ):
        raise ArtifactValidationError(
            f"{label} is outside the canonical skill root: {value!r}"
        )
    return str(value)


def _targets_from_origin(
    entry: Mapping[str, Any],
    *,
    origin_index: int,
    managed_paths: set[str],
    skill_root: str,
) -> set[str]:
    origins = entry.get("origins")
    if not isinstance(origins, list):
        raise ArtifactValidationError(
            "origin_index requires entry.origins to be an array"
        )
    if (
        isinstance(origin_index, bool)
        or not isinstance(origin_index, int)
        or origin_index < 0
        or origin_index >= len(origins)
    ):
        raise ArtifactValidationError(f"origin_index is out of range: {origin_index}")
    origin = origins[origin_index]
    if not isinstance(origin, Mapping):
        raise ArtifactValidationError(
            f"entry.origins[{origin_index}] must be an object"
        )
    artifacts = origin.get("artifacts")
    if not isinstance(artifacts, list):
        raise ArtifactValidationError(
            f"entry.origins[{origin_index}].artifacts must be an array"
        )

    owned: set[str] = set()
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, Mapping):
            raise ArtifactValidationError(
                f"entry.origins[{origin_index}].artifacts[{index}] "
                "must be an object"
            )
        artifact_type = artifact.get("type", "file")
        target = _validate_scope_target(
            artifact.get("target"),
            label=f"entry.origins[{origin_index}].artifacts[{index}].target",
            skill_root=skill_root,
            allow_root=artifact_type == "directory",
        )
        if artifact_type == "file":
            if target in managed_paths:
                owned.add(target)
        elif artifact_type == "directory":
            boundary = PurePosixPath(target)
            owned.update(
                path
                for path in managed_paths
                if PurePosixPath(path) == boundary
                or boundary in PurePosixPath(path).parents
            )
        else:
            raise ArtifactValidationError(
                f"entry.origins[{origin_index}].artifacts[{index}].type "
                f"is unsupported: {artifact_type!r}"
            )
    return owned


def _origin_claims_target(
    entry: Mapping[str, Any],
    *,
    origin_index: int,
    target: str,
    skill_root: str,
) -> bool:
    """Whether one origin's declared scope covers a desired target.

    Unlike ``_targets_from_origin``, this predicate is deliberately independent
    of the old managed manifest.  It therefore protects brand-new payloads from
    a directory claim held by another origin.
    """
    origins = entry.get("origins")
    if not isinstance(origins, list) or not (0 <= origin_index < len(origins)):
        raise ArtifactValidationError(f"origin_index is out of range: {origin_index}")
    origin = origins[origin_index]
    if not isinstance(origin, Mapping):
        raise ArtifactValidationError(
            f"entry.origins[{origin_index}] must be an object"
        )
    artifacts = origin.get("artifacts")
    if not isinstance(artifacts, list):
        raise ArtifactValidationError(
            f"entry.origins[{origin_index}].artifacts must be an array"
        )
    requested = PurePosixPath(target)
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, Mapping):
            raise ArtifactValidationError(
                f"entry.origins[{origin_index}].artifacts[{index}] "
                "must be an object"
            )
        artifact_type = artifact.get("type", "file")
        declared = _validate_scope_target(
            artifact.get("target"),
            label=f"entry.origins[{origin_index}].artifacts[{index}].target",
            skill_root=skill_root,
            allow_root=artifact_type == "directory",
        )
        boundary = PurePosixPath(declared)
        if artifact_type == "file" and requested == boundary:
            return True
        if artifact_type == "directory" and (
            requested == boundary or boundary in requested.parents
        ):
            return True
        if artifact_type not in {"file", "directory"}:
            raise ArtifactValidationError(
                f"entry.origins[{origin_index}].artifacts[{index}].type "
                f"is unsupported: {artifact_type!r}"
            )
    return False


def _changed_inventory_paths(
    before: Mapping[str, str], after: Mapping[str, str]
) -> tuple[str, ...]:
    return tuple(
        sorted(
            path
            for path in set(before) | set(after)
            if before.get(path) != after.get(path)
        )
    )


def plan_artifact_set_sync(
    repo_root: str | os.PathLike[str],
    entry: Mapping[str, Any],
    upstream_artifacts: Iterable[ArtifactPayload | Mapping[str, Any]],
    checkpoint: Mapping[str, Any],
    *,
    origin_index: int | None = None,
    owned_targets: Iterable[str] | None = None,
    protected_targets: Iterable[str] = (),
) -> SyncPlan:
    """Build a complete, read-only synchronization plan.

    Planning performs only reads.  Ownership conflicts are recorded on the
    plan so reporting callers can present all affected paths at once; applying
    a blocked plan raises :class:`OwnershipConflictError`.
    """
    root_input = Path(repo_root)
    try:
        root = root_input.resolve(strict=True)
    except (FileNotFoundError, RuntimeError) as exc:
        raise ArtifactValidationError(
            f"repository root does not exist or cannot be resolved: {repo_root}"
        ) from exc
    if not root.is_dir():
        raise ArtifactValidationError(f"repository root is not a directory: {root}")
    if not isinstance(entry, Mapping):
        raise ArtifactValidationError("entry must be a mapping")
    if not isinstance(checkpoint, Mapping):
        raise ArtifactValidationError("checkpoint must be a mapping")

    repo_skill = entry.get("repo_skill")
    if not _safe_relative_posix(repo_skill):
        raise ArtifactValidationError(
            f"entry.repo_skill is not canonical relative POSIX: {repo_skill!r}"
        )
    repo_skill = str(repo_skill)
    skill_root = PurePosixPath(repo_skill).parent.as_posix()
    if skill_root == "." or not _safe_relative_posix(skill_root):
        raise ArtifactValidationError(
            f"entry.repo_skill has no safe canonical skill root: {repo_skill!r}"
        )
    owner = _entry_owner(entry, skill_root)
    if not owner:
        raise ArtifactValidationError("entry has no usable ownership identity")

    payloads = tuple(_coerce_payload(value) for value in upstream_artifacts)
    if not payloads:
        raise ArtifactValidationError("complete upstream artifact set is empty")
    targets: set[str] = set()
    for payload in payloads:
        if not _inside(payload.target, skill_root):
            raise ArtifactValidationError(
                f"artifact target is outside {skill_root}: {payload.target}"
            )
        if payload.target in targets:
            raise ArtifactValidationError(
                f"duplicate upstream artifact target: {payload.target}"
            )
        targets.add(payload.target)
    if repo_skill not in targets:
        raise ArtifactValidationError(
            f"complete artifact set does not contain repo_skill: {repo_skill}"
        )

    # Deterministic output is important for mapping idempotence.
    payloads = tuple(sorted(payloads, key=lambda item: (item.target, item.source)))
    target_by_path = {item.target: item for item in payloads}
    old_managed_records = _validate_managed_manifest(
        entry, owner=owner, skill_root=skill_root
    )
    old_managed_paths = set(old_managed_records)
    if origin_index is not None and owned_targets is not None:
        raise ArtifactValidationError(
            "origin_index and owned_targets are mutually exclusive"
        )
    if origin_index is not None:
        selected_owned = _targets_from_origin(
            entry,
            origin_index=origin_index,
            managed_paths=old_managed_paths,
            skill_root=skill_root,
        )
        origins = entry.get("origins")
        if not isinstance(origins, list):  # defensive; helper already checked
            raise ArtifactValidationError(
                "origin_index requires entry.origins to be an array"
            )
        other_origin_owned: set[str] = set()
        other_origin_payload_claims: set[str] = set()
        for other_index in range(len(origins)):
            if other_index == origin_index:
                continue
            other_origin_owned.update(
                _targets_from_origin(
                    entry,
                    origin_index=other_index,
                    managed_paths=old_managed_paths,
                    skill_root=skill_root,
                )
            )
            other_origin_payload_claims.update(
                target
                for target in targets
                if _origin_claims_target(
                    entry,
                    origin_index=other_index,
                    target=target,
                    skill_root=skill_root,
                )
            )
        unclaimed_payloads = sorted(
            target
            for target in targets
            if not _origin_claims_target(
                entry,
                origin_index=origin_index,
                target=target,
                skill_root=skill_root,
            )
        )
        if unclaimed_payloads:
            raise ArtifactValidationError(
                "selected origin does not claim payload target(s): "
                + ", ".join(unclaimed_payloads)
            )
        # Ambiguous broad-directory claims are resolved conservatively: an
        # explicit or directory claim from any non-selected origin protects the
        # file.  The provenance validator may separately reject the overlap,
        # but the transaction engine must never turn it into deletion authority.
        selected_owned.difference_update(other_origin_owned)
    elif owned_targets is not None:
        selected_owned = {
            _validate_scope_target(
                value,
                label="owned_targets item",
                skill_root=skill_root,
            )
            for value in owned_targets
        }
        unknown_owned = selected_owned - old_managed_paths
        if unknown_owned:
            raise ArtifactValidationError(
                "owned_targets lack managed-file checkpoints: "
                + ", ".join(sorted(unknown_owned))
            )
    else:
        origins = entry.get("origins")
        if entry.get("kind") != "mirror" or not (
            isinstance(origins, list) and len(origins) == 1
        ):
            raise ArtifactValidationError(
                "implicit ownership is allowed only for a single-origin "
                "mirror; pass origin_index or owned_targets explicitly"
            )
        # A validated single-origin mirror owns its complete managed inventory.
        # Overlay, composite, bundle, and ambiguous multi-origin entries must
        # always select an origin scope explicitly.
        selected_owned = set(old_managed_paths)

    explicit_protected = {
        _validate_scope_target(
            value,
            label="protected_targets item",
            skill_root=skill_root,
        )
        for value in protected_targets
    }
    overlap = selected_owned & explicit_protected
    if overlap:
        raise ArtifactValidationError(
            "targets cannot be both owned and protected: "
            + ", ".join(sorted(overlap))
        )
    protected = (old_managed_paths - selected_owned) | explicit_protected
    if origin_index is not None:
        protected |= other_origin_payload_claims
    old_managed = {
        path: record["sha256"] for path, record in old_managed_records.items()
    }
    old_managed_modes = {
        path: record["mode"] for path, record in old_managed_records.items()
    }

    skill_path = root.joinpath(*PurePosixPath(skill_root).parts)
    _assert_no_symlink_ancestors(root, skill_path)
    for payload in payloads:
        _assert_no_symlink_ancestors(
            root, root.joinpath(*PurePosixPath(payload.target).parts)
        )
    baseline, baseline_modes = _inventory_with_modes(
        root, skill_path, skill_root
    )
    baseline_root_identity = _directory_identity(skill_path)

    drift: list[Drift] = []
    user_modified: set[str] = set()
    unowned_conflicts: set[str] = set()
    changed: set[str] = set()
    pruned: set[str] = set()

    for target, payload in target_by_path.items():
        new_digest = _sha256_bytes(payload.data)
        current_digest = baseline.get(target)
        current_mode = baseline_modes.get(target)
        expected_digest = old_managed.get(target)
        expected_mode = old_managed_modes.get(target)
        if target in protected:
            unowned_conflicts.add(target)
            continue
        if current_digest is None:
            changed.add(target)
            if expected_digest is not None:
                drift.append(Drift(target, "missing", expected_digest, None))
            continue
        if expected_digest is None:
            # Even identical bytes are not ownership authority: silently
            # adopting an unowned file would permit deleting it on a later run.
            unowned_conflicts.add(target)
            continue
        if current_digest != expected_digest:
            drift.append(
                Drift(target, "hash_mismatch", expected_digest, current_digest)
            )
            if current_digest != new_digest:
                user_modified.add(target)
        if current_mode != expected_mode:
            drift.append(
                Drift(
                    target,
                    "mode_mismatch",
                    expected_digest,
                    current_digest,
                    expected_mode,
                    current_mode,
                )
            )
            # For a retained target, executable mode is managed metadata and
            # the reviewed payload explicitly declares its desired value.
            # Content drift remains ownership-protected above; mode-only drift
            # may therefore be repaired without treating bytes as modified.
        if current_digest != new_digest or current_mode != payload.mode:
            changed.add(target)

    for path in selected_owned:
        if path in target_by_path:
            continue
        expected_digest = old_managed[path]
        current_digest = baseline.get(path)
        expected_mode = old_managed_modes[path]
        current_mode = baseline_modes.get(path)
        if current_digest is None:
            drift.append(Drift(path, "missing", expected_digest, None))
        elif current_digest != expected_digest or current_mode != expected_mode:
            drift.append(
                Drift(
                    path,
                    (
                        "hash_mismatch"
                        if current_digest != expected_digest
                        else "mode_mismatch"
                    ),
                    expected_digest,
                    current_digest,
                    expected_mode,
                    current_mode,
                )
            )
            user_modified.add(path)
        else:
            pruned.add(path)

    preserved = tuple(
        sorted(set(baseline) - changed - pruned - unowned_conflicts)
    )
    artifacts: tuple[Mapping[str, str], ...] = tuple(
        MappingProxyType(
            {
                "source": payload.source,
                "target": payload.target,
                "type": "file",
            }
        )
        for payload in payloads
    )
    next_managed: dict[str, Mapping[str, str]] = {
        path: record
        for path, record in old_managed_records.items()
        if path not in selected_owned
    }
    for payload in payloads:
        next_managed[payload.target] = MappingProxyType(
            {
                "path": payload.target,
                "sha256": _sha256_bytes(payload.data),
                "owner": owner,
                "mode": payload.mode,
            }
        )
    managed_files: tuple[Mapping[str, str], ...] = tuple(
        next_managed[path] for path in sorted(next_managed)
    )
    content_sha256 = next(
        item["sha256"]
        for item in managed_files
        if item["path"] == repo_skill
    )
    new_checkpoint = deepcopy(dict(checkpoint))
    new_checkpoint["content_sha256"] = content_sha256

    return SyncPlan(
        repo_root=root,
        skill_root=skill_root,
        repo_skill=repo_skill,
        owner=owner,
        payloads=payloads,
        artifacts=artifacts,
        managed_files=managed_files,
        checkpoint=MappingProxyType(new_checkpoint),
        content_sha256=content_sha256,
        changed=tuple(sorted(changed)),
        pruned=tuple(sorted(pruned)),
        preserved=preserved,
        drift=tuple(sorted(drift, key=lambda item: (item.path, item.kind))),
        user_modified=tuple(sorted(user_modified)),
        unowned_conflicts=tuple(sorted(unowned_conflicts)),
        owned_targets=tuple(sorted(selected_owned)),
        protected_targets=tuple(sorted(protected)),
        baseline_inventory=MappingProxyType(baseline),
        baseline_modes=MappingProxyType(baseline_modes),
        baseline_root_identity=baseline_root_identity,
    )


def _result_from_plan(
    plan: SyncPlan, *, applied: bool, dry_run: bool
) -> SyncResult:
    return SyncResult(
        artifacts=plan.artifacts,
        managed_files=plan.managed_files,
        checkpoint=plan.checkpoint,
        content_sha256=plan.content_sha256,
        changed=plan.changed,
        pruned=plan.pruned,
        preserved=plan.preserved,
        drift=plan.drift,
        applied=applied,
        dry_run=dry_run,
    )


def _invoke_fault(fault_injector: FaultInjector | None, event: str) -> None:
    if fault_injector is not None:
        fault_injector(event)


def _remove_empty_parents(path: Path, boundary: Path) -> None:
    current = path
    while current != boundary:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


def _validate_staged_tree(plan: SyncPlan, stage_skill: Path) -> None:
    inventory, modes = _inventory_with_modes(
        plan.repo_root, stage_skill, plan.skill_root
    )
    desired = {
        payload.target: _sha256_bytes(payload.data)
        for payload in plan.payloads
    }
    for path, digest in desired.items():
        payload = next(item for item in plan.payloads if item.target == path)
        if inventory.get(path) != digest or modes.get(path) != payload.mode:
            raise ArtifactValidationError(
                f"staged artifact digest or mode mismatch: {path}"
            )
    for path in plan.pruned:
        if path in inventory:
            raise ArtifactValidationError(
                f"pruned artifact remains in staged tree: {path}"
            )
    for path in plan.preserved:
        if (
            inventory.get(path) != plan.baseline_inventory.get(path)
            or modes.get(path) != plan.baseline_modes.get(path)
        ):
            raise ArtifactValidationError(
                f"preserved artifact changed in staged tree: {path}"
            )


def _build_stage(plan: SyncPlan, stage_skill: Path) -> None:
    skill_path = plan.repo_root.joinpath(*PurePosixPath(plan.skill_root).parts)
    if skill_path.exists():
        # Copy links as links; staged inventory then rejects them.  This avoids
        # following a link that appeared in the source after planning.
        shutil.copytree(skill_path, stage_skill, symlinks=True)
    else:
        stage_skill.mkdir()

    # Validate the copy before opening any destination.  In particular, never
    # let a symlink introduced between planning and copy redirect a stage write
    # outside the transaction directory.
    _inventory(plan.repo_root, stage_skill, plan.skill_root)

    for path in plan.pruned:
        relative = PurePosixPath(path).relative_to(PurePosixPath(plan.skill_root))
        candidate = stage_skill.joinpath(*relative.parts)
        if candidate.exists():
            if candidate.is_symlink() or not candidate.is_file():
                raise ArtifactValidationError(
                    f"managed prune target is not a regular file: {path}"
                )
            candidate.unlink()
            _remove_empty_parents(candidate.parent, stage_skill)

    for payload in plan.payloads:
        relative = PurePosixPath(payload.target).relative_to(
            PurePosixPath(plan.skill_root)
        )
        candidate = stage_skill.joinpath(*relative.parts)
        candidate.parent.mkdir(parents=True, exist_ok=True)
        if candidate.exists() and (
            candidate.is_symlink() or not candidate.is_file()
        ):
            raise ArtifactValidationError(
                f"artifact target is not a regular file: {payload.target}"
            )
        with candidate.open("wb") as handle:
            handle.write(payload.data)
            handle.flush()
            os.fchmod(
                handle.fileno(),
                0o755 if payload.mode == "100755" else 0o644,
            )
            os.fsync(handle.fileno())

    _validate_staged_tree(plan, stage_skill)


def _cleanup_tree(path: Path | None) -> None:
    if path is None:
        return
    try:
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
        elif path.exists():
            shutil.rmtree(path)
    except FileNotFoundError:
        return


def _current_inventory_with_modes(
    plan: SyncPlan,
) -> tuple[dict[str, str], dict[str, str]]:
    skill_path = plan.repo_root.joinpath(*PurePosixPath(plan.skill_root).parts)
    _assert_no_symlink_ancestors(plan.repo_root, skill_path)
    return _inventory_with_modes(
        plan.repo_root, skill_path, plan.skill_root
    )


def _path_lexists(path: Path) -> bool:
    return os.path.lexists(path)


def _expected_installed_inventory(plan: SyncPlan) -> dict[str, str]:
    expected = dict(plan.baseline_inventory)
    for path in plan.pruned:
        expected.pop(path, None)
    for payload in plan.payloads:
        expected[payload.target] = _sha256_bytes(payload.data)
    return dict(sorted(expected.items()))


def _expected_installed_modes(plan: SyncPlan) -> dict[str, str]:
    expected = dict(plan.baseline_modes)
    for path in plan.pruned:
        expected.pop(path, None)
    for payload in plan.payloads:
        expected[payload.target] = payload.mode
    return dict(sorted(expected.items()))


def _expected_installed_state_inventory(plan: SyncPlan) -> dict[str, str]:
    return _state_inventory(
        _expected_installed_inventory(plan),
        _expected_installed_modes(plan),
    )


# Version 2 binds both bytes and executable mode into journal inventories.
# Older byte-only journals are intentionally rejected for manual recovery:
# treating them as authoritative could erase an unreviewed mode change.
JOURNAL_VERSION = 2
JOURNAL_STATES = {
    "staged",
    "old_moved",
    "new_installed",
    "prepared",
    "rolling_back",
    "committing_new",
}
MAX_JOURNAL_BYTES = 16 * 1024 * 1024


def _fsync_directory(path: Path) -> None:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(path, flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISDIR(metadata.st_mode):
            raise ArtifactValidationError(f"not a directory for fsync: {path}")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _replace_tree_and_fsync(source: Path, destination: Path) -> None:
    os.replace(source, destination)
    for parent in {source.parent, destination.parent}:
        _fsync_directory(parent)


def _fsync_tree(path: Path) -> None:
    """Durably flush every regular file and directory in one staged tree."""
    if not path.exists():
        return
    directories: list[Path] = []
    for current, dirs, files in os.walk(path, followlinks=False):
        current_path = Path(current)
        directories.append(current_path)
        for name in dirs:
            candidate = current_path / name
            metadata = candidate.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                raise ArtifactValidationError(
                    f"unsafe directory in staged tree: {candidate}"
                )
        for name in files:
            candidate = current_path / name
            metadata = candidate.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                raise ArtifactValidationError(
                    f"unsafe file in staged tree: {candidate}"
                )
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(candidate, flags)
            try:
                opened = os.fstat(descriptor)
                if (
                    opened.st_dev != metadata.st_dev
                    or opened.st_ino != metadata.st_ino
                ):
                    raise ArtifactValidationError(
                        f"staged file changed while opening: {candidate}"
                    )
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    for directory in reversed(directories):
        _fsync_directory(directory)


def _owned_regular_metadata(path: Path) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ArtifactRecoveryError(f"cannot inspect durable path {path}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ArtifactRecoveryError(
            f"durable path is not a regular non-symlink file: {path}"
        )
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise ArtifactRecoveryError(
            f"durable path is owned by another user: {path}"
        )
    return metadata


def _owned_directory_metadata(path: Path) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ArtifactRecoveryError(f"cannot inspect durable directory {path}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ArtifactRecoveryError(
            f"durable path is not a non-symlink directory: {path}"
        )
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise ArtifactRecoveryError(
            f"durable directory is owned by another user: {path}"
        )
    return metadata


def _journal_existing_identity(path: Path) -> tuple[int, int] | None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    _owned_regular_metadata(path)
    return metadata.st_dev, metadata.st_ino


def _computed_journal_integrity(payload: Mapping[str, Any]) -> str:
    unsigned = {
        key: deepcopy(value)
        for key, value in payload.items()
        if key != "journal_sha256"
    }
    return hashlib.sha256(
        json.dumps(
            unsigned,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _journal_integrity_is_valid(payload: Mapping[str, Any]) -> bool:
    recorded = payload.get("journal_sha256")
    return bool(
        isinstance(recorded, str)
        and SHA256_RE.fullmatch(recorded)
        and recorded.lower() == _computed_journal_integrity(payload)
    )


def _write_journal(path: Path, payload: Mapping[str, Any]) -> None:
    """Atomically persist and directory-fsync a private transaction journal."""
    _ensure_private_lock_root(path.parent)
    before_identity = _journal_existing_identity(path)
    if before_identity is not None:
        existing = _read_journal(path)
        if existing is None or not _journal_integrity_is_valid(existing):
            raise ArtifactRecoveryError(
                f"existing transaction journal failed integrity validation: {path}",
                recovery_paths=(path,),
            )
        immutable_fields = (
            "version",
            "transaction_id",
            "repo_root",
            "skill_root",
            "repo_skill",
            "stage_container",
            "backup_container",
            "baseline_inventory",
            "new_inventory",
            "baseline_root_identity",
            "new_root_identity",
            "stage_container_identity",
            "backup_container_identity",
            "original_existed",
        )
        if any(existing.get(field) != payload.get(field) for field in immutable_fields):
            raise ArtifactRecoveryError(
                f"existing transaction journal immutable fields changed: {path}",
                recovery_paths=(path,),
            )
        existing_authority = existing.get("authority")
        next_authority = payload.get("authority")
        if existing_authority is not None and existing_authority != next_authority:
            raise ArtifactRecoveryError(
                f"existing transaction journal authority changed: {path}",
                recovery_paths=(path,),
            )
    serialized_payload = {
        key: deepcopy(value)
        for key, value in payload.items()
        if key != "journal_sha256"
    }
    serialized_payload["journal_sha256"] = _computed_journal_integrity(
        serialized_payload
    )
    content = (
        json.dumps(
            serialized_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    if len(content) > MAX_JOURNAL_BYTES:
        raise ArtifactValidationError("artifact transaction journal is too large")
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(temporary, flags, 0o600)
        view = memoryview(content)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError(f"short journal write: {temporary}")
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        if _journal_existing_identity(path) != before_identity:
            raise ArtifactRecoveryError(
                f"transaction journal changed concurrently: {path}",
                recovery_paths=(path,),
            )
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _read_journal(path: Path) -> dict[str, Any] | None:
    try:
        before = path.lstat()
    except FileNotFoundError:
        return None
    _owned_regular_metadata(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if (
            opened.st_dev != before.st_dev
            or opened.st_ino != before.st_ino
            or opened.st_size > MAX_JOURNAL_BYTES
        ):
            raise ArtifactRecoveryError(
                f"transaction journal changed or is oversized: {path}",
                recovery_paths=(path,),
            )
        chunks: list[bytes] = []
        remaining = MAX_JOURNAL_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
        if (
            after.st_dev != opened.st_dev
            or after.st_ino != opened.st_ino
            or after.st_size != opened.st_size
        ):
            raise ArtifactRecoveryError(
                f"transaction journal changed while reading: {path}",
                recovery_paths=(path,),
            )
    finally:
        os.close(descriptor)
    raw = b"".join(chunks)
    if len(raw) > MAX_JOURNAL_BYTES:
        raise ArtifactRecoveryError(
            f"transaction journal is oversized: {path}",
            recovery_paths=(path,),
        )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactRecoveryError(
            f"transaction journal is invalid JSON: {path}: {exc}",
            recovery_paths=(path,),
        ) from exc
    if not isinstance(payload, dict):
        raise ArtifactRecoveryError(
            f"transaction journal root is not an object: {path}",
            recovery_paths=(path,),
        )
    return payload


def _remove_journal(path: Path) -> None:
    try:
        _owned_regular_metadata(path)
    except ArtifactRecoveryError:
        if not os.path.lexists(path):
            return
        raise
    path.unlink()
    _fsync_directory(path.parent)


def _relative_to_repo(repo_root: Path, path: Path) -> str:
    try:
        relative = path.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise ArtifactValidationError(
            f"transaction path escapes repository root: {path}"
        ) from exc
    if not _safe_relative_posix(relative):
        raise ArtifactValidationError(
            f"transaction path is not canonical relative POSIX: {relative!r}"
        )
    return relative


def _journal_inventory(value: object, *, skill_root: str, label: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ArtifactRecoveryError(f"journal {label} must be an object")
    result: dict[str, str] = {}
    for path, digest in value.items():
        if (
            not _safe_relative_posix(path)
            or not _inside(str(path), skill_root)
            or not isinstance(digest, str)
            or not SHA256_RE.fullmatch(digest)
        ):
            raise ArtifactRecoveryError(
                f"journal {label} contains an unsafe path or digest: {path!r}"
            )
        result[str(path)] = digest.lower()
    return dict(sorted(result.items()))


def _journal_identity(
    value: object,
    *,
    label: str,
    nullable: bool,
) -> tuple[int, int] | None:
    if value is None and nullable:
        return None
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0
            for item in value
        )
    ):
        raise ArtifactRecoveryError(
            f"journal {label} must be a device/inode pair"
        )
    return int(value[0]), int(value[1])


def _journal_repo_path(
    repo_root: Path,
    value: object,
    *,
    label: str,
    expected_parent: PurePosixPath | None = None,
    prefix: str | None = None,
) -> Path:
    if not _safe_relative_posix(value):
        raise ArtifactRecoveryError(
            f"journal {label} is not canonical relative POSIX: {value!r}"
        )
    relative = PurePosixPath(str(value))
    if expected_parent is not None and relative.parent != expected_parent:
        raise ArtifactRecoveryError(
            f"journal {label} has an unexpected parent: {value!r}"
        )
    if prefix is not None and not relative.name.startswith(prefix):
        raise ArtifactRecoveryError(
            f"journal {label} has an unexpected name: {value!r}"
        )
    path = repo_root.joinpath(*relative.parts)
    try:
        _assert_no_symlink_ancestors(repo_root, path)
    except ArtifactValidationError as exc:
        raise ArtifactRecoveryError(
            f"journal {label} traverses an unsafe path: {path}"
        ) from exc
    return path


def _secure_mapping_digest(repo_root: Path, relative: str) -> str:
    path = _journal_repo_path(repo_root, relative, label="authority.mapping_path")
    before = _owned_regular_metadata(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if opened.st_dev != before.st_dev or opened.st_ino != before.st_ino:
            raise ArtifactRecoveryError(f"mapping changed while opening: {path}")
        digest = hashlib.sha256()
        for chunk in iter(lambda: os.read(descriptor, 1024 * 1024), b""):
            digest.update(chunk)
        after = os.fstat(descriptor)
        if (
            after.st_dev != opened.st_dev
            or after.st_ino != opened.st_ino
            or after.st_size != opened.st_size
        ):
            raise ArtifactRecoveryError(f"mapping changed while reading: {path}")
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def _validate_journal(
    payload: Mapping[str, Any],
    *,
    repo_root: Path,
    skill_root: str,
    journal_path: Path,
) -> dict[str, Any]:
    if not _journal_integrity_is_valid(payload):
        raise ArtifactRecoveryError(
            "transaction journal integrity hash mismatch",
            recovery_paths=(journal_path,),
        )
    if payload.get("version") != JOURNAL_VERSION:
        raise ArtifactRecoveryError(
            f"unsupported transaction journal version: {payload.get('version')!r}",
            recovery_paths=(journal_path,),
        )
    if payload.get("repo_root") != str(repo_root) or payload.get("skill_root") != skill_root:
        raise ArtifactRecoveryError(
            "transaction journal identity does not match the acquired skill lock",
            recovery_paths=(journal_path,),
        )
    state = payload.get("state")
    if state not in JOURNAL_STATES:
        raise ArtifactRecoveryError(
            f"transaction journal has invalid state: {state!r}",
            recovery_paths=(journal_path,),
        )
    repo_skill = payload.get("repo_skill")
    if (
        not _safe_relative_posix(repo_skill)
        or PurePosixPath(str(repo_skill)).parent.as_posix() != skill_root
    ):
        raise ArtifactRecoveryError(
            f"transaction journal has invalid repo_skill: {repo_skill!r}",
            recovery_paths=(journal_path,),
        )
    skill_parent = PurePosixPath(skill_root).parent
    skill_name = PurePosixPath(skill_root).name
    stage_container = _journal_repo_path(
        repo_root,
        payload.get("stage_container"),
        label="stage_container",
        expected_parent=skill_parent,
        prefix=f".{skill_name}.artifact-stage-",
    )
    backup_container = _journal_repo_path(
        repo_root,
        payload.get("backup_container"),
        label="backup_container",
        expected_parent=skill_parent,
        prefix=f".{skill_name}.artifact-backup-",
    )
    for container in (stage_container, backup_container):
        if os.path.lexists(container):
            _owned_directory_metadata(container)
    stage_container_identity = _journal_identity(
        payload.get("stage_container_identity"),
        label="stage_container_identity",
        nullable=False,
    )
    backup_container_identity = _journal_identity(
        payload.get("backup_container_identity"),
        label="backup_container_identity",
        nullable=False,
    )
    for container, expected_identity in (
        (stage_container, stage_container_identity),
        (backup_container, backup_container_identity),
    ):
        if os.path.lexists(container):
            metadata = _owned_directory_metadata(container)
            if (metadata.st_dev, metadata.st_ino) != expected_identity:
                raise ArtifactRecoveryError(
                    f"durable transaction container inode changed: {container}",
                    recovery_paths=(journal_path, container),
                )
    baseline = _journal_inventory(
        payload.get("baseline_inventory"),
        skill_root=skill_root,
        label="baseline_inventory",
    )
    installed = _journal_inventory(
        payload.get("new_inventory"),
        skill_root=skill_root,
        label="new_inventory",
    )
    if str(repo_skill) not in installed:
        raise ArtifactRecoveryError(
            "transaction journal new inventory omits repo_skill",
            recovery_paths=(journal_path,),
        )
    baseline_root_identity = _journal_identity(
        payload.get("baseline_root_identity"),
        label="baseline_root_identity",
        nullable=True,
    )
    new_root_identity = _journal_identity(
        payload.get("new_root_identity"),
        label="new_root_identity",
        nullable=False,
    )
    transaction_id = payload.get("transaction_id")
    if not isinstance(transaction_id, str) or not re.fullmatch(
        r"[0-9a-f]{32}",
        transaction_id,
    ):
        raise ArtifactRecoveryError(
            "journal transaction_id is invalid",
            recovery_paths=(journal_path,),
        )
    authority = payload.get("authority")
    if authority is not None:
        if not isinstance(authority, dict):
            raise ArtifactRecoveryError("journal authority must be null or an object")
        mapping_path = authority.get("mapping_path")
        before_hash = authority.get("before_sha256")
        after_hash = authority.get("after_sha256")
        if (
            not _safe_relative_posix(mapping_path)
            or not isinstance(before_hash, str)
            or not SHA256_RE.fullmatch(before_hash)
            or not isinstance(after_hash, str)
            or not SHA256_RE.fullmatch(after_hash)
            or before_hash.lower() == after_hash.lower()
        ):
            raise ArtifactRecoveryError(
                "journal authority is malformed",
                recovery_paths=(journal_path,),
            )
        _journal_repo_path(
            repo_root,
            mapping_path,
            label="authority.mapping_path",
        )
        authority = {
            "mapping_path": str(mapping_path),
            "before_sha256": before_hash.lower(),
            "after_sha256": after_hash.lower(),
        }
    explicit_commit = payload.get("explicit_commit", False)
    if not isinstance(explicit_commit, bool):
        raise ArtifactRecoveryError("journal explicit_commit must be boolean")
    original_existed = payload.get("original_existed")
    if not isinstance(original_existed, bool):
        raise ArtifactRecoveryError("journal original_existed must be boolean")
    return {
        **dict(payload),
        "baseline_inventory": baseline,
        "new_inventory": installed,
        "stage_container_path": stage_container,
        "backup_container_path": backup_container,
        "skill_path": repo_root.joinpath(*PurePosixPath(skill_root).parts),
        "authority": authority,
        "explicit_commit": explicit_commit,
        "original_existed": original_existed,
        "baseline_root_identity": baseline_root_identity,
        "new_root_identity": new_root_identity,
        "stage_container_identity": stage_container_identity,
        "backup_container_identity": backup_container_identity,
    }


def _tree_inventory_kind(
    *,
    repo_root: Path,
    candidate: Path,
    skill_root: str,
    baseline: Mapping[str, str],
    installed: Mapping[str, str],
    baseline_identity: tuple[int, int] | None,
    new_identity: tuple[int, int],
) -> str:
    if not os.path.lexists(candidate):
        return "missing"
    metadata = _owned_directory_metadata(candidate)
    identity = (metadata.st_dev, metadata.st_ino)
    inventory, modes = _inventory_with_modes(
        repo_root, candidate, skill_root
    )
    state_inventory = _state_inventory(inventory, modes)
    if _directory_identity(candidate) != identity:
        return "other"
    if state_inventory == dict(baseline) and identity == baseline_identity:
        return "baseline"
    if state_inventory == dict(installed) and identity == new_identity:
        return "new"
    return "other"


def _journal_recovery_paths(journal: Mapping[str, Any], journal_path: Path) -> tuple[Path, ...]:
    return tuple(
        path
        for path in (
            journal_path,
            journal["skill_path"],
            journal["stage_container_path"],
            journal["backup_container_path"],
        )
        if os.path.lexists(path)
    )


def _validate_recovery_container(
    path: Path,
    *,
    allowed_names: set[str],
    journal_path: Path,
    expected_identity: tuple[int, int],
) -> None:
    if not os.path.lexists(path):
        return
    _owned_directory_metadata(path)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != expected_identity:
            raise ArtifactRecoveryError(
                f"recovery container inode changed: {path}",
                recovery_paths=(journal_path, path),
            )
        names = {entry.name for entry in os.scandir(descriptor)}
    except OSError as exc:
        raise ArtifactRecoveryError(
            f"cannot inspect recovery container {path}: {exc}",
            recovery_paths=(journal_path, path),
        ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    unexpected = names - allowed_names
    if unexpected:
        raise ArtifactRecoveryError(
            f"recovery container has unexpected entries: {path}: "
            + ", ".join(sorted(unexpected)),
            recovery_paths=(journal_path, path),
        )


def _recover_pending_transaction(
    repo_root: Path,
    skill_root: str,
    journal_path: Path,
) -> None:
    raw = _read_journal(journal_path)
    if raw is None:
        return
    journal = _validate_journal(
        raw,
        repo_root=repo_root,
        skill_root=skill_root,
        journal_path=journal_path,
    )
    skill_path: Path = journal["skill_path"]
    stage_container: Path = journal["stage_container_path"]
    backup_container: Path = journal["backup_container_path"]
    stage_skill = stage_container / "new"
    backup_skill = backup_container / "previous"
    baseline = journal["baseline_inventory"]
    installed = journal["new_inventory"]
    _validate_recovery_container(
        stage_container,
        allowed_names={"new", "recovery-new"},
        journal_path=journal_path,
        expected_identity=journal["stage_container_identity"],
    )
    _validate_recovery_container(
        backup_container,
        allowed_names={"previous"},
        journal_path=journal_path,
        expected_identity=journal["backup_container_identity"],
    )

    canonical_kind = _tree_inventory_kind(
        repo_root=repo_root,
        candidate=skill_path,
        skill_root=skill_root,
        baseline=baseline,
        installed=installed,
        baseline_identity=journal["baseline_root_identity"],
        new_identity=journal["new_root_identity"],
    )
    stage_kind = _tree_inventory_kind(
        repo_root=repo_root,
        candidate=stage_skill,
        skill_root=skill_root,
        baseline=baseline,
        installed=installed,
        baseline_identity=journal["baseline_root_identity"],
        new_identity=journal["new_root_identity"],
    )
    backup_kind = _tree_inventory_kind(
        repo_root=repo_root,
        candidate=backup_skill,
        skill_root=skill_root,
        baseline=baseline,
        installed=installed,
        baseline_identity=journal["baseline_root_identity"],
        new_identity=journal["new_root_identity"],
    )
    if "other" in {canonical_kind, stage_kind, backup_kind}:
        raise ArtifactRecoveryError(
            "durable artifact transaction contains unrecognized concurrent data",
            recovery_paths=_journal_recovery_paths(journal, journal_path),
        )

    keep_new = bool(journal["explicit_commit"])
    authority = journal["authority"]
    if not keep_new and authority is not None:
        try:
            current_mapping_hash = _secure_mapping_digest(
                repo_root,
                authority["mapping_path"],
            )
        except ArtifactRecoveryError as exc:
            raise ArtifactRecoveryError(
                f"cannot resolve mapping authority during recovery: {exc}",
                recovery_paths=_journal_recovery_paths(journal, journal_path),
            ) from exc
        if current_mapping_hash == authority["before_sha256"]:
            keep_new = False
        elif current_mapping_hash == authority["after_sha256"]:
            keep_new = True
        else:
            raise ArtifactRecoveryError(
                "mapping authority hash matches neither before nor after state",
                recovery_paths=_journal_recovery_paths(journal, journal_path),
            )

    if keep_new:
        if canonical_kind != "new":
            raise ArtifactRecoveryError(
                "mapping committed new authority but canonical new tree is unavailable",
                recovery_paths=_journal_recovery_paths(journal, journal_path),
            )
    elif not journal["original_existed"]:
        if canonical_kind == "new":
            quarantine = stage_container / "recovery-new"
            if os.path.lexists(quarantine):
                raise ArtifactRecoveryError(
                    f"recovery quarantine already exists: {quarantine}",
                    recovery_paths=_journal_recovery_paths(journal, journal_path),
                )
            _replace_tree_and_fsync(skill_path, quarantine)
            canonical_kind = "missing"
        if canonical_kind != "missing":
            raise ArtifactRecoveryError(
                "cannot restore originally absent canonical skill safely",
                recovery_paths=_journal_recovery_paths(journal, journal_path),
            )
    else:
        if canonical_kind == "baseline":
            pass
        elif canonical_kind in {"new", "missing"} and backup_kind == "baseline":
            if canonical_kind == "new":
                quarantine = stage_container / "recovery-new"
                if os.path.lexists(quarantine):
                    raise ArtifactRecoveryError(
                        f"recovery quarantine already exists: {quarantine}",
                        recovery_paths=_journal_recovery_paths(journal, journal_path),
                    )
                _replace_tree_and_fsync(skill_path, quarantine)
            _replace_tree_and_fsync(backup_skill, skill_path)
            canonical_kind = "baseline"
        else:
            raise ArtifactRecoveryError(
                "cannot restore baseline tree from durable transaction",
                recovery_paths=_journal_recovery_paths(journal, journal_path),
            )

    final_kind = _tree_inventory_kind(
        repo_root=repo_root,
        candidate=skill_path,
        skill_root=skill_root,
        baseline=baseline,
        installed=installed,
        baseline_identity=journal["baseline_root_identity"],
        new_identity=journal["new_root_identity"],
    )
    expected_final_kind = (
        "new"
        if keep_new
        else "baseline"
        if journal["original_existed"]
        else "missing"
    )
    if final_kind != expected_final_kind:
        raise ArtifactRecoveryError(
            "canonical tree changed during durable recovery",
            recovery_paths=_journal_recovery_paths(journal, journal_path),
        )
    _validate_recovery_container(
        stage_container,
        allowed_names={"new", "recovery-new"},
        journal_path=journal_path,
        expected_identity=journal["stage_container_identity"],
    )
    _validate_recovery_container(
        backup_container,
        allowed_names={"previous"},
        journal_path=journal_path,
        expected_identity=journal["backup_container_identity"],
    )
    _cleanup_tree(stage_container)
    _cleanup_tree(backup_container)
    _fsync_directory(skill_path.parent)
    _remove_journal(journal_path)


class ArtifactTransaction:
    """A prepared filesystem switch awaiting mapping finalization.

    Use this as a context manager around the caller's atomic mapping write::

        with prepare_artifact_set_sync(plan) as transaction:
            atomic_write_mapping(transaction.result.metadata_patch())
            transaction.commit()

    Leaving the context without ``commit()``, including because the mapping
    writer raised, restores the old canonical directory.
    """

    def __init__(
        self,
        *,
        plan: SyncPlan,
        result: SyncResult,
        skill_path: Path,
        stage_container: Path | None,
        backup_container: Path | None,
        stage_skill: Path | None,
        backup_skill: Path | None,
        original_existed: bool,
        lock: _SkillLock,
        state: str,
        journal_path: Path | None = None,
        journal_payload: dict[str, Any] | None = None,
    ) -> None:
        self.plan = plan
        self.result = result
        self._skill_path = skill_path
        self._stage_container = stage_container
        self._backup_container = backup_container
        self._stage_skill = stage_skill
        self._backup_skill = backup_skill
        self._original_existed = original_existed
        self._lock = lock
        self._old_moved = False
        self._new_installed = False
        self._recovery_path: Path | None = None
        self._state = state
        self._journal_path = journal_path
        self._journal_payload = (
            deepcopy(journal_payload)
            if journal_payload is not None
            else None
        )
        self._authority = (
            deepcopy(self._journal_payload.get("authority"))
            if self._journal_payload is not None
            else None
        )

    @property
    def state(self) -> str:
        return self._state

    @property
    def active(self) -> bool:
        return self._state in {"preparing", "prepared"}

    @property
    def recovery_path(self) -> Path | None:
        """Preserved concurrent content or an unrestored backup, if any."""
        return self._recovery_path

    @property
    def lock_path(self) -> Path:
        return self._lock.path

    @property
    def journal_path(self) -> Path | None:
        return self._journal_path

    def _persist_journal(
        self,
        *,
        state: str | None = None,
        explicit_commit: bool | None = None,
    ) -> None:
        if self._journal_path is None or self._journal_payload is None:
            return
        if state is not None:
            if state not in JOURNAL_STATES:
                raise ArtifactValidationError(
                    f"invalid journal state transition: {state!r}"
                )
            self._journal_payload["state"] = state
        if explicit_commit is not None:
            self._journal_payload["explicit_commit"] = explicit_commit
        _write_journal(self._journal_path, self._journal_payload)

    def bind_authority(
        self,
        mapping_path: str | os.PathLike[str],
        before_sha256: str,
        after_sha256: str,
    ) -> None:
        """Durably bind crash recovery to one atomic mapping replacement.

        Call this after prepare returns and before replacing ``mapping_path``.
        The current mapping must still match ``before_sha256``.
        """
        if self._state != "prepared":
            raise ArtifactValidationError(
                f"transaction cannot bind authority from state {self._state!r}"
            )
        if (
            not isinstance(before_sha256, str)
            or not SHA256_RE.fullmatch(before_sha256)
            or not isinstance(after_sha256, str)
            or not SHA256_RE.fullmatch(after_sha256)
            or before_sha256.lower() == after_sha256.lower()
        ):
            raise ArtifactValidationError(
                "authority hashes must be distinct SHA-256 values"
            )
        candidate = Path(mapping_path)
        if candidate.is_absolute():
            lexical_root = next(
                (
                    ancestor
                    for ancestor in (candidate, *candidate.parents)
                    if ancestor.exists()
                    and ancestor.resolve(strict=True) == self.plan.repo_root
                ),
                None,
            )
            if lexical_root is None:
                raise ArtifactValidationError(
                    f"authority mapping escapes repository root: {candidate}"
                )
            try:
                relative = candidate.relative_to(lexical_root).as_posix()
            except ValueError as exc:  # pragma: no cover - guarded above
                raise ArtifactValidationError(
                    f"authority mapping escapes repository root: {candidate}"
                ) from exc
            current = lexical_root
            for component in PurePosixPath(relative).parts:
                current = current / component
                try:
                    metadata = current.lstat()
                except OSError as exc:
                    raise ArtifactValidationError(
                        f"cannot inspect authority mapping path: {current}"
                    ) from exc
                if stat.S_ISLNK(metadata.st_mode):
                    raise ArtifactRecoveryError(
                        f"authority mapping traverses an unsafe path: {current}"
                    )
        else:
            relative = candidate.as_posix()
        if not _safe_relative_posix(relative):
            raise ArtifactValidationError(
                f"authority mapping is not canonical relative POSIX: {relative!r}"
            )
        current = _secure_mapping_digest(self.plan.repo_root, relative)
        if current != before_sha256.lower():
            raise ConcurrentModificationError((relative,))
        authority = {
            "mapping_path": relative,
            "before_sha256": before_sha256.lower(),
            "after_sha256": after_sha256.lower(),
        }
        if self._journal_payload is not None:
            existing = self._journal_payload.get("authority")
            if existing is not None and existing != authority:
                raise ArtifactValidationError(
                    "transaction authority is already bound differently"
                )
            self._journal_payload["authority"] = authority
            self._persist_journal()
        self._authority = authority

    def commit(self) -> SyncResult:
        """Finalize the filesystem side after the mapping write succeeds."""
        if self._state != "prepared":
            raise ArtifactValidationError(
                f"transaction cannot commit from state {self._state!r}"
            )
        authority = self._authority
        if isinstance(authority, dict):
            current_mapping_hash = _secure_mapping_digest(
                self.plan.repo_root,
                authority["mapping_path"],
            )
            if current_mapping_hash != authority["after_sha256"]:
                raise ArtifactRecoveryError(
                    "cannot commit artifact transaction before its bound "
                    "mapping reaches the after hash",
                    recovery_paths=tuple(
                        path
                        for path in (
                            self._journal_path,
                            self._skill_path,
                            self._backup_container,
                        )
                        if path is not None and os.path.lexists(path)
                    ),
                )
        self._persist_journal(
            state="committing_new",
            explicit_commit=authority is None,
        )
        self._state = "committing"
        failure: Exception | None = None
        try:
            _cleanup_tree(self._stage_container)
            self._stage_container = None
            _cleanup_tree(self._backup_container)
            self._backup_container = None
            _fsync_directory(self._skill_path.parent)
            if self._journal_path is not None:
                _remove_journal(self._journal_path)
                self._journal_path = None
                self._journal_payload = None
        except Exception as cause:  # noqa: BLE001  # pragma: no cover
            failure = cause
        try:
            self._lock.release()
        except Exception as cause:  # noqa: BLE001  # pragma: no cover
            failure = (
                cause
                if failure is None
                else RuntimeError(f"{failure}; lock release failed: {cause}")
            )
        if failure is not None:
            # The caller's mapping and the live directory already describe the
            # new state.  A partially removed backup is not safe rollback
            # material, so report cleanup failure without attempting restore.
            self._state = "commit_cleanup_failed"
            raise ArtifactApplyError(
                "failed to finalize artifact-set transaction",
                rollback_succeeded=False,
                cause=failure,
                recovery_path=self._backup_container,
            ) from failure
        self._state = "committed"
        return self.result

    def _tree_is_installed_payload(self, candidate: Path) -> bool:
        if not self._new_installed or not _path_lexists(candidate):
            return False
        try:
            current, modes = _inventory_with_modes(
                self.plan.repo_root,
                candidate,
                self.plan.skill_root,
            )
        except ArtifactValidationError:
            return False
        return _state_inventory(
            current,
            modes,
        ) == _expected_installed_state_inventory(self.plan)

    def _preserve_path(self, source: Path) -> None:
        if not _path_lexists(source):
            return
        if self._backup_container is None:
            raise RuntimeError(
                f"cannot preserve concurrent occupant at {source}: "
                "transaction has no recovery container"
            )
        self._recovery_path = self._backup_container
        for index in range(1, 1000):
            destination = (
                self._backup_container / f"concurrent-occupant-{index}"
            )
            if _path_lexists(destination):
                continue
            _replace_tree_and_fsync(source, destination)
            return
        raise RuntimeError(
            f"cannot allocate recovery name under {self._backup_container}"
        )

    def _preserve_concurrent_occupant(self) -> None:
        self._preserve_path(self._skill_path)

    def _quarantine_live_tree_for_rollback(self) -> None:
        if not _path_lexists(self._skill_path):
            return
        if self._stage_container is None:
            raise RuntimeError(
                f"cannot isolate rollback candidate at {self._skill_path}: "
                "transaction has no staging container"
            )
        for index in range(1, 1000):
            candidate = (
                self._stage_container / f"live-rollback-candidate-{index}"
            )
            if _path_lexists(candidate):
                continue
            # Move first, inspect second.  No unrelated process can replace the
            # captured inode between classification and cleanup.
            _replace_tree_and_fsync(self._skill_path, candidate)
            if self._tree_is_installed_payload(candidate):
                self._new_installed = False
            else:
                self._new_installed = False
                self._preserve_path(candidate)
            return
        raise RuntimeError(
            f"cannot allocate rollback quarantine under {self._stage_container}"
        )

    def _restore_old_tree(self) -> None:
        if not self._old_moved:
            return
        if self._backup_skill is None or not _path_lexists(self._backup_skill):
            raise RuntimeError(
                f"canonical backup is missing: {self._backup_skill}"
            )
        # A conforming transaction cannot enter while our lock is held, but an
        # unrelated process may still create the canonical path.  Preserve such
        # occupants, then retry the atomic restore a bounded number of times.
        last_error: OSError | None = None
        for _attempt in range(8):
            if _path_lexists(self._skill_path):
                self._preserve_concurrent_occupant()
            try:
                _replace_tree_and_fsync(self._backup_skill, self._skill_path)
                self._old_moved = False
                return
            except OSError as exc:
                last_error = exc
                if not _path_lexists(self._skill_path):
                    break
        raise RuntimeError(
            f"failed to restore canonical backup {self._backup_skill} "
            f"to {self._skill_path}: {last_error}"
        ) from last_error

    def rollback(self) -> None:
        """Restore the pre-transaction canonical directory and clean temps."""
        if self._state == "rolled_back":
            return
        if self._state == "committed":
            raise ArtifactValidationError("committed transaction cannot roll back")
        if self._state not in {"preparing", "prepared"}:
            raise ArtifactValidationError(
                f"transaction cannot roll back from state {self._state!r}"
            )
        if isinstance(self._authority, dict):
            try:
                mapping_hash = _secure_mapping_digest(
                    self.plan.repo_root,
                    self._authority["mapping_path"],
                )
            except ArtifactRecoveryError as exc:
                self._state = "recovery_required"
                self._lock.release()
                raise ArtifactRecoveryError(
                    f"cannot resolve bound authority while rolling back: {exc}",
                    recovery_paths=tuple(
                        path
                        for path in (
                            self._journal_path,
                            self._skill_path,
                            self._backup_container,
                        )
                        if path is not None and os.path.lexists(path)
                    ),
                ) from exc
            if mapping_hash == self._authority["after_sha256"]:
                self.commit()
                return
            if mapping_hash != self._authority["before_sha256"]:
                self._state = "recovery_required"
                self._lock.release()
                raise ArtifactRecoveryError(
                    "bound mapping matches neither before nor after hash "
                    "during rollback",
                    recovery_paths=tuple(
                        path
                        for path in (
                            self._journal_path,
                            self._skill_path,
                            self._backup_container,
                        )
                        if path is not None and os.path.lexists(path)
                    ),
                )
        rollback_errors: list[Exception] = []
        try:
            self._persist_journal(state="rolling_back", explicit_commit=False)
        except Exception as journal_error:  # noqa: BLE001
            rollback_errors.append(journal_error)
        try:
            if self._old_moved or self._new_installed:
                if _path_lexists(self._skill_path):
                    self._quarantine_live_tree_for_rollback()
                if self._old_moved:
                    self._restore_old_tree()
        except Exception as rollback_error:  # noqa: BLE001  # pragma: no cover
            rollback_errors.append(rollback_error)
        finally:
            try:
                _cleanup_tree(self._stage_container)
            except Exception as cleanup_error:  # noqa: BLE001  # pragma: no cover
                rollback_errors.append(cleanup_error)
            self._stage_container = None
            # Never remove a container that may hold the only old canonical
            # tree or a concurrent occupant.  A surfaced recovery_path is an
            # intentional durable quarantine, not disposable staging.
            if not self._old_moved and self._recovery_path is None:
                try:
                    _cleanup_tree(self._backup_container)
                    self._backup_container = None
                except Exception as cleanup_error:  # noqa: BLE001  # pragma: no cover
                    rollback_errors.append(cleanup_error)
            elif self._backup_container is not None:
                self._recovery_path = self._backup_container
            if not rollback_errors and not self._old_moved:
                try:
                    _fsync_directory(self._skill_path.parent)
                    if self._journal_path is not None:
                        _remove_journal(self._journal_path)
                        self._journal_path = None
                        self._journal_payload = None
                except Exception as journal_error:  # noqa: BLE001
                    rollback_errors.append(journal_error)
            try:
                self._lock.release()
            except Exception as lock_error:  # noqa: BLE001  # pragma: no cover
                rollback_errors.append(lock_error)

        if rollback_errors:
            self._state = "rollback_failed"
            cause = RuntimeError(
                "; ".join(str(error) for error in rollback_errors)
            )
            raise ArtifactApplyError(
                "failed to roll back artifact-set transaction",
                rollback_succeeded=False,
                cause=cause,
                recovery_path=self._recovery_path,
            ) from cause
        self._state = "rolled_back"

    def __enter__(self) -> Self:
        if self._state != "prepared":
            raise ArtifactValidationError(
                f"transaction cannot enter from state {self._state!r}"
            )
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        if self._state == "prepared":
            self.rollback()
        return False


def _validate_plan_for_apply(plan: SyncPlan) -> None:
    if not isinstance(plan, SyncPlan):
        raise ArtifactValidationError("plan must be a SyncPlan")
    # A coordinated mapping batch may still be mixed after a hard exit.
    # Its recovery must finish before the artifact authority is consulted.
    # Fail closed for direct engine callers; sync_upstream recovers this first.
    pending_batch = plan.repo_root / ".hvs-transactions" / "pending"
    if pending_batch.exists() or pending_batch.is_symlink():
        raise ArtifactRecoveryError(
            "recover the repository durable mapping batch before artifact sync",
            recovery_paths=(pending_batch,),
        )
    if plan.blocked:
        raise OwnershipConflictError(
            user_modified=plan.user_modified,
            unowned_conflicts=plan.unowned_conflicts,
        )
    current, current_modes = _current_inventory_with_modes(plan)
    changed_since_plan = _changed_inventory_paths(plan.baseline_inventory, current)
    changed_since_plan = tuple(
        sorted(
            set(changed_since_plan)
            | set(
                _changed_inventory_paths(
                    plan.baseline_modes,
                    current_modes,
                )
            )
        )
    )
    skill_path = plan.repo_root.joinpath(*PurePosixPath(plan.skill_root).parts)
    if _directory_identity(skill_path) != plan.baseline_root_identity:
        changed_since_plan = tuple(
            sorted(set(changed_since_plan) | {f"{plan.skill_root}/<root-inode>"})
        )
    if changed_since_plan:
        raise ConcurrentModificationError(changed_since_plan)


def prepare_artifact_set_sync(
    plan: SyncPlan,
    *,
    fault_injector: FaultInjector | None = None,
    lock_timeout: float = 0.0,
    _held_lock: _SkillLock | None = None,
) -> ArtifactTransaction:
    """Install the new tree while retaining rollback state for mapping commit.

    Fault-injection events are ``after_stage_built``, ``after_backup_rename``,
    ``after_install_rename``, and ``after_live_validation``.
    """
    if not isinstance(plan, SyncPlan):
        raise ArtifactValidationError("plan must be a SyncPlan")
    expected_lock_path = skill_lock_path(plan.repo_root, plan.skill_root)
    if _held_lock is not None:
        if (
            not isinstance(_held_lock, _SkillLock)
            or _held_lock.path != expected_lock_path
            or _held_lock._fd is None
        ):
            raise ArtifactValidationError("invalid coordinator-held skill lock")
        lock = _held_lock
    else:
        lock = _SkillLock(expected_lock_path)
        lock.acquire(lock_timeout)
    stage_container: Path | None = None
    backup_container: Path | None = None
    stage_skill: Path | None = None
    backup_skill: Path | None = None
    transaction: ArtifactTransaction | None = None

    try:
        _recover_pending_transaction(
            plan.repo_root,
            plan.skill_root,
            lock.path.with_suffix(".journal.json"),
        )
        _validate_plan_for_apply(plan)
        skill_path = plan.repo_root.joinpath(
            *PurePosixPath(plan.skill_root).parts
        )
        if not plan.has_filesystem_changes:
            return ArtifactTransaction(
                plan=plan,
                result=_result_from_plan(plan, applied=False, dry_run=False),
                skill_path=skill_path,
                stage_container=None,
                backup_container=None,
                stage_skill=None,
                backup_skill=None,
                original_existed=skill_path.exists(),
                lock=lock,
                state="prepared",
            )

        skill_parent = skill_path.parent
        _assert_no_symlink_ancestors(plan.repo_root, skill_parent)
        skill_parent.mkdir(parents=True, exist_ok=True)
        stage_container = Path(
            tempfile.mkdtemp(
                prefix=f".{skill_path.name}.artifact-stage-",
                dir=skill_parent,
            )
        )
        backup_container = Path(
            tempfile.mkdtemp(
                prefix=f".{skill_path.name}.artifact-backup-",
                dir=skill_parent,
            )
        )
        stage_skill = stage_container / "new"
        backup_skill = backup_container / "previous"
        original_existed = _path_lexists(skill_path)
        stage_container_metadata = stage_container.lstat()
        backup_container_metadata = backup_container.lstat()
        journal_path = lock.path.with_suffix(".journal.json")
        journal_payload = {
            "version": JOURNAL_VERSION,
            "transaction_id": uuid.uuid4().hex,
            "repo_root": str(plan.repo_root),
            "skill_root": plan.skill_root,
            "repo_skill": plan.repo_skill,
            "stage_container": _relative_to_repo(
                plan.repo_root,
                stage_container,
            ),
            "backup_container": _relative_to_repo(
                plan.repo_root,
                backup_container,
            ),
            "baseline_inventory": _state_inventory(
                plan.baseline_inventory,
                plan.baseline_modes,
            ),
            "new_inventory": _expected_installed_state_inventory(plan),
            "baseline_root_identity": (
                list(plan.baseline_root_identity)
                if plan.baseline_root_identity is not None
                else None
            ),
            "new_root_identity": None,
            "stage_container_identity": list(
                (stage_container_metadata.st_dev, stage_container_metadata.st_ino)
            ),
            "backup_container_identity": list(
                (backup_container_metadata.st_dev, backup_container_metadata.st_ino)
            ),
            "original_existed": original_existed,
            "state": "staged",
            "authority": None,
            "explicit_commit": False,
        }
        transaction = ArtifactTransaction(
            plan=plan,
            result=_result_from_plan(plan, applied=True, dry_run=False),
            skill_path=skill_path,
            stage_container=stage_container,
            backup_container=backup_container,
            stage_skill=stage_skill,
            backup_skill=backup_skill,
            original_existed=original_existed,
            lock=lock,
            state="preparing",
            journal_path=journal_path,
            journal_payload=journal_payload,
        )
        _build_stage(plan, stage_skill)
        new_root_identity = _directory_identity(stage_skill)
        if new_root_identity is None:
            raise ArtifactValidationError("staged skill root disappeared")
        transaction._journal_payload["new_root_identity"] = list(
            new_root_identity
        )
        _fsync_tree(stage_skill)
        _fsync_directory(stage_container)
        _fsync_directory(backup_container)
        _fsync_directory(skill_parent)
        transaction._persist_journal(state="staged", explicit_commit=False)
        _invoke_fault(fault_injector, "after_stage_built")

        # Recheck the entire directory immediately before the first rename.
        pre_rename_identity = _directory_identity(skill_path)
        current, current_modes = _current_inventory_with_modes(plan)
        changed_since_plan = _changed_inventory_paths(
            plan.baseline_inventory, current
        )
        changed_since_plan = tuple(
            sorted(
                set(changed_since_plan)
                | set(
                    _changed_inventory_paths(
                        plan.baseline_modes,
                        current_modes,
                    )
                )
            )
        )
        if pre_rename_identity != plan.baseline_root_identity:
            changed_since_plan = tuple(
                sorted(
                    set(changed_since_plan)
                    | {f"{plan.skill_root}/<root-inode>"}
                )
            )
        if changed_since_plan:
            raise ConcurrentModificationError(changed_since_plan)

        if transaction._original_existed:
            _replace_tree_and_fsync(skill_path, backup_skill)
            transaction._old_moved = True
            transaction._persist_journal(state="old_moved")
            moved_identity = _directory_identity(backup_skill)
            moved_inventory, moved_modes = _inventory_with_modes(
                plan.repo_root,
                backup_skill,
                plan.skill_root,
            )
            moved_changes = _changed_inventory_paths(
                plan.baseline_inventory,
                moved_inventory,
            )
            moved_changes = tuple(
                sorted(
                    set(moved_changes)
                    | set(
                        _changed_inventory_paths(
                            plan.baseline_modes,
                            moved_modes,
                        )
                    )
                )
            )
            if moved_identity != pre_rename_identity:
                moved_changes = tuple(
                    sorted(
                        set(moved_changes)
                        | {f"{plan.skill_root}/<root-inode>"}
                    )
                )
            if moved_changes:
                raise ConcurrentModificationError(moved_changes)
        _invoke_fault(fault_injector, "after_backup_rename")

        _replace_tree_and_fsync(stage_skill, skill_path)
        transaction._new_installed = True
        transaction._persist_journal(state="new_installed")
        _invoke_fault(fault_injector, "after_install_rename")

        _validate_staged_tree(plan, skill_path)
        _invoke_fault(fault_injector, "after_live_validation")
        transaction._persist_journal(state="prepared")
        transaction._state = "prepared"
        return transaction
    except Exception as cause:
        try:
            if transaction is not None:
                transaction.rollback()
            else:
                cleanup_errors: list[Exception] = []
                try:
                    _cleanup_tree(stage_container)
                    _cleanup_tree(backup_container)
                except Exception as cleanup_error:  # noqa: BLE001
                    cleanup_errors.append(cleanup_error)
                try:
                    lock.release()
                except Exception as lock_error:  # noqa: BLE001
                    cleanup_errors.append(lock_error)
                if cleanup_errors:
                    raise ArtifactApplyError(
                        "failed to clean an unprepared artifact transaction",
                        rollback_succeeded=False,
                        cause=RuntimeError(
                            "; ".join(str(error) for error in cleanup_errors)
                        ),
                        recovery_path=backup_container,
                    )
        except ArtifactApplyError as rollback_error:
            raise ArtifactApplyError(
                "artifact-set transaction failed",
                rollback_succeeded=False,
                cause=RuntimeError(f"{cause}; {rollback_error}"),
                recovery_path=rollback_error.recovery_path,
            ) from cause

        if isinstance(
            cause,
            (
                ArtifactValidationError,
                ArtifactRecoveryError,
                ConcurrentModificationError,
                OwnershipConflictError,
            ),
        ):
            raise
        raise ArtifactApplyError(
            "artifact-set transaction failed",
            rollback_succeeded=True,
            cause=cause,
            recovery_path=(
                transaction.recovery_path
                if transaction is not None
                else None
            ),
        ) from cause


def apply_artifact_set_sync(
    plan: SyncPlan,
    *,
    dry_run: bool = False,
    fault_injector: FaultInjector | None = None,
    lock_timeout: float = 0.0,
) -> SyncResult:
    """Apply and immediately finalize a plan.

    Callers that also update provenance should instead use
    :func:`prepare_artifact_set_sync` so a mapping-write failure can roll back
    the canonical directory.
    """
    if dry_run:
        _validate_plan_for_apply(plan)
        return _result_from_plan(plan, applied=False, dry_run=True)
    transaction = prepare_artifact_set_sync(
        plan,
        fault_injector=fault_injector,
        lock_timeout=lock_timeout,
    )
    return transaction.commit()


def sync_artifact_set(
    repo_root: str | os.PathLike[str],
    entry: Mapping[str, Any],
    upstream_artifacts: Iterable[ArtifactPayload | Mapping[str, Any]],
    checkpoint: Mapping[str, Any],
    *,
    dry_run: bool = False,
    fault_injector: FaultInjector | None = None,
    lock_timeout: float = 0.0,
    origin_index: int | None = None,
    owned_targets: Iterable[str] | None = None,
    protected_targets: Iterable[str] = (),
) -> SyncResult:
    """Plan and apply one complete artifact set."""
    plan = plan_artifact_set_sync(
        repo_root,
        entry,
        upstream_artifacts,
        checkpoint,
        origin_index=origin_index,
        owned_targets=owned_targets,
        protected_targets=protected_targets,
    )
    return apply_artifact_set_sync(
        plan,
        dry_run=dry_run,
        fault_injector=fault_injector,
        lock_timeout=lock_timeout,
    )


__all__ = [
    "ArtifactApplyError",
    "ArtifactLockError",
    "ArtifactPayload",
    "ArtifactRecoveryError",
    "ArtifactSetSyncError",
    "ArtifactTransaction",
    "ArtifactValidationError",
    "ConcurrentModificationError",
    "Drift",
    "OwnershipConflictError",
    "SyncPlan",
    "SyncResult",
    "apply_artifact_set_sync",
    "plan_artifact_set_sync",
    "prepare_artifact_set_sync",
    "skill_advisory_lock",
    "skill_lock_identity",
    "skill_lock_path",
    "skill_transaction_journal_path",
    "sync_artifact_set",
]
