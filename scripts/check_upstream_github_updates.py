#!/usr/bin/env python3
"""Check mapped GitHub skills for meaningful upstream changes.

Replacement-mode skills are compared after repository adaptations and local
supplements are removed. Monitor-mode skills use their reviewed repository
commit checkpoint. This avoids reporting an update merely because a mapping
stores a repository-head SHA while GitHub's path history returns another SHA.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from sync_upstream import (  # noqa: E402
    check_upstream_changes,
    github_commit_sha,
    load_skills_with_upstream,
    resolve_github_token,
)
from provenance_v2 import atomic_write_json  # noqa: E402
from check_browser_foundations import prioritize  # noqa: E402


BUCKETS = (
    "equal",
    "changed",
    "monitor_review",
    "unavailable",
    "rollback",
    "expected_skipped",
)
UPDATE_TYPES = {"body_changed", "artifact_changed"}
REVIEW_TYPES = {"monitor_review", "upstream_rollback"}


def expected_skip_result(skill: dict[str, Any]) -> dict[str, Any] | None:
    """Return policy skips without resolving tokens or touching the network."""
    reason = skill.get("expected_skip_reason")
    if not reason and skill.get("kind") == "snapshot":
        reason = "licensed immutable snapshot; upstream checks are disabled"
    if not reason and skill.get("sync_mode") in {
        "manual",
        "local-only",
        "archived",
    }:
        reason = f"{skill.get('sync_mode')} source is not network checked"
    if not reason:
        return None
    return {
        "needs_update": False,
        "needs_review": False,
        "latest_commit": skill.get("last_synced_commit"),
        "latest_commit_date": None,
        "check_error": None,
        "change_type": "expected_skipped",
        "skip_reason": str(reason),
        "changed_files": [],
        "added_files": [],
        "removed_files": [],
        "moved_candidates": {},
    }


def github_latest_path_commit(
    repo: str,
    path: str,
    ref: str,
    token: str | None,
) -> tuple[str | None, str | None, str | None]:
    api = (
        f"https://api.github.com/repos/{repo}/commits"
        f"?path={urllib.parse.quote(path)}"
        f"&sha={urllib.parse.quote(ref)}&per_page=1"
    )
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "skills-provenance-bot",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(api, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not payload:
        return None, None, "no_commits_found"
    top = payload[0]
    sha = top.get("sha")
    date = (((top.get("commit") or {}).get("author") or {}).get("date"))
    return sha, date, None


def online_result(skill: dict, token: str | None) -> dict:
    """Return meaningful drift state plus display metadata for one skill."""
    policy_skip = expected_skip_result(skill)
    if policy_skip is not None:
        return policy_skip
    checked = check_upstream_changes(skill, token)
    if checked is None:
        return {
            "needs_update": False,
            "needs_review": False,
            "latest_commit": None,
            "latest_commit_date": None,
            "check_error": "upstream_content_unavailable",
            "change_type": "unavailable",
            "changed_files": [],
            "added_files": [],
            "removed_files": [],
            "moved_candidates": {},
        }

    change_type = checked.get("changes", "none")
    latest_commit = checked.get("current_commit")
    latest_commit_date = None
    check_error = (
        checked.get("reason")
        if change_type == "unavailable"
        else None
    )
    if latest_commit is None and change_type != "unavailable":
        try:
            if skill.get("sync_mode") == "monitor":
                latest_commit = github_commit_sha(
                    skill["repo"],
                    skill.get("ref", "main"),
                    token,
                )
            else:
                latest_commit, latest_commit_date, check_error = github_latest_path_commit(
                    skill["repo"],
                    checked.get("upstream_path") or skill.get("upstream_path") or "",
                    skill.get("ref", "main"),
                    token,
                )
        except Exception as exc:
            check_error = f"commit_metadata: {exc}"

    return {
        "needs_update": change_type in {"body_changed", "artifact_changed"},
        "needs_review": change_type in {"monitor_review", "upstream_rollback"},
        "latest_commit": latest_commit,
        "latest_commit_date": latest_commit_date,
        "check_error": check_error,
        "change_type": change_type,
        "changed_files": checked.get("changed_files", []),
        "added_files": checked.get("added_files", []),
        "removed_files": checked.get("removed_files", []),
        "moved_candidates": checked.get("moved_candidates", {}),
    }


def row_bucket(row: object) -> str:
    if not isinstance(row, dict):
        return "unavailable"
    change_type = row.get("change_type")
    if row.get("check_error") or change_type == "unavailable":
        return "unavailable"
    if change_type == "none":
        return "equal"
    if change_type in UPDATE_TYPES:
        return "changed"
    if change_type == "monitor_review":
        return "monitor_review"
    if change_type == "upstream_rollback":
        return "rollback"
    if change_type in {"expected_skipped", "offline"}:
        return "expected_skipped"
    return "unavailable"


def summarize_states(
    rows: list[dict],
    *,
    online: bool = True,
) -> tuple[dict[str, int], str]:
    buckets = {key: 0 for key in BUCKETS}
    for row in rows:
        buckets[row_bucket(row)] += 1

    if not rows or buckets["unavailable"]:
        state = "failed"
    elif (
        not online
        or buckets["monitor_review"]
        or buckets["rollback"]
    ):
        state = "degraded"
    else:
        state = "complete"
    return {"total": len(rows), **buckets}, state


def _base_row(skill: dict[str, Any], root: Path, *, online: bool) -> dict[str, Any]:
    local_path = skill.get("local_path")
    try:
        repo_skill = str(Path(local_path).relative_to(root))
    except (TypeError, ValueError):
        repo_skill = str(local_path or "")
    mapping_value = skill.get("mapping_path")
    return {
        "mapping": Path(mapping_value).name if mapping_value else None,
        "video_name": skill.get("name"),
        "slug": skill.get("name"),
        "repo_skill": repo_skill,
        "status": "verified_in_repo",
        "upstream_repo": skill.get("repo"),
        "upstream_path": skill.get("upstream_path"),
        "upstream_ref": skill.get("ref", "main"),
        "sync_mode": skill.get("sync_mode", "replace"),
        "last_synced_commit": skill.get("last_synced_commit"),
        "needs_update": False,
        "needs_review": False,
        "latest_commit": None,
        "latest_commit_date": None,
        "check_error": None,
        "change_type": "unavailable" if online else "expected_skipped",
        "check_mode": "online" if online else "offline",
        "changed_files": [],
        "added_files": [],
        "removed_files": [],
        "moved_candidates": {},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--online", action="store_true", help="Query GitHub for meaningful upstream drift")
    parser.add_argument("--write-json", default="docs/sources/reports/upstream-check.json")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    try:
        skills = prioritize(load_skills_with_upstream())
        load_error = None
    except Exception as exc:  # a failed inventory can never be reported fresh
        skills = []
        load_error = f"mapping_inventory: {type(exc).__name__}: {exc}"
    token: str | None = None
    token_resolved = False
    rows: list[dict[str, Any]] = []

    for skill in skills:
        item = _base_row(skill, root, online=args.online)
        try:
            policy_skip = expected_skip_result(skill)
            if policy_skip is not None:
                item.update(policy_skip)
            elif args.online:
                if not token_resolved:
                    token = resolve_github_token()
                    token_resolved = True
                item.update(online_result(skill, token))
            elif not skill.get("last_synced_commit"):
                item["check_error"] = "missing_last_synced_commit"
                item["change_type"] = "unavailable"
        except Exception as exc:
            item.update(
                {
                    "needs_update": False,
                    "needs_review": False,
                    "check_error": (
                        f"upstream_check: {type(exc).__name__}: {exc}"
                    ),
                    "change_type": "unavailable",
                }
            )
        rows.append(item)

    summary, state = summarize_states(rows, online=args.online)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "online" if args.online else "offline",
        "state": state,
        "summary": summary,
        "total_checked": len(rows),
        "needs_update_count": sum(1 for row in rows if row["needs_update"]),
        "needs_review_count": sum(1 for row in rows if row["needs_review"]),
        "check_error_count": sum(1 for row in rows if row["check_error"]),
        "inventory_error": load_error,
        "rows": rows,
    }
    if load_error:
        payload["state"] = "failed"

    out = Path(args.write_json)
    if not out.is_absolute():
        out = root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(out, payload)
    try:
        display_path = out.relative_to(root)
    except ValueError:
        display_path = out
    print(f"Wrote upstream check report: {display_path}")
    print(
        f"Checked rows: {payload['total_checked']}, "
        f"needs_update: {payload['needs_update_count']}, "
        f"needs_review: {payload['needs_review_count']}, "
        f"errors: {payload['check_error_count']}, "
        f"state: {payload['state']}"
    )
    return {"complete": 0, "failed": 1, "degraded": 2}[payload["state"]]


if __name__ == "__main__":
    raise SystemExit(main())
