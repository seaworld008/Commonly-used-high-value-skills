#!/usr/bin/env python3
"""Check and synchronize upstream changes for tracked skills.

Reads the provenance mapping to find skills with external upstream sources,
checks for newer versions, and optionally applies updates.

Usage:
    # Check only — report which skills have upstream updates
    python scripts/sync_upstream.py --check-only

    # Check and explicitly record successful comparison timestamps
    python scripts/sync_upstream.py --check-only --record-check

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
import http.client
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path, PurePosixPath
from time import sleep

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
    """Keep local enriched frontmatter and replace the body with upstream content."""
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

    merged_frontmatter = local_frontmatter
    if upstream_frontmatter is not None:
        if upstream_fm.get("name"):
            merged_frontmatter = update_frontmatter_field(merged_frontmatter, "name", upstream_fm["name"])
        if upstream_fm.get("description") and len(upstream_fm["description"]) >= 20:
            merged_frontmatter = update_frontmatter_field(
                merged_frontmatter,
                "description",
                yaml_quote(upstream_fm["description"]),
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
    return merged


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


def _v2_loaded_skill(entry: dict, mapping_path: Path, entry_index: int) -> dict | None:
    """Load one v2 entry from its unique origin/artifact owner.

    Legacy ``upstream`` is intentionally ignored.  If an active external entry
    has no unique artifact mapping to ``repo_skill``, return an unavailable
    descriptor so the caller fails closed instead of falling back to attacker-
    controlled or stale legacy metadata.
    """
    kind = entry.get("kind")
    status = entry.get("status")
    if status not in {"verified_in_repo", "in_house"}:
        return None
    if kind in {"snapshot", "in_house", "reference_only", "composite"}:
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
    origins = entry.get("origins")
    owner_candidates: list[tuple[int, int, dict, dict]] = []
    if isinstance(repo_skill, str) and isinstance(origins, list):
        for origin_index, origin in enumerate(origins):
            if not isinstance(origin, dict):
                continue
            artifacts = origin.get("artifacts")
            if not isinstance(artifacts, list):
                continue
            for artifact_index, artifact in enumerate(artifacts):
                if _artifact_source_for_target(artifact, repo_skill) is not None:
                    owner_candidates.append(
                        (origin_index, artifact_index, origin, artifact)
                    )

    if len(owner_candidates) != 1:
        return {
            **identity,
            "schema_version": 2,
            "source": "provenance:v2",
            "repo": "",
            "load_error": (
                "v2 provenance requires exactly one origin/artifact owner for "
                f"{repo_skill!r}; found {len(owner_candidates)}"
            ),
        }

    origin_index, artifact_index, origin, artifact = owner_candidates[0]
    tracking = origin.get("tracking")
    repo = origin.get("repo")
    origin_path = origin.get("path")
    upstream_path = _artifact_source_for_target(artifact, repo_skill)
    sync_mode = origin.get("sync_mode")
    ref = tracking.get("ref") if isinstance(tracking, dict) else None
    required = {
        "origin.repo": repo,
        "artifact.source": upstream_path,
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
        or not _safe_mapping_path(upstream_path)
    ):
        return {
            **identity,
            "schema_version": 2,
            "source": "provenance:v2",
            "repo": "",
            "load_error": "v2 owner contains an unsafe repo or artifact path",
        }

    # Explicit non-syncable modes are outside this command's active input
    # scope.  The summary states that scope rather than pretending they were
    # checked.
    if sync_mode in {"archived", "local-only"} or repo.startswith("local-repo/"):
        return None

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
        "last_synced_commit": (
            tracking.get("resolved_commit") if isinstance(tracking, dict) else None
        ),
        "path_commit": (
            tracking.get("path_commit") if isinstance(tracking, dict) else None
        ),
        "origin_index": origin_index,
        "artifact_index": artifact_index,
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


def check_upstream_changes(skill: dict, token: str | None) -> dict | None:
    """Check if upstream has changes for a skill."""
    if skill.get("load_error"):
        return {
            "skill": skill,
            "changes": "unavailable",
            "reason": skill["load_error"],
        }

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


def print_monitor_review_guidance(updates: list[dict]) -> None:
    monitor_updates = [u for u in updates if u["skill"].get("sync_mode") == "monitor"]
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


def atomic_write_json(path: Path, data: dict) -> None:
    """Atomically replace a JSON mapping without exposing a partial write."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            os.chmod(temporary_path, path.stat().st_mode & 0o777)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def update_mapping_after_sync(update: dict) -> None:
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


def update_mapping_after_check(result: dict) -> None:
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
    parser.add_argument("--exclude-source", action="append", default=[],
                        help="Exclude a source/repo (can be passed multiple times; accepts github:owner/repo or owner/repo)")
    args = parser.parse_args(argv)
    if args.record_check and not args.check_only:
        parser.error("--record-check requires --check-only")

    token = resolve_github_token()
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
        + "; archived/local-only mappings are excluded.",
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
        if result.get("changes") in {"body_changed", "monitor_review"}:
            print(f"    → Update available!", flush=True)
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
        elif changes == "body_changed":
            if result["skill"].get("sync_mode") == "monitor":
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
        if result.get("changes") in {"body_changed", "monitor_review"}
    ]
    
    if updates:
        print("\nSkills with available updates:", flush=True)
        for u in updates:
            s = u["skill"]
            mode = s.get("sync_mode", "replace")
            mode_note = " [monitor-only]" if mode == "monitor" else ""
            print(
                f"  - {s['name']} ({s['category']}) ← "
                f"{s.get('source', 'unknown')}{mode_note}",
                flush=True,
            )
        print_monitor_review_guidance(updates)
    
    auto_updates = [u for u in updates if u["skill"].get("sync_mode") != "monitor"]
    v2_record_blocked = args.record_check and any(
        skill.get("schema_version") == 2 for skill in skills
    )
    v2_apply_blocked = args.apply and any(
        update["skill"].get("schema_version") == 2 for update in updates
    )

    if v2_record_blocked:
        print(
            "\nBlocked: --record-check cannot write provenance v2 until the "
            "origin-aware artifact-set writer is available; no files were changed.",
            flush=True,
        )
    if v2_apply_blocked:
        print(
            "\nBlocked: --apply cannot mutate provenance v2 with the legacy "
            "single-file/sibling writer; no files were changed.",
            flush=True,
        )
    if unavailable or empty_input or v2_record_blocked or v2_apply_blocked:
        return 2 if (v2_record_blocked or v2_apply_blocked) else 1

    if not args.dry_run and args.record_check:
        for result in checked_results:
            update_mapping_after_check(result)

    if not updates:
        if counts["equal"] == total:
            print("All checked skills are equal to their authoritative upstream.", flush=True)
        else:
            print("No content updates are available; review non-equal states above.", flush=True)
        return 0

    if args.check_only:
        if auto_updates:
            print(
                "\nRun with --apply to download and apply auto-syncable updates; complete the monitor-only review separately.",
                flush=True,
            )
        else:
            print("\nAll reported updates are monitor-only; do the review above before closing the maintenance run.", flush=True)
        return 0
    
    if args.apply:
        if not args.dry_run:
            for result in checked_results:
                if (
                    result.get("changes") == "none"
                    and result["skill"].get("schema_version", 1) == 1
                ):
                    update_mapping_after_check(result)
        applied = 0
        for u in updates:
            s = u["skill"]
            print(f"\n  Applying update: {s['name']}", flush=True)

            if s.get("sync_mode") == "monitor":
                print("    Skipped: upstream is monitored for manual curation; automatic body replacement is disabled.", flush=True)
                for line in monitor_review_guidance(u):
                    print(f"    {line}", flush=True)
                continue
            
            if args.dry_run:
                print(f"    [DRY RUN] Would merge upstream content into {s['local_path']}", flush=True)
                applied += 1
                continue
            
            merged = apply_repository_adaptations(
                merge_frontmatter(s["local_content"], u["upstream_content"]),
                s,
            )
            s["local_path"].write_text(merged, encoding="utf-8")
            print(f"    Updated: {s['local_path']}", flush=True)
            if s["source"].startswith("github:"):
                aux_count = sync_github_auxiliary_files(s, u["upstream_path"], token)
                if aux_count:
                    print(f"    Synced auxiliary files: {aux_count}", flush=True)
            update_mapping_after_sync(u)
            applied += 1
        
        print(f"\nApplied {applied} updates.", flush=True)
        if not args.dry_run:
            print("Run the full pipeline to regenerate views:", flush=True)
            print("  python scripts/refresh_repo_views.py", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
