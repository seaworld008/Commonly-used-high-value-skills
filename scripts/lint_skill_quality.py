#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

def parse_frontmatter(content: str) -> Dict[str, str]:
    """Simple regex-based frontmatter parser."""
    match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not match:
        return {}
    
    yaml_text = match.group(1)
    data = {}
    for line in yaml_text.split('\n'):
        if ':' in line:
            key, val = line.split(':', 1)
            data[key.strip()] = val.strip().strip("'").strip('"')
    return data

def lint_skill(file_path: Path, min_lines: int) -> Dict[str, Any]:
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        return {
            "name": file_path.parent.name,
            "status": "FAIL",
            "errors": [f"Could not read file: {e}"],
            "warnings": [],
            "line_count": 0,
            "checks_passed": 0
        }

    lines = content.splitlines()
    line_count = len(lines)
    
    errors = []
    warnings = []
    passed_count = 0
    
    # 1. Line count check
    if line_count < 50:
        errors.append(f"below minimum 50 lines")
    elif line_count < min_lines:
        warnings.append(f"below minimum {min_lines} lines")
    else:
        passed_count += 1
    
    # Frontmatter checks
    frontmatter = parse_frontmatter(content)
    
    # 2. Required fields
    missing_req = [f for f in ["name", "description"] if f not in frontmatter or not frontmatter[f]]
    if missing_req:
        errors.append(f"missing required field: {', '.join(missing_req)}")
    else:
        passed_count += 1
    
    # 3. Recommended fields
    missing_rec = [f for f in ["version", "tags", "quality"] if f not in frontmatter]
    if missing_rec:
        warnings.append(f"missing recommended field: {', '.join(missing_rec)}")
    else:
        passed_count += 1
            
    # 4. Section check
    trigger_patterns = [r"## 触发条件", r"## When to Use", r"## Trigger"]
    core_patterns = [r"## 核心能力", r"## Core", r"## Capabilities", r"## Usage"]
    common_section_keywords = [
        "overview",
        "workflow",
        "quick start",
        "quick reference",
        "reference",
        "usage",
        "how it works",
        "process",
        "resources",
        "purpose",
        "description",
        "features",
        "inputs",
        "requirements",
        "prerequisites",
        "examples",
        "checklist",
        "integration",
        "best practices",
        "guidance",
        "decision tree",
        "tool priority",
        "output",
    ]

    headings = re.findall(r"^##\s+(.+)$", content, re.MULTILINE)
    normalized_headings = [
        re.sub(r"[^a-z0-9]+", " ", heading.lower()).strip() for heading in headings
    ]

    has_trigger = any(re.search(p, content, re.IGNORECASE) for p in trigger_patterns)
    has_core = any(re.search(p, content, re.IGNORECASE) for p in core_patterns)
    has_common_sections = any(
        keyword in heading
        for heading in normalized_headings
        for keyword in common_section_keywords
    )

    if len(headings) < 2 or not (has_trigger or has_core or has_common_sections):
        warnings.append("missing sections")
    else:
        passed_count += 1
        
    # 5. Code block check
    if "```" not in content:
        warnings.append("no code blocks")
    else:
        passed_count += 1
        
    # 6. description length
    desc = frontmatter.get("description", "")
    if desc and len(desc) < 20:
        warnings.append("description too short")
    elif desc:
        passed_count += 1
    else:
        # already handled by required field check, but for count consistency:
        pass
        
    status = "PASS"
    if errors:
        status = "FAIL"
    elif warnings:
        status = "WARN"
        
    return {
        "name": frontmatter.get("name", file_path.parent.name),
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "line_count": line_count,
        "checks_passed": passed_count
    }

def main():
    parser = argparse.ArgumentParser(description="Lint SKILL.md quality.")
    parser.add_argument("--skills-dir", default="skills", help="Skills directory")
    parser.add_argument("--min-lines", type=int, default=80, help="Minimum line count for WARN")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    skills_dir = Path(args.skills_dir)
    if not skills_dir.exists():
        # Try relative to script location if not found
        script_root = Path(__file__).parent.parent
        skills_dir = script_root / args.skills_dir
        
    if not skills_dir.exists():
        print(f"Error: Directory {skills_dir} does not exist.", file=sys.stderr)
        sys.exit(1)
        
    skill_files = list(skills_dir.glob("**/SKILL.md"))
    # Filter to match skills/*/*/SKILL.md roughly, but excluding internal assets
    # Actually glob **/SKILL.md is fine, usually.
    
    reports = []
    for f in skill_files:
        reports.append(lint_skill(f, args.min_lines))
        
    # Sort: FAIL first, then WARN, then PASS
    status_order = {"FAIL": 0, "WARN": 1, "PASS": 2}
    reports.sort(key=lambda x: (status_order[x["status"]], x["name"]))
    
    if args.json:
        print(json.dumps(reports, indent=2, ensure_ascii=False))
    else:
        print("=== Skill Quality Report ===")
        for r in reports:
            if r["status"] == "PASS":
                print(f"PASS  {r['name']} ({r['line_count']} lines, {r['checks_passed']} checks passed)")
            else:
                issues = r['errors'] + r['warnings']
                print(f"{r['status']:5} {r['name']} ({r['line_count']} lines) — {', '.join(issues)}")
            
        summary = {
            "PASS": sum(1 for r in reports if r["status"] == "PASS"),
            "WARN": sum(1 for r in reports if r["status"] == "WARN"),
            "FAIL": sum(1 for r in reports if r["status"] == "FAIL")
        }
        print(f"\nSummary: {summary['PASS']} PASS, {summary['WARN']} WARN, {summary['FAIL']} FAIL")
        
    has_fail = any(r["status"] == "FAIL" for r in reports)
    has_warn = any(r["status"] == "WARN" for r in reports)
    
    if has_fail or (args.strict and has_warn):
        sys.exit(1)

if __name__ == "__main__":
    main()
