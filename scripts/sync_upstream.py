#!/usr/bin/env python3
"""Check and synchronize upstream changes for tracked skills.

Reads the provenance mapping to find skills with external upstream sources,
checks for newer versions, and optionally applies updates.

Usage:
    # Check only — report which skills have upstream updates
    python scripts/sync_upstream.py --check-only

    # Check and explicitly record successful comparison timestamps
    python scripts/sync_upstream.py --check-only --record-check

    # Also write a machine-readable complete/degraded/failed report
    python scripts/sync_upstream.py --check-only --report-json report.json

    # Apply updates — download and replace with upstream versions
    python scripts/sync_upstream.py --apply

    # Dry run — show what would be updated without writing
    python scripts/sync_upstream.py --apply --dry-run

    # Check a specific source only
    python scripts/sync_upstream.py --check-only --source "github:alirezarezvani/claude-skills"

    # Explicit legacy compatibility (disabled by default)
    python scripts/sync_upstream.py --check-only --allow-v1
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import http.client
import json
import math
import os
import re
import socket
import ssl
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from contextlib import ExitStack, contextmanager
from datetime import date
from pathlib import Path, PurePosixPath
from time import sleep

try:
    from provenance_v2 import is_archived_sidecar
except ModuleNotFoundError:
    from scripts.provenance_v2 import is_archived_sidecar

try:
    import fcntl
except ImportError:  # pragma: no cover - repository CI is POSIX
    fcntl = None  # type: ignore[assignment]

try:
    from github_artifact_provider import (
        ArtifactNotFound,
        GITHUB_REPO_RE,
        GitHubArtifactProvider,
        GitHubProviderError,
        LicenseEvidence,
    )
except ModuleNotFoundError:  # pragma: no cover - import path used by test loaders
    from scripts.github_artifact_provider import (
        ArtifactNotFound,
        GITHUB_REPO_RE,
        GitHubArtifactProvider,
        GitHubProviderError,
        LicenseEvidence,
    )

try:
    from audit_licenses import PERMISSIVE_LICENSES
except ModuleNotFoundError:  # pragma: no cover - import path used by tests
    from scripts.audit_licenses import PERMISSIVE_LICENSES

try:
    from durable_file_batch import (
        DurableBatchGuard,
        durable_batch_lock_and_recover,
    )
except ModuleNotFoundError:  # pragma: no cover - package-style unit import
    from scripts.durable_file_batch import (
        DurableBatchGuard,
        durable_batch_lock_and_recover,
    )

try:
    from validate_skill_sources import (
        validate_mapping as validate_provenance_mapping,
        validate_repository_mappings,
    )
except ModuleNotFoundError:  # pragma: no cover - import path used by tests
    from scripts.validate_skill_sources import (
        validate_mapping as validate_provenance_mapping,
        validate_repository_mappings,
    )

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
PROVENANCE_FILE = REPO_ROOT / "docs" / "sources" / "in-house.skills.json"
SOURCE_MAPPINGS_DIR = REPO_ROOT / "docs" / "sources"
NETWORK_ERRORS = (
    urllib.error.URLError,
    http.client.RemoteDisconnected,
    http.client.IncompleteRead,
    TimeoutError,
    socket.timeout,
    ssl.SSLError,
)
MONITOR_CHANNELS = {"default_branch", "canary"}
AUTO_CHANNELS = {"latest_release", "fixed_ref"}
COMMIT_RE = re.compile(r"^(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VALID_KINDS = {
    "mirror",
    "overlay",
    "composite",
    "bundle",
    "snapshot",
    "in_house",
    "reference_only",
}
VALID_SYNC_MODES = {"replace", "monitor", "local-only", "archived", "manual"}
VALID_CHANNELS = {
    "latest_release",
    "default_branch",
    "canary",
    "fixed_ref",
    "local",
}
_ACTIVE_ARTIFACT_PROVIDER: GitHubArtifactProvider | None = None
_TOKEN_UNRESOLVED = object()
_ACTIVE_GITHUB_TOKEN: str | None | object = _TOKEN_UNRESOLVED
LOCAL_AUTHORITY_FRONTMATTER_FIELDS = frozenset(
    {
        "zh_description",
        "version",
        "author",
        "source",
        "source_url",
        "license",
        "tags",
        "created_at",
        "updated_at",
        "quality",
        "complexity",
    }
)
LOCAL_SUPPLEMENT_FRONTMATTER_FIELDS = frozenset({"upstream_slug"})
LOCAL_FRONTMATTER_FIELDS = (
    LOCAL_AUTHORITY_FRONTMATTER_FIELDS
    | LOCAL_SUPPLEMENT_FRONTMATTER_FIELDS
)


def github_raw_url(repo: str, path: str, ref: str = "main") -> str:
    """Construct a GitHub raw content URL."""
    return f"https://raw.githubusercontent.com/{repo}/{ref}/{path}"


def github_path_from_source_url(source_url: str, repo: str) -> str | None:
    """Extract an upstream SKILL.md path from a GitHub blob/tree source URL."""
    pattern = rf"https://github\.com/{re.escape(repo)}/(blob|tree)/([^/]+)/(.*)"
    match = re.match(pattern, source_url.rstrip("/"))
    if not match:
        return None
    kind, _ref, path = match.groups()
    if kind == "blob":
        return path if path.endswith("SKILL.md") else None
    if kind == "tree":
        return f"{path.rstrip('/')}/SKILL.md"
    return None


def resolve_github_token() -> str | None:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError, TimeoutError):
        return None
    candidate = result.stdout.strip()
    if result.returncode == 0 and candidate:
        return candidate
    return None


def fetch_url(
    url: str,
    token: str | None = None,
    *,
    quiet_404: bool = False,
    retries: int = 1,
) -> str | None:
    """Fetch content from a URL."""
    headers = {"User-Agent": "skills-sync-bot"}
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                try:
                    return resp.read().decode("utf-8", errors="replace")
                except http.client.IncompleteRead as e:
                    print(f"    Warning: incomplete read for {url}; using partial content", file=sys.stderr)
                    return e.partial.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            last_error = e
            break
        except NETWORK_ERRORS as e:
            last_error = e
            if attempt < retries:
                sleep(0.5 * (attempt + 1))
                continue
            break

    if last_error is not None:
        if not (
            quiet_404
            and isinstance(last_error, urllib.error.HTTPError)
            and last_error.code == 404
        ):
            print(f"    Warning: fetch failed for {url}: {last_error}", file=sys.stderr)
        fallback = fetch_github_raw_via_api(url, token)
        if fallback is not None:
            return fallback
    return None


def github_api_get(url: str, token: str | None = None) -> dict | None:
    """Make a GET request to GitHub API."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "skills-sync-bot",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.HTTPError, *NETWORK_ERRORS, json.JSONDecodeError) as e:
        print(f"    Warning: API request failed: {e}", file=sys.stderr)
        return None


def github_commit_sha(repo: str, ref: str, token: str | None = None) -> str | None:
    """Resolve a GitHub ref to a commit SHA for curated monitor checkpoints."""
    data = github_api_get(f"https://api.github.com/repos/{repo}/commits/{ref}", token)
    if not data:
        return None
    sha = data.get("sha")
    return str(sha) if sha else None


def github_compare_relation(
    repo: str,
    base: str,
    head: str,
    token: str | None = None,
) -> dict[str, int | str] | None:
    """Return the commit relationship between a reviewed checkpoint and a ref."""
    data = github_api_get(
        f"https://api.github.com/repos/{repo}/compare/{base}...{head}",
        token,
    )
    if not data:
        return None
    status = data.get("status")
    if status not in {"ahead", "behind", "diverged", "identical"}:
        return None
    return {
        "status": str(status),
        "ahead_by": int(data.get("ahead_by", 0)),
        "behind_by": int(data.get("behind_by", 0)),
    }


def fetch_github_raw_via_api(raw_url: str, token: str | None = None) -> str | None:
    """Fallback for raw.githubusercontent.com fetches using GitHub Contents API."""
    m = re.match(r"https://raw\.githubusercontent\.com/([^/]+/[^/]+)/([^/]+)/(.*)", raw_url)
    if not m:
        return None

    repo, ref, path = m.groups()
    api_url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
    data = github_api_get(api_url, token)
    if not data or data.get("type") != "file":
        return None

    content = data.get("content", "")
    if data.get("encoding") == "base64":
        return base64.b64decode(content).decode("utf-8", errors="replace")
    return content


def parse_frontmatter(text: str) -> dict[str, str]:
    """Extract frontmatter key-value pairs."""
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm: dict[str, str] = {}
    lines = m.group(1).splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if ":" not in line or line.startswith((" ", "\t")):
            index += 1
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if val in {"|", ">"}:
            collected = []
            index += 1
            while index < len(lines) and (lines[index].startswith((" ", "\t")) or not lines[index].strip()):
                if lines[index].strip():
                    collected.append(lines[index].strip())
                index += 1
            fm[key] = re.sub(r"\s+", " ", " ".join(collected)).strip()
            continue
        fm[key] = val.strip('"').strip("'")
        index += 1
    return fm


def strip_frontmatter(text: str) -> str:
    return re.sub(r"^---.*?---\s*", "", text, count=1, flags=re.DOTALL).strip()


def split_frontmatter(text: str) -> tuple[str | None, str]:
    match = re.match(r"^(---\s*\n.*?\n---\s*\n?)(.*)", text, re.DOTALL)
    if not match:
        return None, text
    return match.group(1), match.group(2)


def _frontmatter_field_blocks(text: str) -> tuple[list[str], dict[str, list[str]]]:
    """Return ordered, complete top-level YAML field blocks."""
    match = re.match(r"^---\s*\n(.*?)\n---(?:\s*\n|$)", text, re.DOTALL)
    if not match:
        return [], {}
    order: list[str] = []
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    pending: list[str] = []
    field_pattern = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:[ \t].*)?$")
    for line in match.group(1).splitlines():
        field_match = field_pattern.match(line)
        if field_match:
            current = field_match.group(1)
            if current in blocks:
                raise RuntimeError(
                    f"duplicate top-level frontmatter field: {current}"
                )
            order.append(current)
            blocks[current] = [*pending, line]
            pending = []
            continue
        if current is None:
            if not line.strip() or line.lstrip().startswith("#"):
                pending.append(line)
                continue
            raise RuntimeError(
                "frontmatter contains content outside a top-level field"
            )
        blocks[current].append(line)
    return order, blocks


def _normalized_frontmatter_block(lines: list[str]) -> str:
    normalized = [line.rstrip() for line in lines]
    while normalized and not normalized[-1]:
        normalized.pop()
    if len(normalized) == 1 and ":" in normalized[0]:
        key, _, raw_value = normalized[0].partition(":")
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            quote = value[0]
            if quote == "'":
                decoded = value[1:-1].replace("''", "'")
            else:
                try:
                    decoded = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    decoded = None
            # Quoting a flow collection changes its YAML type, so preserve that
            # distinction. Ordinary scalar quote-style differences are noise.
            if isinstance(decoded, str) and not decoded.lstrip().startswith(("[", "{")):
                return f"{key.strip()}: {decoded}"
    return "\n".join(normalized)


def _upstream_frontmatter_contract(text: str) -> dict[str, str]:
    _order, blocks = _frontmatter_field_blocks(text)
    return {
        key: _normalized_frontmatter_block(lines)
        for key, lines in blocks.items()
        if key not in LOCAL_FRONTMATTER_FIELDS
    }


def _merge_frontmatter_authority(local_text: str, upstream_text: str) -> str:
    """Preserve explicit local fields and replace every upstream-owned field."""
    local_order, local_blocks = _frontmatter_field_blocks(local_text)
    upstream_order, upstream_blocks = _frontmatter_field_blocks(upstream_text)
    merged_order: list[str] = []
    merged_blocks: dict[str, list[str]] = {}
    for key in local_order:
        if key in LOCAL_FRONTMATTER_FIELDS:
            merged_order.append(key)
            merged_blocks[key] = local_blocks[key]
        elif key in upstream_blocks:
            merged_order.append(key)
            merged_blocks[key] = upstream_blocks[key]
    for key in upstream_order:
        if key in LOCAL_FRONTMATTER_FIELDS or key in merged_blocks:
            continue
        merged_order.append(key)
        merged_blocks[key] = upstream_blocks[key]
    lines = ["---"]
    for key in merged_order:
        lines.extend(merged_blocks[key])
    lines.append("---")
    return "\n".join(lines) + "\n"


def update_frontmatter_field(frontmatter: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^({re.escape(key)}:\s*).*$", re.MULTILINE)
    line = f"{key}: {value}"
    if pattern.search(frontmatter):
        return pattern.sub(line, frontmatter)
    return re.sub(r"\n---\s*\n?$", f"\n{line}\n---\n", frontmatter.rstrip() + "\n")


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def bump_patch_version(version: str) -> str:
    raw = version.strip().strip('"').strip("'")
    parts = raw.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return version
    parts[2] = str(int(parts[2]) + 1)
    return yaml_quote(".".join(parts))


def remove_local_supplements(content: str) -> str:
    for marker in ("LOCAL-QUALITY-SUPPLEMENT", "LOCAL-CURATION-SUPPLEMENT"):
        content = re.sub(
            rf"\n+<!-- {marker}:START -->.*?<!-- {marker}:END -->\s*",
            "\n\n",
            content,
            flags=re.DOTALL,
        )
    return content.rstrip() + "\n"


def extract_local_supplement(content: str, marker: str) -> str:
    match = re.search(
        rf"<!-- {re.escape(marker)}:START -->.*?<!-- {re.escape(marker)}:END -->",
        content,
        flags=re.DOTALL,
    )
    return match.group(0).strip() if match else ""


def comparable_body(text: str) -> str:
    body = strip_frontmatter(remove_local_supplements(text))
    return "\n".join(line.rstrip() for line in body.splitlines())


def needs_quality_supplement(content: str) -> bool:
    line_count = len(content.splitlines())
    headings = re.findall(r"^##\s+.+$", content, re.MULTILINE)
    normalized_headings = [
        re.sub(r"[^a-z0-9]+", " ", heading.lower()).strip() for heading in headings
    ]
    has_lint_friendly_section = any(
        keyword in heading
        for heading in normalized_headings
        for keyword in ("overview", "workflow", "quick start", "quick reference", "usage", "process", "examples")
    )
    return line_count < 90 or "```" not in content or len(headings) < 2 or not has_lint_friendly_section


def build_quality_supplement(skill_name: str) -> str:
    title = skill_name.replace("-", " ").title()
    return f"""
<!-- LOCAL-QUALITY-SUPPLEMENT:START -->
## Usage Notes

This supplement is maintained by the repository sync pipeline. It keeps the
imported upstream skill usable inside this curated collection when the upstream
source is intentionally concise.

## Common Patterns

```text
1. Confirm that the user's task matches the skill trigger.
2. Read the relevant project files or user-provided context before acting.
3. Choose the smallest reversible action that advances the task.
4. Run the verification command or manual check that proves the result.
5. Report the outcome, evidence, and any remaining risk.
```

## Boundaries

- Prefer the upstream workflow for {title}; this section only adds local quality
  guardrails.
- Do not invent project facts when required files, vaults, services, or tools are
  unavailable.
- Stop and ask for clarification when the next action could overwrite user work,
  expose private data, or change production state.
- Treat skill selection as routing, not ceremony: invoke only the narrowest
  applicable workflow and keep user or repository instructions authoritative.
<!-- LOCAL-QUALITY-SUPPLEMENT:END -->
"""


def ensure_quality_floor(content: str, skill_name: str) -> str:
    cleaned = remove_local_supplements(content)
    if not needs_quality_supplement(cleaned):
        return cleaned
    return cleaned.rstrip() + "\n" + build_quality_supplement(skill_name).lstrip()


def merge_frontmatter(local_content: str, upstream_content: str) -> str:
    """Merge the explicit local allowlist with authoritative upstream metadata."""
    local_fm = parse_frontmatter(local_content)
    upstream_fm = parse_frontmatter(upstream_content)
    local_frontmatter, _ = split_frontmatter(local_content)
    upstream_frontmatter, upstream_body = split_frontmatter(upstream_content)
    local_curation = extract_local_supplement(local_content, "LOCAL-CURATION-SUPPLEMENT")

    if local_frontmatter is None:
        name = upstream_fm.get("name", local_fm.get("name", "imported-skill"))
        description = upstream_fm.get("description", local_fm.get("description", "Synced upstream skill."))
        local_frontmatter = "\n".join(
            [
                "---",
                f"name: {name}",
                f"description: {yaml_quote(description)}",
                'version: "1.0.0"',
                f'updated_at: "{date.today().isoformat()}"',
                "---",
                "",
            ]
        )

    merged_frontmatter = _merge_frontmatter_authority(
        local_frontmatter,
        upstream_frontmatter or "",
    )
    if local_fm.get("version"):
        merged_frontmatter = update_frontmatter_field(
            merged_frontmatter,
            "version",
            bump_patch_version(local_fm["version"]),
        )
    merged_frontmatter = update_frontmatter_field(
        merged_frontmatter,
        "updated_at",
        yaml_quote(date.today().isoformat()),
    )

    merged = merged_frontmatter.rstrip() + "\n" + upstream_body.lstrip()
    merged = ensure_quality_floor(
        merged,
        local_fm.get("name", upstream_fm.get("name", "synced-skill")),
    )
    if local_curation:
        merged = merged.rstrip() + "\n\n" + local_curation + "\n"
    # Hash exactly the canonical bytes that refresh_repo_views will retain.
    # Otherwise its quote/blank-line normalization invalidates both the
    # managed digest and any composite lock immediately after a safe apply.
    try:
        from export_openclaw_skills import normalize_skill_markdown
    except ModuleNotFoundError:
        from scripts.export_openclaw_skills import normalize_skill_markdown
    return normalize_skill_markdown(
        local_fm.get("name", upstream_fm.get("name", "synced-skill")), merged
    )


def apply_repository_adaptations(content: str, skill: dict) -> str:
    """Adapt upstream repository-relative links to this categorized layout."""
    if skill.get("repo") == "addyosmani/agent-skills":
        return content.replace("../../references/", "references/")
    return content


def _safe_mapping_path(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    return (
        not path.is_absolute()
        and path != PurePosixPath(".")
        and ".." not in path.parts
        and not re.match(r"^[A-Za-z]:/", normalized)
    )


def _mapping_identity(entry: dict, mapping_path: Path, entry_index: int) -> dict:
    """Build non-authoritative display fields for one provenance entry."""
    repo_skill = entry.get("repo_skill")
    local_path = REPO_ROOT / repo_skill if _safe_mapping_path(repo_skill) else REPO_ROOT
    return {
        "name": (
            entry.get("normalized_slug")
            or entry.get("video_name")
            or (local_path.parent.name if local_path != REPO_ROOT else f"entry-{entry_index}")
        ),
        "category": (
            local_path.parent.parent.name
            if isinstance(repo_skill, str) and len(local_path.parents) >= 2
            else "unknown"
        ),
        "local_path": local_path,
        "mapping_path": mapping_path,
        "mapping_entry_index": entry_index,
    }


def _artifact_source_for_target(artifact: object, target: str) -> str | None:
    """Resolve the source file owned by a file or directory artifact."""
    if not isinstance(artifact, dict):
        return None
    source = artifact.get("source")
    declared_target = artifact.get("target")
    artifact_type = artifact.get("type", "file")
    if artifact_type not in {"file", "directory"}:
        return None
    if not _safe_mapping_path(source) or not _safe_mapping_path(declared_target):
        return None
    source_path = PurePosixPath(str(source).replace("\\", "/"))
    target_path = PurePosixPath(str(declared_target).replace("\\", "/"))
    requested = PurePosixPath(target.replace("\\", "/"))
    if artifact_type == "directory":
        if requested != target_path and target_path not in requested.parents:
            return None
        relative = requested.relative_to(target_path)
        return str(source_path / relative)
    return str(source_path) if requested == target_path else None


def _artifact_owns_target(artifact: dict, target: str) -> bool:
    declared = artifact.get("target")
    if not isinstance(declared, str):
        return False
    if artifact.get("type", "file") == "file":
        return target == declared
    boundary = PurePosixPath(declared)
    candidate = PurePosixPath(target)
    return candidate == boundary or boundary in candidate.parents


def _v2_sync_entry_errors(entry: dict) -> list[str]:
    """Validate every sync-relevant v2 field before policy-based skipping."""
    errors: list[str] = []
    kind = entry.get("kind")
    if kind not in VALID_KINDS:
        errors.append(f"invalid kind: {kind!r}")
        return errors
    if kind not in {"mirror", "overlay", "snapshot"}:
        return errors
    if entry.get("status") not in {"verified_in_repo", "in_house"}:
        errors.append(f"invalid active status: {entry.get('status')!r}")
    slug = entry.get("normalized_slug")
    repo_skill = entry.get("repo_skill")
    if not isinstance(slug, str) or not slug:
        errors.append("normalized_slug is required")
    expected_repo_skill = (
        f"/{slug}/SKILL.md" if isinstance(slug, str) and slug else None
    )
    if (
        not _safe_mapping_path(repo_skill)
        or expected_repo_skill is None
        or not str(repo_skill).endswith(expected_repo_skill)
        or not str(repo_skill).startswith("skills/")
    ):
        errors.append(f"repo_skill is not canonical for {slug!r}: {repo_skill!r}")
        return errors
    skill_root = PurePosixPath(str(repo_skill)).parent
    entry_mode = entry.get("sync_mode")
    if entry_mode not in VALID_SYNC_MODES:
        errors.append(f"invalid entry sync_mode: {entry_mode!r}")

    origins = entry.get("origins")
    if not isinstance(origins, list) or not origins:
        errors.append("origins must be a non-empty array")
        return errors
    managed = entry.get("managed_files")
    if not isinstance(managed, list) or not managed:
        errors.append("managed_files must be a non-empty array")
        return errors

    managed_by_path: dict[str, dict] = {}
    for index, item in enumerate(managed):
        if not isinstance(item, dict):
            errors.append(f"managed_files[{index}] must be an object")
            continue
        path = item.get("path")
        digest = item.get("sha256")
        owner = item.get("owner")
        if (
            not _safe_mapping_path(path)
            or not PurePosixPath(str(path)).is_relative_to(skill_root)
        ):
            errors.append(f"managed_files[{index}] has unsafe target: {path!r}")
            continue
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(f"managed_files[{index}] has invalid sha256")
        if owner != slug:
            errors.append(
                f"managed_files[{index}] owner {owner!r} does not match {slug!r}"
            )
        if path in managed_by_path:
            errors.append(f"duplicate managed path: {path}")
        managed_by_path[str(path)] = item
        if _safe_mapping_path(path):
            candidate = REPO_ROOT / str(path)
            try:
                ancestor = REPO_ROOT
                for component in PurePosixPath(str(path)).parts[:-1]:
                    ancestor = ancestor / component
                    if ancestor.is_symlink():
                        raise ValueError("symlink ancestor")
                resolved = candidate.resolve(strict=True)
                resolved.relative_to(REPO_ROOT.resolve())
                metadata = candidate.lstat()
                if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(
                    metadata.st_mode
                ):
                    raise ValueError("not a regular file")
                if (
                    isinstance(digest, str)
                    and SHA256_RE.fullmatch(digest)
                    and hashlib.sha256(candidate.read_bytes()).hexdigest()
                    != digest.lower()
                ):
                    errors.append(
                        f"managed_files[{index}] digest does not match disk"
                    )
            except (FileNotFoundError, OSError, ValueError):
                errors.append(
                    f"managed_files[{index}] target is missing or unsafe"
                )

    external_modes: list[str] = []
    artifact_owners: dict[str, int] = {path: 0 for path in managed_by_path}
    for origin_index, origin in enumerate(origins):
        if not isinstance(origin, dict):
            errors.append(f"origins[{origin_index}] must be an object")
            continue
        missing = {
            "repo",
            "path",
            "license",
            "sync_mode",
            "artifacts",
            "tracking",
        } - set(origin)
        if missing:
            errors.append(
                f"origins[{origin_index}] missing keys: {sorted(missing)}"
            )
            continue
        repo = origin.get("repo")
        is_local = isinstance(repo, str) and repo.startswith("local-repo/")
        if not is_local and (
            not isinstance(repo, str)
            or not GITHUB_REPO_RE.fullmatch(repo)
            or repo.endswith(".git")
            or repo.rsplit("/", 1)[-1] in {".", ".."}
        ):
            errors.append(f"origins[{origin_index}] has invalid repo: {repo!r}")
        if is_local and repo != "local-repo/curation":
            errors.append(f"origins[{origin_index}] has invalid local repo")
        origin_path = origin.get("path")
        if origin_path is not None and not _safe_mapping_path(origin_path):
            errors.append(f"origins[{origin_index}] has unsafe path")
        license_value = origin.get("license")
        if not is_local and (
            not isinstance(license_value, str)
            or license_value not in PERMISSIVE_LICENSES
        ):
            errors.append(
                f"origins[{origin_index}] has no permitted external license"
            )
        mode = origin.get("sync_mode")
        if mode not in VALID_SYNC_MODES:
            errors.append(f"origins[{origin_index}] has invalid sync_mode")

        artifacts = origin.get("artifacts")
        if not isinstance(artifacts, list) or (not artifacts and not is_local):
            errors.append(f"origins[{origin_index}] has no artifact inventory")
            artifacts = []
        for artifact_index, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict):
                errors.append(
                    f"origins[{origin_index}].artifacts[{artifact_index}] "
                    "must be an object"
                )
                continue
            source = artifact.get("source")
            target = artifact.get("target")
            artifact_type = artifact.get("type", "file")
            if (
                not _safe_mapping_path(source)
                or not _safe_mapping_path(target)
                or artifact_type not in {"file", "directory"}
            ):
                errors.append(
                    f"origins[{origin_index}].artifacts[{artifact_index}] "
                    "is invalid"
                )
                continue
            target_path = PurePosixPath(str(target))
            if not (
                target_path.is_relative_to(skill_root)
                or (
                    artifact_type == "directory"
                    and target_path == skill_root
                )
            ):
                errors.append(
                    f"origins[{origin_index}].artifacts[{artifact_index}] "
                    "escapes the canonical skill root"
                )
            for managed_path in artifact_owners:
                if _artifact_owns_target(artifact, managed_path):
                    artifact_owners[managed_path] += 1

        tracking = origin.get("tracking")
        if not isinstance(tracking, dict):
            errors.append(f"origins[{origin_index}] tracking must be an object")
            continue
        tracking_missing = {
            "channel",
            "ref",
            "resolved_commit",
            "path_commit",
            "content_sha256",
            "last_checked_at",
            "last_synced_at",
        } - set(tracking)
        if tracking_missing:
            errors.append(
                f"origins[{origin_index}] tracking missing keys: "
                f"{sorted(tracking_missing)}"
            )
            continue
        channel = tracking.get("channel")
        ref = tracking.get("ref")
        owns_canonical = any(
            isinstance(artifact, dict)
            and _artifact_owns_target(artifact, str(repo_skill))
            for artifact in artifacts
        )
        archived_sidecar = is_archived_sidecar(
            origin, repo_skill, entry.get("kind")
        )
        if (
            not is_local
            and entry.get("kind") in {"mirror", "overlay"}
            and mode == "archived"
            and not owns_canonical
            and not archived_sidecar
        ):
            errors.append(
                f"origins[{origin_index}] archived sidecar requires safe "
                "non-canonical files and a fixed ref matching resolved_commit"
            )
        if not is_local and not archived_sidecar:
            external_modes.append(str(mode))
        if channel not in VALID_CHANNELS:
            errors.append(f"origins[{origin_index}] has invalid channel")
        if (
            not isinstance(ref, str)
            or not ref
            or len(ref) > 1024
            or any(ord(character) < 0x20 for character in ref)
        ):
            errors.append(f"origins[{origin_index}] has invalid ref")
        if is_local != (channel == "local"):
            errors.append(f"origins[{origin_index}] channel/repo semantics conflict")
        if channel == "fixed_ref" and (
            not isinstance(ref, str) or not COMMIT_RE.fullmatch(ref)
        ):
            errors.append(f"origins[{origin_index}] fixed_ref is not immutable")
        for field in ("resolved_commit", "path_commit"):
            value = tracking.get(field)
            if value is not None and (
                not isinstance(value, str) or not COMMIT_RE.fullmatch(value)
            ):
                errors.append(f"origins[{origin_index}] has invalid {field}")
        content_hash = tracking.get("content_sha256")
        if content_hash is not None and (
            not isinstance(content_hash, str)
            or not SHA256_RE.fullmatch(content_hash)
        ):
            errors.append(
                f"origins[{origin_index}] has invalid content_sha256"
            )
        if (
            any(
                isinstance(artifact, dict)
                and _artifact_owns_target(artifact, str(repo_skill))
                for artifact in artifacts
            )
            and str(repo_skill) in managed_by_path
            and isinstance(content_hash, str)
            and content_hash.lower()
            != str(managed_by_path[str(repo_skill)].get("sha256", "")).lower()
        ):
            errors.append(
                f"origins[{origin_index}] content_sha256 does not match repo_skill"
            )
        for field in ("last_checked_at", "last_synced_at"):
            value = tracking.get(field)
            if value is not None and (
                not isinstance(value, str) or not DATE_RE.fullmatch(value)
            ):
                errors.append(f"origins[{origin_index}] has invalid {field}")
        license_checkpoint = tracking.get("license_checkpoint")
        if license_checkpoint is not None:
            if is_local or not isinstance(license_checkpoint, dict):
                errors.append(
                    f"origins[{origin_index}] has invalid license_checkpoint"
                )
            else:
                expected_keys = {
                    "path",
                    "blob_sha",
                    "content_sha256",
                    "spdx",
                    "resolved_commit",
                }
                allowed_keys = expected_keys | {"api_spdx"}
                if set(license_checkpoint) - allowed_keys:
                    errors.append(
                        f"origins[{origin_index}] license_checkpoint "
                        "contains unknown fields"
                    )
                if not _safe_mapping_path(license_checkpoint.get("path")):
                    errors.append(
                        f"origins[{origin_index}] license_checkpoint path "
                        "is invalid"
                    )
                if not isinstance(
                    license_checkpoint.get("blob_sha"), str
                ) or not COMMIT_RE.fullmatch(
                    str(license_checkpoint.get("blob_sha"))
                ):
                    errors.append(
                        f"origins[{origin_index}] license_checkpoint "
                        "blob_sha is invalid"
                    )
                if not isinstance(
                    license_checkpoint.get("content_sha256"), str
                ) or not SHA256_RE.fullmatch(
                    str(license_checkpoint.get("content_sha256"))
                ):
                    errors.append(
                        f"origins[{origin_index}] license_checkpoint "
                        "content_sha256 is invalid"
                    )
                if license_checkpoint.get("spdx") != license_value:
                    errors.append(
                        f"origins[{origin_index}] license_checkpoint SPDX "
                        "does not match origin license"
                    )
                if not isinstance(
                    license_checkpoint.get("resolved_commit"), str
                ) or not COMMIT_RE.fullmatch(
                    str(license_checkpoint.get("resolved_commit"))
                ):
                    errors.append(
                        f"origins[{origin_index}] license_checkpoint "
                        "resolved_commit is invalid"
                    )
                api_spdx = license_checkpoint.get("api_spdx")
                if api_spdx is not None and (
                    not isinstance(api_spdx, str)
                    or not api_spdx
                    or api_spdx != api_spdx.strip()
                    or len(api_spdx) > 128
                    or any(ord(character) < 0x20 for character in api_spdx)
                ):
                    errors.append(
                        f"origins[{origin_index}] license_checkpoint "
                        "api_spdx is invalid"
                    )
                elif api_spdx not in {None, "NOASSERTION", license_value}:
                    errors.append(
                        f"origins[{origin_index}] license_checkpoint "
                        "api_spdx conflicts with detected SPDX"
                    )

    if len(external_modes) != 1:
        errors.append(
            f"expected exactly one external origin, found {len(external_modes)}"
        )
    elif entry_mode != external_modes[0]:
        errors.append("entry/external origin sync_mode conflict")
    for path, owners in artifact_owners.items():
        if owners != 1:
            errors.append(
                f"managed file {path!r} must have exactly one artifact owner; "
                f"found {owners}"
            )
    if str(repo_skill) not in managed_by_path:
        errors.append("repo_skill is absent from managed_files")
    return errors


def _entry_origin_fingerprint(entry: dict, origin_index: int) -> str:
    try:
        selected_origin = entry["origins"][origin_index]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("cannot fingerprint malformed v2 entry") from exc

    def authority_origin(origin: object) -> object:
        if not isinstance(origin, dict):
            return origin
        tracking = origin.get("tracking")
        return {
            "repo": origin.get("repo"),
            "path": origin.get("path"),
            "license": origin.get("license"),
            "sync_mode": origin.get("sync_mode"),
            "artifacts": origin.get("artifacts"),
            "tracking": (
                {
                    "channel": tracking.get("channel"),
                    "ref": tracking.get("ref"),
                    "resolved_commit": tracking.get("resolved_commit"),
                    "path_commit": tracking.get("path_commit"),
                    "content_sha256": tracking.get("content_sha256"),
                    "license_checkpoint": tracking.get(
                        "license_checkpoint"
                    ),
                }
                if isinstance(tracking, dict)
                else tracking
            ),
        }

    authoritative = {
        "kind": entry.get("kind"),
        "status": entry.get("status"),
        "normalized_slug": entry.get("normalized_slug"),
        "repo_skill": entry.get("repo_skill"),
        "entry_sync_mode": entry.get("sync_mode"),
        "selected_origin_index": origin_index,
        "selected_origin": authority_origin(selected_origin),
        "all_origins": [
            authority_origin(origin) for origin in entry.get("origins", [])
        ],
        "managed_files": entry.get("managed_files"),
    }
    encoded = json.dumps(
        authoritative,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _v2_loaded_skill(entry: dict, mapping_path: Path, entry_index: int) -> dict | None:
    """Load one v2 entry from its unique active external origin.

    Legacy ``upstream`` fields are compatibility output, never authority.  All
    source-to-target ownership comes from the selected origin's artifacts.
    """
    kind = entry.get("kind")
    status = entry.get("status")
    if status not in {"verified_in_repo", "in_house"}:
        return None
    if kind in {"in_house", "reference_only", "composite", "bundle"}:
        return None

    identity = _mapping_identity(entry, mapping_path, entry_index)
    repo_skill = entry.get("repo_skill")
    if not _safe_mapping_path(repo_skill):
        return {
            **identity,
            "schema_version": 2,
            "source": "provenance:v2",
            "repo": "",
            "load_error": f"v2 repo_skill is not a safe relative path: {repo_skill!r}",
        }
    structural_errors = _v2_sync_entry_errors(entry)
    if structural_errors:
        return {
            **identity,
            "schema_version": 2,
            "source": "provenance:v2",
            "repo": "",
            "load_error": "invalid v2 sync entry: " + "; ".join(structural_errors),
        }
    origins = entry.get("origins")
    if kind == "snapshot":
        if not identity["local_path"].is_file():
            return {
                **identity,
                "schema_version": 2,
                "source": "provenance:v2",
                "repo": "",
                "load_error": f"mapped local skill is missing: {repo_skill}",
            }
        external_origins = [
            (index, origin)
            for index, origin in enumerate(origins or [])
            if isinstance(origin, dict)
            and isinstance(origin.get("repo"), str)
            and not origin["repo"].startswith("local-repo/")
        ]
        if len(external_origins) != 1:
            return {
                **identity,
                "schema_version": 2,
                "source": "provenance:v2",
                "repo": "",
                "load_error": (
                    "v2 snapshot requires exactly one external lineage origin; "
                    f"found {len(external_origins)}"
                ),
            }
        origin_index, origin = external_origins[0]
        repo = origin["repo"]
        return {
            **identity,
            "schema_version": 2,
            "kind": "snapshot",
            "source": f"github:{repo}",
            "repo": repo,
            "sync_mode": origin.get("sync_mode") or entry.get("sync_mode"),
            "mapping_path": mapping_path,
            "mapping_entry_index": entry_index,
            "origin_index": origin_index,
            "mapping_fingerprint": _entry_origin_fingerprint(
                entry, origin_index
            ),
            "expected_skip_reason": (
                "licensed immutable snapshot; automatic upstream checking is "
                "disabled by provenance policy"
            ),
        }

    origin_candidates: list[tuple[int, dict]] = []
    if isinstance(origins, list):
        for origin_index, origin in enumerate(origins):
            if not isinstance(origin, dict):
                continue
            repo = origin.get("repo")
            sync_mode = origin.get("sync_mode")
            if (
                isinstance(repo, str)
                and not repo.startswith("local-repo/")
                and sync_mode not in {"archived", "local-only"}
            ):
                origin_candidates.append((origin_index, origin))

    if len(origin_candidates) != 1:
        return {
            **identity,
            "schema_version": 2,
            "source": "provenance:v2",
            "repo": "",
            "load_error": (
                "v2 provenance requires exactly one active external origin; "
                f"found {len(origin_candidates)}"
            ),
        }

    origin_index, origin = origin_candidates[0]
    tracking = origin.get("tracking")
    repo = origin.get("repo")
    origin_path = origin.get("path")
    artifacts = origin.get("artifacts")
    sync_mode = origin.get("sync_mode")
    ref = tracking.get("ref") if isinstance(tracking, dict) else None
    required = {
        "origin.repo": repo,
        "origin.sync_mode": sync_mode,
        "origin.tracking.ref": ref,
    }
    missing = [key for key, value in required.items() if not isinstance(value, str) or not value]
    if missing:
        return {
            **identity,
            "schema_version": 2,
            "source": "provenance:v2",
            "repo": repo if isinstance(repo, str) else "",
            "load_error": "v2 owner metadata is incomplete: " + ", ".join(missing),
        }
    if (
        not re.fullmatch(r"[^/\s]+/[^/\s]+", repo)
        or (origin_path is not None and not _safe_mapping_path(origin_path))
    ):
        return {
            **identity,
            "schema_version": 2,
            "source": "provenance:v2",
            "repo": "",
            "load_error": "v2 owner contains an unsafe repo or artifact path",
        }

    if not isinstance(artifacts, list) or not artifacts:
        return {
            **identity,
            "schema_version": 2,
            "source": f"github:{repo}",
            "repo": repo,
            "load_error": "v2 external origin has no declared artifacts",
        }
    invalid_artifacts = [
        artifact
        for artifact in artifacts
        if not isinstance(artifact, dict)
        or artifact.get("type", "file") not in {"file", "directory"}
        or not _safe_mapping_path(artifact.get("source"))
        or not _safe_mapping_path(artifact.get("target"))
    ]
    if invalid_artifacts:
        return {
            **identity,
            "schema_version": 2,
            "source": f"github:{repo}",
            "repo": repo,
            "load_error": "v2 external origin contains an invalid artifact mapping",
        }

    repo_skill_owners = [
        artifact
        for artifact in artifacts
        if _artifact_source_for_target(artifact, str(repo_skill)) is not None
    ]
    if len(repo_skill_owners) != 1:
        return {
            **identity,
            "schema_version": 2,
            "source": "provenance:v2",
            "repo": "",
            "load_error": (
                "v2 provenance requires exactly one origin/artifact owner for "
                f"{repo_skill!r}; found {len(repo_skill_owners)}"
            ),
        }
    upstream_path = _artifact_source_for_target(repo_skill_owners[0], str(repo_skill))

    local_path = identity["local_path"]
    if not local_path.is_file():
        return {
            **identity,
            "schema_version": 2,
            "source": f"github:{repo}",
            "repo": repo,
            "load_error": f"mapped local skill is missing: {repo_skill}",
        }

    content = local_path.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(content)
    other_origin_artifacts: list[dict] = []
    for other_index, other_origin in enumerate(origins):
        if other_index == origin_index or not isinstance(other_origin, dict):
            continue
        other_artifacts = other_origin.get("artifacts")
        if isinstance(other_artifacts, list):
            other_origin_artifacts.extend(
                copy.deepcopy(item)
                for item in other_artifacts
                if isinstance(item, dict)
            )
    return {
        **identity,
        "name": fm.get("name", identity["name"]),
        "schema_version": 2,
        "kind": kind,
        "source": f"github:{repo}",
        "repo": repo,
        "local_content": content,
        "upstream_path": upstream_path,
        "origin_path": origin_path,
        "ref": ref,
        "sync_mode": sync_mode,
        "tracking": copy.deepcopy(tracking),
        "license": origin.get("license"),
        "artifacts": copy.deepcopy(artifacts),
        "other_origin_artifacts": other_origin_artifacts,
        "managed_files": copy.deepcopy(entry.get("managed_files", [])),
        "repo_skill": repo_skill,
        "owner": entry.get("normalized_slug") or identity["name"],
        "last_synced_commit": (
            tracking.get("resolved_commit") if isinstance(tracking, dict) else None
        ),
        "path_commit": (
            tracking.get("path_commit") if isinstance(tracking, dict) else None
        ),
        "origin_index": origin_index,
        "artifact_index": artifacts.index(repo_skill_owners[0]),
        "mapping_fingerprint": _entry_origin_fingerprint(entry, origin_index),
    }


def _v1_loaded_skill(entry: dict, mapping_path: Path, entry_index: int) -> dict | None:
    """Load a legacy v1 entry from its legacy ``upstream`` fields."""
    upstream = entry.get("upstream") or {}
    repo = upstream.get("repo")
    repo_skill = entry.get("repo_skill")
    upstream_path = upstream.get("path")
    if upstream.get("sync_mode") in {"archived", "local-only"}:
        return None
    if not repo or repo.startswith("local-repo/") or not repo_skill or not upstream_path:
        return None
    if not _safe_mapping_path(repo_skill) or not _safe_mapping_path(upstream_path):
        identity = _mapping_identity(entry, mapping_path, entry_index)
        return {
            **identity,
            "schema_version": 1,
            "source": f"github:{repo}",
            "repo": repo,
            "load_error": "legacy mapping contains an unsafe local or upstream path",
        }

    identity = _mapping_identity(entry, mapping_path, entry_index)
    local_path = identity["local_path"]
    if not local_path.is_file():
        return {
            **identity,
            "schema_version": 1,
            "source": f"github:{repo}",
            "repo": repo,
            "load_error": f"mapped local skill is missing: {repo_skill}",
        }
    content = local_path.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(content)
    return {
        **identity,
        "name": fm.get("name", identity["name"]),
        "schema_version": 1,
        "source": f"github:{repo}",
        "repo": repo,
        "local_content": content,
        "upstream_path": upstream_path,
        "ref": upstream.get("ref", "main"),
        "sync_mode": upstream.get("sync_mode", "replace"),
        "last_synced_commit": upstream.get("last_synced_commit"),
    }


def _mapping_unavailable_skill(
    entry: object,
    mapping_path: Path,
    entry_index: int,
    schema_version: object,
    reason: str,
) -> dict:
    identity = (
        _mapping_identity(entry, mapping_path, entry_index)
        if isinstance(entry, dict)
        else {
            "name": f"{mapping_path.stem}:entry-{entry_index}",
            "category": "unknown",
            "local_path": REPO_ROOT,
            "mapping_path": mapping_path,
            "mapping_entry_index": entry_index,
        }
    )
    return {
        **identity,
        "schema_version": schema_version,
        "source": "provenance:invalid-schema",
        "repo": "",
        "load_error": reason,
    }


def load_skills_from_source_mappings(*, allow_v1: bool = False) -> list[dict]:
    """Load source mappings without implicit schema downgrade.

    Strict integer schema v2 is the default.  Headerless or integer-v1 legacy
    mappings are read only when the caller explicitly opts in.
    """
    results = []
    for mapping_path in sorted(SOURCE_MAPPINGS_DIR.glob("*.skills.json")):
        try:
            data = json.loads(mapping_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            results.append(
                _mapping_unavailable_skill(
                    None,
                    mapping_path,
                    0,
                    None,
                    f"could not parse provenance mapping: {exc}",
                )
            )
            continue
        if not isinstance(data, dict):
            results.append(
                _mapping_unavailable_skill(
                    None,
                    mapping_path,
                    0,
                    None,
                    "provenance mapping top level must be an object",
                )
            )
            continue
        schema_version = data.get("schema_version")
        entries = data.get("skills", [])
        if not isinstance(entries, list):
            results.append(
                _mapping_unavailable_skill(
                    None,
                    mapping_path,
                    0,
                    schema_version,
                    "provenance mapping skills must be an array",
                )
            )
            continue
        if not entries:
            results.append(
                _mapping_unavailable_skill(
                    None,
                    mapping_path,
                    0,
                    schema_version,
                    "provenance mapping skills must not be empty",
                )
            )
            continue
        strict_v2 = type(schema_version) is int and schema_version == 2
        explicit_v1 = allow_v1 and (
            schema_version is None
            or (type(schema_version) is int and schema_version == 1)
        )
        for entry_index, entry in enumerate(entries):
            if not strict_v2 and not explicit_v1:
                results.append(
                    _mapping_unavailable_skill(
                        entry,
                        mapping_path,
                        entry_index,
                        schema_version,
                        "unsupported provenance schema_version "
                        f"{schema_version!r}; strict integer 2 is required",
                    )
                )
                continue
            if not isinstance(entry, dict):
                results.append(
                    _mapping_unavailable_skill(
                        entry,
                        mapping_path,
                        entry_index,
                        schema_version,
                        "provenance skill entry must be an object",
                    )
                )
                continue
            if strict_v2:
                loaded = _v2_loaded_skill(entry, mapping_path, entry_index)
            else:
                loaded = _v1_loaded_skill(entry, mapping_path, entry_index)
            if loaded is not None:
                results.append(loaded)
    return results


def load_all_mapped_paths() -> set[Path]:
    """Return every mapped path, including invalid and non-syncable v2 entries."""
    paths: set[Path] = set()
    for mapping_path in sorted(SOURCE_MAPPINGS_DIR.glob("*.skills.json")):
        try:
            data = json.loads(mapping_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or not isinstance(data.get("skills"), list):
            continue
        for entry in data["skills"]:
            if not isinstance(entry, dict):
                continue
            repo_skill = entry.get("repo_skill")
            if _safe_mapping_path(repo_skill):
                paths.add((REPO_ROOT / repo_skill).resolve())
    return paths


def load_non_syncable_mapped_paths() -> set[Path]:
    """Backward-compatible alias for the complete mapped-path exclusion set."""
    return load_all_mapped_paths()


def load_skills_with_upstream(*, allow_v1: bool = False) -> list[dict]:
    """Load skills that have external upstream sources.

    Prefer exact paths from docs/sources/*.skills.json, then fall back to
    frontmatter-only github sources that are not yet mapped.
    """
    mapped = load_skills_from_source_mappings(allow_v1=allow_v1)
    mapped_paths = load_all_mapped_paths()
    results = []
    for skill_md in sorted(SKILLS_DIR.glob("*/*/SKILL.md")):
        if skill_md.resolve() in mapped_paths:
            continue
        content = skill_md.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(content)
        source = fm.get("source", "in-house")
        
        # Only process skills with external sources
        if source.startswith("github:"):
            repo = source.replace("github:", "")
            skill_name = fm.get("name", skill_md.parent.name)
            source_url = fm.get("source_url", "")
            if not allow_v1:
                results.append(
                    {
                        "name": skill_name,
                        "category": skill_md.parent.parent.name,
                        "source": source,
                        "repo": repo,
                        "local_path": skill_md,
                        "local_content": content,
                        "schema_version": None,
                        "load_error": (
                            "unmapped GitHub skill lacks strict provenance v2; "
                            "legacy frontmatter fallback is disabled"
                        ),
                    }
                )
                continue
            source_url_path = github_path_from_source_url(source_url, repo)
            if not source_url_path and source_url.startswith("https://skills.sh/"):
                continue
            if not source_url_path and source_url.rstrip("/") == f"https://github.com/{repo}":
                continue
            results.append({
                "name": skill_name,
                "category": skill_md.parent.parent.name,
                "source": source,
                "repo": repo,
                "local_path": skill_md,
                "source_url": source_url,
                "local_content": content,
                "source_url_path": source_url_path,
                "ref": "main",
                "schema_version": 1,
            })
        elif source in ("skills.sh", "clawhub", "community"):
            # These don't have auto-syncable upstreams yet
            pass
    return mapped + results


def _check_legacy_upstream_changes(skill: dict, token: str | None) -> dict | None:
    """Legacy v1 single-file checker retained behind explicit ``--allow-v1``."""
    if skill.get("load_error"):
        return {
            "skill": skill,
            "changes": "unavailable",
            "reason": skill["load_error"],
        }
    token = _github_token_for(token)

    repo = skill["repo"]
    skill_name = skill["name"]

    if skill.get("sync_mode") == "monitor":
        if not skill.get("last_synced_commit"):
            return {
                "skill": skill,
                "upstream_path": skill.get("upstream_path"),
                "changes": "unavailable",
                "reason": "monitor-only source has no reviewed commit checkpoint",
            }
        current_commit = github_commit_sha(repo, skill.get("ref", "main"), token)
        if not current_commit:
            return {
                "skill": skill,
                "upstream_path": skill.get("upstream_path"),
                "changes": "unavailable",
                "reason": "could not resolve monitor-only upstream head",
            }
        if current_commit == skill["last_synced_commit"]:
            return {
                "skill": skill,
                "upstream_path": skill.get("upstream_path"),
                "changes": "none",
            }
        relation = github_compare_relation(
            repo,
            skill["last_synced_commit"],
            current_commit,
            token,
        )
        if relation is None:
            return {
                "skill": skill,
                "upstream_path": skill.get("upstream_path"),
                "changes": "unavailable",
                "current_commit": current_commit,
                "reason": "could not resolve monitor-only checkpoint relationship",
            }
        if relation["status"] == "behind":
            return {
                "skill": skill,
                "upstream_path": skill.get("upstream_path"),
                "changes": "upstream_rollback",
                "current_commit": current_commit,
                "ahead_by": relation["ahead_by"],
                "behind_by": relation["behind_by"],
            }
        # Only exact checkpoint identity is equal.  A new/diverged/aliased head
        # requires review even when SKILL.md happens to have the same body,
        # because sidecars, dependencies, or release metadata may have changed.
        return {
            "skill": skill,
            "upstream_path": skill.get("upstream_path"),
            "changes": "monitor_review",
            "current_commit": current_commit,
            "relation": relation["status"],
            "ahead_by": relation["ahead_by"],
            "behind_by": relation["behind_by"],
        }
    
    # Prefer exact provenance paths. Fallbacks support older frontmatter-only entries.
    if skill.get("upstream_path"):
        candidate_paths = [skill["upstream_path"]]
    elif skill.get("source_url_path"):
        candidate_paths = [skill["source_url_path"]]
    else:
        candidate_paths = [
            f"skills/{skill_name}/SKILL.md",
            f"skills/{skill['category']}/{skill_name}/SKILL.md",
            f"{skill_name}/SKILL.md",
        ]
    
    for path in candidate_paths:
        url = github_raw_url(repo, path, skill.get("ref", "main"))
        try:
            upstream_content = fetch_url(
                url,
                token,
                quiet_404=len(candidate_paths) > 1 and path != candidate_paths[-1],
            )
        except TypeError:
            upstream_content = fetch_url(url, token)
        if upstream_content is not None:
            upstream_content = apply_repository_adaptations(upstream_content, skill)
            # Compare content (ignore frontmatter for diff)
            local_body = comparable_body(skill["local_content"])
            upstream_body = comparable_body(upstream_content)
            
            if local_body != upstream_body:
                return {
                    "skill": skill,
                    "upstream_path": path,
                    "upstream_content": upstream_content,
                    "changes": "body_changed",
                }
            else:
                return {
                    "skill": skill,
                    "upstream_path": path,
                    "upstream_content": upstream_content,
                    "changes": "none",
                }
    
    return {
        "skill": skill,
        "changes": "unavailable",
        "reason": (
            "could not fetch any authoritative upstream path: "
            + ", ".join(candidate_paths)
        ),
    }


def _provider_for(token: str | None) -> GitHubArtifactProvider:
    global _ACTIVE_ARTIFACT_PROVIDER
    if _ACTIVE_ARTIFACT_PROVIDER is None:
        _ACTIVE_ARTIFACT_PROVIDER = GitHubArtifactProvider(
            _github_token_for(token)
        )
    return _ACTIVE_ARTIFACT_PROVIDER


def _github_token_for(token: str | None) -> str | None:
    if token is not None:
        return token
    global _ACTIVE_GITHUB_TOKEN
    if _ACTIVE_GITHUB_TOKEN is _TOKEN_UNRESOLVED:
        _ACTIVE_GITHUB_TOKEN = resolve_github_token()
    return (
        _ACTIVE_GITHUB_TOKEN
        if isinstance(_ACTIVE_GITHUB_TOKEN, str)
        else None
    )


def detected_license_spdx(
    evidence: LicenseEvidence,
) -> tuple[str | None, str | None]:
    """Prefer explicit GitHub SPDX; otherwise require one canonical text match."""
    if evidence.api_spdx not in {None, "NOASSERTION"}:
        return evidence.api_spdx, None
    candidates = evidence.spdx_candidates
    if len(candidates) != 1:
        return (
            None,
            "license review required: immutable license content produced "
            f"{len(candidates)} canonical SPDX matches "
            f"{list(candidates)!r}",
        )
    return candidates[0], None


def license_checkpoint(evidence: LicenseEvidence) -> dict[str, str]:
    """Serialize one uniquely classified immutable license observation."""
    detected, error = detected_license_spdx(evidence)
    if error is not None or detected is None:
        raise RuntimeError(error or "license evidence has no SPDX result")
    checkpoint = {
        "path": evidence.path,
        "blob_sha": evidence.blob_sha,
        "content_sha256": evidence.content_sha256,
        "spdx": detected,
        "resolved_commit": evidence.resolved_commit,
    }
    if evidence.api_spdx is not None:
        checkpoint["api_spdx"] = evidence.api_spdx
    return checkpoint


def validate_license_evidence(
    declared_spdx: object,
    evidence: LicenseEvidence,
) -> tuple[dict[str, str] | None, str | None]:
    """Validate commit-bound evidence against one declared SPDX identifier."""
    detected, detection_error = detected_license_spdx(evidence)
    if detection_error is not None or detected is None:
        return None, detection_error or "license evidence has no SPDX result"
    if detected not in PERMISSIVE_LICENSES:
        return (
            None,
            f"license review required: detected SPDX {detected!r} is not permitted",
        )
    if declared_spdx != detected:
        return (
            None,
            "license review required: detected SPDX "
            f"{detected!r} does not match origin.license "
            f"{declared_spdx!r}",
        )
    return license_checkpoint(evidence), None


def _license_checkpoint(evidence: LicenseEvidence) -> dict[str, str]:
    """Backward-compatible private alias for older callers and tests."""
    return license_checkpoint(evidence)


def _validate_license_evidence(
    skill: dict,
    evidence: LicenseEvidence,
) -> tuple[dict[str, str] | None, str | None]:
    """Validate current evidence and retain the sync drift policy."""
    checkpoint, error = validate_license_evidence(
        skill.get("license"),
        evidence,
    )
    if error is not None or checkpoint is None:
        return checkpoint, error
    previous = (skill.get("tracking") or {}).get("license_checkpoint")
    if isinstance(previous, dict):
        immutable_fields = ("path", "blob_sha", "content_sha256", "spdx")
        changed = [
            field
            for field in immutable_fields
            if previous.get(field) != checkpoint.get(field)
        ]
        if changed:
            return (
                None,
                "license review required: immutable license evidence changed: "
                + ", ".join(changed),
            )
    return checkpoint, None


def _artifact_local_bytes(skill: dict, target: str) -> bytes | None:
    if not _safe_mapping_path(target):
        return None
    path = (REPO_ROOT / target).resolve()
    try:
        path.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return None
    try:
        return path.read_bytes()
    except OSError:
        return None


def _artifact_local_mode(target: str) -> str | None:
    if not _safe_mapping_path(target):
        return None
    path = REPO_ROOT / target
    try:
        metadata = path.lstat()
    except OSError:
        return None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        return None
    return "100755" if stat.S_IMODE(metadata.st_mode) & 0o111 else "100644"


def _main_artifact_equal(skill: dict, local: bytes, upstream: bytes) -> bool:
    try:
        local_text = local.decode("utf-8")
        upstream_text = upstream.decode("utf-8")
    except UnicodeDecodeError:
        return local == upstream
    upstream_text = apply_repository_adaptations(upstream_text, skill)
    if comparable_body(local_text) != comparable_body(upstream_text):
        return False
    return _upstream_frontmatter_contract(
        local_text
    ) == _upstream_frontmatter_contract(upstream_text)


def _artifact_diff(
    skill: dict,
    upstream_files: dict[str, bytes],
    upstream_modes: dict[str, str],
) -> tuple[list[str], list[str], list[str]]:
    if set(upstream_modes) != set(upstream_files) or any(
        mode not in {"100644", "100755"} for mode in upstream_modes.values()
    ):
        raise RuntimeError("upstream artifact modes are incomplete or invalid")
    desired = set(upstream_files)
    previous_external_targets = _owned_targets_for_artifacts(
        skill.get("artifacts", []),
        skill.get("managed_files", []),
    )
    protected_targets = _owned_targets_for_artifacts(
        skill.get("other_origin_artifacts", []),
        skill.get("managed_files", []),
    )
    owned = previous_external_targets - protected_targets
    # Ownership, not incidental disk equality, determines additions/removals.
    # This ensures an unowned same-byte file still requires safe adoption and a
    # missing formerly owned file is still reflected in the inventory delta.
    added = sorted(desired - owned)
    removed = sorted(owned - desired)
    changed: list[str] = []
    repo_skill = skill.get("repo_skill")
    manifest_hashes = {
        item.get("path"): item.get("sha256")
        for item in skill.get("managed_files", [])
        if isinstance(item, dict)
    }
    manifest_modes = {
        item.get("path"): item.get("mode")
        for item in skill.get("managed_files", [])
        if isinstance(item, dict)
    }
    for path in sorted(desired & owned):
        raw = _artifact_local_bytes(skill, path)
        upstream = upstream_files[path]
        expected = manifest_hashes.get(path)
        local_mode = _artifact_local_mode(path)
        upstream_mode = upstream_modes[path]
        expected_mode = manifest_modes.get(path)
        content_changed = (
            raw is None
            or (
                not _main_artifact_equal(skill, raw, upstream)
                if path == repo_skill
                else raw != upstream
            )
        )
        manifest_drift = (
            raw is not None
            and isinstance(expected, str)
            and hashlib.sha256(raw).hexdigest() != expected.lower()
        )
        mode_changed = local_mode != upstream_mode
        mode_manifest_drift = (
            local_mode is not None
            and isinstance(expected_mode, str)
            and local_mode != expected_mode
        )
        if content_changed or manifest_drift or mode_changed or mode_manifest_drift:
            changed.append(path)
    return changed, added, removed


def _owned_targets_for_artifacts(
    artifacts: list[dict],
    managed_files: list[dict],
) -> set[str]:
    """Expand prior artifact ownership only across manifest-owned files."""
    managed_paths = {
        item.get("path") if isinstance(item, dict) else item
        for item in managed_files
    }
    managed_paths = {path for path in managed_paths if isinstance(path, str)}
    owned: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        target = artifact.get("target")
        if not isinstance(target, str):
            continue
        if artifact.get("type", "file") == "file":
            if target in managed_paths:
                owned.add(target)
            continue
        prefix = target.rstrip("/") + "/"
        owned.update(path for path in managed_paths if path.startswith(prefix))
    return owned


def _local_source_bytes_for_missing(
    skill: dict,
    missing_sources: list[str],
) -> dict[str, bytes]:
    values: dict[str, bytes] = {}
    for source in missing_sources:
        for artifact in skill.get("artifacts", []):
            if not isinstance(artifact, dict) or artifact.get("source") != source:
                continue
            target = artifact.get("target")
            if artifact.get("type", "file") == "file" and isinstance(target, str):
                raw = _artifact_local_bytes(skill, target)
                if raw is not None:
                    values[source] = raw
    return values


def _check_v2_upstream_changes(
    skill: dict,
    token: str | None,
) -> dict:
    tracking = skill.get("tracking")
    if not isinstance(tracking, dict):
        return {
            "skill": skill,
            "changes": "unavailable",
            "reason": "v2 origin has no tracking object",
        }
    channel = tracking.get("channel")
    monitor_only = (
        channel in MONITOR_CHANNELS
        or skill.get("sync_mode") == "monitor"
    )
    tracking_checkpoint = tracking.get("resolved_commit")
    legacy_checkpoint = skill.get("last_synced_commit")
    reviewed_checkpoint = (
        tracking_checkpoint
        if isinstance(tracking_checkpoint, str)
        and COMMIT_RE.fullmatch(tracking_checkpoint)
        else legacy_checkpoint
        if isinstance(legacy_checkpoint, str)
        and COMMIT_RE.fullmatch(legacy_checkpoint)
        else None
    )
    if skill.get("sync_mode") == "manual":
        return {
            "skill": skill,
            "changes": "expected_skipped",
            "reason": "external origin is explicitly manual",
        }
    if monitor_only:
        missing_checkpoint = []
        if reviewed_checkpoint is None:
            missing_checkpoint.append("resolved_commit")
        path_checkpoint = tracking.get("path_commit")
        if not (
            isinstance(path_checkpoint, str)
            and COMMIT_RE.fullmatch(path_checkpoint)
        ):
            missing_checkpoint.append("path_commit")
        content_sha = tracking.get("content_sha256")
        if not (
            isinstance(content_sha, str)
            and re.fullmatch(r"[0-9a-fA-F]{64}", content_sha)
        ):
            missing_checkpoint.append("content_sha256")
        if missing_checkpoint:
            return {
                "skill": skill,
                "changes": "unavailable",
                "reason": (
                    "monitor-only v2 source has no complete reviewed checkpoint: "
                    + ", ".join(missing_checkpoint)
                ),
            }

    provider = _provider_for(token)
    try:
        resolved = provider.resolve_tracking(skill["repo"], tracking)
        license_evidence = provider.license_evidence(
            skill["repo"], resolved.commit
        )
        license_checkpoint, license_error = _validate_license_evidence(
            skill, license_evidence
        )
        if license_error is not None or license_checkpoint is None:
            return {
                "skill": skill,
                "changes": "unavailable",
                "reason": license_error or "license evidence is unavailable",
                "resolved_ref": resolved.ref,
                "current_commit": resolved.commit,
            }
        current_commit = resolved.commit.lower()
        if license_checkpoint.get("resolved_commit") != current_commit:
            return {
                "skill": skill,
                "changes": "unavailable",
                "reason": (
                    "license review required: immutable license evidence is "
                    "not bound to the resolved upstream commit"
                ),
                "resolved_ref": resolved.ref,
                "current_commit": current_commit,
            }
        checkpoint = reviewed_checkpoint
        relation = None
        checkpoint_matches_current = bool(
            monitor_only
            and checkpoint
            and checkpoint.lower() == current_commit
        )
        if checkpoint and checkpoint.lower() != current_commit:
            relation = provider.compare(
                skill["repo"], checkpoint.lower(), current_commit
            )
            if relation["status"] == "behind":
                path = skill.get("origin_path") or skill.get("upstream_path")
                rollback_path_commit = provider.path_commit(
                    skill["repo"], current_commit, str(path)
                )
                return {
                    "skill": skill,
                    "changes": "upstream_rollback",
                    "resolved_ref": resolved.ref,
                    "current_commit": current_commit,
                    "path_commit": rollback_path_commit,
                    "license_evidence": license_checkpoint,
                    "ahead_by": relation["ahead_by"],
                    "behind_by": relation["behind_by"],
                }

        inventory = provider.fetch_artifacts(
            skill["repo"],
            tracking,
            skill["artifacts"],
        )
        path = skill.get("origin_path") or skill.get("upstream_path")
        path_commit = provider.path_commit(
            skill["repo"], inventory.resolved.commit, str(path)
        )
    except ArtifactNotFound as exc:
        try:
            resolved = provider.resolve_tracking(skill["repo"], tracking)
            moved = provider.moved_candidates(
                skill["repo"],
                skill.get("last_synced_commit"),
                resolved.commit,
                exc.missing_sources,
                local_files=_local_source_bytes_for_missing(
                    skill, exc.missing_sources
                ),
            )
        except GitHubProviderError:
            moved = {}
            resolved = None
        return {
            "skill": skill,
            "changes": "unavailable",
            "reason": str(exc),
            "moved_candidates": moved,
            "current_commit": resolved.commit if resolved else None,
            "resolved_ref": resolved.ref if resolved else None,
        }
    except GitHubProviderError as exc:
        return {
            "skill": skill,
            "changes": "unavailable",
            "reason": str(exc),
        }

    changed, added, removed = _artifact_diff(
        skill,
        inventory.files,
        inventory.modes,
    )
    artifact_changed = bool(changed or added or removed)
    checkpoint_changed = bool(
        reviewed_checkpoint
        and reviewed_checkpoint.lower() != inventory.resolved.commit.lower()
    )
    common = {
        "skill": skill,
        "upstream_path": skill.get("upstream_path"),
        "upstream_files": inventory.files,
        "source_blobs": inventory.source_blobs,
        "upstream_modes": inventory.modes,
        "main_source_blob": inventory.source_blobs.get(
            skill.get("upstream_path")
        ),
        "resolved_ref": inventory.resolved.ref,
        "current_commit": inventory.resolved.commit,
        "path_commit": path_commit,
        "license_evidence": license_checkpoint,
        "relation": relation["status"] if relation else "identical",
        "changed_files": changed,
        "added_files": added,
        "removed_files": removed,
    }
    if checkpoint_matches_current:
        # A monitor source is intentionally curated and need not byte-match the
        # upstream artifact set at its already reviewed commit. We still fetch
        # every declaration and refresh path_commit above so missing/moved
        # sources or an invalid immutable checkpoint remain fail-closed.
        return {**common, "changes": "none"}
    if monitor_only and (artifact_changed or checkpoint_changed):
        return {**common, "changes": "monitor_review"}
    if artifact_changed:
        return {**common, "changes": "artifact_changed"}
    return {**common, "changes": "none"}


def check_upstream_changes(skill: dict, token: str | None) -> dict | None:
    """Check every authoritative artifact for a skill."""
    if skill.get("load_error"):
        return {
            "skill": skill,
            "changes": "unavailable",
            "reason": skill["load_error"],
        }
    if skill.get("expected_skip_reason"):
        return {
            "skill": skill,
            "changes": "expected_skipped",
            "reason": skill["expected_skip_reason"],
        }
    if skill.get("schema_version") == 2:
        return _check_v2_upstream_changes(skill, token)
    return _check_legacy_upstream_changes(skill, token)


def monitor_review_guidance(update: dict) -> list[str]:
    """Return human-review guidance for monitor-only upstream changes.

    Monitor-only mappings are intentionally not auto-replaced because the local
    skill is curated from upstream rather than mirrored. Still, a changed
    upstream file is a maintenance task: reviewers must decide whether durable
    method, install, scoring, CI, or safety changes should be absorbed locally.
    """
    skill = update["skill"]
    repo = skill["repo"]
    ref = skill.get("ref", "main")
    last_synced_commit = skill.get("last_synced_commit")
    upstream_path = update.get("upstream_path") or skill.get("upstream_path")
    local_path = skill.get("local_path")
    compare_url = None
    if last_synced_commit:
        compare_url = f"https://github.com/{repo}/compare/{last_synced_commit}...{ref}"

    lines = [
        f"  - {skill['name']} requires manual monitor review.",
        f"    Local: {local_path}",
        f"    Upstream: https://github.com/{repo}/blob/{ref}/{upstream_path}",
    ]
    if compare_url:
        lines.append(f"    Compare: {compare_url}")
    lines.extend(
        [
            "    Review checklist:",
            "      * Identify durable method, install, scoring, CI, security, or compatibility changes.",
            "      * Ignore product telemetry, generated reports, dashboards, and bulk audit artifacts unless they change the reusable workflow.",
            "      * If local guidance changes, update the curated SKILL.md, bump version/updated_at, update provenance last_synced_commit, then run the full pipeline.",
            "      * If no local change is needed, record why in provenance verification_attempts or the automation memory.",
        ]
    )
    return lines


def _is_monitor_skill(skill: dict) -> bool:
    return (
        skill.get("sync_mode") == "monitor"
        or (skill.get("tracking") or {}).get("channel") in MONITOR_CHANNELS
    )


def print_monitor_review_guidance(updates: list[dict]) -> None:
    monitor_updates = [u for u in updates if _is_monitor_skill(u["skill"])]
    if not monitor_updates:
        return
    print("\nMONITOR-ONLY REVIEW REQUIRED:", flush=True)
    print(
        "These upstream changes are intentionally not auto-applied; they still need manual curation before the run is considered complete.",
        flush=True,
    )
    for update in monitor_updates:
        for line in monitor_review_guidance(update):
            print(line, flush=True)


def monitor_rollback_guidance(result: dict) -> list[str]:
    """Explain a monitor-only ref rollback without treating it as an update."""
    skill = result["skill"]
    behind_by = result.get("behind_by", "an unknown number of")
    return [
        f"  - {skill['name']} upstream ref moved backward by {behind_by} commits.",
        f"    Current head: {result.get('current_commit', 'unknown')}",
        f"    Reviewed checkpoint: {skill.get('last_synced_commit', 'unknown')}",
        "    Do not move the checkpoint backward or replace curated local guidance.",
        "    Record the rollback review in provenance and re-check when upstream advances.",
    ]


def print_monitor_rollbacks(results: list[dict]) -> None:
    """Print commit-aware warnings for monitored refs that moved backward."""
    rollbacks = [result for result in results if result.get("changes") == "upstream_rollback"]
    if not rollbacks:
        return
    print("\nMONITOR-ONLY UPSTREAM ROLLBACK DETECTED:", flush=True)
    print(
        "These refs are behind their reviewed checkpoints and are not update candidates.",
        flush=True,
    )
    for result in rollbacks:
        for line in monitor_rollback_guidance(result):
            print(line, flush=True)


def sync_github_auxiliary_files(skill: dict, upstream_path: str, token: str | None) -> int:
    """Sync non-SKILL.md files and directories beside the upstream SKILL.md."""
    repo = skill["repo"]
    token = _github_token_for(token)
    upstream_dir = str(Path(upstream_path).parent)
    local_dir = skill["local_path"].parent
    ref = skill.get("ref", "main")

    def sync_directory(api_url: str, relative_dir: Path) -> int:
        data = github_api_get(api_url, token)
        if not isinstance(data, list):
            return 0

        synced = 0
        for item in data:
            name = item.get("name", "")
            if not name or name in {".", ".."} or "/" in name:
                continue
            relative_path = relative_dir / name
            destination = local_dir / relative_path
            item_type = item.get("type")
            if item_type == "dir":
                child_url = item.get("url")
                if child_url:
                    synced += sync_directory(child_url, relative_path)
                continue
            if item_type != "file" or name.lower() == "skill.md":
                continue
            download_url = item.get("download_url")
            if not download_url:
                continue
            content = fetch_url(download_url, token)
            if content is None:
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")
            synced += 1
        return synced

    api_url = f"https://api.github.com/repos/{repo}/contents/{upstream_dir}?ref={ref}"
    return sync_directory(api_url, Path())


class MappingLockError(RuntimeError):
    """A mapping is already being changed by another conforming process."""


class AtomicMappingWriteError(RuntimeError):
    """A mapping write failed before or after the atomic replace boundary."""

    def __init__(self, message: str, *, replaced: bool, cause: BaseException):
        self.replaced = replaced
        self.cause = cause
        phase = "after replace" if replaced else "before replace"
        super().__init__(f"{message} ({phase}): {cause}")


class AtomicMappingBatchError(RuntimeError):
    """A multi-mapping record batch failed and reports rollback evidence."""

    def __init__(
        self,
        message: str,
        *,
        cause: BaseException,
        rollback_succeeded: bool,
        recovery_paths: list[Path] | None = None,
    ) -> None:
        self.cause = cause
        self.rollback_succeeded = rollback_succeeded
        self.recovery_paths = tuple(recovery_paths or ())
        recovery = (
            "; recovery=" + ", ".join(str(path) for path in self.recovery_paths)
            if self.recovery_paths
            else ""
        )
        super().__init__(
            f"{message}; rollback_succeeded={rollback_succeeded}{recovery}: "
            f"{cause}"
        )


class MappingSnapshot:
    __slots__ = (
        "content",
        "sha256",
        "device",
        "inode",
        "mode",
        "parent_device",
        "parent_inode",
    )

    def __init__(
        self,
        *,
        content: bytes,
        sha256: str,
        device: int,
        inode: int,
        mode: int,
        parent_device: int | None = None,
        parent_inode: int | None = None,
    ) -> None:
        self.content = content
        self.sha256 = sha256
        self.device = device
        self.inode = inode
        self.mode = mode
        self.parent_device = parent_device
        self.parent_inode = parent_inode


class StagedMappingTemporary:
    """One staged mapping whose original inode remains pinned by an open fd."""

    def __init__(
        self,
        path: Path,
        descriptor: int,
        identity: tuple[int, int],
    ) -> None:
        self.path = path
        self.descriptor = descriptor
        self.identity = identity

    def __enter__(self) -> "StagedMappingTemporary":
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        self.close()

    def close(self) -> None:
        descriptor = self.descriptor
        if descriptor < 0:
            return
        self.descriptor = -1
        os.close(descriptor)


def serialize_mapping_json(data: dict) -> bytes:
    return (
        json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")


def _mapping_path_parts(path: Path) -> tuple[Path, tuple[str, ...]]:
    """Return a lexical repository-relative mapping path without following it."""
    root = Path(os.path.abspath(REPO_ROOT))
    candidate = Path(os.path.abspath(path))
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(
            f"provenance mapping escapes the repository root: {path}"
        ) from exc
    parts = relative.parts
    if (
        not parts
        or any(part in {"", ".", ".."} for part in parts)
        or candidate == root
    ):
        raise RuntimeError(f"invalid provenance mapping path: {path}")
    return root, parts


@contextmanager
def _open_mapping_parent(path: Path):
    """Pin every mapping ancestor with openat + O_NOFOLLOW."""
    root, parts = _mapping_path_parts(Path(path))
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(root, flags)
    try:
        root_metadata = os.fstat(descriptor)
        root_path_metadata = root.lstat()
        if (
            not stat.S_ISDIR(root_metadata.st_mode)
            or stat.S_ISLNK(root_path_metadata.st_mode)
            or root_metadata.st_dev != root_path_metadata.st_dev
            or root_metadata.st_ino != root_path_metadata.st_ino
        ):
            raise RuntimeError(f"unsafe repository root for mapping: {root}")
        for component in parts[:-1]:
            next_descriptor = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
            metadata = os.fstat(descriptor)
            if not stat.S_ISDIR(metadata.st_mode):
                raise RuntimeError(
                    f"mapping ancestor is not a directory: {component}"
                )
        parent_metadata = os.fstat(descriptor)
        yield (
            descriptor,
            parts[-1],
            (parent_metadata.st_dev, parent_metadata.st_ino),
        )
    finally:
        os.close(descriptor)


def _validate_mapping_parent(
    path: Path,
    expected_identity: tuple[int, int],
) -> None:
    with _open_mapping_parent(path) as (_descriptor, _name, identity):
        if identity != expected_identity:
            raise RuntimeError(
                f"mapping parent directory changed concurrently: {path.parent}"
            )


def capture_mapping_snapshot(path: Path) -> MappingSnapshot:
    path = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    with _open_mapping_parent(path) as (
        parent_descriptor,
        name,
        parent_identity,
    ):
        descriptor = os.open(name, flags, dir_fd=parent_descriptor)
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError(f"mapping target is not a regular file: {path}")
            chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            content = b"".join(chunks)
            current = os.stat(
                name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            if (
                stat.S_ISLNK(current.st_mode)
                or not stat.S_ISREG(current.st_mode)
                or current.st_dev != metadata.st_dev
                or current.st_ino != metadata.st_ino
            ):
                raise RuntimeError(
                    f"mapping inode changed while it was being read: {path}"
                )
            _validate_mapping_parent(path, parent_identity)
            return MappingSnapshot(
                content=content,
                sha256=hashlib.sha256(content).hexdigest(),
                device=metadata.st_dev,
                inode=metadata.st_ino,
                mode=metadata.st_mode & 0o777,
                parent_device=parent_identity[0],
                parent_inode=parent_identity[1],
            )
        finally:
            os.close(descriptor)


def _validate_mapping_snapshot(path: Path, expected: MappingSnapshot) -> None:
    current = capture_mapping_snapshot(path)
    if (
        current.device != expected.device
        or current.inode != expected.inode
        or current.sha256 != expected.sha256
        or current.content != expected.content
        or (
            expected.parent_device is not None
            and current.parent_device != expected.parent_device
        )
        or (
            expected.parent_inode is not None
            and current.parent_inode != expected.parent_inode
        )
    ):
        raise RuntimeError(
            f"mapping changed before atomic replacement: {path}"
        )


def _mapping_target_exists(path: Path) -> bool:
    try:
        with _open_mapping_parent(Path(path)) as (descriptor, name, _identity):
            os.stat(name, dir_fd=descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return True


def _mapping_lock_path(path: Path) -> Path:
    uid = os.getuid() if hasattr(os, "getuid") else 0
    # Lock identity is lexical and repository-scoped; resolving here would
    # follow an attacker-controlled mapping ancestor before nofollow checks.
    digest = hashlib.sha256(
        str(Path(os.path.abspath(path))).encode("utf-8")
    ).hexdigest()
    return (
        Path(tempfile.gettempdir())
        / f"high-value-skills-mapping-locks-{uid}"
        / f"{digest}.lock"
    )


@contextmanager
def mapping_advisory_lock(path: Path, *, timeout: float = 10.0):
    """Hold a stable-inode POSIX lock for one provenance mapping."""
    if fcntl is None:  # pragma: no cover - repository CI is POSIX
        raise MappingLockError("mapping locks require POSIX flock")
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(float(timeout))
        or timeout < 0
    ):
        raise ValueError("mapping lock timeout must be finite and non-negative")
    lock_path = _mapping_lock_path(Path(path))
    lock_root = lock_path.parent
    lock_root.mkdir(mode=0o700, exist_ok=True)
    root_metadata = lock_root.lstat()
    if (
        stat.S_ISLNK(root_metadata.st_mode)
        or not stat.S_ISDIR(root_metadata.st_mode)
        or (hasattr(os, "getuid") and root_metadata.st_uid != os.getuid())
    ):
        raise MappingLockError(f"unsafe mapping lock root: {lock_root}")
    if root_metadata.st_mode & 0o077:
        lock_root.chmod(0o700)
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(lock_path, flags, 0o600)
    acquired = False
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or (hasattr(os, "getuid") and metadata.st_uid != os.getuid())
        ):
            raise MappingLockError(f"unsafe mapping lock file: {lock_path}")
        deadline = time.monotonic() + float(timeout)
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    raise MappingLockError(
                        f"mapping transaction is already active: {lock_path}"
                    ) from exc
                time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
        os.ftruncate(descriptor, 0)
        os.write(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
        os.fsync(descriptor)
        yield
    finally:
        try:
            if acquired:
                os.ftruncate(descriptor, 0)
                os.fsync(descriptor)
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def atomic_write_json(
    path: Path,
    data: dict,
    *,
    fault_injector=None,
    expected_snapshot: MappingSnapshot | None = None,
) -> None:
    """Hardened atomic mapping replacement with an explicit commit boundary."""
    path = Path(path)
    try:
        if expected_snapshot is None and _mapping_target_exists(path):
            expected_snapshot = capture_mapping_snapshot(path)
    except BaseException as exc:
        raise AtomicMappingWriteError(
            f"cannot capture mapping authority: {path}",
            replaced=False,
            cause=exc,
        ) from exc
    replaced = False
    payload = serialize_mapping_json(data)
    try:
        with _open_mapping_parent(path) as (
            directory_fd,
            target_name,
            parent_identity,
        ):
            if expected_snapshot is not None and (
                expected_snapshot.parent_device is not None
                and parent_identity
                != (
                    expected_snapshot.parent_device,
                    expected_snapshot.parent_inode,
                )
            ):
                raise RuntimeError(
                    f"mapping parent directory changed concurrently: {path.parent}"
                )
            with _stage_bytes_for_replace(
                path,
                payload,
                mode=(
                    expected_snapshot.mode
                    if expected_snapshot is not None
                    else 0o600
                ),
                directory_fd=directory_fd,
                parent_identity=parent_identity,
            ) as temporary:
                temporary_path = temporary.path
                temporary_name = temporary_path.name
                try:
                    temporary_metadata = _secure_temporary_metadata(
                        temporary_path,
                        directory_fd,
                    )
                    if temporary.identity != (
                        temporary_metadata.st_dev,
                        temporary_metadata.st_ino,
                    ):
                        raise RuntimeError(
                            "mapping staged inode identity is invalid"
                        )
                    installed_snapshot = MappingSnapshot(
                        content=payload,
                        sha256=hashlib.sha256(payload).hexdigest(),
                        device=temporary_metadata.st_dev,
                        inode=temporary_metadata.st_ino,
                        mode=(
                            expected_snapshot.mode
                            if expected_snapshot is not None
                            else 0o600
                        ),
                        parent_device=parent_identity[0],
                        parent_inode=parent_identity[1],
                    )
                    if fault_injector is not None:
                        fault_injector("after_temp_fsync")
                    _validate_pinned_temporary(
                        temporary_path,
                        directory_fd,
                        temporary.descriptor,
                        temporary.identity,
                    )
                    if expected_snapshot is not None:
                        _validate_mapping_snapshot(path, expected_snapshot)
                    elif _mapping_target_exists(path):
                        raise RuntimeError(
                            "mapping unexpectedly appeared before "
                            f"replacement: {path}"
                        )
                    _validate_mapping_parent(path, parent_identity)
                    os.replace(
                        temporary_name,
                        target_name,
                        src_dir_fd=directory_fd,
                        dst_dir_fd=directory_fd,
                    )
                    replaced = True
                    if fault_injector is not None:
                        fault_injector("after_replace")
                    _validate_mapping_snapshot(path, installed_snapshot)
                    os.fsync(directory_fd)
                    _validate_mapping_snapshot(path, installed_snapshot)
                finally:
                    try:
                        _validate_pinned_temporary(
                            temporary_path,
                            directory_fd,
                            temporary.descriptor,
                            temporary.identity,
                        )
                        os.unlink(
                            temporary_name,
                            dir_fd=directory_fd,
                        )
                    except (FileNotFoundError, RuntimeError):
                        pass
    except BaseException as exc:
        if isinstance(exc, AtomicMappingWriteError):
            raise
        raise AtomicMappingWriteError(
            f"failed to atomically replace mapping {path}",
            replaced=replaced,
            cause=exc,
        ) from exc


def _stage_bytes_for_replace(
    path: Path,
    payload: bytes,
    *,
    mode: int,
    suffix: str = ".tmp",
    directory_fd: int | None = None,
    parent_identity: tuple[int, int] | None = None,
) -> StagedMappingTemporary:
    path = Path(path)
    if directory_fd is None:
        with _open_mapping_parent(path) as (
            opened_descriptor,
            _target_name,
            opened_identity,
        ):
            return _stage_bytes_for_replace(
                path,
                payload,
                mode=mode,
                suffix=suffix,
                directory_fd=opened_descriptor,
                parent_identity=opened_identity,
            )
    if parent_identity is None:
        metadata = os.fstat(directory_fd)
        parent_identity = (metadata.st_dev, metadata.st_ino)
    temporary_name = f".{path.name}.{os.urandom(16).hex()}{suffix}"
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
    )
    fd = os.open(temporary_name, flags, 0o600, dir_fd=directory_fd)
    temporary = path.parent / temporary_name
    descriptor_metadata = os.fstat(fd)
    pinned_descriptor: int | None = None
    try:
        if not stat.S_ISREG(descriptor_metadata.st_mode):
            raise ValueError("mapping temporary inode is not regular")
        remaining = memoryview(payload)
        while remaining:
            written = os.write(fd, remaining)
            if written <= 0:
                raise OSError("mapping temporary write made no progress")
            remaining = remaining[written:]
        os.fchmod(fd, mode)
        os.fsync(fd)
        metadata = os.stat(
            temporary_name,
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
        if (
            stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_dev != descriptor_metadata.st_dev
            or metadata.st_ino != descriptor_metadata.st_ino
        ):
            raise ValueError("mapping temporary inode changed before replace")
        pinned_descriptor, pinned_metadata = _pin_temporary_inode(
            temporary,
            directory_fd,
        )
        if (
            pinned_metadata.st_dev,
            pinned_metadata.st_ino,
        ) != (
            descriptor_metadata.st_dev,
            descriptor_metadata.st_ino,
        ):
            raise RuntimeError(
                f"mapping temporary changed while being pinned: {temporary}"
            )
        identity = (
            descriptor_metadata.st_dev,
            descriptor_metadata.st_ino,
        )
        os.close(fd)
        fd = -1
        _validate_pinned_temporary(
            temporary,
            directory_fd,
            pinned_descriptor,
            identity,
        )
        _validate_mapping_parent(path, parent_identity)
        _validate_pinned_temporary(
            temporary,
            directory_fd,
            pinned_descriptor,
            identity,
        )
        result = StagedMappingTemporary(
            temporary,
            pinned_descriptor,
            identity,
        )
        pinned_descriptor = None
        return result
    except BaseException:
        cleanup_descriptor = (
            pinned_descriptor
            if pinned_descriptor is not None
            else fd
        )
        try:
            if cleanup_descriptor is not None and cleanup_descriptor >= 0:
                _validate_pinned_temporary(
                    temporary,
                    directory_fd,
                    cleanup_descriptor,
                    (
                        descriptor_metadata.st_dev,
                        descriptor_metadata.st_ino,
                    ),
                )
                os.unlink(temporary_name, dir_fd=directory_fd)
        except (FileNotFoundError, RuntimeError):
            pass
        if pinned_descriptor is not None:
            os.close(pinned_descriptor)
        if fd >= 0:
            os.close(fd)
        raise


def _secure_temporary_metadata(path: Path, directory_fd: int) -> os.stat_result:
    metadata = os.stat(
        path.name,
        dir_fd=directory_fd,
        follow_symlinks=False,
    )
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RuntimeError(f"mapping temporary is unsafe: {path}")
    return metadata


def _pin_temporary_inode(
    path: Path,
    directory_fd: int,
) -> tuple[int, os.stat_result]:
    """Open and retain a stable reference to one staged temporary inode.

    Linux filesystems may immediately reuse an unlinked inode number.  Keeping
    this descriptor open until replace/cleanup prevents a foreign file created
    under the same temporary name from passing a dev/inode-only ABA check.
    """
    descriptor = os.open(
        path.name,
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=directory_fd,
    )
    try:
        opened = os.fstat(descriptor)
        named = os.stat(
            path.name,
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(opened.st_mode)
            or stat.S_ISLNK(named.st_mode)
            or opened.st_dev != named.st_dev
            or opened.st_ino != named.st_ino
        ):
            raise RuntimeError(
                f"mapping temporary changed while being pinned: {path}"
            )
        return descriptor, opened
    except BaseException:
        os.close(descriptor)
        raise


def _validate_pinned_temporary(
    path: Path,
    directory_fd: int,
    descriptor: int,
    identity: tuple[int, int],
) -> os.stat_result:
    """Require the temporary name and retained descriptor to bind one inode."""
    named = _secure_temporary_metadata(path, directory_fd)
    pinned = os.fstat(descriptor)
    if (
        not stat.S_ISREG(pinned.st_mode)
        or (named.st_dev, named.st_ino) != identity
        or (pinned.st_dev, pinned.st_ino) != identity
    ):
        raise RuntimeError(f"mapping temporary inode changed: {path}")
    return named


def _stage_private_mapping_recovery(path: Path, payload: bytes) -> Path:
    """Preserve rollback bytes even when the canonical parent was detached."""
    recovery_root = _mapping_lock_path(path).parent
    recovery_root.mkdir(mode=0o700, exist_ok=True)
    root_metadata = recovery_root.lstat()
    if (
        stat.S_ISLNK(root_metadata.st_mode)
        or not stat.S_ISDIR(root_metadata.st_mode)
        or (hasattr(os, "getuid") and root_metadata.st_uid != os.getuid())
    ):
        raise RuntimeError(
            f"unsafe private mapping recovery root: {recovery_root}"
        )
    if root_metadata.st_mode & 0o077:
        recovery_root.chmod(0o700)
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    directory_fd = os.open(recovery_root, directory_flags)
    name = (
        f".{hashlib.sha256(str(path).encode('utf-8')).hexdigest()}."
        f"{os.urandom(16).hex()}.recovery.json"
    )
    recovery_path = recovery_root / name
    descriptor = -1
    pinned_descriptor: int | None = None
    created_identity: tuple[int, int] | None = None
    try:
        descriptor = os.open(
            name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=directory_fd,
        )
        created = os.fstat(descriptor)
        if not stat.S_ISREG(created.st_mode):
            raise RuntimeError("private mapping recovery inode is unsafe")
        created_identity = (created.st_dev, created.st_ino)
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("private mapping recovery write made no progress")
            remaining = remaining[written:]
        os.fchmod(descriptor, 0o600)
        os.fsync(descriptor)
        metadata = os.stat(
            name,
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
        if (
            stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISREG(metadata.st_mode)
            or (metadata.st_dev, metadata.st_ino) != created_identity
        ):
            raise RuntimeError("private mapping recovery inode is unsafe")
        pinned_descriptor, pinned = _pin_temporary_inode(
            recovery_path,
            directory_fd,
        )
        if (pinned.st_dev, pinned.st_ino) != created_identity:
            raise RuntimeError(
                "private mapping recovery inode changed while being pinned"
            )
        os.close(descriptor)
        descriptor = -1
        _validate_pinned_temporary(
            recovery_path,
            directory_fd,
            pinned_descriptor,
            created_identity,
        )
        os.fsync(directory_fd)
        current_root = recovery_root.lstat()
        if (
            current_root.st_dev != root_metadata.st_dev
            or current_root.st_ino != root_metadata.st_ino
            or stat.S_ISLNK(current_root.st_mode)
            or not stat.S_ISDIR(current_root.st_mode)
        ):
            raise RuntimeError(
                "private mapping recovery root changed concurrently"
            )
        _validate_pinned_temporary(
            recovery_path,
            directory_fd,
            pinned_descriptor,
            created_identity,
        )
        os.close(pinned_descriptor)
        pinned_descriptor = None
        return recovery_path
    except BaseException:
        cleanup_descriptor = (
            pinned_descriptor
            if pinned_descriptor is not None
            else descriptor
        )
        try:
            if (
                cleanup_descriptor is not None
                and cleanup_descriptor >= 0
                and created_identity is not None
            ):
                _validate_pinned_temporary(
                    recovery_path,
                    directory_fd,
                    cleanup_descriptor,
                    created_identity,
                )
                os.unlink(name, dir_fd=directory_fd)
        except (FileNotFoundError, RuntimeError):
            pass
        if pinned_descriptor is not None:
            os.close(pinned_descriptor)
        if descriptor >= 0:
            os.close(descriptor)
        raise
    finally:
        os.close(directory_fd)


def _atomic_write_json_batch_locked(
    prepared: dict[Path, dict],
    *,
    fault_injector=None,
    expected_snapshots: dict[Path, MappingSnapshot] | None = None,
) -> None:
    """Two-phase, rollback-safe replacement for an already-locked batch."""
    if not prepared:
        return
    paths = sorted(Path(path) for path in prepared)
    originals: dict[Path, bytes] = {}
    modes: dict[Path, int] = {}
    snapshots: dict[Path, MappingSnapshot] = {}
    installed_snapshots: dict[Path, MappingSnapshot] = {}
    staged: dict[Path, Path | None] = {}
    staged_temporaries: dict[Path, StagedMappingTemporary] = {}
    directory_fds: dict[Path, int] = {}
    target_names: dict[Path, str] = {}
    parent_identities: dict[Path, tuple[int, int]] = {}
    parent_stack = ExitStack()
    temporary_stack = ExitStack()
    replaced: list[Path] = []
    try:
        for path in paths:
            expected = (
                (expected_snapshots or {}).get(path)
                or capture_mapping_snapshot(path)
            )
            snapshots[path] = expected
            originals[path] = expected.content
            modes[path] = expected.mode
            descriptor, target_name, parent_identity = (
                parent_stack.enter_context(_open_mapping_parent(path))
            )
            directory_fds[path] = descriptor
            target_names[path] = target_name
            parent_identities[path] = parent_identity
            if expected.parent_device is not None and parent_identity != (
                expected.parent_device,
                expected.parent_inode,
            ):
                raise RuntimeError(
                    f"mapping parent directory changed concurrently: {path.parent}"
                )
            payload = serialize_mapping_json(prepared[path])
            temporary = temporary_stack.enter_context(
                _stage_bytes_for_replace(
                    path,
                    payload,
                    mode=modes[path],
                    directory_fd=descriptor,
                    parent_identity=parent_identity,
                )
            )
            staged[path] = temporary.path
            staged_temporaries[path] = temporary
            temporary_metadata = _secure_temporary_metadata(
                staged[path],
                descriptor,
            )
            if temporary.identity != (
                temporary_metadata.st_dev,
                temporary_metadata.st_ino,
            ):
                raise RuntimeError(
                    f"mapping staged inode identity is invalid: "
                    f"{staged[path]}"
                )
            installed_snapshots[path] = MappingSnapshot(
                content=payload,
                sha256=hashlib.sha256(payload).hexdigest(),
                device=temporary.identity[0],
                inode=temporary.identity[1],
                mode=modes[path],
                parent_device=parent_identity[0],
                parent_inode=parent_identity[1],
            )
            if fault_injector is not None:
                fault_injector("after_stage", path)

        for path in paths:
            _validate_mapping_snapshot(path, snapshots[path])
        for path in paths:
            temporary = staged[path]
            if temporary is None:
                raise RuntimeError(f"missing staged mapping: {path}")
            _validate_mapping_snapshot(path, snapshots[path])
            _validate_pinned_temporary(
                temporary,
                directory_fds[path],
                staged_temporaries[path].descriptor,
                staged_temporaries[path].identity,
            )
            _validate_mapping_parent(path, parent_identities[path])
            os.replace(
                temporary.name,
                target_names[path],
                src_dir_fd=directory_fds[path],
                dst_dir_fd=directory_fds[path],
            )
            staged[path] = None
            replaced.append(path)
            if fault_injector is not None:
                fault_injector("after_replace", path)
            _validate_mapping_snapshot(path, installed_snapshots[path])
        for path, descriptor in directory_fds.items():
            if fault_injector is not None:
                fault_injector("before_dir_fsync", path.parent)
            os.fsync(descriptor)
        for path in paths:
            _validate_mapping_snapshot(path, installed_snapshots[path])
    except BaseException as cause:
        recovery_paths: list[Path] = []
        recovery_recorded: set[Path] = set()
        rollback_errors: list[BaseException] = []
        rolled_back_snapshots: dict[Path, MappingSnapshot] = {}
        for path in reversed(replaced):
            rollback: Path | None = None
            try:
                _validate_mapping_snapshot(path, installed_snapshots[path])
                with _stage_bytes_for_replace(
                    path,
                    originals[path],
                    mode=modes[path],
                    suffix=".rollback.tmp",
                    directory_fd=directory_fds[path],
                    parent_identity=parent_identities[path],
                ) as rollback_temporary:
                    rollback = rollback_temporary.path
                    try:
                        rollback_metadata = _secure_temporary_metadata(
                            rollback,
                            directory_fds[path],
                        )
                        if rollback_temporary.identity != (
                            rollback_metadata.st_dev,
                            rollback_metadata.st_ino,
                        ):
                            raise RuntimeError(
                                "mapping rollback staged inode identity is "
                                f"invalid: {rollback}"
                            )
                        rollback_snapshot = MappingSnapshot(
                            content=originals[path],
                            sha256=hashlib.sha256(
                                originals[path]
                            ).hexdigest(),
                            device=rollback_temporary.identity[0],
                            inode=rollback_temporary.identity[1],
                            mode=modes[path],
                            parent_device=parent_identities[path][0],
                            parent_inode=parent_identities[path][1],
                        )
                        _validate_pinned_temporary(
                            rollback,
                            directory_fds[path],
                            rollback_temporary.descriptor,
                            rollback_temporary.identity,
                        )
                        os.replace(
                            rollback.name,
                            target_names[path],
                            src_dir_fd=directory_fds[path],
                            dst_dir_fd=directory_fds[path],
                        )
                        rollback = None
                        _validate_mapping_snapshot(path, rollback_snapshot)
                        rolled_back_snapshots[path] = rollback_snapshot
                    finally:
                        if rollback is not None:
                            try:
                                _validate_pinned_temporary(
                                    rollback,
                                    directory_fds[path],
                                    rollback_temporary.descriptor,
                                    rollback_temporary.identity,
                                )
                                os.unlink(
                                    rollback.name,
                                    dir_fd=directory_fds[path],
                                )
                            except (FileNotFoundError, RuntimeError):
                                pass
            except BaseException as rollback_error:
                rollback_errors.append(rollback_error)
                try:
                    with _stage_bytes_for_replace(
                        path,
                        originals[path],
                        mode=0o600,
                        suffix=".recovery.json",
                        directory_fd=directory_fds[path],
                        parent_identity=parent_identities[path],
                    ) as recovery_temporary:
                        recovery_paths.append(recovery_temporary.path)
                        recovery_recorded.add(path)
                except BaseException as recovery_error:
                    rollback_errors.append(recovery_error)
                    try:
                        recovery_paths.append(
                            _stage_private_mapping_recovery(
                                path,
                                originals[path],
                            )
                        )
                        recovery_recorded.add(path)
                    except BaseException as private_recovery_error:
                        rollback_errors.append(private_recovery_error)
        try:
            for descriptor in directory_fds.values():
                os.fsync(descriptor)
            for path, rollback_snapshot in rolled_back_snapshots.items():
                _validate_mapping_snapshot(path, rollback_snapshot)
        except BaseException as rollback_fsync_error:
            rollback_errors.append(rollback_fsync_error)
        if rollback_errors:
            for path in paths:
                if path in recovery_recorded:
                    continue
                try:
                    with _stage_bytes_for_replace(
                        path,
                        originals[path],
                        mode=0o600,
                        suffix=".recovery.json",
                        directory_fd=directory_fds[path],
                        parent_identity=parent_identities[path],
                    ) as recovery_temporary:
                        recovery_paths.append(recovery_temporary.path)
                        recovery_recorded.add(path)
                except BaseException as recovery_error:
                    rollback_errors.append(recovery_error)
                    try:
                        recovery_paths.append(
                            _stage_private_mapping_recovery(
                                path,
                                originals[path],
                            )
                        )
                        recovery_recorded.add(path)
                    except BaseException as private_recovery_error:
                        rollback_errors.append(private_recovery_error)
            detail = RuntimeError(
                f"{cause}; rollback errors: "
                + "; ".join(str(error) for error in rollback_errors)
            )
            raise AtomicMappingBatchError(
                "mapping batch failed and rollback was incomplete",
                cause=detail,
                rollback_succeeded=False,
                recovery_paths=recovery_paths,
            ) from cause
        raise AtomicMappingBatchError(
            "mapping batch failed",
            cause=cause,
            rollback_succeeded=True,
        ) from cause
    finally:
        for path, temporary in staged.items():
            if temporary is not None:
                staged_temporary = staged_temporaries.get(path)
                if staged_temporary is None:
                    continue
                try:
                    _validate_pinned_temporary(
                        temporary,
                        directory_fds[path],
                        staged_temporary.descriptor,
                        staged_temporary.identity,
                    )
                    os.unlink(
                        temporary.name,
                        dir_fd=directory_fds[path],
                    )
                except (FileNotFoundError, RuntimeError):
                    pass
        try:
            temporary_stack.close()
        finally:
            parent_stack.close()


def atomic_write_json_batch(
    prepared: dict[Path, dict],
    *,
    fault_injector=None,
    expected_snapshots: dict[Path, MappingSnapshot] | None = None,
    durable_guard: DurableBatchGuard | None = None,
) -> None:
    """Crash-durable wrapper around the hardened mapping batch writer."""
    if not prepared:
        return
    if durable_guard is None:
        with durable_batch_lock_and_recover(REPO_ROOT) as guard:
            atomic_write_json_batch(
                prepared,
                fault_injector=fault_injector,
                expected_snapshots=expected_snapshots,
                durable_guard=guard,
            )
        return

    paths = sorted(Path(path) for path in prepared)
    replacement_bytes = {
        path: serialize_mapping_json(prepared[path]) for path in paths
    }
    after_modes: dict[Path, int | None] = {}
    for path in paths:
        snapshot = (expected_snapshots or {}).get(path)
        if snapshot is None:
            snapshot = capture_mapping_snapshot(path)
        after_modes[path] = snapshot.mode

    durable_guard.commit_batch(
        replacement_bytes,
        lambda: _atomic_write_json_batch_locked(
            prepared,
            fault_injector=fault_injector,
            expected_snapshots=expected_snapshots,
        ),
        after_modes=after_modes,
    )


def _validate_candidate_mappings(prepared: dict[Path, dict]) -> None:
    """Run full provenance and unique-claim gates without replacing mappings."""
    staged: dict[Path, Path] = {}
    staged_temporaries: dict[Path, StagedMappingTemporary] = {}
    directory_fds: dict[Path, int] = {}
    parent_identities: dict[Path, tuple[int, int]] = {}
    parent_stack = ExitStack()
    temporary_stack = ExitStack()
    try:
        for path, data in prepared.items():
            descriptor, _target_name, parent_identity = (
                parent_stack.enter_context(_open_mapping_parent(path))
            )
            directory_fds[path] = descriptor
            parent_identities[path] = parent_identity
            payload = serialize_mapping_json(data)
            temporary = temporary_stack.enter_context(
                _stage_bytes_for_replace(
                    path,
                    payload,
                    mode=0o600,
                    suffix=".validation.skills.json",
                    directory_fd=descriptor,
                    parent_identity=parent_identity,
                )
            )
            staged[path] = temporary.path
            staged_temporaries[path] = temporary
            temporary_metadata = _secure_temporary_metadata(
                staged[path],
                descriptor,
            )
            if temporary.identity != (
                temporary_metadata.st_dev,
                temporary_metadata.st_ino,
            ):
                raise RuntimeError(
                    "validation mapping staged inode identity is invalid: "
                    f"{staged[path]}"
                )
        errors: list[str] = []
        for mapping_path in sorted(staged):
            path = staged[mapping_path]
            temporary = staged_temporaries[mapping_path]
            _validate_pinned_temporary(
                path,
                directory_fds[mapping_path],
                temporary.descriptor,
                temporary.identity,
            )
            errors.extend(
                validate_provenance_mapping(path, REPO_ROOT, allow_v1=False)
            )
            _validate_pinned_temporary(
                path,
                directory_fds[mapping_path],
                temporary.descriptor,
                temporary.identity,
            )
        staged_paths = set(staged.values())
        original_paths = set(staged)
        repository_paths = [
            path
            for pattern in ("*.skills.json", "*.bundle.json")
            for path in SOURCE_MAPPINGS_DIR.glob(pattern)
            if path not in original_paths and path not in staged_paths
        ]
        repository_paths.extend(staged.values())
        for mapping_path, temporary_path in staged.items():
            temporary = staged_temporaries[mapping_path]
            _validate_pinned_temporary(
                temporary_path,
                directory_fds[mapping_path],
                temporary.descriptor,
                temporary.identity,
            )
        errors.extend(
            validate_repository_mappings(
                sorted(repository_paths),
                REPO_ROOT,
            )
        )
        for mapping_path, temporary_path in staged.items():
            temporary = staged_temporaries[mapping_path]
            _validate_pinned_temporary(
                temporary_path,
                directory_fds[mapping_path],
                temporary.descriptor,
                temporary.identity,
            )
        if errors:
            raise RuntimeError(
                "candidate mapping failed full provenance validation: "
                + " | ".join(errors[:20])
            )
    finally:
        cleanup_errors: list[BaseException] = []
        for mapping_path, temporary_path in staged.items():
            temporary = staged_temporaries[mapping_path]
            try:
                _validate_mapping_parent(
                    mapping_path,
                    parent_identities[mapping_path],
                )
            except BaseException as exc:
                cleanup_errors.append(exc)
            try:
                _validate_pinned_temporary(
                    temporary_path,
                    directory_fds[mapping_path],
                    temporary.descriptor,
                    temporary.identity,
                )
                os.unlink(
                    temporary_path.name,
                    dir_fd=directory_fds[mapping_path],
                )
            except FileNotFoundError:
                cleanup_errors.append(
                    RuntimeError(
                        f"validation mapping disappeared: {temporary_path}"
                    )
                )
            except BaseException as exc:
                cleanup_errors.append(exc)
        try:
            temporary_stack.close()
        finally:
            parent_stack.close()
        if cleanup_errors and sys.exc_info()[0] is None:
            raise RuntimeError(
                "candidate mapping cleanup failed safely: "
                + "; ".join(str(error) for error in cleanup_errors)
            )


def _v2_entry_and_origin(
    data: dict,
    skill: dict,
    *,
    for_apply: bool = False,
) -> tuple[dict, dict]:
    entry_index = skill.get("mapping_entry_index")
    origin_index = skill.get("origin_index")
    if type(entry_index) is not int or type(origin_index) is not int:
        raise RuntimeError("v2 mapping coordinates are missing")
    try:
        entry = data["skills"][entry_index]
        origin = entry["origins"][origin_index]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("v2 mapping coordinates are stale") from exc
    if not isinstance(entry, dict) or not isinstance(origin, dict):
        raise RuntimeError("v2 mapping entry/origin is malformed")
    structural_errors = _v2_sync_entry_errors(entry)
    if structural_errors:
        raise RuntimeError(
            "v2 mapping authority is no longer valid: "
            + "; ".join(structural_errors)
        )
    if entry.get("status") != "verified_in_repo":
        raise RuntimeError("v2 mapping entry is no longer active")
    if entry.get("kind") not in {"mirror", "overlay"}:
        raise RuntimeError(
            f"v2 mapping kind is not synchronizable: {entry.get('kind')!r}"
        )
    active_external_indexes = [
        index
        for index, candidate in enumerate(entry.get("origins", []))
        if isinstance(candidate, dict)
        and isinstance(candidate.get("repo"), str)
        and not candidate["repo"].startswith("local-repo/")
        and candidate.get("sync_mode") not in {"archived", "local-only"}
    ]
    if active_external_indexes != [origin_index]:
        raise RuntimeError(
            "selected origin is no longer the unique active external origin"
        )
    if origin.get("repo") != skill.get("repo"):
        raise RuntimeError("v2 mapping origin changed during synchronization")
    expected_fingerprint = skill.get("mapping_fingerprint")
    if not isinstance(expected_fingerprint, str) or not SHA256_RE.fullmatch(
        expected_fingerprint
    ):
        raise RuntimeError("v2 checked mapping fingerprint is missing or invalid")
    if _entry_origin_fingerprint(entry, origin_index) != expected_fingerprint:
        raise RuntimeError(
            "v2 mapping entry/origin changed after upstream check"
        )
    if for_apply:
        tracking = origin.get("tracking")
        channel = tracking.get("channel") if isinstance(tracking, dict) else None
        if (
            entry.get("sync_mode") != "replace"
            or origin.get("sync_mode") != "replace"
            or channel not in AUTO_CHANNELS
        ):
            raise RuntimeError(
                "v2 mapping no longer permits automatic stable apply"
            )
    return entry, origin


def _record_v2_result(
    data: dict,
    result: dict,
    *,
    synced: bool,
    entry_origin: tuple[dict, dict] | None = None,
) -> None:
    skill = result["skill"]
    entry, origin = (
        entry_origin
        if entry_origin is not None
        else _v2_entry_and_origin(data, skill)
    )
    tracking = origin.get("tracking")
    if not isinstance(tracking, dict):
        raise RuntimeError("v2 origin tracking object is missing")
    commit = result.get("current_commit")
    if not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit):
        raise RuntimeError("successful v2 result has no full resolved commit")
    path_commit = result.get("path_commit")
    if not isinstance(path_commit, str) or not COMMIT_RE.fullmatch(path_commit):
        raise RuntimeError("successful v2 result has an invalid path commit")
    license_evidence = result.get("license_evidence")
    if not isinstance(license_evidence, dict):
        raise RuntimeError("successful v2 result has no license evidence")
    required_license_keys = {
        "path",
        "blob_sha",
        "content_sha256",
        "spdx",
        "resolved_commit",
    }
    if (
        not required_license_keys.issubset(license_evidence)
        or not _safe_mapping_path(license_evidence.get("path"))
        or not isinstance(license_evidence.get("blob_sha"), str)
        or not COMMIT_RE.fullmatch(str(license_evidence.get("blob_sha")))
        or not isinstance(license_evidence.get("content_sha256"), str)
        or not SHA256_RE.fullmatch(
            str(license_evidence.get("content_sha256"))
        )
        or license_evidence.get("spdx") != origin.get("license")
        or license_evidence.get("resolved_commit") != commit.lower()
        or license_evidence.get("api_spdx")
        not in {None, "NOASSERTION", origin.get("license")}
    ):
        raise RuntimeError("successful v2 result has invalid license evidence")

    today = date.today().isoformat()
    tracking["last_checked_at"] = today
    if result.get("changes") != "upstream_rollback":
        tracking["license_checkpoint"] = copy.deepcopy(license_evidence)
    if synced or result.get("changes") == "none":
        resolved_ref = result.get("resolved_ref")
        channel = tracking.get("channel")
        if isinstance(resolved_ref, str) and resolved_ref:
            if channel == "latest_release":
                tracking["ref"] = resolved_ref
            elif channel == "fixed_ref" and resolved_ref != tracking.get("ref"):
                raise RuntimeError(
                    "fixed_ref observation attempted to rewrite immutable ref"
                )
            elif channel not in {"default_branch", "canary", "fixed_ref"}:
                raise RuntimeError(f"unsupported tracking channel: {channel!r}")
        tracking["resolved_commit"] = commit.lower()
        if path_commit is not None:
            tracking["path_commit"] = path_commit.lower()
        tracking["last_synced_at"] = today

    legacy = entry.setdefault("upstream", {})
    if isinstance(legacy, dict):
        legacy["repo"] = origin.get("repo")
        legacy["last_checked_at"] = today
        if synced or result.get("changes") == "none":
            legacy["ref"] = tracking["ref"]
            if path_commit is not None:
                legacy["path_commit"] = path_commit.lower()
            legacy["last_synced_at"] = today
            legacy["last_synced_commit"] = commit.lower()
    data.setdefault("video", {})["checked_at"] = today


def record_v2_checks(results: list[dict]) -> None:
    """Atomically persist observations only after every check succeeded."""
    grouped: dict[Path, list[dict]] = {}
    skill_roots: set[str] = set()
    for result in results:
        skill = result["skill"]
        if skill.get("schema_version") != 2:
            continue
        if result.get("changes") in {"unavailable", "expected_skipped"}:
            continue
        mapping_path = skill.get("mapping_path")
        if mapping_path is None:
            raise RuntimeError("v2 result has no mapping path")
        grouped.setdefault(Path(mapping_path), []).append(result)
        repo_skill = skill.get("repo_skill")
        if not _safe_mapping_path(repo_skill):
            raise RuntimeError("v2 result has an invalid canonical skill path")
        skill_root = PurePosixPath(str(repo_skill)).parent.as_posix()
        if not skill_root.startswith("skills/"):
            raise RuntimeError("v2 result canonical skill escapes skills/")
        skill_roots.add(skill_root)

    if not grouped:
        return

    # Cross-tool order is durable global, mappings, then canonical skills.
    # The outer guard resolves any hard-exit batch before authority is reread.
    with durable_batch_lock_and_recover(REPO_ROOT) as durable_guard:
        with ExitStack() as locks:
            for path in sorted(grouped):
                locks.enter_context(mapping_advisory_lock(path))
            engine = _load_artifact_engine()
            for skill_root in sorted(skill_roots):
                locks.enter_context(
                    engine.skill_advisory_lock(
                        REPO_ROOT,
                        skill_root,
                        timeout=0.0,
                    )
                )
            prepared: dict[Path, dict] = {}
            snapshots: dict[Path, MappingSnapshot] = {}
            for path in sorted(grouped):
                path_results = grouped[path]
                # Re-read only after both batch and skill-tree crash recovery.
                snapshot = capture_mapping_snapshot(path)
                snapshots[path] = snapshot
                data = json.loads(snapshot.content.decode("utf-8"))
                for result in path_results:
                    _record_v2_result(data, result, synced=False)
                prepared[path] = data

            _validate_candidate_mappings(prepared)
            atomic_write_json_batch(
                prepared,
                expected_snapshots=snapshots,
                durable_guard=durable_guard,
            )


def record_v2_monitor_reviews(results: list[dict]) -> None:
    """Advance explicitly reviewed monitor checkpoints without replacing bodies."""
    reviewed = [
        result
        for result in results
        if result["skill"].get("schema_version") == 2
        and _is_monitor_skill(result["skill"])
        and result.get("changes")
        not in {"unavailable", "expected_skipped", "upstream_rollback"}
    ]
    if not reviewed:
        raise RuntimeError("no successful monitor results were available to record")

    grouped: dict[Path, list[dict]] = {}
    skill_roots: set[str] = set()
    for result in reviewed:
        skill = result["skill"]
        mapping_path = skill.get("mapping_path")
        repo_skill = skill.get("repo_skill")
        if mapping_path is None or not _safe_mapping_path(repo_skill):
            raise RuntimeError("reviewed monitor result has invalid mapping coordinates")
        grouped.setdefault(Path(mapping_path), []).append(result)
        skill_roots.add(PurePosixPath(str(repo_skill)).parent.as_posix())

    with durable_batch_lock_and_recover(REPO_ROOT) as durable_guard:
        with ExitStack() as locks:
            for path in sorted(grouped):
                locks.enter_context(mapping_advisory_lock(path))
            engine = _load_artifact_engine()
            for skill_root in sorted(skill_roots):
                locks.enter_context(
                    engine.skill_advisory_lock(
                        REPO_ROOT,
                        skill_root,
                        timeout=0.0,
                    )
                )

            prepared: dict[Path, dict] = {}
            snapshots: dict[Path, MappingSnapshot] = {}
            today = date.today().isoformat()
            for path in sorted(grouped):
                snapshot = capture_mapping_snapshot(path)
                snapshots[path] = snapshot
                data = json.loads(snapshot.content.decode("utf-8"))
                review_targets: set[str] = set()
                for result in grouped[path]:
                    entry, origin = _v2_entry_and_origin(
                        data,
                        result["skill"],
                    )
                    _record_v2_result(
                        data,
                        result,
                        synced=True,
                        entry_origin=(entry, origin),
                    )
                    repo_skill = result["skill"]["repo_skill"]
                    canonical_path = REPO_ROOT / repo_skill
                    origin["tracking"]["content_sha256"] = hashlib.sha256(
                        canonical_path.read_bytes()
                    ).hexdigest()
                    review_targets.add(
                        f"{origin['repo']}@{result['current_commit']}"
                    )
                attempts = data.setdefault("verification_attempts", [])
                for target in sorted(review_targets):
                    attempts.append(
                        {
                            "date": today,
                            "method": "commit-aware-manual-monitor-review",
                            "target": target,
                            "result": "success",
                            "evidence": (
                                "Explicit reviewer checkpoint recorded after "
                                "curating durable method, compatibility, "
                                "security, CI, and validation changes."
                            ),
                        }
                    )
                prepared[path] = data

            _validate_candidate_mappings(prepared)
            atomic_write_json_batch(
                prepared,
                expected_snapshots=snapshots,
                durable_guard=durable_guard,
            )


def _artifact_payloads_for_engine(update: dict) -> list[dict]:
    skill = update["skill"]
    upstream_files = update.get("upstream_files")
    source_blobs = update.get("source_blobs")
    upstream_modes = update.get("upstream_modes")
    if (
        not isinstance(upstream_files, dict)
        or not isinstance(source_blobs, dict)
        or not isinstance(upstream_modes, dict)
        or set(upstream_modes) != set(upstream_files)
        or any(
            mode not in {"100644", "100755"}
            for mode in upstream_modes.values()
        )
    ):
        raise RuntimeError("v2 update has no materialized artifact inventory")
    payloads: list[dict] = []
    repo_skill = skill.get("repo_skill")
    for artifact in skill.get("artifacts", []):
        source = artifact["source"]
        target = artifact["target"]
        if artifact.get("type", "file") == "file":
            targets = [(source, target)]
        else:
            prefix = source.rstrip("/") + "/"
            targets = [
                (
                    source_path,
                    target.rstrip("/") + "/" + source_path[len(prefix) :],
                )
                for source_path in sorted(source_blobs)
                if source_path.startswith(prefix)
            ]
        for expanded_source, expanded_target in targets:
            raw = upstream_files[expanded_target]
            if expanded_target == repo_skill:
                try:
                    upstream_text = raw.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise RuntimeError("canonical SKILL.md upstream is not UTF-8") from exc
                upstream_text = apply_repository_adaptations(upstream_text, skill)
                raw = merge_frontmatter(
                    skill["local_path"].read_text(
                        encoding="utf-8", errors="strict"
                    ),
                    upstream_text,
                ).encode("utf-8")
            payloads.append(
                {
                    "source": expanded_source,
                    "target": expanded_target,
                    "type": "file",
                    "data": raw,
                    "mode": upstream_modes[expanded_target],
                }
            )
    return payloads


def _other_origin_target_conflicts(
    entry: dict,
    *,
    selected_origin_index: int,
    desired_targets: set[str],
) -> list[str]:
    conflicts: set[str] = set()
    for index, origin in enumerate(entry.get("origins", [])):
        if index == selected_origin_index or not isinstance(origin, dict):
            continue
        artifacts = origin.get("artifacts")
        if not isinstance(artifacts, list):
            continue
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            conflicts.update(
                target
                for target in desired_targets
                if _artifact_owns_target(artifact, target)
            )
    return sorted(conflicts)


def _load_artifact_engine():
    try:
        import artifact_set_sync as engine
    except ModuleNotFoundError:
        from scripts import artifact_set_sync as engine
    return engine


def apply_v2_update(
    update: dict,
    *,
    dry_run: bool = False,
    reviewed_dependents: dict[str, str] | None = None,
    _durable_guard: DurableBatchGuard | None = None,
):
    """Apply artifacts and reviewed dependency locks with coordinated journals.

    A dependent approval is its canonical SKILL.md SHA-256, not permission to
    silently accept arbitrary future composite changes. Mapping batch recovery
    always precedes artifact recovery under the repository-wide durable guard.
    """
    if _durable_guard is None and not dry_run:
        with durable_batch_lock_and_recover(REPO_ROOT) as durable_guard:
            return apply_v2_update(
                update,
                dry_run=dry_run,
                reviewed_dependents=reviewed_dependents,
                _durable_guard=durable_guard,
            )
    skill = update["skill"]
    channel = (skill.get("tracking") or {}).get("channel")
    if channel not in AUTO_CHANNELS or skill.get("sync_mode") != "replace":
        raise RuntimeError(
            f"automatic apply is forbidden for channel={channel!r} "
            f"sync_mode={skill.get('sync_mode')!r}"
        )
    mapping_path = Path(skill["mapping_path"])
    with ExitStack() as locks:
        # Freeze the reverse-dependency graph as well as the owning mapping.
        # All cooperating writers use global -> sorted mappings -> skills.
        mapping_paths = sorted(
            set(mapping_path.parent.glob("*.skills.json")) | {mapping_path}
        )
        for path in mapping_paths:
            locks.enter_context(mapping_advisory_lock(path))
        snapshots = {
            path: capture_mapping_snapshot(path) for path in mapping_paths
        }
        documents = {
            path: json.loads(snapshot.content.decode("utf-8"))
            for path, snapshot in snapshots.items()
        }
        mapping_snapshot = capture_mapping_snapshot(mapping_path)
        mapping_before = mapping_snapshot.content
        mapping_data = json.loads(mapping_before.decode("utf-8"))
        entry, origin = _v2_entry_and_origin(
            mapping_data, skill, for_apply=True
        )
        current_other_artifacts: list[dict] = []
        for index, origin in enumerate(entry.get("origins", [])):
            if index == skill["origin_index"] or not isinstance(origin, dict):
                continue
            artifacts = origin.get("artifacts")
            if isinstance(artifacts, list):
                current_other_artifacts.extend(
                    item for item in artifacts if isinstance(item, dict)
                )
        engine = _load_artifact_engine()
        payloads = _artifact_payloads_for_engine(update)
        scope_conflicts = _other_origin_target_conflicts(
            entry,
            selected_origin_index=skill["origin_index"],
            desired_targets={payload["target"] for payload in payloads},
        )
        if scope_conflicts:
            raise RuntimeError(
                "desired upstream targets collide with another origin scope: "
                + ", ".join(scope_conflicts)
            )
        checkpoint = {
            "resolved_commit": update["current_commit"],
            "path_commit": update["path_commit"],
            "resolved_ref": update.get("resolved_ref"),
        }
        plan = engine.plan_artifact_set_sync(
            REPO_ROOT,
            entry,
            payloads,
            checkpoint,
            origin_index=skill["origin_index"],
            protected_targets=_owned_targets_for_artifacts(
                current_other_artifacts,
                entry.get("managed_files", []),
            ),
        )
        if dry_run:
            return engine.apply_artifact_set_sync(plan, dry_run=True)

        prepared = {mapping_path: mapping_data}
        approved_files: dict[Path, str] = {}
        old_content_hash = hashlib.sha256(
            Path(skill["local_path"]).read_bytes()
        ).hexdigest()
        if plan.content_sha256 != old_content_hash:
            slug = entry["normalized_slug"]
            for path, document in documents.items():
                if path == mapping_path:
                    document = mapping_data
                for dependent in document.get("skills", []):
                    composition = dependent.get("composition") or {}
                    if not any(
                        dependency.get("skill") == slug
                        for dependency in composition.get("depends_on", [])
                        if isinstance(dependency, dict)
                    ):
                        continue
                    dependent_slug = dependent["normalized_slug"]
                    canonical = REPO_ROOT / dependent["repo_skill"]
                    canonical.resolve(strict=True).relative_to(REPO_ROOT.resolve())
                    if canonical.is_symlink():
                        raise RuntimeError("dependent canonical file is a symlink")
                    digest = hashlib.sha256(canonical.read_bytes()).hexdigest()
                    if (reviewed_dependents or {}).get(dependent_slug) != digest:
                        raise RuntimeError(
                            f"dependency upgrade requires explicit review: "
                            f"--reviewed-dependent {dependent_slug}={digest}"
                        )
                    dependency_lock = composition.get("dependency_lock") or {}
                    if dependency_lock.get(slug) != old_content_hash:
                        raise RuntimeError(
                            f"dependent {dependent_slug} has a stale baseline lock"
                        )
                    dependency_lock[slug] = plan.content_sha256
                    prepared[path] = document
                    approved_files[canonical] = digest

        held_owner_lock = None
        reviewed_snapshots = {}
        if approved_files:
            roots = {
                path.parent.relative_to(REPO_ROOT).as_posix()
                for path in approved_files
            } | {plan.skill_root}
            for root in sorted(roots):
                held = locks.enter_context(
                    engine.skill_advisory_lock(REPO_ROOT, root)
                )
                if root == plan.skill_root:
                    held_owner_lock = held
            for path, digest in approved_files.items():
                snapshot = capture_mapping_snapshot(path)
                if snapshot.sha256 != digest:
                    raise RuntimeError("reviewed dependent changed before locking")
                reviewed_snapshots[path] = snapshot

        def validate_reviewed_files(*_args):
            for path, snapshot in reviewed_snapshots.items():
                _validate_mapping_snapshot(path, snapshot)

        with engine.prepare_artifact_set_sync(
            plan, **({"_held_lock": held_owner_lock} if held_owner_lock else {})
        ) as transaction:
            sync_result = transaction.result
            # Keep the reviewed source→target declarations (including
            # directory mappings). Expansion updates managed_files only.
            entry["managed_files"] = [
                dict(item) for item in sync_result.managed_files
            ]
            tracking = origin["tracking"]
            tracking["content_sha256"] = sync_result.content_sha256
            result_with_checkpoint = {
                **update,
                "current_commit": sync_result.checkpoint.get(
                    "resolved_commit", update["current_commit"]
                ),
                "path_commit": sync_result.checkpoint.get(
                    "path_commit", update["path_commit"]
                ),
                "resolved_ref": sync_result.checkpoint.get(
                    "resolved_ref", update.get("resolved_ref")
                ),
            }
            _record_v2_result(
                mapping_data,
                result_with_checkpoint,
                synced=True,
                entry_origin=(entry, origin),
            )
            _validate_candidate_mappings(prepared)
            for path, snapshot in snapshots.items():
                _validate_mapping_snapshot(path, snapshot)
            validate_reviewed_files()
            mapping_after = serialize_mapping_json(mapping_data)
            mapping_after_sha256 = hashlib.sha256(mapping_after).hexdigest()
            if mapping_after_sha256 == mapping_snapshot.sha256:
                if not sync_result.has_filesystem_changes:
                    raise RuntimeError(
                        "artifact apply produced neither filesystem nor "
                        "mapping changes"
                    )
                # A mode-only repair can leave provenance unchanged because
                # its managed checkpoint already declares the reviewed mode.
                # The unchanged mapping is existing authority for the staged
                # tree, so commit explicitly without binding an impossible
                # same-hash mapping transition.
                transaction.commit()
                return sync_result
            try:
                mapping_authority_path = (
                    mapping_path.resolve()
                    .relative_to(REPO_ROOT.resolve())
                    .as_posix()
                )
            except ValueError as exc:
                raise RuntimeError(
                    "provenance mapping escapes the repository root"
                ) from exc
            transaction.bind_authority(
                mapping_authority_path,
                mapping_snapshot.sha256,
                mapping_after_sha256,
            )
            try:
                if approved_files:
                    # The artifact journal owns the tree. This journal owns all
                    # mappings; recovery restores them before the artifact
                    # authority digest is consulted. Do not nest batch journals.
                    atomic_write_json_batch(
                        prepared,
                        expected_snapshots={
                            path: snapshots[path] for path in prepared
                        },
                        durable_guard=_durable_guard,
                        fault_injector=validate_reviewed_files,
                    )
                else:
                    atomic_write_json(
                        mapping_path,
                        mapping_data,
                        expected_snapshot=mapping_snapshot,
                    )
            except AtomicMappingWriteError as write_error:
                if write_error.replaced:
                    # A post-replace durability error commits the live tree
                    # only when the canonical mapping still carries the exact
                    # after-authority digest. A detached-parent replace must
                    # roll the tree back.
                    try:
                        installed = capture_mapping_snapshot(mapping_path)
                    except BaseException:
                        installed = None
                    if (
                        installed is not None
                        and installed.sha256 == mapping_after_sha256
                    ):
                        transaction.commit()
                raise
            transaction.commit()
            return sync_result


def _report_safe_result(result: dict) -> dict:
    skill = result.get("skill", {})
    safe = {
        "name": skill.get("name"),
        "source": skill.get("source"),
        "repository": skill.get("repo"),
        "status": result.get("changes"),
    }
    for key in (
        "reason",
        "resolved_ref",
        "current_commit",
        "path_commit",
        "relation",
        "ahead_by",
        "behind_by",
        "changed_files",
        "added_files",
        "removed_files",
        "moved_candidates",
        "main_source_blob",
        "license_evidence",
    ):
        if key in result:
            safe[key] = result[key]
    return safe


def write_report_json(path_value: str, report: dict) -> None:
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    path = Path(path_value)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _update_mapping_after_sync_locked(update: dict) -> None:
    """Update provenance timestamps for a successfully synced mapped skill."""
    skill = update["skill"]
    if skill.get("schema_version") == 2:
        raise RuntimeError(
            "v2 mapping writes require the artifact-set writer; legacy upstream "
            "timestamps must not be mutated"
        )
    mapping_path = skill.get("mapping_path")
    entry_index = skill.get("mapping_entry_index")
    if mapping_path is None or entry_index is None:
        return

    data = json.loads(Path(mapping_path).read_text(encoding="utf-8"))
    try:
        upstream = data["skills"][entry_index].setdefault("upstream", {})
    except (KeyError, IndexError):
        return
    today = date.today().isoformat()
    upstream["last_checked_at"] = today
    upstream["last_synced_at"] = today
    data["video"]["checked_at"] = today
    atomic_write_json(Path(mapping_path), data)


def _update_mapping_after_check_locked(result: dict) -> None:
    """Record a successful upstream comparison without claiming an unapplied sync."""
    skill = result["skill"]
    if skill.get("schema_version") == 2:
        raise RuntimeError(
            "v2 check recording requires an origin-aware writer; legacy upstream "
            "timestamps must not be mutated"
        )
    mapping_path = skill.get("mapping_path")
    entry_index = skill.get("mapping_entry_index")
    if mapping_path is None or entry_index is None:
        return

    path = Path(mapping_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        upstream = data["skills"][entry_index].setdefault("upstream", {})
    except (KeyError, IndexError):
        return

    today = date.today().isoformat()
    upstream["last_checked_at"] = today
    if result.get("changes") == "none":
        # Exact body equality proves the local snapshot is synchronized.
        upstream["last_synced_at"] = today
    data.setdefault("video", {})["checked_at"] = today
    atomic_write_json(path, data)


def update_mapping_after_sync(update: dict) -> None:
    """Serialize legacy mapping writes behind the cross-tool recovery lock."""
    mapping_path = update.get("skill", {}).get("mapping_path")
    if mapping_path is None:
        return _update_mapping_after_sync_locked(update)
    path = Path(mapping_path)
    with durable_batch_lock_and_recover(REPO_ROOT):
        with mapping_advisory_lock(path):
            _update_mapping_after_sync_locked(update)


def update_mapping_after_check(result: dict) -> None:
    """Serialize legacy check recording behind cross-tool recovery."""
    mapping_path = result.get("skill", {}).get("mapping_path")
    if mapping_path is None:
        return _update_mapping_after_check_locked(result)
    path = Path(mapping_path)
    with durable_batch_lock_and_recover(REPO_ROOT):
        with mapping_advisory_lock(path):
            _update_mapping_after_check_locked(result)


def _legacy_canonical_skill_root(local_path: Path) -> str | None:
    """Return the artifact-engine lock identity for a canonical legacy skill."""
    root = Path(os.path.abspath(REPO_ROOT))
    candidate = Path(os.path.abspath(local_path))
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        return None
    if (
        len(relative.parts) < 4
        or relative.parts[0] != "skills"
        or relative.name.lower() != "skill.md"
    ):
        return None
    return relative.parent.as_posix()


def apply_legacy_update(update: dict, token: str | None) -> int:
    """Apply an explicitly allowed v1 update under the global lock order.

    Provenance v1 remains a compatibility path, but it must not bypass recovery
    of a pending durable v2/ingest/reconcile batch.  The fixed order is global
    durable guard, mapping lock, then canonical skill lock.
    """
    skill = update["skill"]
    mapping_value = skill.get("mapping_path")
    mapping_path = Path(mapping_value) if mapping_value is not None else None
    skill_root = _legacy_canonical_skill_root(Path(skill["local_path"]))

    with durable_batch_lock_and_recover(REPO_ROOT):
        with ExitStack() as locks:
            if mapping_path is not None:
                locks.enter_context(mapping_advisory_lock(mapping_path))
            if skill_root is not None:
                engine = _load_artifact_engine()
                locks.enter_context(
                    engine.skill_advisory_lock(
                        REPO_ROOT,
                        skill_root,
                        timeout=10.0,
                    )
                )

            current_local = Path(skill["local_path"]).read_text(
                encoding="utf-8",
                errors="strict",
            )
            if current_local != skill["local_content"]:
                raise RuntimeError(
                    "legacy canonical skill changed after upstream check"
                )
            merged = apply_repository_adaptations(
                merge_frontmatter(
                    current_local,
                    update["upstream_content"],
                ),
                skill,
            )
            Path(skill["local_path"]).write_text(merged, encoding="utf-8")
            auxiliary_count = 0
            if skill["source"].startswith("github:"):
                auxiliary_count = sync_github_auxiliary_files(
                    skill,
                    update["upstream_path"],
                    token,
                )
            _update_mapping_after_sync_locked(update)
            return auxiliary_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check and synchronize upstream changes for tracked skills."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-only", action="store_true", help="Only report updates, don't apply")
    group.add_argument("--apply", action="store_true", help="Apply upstream updates to local files")
    parser.add_argument(
        "--record-check",
        action="store_true",
        help="With --check-only, explicitly record successful comparison timestamps",
    )
    parser.add_argument(
        "--record-review",
        action="store_true",
        help=(
            "With --check-only, explicitly advance successful monitor-only "
            "checkpoints after manual curation"
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing")
    parser.add_argument(
        "--allow-v1",
        action="store_true",
        help=(
            "Explicitly allow legacy/headerless v1 mappings and writes; "
            "disabled by default"
        ),
    )
    parser.add_argument("--source", help="Filter to a specific source (e.g. 'github:obra/superpowers')")
    parser.add_argument(
        "--reviewed-dependent",
        action="append",
        default=[],
        metavar="SLUG=SHA256",
        help="With --apply, approve compatibility of this exact composite body",
    )
    parser.add_argument(
        "--report-json",
        metavar="PATH",
        help="Write a machine-readable report atomically",
    )
    parser.add_argument("--exclude-source", action="append", default=[],
                        help="Exclude a source/repo (can be passed multiple times; accepts github:owner/repo or owner/repo)")
    args = parser.parse_args(argv)
    if args.record_check and not args.check_only:
        parser.error("--record-check requires --check-only")
    if args.record_review and not args.check_only:
        parser.error("--record-review requires --check-only")
    if args.record_check and args.record_review:
        parser.error("--record-check and --record-review are mutually exclusive")
    if args.report_json == "-":
        parser.error("--report-json requires a file path, not stdout")
    reviewed_dependents = {}
    for approval in args.reviewed_dependent:
        slug, separator, digest = approval.partition("=")
        if not separator or not re.fullmatch(r"[a-z0-9-]+", slug) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            parser.error("--reviewed-dependent must be SLUG=lowercase-SHA256")
        if not args.apply:
            parser.error("--reviewed-dependent requires --apply")
        if slug in reviewed_dependents:
            parser.error("duplicate --reviewed-dependent approval")
        reviewed_dependents[slug] = digest

    global _ACTIVE_ARTIFACT_PROVIDER, _ACTIVE_GITHUB_TOKEN
    _ACTIVE_ARTIFACT_PROVIDER = None
    _ACTIVE_GITHUB_TOKEN = _TOKEN_UNRESOLVED
    token = None
    skills = load_skills_with_upstream(allow_v1=args.allow_v1)

    if not args.allow_v1:
        for index, skill in enumerate(skills):
            if not (
                type(skill.get("schema_version")) is int
                and skill.get("schema_version") == 2
            ):
                skills[index] = {
                    **skill,
                    "load_error": (
                        skill.get("load_error")
                        or "legacy provenance requires explicit --allow-v1"
                    ),
                }
    
    if args.source:
        source = args.source.replace("github:", "")
        skills = [
            s
            for s in skills
            if s.get("repo") == source or s.get("source") == args.source
        ]
    if args.exclude_source:
        excluded = {item.replace("github:", "") for item in args.exclude_source}
        skills = [
            s
            for s in skills
            if s.get("repo") not in excluded
            and s.get("source") not in args.exclude_source
        ]
    
    print(
        f"Checking {len(skills)} active skills with external upstream sources...",
        flush=True,
    )
    print(
        "Input scope: strict provenance v2 active external mappings"
        + (
            " plus explicitly enabled legacy v1/frontmatter"
            if args.allow_v1
            else ""
        )
        + (
            "; licensed snapshot/local-only/archived entries are counted as "
            "expected_skipped, and bundles are checked by their bundle tooling."
        ),
        flush=True,
    )
    
    checked_results: list[dict] = []
    for skill in skills:
        print(
            f"  Checking: {skill['name']} ({skill.get('source', 'unknown')})",
            flush=True,
        )
        if skill.get("load_error"):
            result = {
                "skill": skill,
                "changes": "unavailable",
                "reason": skill["load_error"],
            }
        else:
            try:
                result = check_upstream_changes(skill, token)
            except Exception as exc:
                result = {
                    "skill": skill,
                    "changes": "unavailable",
                    "reason": f"upstream check raised {type(exc).__name__}: {exc}",
                }
        if result is None:
            result = {
                "skill": skill,
                "changes": "unavailable",
                "reason": "upstream check returned no result",
            }
        elif result.get("changes") not in {
            "none",
            "body_changed",
            "artifact_changed",
            "monitor_review",
            "upstream_rollback",
            "expected_skipped",
            "unavailable",
        }:
            result = {
                "skill": skill,
                "changes": "unavailable",
                "reason": (
                    "upstream check returned an unknown state: "
                    f"{result.get('changes')!r}"
                ),
            }
        checked_results.append(result)
        if result.get("changes") in {
            "body_changed",
            "artifact_changed",
            "monitor_review",
        }:
            print("    → Update available!", flush=True)
        elif result.get("changes") == "unavailable":
            print(f"    → Unavailable: {result.get('reason', 'unknown error')}", flush=True)

    counts = {
        "equal": 0,
        "changed": 0,
        "monitor_review": 0,
        "unavailable": 0,
        "rollback": 0,
        "expected_skipped": 0,
    }
    for result in checked_results:
        changes = result.get("changes")
        if changes == "none":
            counts["equal"] += 1
        elif changes == "monitor_review":
            counts["monitor_review"] += 1
        elif changes in {"body_changed", "artifact_changed"}:
            if _is_monitor_skill(result["skill"]):
                counts["monitor_review"] += 1
            else:
                counts["changed"] += 1
        elif changes == "upstream_rollback":
            counts["rollback"] += 1
        elif changes == "expected_skipped":
            counts["expected_skipped"] += 1
        else:
            counts["unavailable"] += 1

    total = len(skills)
    classified_total = sum(counts.values())
    if classified_total != total:
        raise RuntimeError(
            f"sync result accounting invariant failed: total={total}, "
            f"classified={classified_total}"
        )
    
    print(f"\n{'='*60}", flush=True)
    print(
        "Summary: "
        f"total={total} "
        f"equal={counts['equal']} "
        f"changed={counts['changed']} "
        f"monitor_review={counts['monitor_review']} "
        f"unavailable={counts['unavailable']} "
        f"rollback={counts['rollback']} "
        f"expected_skipped={counts['expected_skipped']}",
        flush=True,
    )
    print_monitor_rollbacks(checked_results)

    unavailable = [
        result
        for result in checked_results
        if result.get("changes") == "unavailable"
    ]
    if unavailable:
        print("\nUNEXPECTED UPSTREAM UNAVAILABLE:", flush=True)
        for result in unavailable:
            skill = result["skill"]
            print(
                f"  - {skill['name']}: {result.get('reason', 'unknown error')}",
                flush=True,
            )
            moved = result.get("moved_candidates") or {}
            for source_path, candidates in sorted(moved.items()):
                print(
                    f"    exact-blob move candidate for {source_path}: "
                    + ", ".join(candidates),
                    flush=True,
                )
    empty_input = total == 0
    if empty_input:
        if args.source:
            print(
                "\nERROR: no active upstream entries matched explicit "
                f"--source {args.source!r}; refusing an empty successful check.",
                flush=True,
            )
        else:
            print(
                "\nERROR: no active external upstream entries were discovered; "
                "refusing an empty successful check.",
                flush=True,
            )

    updates = [
        result
        for result in checked_results
        if result.get("changes")
        in {"body_changed", "artifact_changed", "monitor_review"}
    ]
    
    if updates:
        print("\nSkills with available updates:", flush=True)
        for u in updates:
            s = u["skill"]
            mode_note = " [monitor-only]" if _is_monitor_skill(s) else ""
            print(
                f"  - {s['name']} ({s['category']}) ← "
                f"{s.get('source', 'unknown')}{mode_note}",
                flush=True,
            )
        print_monitor_review_guidance(updates)
    
    auto_updates = [
        update
        for update in updates
        if (
            update["skill"].get("schema_version") == 1
            and update["skill"].get("sync_mode") != "monitor"
        )
        or (
            update["skill"].get("schema_version") == 2
            and (update["skill"].get("tracking") or {}).get("channel")
            in AUTO_CHANNELS
            and update["skill"].get("sync_mode") == "replace"
        )
    ]

    automation_state = (
        "failed"
        if unavailable or empty_input
        else "degraded"
        if counts["monitor_review"] or counts["rollback"]
        else "complete"
    )
    apply_errors: list[dict[str, str]] = []

    def emit_report(state: str = automation_state) -> None:
        if not args.report_json:
            return
        write_report_json(
            args.report_json,
            {
                "state": state,
                "mode": "apply" if args.apply else "check",
                "dry_run": bool(args.dry_run),
                "summary": {"total": total, **counts},
                "results": [
                    _report_safe_result(result) for result in checked_results
                ],
                "apply_errors": list(apply_errors),
            },
        )

    if unavailable or empty_input:
        emit_report("failed")
        return 1

    if not args.dry_run and (args.record_check or args.record_review):
        try:
            if args.record_review:
                record_v2_monitor_reviews(checked_results)
            else:
                record_v2_checks(checked_results)
            for result in checked_results:
                if result["skill"].get("schema_version", 1) == 1:
                    update_mapping_after_check(result)
        except Exception as exc:
            print(f"\nFailed to record check atomically: {exc}", flush=True)
            emit_report("failed")
            return 1

    if not updates:
        if counts["equal"] == total:
            print("All checked skills are equal to their authoritative upstream.", flush=True)
        else:
            print("No content updates are available; review non-equal states above.", flush=True)
        emit_report()
        return 2 if automation_state == "degraded" else 0

    if args.check_only:
        if auto_updates:
            print(
                "\nRun with --apply to download and apply auto-syncable updates; complete the monitor-only review separately.",
                flush=True,
            )
        else:
            print("\nAll reported updates are monitor-only; do the review above before closing the maintenance run.", flush=True)
        emit_report()
        return 2 if automation_state == "degraded" else 0
    
    if args.apply:
        if not args.dry_run:
            for result in checked_results:
                if (
                    result.get("changes") == "none"
                    and result["skill"].get("schema_version", 1) == 1
                ):
                    update_mapping_after_check(result)
        applied = 0
        apply_failed = False
        for u in updates:
            s = u["skill"]
            print(f"\n  Applying update: {s['name']}", flush=True)

            v2_channel = (s.get("tracking") or {}).get("channel")
            if (
                s.get("sync_mode") == "monitor"
                or v2_channel in MONITOR_CHANNELS
            ):
                print("    Skipped: upstream is monitored for manual curation; automatic body replacement is disabled.", flush=True)
                for line in monitor_review_guidance(u):
                    print(f"    {line}", flush=True)
                continue
            
            if args.dry_run:
                try:
                    if s.get("schema_version") == 2:
                        preview = apply_v2_update(u, dry_run=True)
                        print(
                            "    [DRY RUN] Artifact plan: "
                            f"{len(preview.changed)} changed, "
                            f"{len(preview.pruned)} pruned",
                            flush=True,
                        )
                    else:
                        print(
                            f"    [DRY RUN] Would merge upstream content into "
                            f"{s['local_path']}",
                            flush=True,
                        )
                    applied += 1
                except Exception as exc:
                    apply_failed = True
                    apply_errors.append(
                        {
                            "name": str(s.get("name", "unknown")),
                            "type": type(exc).__name__,
                            "message": str(exc),
                        }
                    )
                    print(
                        f"    [DRY RUN] FAILED: {type(exc).__name__}: {exc}",
                        flush=True,
                    )
                    break
                continue
            
            try:
                if s.get("schema_version") == 2:
                    sync_result = apply_v2_update(
                        u, reviewed_dependents=reviewed_dependents
                    )
                    print(
                        "    Updated artifact set: "
                        f"{len(sync_result.changed)} changed, "
                        f"{len(sync_result.pruned)} pruned",
                        flush=True,
                    )
                else:
                    aux_count = apply_legacy_update(u, token)
                    print(f"    Updated: {s['local_path']}", flush=True)
                    if aux_count:
                        print(
                            f"    Synced auxiliary files: {aux_count}",
                            flush=True,
                        )
                applied += 1
            except Exception as exc:
                apply_failed = True
                apply_errors.append(
                    {
                        "name": str(s.get("name", "unknown")),
                        "type": type(exc).__name__,
                        "message": str(exc),
                    }
                )
                print(
                    f"    FAILED; artifact transaction/mapping was not advanced: "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )
                break
        
        print(f"\nApplied {applied} updates.", flush=True)
        if not args.dry_run:
            print("Run the full pipeline to regenerate views:", flush=True)
            print("  python scripts/refresh_repo_views.py", flush=True)
        if apply_failed:
            emit_report("failed")
            return 1
    emit_report()
    return 2 if automation_state == "degraded" else 0


if __name__ == "__main__":
    raise SystemExit(main())
