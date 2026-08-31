"""Cached, binary-safe GitHub artifact access for provenance v2 synchronization."""
from __future__ import annotations

import base64
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

FULL_COMMIT_RE = re.compile(r"^(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$")
GITHUB_REPO_RE = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]+$"
)
GIT_OBJECT_RE = FULL_COMMIT_RE
REGULAR_BLOB_MODES = frozenset({"100644", "100755"})
TREE_MODE = "040000"
SYMLINK_BLOB_MODE = "120000"
GITLINK_MODE = "160000"
CANONICAL_LICENSE_NORMALIZED_SHA256 = {
    # GitHub License API canonical templates, normalized with collapsed
    # whitespace and lowercase UTF-8. Explicit API SPDX remains authoritative;
    # these fingerprints are used only for NOASSERTION/missing SPDX evidence.
    "948703bcf1cb4a2dafd21676dd01e40a58fe21bd9b425c000b9070eccb441092": (
        "Apache-2.0"
    ),
    "78f11354a160ad5309cb9d24f8c4385dc807d9d098e8d8878f8732a5c2d395cd": (
        "BSD-2-Clause"
    ),
    "d86113948e206c727e862360f035d45432d06f72987bdc27bc8edd49660d8609": (
        "BSD-3-Clause"
    ),
    "3de3b5118df8d74984d5d56a03ca27484aae85fac8339e6c9faa8b5c4e69460c": (
        "CC0-1.0"
    ),
    "75b9da4d2b27f2f9a0cd5cca74ed1d40b9e2bc01d49d2c7f38daacad6122c016": (
        "MIT"
    ),
    "da4c44c6f085e773c147576dd132ed4985b336dca115e13d73555d0aaef1f87b": (
        "MPL-2.0"
    ),
    "a46a9193a46751396c49892e9518697927dd0af3947170a6b4c8e81be182dbef": (
        "Unlicense"
    ),
}


class GitHubProviderError(RuntimeError):
    """Base class for deterministic upstream provider failures."""


class GitHubUnavailable(GitHubProviderError):
    """The GitHub API could not provide an authoritative response."""


class ArtifactNotFound(GitHubProviderError):
    """One or more declared artifact sources do not exist at the resolved commit."""

    def __init__(self, missing_sources: list[str]) -> None:
        self.missing_sources = sorted(set(missing_sources))
        super().__init__(
            "declared upstream artifact source is missing: "
            + ", ".join(self.missing_sources)
        )


@dataclass(frozen=True)
class ResolvedRef:
    channel: str
    ref: str
    commit: str


@dataclass(frozen=True)
class ArtifactInventory:
    """Materialized source-to-target mapping for one immutable commit."""

    files: dict[str, bytes]
    source_blobs: dict[str, str]
    modes: dict[str, str]
    resolved: ResolvedRef


@dataclass(frozen=True)
class LicenseEvidence:
    """Strict immutable license bytes plus deterministic SPDX candidates."""

    path: str
    blob_sha: str
    content_sha256: str
    resolved_commit: str
    spdx_candidates: tuple[str, ...]
    api_spdx: str | None


class GitHubArtifactProvider:
    """Fetch immutable GitHub trees and blobs with per-run caching.

    The provider intentionally uses the Git Trees and Git Blobs APIs instead of
    raw text URLs.  This preserves binary bytes, provides a complete directory
    inventory, and makes rename diagnosis possible without guessing paths.
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        api_get=None,
    ) -> None:
        self.token = token
        self._api_get_override = api_get
        self._json_cache: dict[str, Any] = {}
        self._commit_cache: dict[tuple[str, str], str] = {}
        self._release_cache: dict[str, ResolvedRef] = {}
        self._tree_cache: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
        self._blob_cache: dict[tuple[str, str], bytes] = {}
        self._path_commit_cache: dict[tuple[str, str, str], str] = {}
        self._license_cache: dict[tuple[str, str], LicenseEvidence] = {}

    def _get_json(self, url: str) -> Any:
        if url in self._json_cache:
            return self._json_cache[url]
        if self._api_get_override is not None:
            try:
                value = self._api_get_override(url)
            except TypeError:
                value = self._api_get_override(url, self.token)
            if value is None:
                raise GitHubUnavailable(f"GitHub API returned no data for {url}")
            self._json_cache[url] = value
            return value

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "skills-sync-bot",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, headers=headers)
        # These requests are read-only. Retry only transient transport/server
        # failures, never reinterpret denied or missing resources as success.
        # A long/HTTP-date Retry-After is left to the next maintenance run.
        for attempt in range(3):
            delay = 0.5 * (2 ** attempt)
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    value = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                if retry_after is not None:
                    try:
                        delay = max(delay, float(retry_after))
                    except ValueError:
                        delay = float("inf")
                if (
                    attempt == 2
                    or exc.code not in {429, 500, 502, 503, 504}
                    or not 0 <= delay <= 5
                ):
                    raise GitHubUnavailable(
                        f"GitHub API HTTP {exc.code} for {url}"
                    ) from exc
            except OSError as exc:
                if attempt == 2:
                    raise GitHubUnavailable(
                        f"GitHub API failed for {url}: {exc}"
                    ) from exc
            except ValueError as exc:
                raise GitHubUnavailable(
                    f"GitHub API failed for {url}: {exc}"
                ) from exc
            time.sleep(delay)
        self._json_cache[url] = value
        return value

    @staticmethod
    def _validate_repo(repo: str) -> str:
        if (
            not isinstance(repo, str)
            or not GITHUB_REPO_RE.fullmatch(repo)
            or repo.endswith(("/", ".git"))
            or repo.rsplit("/", 1)[1] in {".", ".."}
        ):
            raise GitHubUnavailable(f"invalid GitHub repository slug: {repo!r}")
        return repo

    @classmethod
    def _repo_api(cls, repo: str, suffix: str) -> str:
        repo = cls._validate_repo(repo)
        return f"https://api.github.com/repos/{repo}/{suffix.lstrip('/')}"

    @staticmethod
    def _quoted_ref(value: str, *, label: str) -> str:
        if (
            not isinstance(value, str)
            or not value
            or len(value) > 1024
            or any(ord(character) < 0x20 for character in value)
        ):
            raise GitHubUnavailable(f"invalid GitHub {label}: {value!r}")
        return urllib.parse.quote(value, safe="")

    @staticmethod
    def _safe_repo_path(value: object) -> bool:
        if (
            not isinstance(value, str)
            or not value
            or value != value.strip()
            or value.startswith("/")
            or "\\" in value
            or any(ord(character) < 0x20 for character in value)
        ):
            return False
        parts = value.split("/")
        return all(part not in {"", ".", ".."} for part in parts)

    def resolve_commit(self, repo: str, ref: str) -> str:
        repo = self._validate_repo(repo)
        key = (repo, ref)
        if key in self._commit_cache:
            return self._commit_cache[key]
        quoted = self._quoted_ref(ref, label="ref")
        data = self._get_json(self._repo_api(repo, f"commits/{quoted}"))
        sha = data.get("sha") if isinstance(data, dict) else None
        if not isinstance(sha, str) or not FULL_COMMIT_RE.fullmatch(sha):
            raise GitHubUnavailable(f"could not resolve {repo}@{ref} to a full commit")
        sha = sha.lower()
        self._commit_cache[key] = sha
        return sha

    def resolve_tracking(self, repo: str, tracking: dict[str, Any]) -> ResolvedRef:
        repo = self._validate_repo(repo)
        channel = tracking.get("channel")
        ref = tracking.get("ref")
        if not isinstance(channel, str) or not isinstance(ref, str) or not ref:
            raise GitHubUnavailable("tracking.channel and tracking.ref are required")
        self._quoted_ref(ref, label="tracking ref")

        if channel == "latest_release":
            if repo in self._release_cache:
                return self._release_cache[repo]
            data = self._get_json(self._repo_api(repo, "releases/latest"))
            if (
                not isinstance(data, dict)
                or data.get("draft") is True
                or data.get("prerelease") is True
            ):
                raise GitHubUnavailable(
                    f"{repo} has no authoritative latest stable release"
                )
            tag = data.get("tag_name")
            if not isinstance(tag, str) or not tag:
                raise GitHubUnavailable(f"{repo} latest release has no tag_name")
            resolved = ResolvedRef(channel, tag, self.resolve_commit(repo, tag))
            self._release_cache[repo] = resolved
            return resolved

        if channel == "fixed_ref":
            if not FULL_COMMIT_RE.fullmatch(ref):
                raise GitHubUnavailable(
                    "fixed_ref must be a full 40- or 64-character commit SHA"
                )
            commit = self.resolve_commit(repo, ref)
            if commit != ref.lower():
                raise GitHubUnavailable(
                    f"fixed_ref resolved to unexpected commit {commit}"
                )
            return ResolvedRef(channel, ref.lower(), commit)

        if channel in {"default_branch", "canary"}:
            return ResolvedRef(channel, ref, self.resolve_commit(repo, ref))

        raise GitHubUnavailable(f"unsupported external tracking channel: {channel!r}")

    @classmethod
    def _validate_tree_entry(
        cls,
        repo: str,
        commit: str,
        item: object,
        *,
        nested_name: bool = False,
    ) -> dict[str, Any]:
        """Validate one Git Trees API entry and preserve known Git objects.

        GitHub represents symlinks as ``blob`` entries with mode ``120000`` and
        submodules/gitlinks as ``commit`` entries with mode ``160000``.  Neither
        can be materialized safely as a regular artifact file.  They remain in
        the inventory so artifact declarations can reject them within their own
        source scope without unrelated special objects blocking the repository.
        Unknown type/mode combinations still fail closed globally.  Executable
        regular blobs remain byte payloads; accepting mode ``100755`` does not
        alter their content.
        """
        if not isinstance(item, dict):
            raise GitHubUnavailable(
                f"invalid Git tree entry for {repo}@{commit}"
            )
        path = item.get("path")
        item_type = item.get("type")
        mode = item.get("mode")
        sha = item.get("sha")
        safe_path = cls._safe_repo_path(path)
        if nested_name and isinstance(path, str) and "/" in path:
            safe_path = False
        if (
            not safe_path
            or not isinstance(sha, str)
            or not GIT_OBJECT_RE.fullmatch(sha)
        ):
            raise GitHubUnavailable(
                f"invalid Git tree entry for {repo}@{commit}"
            )
        if not (
            (item_type == "blob" and mode in REGULAR_BLOB_MODES)
            or (item_type == "blob" and mode == SYMLINK_BLOB_MODE)
            or (item_type == "tree" and mode == TREE_MODE)
            or (item_type == "commit" and mode == GITLINK_MODE)
        ):
            raise GitHubUnavailable(
                "unsupported Git tree entry type/mode requires manual review "
                f"for {repo}@{commit}:{path}: {item_type!r}/{mode!r}"
            )
        return item

    @staticmethod
    def _is_regular_blob(item: object) -> bool:
        return (
            isinstance(item, dict)
            and item.get("type") == "blob"
            and item.get("mode") in REGULAR_BLOB_MODES
        )

    @staticmethod
    def _is_special_git_object(item: object) -> bool:
        return isinstance(item, dict) and (
            (
                item.get("type") == "blob"
                and item.get("mode") == SYMLINK_BLOB_MODE
            )
            or (
                item.get("type") == "commit"
                and item.get("mode") == GITLINK_MODE
            )
        )

    def tree(self, repo: str, commit: str) -> dict[str, dict[str, Any]]:
        repo = self._validate_repo(repo)
        if not FULL_COMMIT_RE.fullmatch(commit):
            raise GitHubUnavailable(f"invalid resolved commit: {commit!r}")
        key = (repo, commit)
        if key in self._tree_cache:
            return self._tree_cache[key]
        data = self._get_json(
            self._repo_api(
                repo,
                f"git/trees/{self._quoted_ref(commit, label='commit')}?recursive=1",
            )
        )
        if not isinstance(data, dict):
            raise GitHubUnavailable(
                f"invalid recursive tree for {repo}@{commit}"
            )
        if data.get("truncated") is True:
            inventory = self._walk_git_trees(repo, commit)
            self._tree_cache[key] = inventory
            return inventory
        raw_tree = data.get("tree")
        if not isinstance(raw_tree, list):
            raise GitHubUnavailable(f"invalid recursive tree for {repo}@{commit}")
        inventory: dict[str, dict[str, Any]] = {}
        for item in raw_tree:
            item = self._validate_tree_entry(repo, commit, item)
            path = item["path"]
            if path in inventory:
                raise GitHubUnavailable(
                    f"duplicate recursive tree path for {repo}@{commit}: {path}"
                )
            inventory[str(path)] = item
        self._tree_cache[key] = inventory
        return inventory

    def _walk_git_trees(
        self, repo: str, commit: str
    ) -> dict[str, dict[str, Any]]:
        """Build a complete inventory through non-recursive Git Trees calls."""
        inventory: dict[str, dict[str, Any]] = {}
        pending: list[tuple[str, str]] = [("", commit)]
        visited_nodes = 0
        while pending:
            prefix, tree_sha = pending.pop()
            visited_nodes += 1
            if visited_nodes > 1_000_000:
                raise GitHubUnavailable(
                    f"Git tree inventory exceeds safety limit for {repo}@{commit}"
                )
            data = self._get_json(
                self._repo_api(
                    repo,
                    f"git/trees/{self._quoted_ref(tree_sha, label='tree SHA')}",
                )
            )
            if not isinstance(data, dict) or data.get("truncated") is True:
                raise GitHubUnavailable(
                    f"complete non-recursive Git tree unavailable for "
                    f"{repo}@{commit}:{prefix or '/'}"
                )
            raw_tree = data.get("tree")
            if not isinstance(raw_tree, list):
                raise GitHubUnavailable(
                    f"invalid non-recursive Git tree for "
                    f"{repo}@{commit}:{prefix or '/'}"
                )
            for item in raw_tree:
                item = self._validate_tree_entry(
                    repo,
                    commit,
                    item,
                    nested_name=True,
                )
                name = item["path"]
                item_type = item["type"]
                sha = item["sha"]
                path = f"{prefix}/{name}" if prefix else str(name)
                if path in inventory:
                    raise GitHubUnavailable(
                        f"duplicate Git tree path for {repo}@{commit}: {path}"
                    )
                inventory[path] = {
                    "path": path,
                    "type": item_type,
                    "mode": item["mode"],
                    "sha": sha,
                    "size": item.get("size"),
                }
                if item_type == "tree":
                    pending.append((path, sha))
        return inventory

    def blob(self, repo: str, blob_sha: str) -> bytes:
        repo = self._validate_repo(repo)
        if not GIT_OBJECT_RE.fullmatch(blob_sha):
            raise GitHubUnavailable(f"invalid Git blob SHA: {blob_sha!r}")
        key = (repo, blob_sha)
        if key in self._blob_cache:
            return self._blob_cache[key]
        data = self._get_json(
            self._repo_api(
                repo,
                f"git/blobs/{self._quoted_ref(blob_sha, label='blob SHA')}",
            )
        )
        if not isinstance(data, dict):
            raise GitHubUnavailable(f"invalid blob response for {repo}@{blob_sha}")
        encoding = data.get("encoding")
        content = data.get("content")
        if encoding != "base64" or not isinstance(content, str):
            raise GitHubUnavailable(
                f"unsupported blob encoding for {repo}@{blob_sha}: {encoding!r}"
            )
        try:
            compact = re.sub(r"[ \t\r\n\f\v]+", "", content)
            raw = base64.b64decode(compact.encode("ascii"), validate=True)
        except (ValueError, TypeError, UnicodeEncodeError) as exc:
            raise GitHubUnavailable(
                f"invalid base64 blob for {repo}@{blob_sha}"
            ) from exc
        size = data.get("size")
        if (
            isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or size != len(raw)
        ):
            raise GitHubUnavailable(
                f"Git blob size mismatch for {repo}@{blob_sha}"
            )
        algorithm = hashlib.sha1 if len(blob_sha) == 40 else hashlib.sha256
        header = f"blob {len(raw)}\0".encode("ascii")
        actual_sha = algorithm(header + raw).hexdigest()
        if actual_sha.lower() != blob_sha.lower():
            raise GitHubUnavailable(
                f"Git blob hash mismatch for {repo}@{blob_sha}"
            )
        self._blob_cache[key] = raw
        return raw

    @staticmethod
    def _detect_license_spdx(raw: bytes) -> tuple[str, ...]:
        """Match complete normalized text to GitHub canonical templates."""
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return ()
        normalized = re.sub(r"\s+", " ", text).strip().lower().encode("utf-8")
        detected = CANONICAL_LICENSE_NORMALIZED_SHA256.get(
            hashlib.sha256(normalized).hexdigest()
        )
        return (detected,) if detected is not None else ()

    def license_evidence(self, repo: str, commit: str) -> LicenseEvidence:
        """Fetch and verify GitHub's license file at one immutable commit."""
        repo = self._validate_repo(repo)
        if not FULL_COMMIT_RE.fullmatch(commit):
            raise GitHubUnavailable(
                "license query ref must be a full immutable commit SHA"
            )
        commit = commit.lower()
        key = (repo, commit)
        if key in self._license_cache:
            return self._license_cache[key]
        query = urllib.parse.urlencode({"ref": commit})
        data = self._get_json(self._repo_api(repo, f"license?{query}"))
        if not isinstance(data, dict):
            raise GitHubUnavailable(
                f"invalid license response for {repo}@{commit}"
            )
        path = data.get("path")
        blob_sha = data.get("sha")
        encoding = data.get("encoding")
        content = data.get("content")
        size = data.get("size")
        if not self._safe_repo_path(path):
            raise GitHubUnavailable(
                f"invalid license path for {repo}@{commit}: {path!r}"
            )
        if not isinstance(blob_sha, str) or not GIT_OBJECT_RE.fullmatch(blob_sha):
            raise GitHubUnavailable(
                f"invalid license blob SHA for {repo}@{commit}"
            )
        if encoding != "base64" or not isinstance(content, str):
            raise GitHubUnavailable(
                f"unsupported license encoding for {repo}@{commit}: {encoding!r}"
            )
        try:
            compact = re.sub(r"[ \t\r\n\f\v]+", "", content)
            raw = base64.b64decode(compact.encode("ascii"), validate=True)
        except (ValueError, TypeError, UnicodeEncodeError) as exc:
            raise GitHubUnavailable(
                f"invalid base64 license content for {repo}@{commit}"
            ) from exc
        if (
            isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or size != len(raw)
        ):
            raise GitHubUnavailable(
                f"license size mismatch for {repo}@{commit}"
            )
        algorithm = hashlib.sha1 if len(blob_sha) == 40 else hashlib.sha256
        actual_sha = algorithm(
            f"blob {len(raw)}\0".encode("ascii") + raw
        ).hexdigest()
        if actual_sha.lower() != blob_sha.lower():
            raise GitHubUnavailable(
                f"license Git blob hash mismatch for {repo}@{commit}"
            )
        license_value = data.get("license")
        api_spdx = (
            license_value.get("spdx_id")
            if isinstance(license_value, dict)
            else None
        )
        if api_spdx is not None and (
            not isinstance(api_spdx, str)
            or not api_spdx
            or api_spdx != api_spdx.strip()
            or len(api_spdx) > 128
            or any(ord(character) < 0x20 for character in api_spdx)
        ):
            raise GitHubUnavailable(
                f"invalid GitHub SPDX evidence for {repo}@{commit}"
            )
        evidence = LicenseEvidence(
            path=str(path),
            blob_sha=blob_sha.lower(),
            content_sha256=hashlib.sha256(raw).hexdigest(),
            resolved_commit=commit,
            spdx_candidates=self._detect_license_spdx(raw),
            api_spdx=api_spdx,
        )
        self._license_cache[key] = evidence
        return evidence

    def fetch_artifacts(
        self,
        repo: str,
        tracking: dict[str, Any],
        artifacts: list[dict[str, Any]],
    ) -> ArtifactInventory:
        repo = self._validate_repo(repo)
        if not isinstance(artifacts, list) or not artifacts:
            raise GitHubUnavailable("artifact inventory must be a non-empty array")
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                raise GitHubUnavailable("artifact declarations must be objects")
            source = artifact.get("source")
            target = artifact.get("target")
            if (
                not self._safe_repo_path(source)
                or not self._safe_repo_path(target)
                or artifact.get("type", "file") not in {"file", "directory"}
            ):
                raise GitHubUnavailable(
                    "artifact source and target must be safe paths"
                )
        resolved = self.resolve_tracking(repo, tracking)
        tree = self.tree(repo, resolved.commit)
        pending_files: list[tuple[str, str, str]] = []
        source_blobs: dict[str, str] = {}
        modes: dict[str, str] = {}
        missing: list[str] = []
        claimed_targets: set[str] = set()

        for artifact in artifacts:
            source = artifact.get("source")
            target = artifact.get("target")
            artifact_type = artifact.get("type", "file")
            if not isinstance(source, str) or not isinstance(target, str):
                raise GitHubUnavailable("artifact source and target must be strings")
            if not self._safe_repo_path(source) or not self._safe_repo_path(target):
                raise GitHubUnavailable("artifact source and target must be safe paths")
            if artifact_type == "file":
                item = tree.get(source)
                if item is None:
                    missing.append(source)
                    continue
                if self._is_special_git_object(item):
                    raise GitHubUnavailable(
                        "declared artifact source is a symlink or gitlink and "
                        "requires manual review: "
                        f"{repo}@{resolved.commit}:{source} "
                        f"({item.get('type')}/{item.get('mode')})"
                    )
                if not self._is_regular_blob(item):
                    missing.append(source)
                    continue
                blob_sha = item.get("sha")
                if not isinstance(blob_sha, str):
                    raise GitHubUnavailable(f"artifact {source} has no blob SHA")
                if target in claimed_targets:
                    raise GitHubUnavailable(f"multiple artifacts claim target {target}")
                claimed_targets.add(target)
                pending_files.append((source, target, blob_sha))
                source_blobs[source] = blob_sha
                modes[target] = str(item["mode"])
                continue

            if artifact_type != "directory":
                raise GitHubUnavailable(f"unsupported artifact type: {artifact_type!r}")
            prefix = source.rstrip("/") + "/"
            scoped_special = [
                (
                    f"{path} "
                    f"({item.get('type')}/{item.get('mode')})"
                )
                for path, item in tree.items()
                if (path == source or path.startswith(prefix))
                and self._is_special_git_object(item)
            ]
            if scoped_special:
                raise GitHubUnavailable(
                    "declared directory artifact contains a symlink or gitlink "
                    "and requires manual review: "
                    f"{repo}@{resolved.commit}:"
                    + ", ".join(sorted(scoped_special))
                )
            members = [
                (path, item)
                for path, item in tree.items()
                if path.startswith(prefix)
                and self._is_regular_blob(item)
            ]
            if not members:
                missing.append(source)
                continue
            for path, item in sorted(members):
                relative = path[len(prefix) :]
                mapped_target = target.rstrip("/") + "/" + relative
                if mapped_target in claimed_targets:
                    raise GitHubUnavailable(
                        f"multiple artifacts claim target {mapped_target}"
                    )
                blob_sha = item.get("sha")
                if not isinstance(blob_sha, str):
                    raise GitHubUnavailable(f"artifact {path} has no blob SHA")
                claimed_targets.add(mapped_target)
                pending_files.append((path, mapped_target, blob_sha))
                source_blobs[path] = blob_sha
                modes[mapped_target] = str(item["mode"])

        if missing:
            raise ArtifactNotFound(missing)
        files = {
            target: self.blob(repo, blob_sha)
            for _source, target, blob_sha in pending_files
        }
        return ArtifactInventory(files, source_blobs, modes, resolved)

    def compare(self, repo: str, base: str, head: str) -> dict[str, Any]:
        repo = self._validate_repo(repo)
        if not FULL_COMMIT_RE.fullmatch(base) or not FULL_COMMIT_RE.fullmatch(head):
            raise GitHubUnavailable(
                "compare base and head must be full commit SHAs"
            )
        quoted_base = self._quoted_ref(base, label="compare base")
        quoted_head = self._quoted_ref(head, label="compare head")
        data = self._get_json(
            self._repo_api(repo, f"compare/{quoted_base}...{quoted_head}")
        )
        if not isinstance(data, dict) or data.get("status") not in {
            "ahead",
            "behind",
            "diverged",
            "identical",
        }:
            raise GitHubUnavailable(
                f"could not compare {repo}@{base}...{head}"
            )
        return {
            "status": data["status"],
            "ahead_by": int(data.get("ahead_by", 0)),
            "behind_by": int(data.get("behind_by", 0)),
        }

    def path_commit(self, repo: str, ref: str, path: str) -> str:
        repo = self._validate_repo(repo)
        if not FULL_COMMIT_RE.fullmatch(ref):
            raise GitHubUnavailable(
                "path commit query ref must be a full commit SHA"
            )
        if not self._safe_repo_path(path):
            raise GitHubUnavailable(f"invalid GitHub path: {path!r}")
        key = (repo, ref, path)
        if key in self._path_commit_cache:
            return self._path_commit_cache[key]
        query = urllib.parse.urlencode({"sha": ref, "path": path, "per_page": 1})
        data = self._get_json(self._repo_api(repo, f"commits?{query}"))
        if not isinstance(data, list) or not data:
            raise GitHubUnavailable(
                f"could not resolve path commit for {repo}@{ref}:{path}"
            )
        sha = data[0].get("sha") if isinstance(data[0], dict) else None
        if not isinstance(sha, str) or not FULL_COMMIT_RE.fullmatch(sha):
            raise GitHubUnavailable(
                f"invalid path commit for {repo}@{ref}:{path}"
            )
        self._path_commit_cache[key] = sha.lower()
        return sha.lower()

    def moved_candidates(
        self,
        repo: str,
        old_commit: str | None,
        new_commit: str,
        missing_sources: list[str],
        *,
        local_files: dict[str, bytes] | None = None,
    ) -> dict[str, list[str]]:
        """Locate exact-blob rename candidates; never chooses one automatically."""
        new_tree = self.tree(repo, new_commit)
        old_tree = self.tree(repo, old_commit) if old_commit else {}
        local_files = local_files or {}
        candidates: dict[str, list[str]] = {}

        for source in missing_sources:
            old_sha = None
            old_type = "blob"
            old_item = old_tree.get(source)
            if (
                isinstance(old_item, dict)
                and (
                    self._is_regular_blob(old_item)
                    or (
                        old_item.get("type") == "tree"
                        and old_item.get("mode") == TREE_MODE
                    )
                )
            ):
                candidate_sha = old_item.get("sha")
                if isinstance(candidate_sha, str):
                    old_sha = candidate_sha
                    old_type = str(old_item.get("type"))
            if old_sha is None and source in local_files:
                raw = local_files[source]
                header = f"blob {len(raw)}\0".encode("ascii")
                old_sha = hashlib.sha1(header + raw).hexdigest()
            if old_sha is None:
                continue
            matches = sorted(
                path
                for path, item in new_tree.items()
                if isinstance(item, dict)
                and item.get("type") == old_type
                and (
                    self._is_regular_blob(item)
                    or (
                        item.get("type") == "tree"
                        and item.get("mode") == TREE_MODE
                    )
                )
                and item.get("sha") == old_sha
                and path != source
            )
            if matches:
                candidates[source] = matches
        return candidates
