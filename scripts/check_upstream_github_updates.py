#!/usr/bin/env python3
"""Check upstream GitHub changes for mapped skills.

By default runs in offline-safe mode (no network) and reports missing metadata.
Use --online to query GitHub commits API and detect true upstream drift.
"""
from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


def github_latest_commit(repo: str, path: str, ref: str) -> tuple[str | None, str | None, str | None]:
    api = f"https://api.github.com/repos/{repo}/commits?path={urllib.parse.quote(path)}&sha={urllib.parse.quote(ref)}&per_page=1"
    req = urllib.request.Request(api, headers={"User-Agent": "skills-provenance-bot"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not payload:
        return None, None, "no_commits_found"
    top = payload[0]
    sha = top.get("sha")
    date = (((top.get("commit") or {}).get("author") or {}).get("date"))
    return sha, date, None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--online", action="store_true", help="Query GitHub API for real-time upstream checks")
    parser.add_argument("--write-json", default="docs/sources/reports/upstream-check.json")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    mappings = sorted((root / "docs/sources").glob("*.skills.json"))

    rows = []
    for mapping in mappings:
        data = json.loads(mapping.read_text(encoding="utf-8"))
        for s in data.get("skills", []):
            upstream = s.get("upstream") or {}
            repo = upstream.get("repo")
            path = upstream.get("path")
            ref = upstream.get("ref") or "main"
            last_synced = upstream.get("last_synced_commit")
            status = s.get("status")

            if not repo or repo == "local-repo/in-house":
                continue

            item = {
                "mapping": mapping.name,
                "video_name": s.get("video_name"),
                "slug": s.get("normalized_slug"),
                "repo_skill": s.get("repo_skill"),
                "status": status,
                "upstream_repo": repo,
                "upstream_path": path,
                "upstream_ref": ref,
                "last_synced_commit": last_synced,
                "needs_update": False,
                "latest_commit": None,
                "latest_commit_date": None,
                "check_error": None,
                "check_mode": "online" if args.online else "offline",
            }

            if not args.online:
                if not last_synced:
                    item["check_error"] = "missing_last_synced_commit"
                rows.append(item)
                continue

            try:
                sha, d, err = github_latest_commit(repo, path or "", ref)
                item["latest_commit"] = sha
                item["latest_commit_date"] = d
                item["check_error"] = err
                if sha and last_synced and sha != last_synced:
                    item["needs_update"] = True
                if sha and not last_synced:
                    item["needs_update"] = True
            except Exception as e:  # network/runtime errors are reported, not fatal
                item["check_error"] = str(e)
            rows.append(item)

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "mode": "online" if args.online else "offline",
        "total_checked": len(rows),
        "needs_update_count": sum(1 for r in rows if r.get("needs_update")),
        "rows": rows,
    }

    out = root / args.write_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote upstream check report: {out.relative_to(root)}")
    print(f"Checked rows: {payload['total_checked']}, needs_update: {payload['needs_update_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
