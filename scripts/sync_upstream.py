#!/usr/bin/env python3
"""Check and synchronize upstream changes for tracked skills.

Reads the provenance mapping to find skills with external upstream sources,
checks for newer versions, and optionally applies updates.

Usage:
    # Check only — report which skills have upstream updates
    python scripts/sync_upstream.py --check-only

    # Apply updates — download and replace with upstream versions
    python scripts/sync_upstream.py --apply

    # Dry run — show what would be updated without writing
    python scripts/sync_upstream.py --apply --dry-run

    # Check a specific source only
    python scripts/sync_upstream.py --check-only --source "github:alirezarezvani/claude-skills"
"""
from __future__ import annotations

import argparse
import base64
import http.client
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
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
_GITHUB_REF_CACHE: dict[tuple[str, str], str | None] = {}
_GITHUB_FILE_BYTES_CACHE: dict[tuple[str, str, str], bytes] = {}
_COMMON_REFERENCE_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])(_common/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\.[A-Za-z0-9]+)"
)
_SKILL_ROOT_REFERENCE_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])((?:reference|references)/"
    r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\.[A-Za-z0-9]+)"
)
_MAX_REFERENCE_SCAN_BYTES = 2_000_000
_MAX_REFERENCE_SCAN_FILES = 2_000
_MAX_REFERENCE_FETCHES = 256


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
                return resp.read().decode("utf-8", errors="replace")
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


def github_api_get(url: str, token: str | None = None) -> dict | list | None:
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


def resolve_github_ref(repo: str, ref: str, token: str | None = None) -> str | None:
    """Resolve a moving branch/tag ref to the immutable commit SHA GitHub serves."""
    cache_key = (repo, ref)
    if cache_key in _GITHUB_REF_CACHE:
        return _GITHUB_REF_CACHE[cache_key]
    if re.fullmatch(r"[0-9a-fA-F]{40}", ref):
        resolved = ref.lower()
        _GITHUB_REF_CACHE[cache_key] = resolved
        return resolved
    encoded_ref = urllib.parse.quote(ref, safe="")
    data = github_api_get(
        f"https://api.github.com/repos/{repo}/commits/{encoded_ref}",
        token,
    )
    if not isinstance(data, dict):
        _GITHUB_REF_CACHE[cache_key] = None
        return None
    sha = str(data.get("sha", ""))
    if not re.fullmatch(r"[0-9a-fA-F]{40}", sha):
        print(
            f"    Warning: GitHub did not return a full commit SHA for {repo}@{ref}",
            file=sys.stderr,
        )
        _GITHUB_REF_CACHE[cache_key] = None
        return None
    resolved = sha.lower()
    _GITHUB_REF_CACHE[cache_key] = resolved
    return resolved


def fetch_url_bytes(
    url: str,
    token: str | None = None,
    *,
    quiet_404: bool = False,
    retries: int = 1,
) -> bytes | None:
    """Fetch raw bytes without decoding binary auxiliary assets as UTF-8."""
    headers = {"User-Agent": "skills-sync-bot"}
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            last_error = exc
            break
        except NETWORK_ERRORS as exc:
            last_error = exc
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
        fallback = fetch_github_raw_via_api_bytes(url, token)
        if fallback is not None:
            return fallback
    return None


def fetch_github_raw_via_api_bytes(
    raw_url: str,
    token: str | None = None,
) -> bytes | None:
    """Binary-safe Contents API fallback for raw.githubusercontent.com URLs."""
    match = re.match(
        r"https://raw\.githubusercontent\.com/([^/]+/[^/]+)/([^/]+)/(.*)",
        raw_url,
    )
    if not match:
        return None

    repo, ref, path = match.groups()
    encoded_path = urllib.parse.quote(path, safe="/")
    encoded_ref = urllib.parse.quote(ref, safe="")
    data = github_api_get(
        f"https://api.github.com/repos/{repo}/contents/{encoded_path}?ref={encoded_ref}",
        token,
    )
    if not isinstance(data, dict) or data.get("type") != "file":
        return None

    content = data.get("content", "")
    if data.get("encoding") == "base64":
        try:
            return base64.b64decode(content)
        except (TypeError, ValueError):
            return None
    if isinstance(content, str):
        return content.encode("utf-8")
    return None


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


def remove_generated_quality_supplement(content: str) -> str:
    """Drop only the regenerable quality block, retaining hand-curated guidance."""
    return re.sub(
        r"\n+<!-- LOCAL-QUALITY-SUPPLEMENT:START -->.*?"
        r"<!-- LOCAL-QUALITY-SUPPLEMENT:END -->\s*",
        "\n\n",
        content,
        flags=re.DOTALL,
    ).rstrip() + "\n"


def extract_local_curation_supplements(content: str) -> list[str]:
    """Return repository-owned curation blocks so upstream replacement cannot erase them."""
    pattern = re.compile(
        r"<!-- LOCAL-CURATION-SUPPLEMENT:START -->.*?"
        r"<!-- LOCAL-CURATION-SUPPLEMENT:END -->",
        re.DOTALL,
    )
    return [match.group(0).strip() for match in pattern.finditer(content)]


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
<!-- LOCAL-QUALITY-SUPPLEMENT:END -->
"""


def ensure_quality_floor(content: str, skill_name: str) -> str:
    cleaned = remove_generated_quality_supplement(content)
    if not needs_quality_supplement(cleaned):
        return cleaned
    return cleaned.rstrip() + "\n" + build_quality_supplement(skill_name).lstrip()


def merge_frontmatter(local_content: str, upstream_content: str) -> str:
    """Keep local enriched frontmatter and replace the body with upstream content."""
    local_fm = parse_frontmatter(local_content)
    upstream_fm = parse_frontmatter(upstream_content)
    local_curations = extract_local_curation_supplements(local_content)
    local_frontmatter, _ = split_frontmatter(local_content)
    upstream_frontmatter, upstream_body = split_frontmatter(upstream_content)

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
        if (
            not local_curations
            and upstream_fm.get("description")
            and len(upstream_fm["description"]) >= 20
        ):
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

    cleaned_upstream_body = remove_local_supplements(upstream_body).strip()
    body_parts = [cleaned_upstream_body]
    body_parts.extend(local_curations)
    merged_body = "\n\n".join(part for part in body_parts if part).rstrip() + "\n"
    merged = merged_frontmatter.rstrip() + "\n" + merged_body
    return ensure_quality_floor(merged, local_fm.get("name", upstream_fm.get("name", "synced-skill")))


def load_skills_from_source_mappings() -> list[dict]:
    """Load externally tracked skills from docs/sources/*.skills.json."""
    results = []
    for mapping_path in sorted(SOURCE_MAPPINGS_DIR.glob("*.skills.json")):
        if mapping_path.name == PROVENANCE_FILE.name:
            continue
        data = json.loads(mapping_path.read_text(encoding="utf-8"))
        for entry_index, entry in enumerate(data.get("skills", [])):
            upstream = entry.get("upstream") or {}
            repo = upstream.get("repo")
            repo_skill = entry.get("repo_skill")
            upstream_path = upstream.get("path")
            if upstream.get("sync_mode") in {"archived", "local-only"}:
                continue
            if not repo or repo.startswith("local-repo/") or not repo_skill or not upstream_path:
                continue
            local_path = REPO_ROOT / repo_skill
            if not local_path.exists():
                print(f"    Warning: mapped local skill missing: {repo_skill}", file=sys.stderr)
                continue
            content = local_path.read_text(encoding="utf-8", errors="replace")
            fm = parse_frontmatter(content)
            skill_name = fm.get("name", entry.get("normalized_slug") or entry.get("video_name") or local_path.parent.name)
            results.append(
                {
                    "name": skill_name,
                    "category": local_path.parent.parent.name,
                    "source": f"github:{repo}",
                    "repo": repo,
                    "local_path": local_path,
                    "source_url": entry.get("source", ""),
                    "local_content": content,
                    "upstream_path": upstream_path,
                    "ref": upstream.get("ref", "main"),
                    "sync_mode": upstream.get("sync_mode", "replace"),
                    "last_synced_commit": upstream.get("last_synced_commit"),
                    "mapping_path": mapping_path,
                    "mapping_entry_index": entry_index,
                }
            )
    return results


def load_non_syncable_mapped_paths() -> set[Path]:
    """Return local skill paths explicitly excluded from automatic upstream sync."""
    paths: set[Path] = set()
    for mapping_path in sorted(SOURCE_MAPPINGS_DIR.glob("*.skills.json")):
        if mapping_path.name == PROVENANCE_FILE.name:
            continue
        data = json.loads(mapping_path.read_text(encoding="utf-8"))
        for entry in data.get("skills", []):
            upstream = entry.get("upstream") or {}
            if upstream.get("sync_mode") not in {"archived", "local-only"}:
                continue
            repo_skill = entry.get("repo_skill")
            if repo_skill:
                paths.add((REPO_ROOT / repo_skill).resolve())
    return paths


def load_skills_with_upstream() -> list[dict]:
    """Load skills that have external upstream sources.

    Prefer exact paths from docs/sources/*.skills.json, then fall back to
    frontmatter-only github sources that are not yet mapped.
    """
    mapped = load_skills_from_source_mappings()
    mapped_paths = {item["local_path"].resolve() for item in mapped}
    mapped_paths.update(load_non_syncable_mapped_paths())
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
            })
        elif source in ("skills.sh", "clawhub", "community"):
            # These don't have auto-syncable upstreams yet
            pass
    return mapped + results


def check_upstream_changes(skill: dict, token: str | None) -> dict | None:
    """Check if upstream has changes for a skill."""
    repo = skill["repo"]
    skill_name = skill["name"]
    source_ref = skill.get("ref", "main")
    resolved_commit = resolve_github_ref(repo, source_ref, token)
    skill["resolved_commit"] = resolved_commit
    if resolved_commit is None:
        skill["_upstream_fetch_failed"] = True
        print(
            f"    Warning: unable to freeze {repo}@{source_ref}; skipping unsafe moving-ref fetch",
            file=sys.stderr,
        )
        return None
    fetch_ref = resolved_commit
    
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
        url = github_raw_url(repo, path, fetch_ref)
        try:
            upstream_content = fetch_url(
                url,
                token,
                quiet_404=len(candidate_paths) > 1 and path != candidate_paths[-1],
            )
        except TypeError:
            upstream_content = fetch_url(url, token)
        if upstream_content:
            skill["_upstream_fetch_failed"] = False
            # Compare content (ignore frontmatter for diff)
            local_body = comparable_body(skill["local_content"])
            upstream_body = comparable_body(upstream_content)
            
            if local_body != upstream_body:
                return {
                    "skill": skill,
                    "upstream_path": path,
                    "upstream_content": upstream_content,
                    "changes": "body_changed",
                    "resolved_commit": resolved_commit,
                }
            if (
                skill.get("mapping_path") is not None
                and resolved_commit
                and resolved_commit != skill.get("last_synced_commit")
            ):
                return {
                    "skill": skill,
                    "upstream_path": path,
                    "upstream_content": upstream_content,
                    "changes": "upstream_commit_changed",
                    "resolved_commit": resolved_commit,
                }
            return None  # No body or immutable upstream revision change
    
    skill["_upstream_fetch_failed"] = True
    return None  # Could not find upstream file


def expand_related_auxiliary_updates(updates: list[dict], skills: list[dict]) -> list[dict]:
    """Mirror every mapped skill in repos that have an auto-syncable update.

    A repository commit can change only ``reference/`` or assets while leaving a
    sibling skill body byte-identical. Expanding at repository scope prevents
    those reference-only changes from being silently omitted.
    """
    expanded = list(updates)
    updated_repos = {
        update["skill"]["repo"]
        for update in updates
        if update["skill"].get("sync_mode") != "monitor"
    }
    existing_paths = {str(update["skill"].get("local_path")) for update in expanded}

    for skill in skills:
        if skill.get("repo") not in updated_repos:
            continue
        if skill.get("sync_mode") == "monitor" or not skill.get("upstream_path"):
            continue
        if skill.get("_upstream_fetch_failed"):
            continue
        local_path_key = str(skill.get("local_path"))
        if local_path_key in existing_paths:
            continue
        resolved_commit = skill.get("resolved_commit")
        if not resolved_commit:
            continue
        expanded.append(
            {
                "skill": skill,
                "upstream_path": skill["upstream_path"],
                "changes": "related_repo_auxiliary_sync",
                "resolved_commit": resolved_commit,
            }
        )
        existing_paths.add(local_path_key)
    return expanded


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


def _is_legal_auxiliary_name(name: str) -> bool:
    return bool(re.fullmatch(r"(?:licen[cs]e|notice)(?:[._-].*)?", name, re.IGNORECASE))


def _is_preserved_local_auxiliary(relative_path: Path) -> bool:
    if len(relative_path.parts) == 1 and relative_path.name.lower() == "skill.md":
        return True
    return _is_legal_auxiliary_name(relative_path.name)


def _decode_github_file_content(data: object) -> bytes | None:
    if not isinstance(data, dict) or data.get("type") != "file":
        return None
    content = data.get("content", "")
    if data.get("encoding") == "base64":
        try:
            return base64.b64decode(content)
        except (TypeError, ValueError):
            return None
    if isinstance(content, str):
        return content.encode("utf-8")
    return None


def _fetch_github_auxiliary_item(
    item: dict,
    ref: str,
    token: str | None,
) -> bytes | None:
    download_url = item.get("download_url")
    if download_url:
        return fetch_url_bytes(str(download_url), token)

    item_api_url = item.get("url")
    if not item_api_url:
        return None
    separator = "&" if "?" in str(item_api_url) else "?"
    encoded_ref = urllib.parse.quote(ref, safe="")
    data = github_api_get(f"{item_api_url}{separator}ref={encoded_ref}", token)
    return _decode_github_file_content(data)


def _fetch_github_repo_file(
    repo: str,
    path: str,
    ref: str,
    token: str | None,
) -> bytes | None:
    cache_key = (repo, ref, path)
    if cache_key in _GITHUB_FILE_BYTES_CACHE:
        return _GITHUB_FILE_BYTES_CACHE[cache_key]
    encoded_path = urllib.parse.quote(path, safe="/")
    encoded_ref = urllib.parse.quote(ref, safe="")
    data = github_api_get(
        f"https://api.github.com/repos/{repo}/contents/{encoded_path}?ref={encoded_ref}",
        token,
    )
    payload = _decode_github_file_content(data)
    if payload is not None:
        _GITHUB_FILE_BYTES_CACHE[cache_key] = payload
    return payload


def _safe_dependency_relative_path(raw_path: str, allowed_root: str) -> Path | None:
    relative_path = Path(raw_path)
    if relative_path.is_absolute() or not relative_path.parts:
        return None
    if relative_path.parts[0] != allowed_root:
        return None
    if any(part in {"", ".", ".."} for part in relative_path.parts):
        return None
    return relative_path


def _direct_common_references(skill_path: Path) -> set[Path]:
    """Find safe direct ``_common/...`` dependencies declared by one text file."""
    try:
        content = skill_path.read_text(encoding="utf-8")
    except OSError:
        return set()
    references: set[Path] = set()
    for raw_path in _COMMON_REFERENCE_RE.findall(content):
        relative_path = _safe_dependency_relative_path(raw_path, "_common")
        if relative_path is not None:
            references.add(relative_path)
    return references


def _materialize_reference_closure(
    staging_dir: Path,
    repo: str,
    upstream_dir: str,
    ref: str,
    token: str | None,
) -> tuple[int, list[str], list[str], bool]:
    """Materialize safe transitive shared/reference dependencies to a fixed point.

    Only repository-root ``_common/...`` and current-skill-root
    ``reference/...``/``references/...`` paths are eligible. Missing paths are
    reported as upstream defects but do not invalidate an otherwise complete
    mirror; sibling-skill paths and traversal attempts are never fetched.
    """
    queued: set[Path] = set()
    queue: list[Path] = []
    for path in sorted(staging_dir.rglob("*")):
        if path.is_file():
            relative_path = path.relative_to(staging_dir)
            queue.append(relative_path)
            queued.add(relative_path)

    scanned: set[Path] = set()
    defects: set[str] = set()
    unsafe: set[str] = set()
    added = 0
    fetches = 0
    closure_complete = True
    normalized_upstream_dir = "" if upstream_dir in {"", "."} else upstream_dir.strip("/")

    while queue:
        if len(scanned) >= _MAX_REFERENCE_SCAN_FILES:
            defects.add(
                f"reference closure scan limit exceeded ({_MAX_REFERENCE_SCAN_FILES} files)"
            )
            closure_complete = False
            break
        source_relative = queue.pop(0)
        if source_relative in scanned:
            continue
        scanned.add(source_relative)
        source_path = staging_dir / source_relative
        try:
            if source_path.stat().st_size > _MAX_REFERENCE_SCAN_BYTES:
                continue
            content = source_path.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        candidates = [
            ("_common", raw_path)
            for raw_path in _COMMON_REFERENCE_RE.findall(content)
        ]
        candidates.extend(
            (raw_path.split("/", 1)[0], raw_path)
            for raw_path in _SKILL_ROOT_REFERENCE_RE.findall(content)
        )

        for allowed_root, raw_path in candidates:
            relative_path = _safe_dependency_relative_path(raw_path, allowed_root)
            if relative_path is None:
                unsafe.add(raw_path)
                continue

            target = staging_dir / relative_path
            if target.is_file():
                if relative_path not in queued:
                    queue.append(relative_path)
                    queued.add(relative_path)
                continue
            if target.exists():
                defects.add(f"{source_relative.as_posix()} -> {raw_path} (not a file)")
                continue

            if allowed_root == "_common":
                repo_path = relative_path.as_posix()
            else:
                repo_path = "/".join(
                    part
                    for part in (normalized_upstream_dir, relative_path.as_posix())
                    if part
                )
            if fetches >= _MAX_REFERENCE_FETCHES:
                defects.add(
                    f"reference closure fetch limit exceeded ({_MAX_REFERENCE_FETCHES} files)"
                )
                closure_complete = False
                queue.clear()
                break
            fetches += 1
            payload = _fetch_github_repo_file(repo, repo_path, ref, token)
            if payload is None:
                defects.add(f"{source_relative.as_posix()} -> {raw_path}")
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            added += 1
            if relative_path not in queued:
                queue.append(relative_path)
                queued.add(relative_path)

    return added, sorted(defects), sorted(unsafe), closure_complete


def _prune_stale_auxiliary_files(local_dir: Path, upstream_files: set[Path]) -> int:
    """Delete stale mirrored files while retaining canonical and legal local files."""
    removed = 0
    paths = sorted(
        local_dir.rglob("*"),
        key=lambda path: len(path.relative_to(local_dir).parts),
        reverse=True,
    )
    for path in paths:
        relative_path = path.relative_to(local_dir)
        if path.is_symlink() or path.is_file():
            if relative_path in upstream_files or _is_preserved_local_auxiliary(relative_path):
                continue
            path.unlink()
            removed += 1

    for path in paths:
        if not path.is_dir() or path.is_symlink():
            continue
        try:
            path.rmdir()
        except OSError:
            pass
    return removed


def _skill_path_boundary_error(skill: dict, local_dir: Path, canonical_path: Path) -> str | None:
    """Reject lexical/resolved escapes and symlinks below the repository root."""
    repo_root = Path(skill.get("repo_root", REPO_ROOT))
    try:
        relative_dir = local_dir.relative_to(repo_root)
    except ValueError:
        return f"skill directory is outside repository root: {local_dir}"

    current = repo_root
    for part in relative_dir.parts:
        current = current / part
        if current.is_symlink():
            return f"repository-relative skill parent is a symlink: {current}"

    if canonical_path.parent != local_dir:
        return f"canonical skill is not a direct child of its skill directory: {canonical_path}"
    if canonical_path.is_symlink():
        return f"canonical skill is a symlink: {canonical_path}"

    try:
        resolved_root = repo_root.resolve(strict=True)
        resolved_dir = local_dir.resolve(strict=True)
        resolved_canonical = canonical_path.resolve(strict=True)
    except OSError as exc:
        return f"unable to resolve skill path boundary: {exc}"
    if not resolved_dir.is_relative_to(resolved_root):
        return f"resolved skill directory escapes repository root: {resolved_dir}"
    if not resolved_canonical.is_relative_to(resolved_dir):
        return f"resolved canonical skill escapes its skill directory: {resolved_canonical}"
    return None


def sync_github_auxiliary_files(
    skill: dict,
    upstream_path: str,
    token: str | None,
    *,
    ref: str | None = None,
    canonical_content: str | None = None,
) -> int:
    """Recursively mirror the upstream skill subtree beside canonical SKILL.md.

    Root ``skill.md`` is the upstream body source and must never overwrite the
    repository's enriched ``SKILL.md``. Nested skill files are real payload and
    are retained. Pruning runs only after every directory and file was fetched,
    preventing a transient API failure from deleting a valid local mirror.
    """
    repo = skill["repo"]
    upstream_dir = str(Path(upstream_path).parent)
    fetch_ref = ref or skill.get("ref", "main")
    local_dir = skill["local_path"].parent
    canonical_path = skill["local_path"]
    upstream_files: set[Path] = set()
    synced = 0
    complete = True
    skill["_auxiliary_sync_complete"] = False
    skill["_upstream_reference_defects"] = []
    skill["_unsafe_reference_paths"] = []

    boundary_error = _skill_path_boundary_error(skill, local_dir, canonical_path)
    if boundary_error:
        print(
            f"    Warning: refusing unsafe auxiliary mirror path: {boundary_error}",
            file=sys.stderr,
        )
        return 0

    try:
        with tempfile.TemporaryDirectory(
            prefix=f".{local_dir.name}.sync-",
            dir=local_dir.parent,
        ) as temporary_root:
            staging_dir = Path(temporary_root) / "candidate"
            staging_dir.mkdir()

            # Build a complete candidate tree without touching the live skill.
            # Preserve canonical root skill files and local legal notices only.
            for existing in local_dir.rglob("*"):
                relative_path = existing.relative_to(local_dir)
                if not (
                    _is_preserved_local_auxiliary(relative_path)
                    and (existing.is_file() or existing.is_symlink())
                ):
                    continue
                if existing.is_symlink():
                    raise OSError(f"protected local file is a symlink: {existing}")
                target = staging_dir / relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(existing, target)

            staged_canonical = staging_dir / canonical_path.name
            if canonical_content is not None:
                staged_canonical.write_text(canonical_content, encoding="utf-8")
            elif not staged_canonical.exists():
                shutil.copy2(canonical_path, staged_canonical)

            def walk(api_path: str, relative_dir: Path) -> None:
                nonlocal complete, synced
                encoded_path = urllib.parse.quote(api_path, safe="/")
                encoded_ref = urllib.parse.quote(fetch_ref, safe="")
                api_url = (
                    f"https://api.github.com/repos/{repo}/contents/{encoded_path}"
                    f"?ref={encoded_ref}"
                )
                data = github_api_get(api_url, token)
                if not isinstance(data, list):
                    complete = False
                    return

                for raw_item in data:
                    if not isinstance(raw_item, dict):
                        complete = False
                        continue
                    item_type = raw_item.get("type")
                    name = str(raw_item.get("name", ""))
                    if not name or name in {".", ".."} or "/" in name or "\\" in name:
                        complete = False
                        continue
                    relative_path = relative_dir / name
                    item_path = str(raw_item.get("path") or f"{api_path.rstrip('/')}/{name}")

                    if item_type == "dir":
                        walk(item_path, relative_path)
                        continue
                    if item_type != "file":
                        complete = False
                        continue
                    if not relative_dir.parts and name.lower() == "skill.md":
                        continue

                    target = staging_dir / relative_path
                    upstream_files.add(relative_path)
                    if _is_legal_auxiliary_name(name) and target.exists():
                        continue
                    payload = _fetch_github_auxiliary_item(raw_item, fetch_ref, token)
                    if payload is None:
                        complete = False
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(payload)
                    synced += 1

            walk(upstream_dir, Path())
            if complete:
                added, defects, unsafe, closure_complete = _materialize_reference_closure(
                    staging_dir,
                    repo,
                    upstream_dir,
                    fetch_ref,
                    token,
                )
                synced += added
                complete = complete and closure_complete
                skill["_upstream_reference_defects"] = defects
                skill["_unsafe_reference_paths"] = unsafe
                for defect in defects:
                    print(
                        f"    Warning: upstream reference defect (non-fatal): {defect}",
                        file=sys.stderr,
                    )
                for unsafe_path in unsafe:
                    print(
                        f"    Warning: unsafe reference path ignored: {unsafe_path}",
                        file=sys.stderr,
                    )

            if not complete:
                print(
                    "    Warning: auxiliary mirror was incomplete; transaction discarded",
                    file=sys.stderr,
                )
                return synced

            old_files = {
                path.relative_to(local_dir)
                for path in local_dir.rglob("*")
                if path.is_file() or path.is_symlink()
            }
            staged_files = {
                path.relative_to(staging_dir)
                for path in staging_dir.rglob("*")
                if path.is_file()
            }
            removed = len(old_files - staged_files)

            backup_dir = Path(temporary_root) / "previous"
            os.replace(local_dir, backup_dir)
            try:
                os.replace(staging_dir, local_dir)
            except BaseException:
                os.replace(backup_dir, local_dir)
                raise
            shutil.rmtree(backup_dir, ignore_errors=True)

            skill["_auxiliary_sync_complete"] = True
            if removed:
                print(f"    Pruned stale auxiliary files: {removed}", flush=True)
            return synced
    except OSError as exc:
        print(f"    Warning: auxiliary mirror transaction failed: {exc}", file=sys.stderr)
        return synced


def update_mapping_after_sync(update: dict) -> None:
    """Update provenance timestamps for a successfully synced mapped skill."""
    skill = update["skill"]
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
    if update.get("resolved_commit"):
        upstream["last_synced_commit"] = update["resolved_commit"]
    data["video"]["checked_at"] = today
    Path(mapping_path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check and synchronize upstream changes for tracked skills."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-only", action="store_true", help="Only report updates, don't apply")
    group.add_argument("--apply", action="store_true", help="Apply upstream updates to local files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing")
    parser.add_argument("--source", help="Filter to a specific source (e.g. 'github:obra/superpowers')")
    parser.add_argument("--exclude-source", action="append", default=[],
                        help="Exclude a source/repo (can be passed multiple times; accepts github:owner/repo or owner/repo)")
    args = parser.parse_args()

    token = resolve_github_token()
    skills = load_skills_with_upstream()
    
    if args.source:
        source = args.source.replace("github:", "")
        skills = [s for s in skills if s["repo"] == source or s["source"] == args.source]
    if args.exclude_source:
        excluded = {item.replace("github:", "") for item in args.exclude_source}
        skills = [s for s in skills if s["repo"] not in excluded and s["source"] not in args.exclude_source]
    
    print(f"Checking {len(skills)} skills with external upstream sources...", flush=True)
    
    updates = []
    for skill in skills:
        print(f"  Checking: {skill['name']} ({skill['source']})", flush=True)
        update = check_upstream_changes(skill, token)
        if update:
            updates.append(update)
            print(f"    → Update available!", flush=True)

    direct_update_count = len(updates)
    updates = expand_related_auxiliary_updates(updates, skills)
    related_count = len(updates) - direct_update_count
    if related_count:
        print(
            f"  Added {related_count} same-repository skill(s) for auxiliary mirror sync.",
            flush=True,
        )
    
    print(f"\n{'='*60}", flush=True)
    print(f"Results: {len(updates)} updates available out of {len(skills)} checked", flush=True)
    
    if not updates:
        print("All skills are up to date.", flush=True)
        return
    
    print("\nSkills with available updates:", flush=True)
    for u in updates:
        s = u["skill"]
        mode = s.get("sync_mode", "replace")
        mode_note = " [monitor-only]" if mode == "monitor" else ""
        print(f"  - {s['name']} ({s['category']}) ← {s['source']}{mode_note}", flush=True)
    print_monitor_review_guidance(updates)
    
    auto_updates = [u for u in updates if u["skill"].get("sync_mode") != "monitor"]

    if args.check_only:
        if auto_updates:
            print(
                "\nRun with --apply to download and apply auto-syncable updates; complete the monitor-only review separately.",
                flush=True,
            )
        else:
            print("\nAll reported updates are monitor-only; do the review above before closing the maintenance run.", flush=True)
        return
    
    if args.apply:
        applied = 0
        failed = 0
        for u in updates:
            s = u["skill"]
            print(f"\n  Applying update: {s['name']}", flush=True)

            if s.get("sync_mode") == "monitor":
                print("    Skipped: upstream is monitored for manual curation; automatic body replacement is disabled.", flush=True)
                for line in monitor_review_guidance(u):
                    print(f"    {line}", flush=True)
                continue
            
            if args.dry_run:
                action = (
                    "merge upstream body and mirror auxiliaries"
                    if u.get("changes") == "body_changed"
                    else "mirror auxiliaries and record the immutable upstream revision"
                )
                print(f"    [DRY RUN] Would {action}: {s['local_path']}", flush=True)
                applied += 1
                continue

            merged = None
            if u.get("changes") == "body_changed":
                merged = merge_frontmatter(s["local_content"], u["upstream_content"])
            else:
                print("    Body unchanged; syncing auxiliary subtree.", flush=True)
            if s["source"].startswith("github:"):
                aux_count = sync_github_auxiliary_files(
                    s,
                    u["upstream_path"],
                    token,
                    ref=u.get("resolved_commit"),
                    canonical_content=merged,
                )
                if aux_count:
                    print(f"    Synced auxiliary files: {aux_count}", flush=True)
                if not s.get("_auxiliary_sync_complete", False):
                    print(
                        "    Mapping not advanced because the auxiliary mirror was incomplete.",
                        file=sys.stderr,
                    )
                    failed += 1
                    continue
            elif merged is not None:
                s["local_path"].write_text(merged, encoding="utf-8")
            if merged is not None:
                print(f"    Updated body: {s['local_path']}", flush=True)
            update_mapping_after_sync(u)
            applied += 1
        
        print(f"\nApplied {applied} updates.", flush=True)
        if not args.dry_run:
            print("Run the full pipeline to regenerate views:", flush=True)
            print("  python scripts/refresh_repo_views.py", flush=True)
        if failed:
            print(f"Auxiliary mirror failed for {failed} skill(s).", file=sys.stderr)
            raise SystemExit(1)


if __name__ == "__main__":
    main()
