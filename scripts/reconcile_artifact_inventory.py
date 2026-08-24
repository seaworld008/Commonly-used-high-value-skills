#!/usr/bin/env python3
"""Reconcile canonical skill directories with provenance artifact inventories.

The command is read-only unless ``--write`` is supplied.  It compares every
regular file in an active external skill directory with the artifact and
managed-file declarations in provenance v2.  Undeclared files are classified
against the exact bytes at each origin's resolved commit:

* ``external_exact``: the inferred upstream sibling exists with identical bytes;
* ``local_overlay``: the source tree is available, but no inferred exact source
  exists (or its bytes differ);
* ``unavailable``: the immutable source tree/blob cannot be inspected.

Only exact, path-preserving proposals are admitted automatically.  This is
deliberately narrower than a repository-wide content search: a runtime snapshot
copied from an unrelated upstream directory must remain a local overlay instead
of being falsely claimed by the official skill artifact origin.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import contextlib
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import uuid
from collections import Counter
from copy import deepcopy
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

try:
    from provenance_v2 import (
        ACTIVE_STATUSES,
        COMMIT_RE,
        EXTERNAL_KINDS,
        LOCAL_CURATION_REPO,
        atomic_write_json,
        discover_source_mappings,
        is_local_repo,
        safe_relative_path,
    )
except ModuleNotFoundError:  # pragma: no cover - import path used by unit tests
    from scripts.provenance_v2 import (
        ACTIVE_STATUSES,
        COMMIT_RE,
        EXTERNAL_KINDS,
        LOCAL_CURATION_REPO,
        atomic_write_json,
        discover_source_mappings,
        is_local_repo,
        safe_relative_path,
    )


REPORT_SCHEMA_VERSION = 1
LOCAL_OVERLAY_REPO = LOCAL_CURATION_REPO
VALID_GIT_FILE_MODES = {"100644", "100755"}
IGNORED_DIRECTORY_NAMES = {
    "__pycache__",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}
IGNORED_FILE_NAMES = {".DS_Store"}
IGNORED_FILE_SUFFIXES = {".pyc", ".pyo"}


class SourceUnavailable(RuntimeError):
    """Raised when an immutable upstream object cannot be inspected."""


class CacheMiss(SourceUnavailable):
    """A secure cache path is simply absent, rather than malformed/unsafe."""


class ReconciliationWriteError(RuntimeError):
    """A batch mapping write failed and may have durable recovery material."""

    def __init__(
        self,
        message: str,
        *,
        recovery_paths: Iterable[Path] = (),
        committed: bool = False,
    ) -> None:
        self.recovery_paths = tuple(Path(path) for path in recovery_paths)
        self.committed = committed
        suffix = (
            "; recovery_paths="
            + ", ".join(str(path) for path in self.recovery_paths)
            if self.recovery_paths
            else ""
        )
        super().__init__(message + suffix)


def _cache_repo_key(repo: str) -> str:
    return repo.replace("/", "__")


def _git_blob_oid(content: bytes, algorithm: str) -> str:
    """Return the Git content address for exact local blob bytes."""
    payload = f"blob {len(content)}\0".encode("ascii") + content
    if algorithm == "sha1":
        return hashlib.sha1(payload).hexdigest()
    if algorithm == "sha256":
        return hashlib.sha256(payload).hexdigest()
    raise ValueError(f"unsupported Git object algorithm: {algorithm}")


def _open_directory_chain(
    anchor: Path,
    relative_parts: Iterable[str],
    *,
    create: bool,
) -> int:
    """Open a directory below ``anchor`` without following any symlink."""
    try:
        if create:
            anchor.mkdir(parents=True, exist_ok=True)
        anchor_stat = anchor.lstat()
    except FileNotFoundError as exc:
        raise CacheMiss(f"directory anchor is absent: {anchor}") from exc
    except OSError as exc:
        raise SourceUnavailable(f"cannot inspect directory anchor {anchor}: {exc}") from exc
    if stat.S_ISLNK(anchor_stat.st_mode) or not stat.S_ISDIR(anchor_stat.st_mode):
        raise SourceUnavailable(f"directory anchor is a symlink or not a directory: {anchor}")

    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(anchor, flags)
    except OSError as exc:
        raise SourceUnavailable(f"cannot open directory anchor safely: {anchor}: {exc}") from exc
    current_display = anchor
    try:
        for component in relative_parts:
            if component in {"", ".", ".."} or "/" in component or "\\" in component:
                raise SourceUnavailable(
                    f"unsafe directory component below {anchor}: {component!r}"
                )
            current_display = current_display / component
            if create:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
                except OSError as exc:
                    raise SourceUnavailable(
                        f"cannot create cache directory safely: {current_display}: {exc}"
                    ) from exc
            try:
                next_descriptor = os.open(component, flags, dir_fd=descriptor)
            except OSError as exc:
                try:
                    metadata = os.stat(
                        component,
                        dir_fd=descriptor,
                        follow_symlinks=False,
                    )
                except OSError:
                    metadata = None
                issue = (
                    "symlink"
                    if metadata is not None and stat.S_ISLNK(metadata.st_mode)
                    else "unsafe ancestor"
                )
                if metadata is None and isinstance(exc, FileNotFoundError):
                    raise CacheMiss(
                        f"cache/directory path is absent: {current_display}"
                    ) from exc
                raise SourceUnavailable(
                    f"{issue} in directory chain: {current_display}: {exc}"
                ) from exc
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _read_regular_beneath(anchor: Path, relative: PurePosixPath) -> tuple[bytes, os.stat_result]:
    parent_fd = _open_directory_chain(anchor, relative.parts[:-1], create=False)
    descriptor = -1
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(relative.name, flags, dir_fd=parent_fd)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise SourceUnavailable(
                f"cache/file destination is not a regular file: {anchor / relative}"
            )
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (
            after.st_dev != opened.st_dev
            or after.st_ino != opened.st_ino
            or after.st_size != opened.st_size
        ):
            raise SourceUnavailable(f"file changed while reading: {anchor / relative}")
        return b"".join(chunks), opened
    except FileNotFoundError as exc:
        raise CacheMiss(f"cache/file path is absent: {anchor / relative}") from exc
    except OSError as exc:
        raise SourceUnavailable(
            f"cannot read regular file safely: {anchor / relative}: {exc}"
        ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_fd)


def _atomic_write_bytes(
    path: Path,
    content: bytes,
    *,
    anchor: Path | None = None,
    mode: int = 0o600,
) -> None:
    """Atomically cache bytes without following a hostile destination symlink."""
    if anchor is not None:
        try:
            relative = PurePosixPath(path.relative_to(anchor).as_posix())
        except ValueError as exc:
            raise SourceUnavailable(f"cache path escapes cache root: {path}") from exc
        parent_fd = _open_directory_chain(anchor, relative.parts[:-1], create=True)
        temporary_name = f".{relative.name}.{uuid.uuid4().hex}.tmp"
        descriptor = -1
        try:
            flags = (
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_NOFOLLOW", 0)
            )
            descriptor = os.open(
                temporary_name,
                flags,
                0o600,
                dir_fd=parent_fd,
            )
            view = memoryview(content)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise SourceUnavailable(
                        f"short cache write for {path}"
                    )
                view = view[written:]
            os.fchmod(descriptor, mode)
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = -1
            try:
                destination_stat = os.stat(
                    relative.name,
                    dir_fd=parent_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                destination_stat = None
            if destination_stat is not None and not stat.S_ISREG(
                destination_stat.st_mode
            ):
                raise SourceUnavailable(
                    f"cache destination is not a regular file: {path}"
                )
            os.replace(
                temporary_name,
                relative.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
            os.fsync(parent_fd)
            return
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                os.unlink(temporary_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
            os.close(parent_fd)

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination_stat = path.lstat()
    except FileNotFoundError:
        destination_stat = None
    if destination_stat is not None and not stat.S_ISREG(destination_stat.st_mode):
        raise SourceUnavailable(f"cache destination is not a regular file: {path}")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(content)
            handle.flush()
            os.fchmod(handle.fileno(), mode)
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


class GitHubObjectCache:
    """GitHub recursive-tree/blob reader with deterministic on-disk fixtures."""

    def __init__(
        self,
        cache_dir: Path,
        *,
        offline: bool = False,
        gh_binary: str = "gh",
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.offline = offline
        self.gh_binary = gh_binary
        self._trees: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
        self._online_verified_trees: set[tuple[str, str]] = set()
        self._blobs: dict[tuple[str, str], bytes] = {}

    def tree_cache_path(self, repo: str, commit: str) -> Path:
        return self.cache_dir / "trees" / _cache_repo_key(repo) / f"{commit}.json"

    def blob_cache_path(self, repo: str, object_sha: str) -> Path:
        return self.cache_dir / "blobs" / _cache_repo_key(repo) / f"{object_sha}.bin"

    def blob_is_cached(self, repo: str, object_sha: str) -> bool:
        if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", object_sha):
            return False
        path = self.blob_cache_path(repo, object_sha)
        try:
            relative = PurePosixPath(path.relative_to(self.cache_dir).as_posix())
            _read_regular_beneath(self.cache_dir, relative)
        except (SourceUnavailable, ValueError):
            return False
        return True

    def _gh_json(self, endpoint: str, *, fields: dict[str, str] | None = None) -> Any:
        if self.offline:
            raise SourceUnavailable(f"offline cache miss: {endpoint}")
        command = [self.gh_binary, "api", "--method", "GET", endpoint]
        for key, value in (fields or {}).items():
            command.extend(["-f", f"{key}={value}"])
        try:
            result = subprocess.run(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as exc:
            raise SourceUnavailable(f"cannot run gh for {endpoint}: {exc}") from exc
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", errors="replace").strip()
            raise SourceUnavailable(
                f"GitHub object unavailable for {endpoint}: "
                f"{detail or f'exit {result.returncode}'}"
            )
        try:
            return json.loads(result.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SourceUnavailable(f"invalid GitHub JSON for {endpoint}: {exc}") from exc

    def get_tree(self, repo: str, commit: str) -> dict[str, dict[str, Any]]:
        commit = commit.lower()
        key = (repo, commit)
        if key in self._trees and (
            self.offline or key in self._online_verified_trees
        ):
            return self._trees[key]
        if not COMMIT_RE.fullmatch(commit):
            raise SourceUnavailable(
                f"{repo} has no immutable resolved commit: {commit!r}"
            )

        cache_path = self.tree_cache_path(repo, commit)
        if self.offline:
            try:
                relative_cache_path = PurePosixPath(
                    cache_path.relative_to(self.cache_dir).as_posix()
                )
                cached_bytes, _ = _read_regular_beneath(
                    self.cache_dir,
                    relative_cache_path,
                )
            except CacheMiss as exc:
                raise SourceUnavailable(
                    f"offline tree cache miss: {repo}@{commit}"
                ) from exc
            try:
                payload = json.loads(cached_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise SourceUnavailable(f"invalid tree cache {cache_path}: {exc}") from exc
        else:
            # A mutable on-disk cache is never source authority. Resolve the
            # immutable commit object online, bind it to its root tree, then
            # require the recursive tree response to carry that exact tree OID.
            commit_payload = self._gh_json(
                f"repos/{repo}/git/commits/{commit}",
            )
            commit_sha = (
                commit_payload.get("sha")
                if isinstance(commit_payload, dict)
                else None
            )
            tree_record = (
                commit_payload.get("tree")
                if isinstance(commit_payload, dict)
                else None
            )
            root_tree_sha = (
                tree_record.get("sha")
                if isinstance(tree_record, dict)
                else None
            )
            if (
                not isinstance(commit_sha, str)
                or commit_sha.lower() != commit
                or not isinstance(root_tree_sha, str)
                or not re.fullmatch(
                    r"(?:[0-9a-f]{40}|[0-9a-f]{64})",
                    root_tree_sha,
                )
            ):
                raise SourceUnavailable(
                    f"commit/root-tree binding is invalid for {repo}@{commit}"
                )
            payload = self._gh_json(
                f"repos/{repo}/git/trees/{root_tree_sha.lower()}",
                fields={"recursive": "1"},
            )
            if (
                not isinstance(payload, dict)
                or not isinstance(payload.get("sha"), str)
                or payload["sha"].lower() != root_tree_sha.lower()
            ):
                raise SourceUnavailable(f"invalid tree response for {repo}@{commit}")
            _atomic_write_bytes(
                cache_path,
                (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode(
                    "utf-8"
                ),
                anchor=self.cache_dir,
            )

        if payload.get("truncated") is True:
            raise SourceUnavailable(f"recursive tree is truncated for {repo}@{commit}")
        entries = payload.get("tree")
        if not isinstance(entries, list):
            raise SourceUnavailable(f"tree response has no entries for {repo}@{commit}")

        normalized: dict[str, dict[str, Any]] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                raise SourceUnavailable(
                    f"tree response contains a non-object entry for {repo}@{commit}"
                )
            entry_type = entry.get("type")
            if entry_type != "blob":
                continue
            path = entry.get("path")
            object_sha = entry.get("sha")
            size = entry.get("size")
            git_mode = entry.get("mode")
            if git_mode == "120000":
                # A repository may contain unrelated convenience symlinks.
                # They are never eligible as provenance artifacts, but they
                # must not make every regular blob in the immutable tree
                # unavailable.
                continue
            if git_mode not in VALID_GIT_FILE_MODES:
                raise SourceUnavailable(
                    "tree response contains a non-regular or unknown blob mode "
                    f"for {repo}@{commit}: {entry.get('path')}: {git_mode!r}"
                )
            if not isinstance(path, str) or not safe_relative_path(path):
                raise SourceUnavailable(
                    f"tree response contains an unsafe blob path for {repo}@{commit}"
                )
            if (
                not isinstance(object_sha, str)
                or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", object_sha)
            ):
                raise SourceUnavailable(
                    f"tree response contains an invalid blob object id: {object_sha!r}"
                )
            if (
                isinstance(size, bool) or not isinstance(size, int) or size < 0
            ):
                raise SourceUnavailable(
                    f"tree response contains a missing or invalid blob size for {path}"
                )
            if path in normalized:
                raise SourceUnavailable(
                    f"tree response contains duplicate blob path: {path}"
                )
            normalized[path] = {
                **entry,
                "sha": object_sha.lower(),
                "size": size,
                "mode": git_mode,
            }
        self._trees[key] = normalized
        if not self.offline:
            self._online_verified_trees.add(key)
        return normalized

    def get_blob(
        self,
        repo: str,
        object_sha: str,
        *,
        expected_size: int | None = None,
    ) -> bytes:
        if not isinstance(object_sha, str) or not re.fullmatch(
            r"(?:[0-9a-f]{40}|[0-9a-f]{64})",
            object_sha,
        ):
            raise SourceUnavailable(
                f"invalid Git blob object id for {repo}: {object_sha!r}"
            )
        if expected_size is not None and (
            isinstance(expected_size, bool)
            or not isinstance(expected_size, int)
            or expected_size < 0
        ):
            raise SourceUnavailable(
                f"invalid expected Git blob size for {repo}:{object_sha}"
            )
        key = (repo, object_sha)
        if key in self._blobs:
            content = self._blobs[key]
            self._validate_blob(
                repo,
                object_sha,
                content,
                expected_size=expected_size,
            )
            return content
        cache_path = self.blob_cache_path(repo, object_sha)
        try:
            relative_cache_path = PurePosixPath(
                cache_path.relative_to(self.cache_dir).as_posix()
            )
            content, _ = _read_regular_beneath(
                self.cache_dir,
                relative_cache_path,
            )
            cache_hit = True
        except CacheMiss:
            cache_hit = False
        if cache_hit:
            self._validate_blob(
                repo,
                object_sha,
                content,
                expected_size=expected_size,
            )
        else:
            payload = self._gh_json(f"repos/{repo}/git/blobs/{object_sha}")
            if not isinstance(payload, dict):
                raise SourceUnavailable(f"invalid blob response for {repo}:{object_sha}")
            encoded = payload.get("content")
            encoding = payload.get("encoding")
            response_sha = payload.get("sha")
            response_size = payload.get("size")
            if (
                not isinstance(encoded, str)
                or encoding != "base64"
                or response_sha != object_sha
                or isinstance(response_size, bool)
                or not isinstance(response_size, int)
                or response_size < 0
            ):
                raise SourceUnavailable(
                    f"unsupported or inconsistent blob response for "
                    f"{repo}:{object_sha}"
                )
            try:
                compact = re.sub(r"[ \t\r\n]", "", encoded)
                content = base64.b64decode(compact, validate=True)
            except (ValueError, TypeError, binascii.Error) as exc:
                raise SourceUnavailable(
                    f"invalid base64 blob for {repo}:{object_sha}"
                ) from exc
            if len(content) != response_size:
                raise SourceUnavailable(
                    f"blob response size mismatch for {repo}:{object_sha}: "
                    f"declared {response_size}, decoded {len(content)}"
                )
            self._validate_blob(
                repo,
                object_sha,
                content,
                expected_size=expected_size,
            )
            _atomic_write_bytes(cache_path, content, anchor=self.cache_dir)
        self._blobs[key] = content
        return content

    @staticmethod
    def _validate_blob(
        repo: str,
        object_sha: str,
        content: bytes,
        *,
        expected_size: int | None,
    ) -> None:
        algorithm = "sha1" if len(object_sha) == 40 else "sha256"
        actual_oid = _git_blob_oid(content, algorithm)
        if actual_oid != object_sha:
            raise SourceUnavailable(
                f"Git blob object id mismatch for {repo}:{object_sha}; "
                f"computed {actual_oid}"
            )
        if expected_size is not None and len(content) != expected_size:
            raise SourceUnavailable(
                f"Git blob size mismatch for {repo}:{object_sha}; "
                f"expected {expected_size}, got {len(content)}"
            )


def _is_active_external_canonical(entry: dict[str, Any]) -> bool:
    repo_skill = entry.get("repo_skill")
    slug = entry.get("normalized_slug")
    if (
        entry.get("status") not in ACTIVE_STATUSES
        or entry.get("kind") not in EXTERNAL_KINDS
        or not isinstance(repo_skill, str)
        or not safe_relative_path(repo_skill)
        or not isinstance(slug, str)
        or not slug
    ):
        return False
    path = PurePosixPath(repo_skill)
    return (
        len(path.parts) == 4
        and path.parts[0] == "skills"
        and path.parts[2] == slug
        and path.parts[3] == "SKILL.md"
    )


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return str(path)


def _git_mode_from_stat(metadata: os.stat_result) -> str:
    """Project one regular worktree inode into Git's portable file modes."""
    if not stat.S_ISREG(metadata.st_mode):
        raise OSError("file mode cannot be projected from a non-regular inode")
    return "100755" if stat.S_IMODE(metadata.st_mode) & 0o111 else "100644"


def _regular_file_snapshot(path: Path) -> tuple[bytes, dict[str, int | str]]:
    """Bind bytes and portable mode to one stable, nofollow descriptor."""
    before = path.lstat()
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise OSError(f"not a regular non-symlink file: {path}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_dev != before.st_dev
            or opened.st_ino != before.st_ino
        ):
            raise OSError(f"file changed while opening: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        content = b"".join(chunks)
        after = os.fstat(descriptor)
        named = path.lstat()
        if (
            after.st_dev != opened.st_dev
            or after.st_ino != opened.st_ino
            or after.st_size != opened.st_size
            or after.st_mtime_ns != opened.st_mtime_ns
            or after.st_ctime_ns != opened.st_ctime_ns
            or after.st_mode != opened.st_mode
            or named.st_dev != opened.st_dev
            or named.st_ino != opened.st_ino
            or stat.S_ISLNK(named.st_mode)
        ):
            raise OSError(f"file changed while reading: {path}")
        return content, {
            "dev": opened.st_dev,
            "ino": opened.st_ino,
            "size": len(content),
            "mtime_ns": opened.st_mtime_ns,
            "ctime_ns": opened.st_ctime_ns,
            "sha256": hashlib.sha256(content).hexdigest(),
            "mode": _git_mode_from_stat(opened),
        }
    finally:
        os.close(descriptor)


def _read_regular_file(path: Path) -> bytes:
    return _regular_file_snapshot(path)[0]


def _sha256_regular_file(path: Path) -> str:
    return str(_regular_file_snapshot(path)[1]["sha256"])


def _scan_issue(
    *,
    path: Path,
    repo_root: Path,
    issue: str,
    operation: str,
    detail: str,
) -> dict[str, str]:
    return {
        "path": _display_path(path, repo_root),
        "issue": issue,
        "operation": operation,
        "detail": detail,
    }


def _iter_regular_skill_files(
    repo_root: Path,
    repo_skill: str,
) -> tuple[list[str], list[dict[str, str]]]:
    """Walk a skill directory without following an ancestor or child symlink."""
    paths, issues, _, _ = _scan_regular_skill_files(
        repo_root,
        repo_skill,
        capture_bytes=False,
    )
    return paths, issues


def _scan_regular_skill_files(
    repo_root: Path,
    repo_skill: str,
    *,
    capture_bytes: bool,
) -> tuple[
    list[str],
    list[dict[str, str]],
    dict[str, dict[str, int | str]],
    dict[str, bytes],
]:
    """Securely scan and optionally capture every canonical skill file.

    Directory file descriptors bind the walk to the repository root.  A
    symlink in ``skills/<category>/<slug>`` is therefore reported rather than
    traversed, even when the final skill directory itself looks ordinary
    through normal path resolution.
    """
    skill_root = PurePosixPath(repo_skill).parent
    root = repo_root.joinpath(*skill_root.parts)
    issues: list[dict[str, str]] = []
    try:
        root_fd = _open_directory_chain(repo_root, skill_root.parts, create=False)
    except SourceUnavailable as exc:
        issue = "symlink" if "symlink" in str(exc).lower() else "io_error"
        issues.append(
            _scan_issue(
                path=root,
                repo_root=repo_root,
                issue=issue,
                operation="open_skill_root",
                detail=str(exc),
            )
        )
        return [], issues, {}, {}

    paths: list[str] = []
    snapshots: dict[str, dict[str, int | str]] = {}
    contents: dict[str, bytes] = {}

    def walk(directory_fd: int, relative_parts: tuple[str, ...]) -> None:
        try:
            with os.scandir(directory_fd) as iterator:
                entries = sorted(list(iterator), key=lambda item: item.name)
        except OSError as exc:
            directory = repo_root.joinpath(*relative_parts)
            issues.append(
                _scan_issue(
                    path=directory,
                    repo_root=repo_root,
                    issue="io_error",
                    operation="scandir",
                    detail=str(exc),
                )
            )
            return
        for item in entries:
            item_path = repo_root.joinpath(*relative_parts, item.name)
            try:
                metadata = os.stat(
                    item.name,
                    dir_fd=directory_fd,
                    follow_symlinks=False,
                )
                if stat.S_ISLNK(metadata.st_mode):
                    issues.append(
                        _scan_issue(
                            path=item_path,
                            repo_root=repo_root,
                            issue="symlink",
                            operation="walk",
                            detail="symlink was not followed",
                        )
                    )
                    continue
                if (
                    item.name in IGNORED_DIRECTORY_NAMES
                    or item.name in IGNORED_FILE_NAMES
                ):
                    continue
                if stat.S_ISDIR(metadata.st_mode):
                    flags = (
                        os.O_RDONLY
                        | getattr(os, "O_DIRECTORY", 0)
                        | getattr(os, "O_NOFOLLOW", 0)
                    )
                    child_fd = os.open(item.name, flags, dir_fd=directory_fd)
                    try:
                        opened = os.fstat(child_fd)
                        if (
                            opened.st_dev != metadata.st_dev
                            or opened.st_ino != metadata.st_ino
                        ):
                            raise OSError(
                                f"directory changed while opening: {item_path}"
                            )
                        walk(child_fd, (*relative_parts, item.name))
                    finally:
                        os.close(child_fd)
                elif stat.S_ISREG(metadata.st_mode):
                    if item_path.suffix in IGNORED_FILE_SUFFIXES:
                        continue
                    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                    descriptor = os.open(
                        item.name,
                        flags,
                        dir_fd=directory_fd,
                    )
                    try:
                        opened = os.fstat(descriptor)
                        if (
                            not stat.S_ISREG(opened.st_mode)
                            or opened.st_dev != metadata.st_dev
                            or opened.st_ino != metadata.st_ino
                        ):
                            raise OSError(f"file changed while opening: {item_path}")
                        chunks: list[bytes] = []
                        while True:
                            chunk = os.read(descriptor, 1024 * 1024)
                            if not chunk:
                                break
                            chunks.append(chunk)
                        after = os.fstat(descriptor)
                        if (
                            after.st_dev != opened.st_dev
                            or after.st_ino != opened.st_ino
                            or after.st_size != opened.st_size
                            or after.st_mtime_ns != opened.st_mtime_ns
                            or after.st_ctime_ns != opened.st_ctime_ns
                            or after.st_mode != opened.st_mode
                        ):
                            raise OSError(f"file changed while reading: {item_path}")
                        data = b"".join(chunks)
                    finally:
                        os.close(descriptor)
                    target = PurePosixPath(*relative_parts, item.name).as_posix()
                    digest = hashlib.sha256(data).hexdigest()
                    paths.append(target)
                    snapshots[target] = {
                        "dev": opened.st_dev,
                        "ino": opened.st_ino,
                        "size": len(data),
                        "mtime_ns": opened.st_mtime_ns,
                        "ctime_ns": opened.st_ctime_ns,
                        "sha256": digest,
                        "mode": _git_mode_from_stat(opened),
                    }
                    if capture_bytes:
                        contents[target] = data
                else:
                    issues.append(
                        _scan_issue(
                            path=item_path,
                            repo_root=repo_root,
                            issue="unsupported_file_type",
                            operation="walk",
                            detail="non-directory, non-regular entry was not scanned",
                        )
                    )
            except OSError as exc:
                issues.append(
                    _scan_issue(
                        path=item_path,
                        repo_root=repo_root,
                        issue="io_error",
                        operation="inspect_directory_entry",
                        detail=str(exc),
                    )
                )
                continue

    try:
        walk(root_fd, tuple(skill_root.parts))
    finally:
        os.close(root_fd)
    return sorted(paths), issues, snapshots, contents


def _artifact_covers(artifact: object, target: str) -> bool:
    if (
        not isinstance(artifact, dict)
        or not safe_relative_path(artifact.get("target"))
        or not safe_relative_path(target)
    ):
        return False
    declared = PurePosixPath(str(artifact["target"]))
    requested = PurePosixPath(target)
    if artifact.get("type", "file") == "directory":
        return requested == declared or declared in requested.parents
    return requested == declared


def _artifact_owners(
    entry: dict[str, Any],
    target: str,
) -> list[tuple[int, dict[str, Any], dict[str, Any]]]:
    owners: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    for origin_index, origin in enumerate(entry.get("origins", [])):
        if not isinstance(origin, dict):
            continue
        matches = [
            artifact
            for artifact in origin.get("artifacts", [])
            if isinstance(artifact, dict) and _artifact_covers(artifact, target)
        ]
        if not matches:
            continue
        # Ownership belongs to an origin, not to each overlapping declaration
        # inside that origin.  Retain the most specific declaration only so a
        # directory plus an explicit file mapping does not become a false
        # cross-origin conflict.
        artifact = max(
            matches,
            key=lambda candidate: (
                candidate.get("type", "file") != "directory",
                len(PurePosixPath(str(candidate["target"])).parts),
            ),
        )
        owners.append((origin_index, origin, artifact))
    return owners


def _source_candidates(
    origin: dict[str, Any],
    target: str,
    skill_root: PurePosixPath,
) -> list[str]:
    """Infer only path-preserving sources from declared transformation roots."""
    requested = PurePosixPath(target)
    proposals: list[tuple[int, str]] = []
    for artifact in origin.get("artifacts", []):
        if not isinstance(artifact, dict):
            continue
        source = artifact.get("source")
        declared_target = artifact.get("target")
        if not safe_relative_path(source) or not safe_relative_path(declared_target):
            continue
        source_path = PurePosixPath(str(source))
        target_path = PurePosixPath(str(declared_target))
        if artifact.get("type", "file") == "directory":
            if requested == target_path or target_path in requested.parents:
                relative = requested.relative_to(target_path)
                proposals.append(
                    (len(target_path.parts), (source_path / relative).as_posix())
                )
            continue

        # A transformed standalone entrypoint (for example
        # ``graphify/skill-codex.md`` -> ``SKILL.md``) does not establish that
        # its entire upstream package directory is part of the skill artifact
        # set.  Only a canonical upstream SKILL.md establishes the implicit
        # sibling root; explicit non-entrypoint sidecars still establish their
        # own path-preserving sibling roots.
        if (
            target_path.name == "SKILL.md"
            and source_path.name.lower() != "skill.md"
        ):
            continue
        local_base = target_path.parent
        if requested == local_base or local_base not in requested.parents:
            continue
        relative = requested.relative_to(local_base)
        proposals.append(
            (len(local_base.parts), (source_path.parent / relative).as_posix())
        )

    if not proposals:
        origin_path = origin.get("path")
        if safe_relative_path(origin_path) and (
            requested == skill_root or skill_root in requested.parents
        ):
            source_path = PurePosixPath(str(origin_path))
            if source_path.name.lower().endswith((".md", ".markdown")):
                if source_path.name.lower() != "skill.md":
                    return []
                source_path = source_path.parent
            relative = requested.relative_to(skill_root)
            proposals.append(
                (len(skill_root.parts), (source_path / relative).as_posix())
            )

    result: list[str] = []
    for _, proposal in sorted(proposals, key=lambda value: (-value[0], value[1])):
        if safe_relative_path(proposal) and proposal not in result:
            result.append(proposal)
    return result


def _classify_unowned_file(
    *,
    entry: dict[str, Any],
    target: str,
    local_bytes: bytes,
    local_mode: str,
    cache: GitHubObjectCache,
    origin_indexes: set[int] | None = None,
) -> dict[str, Any]:
    if local_mode not in VALID_GIT_FILE_MODES:
        raise ValueError(f"invalid local Git file mode: {local_mode!r}")
    repo_skill = PurePosixPath(str(entry["repo_skill"]))
    skill_root = repo_skill.parent
    checked_sources: list[dict[str, Any]] = []
    unavailable: list[str] = []

    for origin_index, origin in enumerate(entry.get("origins", [])):
        if origin_indexes is not None and origin_index not in origin_indexes:
            continue
        if not isinstance(origin, dict) or is_local_repo(origin.get("repo")):
            continue
        repo = origin.get("repo")
        tracking = origin.get("tracking")
        commit = (
            tracking.get("resolved_commit")
            if isinstance(tracking, dict)
            else None
        )
        if not isinstance(repo, str) or not isinstance(commit, str):
            unavailable.append(
                f"origin[{origin_index}] lacks repo or resolved_commit"
            )
            continue
        try:
            tree = cache.get_tree(repo, commit)
        except SourceUnavailable as exc:
            unavailable.append(str(exc))
            continue

        candidates = _source_candidates(origin, target, skill_root)
        if not candidates:
            checked_sources.append(
                {
                    "origin_index": origin_index,
                    "repo": repo,
                    "resolved_commit": commit,
                    "source": None,
                    "result": "no_path_preserving_candidate",
                }
            )
            continue
        for source in candidates:
            tree_entry = tree.get(source)
            if tree_entry is None:
                checked_sources.append(
                    {
                        "origin_index": origin_index,
                        "repo": repo,
                        "resolved_commit": commit,
                        "source": source,
                        "result": "source_missing",
                    }
                )
                continue
            object_sha = str(tree_entry["sha"]).lower()
            declared_size = tree_entry.get("size")
            upstream_mode = tree_entry.get("mode")
            if upstream_mode != local_mode:
                checked_sources.append(
                    {
                        "origin_index": origin_index,
                        "repo": repo,
                        "resolved_commit": commit,
                        "source": source,
                        "result": "mode_mismatch",
                        "local_mode": local_mode,
                        "upstream_mode": upstream_mode,
                    }
                )
                continue
            algorithm = (
                "sha1"
                if len(object_sha) == 40
                else "sha256"
                if len(object_sha) == 64
                else None
            )
            if (
                algorithm is not None
                and _git_blob_oid(local_bytes, algorithm) == object_sha
            ):
                if declared_size != len(local_bytes):
                    unavailable.append(
                        f"Git tree blob size mismatch for {repo}:{source}: "
                        f"declared {declared_size}, local {len(local_bytes)}"
                    )
                    checked_sources.append(
                        {
                            "origin_index": origin_index,
                            "repo": repo,
                            "resolved_commit": commit,
                            "source": source,
                            "result": "size_mismatch",
                        }
                    )
                    continue
                if cache.offline:
                    unavailable.append(
                        "offline tree cache cannot authorize new external "
                        f"ownership for {repo}@{commit}:{source}"
                    )
                    checked_sources.append(
                        {
                            "origin_index": origin_index,
                            "repo": repo,
                            "resolved_commit": commit,
                            "source": source,
                            "result": "offline_authority_forbidden",
                        }
                    )
                    continue
                return {
                    "target": target,
                    "sha256": hashlib.sha256(local_bytes).hexdigest(),
                    "mode": local_mode,
                    "classification": "external_exact",
                    "origin_index": origin_index,
                    "repo": repo,
                    "resolved_commit": commit,
                    "source": source,
                    "reason": (
                        "path-preserving Git blob content address matches "
                        "exact local bytes"
                    ),
                    "checked_sources": checked_sources,
                }
            # A valid Git object id that differs proves the bytes differ.  A
            # cached blob is still read (and offline cache fixtures therefore
            # exercise byte comparison), while live scans avoid one API call
            # per known mismatch.
            if algorithm is not None and not (
                cache.offline or cache.blob_is_cached(repo, object_sha)
            ):
                checked_sources.append(
                    {
                        "origin_index": origin_index,
                        "repo": repo,
                        "resolved_commit": commit,
                        "source": source,
                        "result": "content_address_mismatch",
                    }
                )
                continue
            try:
                upstream_bytes = cache.get_blob(
                    repo,
                    object_sha,
                    expected_size=declared_size,
                )
            except SourceUnavailable as exc:
                unavailable.append(str(exc))
                checked_sources.append(
                    {
                        "origin_index": origin_index,
                        "repo": repo,
                        "resolved_commit": commit,
                        "source": source,
                        "result": "blob_unavailable",
                    }
                )
                continue
            if upstream_bytes == local_bytes:
                if cache.offline:
                    unavailable.append(
                        "offline tree/blob cache cannot authorize new external "
                        f"ownership for {repo}@{commit}:{source}"
                    )
                    checked_sources.append(
                        {
                            "origin_index": origin_index,
                            "repo": repo,
                            "resolved_commit": commit,
                            "source": source,
                            "result": "offline_authority_forbidden",
                        }
                    )
                    continue
                return {
                    "target": target,
                    "sha256": hashlib.sha256(local_bytes).hexdigest(),
                    "mode": local_mode,
                    "classification": "external_exact",
                    "origin_index": origin_index,
                    "repo": repo,
                    "resolved_commit": commit,
                    "source": source,
                    "reason": "path-preserving upstream bytes match",
                    "checked_sources": checked_sources,
                }
            checked_sources.append(
                {
                    "origin_index": origin_index,
                    "repo": repo,
                    "resolved_commit": commit,
                    "source": source,
                    "result": "content_mismatch",
                }
            )

    result = {
        "target": target,
        "sha256": hashlib.sha256(local_bytes).hexdigest(),
        "mode": local_mode,
        "checked_sources": checked_sources,
    }
    if unavailable:
        result.update(
            {
                "classification": "unavailable",
                "source": None,
                "reason": "; ".join(sorted(set(unavailable))),
            }
        )
    else:
        result.update(
            {
                "classification": "local_overlay",
                "source": target,
                "repo": LOCAL_OVERLAY_REPO,
                "reason": (
                    "no path-preserving source at resolved external commit "
                    "matches local bytes"
                ),
            }
        )
    return result


def _managed_by_path(entry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for managed in entry.get("managed_files", []):
        if isinstance(managed, dict) and safe_relative_path(managed.get("path")):
            result[str(managed["path"])] = managed
    return result


def inspect_entry(
    entry: dict[str, Any],
    *,
    repo_root: Path,
    cache: GitHubObjectCache,
) -> dict[str, Any]:
    slug = str(entry["normalized_slug"])
    repo_skill = str(entry["repo_skill"])
    actual, scan_errors, filesystem_checkpoint, local_contents = (
        _scan_regular_skill_files(
            repo_root,
            repo_skill,
            capture_bytes=True,
        )
    )
    actual_set = set(actual)
    managed = _managed_by_path(entry)
    managed_set = set(managed)
    unowned: list[dict[str, Any]] = []
    ownership_conflicts: list[dict[str, Any]] = []

    for target in actual:
        owners = _artifact_owners(entry, target)
        if len(owners) > 1:
            ownership_conflicts.append(
                {
                    "target": target,
                    "owners": [
                        {
                            "origin_index": index,
                            "repo": origin.get("repo"),
                            "source": artifact.get("source"),
                        }
                        for index, origin, artifact in owners
                    ],
                }
            )
        # An artifact declaration is not a deletion/pruning checkpoint.
        # Missing managed state must still be re-verified against exact source
        # bytes before the file may become managed.
        if owners and target in managed_set:
            continue
        local_bytes = local_contents.get(target)
        local_snapshot = filesystem_checkpoint.get(target)
        local_mode = (
            local_snapshot.get("mode")
            if isinstance(local_snapshot, dict)
            else None
        )
        if local_bytes is None or local_mode not in VALID_GIT_FILE_MODES:
            unowned.append(
                {
                    "target": target,
                    "sha256": None,
                    "mode": local_mode,
                    "classification": "unavailable",
                    "source": None,
                    "reason": (
                        "cannot bind local bytes and regular Git mode from "
                        "secure scan checkpoint"
                    ),
                }
            )
            continue
        declared_owner = None
        if len(owners) == 1:
            owner_index, owner_origin, owner_artifact = owners[0]
            declared_owner = {
                "origin_index": owner_index,
                "repo": owner_origin.get("repo"),
                "source": owner_artifact.get("source"),
                "local": is_local_repo(owner_origin.get("repo")),
            }
            if declared_owner["local"]:
                classified = {
                    "target": target,
                    "sha256": hashlib.sha256(local_bytes).hexdigest(),
                    "mode": local_mode,
                    "classification": "local_overlay",
                    "origin_index": owner_index,
                    "repo": owner_origin.get("repo"),
                    "source": target,
                    "reason": (
                        "declared local artifact lacks a managed checkpoint"
                    ),
                    "checked_sources": [],
                }
            else:
                classified = _classify_unowned_file(
                    entry=entry,
                    target=target,
                    local_bytes=local_bytes,
                    local_mode=local_mode,
                    cache=cache,
                    origin_indexes={owner_index},
                )
        else:
            classified = _classify_unowned_file(
                entry=entry,
                target=target,
                local_bytes=local_bytes,
                local_mode=local_mode,
                cache=cache,
            )
        if declared_owner is not None:
            classified["declared_owner"] = declared_owner
        unowned.append(classified)

    stale_artifact_targets: list[str] = []
    for origin in entry.get("origins", []):
        if not isinstance(origin, dict):
            continue
        for artifact in origin.get("artifacts", []):
            if (
                isinstance(artifact, dict)
                and artifact.get("type", "file") == "file"
                and safe_relative_path(artifact.get("target"))
                and artifact["target"] not in actual_set
            ):
                stale_artifact_targets.append(str(artifact["target"]))

    hash_mismatches: list[str] = []
    mode_mismatches: list[str] = []
    for target in sorted(actual_set & managed_set):
        try:
            _current_bytes, current_snapshot = _regular_file_snapshot(
                repo_root / target
            )
        except OSError as exc:
            scan_errors.append(
                _scan_issue(
                    path=repo_root / target,
                    repo_root=repo_root,
                    issue="io_error",
                    operation="hash_managed_file",
                    detail=str(exc),
                )
            )
            continue
        checkpoint = filesystem_checkpoint.get(target, {})
        if any(
            current_snapshot.get(field) != checkpoint.get(field)
            for field in (
                "dev",
                "ino",
                "size",
                "mtime_ns",
                "ctime_ns",
                "sha256",
                "mode",
            )
        ):
            scan_errors.append(
                _scan_issue(
                    path=repo_root / target,
                    repo_root=repo_root,
                    issue="concurrent_modification",
                    operation="hash_managed_file",
                    detail="managed file changed after secure scan",
                )
            )
            continue
        if managed[target].get("sha256") != current_snapshot["sha256"]:
            hash_mismatches.append(target)
        if managed[target].get("mode") != current_snapshot["mode"]:
            mode_mismatches.append(target)

    return {
        "slug": slug,
        "repo_skill": repo_skill,
        "kind": entry.get("kind"),
        "actual_files": actual,
        "missing_managed": sorted(actual_set - managed_set),
        "stale_managed": sorted(managed_set - actual_set),
        "stale_artifact_targets": sorted(set(stale_artifact_targets)),
        "hash_mismatches": hash_mismatches,
        "mode_mismatches": mode_mismatches,
        "scan_errors": scan_errors,
        "ownership_conflicts": ownership_conflicts,
        "unowned": unowned,
        "filesystem_checkpoint": filesystem_checkpoint,
    }


def _local_overlay_origin(
    entry: dict[str, Any],
    artifacts: list[dict[str, str]],
    *,
    today: str,
) -> dict[str, Any]:
    repo_skill = PurePosixPath(str(entry["repo_skill"]))
    return {
        "repo": LOCAL_OVERLAY_REPO,
        "path": repo_skill.parent.as_posix(),
        "license": None,
        "sync_mode": "local-only",
        "artifacts": artifacts,
        "tracking": {
            "channel": "local",
            "ref": "local",
            "resolved_commit": None,
            "path_commit": None,
            "content_sha256": None,
            "last_checked_at": today,
            "last_synced_at": today,
        },
    }


def apply_entry_reconciliation(
    entry: dict[str, Any],
    inspection: dict[str, Any],
    *,
    repo_root: Path,
    today: str,
) -> tuple[dict[str, Any], bool, str | None]:
    """Apply only classifications with proven owners to a copied entry."""
    updated = deepcopy(entry)
    unavailable = [
        item
        for item in inspection["unowned"]
        if item["classification"] == "unavailable"
    ]
    conflicts = inspection["ownership_conflicts"]
    hash_mismatches = inspection.get("hash_mismatches", [])
    mode_mismatches = inspection.get("mode_mismatches", [])
    stale_managed = inspection.get("stale_managed", [])
    stale_artifact_targets = inspection.get("stale_artifact_targets", [])
    scan_errors = inspection.get("scan_errors", [])
    declared_owner_mismatches = [
        item
        for item in inspection["unowned"]
        if item["classification"] == "local_overlay"
        and isinstance(item.get("declared_owner"), dict)
        and not item["declared_owner"].get("local")
    ]
    if (
        unavailable
        or conflicts
        or hash_mismatches
        or mode_mismatches
        or stale_managed
        or stale_artifact_targets
        or scan_errors
        or declared_owner_mismatches
    ):
        reasons = []
        if unavailable:
            reasons.append(f"{len(unavailable)} unavailable source(s)")
        if conflicts:
            reasons.append(f"{len(conflicts)} ownership conflict(s)")
        if hash_mismatches:
            reasons.append(f"{len(hash_mismatches)} managed hash mismatch(es)")
        if mode_mismatches:
            reasons.append(f"{len(mode_mismatches)} managed mode mismatch(es)")
        if stale_managed:
            reasons.append(f"{len(stale_managed)} stale managed file(s)")
        if stale_artifact_targets:
            reasons.append(
                f"{len(stale_artifact_targets)} stale artifact target(s)"
            )
        if scan_errors:
            reasons.append(f"{len(scan_errors)} scan/read error(s)")
        if declared_owner_mismatches:
            reasons.append(
                f"{len(declared_owner_mismatches)} declared owner mismatch(es)"
            )
        return updated, False, ", ".join(reasons)

    exact = [
        item
        for item in inspection["unowned"]
        if item["classification"] == "external_exact"
    ]
    overlays = [
        item
        for item in inspection["unowned"]
        if item["classification"] == "local_overlay"
    ]

    origins = updated.get("origins")
    if not isinstance(origins, list):
        return updated, False, "origins is not an array"
    for proposal in exact:
        origin_index = proposal.get("origin_index")
        if not isinstance(origin_index, int) or not (0 <= origin_index < len(origins)):
            return updated, False, "external proposal has invalid origin index"
        origin = origins[origin_index]
        if not isinstance(origin, dict):
            return updated, False, "external proposal origin is invalid"
        artifacts = origin.setdefault("artifacts", [])
        artifact = {
            "source": proposal["source"],
            "target": proposal["target"],
            "type": "file",
        }
        if not any(
            _artifact_covers(existing, proposal["target"])
            for existing in artifacts
        ):
            artifacts.append(artifact)

    if overlays:
        local_origin = next(
            (
                origin
                for origin in origins
                if isinstance(origin, dict)
                and origin.get("repo") == LOCAL_OVERLAY_REPO
            ),
            None,
        )
        overlay_artifacts = [
            {
                "source": item["target"],
                "target": item["target"],
                "type": "file",
            }
            for item in overlays
        ]
        if local_origin is None:
            local_origin = _local_overlay_origin(
                updated,
                overlay_artifacts,
                today=today,
            )
            origins.append(local_origin)
        else:
            local_origin["license"] = None
            local_origin["sync_mode"] = "local-only"
            existing_artifacts = local_origin.setdefault("artifacts", [])
            for artifact in overlay_artifacts:
                if not any(
                    _artifact_covers(existing, artifact["target"])
                    for existing in existing_artifacts
                ):
                    existing_artifacts.append(artifact)
        if updated.get("kind") != "snapshot":
            updated["kind"] = "overlay"
            updated["sync_mode"] = "monitor"
            upstream = updated.get("upstream")
            if isinstance(upstream, dict):
                upstream["sync_mode"] = "monitor"
            for origin in origins:
                if isinstance(origin, dict) and not is_local_repo(origin.get("repo")):
                    origin["sync_mode"] = "monitor"

    for origin in origins:
        if isinstance(origin, dict) and isinstance(origin.get("artifacts"), list):
            origin["artifacts"] = sorted(
                origin["artifacts"],
                key=lambda artifact: (
                    str(artifact.get("target")),
                    str(artifact.get("source")),
                    str(artifact.get("type", "file")),
                ),
            )

    owner = str(updated["normalized_slug"])
    filesystem_checkpoint = inspection.get("filesystem_checkpoint")
    if not isinstance(filesystem_checkpoint, dict):
        return deepcopy(entry), False, "filesystem checkpoint is missing"
    managed_files: list[dict[str, str]] = []
    for target in inspection["actual_files"]:
        snapshot = filesystem_checkpoint.get(target)
        digest = snapshot.get("sha256") if isinstance(snapshot, dict) else None
        mode = snapshot.get("mode") if isinstance(snapshot, dict) else None
        if not isinstance(digest, str) or mode not in VALID_GIT_FILE_MODES:
            return (
                deepcopy(entry),
                False,
                f"filesystem checkpoint is incomplete for {target}",
            )
        managed_files.append(
            {
                "path": target,
                "sha256": digest,
                "owner": owner,
                "mode": mode,
            }
        )
    updated["managed_files"] = managed_files
    return updated, updated != entry, None


def _verify_inspection_checkpoint(
    entry: dict[str, Any],
    inspection: dict[str, Any],
    *,
    repo_root: Path,
) -> str | None:
    """Bind a classification to the same full file set immediately pre-write."""
    actual, issues, current, _ = _scan_regular_skill_files(
        repo_root,
        str(entry["repo_skill"]),
        capture_bytes=False,
    )
    if issues:
        return f"{len(issues)} scan/read error(s) during write preflight"
    expected_actual = inspection.get("actual_files")
    if actual != expected_actual:
        return "canonical skill file set changed after classification"
    expected = inspection.get("filesystem_checkpoint")
    if not isinstance(expected, dict):
        return "filesystem checkpoint is missing"
    for target in actual:
        before = expected.get(target)
        after = current.get(target)
        if not isinstance(before, dict) or not isinstance(after, dict):
            return f"filesystem checkpoint is incomplete for {target}"
        for field in (
            "dev",
            "ino",
            "size",
            "mtime_ns",
            "ctime_ns",
            "sha256",
            "mode",
        ):
            if before.get(field) != after.get(field):
                return (
                    f"canonical skill changed after classification: "
                    f"{target} ({field})"
                )
    return None


def _default_cache_dir() -> Path:
    root = os.environ.get("XDG_CACHE_HOME")
    if root:
        return Path(root) / "high-value-skills" / "artifact-inventory"
    return Path.home() / ".cache" / "high-value-skills" / "artifact-inventory"


def _mapping_snapshot(mapping: Path, repo_root: Path) -> dict[str, Any]:
    try:
        relative = PurePosixPath(mapping.relative_to(repo_root).as_posix())
    except ValueError as exc:
        raise ReconciliationWriteError(
            f"mapping escapes repository root: {mapping}"
        ) from exc
    if not safe_relative_path(relative.as_posix()):
        raise ReconciliationWriteError(f"mapping path is unsafe: {mapping}")
    try:
        content, metadata = _read_regular_beneath(repo_root, relative)
    except SourceUnavailable as exc:
        raise ReconciliationWriteError(
            f"cannot read mapping safely: {mapping}: {exc}"
        ) from exc
    return {
        "bytes": content,
        "dev": metadata.st_dev,
        "ino": metadata.st_ino,
        "size": metadata.st_size,
        "mode": stat.S_IMODE(metadata.st_mode),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _mapping_matches_snapshot(
    mapping: Path,
    repo_root: Path,
    snapshot: dict[str, Any],
) -> bool:
    try:
        current = _mapping_snapshot(mapping, repo_root)
    except ReconciliationWriteError:
        return False
    return all(
        current.get(field) == snapshot.get(field)
        for field in ("dev", "ino", "size", "mode", "sha256")
    )


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _mapping_snapshot_at(
    parent_fd: int,
    leaf: str,
    *,
    display_path: Path,
) -> dict[str, Any]:
    descriptor = -1
    try:
        metadata = os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ReconciliationWriteError(
                f"mapping target is not a regular file: {display_path}"
            )
        descriptor = os.open(
            leaf,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
        opened = os.fstat(descriptor)
        if (
            opened.st_dev != metadata.st_dev
            or opened.st_ino != metadata.st_ino
            or not stat.S_ISREG(opened.st_mode)
        ):
            raise ReconciliationWriteError(
                f"mapping changed while opening: {display_path}"
            )
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        content = b"".join(chunks)
        completed = os.fstat(descriptor)
        named = os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
        if (
            completed.st_dev != opened.st_dev
            or completed.st_ino != opened.st_ino
            or completed.st_size != opened.st_size
            or completed.st_mtime_ns != opened.st_mtime_ns
            or named.st_dev != opened.st_dev
            or named.st_ino != opened.st_ino
        ):
            raise ReconciliationWriteError(
                f"mapping changed while reading: {display_path}"
            )
        return {
            "bytes": content,
            "dev": opened.st_dev,
            "ino": opened.st_ino,
            "size": opened.st_size,
            "mode": stat.S_IMODE(opened.st_mode),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    except OSError as exc:
        raise ReconciliationWriteError(
            f"cannot inspect mapping safely: {display_path}: {exc}"
        ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _assert_active_mapping_parent(
    repo_root: Path,
    relative: PurePosixPath,
    expected: tuple[int, int],
) -> None:
    descriptor = _open_directory_chain(
        repo_root,
        relative.parts[:-1],
        create=False,
    )
    try:
        metadata = os.fstat(descriptor)
        if (metadata.st_dev, metadata.st_ino) != expected:
            raise ReconciliationWriteError(
                f"mapping parent changed concurrently: {repo_root / relative}"
            )
    finally:
        os.close(descriptor)


def _atomic_replace_mapping(
    mapping: Path,
    content: bytes,
    snapshot: dict[str, Any],
    *,
    repo_root: Path,
) -> None:
    try:
        relative = PurePosixPath(mapping.relative_to(repo_root).as_posix())
    except ValueError as exc:
        raise ReconciliationWriteError(
            f"mapping escapes repository root: {mapping}"
        ) from exc
    if not safe_relative_path(relative.as_posix()):
        raise ReconciliationWriteError(f"mapping path is unsafe: {mapping}")
    parent_fd = _open_directory_chain(
        repo_root,
        relative.parts[:-1],
        create=False,
    )
    temporary_name = (
        f".{relative.name}.inventory-stage-{uuid.uuid4().hex}.tmp"
    )
    temporary_created = False
    descriptor = -1
    try:
        parent_metadata = os.fstat(parent_fd)
        parent_identity = (parent_metadata.st_dev, parent_metadata.st_ino)
        if _mapping_snapshot_at(
            parent_fd,
            relative.name,
            display_path=mapping,
        ) != snapshot:
            raise ReconciliationWriteError(
                f"mapping changed after reconciliation preflight: {mapping}"
            )
        descriptor = os.open(
            temporary_name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=parent_fd,
        )
        temporary_created = True
        temporary_metadata = os.fstat(descriptor)
        offset = 0
        while offset < len(content):
            written = os.write(descriptor, content[offset:])
            if written <= 0:
                raise ReconciliationWriteError(
                    f"short mapping stage write: {mapping}"
                )
            offset += written
        os.fchmod(descriptor, int(snapshot["mode"]))
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        named_temporary = os.stat(
            temporary_name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        if (
            stat.S_ISLNK(named_temporary.st_mode)
            or not stat.S_ISREG(named_temporary.st_mode)
            or named_temporary.st_dev != temporary_metadata.st_dev
            or named_temporary.st_ino != temporary_metadata.st_ino
        ):
            raise ReconciliationWriteError(
                f"mapping stage changed before replace: {mapping}"
            )
        if _mapping_snapshot_at(
            parent_fd,
            relative.name,
            display_path=mapping,
        ) != snapshot:
            raise ReconciliationWriteError(
                f"mapping changed immediately before replace: {mapping}"
            )
        _assert_active_mapping_parent(
            repo_root,
            relative,
            parent_identity,
        )
        os.replace(
            temporary_name,
            relative.name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        temporary_created = False
        os.fsync(parent_fd)
        _assert_active_mapping_parent(
            repo_root,
            relative,
            parent_identity,
        )
        installed = _mapping_snapshot_at(
            parent_fd,
            relative.name,
            display_path=mapping,
        )
        if (
            installed["bytes"] != content
            or installed["sha256"] != hashlib.sha256(content).hexdigest()
            or installed["mode"] != snapshot["mode"]
            or installed["dev"] != temporary_metadata.st_dev
            or installed["ino"] != temporary_metadata.st_ino
        ):
            raise ReconciliationWriteError(
                f"installed mapping failed verification: {mapping}"
            )
    except ReconciliationWriteError:
        raise
    except Exception as exc:
        raise ReconciliationWriteError(
            f"failed to atomically replace mapping {mapping}: {exc}"
        ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary_created:
            try:
                os.unlink(temporary_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
        os.close(parent_fd)


def _atomic_write_mapping_batch(
    writes: list[tuple[Path, bytes, dict[str, Any]]],
    *,
    repo_root: Path,
) -> None:
    """Install a locked batch; the outer durable guard owns rollback."""
    for mapping, _content, snapshot in writes:
        if not _mapping_matches_snapshot(mapping, repo_root, snapshot):
            raise ReconciliationWriteError(
                f"mapping changed after reconciliation preflight: {mapping}"
            )
    for mapping, content, snapshot in writes:
        _atomic_replace_mapping(
            mapping,
            content,
            snapshot,
            repo_root=repo_root,
        )


def reconcile_mappings(
    mappings: Iterable[Path],
    *,
    repo_root: Path,
    cache: GitHubObjectCache,
    write: bool = False,
    today: str | None = None,
    lock_timeout: float = 10.0,
) -> dict[str, Any]:
    mappings = sorted(Path(mapping) for mapping in mappings)
    if write:
        try:
            from sync_upstream import mapping_advisory_lock
            from durable_file_batch import durable_batch_lock_and_recover
        except ModuleNotFoundError:  # pragma: no cover - package-style import
            from scripts.sync_upstream import mapping_advisory_lock
            from scripts.durable_file_batch import (
                durable_batch_lock_and_recover,
            )
        # Global order shared by sync, ingest, and reconciliation:
        # durable repository batch -> sorted mappings -> sorted skills.
        with durable_batch_lock_and_recover(
            repo_root,
            timeout=lock_timeout,
        ) as batch_guard:
            with contextlib.ExitStack() as locks:
                # The first mapping snapshot is captured only after every
                # mapping lock is held, so the following CAS window cannot
                # overlap another conforming writer.
                for mapping in mappings:
                    locks.enter_context(
                        mapping_advisory_lock(mapping, timeout=lock_timeout)
                    )
                return _reconcile_mappings_locked(
                    mappings,
                    repo_root=repo_root,
                    cache=cache,
                    write=True,
                    today=today,
                    batch_guard=batch_guard,
                )
    return _reconcile_mappings_locked(
        mappings,
        repo_root=repo_root,
        cache=cache,
        write=False,
        today=today,
        batch_guard=None,
    )


def _reconcile_mappings_locked(
    mappings: list[Path],
    *,
    repo_root: Path,
    cache: GitHubObjectCache,
    write: bool,
    today: str | None,
    batch_guard: Any | None,
) -> dict[str, Any]:
    report_entries: list[dict[str, Any]] = []
    mappings_changed = 0
    scanned = 0
    write_blocked = 0
    today = today or date.today().isoformat()
    planned_payloads: dict[Path, dict[str, Any]] = {}
    mapping_snapshots: dict[Path, dict[str, Any]] = {}
    mapping_changed_flags: dict[Path, bool] = {}
    entries_for_preflight: list[tuple[dict[str, Any], dict[str, Any]]] = []
    write_error: str | None = None
    recovery_paths: list[str] = []

    for mapping in mappings:
        snapshot = _mapping_snapshot(mapping, repo_root)
        mapping_snapshots[mapping] = snapshot
        payload = json.loads(snapshot["bytes"].decode("utf-8"))
        updated_payload = deepcopy(payload)
        mapping_changed = False
        for index, entry in enumerate(payload.get("skills", [])):
            if not isinstance(entry, dict) or not _is_active_external_canonical(entry):
                continue
            scanned += 1
            inspection = inspect_entry(entry, repo_root=repo_root, cache=cache)
            if write and cache.offline and inspection["unowned"]:
                for proposal in inspection["unowned"]:
                    proposal["classification"] = "unavailable"
                    proposal["source"] = None
                    proposal["reason"] = (
                        "offline reconciliation cannot authorize ownership "
                        "changes; rerun online"
                    )
            inspection["mapping"] = mapping.relative_to(repo_root).as_posix()
            updated, changed, blocked_reason = apply_entry_reconciliation(
                entry,
                inspection,
                repo_root=repo_root,
                today=today,
            )
            inspection["would_change"] = changed
            inspection["write_blocked_reason"] = blocked_reason
            if blocked_reason:
                write_blocked += 1
            entries_for_preflight.append((entry, inspection))
            if changed and not blocked_reason:
                updated_payload["skills"][index] = updated
                mapping_changed = True
            report_entries.append(inspection)
        planned_payloads[mapping] = updated_payload
        mapping_changed_flags[mapping] = mapping_changed

    if write and write_blocked == 0:
        for entry, inspection in entries_for_preflight:
            checkpoint_error = _verify_inspection_checkpoint(
                entry,
                inspection,
                repo_root=repo_root,
            )
            if checkpoint_error is None:
                continue
            inspection["write_blocked_reason"] = checkpoint_error
            write_blocked += 1

    if write and write_blocked == 0:
        writes = [
            (
                mapping,
                (
                    json.dumps(
                        planned_payloads[mapping],
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n"
                ).encode("utf-8"),
                mapping_snapshots[mapping],
            )
            for mapping in mappings
            if mapping_changed_flags[mapping]
        ]
        if writes:
            try:
                replacements = {
                    mapping: content
                    for mapping, content, _snapshot in writes
                }
                if batch_guard is None:
                    raise ReconciliationWriteError(
                        "reconciliation write has no durable batch guard"
                    )
                batch_guard.commit_batch(
                    replacements,
                    lambda: _atomic_write_mapping_batch(
                        writes,
                        repo_root=repo_root,
                    ),
                )
                mappings_changed = len(writes)
            except ReconciliationWriteError as exc:
                write_error = str(exc)
                recovery_paths = [str(path) for path in exc.recovery_paths]
                if exc.committed:
                    mappings_changed = len(writes)

    classification_counts = Counter(
        item["classification"]
        for entry in report_entries
        for item in entry["unowned"]
    )
    summary = {
        "mappings_scanned": len(mappings),
        "entries_scanned": scanned,
        "actual_files": sum(len(entry["actual_files"]) for entry in report_entries),
        "external_exact": classification_counts["external_exact"],
        "local_overlay": classification_counts["local_overlay"],
        "unavailable": classification_counts["unavailable"],
        "missing_managed": sum(
            len(entry["missing_managed"]) for entry in report_entries
        ),
        "stale_managed": sum(
            len(entry["stale_managed"]) for entry in report_entries
        ),
        "stale_artifact_targets": sum(
            len(entry["stale_artifact_targets"]) for entry in report_entries
        ),
        "hash_mismatches": sum(
            len(entry["hash_mismatches"]) for entry in report_entries
        ),
        "mode_mismatches": sum(
            len(entry.get("mode_mismatches", [])) for entry in report_entries
        ),
        "scan_errors": sum(
            len(entry.get("scan_errors", [])) for entry in report_entries
        ),
        "ownership_conflicts": sum(
            len(entry["ownership_conflicts"]) for entry in report_entries
        ),
        "write_blocked_entries": write_blocked,
        "mappings_changed": mappings_changed,
        "write_error": write_error,
        "recovery_paths": recovery_paths,
    }
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "mode": "write" if write else "dry-run",
        "summary": summary,
        "entries": report_entries,
    }


def _mapping_paths(args: argparse.Namespace, repo_root: Path) -> list[Path]:
    if args.mapping:
        result = []
        for value in args.mapping:
            path = Path(value)
            result.append(path if path.is_absolute() else repo_root / path)
        return sorted(result)
    return discover_source_mappings(repo_root / "docs/sources")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument(
        "--mapping",
        action="append",
        help="Mapping path relative to repo root; repeat for multiple mappings.",
    )
    parser.add_argument("--cache-dir", default=str(_default_cache_dir()))
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use only pre-recorded tree/blob cache fixtures.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Atomically write safe reconciliation proposals.",
    )
    parser.add_argument(
        "--check-clean",
        action="store_true",
        help=(
            "Exit non-zero unless the dry-run inventory has no ownership, "
            "hash, mode, availability, or scan debt"
        ),
    )
    parser.add_argument(
        "--output",
        help="Write the JSON report to this path instead of stdout.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only the summary instead of the full JSON report.",
    )
    args = parser.parse_args(argv)
    if args.write and args.check_clean:
        parser.error("--check-clean cannot be combined with --write")

    repo_root = Path(args.repo_root).resolve()
    mappings = _mapping_paths(args, repo_root)
    cache = GitHubObjectCache(
        Path(args.cache_dir),
        offline=args.offline,
    )
    report = reconcile_mappings(
        mappings,
        repo_root=repo_root,
        cache=cache,
        write=args.write,
    )
    if args.output and args.quiet:
        parser.error("--quiet cannot be combined with --output")
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(output, report)
    elif args.quiet:
        print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    else:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    if args.write and (
        report["summary"].get("write_blocked_entries", 0)
        or report["summary"].get("write_error")
    ):
        return 1
    if args.check_clean:
        debt_fields = (
            "external_exact",
            "local_overlay",
            "unavailable",
            "missing_managed",
            "stale_managed",
            "stale_artifact_targets",
            "hash_mismatches",
            "mode_mismatches",
            "scan_errors",
            "ownership_conflicts",
            "write_blocked_entries",
        )
        if any(report["summary"].get(field, 0) for field in debt_fields):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
