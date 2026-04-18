#!/usr/bin/env python3
"""Audit license attribution for every skill.

Policy:
  - Every skill with an external `source:` (github:*, skills.sh, community,
    adapted-from-*) MUST declare a `license:` field in its SKILL.md frontmatter.
    License compliance for external sources cannot be assumed.
  - Skills with `source: in-house` are exempt (licensed under the repo's own
    LICENSE file).

Exit code:
  0  every external skill carries a license tag
  1  one or more external skills are missing license attribution

Usage:
    python scripts/audit_licenses.py           # report + exit code
    python scripts/audit_licenses.py --json    # machine-readable report
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"

INHOUSE_SOURCES = {"in-house", "", "local-repo/in-house"}
# Light allowlist; unknown tags trigger a WARN, not a FAIL.
PERMISSIVE_LICENSES = {
    "MIT", "Apache-2.0", "Apache 2.0", "BSD-2-Clause", "BSD-3-Clause",
    "ISC", "CC-BY-4.0", "CC0-1.0", "Unlicense", "0BSD", "MPL-2.0",
}


def parse_frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm: dict[str, str] = {}
    current = None
    for line in m.group(1).splitlines():
        if line and (line[0] == " " or line[0] == "\t"):
            continue  # skip nested blocks
        if ":" in line:
            k, v = line.split(":", 1)
            current = k.strip()
            fm[current] = v.strip().strip('"').strip("'")
    return fm


def audit() -> list[dict]:
    rows = []
    for skill_md in sorted(SKILLS_DIR.glob("*/*/SKILL.md")):
        fm = parse_frontmatter(skill_md.read_text(encoding="utf-8", errors="replace"))
        source = fm.get("source", "in-house")
        license_tag = fm.get("license", "")
        status = "OK"
        note = ""
        if source in INHOUSE_SOURCES:
            status = "EXEMPT"
        elif not license_tag:
            status = "MISSING"
            note = f"external source {source!r} lacks license tag"
        elif license_tag not in PERMISSIVE_LICENSES:
            status = "UNKNOWN"
            note = f"license {license_tag!r} not in permissive allowlist"
        rows.append({
            "skill": skill_md.parent.name,
            "path": str(skill_md.relative_to(REPO_ROOT)),
            "source": source,
            "license": license_tag,
            "status": status,
            "note": note,
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true",
                        help="Fail on UNKNOWN licenses in addition to MISSING.")
    args = parser.parse_args()

    rows = audit()
    missing = [r for r in rows if r["status"] == "MISSING"]
    unknown = [r for r in rows if r["status"] == "UNKNOWN"]

    if args.json:
        print(json.dumps({
            "total": len(rows),
            "exempt": sum(1 for r in rows if r["status"] == "EXEMPT"),
            "ok": sum(1 for r in rows if r["status"] == "OK"),
            "missing": len(missing),
            "unknown": len(unknown),
            "rows": rows,
        }, indent=2, ensure_ascii=False))
    else:
        print(f"License audit: {len(rows)} skills")
        print(f"  EXEMPT (in-house): {sum(1 for r in rows if r['status']=='EXEMPT')}")
        print(f"  OK:                {sum(1 for r in rows if r['status']=='OK')}")
        print(f"  MISSING:           {len(missing)}")
        print(f"  UNKNOWN license:   {len(unknown)}")
        for r in missing:
            print(f"    MISSING  {r['skill']} ({r['source']})")
        for r in unknown:
            print(f"    UNKNOWN  {r['skill']} ({r['source']}): {r['license']}")

    fail = bool(missing) or (args.strict and unknown)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
