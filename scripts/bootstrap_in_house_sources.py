#!/usr/bin/env python3
"""Bootstrap or refresh the repository skill provenance mapping.

The original implementation rewrote every entry as `in_house`, which erased
externally tracked provenance metadata. This version preserves existing tracked
entries and only backfills truly local-only skills.
"""
from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from datetime import date
from pathlib import Path


CANONICAL_NOTE = "In-house canonical skill (local repository source of truth)."


def parse_frontmatter_name(skill_md: Path) -> str:
    text = skill_md.read_text(encoding="utf-8")
    m = re.search(r"^name:\s*['\"]?([^'\"\n]+)['\"]?\s*$", text, re.MULTILINE)
    if not m:
        raise ValueError(f"Missing frontmatter name in {skill_md}")
    return m.group(1).strip()


def load_existing_payload(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_default_entry(name: str, rel: str, repo_url: str, today: str) -> dict:
    return {
        "video_name": name,
        "normalized_slug": name,
        "status": "in_house",
        "repo_skill": rel,
        "source": repo_url,
        "notes": CANONICAL_NOTE,
        "upstream": {
            "repo": "local-repo/in-house",
            "path": rel.rsplit("/", 1)[0],
            "ref": "main",
            "last_checked_at": today,
            "last_synced_at": today,
            "last_synced_commit": None,
        },
    }


def merge_existing_entry(existing: dict, *, name: str, rel: str, repo_url: str, today: str) -> dict:
    merged = deepcopy(existing)
    merged["video_name"] = name
    merged["repo_skill"] = rel

    status = merged.get("status") or "in_house"
    if status in {"verified_in_repo", "in_house"} or merged.get("normalized_slug") in (None, ""):
        merged["normalized_slug"] = name

    if not merged.get("source"):
        merged["source"] = repo_url
    if not merged.get("notes"):
        merged["notes"] = CANONICAL_NOTE

    upstream = deepcopy(merged.get("upstream") or {})
    if status == "in_house":
        upstream.setdefault("repo", "local-repo/in-house")
        upstream.setdefault("path", rel.rsplit("/", 1)[0])
        upstream.setdefault("ref", "main")
        upstream["last_checked_at"] = today
        upstream.setdefault("last_synced_at", today)
        upstream.setdefault("last_synced_commit", None)
    else:
        upstream.setdefault("path", rel.rsplit("/", 1)[0])
        upstream.setdefault("ref", "main")
        upstream["last_checked_at"] = today
    if upstream:
        merged["upstream"] = upstream

    return merged


def build_official_references(existing_payload: dict | None, repo_url: str) -> list[dict]:
    references: list[dict] = []
    seen_urls: set[str] = set()
    if existing_payload:
        for item in existing_payload.get("official_references", []):
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            if url and url not in seen_urls:
                references.append(item)
                seen_urls.add(url)

    if repo_url not in seen_urls:
        references.append(
            {
                "name": "Repository canonical skills tree",
                "url": repo_url,
                "purpose": "Marks local source-of-truth skills as in_house.",
            }
        )
    return references


def build_verification_attempts(
    *,
    existing_payload: dict | None,
    today: str,
    skill_count: int,
) -> list[dict]:
    attempts = []
    if existing_payload:
        for item in existing_payload.get("verification_attempts", []):
            if isinstance(item, dict):
                attempts.append(item)
    attempts.append(
        {
            "date": today,
            "method": "local-scan",
            "target": "skills/*/*/SKILL.md",
            "result": "success",
            "evidence": f"Merged provenance for {skill_count} local skills",
        }
    )
    return attempts


def build_in_house_mapping(
    *,
    repo_root: Path,
    repo_url: str,
    existing_payload: dict | None = None,
    today: str | None = None,
) -> dict:
    today = today or date.today().isoformat()
    skill_files = sorted(repo_root.glob("skills/*/*/SKILL.md"))

    existing_by_path: dict[str, dict] = {}
    existing_by_name: dict[str, dict] = {}
    if existing_payload:
        for entry in existing_payload.get("skills", []):
            if not isinstance(entry, dict):
                continue
            repo_skill = entry.get("repo_skill")
            video_name = entry.get("video_name")
            if repo_skill:
                existing_by_path[repo_skill] = entry
            if video_name:
                existing_by_name[video_name] = entry

    skills = []
    for sf in skill_files:
        name = parse_frontmatter_name(sf)
        rel = sf.relative_to(repo_root).as_posix()
        existing = existing_by_path.get(rel) or existing_by_name.get(name)
        if existing:
            skills.append(
                merge_existing_entry(
                    existing,
                    name=name,
                    rel=rel,
                    repo_url=repo_url,
                    today=today,
                )
            )
        else:
            skills.append(build_default_entry(name, rel, repo_url, today))

    skills.sort(key=lambda item: item["video_name"])

    video = {
        "url": repo_url,
        "checked_at": today,
        "note": "Auto-generated provenance mapping for all local skills.",
    }
    if existing_payload and isinstance(existing_payload.get("video"), dict):
        video.update({k: v for k, v in existing_payload["video"].items() if k != "checked_at"})
        video["url"] = repo_url
        video["checked_at"] = today

    return {
        "video": video,
        "official_references": build_official_references(existing_payload, repo_url),
        "skills": skills,
        "verification_attempts": build_verification_attempts(
            existing_payload=existing_payload,
            today=today,
            skill_count=len(skills),
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json", default="docs/sources/in-house.skills.json")
    parser.add_argument("--repo-url", default="https://github.com/your-org/Commonly-used-high-value-skills")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    out = root / args.write_json
    payload = build_in_house_mapping(
        repo_root=root,
        repo_url=args.repo_url,
        existing_payload=load_existing_payload(out),
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote in-house mapping: {out.relative_to(root)}")
    print(f"Skills mapped: {len(payload['skills'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
