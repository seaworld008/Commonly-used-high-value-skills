#!/usr/bin/env python3
"""Check browser foundations before bulk maintenance; never install or advance review baselines."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import os
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/sources/browser-foundations.json"


def load_policy(path=POLICY):
    policy = json.loads(Path(path).read_text(encoding="utf-8"))
    if policy.get("schema_version") != 1 or not policy.get("targets"):
        raise ValueError("browser foundation policy is missing or invalid")
    ids = [target["id"] for target in policy["targets"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate browser foundation target")
    return policy


def prioritize(skills):
    ranks = {name: i for i, name in enumerate(load_policy()["priority_skills"])}
    return sorted(skills, key=lambda skill: ranks.get(skill.get("name"), len(ranks)))


def tree_digest(tree, prefixes):
    if tree.get("truncated") or not isinstance(tree.get("tree"), list):
        raise ValueError("incomplete GitHub tree; freshness cannot be established")
    files = [
        (entry["path"], entry["sha"], entry["mode"])
        for entry in tree["tree"]
        if entry["type"] == "blob" and any(
            entry["path"] == prefix or entry["path"].startswith(prefix.rstrip("/") + "/")
            for prefix in prefixes
        )
    ]
    if not files or any(not any(p == prefix or p.startswith(prefix.rstrip("/") + "/")
                                for p, _, _ in files) for prefix in prefixes):
        raise ValueError("a monitored upstream path is missing")
    return hashlib.sha256(json.dumps(sorted(files), separators=(",", ":")).encode()).hexdigest()


def get_json(url, token=None):
    headers = {"User-Agent": "skills-browser-foundations", "Accept": "application/json"}
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def check_target(target, token=None, fetch=get_json):
    row = {"id": target["id"], "state": "current", "reasons": []}
    phase = "github_tree"
    try:
        repo = target["repo"]
        tree = fetch(f"https://api.github.com/repos/{repo}/git/trees/{target.get('ref', 'main')}?recursive=1", token)
        digest = tree_digest(tree, target["paths"])
        row.update(commit=tree["sha"], tree_digest=digest)
        if digest != target["reviewed_tree_digest"]:
            row["reasons"].append("upstream command/skill contract changed; review the path diff")
        if target.get("package"):
            phase = "npm_latest"
            package = urllib.parse.quote(target["package"], safe="")
            npm = fetch(f"https://registry.npmjs.org/{package}/latest", None)
            version = npm["version"]
            row.update(latest_package_version=version, engines=npm.get("engines", {}))
            if version != target["reviewed_version"]:
                row["reasons"].append(f"npm latest {version} differs from reviewed {target['reviewed_version']}")
            phase = "github_release"
            release = fetch(f"https://api.github.com/repos/{repo}/releases/latest", token)
            if release.get("draft") or release.get("prerelease"):
                raise ValueError("latest release is not stable")
            row["latest_release"] = release["tag_name"]
            if release["tag_name"] != target["reviewed_release"]:
                row["reasons"].append(f"new stable release {release['tag_name']}")
        if row["reasons"]:
            row["state"] = "review_required"
    except Exception as exc:
        # Do not embed URL/header/body-bearing exceptions in public reports.
        status = f" HTTP {exc.code}" if isinstance(getattr(exc, "code", None), int) else ""
        row.update(state="unavailable", reasons=[f"{phase}: {type(exc).__name__}{status}; upstream check incomplete"])
    return row


def check_policy(policy, token=None, fetch=get_json):
    rows = [check_target(target, token, fetch) for target in policy["targets"]]
    state = "failed" if any(r["state"] == "unavailable" for r in rows) else (
        "degraded" if any(r["state"] == "review_required" for r in rows) else "complete")
    return {"schema_version": 1, "mode": "online", "state": state,
            "generated_at": datetime.now(timezone.utc).isoformat(), "rows": rows}


def validate_report(payload, policy=None):
    policy = policy or load_policy()
    if not isinstance(payload, dict) or payload.get("schema_version") != 1 or payload.get("mode") != "online":
        raise ValueError("invalid browser foundation report")
    try:
        generated = datetime.fromisoformat(payload["generated_at"].replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - generated
        if age < -timedelta(minutes=5) or age > timedelta(days=1):
            raise ValueError("outdated browser foundation report")
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("missing/invalid browser foundation check time") from exc
    rows = payload.get("rows")
    expected = {target["id"] for target in policy["targets"]}
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("invalid browser foundation rows")
    if len(rows) != len(expected) or {row.get("id") for row in rows} != expected:
        raise ValueError("browser foundation report did not check every target")
    for row in rows:
        if row.get("state") not in {"current", "review_required", "unavailable"}:
            raise ValueError("unknown browser foundation state")
        if not isinstance(row.get("reasons"), list) or (row["state"] == "current" and row["reasons"]):
            raise ValueError("inconsistent browser foundation reasons")
    state = "failed" if any(r["state"] == "unavailable" for r in rows) else (
        "degraded" if any(r["state"] == "review_required" for r in rows) else "complete")
    if payload.get("state") != state:
        raise ValueError("inconsistent browser foundation summary")
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=POLICY)
    parser.add_argument("--write-json", type=Path, default=ROOT / "docs/sources/reports/browser-foundations.json")
    args = parser.parse_args(argv)
    sys.path.insert(0, str(ROOT / "scripts"))
    from sync_upstream import resolve_github_token
    try:
        payload = check_policy(load_policy(args.policy), resolve_github_token())
    except Exception as exc:
        payload = {"schema_version": 1, "mode": "online", "state": "failed", "rows": [],
                   "error": f"{type(exc).__name__}: foundation inventory/check failed"}
    destination = args.write_json.absolute()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink():
        raise ValueError("refusing symlink report destination")
    descriptor, temporary = tempfile.mkstemp(prefix=".browser-foundations-", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    for row in payload["rows"]:
        print(f"{row['id']}: {row['state']}" + ("; " + "; ".join(row["reasons"]) if row["reasons"] else ""))
    print(f"Browser foundations: {payload['state']}")
    return {"complete": 0, "degraded": 2, "failed": 1}[payload["state"]]


if __name__ == "__main__":
    raise SystemExit(main())
