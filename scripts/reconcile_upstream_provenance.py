#!/usr/bin/env python3
"""Reconcile SKILL.md `source:` declarations with provenance JSON mappings.

Problem: some skills declare `source: github:owner/repo` in their SKILL.md
frontmatter but remain tracked under `in-house.skills.json` with
`upstream.repo = local-repo/in-house`. That prevents
`check_upstream_github_updates.py --online` from detecting real upstream drift.

This script:
  1. Scans every skills/*/*/SKILL.md for `source:` and `name:`.
  2. For each skill with a known external source, ensures a correctly
     populated entry exists in the matching external `*.skills.json` mapping.
  3. Reports any remaining skills with external-looking sources that have
     no resolvable upstream (community, skills.sh without known repo, etc.).

After running this script, re-run
`python scripts/bootstrap_in_house_sources.py --write-json docs/sources/in-house.skills.json`
so in-house.skills.json evicts the skills now claimed by external mappings.

Usage:
    python scripts/reconcile_upstream_provenance.py            # dry run
    python scripts/reconcile_upstream_provenance.py --apply    # write JSON
"""
from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCES_DIR = REPO_ROOT / "docs" / "sources"
SKILLS_DIR = REPO_ROOT / "skills"

# Known external source → mapping-file + repo-layout rules.
# path_overrides wins over path_template when a skill name is present there.
KNOWN_EXTERNALS: dict[str, dict] = {
    "github:obra/superpowers": {
        "mapping": "obra-superpowers-2026-04.skills.json",
        "repo": "obra/superpowers",
        "path_template": "skills/{name}/SKILL.md",
        "source_url_template": "https://skills.sh/obra/superpowers/{name}",
        "reference_url": "https://github.com/obra/superpowers",
    },
    "github:wshobson/agents": {
        "mapping": "wshobson-agents-2026-04.skills.json",
        "repo": "wshobson/agents",
        "path_template": "plugins/developer-essentials/skills/{name}/SKILL.md",
        "source_url_template": "https://skills.sh/wshobson/agents/{name}",
        "reference_url": "https://github.com/wshobson/agents",
    },
    "github:alirezarezvani/claude-skills": {
        "mapping": "alirezarezvani-claude-skills-2026-04.skills.json",
        "repo": "alirezarezvani/claude-skills",
        "path_overrides": {
            "agent-hub": "engineering/agenthub/SKILL.md",
            "senior-architect": "engineering-team/senior-architect/SKILL.md",
            "saas-metrics-coach": "finance/saas-metrics-coach/SKILL.md",
            "landing-page-generator": "product-team/landing-page-generator/SKILL.md",
            "skill-security-auditor": "engineering/skill-security-auditor/SKILL.md",
        },
        "source_url_template": "https://github.com/alirezarezvani/claude-skills",
        "reference_url": "https://github.com/alirezarezvani/claude-skills",
    },
}

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def load_skill_records() -> list[dict]:
    records = []
    for skill_md in sorted(SKILLS_DIR.glob("*/*/SKILL.md")):
        fm = parse_frontmatter(skill_md.read_text(encoding="utf-8", errors="replace"))
        records.append({
            "skill_md": skill_md,
            "rel": skill_md.relative_to(REPO_ROOT).as_posix(),
            "name": fm.get("name", skill_md.parent.name),
            "source": fm.get("source", "in-house"),
            "source_url": fm.get("source_url", ""),
            "category": skill_md.parent.parent.name,
        })
    return records


def load_mapping(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "video": {},
        "official_references": [],
        "skills": [],
        "verification_attempts": [],
    }


def resolve_upstream_path(source: str, name: str) -> str | None:
    rule = KNOWN_EXTERNALS.get(source)
    if not rule:
        return None
    overrides = rule.get("path_overrides") or {}
    if name in overrides:
        return overrides[name]
    tmpl = rule.get("path_template")
    if tmpl:
        return tmpl.format(name=name)
    return None


def build_entry(record: dict, upstream_path: str, rule: dict, today: str) -> dict:
    name = record["name"]
    source_url = record["source_url"] or rule["source_url_template"].format(name=name)
    return {
        "video_name": name,
        "normalized_slug": name,
        "status": "verified_in_repo",
        "repo_skill": record["rel"],
        "source": source_url,
        "notes": "Reconciled from SKILL.md source declaration; upstream tracking enabled.",
        "upstream": {
            "repo": rule["repo"],
            "path": upstream_path,
            "ref": "main",
            "last_checked_at": today,
            "last_synced_at": today,
            "last_synced_commit": None,
        },
    }


def ensure_reference(payload: dict, rule: dict) -> None:
    refs = payload.setdefault("official_references", [])
    url = rule["reference_url"]
    if any(isinstance(r, dict) and r.get("url") == url for r in refs):
        return
    refs.append({
        "name": f"{rule['repo']} repository",
        "url": url,
        "purpose": "Canonical upstream repository for reconciled skills.",
    })


def ensure_video_header(payload: dict, rule: dict, today: str) -> None:
    video = payload.get("video") or {}
    if not video:
        video = {
            "url": rule["reference_url"],
            "checked_at": today,
            "note": f"Curated from {rule['repo']} with upstream tracking enabled.",
        }
    else:
        video.setdefault("url", rule["reference_url"])
        video["checked_at"] = today
    payload["video"] = video


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes to mapping JSON files")
    args = parser.parse_args()

    today = date.today().isoformat()
    records = load_skill_records()

    # Build a path-set of skills already claimed in any non-in-house mapping.
    claimed: set[str] = set()
    for mp in sorted(SOURCES_DIR.glob("*.skills.json")):
        if mp.name == "in-house.skills.json":
            continue
        data = json.loads(mp.read_text(encoding="utf-8"))
        for item in data.get("skills", []):
            rel = item.get("repo_skill")
            if rel:
                claimed.add(rel)

    updates: dict[str, dict] = {}  # mapping filename → mutable payload
    added: list[tuple[str, str]] = []  # (mapping, skill_name)
    unresolved: list[dict] = []

    for rec in records:
        src = rec["source"]
        if src in ("in-house", "") or src.startswith("local-"):
            continue
        if rec["rel"] in claimed:
            continue
        rule = KNOWN_EXTERNALS.get(src)
        if not rule:
            unresolved.append(rec)
            continue
        path = resolve_upstream_path(src, rec["name"])
        if not path:
            unresolved.append(rec)
            continue
        mapping_name = rule["mapping"]
        mapping_path = SOURCES_DIR / mapping_name
        if mapping_name not in updates:
            updates[mapping_name] = load_mapping(mapping_path)
        payload = updates[mapping_name]
        ensure_video_header(payload, rule, today)
        ensure_reference(payload, rule)
        entry = build_entry(rec, path, rule, today)
        payload.setdefault("skills", []).append(entry)
        added.append((mapping_name, rec["name"]))

    # Report
    print(f"Reconciliation scan @ {today}")
    print(f"  records scanned: {len(records)}")
    print(f"  already claimed externally: {len(claimed)}")
    print(f"  new entries to add: {len(added)}")
    for mapping, name in added:
        print(f"    + {mapping}: {name}")
    if unresolved:
        print(f"  unresolved external sources ({len(unresolved)}):")
        for rec in unresolved:
            print(f"    ? {rec['rel']}  source={rec['source']!r}")
    if not added:
        print("No reconciliation changes needed.")
        return 0

    if not args.apply:
        print("\nDry run — rerun with --apply to write changes.")
        print("Then run: python scripts/bootstrap_in_house_sources.py "
              "--write-json docs/sources/in-house.skills.json")
        return 0

    # Sort skills deterministically and write each updated mapping.
    for mapping_name, payload in updates.items():
        skills = payload.get("skills", [])
        skills.sort(key=lambda s: s.get("video_name", ""))
        # dedupe by repo_skill, prefer last (newest) entry
        seen: dict[str, dict] = {}
        for s in skills:
            key = s.get("repo_skill") or s.get("video_name")
            seen[key] = s
        payload["skills"] = sorted(seen.values(), key=lambda s: s.get("video_name", ""))
        out_path = SOURCES_DIR / mapping_name
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {out_path.relative_to(REPO_ROOT)}  (skills: {len(payload['skills'])})")

    print("\nNext: python scripts/bootstrap_in_house_sources.py "
          "--write-json docs/sources/in-house.skills.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
