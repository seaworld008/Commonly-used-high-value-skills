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

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from sync_upstream import (  # noqa: E402
    check_upstream_changes,
    github_commit_sha,
    load_skills_with_upstream,
    resolve_github_token,
)


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
    checked = check_upstream_changes(skill, token)
    if checked is None:
        return {
            "needs_update": False,
            "latest_commit": None,
            "latest_commit_date": None,
            "check_error": "upstream_content_unavailable",
            "change_type": "unavailable",
        }

    change_type = checked.get("changes", "none")
    latest_commit = None
    latest_commit_date = None
    check_error = None
    try:
        if skill.get("sync_mode") == "monitor":
            latest_commit = checked.get("current_commit") or github_commit_sha(
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
        "needs_update": change_type == "body_changed",
        "latest_commit": latest_commit,
        "latest_commit_date": latest_commit_date,
        "check_error": check_error,
        "change_type": change_type,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--online", action="store_true", help="Query GitHub for meaningful upstream drift")
    parser.add_argument("--write-json", default="docs/sources/reports/upstream-check.json")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    skills = load_skills_with_upstream()
    token = resolve_github_token() if args.online else None
    rows = []

    for skill in skills:
        item = {
            "mapping": Path(skill.get("mapping_path", "")).name or None,
            "video_name": skill.get("name"),
            "slug": skill.get("name"),
            "repo_skill": str(skill["local_path"].relative_to(root)),
            "status": "verified_in_repo",
            "upstream_repo": skill["repo"],
            "upstream_path": skill.get("upstream_path"),
            "upstream_ref": skill.get("ref", "main"),
            "sync_mode": skill.get("sync_mode", "replace"),
            "last_synced_commit": skill.get("last_synced_commit"),
            "needs_update": False,
            "latest_commit": None,
            "latest_commit_date": None,
            "check_error": None,
            "change_type": "offline",
            "check_mode": "online" if args.online else "offline",
        }

        if args.online:
            item.update(online_result(skill, token))
        elif not skill.get("last_synced_commit"):
            item["check_error"] = "missing_last_synced_commit"
        rows.append(item)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "online" if args.online else "offline",
        "total_checked": len(rows),
        "needs_update_count": sum(1 for row in rows if row["needs_update"]),
        "check_error_count": sum(1 for row in rows if row["check_error"]),
        "rows": rows,
    }

    out = root / args.write_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        display_path = out.relative_to(root)
    except ValueError:
        display_path = out
    print(f"Wrote upstream check report: {display_path}")
    print(
        f"Checked rows: {payload['total_checked']}, "
        f"needs_update: {payload['needs_update_count']}, "
        f"errors: {payload['check_error_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
