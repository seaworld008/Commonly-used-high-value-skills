#!/usr/bin/env python3
"""Generate the repository SVG banner from docs/catalog.json."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

CATEGORY_LABELS = {
    "developer-engineering": "Developer Engineering",
    "ai-workflow": "AI Workflow",
    "engineering-workflow-automation": "Workflow Automation",
    "ai-agent-platform": "AI Platform",
    "office-white-collar": "Office Automation",
    "finance-investing": "Finance Investing",
    "growth-operations-xiaohongshu": "Growth Operations",
    "operations-general": "General Operations",
    "product-design": "Product Design",
    "knowledge-and-pm-integrations": "Knowledge + PM",
    "security-and-reliability": "Security + Reliability",
    "multimodal-media": "Multimodal Media",
    "deployment-platforms": "Deployment Platforms",
    "openclaw-memory-and-safety": "Memory + Safety",
    "task-understanding-decomposition": "Task Understanding",
}

FEATURED_CATEGORY_ORDER = (
    "developer-engineering",
    "ai-workflow",
    "engineering-workflow-automation",
)


def load_catalog(catalog_path: Path) -> dict:
    return json.loads(catalog_path.read_text(encoding="utf-8"))


def category_counts(catalog: dict) -> dict[str, int]:
    return {entry["name"]: int(entry["count"]) for entry in catalog.get("categories", [])}


def label_for(category: str) -> str:
    if category in CATEGORY_LABELS:
        return CATEGORY_LABELS[category]
    return " ".join(part.capitalize() for part in category.replace("-", " ").split())


def select_featured_categories(catalog: dict) -> list[tuple[str, int]]:
    counts = category_counts(catalog)
    featured: list[tuple[str, int]] = []

    for category in FEATURED_CATEGORY_ORDER:
        if category in counts:
            featured.append((category, counts[category]))

    for entry in catalog.get("categories", []):
        category = entry["name"]
        if category not in {item[0] for item in featured}:
            featured.append((category, int(entry["count"])))
        if len(featured) >= 3:
            break

    return featured[:3]


def svg_text(value: object) -> str:
    return html.escape(str(value), quote=False)


def skill_word(count: int) -> str:
    return "skill" if count == 1 else "skills"


def render_featured_rows(featured: list[tuple[str, int]]) -> str:
    colors = ("#93C5FD", "#BBF7D0", "#FDE68A")
    fills = (
        'fill="url(#card)" stroke="#FFFFFF" stroke-opacity="0.14"',
        'fill="#34D399" fill-opacity="0.14" stroke="#6EE7B7" stroke-opacity="0.24"',
        'fill="url(#card)" stroke="#FFFFFF" stroke-opacity="0.14"',
    )
    rows = []
    for index, (category, count) in enumerate(featured):
        y = 26 + index * 82
        label = svg_text(label_for(category))
        metric = svg_text(f"{count} {skill_word(count)}")
        rows.append(
            f'''    <rect x="24" y="{y}" width="342" height="62" rx="18" {fills[index]}/>
    <text x="50" y="{y + 29}" fill="{colors[index]}" font-family="Segoe UI, Arial, sans-serif" font-size="22" font-weight="800">
      {label}
    </text>
    <text x="50" y="{y + 51}" fill="#CBD5E1" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="700">
      {metric}
    </text>'''
        )
    return "\n\n".join(rows)


def render_banner(catalog: dict) -> str:
    total_skills = int(catalog.get("total_skills", 0))
    total_categories = int(catalog.get("total_categories", 0))
    featured = select_featured_categories(catalog)
    featured_rows = render_featured_rows(featured)

    badge = svg_text(f"{total_skills} skills · {total_categories} categories · upstream sync")
    total_skills_text = svg_text(total_skills)
    total_categories_text = svg_text(total_categories)

    return f'''<svg width="1280" height="640" viewBox="0 0 1280 640" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1280" y2="640" gradientUnits="userSpaceOnUse">
      <stop stop-color="#111827"/>
      <stop offset="0.46" stop-color="#12332F"/>
      <stop offset="1" stop-color="#3B255E"/>
    </linearGradient>
    <linearGradient id="accent" x1="160" y1="146" x2="610" y2="540" gradientUnits="userSpaceOnUse">
      <stop stop-color="#60A5FA"/>
      <stop offset="0.52" stop-color="#34D399"/>
      <stop offset="1" stop-color="#FBBF24"/>
    </linearGradient>
    <linearGradient id="panel" x1="86" y1="70" x2="1198" y2="568" gradientUnits="userSpaceOnUse">
      <stop stop-color="#FFFFFF" stop-opacity="0.17"/>
      <stop offset="1" stop-color="#FFFFFF" stop-opacity="0.06"/>
    </linearGradient>
    <linearGradient id="card" x1="728" y1="152" x2="1138" y2="516" gradientUnits="userSpaceOnUse">
      <stop stop-color="#FFFFFF" stop-opacity="0.16"/>
      <stop offset="1" stop-color="#FFFFFF" stop-opacity="0.08"/>
    </linearGradient>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M40 0H0V40" stroke="#FFFFFF" stroke-opacity="0.10" stroke-width="1"/>
    </pattern>
    <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%" color-interpolation-filters="sRGB">
      <feDropShadow dx="0" dy="22" stdDeviation="28" flood-color="#020617" flood-opacity="0.32"/>
    </filter>
    <filter id="smallShadow" x="-20%" y="-20%" width="140%" height="140%" color-interpolation-filters="sRGB">
      <feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#020617" flood-opacity="0.22"/>
    </filter>
  </defs>

  <rect width="1280" height="640" rx="34" fill="url(#bg)"/>
  <rect width="1280" height="640" rx="34" fill="url(#grid)" opacity="0.34"/>
  <path d="M0 496L1280 360V640H0V496Z" fill="#0F172A" fill-opacity="0.26"/>
  <path d="M830 0H1280V640H1030L760 0H830Z" fill="#FFFFFF" fill-opacity="0.045"/>

  <rect x="72" y="64" width="1136" height="512" rx="30" fill="url(#panel)" stroke="#FFFFFF" stroke-opacity="0.16"/>

  <g transform="translate(136 122)">
    <rect x="0" y="0" width="376" height="42" rx="21" fill="#020617" fill-opacity="0.28" stroke="#FFFFFF" stroke-opacity="0.15"/>
    <circle cx="24" cy="21" r="8" fill="#34D399"/>
    <text x="44" y="28" fill="#D1FAE5" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="700">
      {badge}
    </text>

    <text x="0" y="124" fill="#FFFFFF" font-family="Segoe UI, Arial, sans-serif" font-size="56" font-weight="850">
      Commonly Used
    </text>
    <text x="0" y="194" fill="#FFFFFF" font-family="Segoe UI, Arial, sans-serif" font-size="56" font-weight="850">
      High-Value Skills
    </text>

    <rect x="2" y="222" width="490" height="6" rx="3" fill="url(#accent)"/>

    <text x="0" y="278" fill="#E0F2FE" font-family="Segoe UI, Arial, sans-serif" font-size="25" font-weight="650">
      For Codex, Claude Code, Hermes Agent,
    </text>
    <text x="0" y="316" fill="#E0F2FE" font-family="Segoe UI, Arial, sans-serif" font-size="25" font-weight="650">
      OpenClaw, and automation workflows.
    </text>

    <g transform="translate(0 366)">
      <rect x="0" y="0" width="178" height="54" rx="15" fill="#2563EB"/>
      <text x="26" y="35" fill="#FFFFFF" font-family="Segoe UI, Arial, sans-serif" font-size="21" font-weight="800">
        Reusable
      </text>
      <rect x="196" y="0" width="184" height="54" rx="15" fill="#059669"/>
      <text x="222" y="35" fill="#FFFFFF" font-family="Segoe UI, Arial, sans-serif" font-size="21" font-weight="800">
        Curated
      </text>
      <rect x="398" y="0" width="188" height="54" rx="15" fill="#7C3AED"/>
      <text x="424" y="35" fill="#FFFFFF" font-family="Segoe UI, Arial, sans-serif" font-size="21" font-weight="800">
        Updatable
      </text>
    </g>
  </g>

  <g transform="translate(762 126)" filter="url(#softShadow)">
    <rect x="0" y="0" width="390" height="388" rx="26" fill="#0B1120" fill-opacity="0.56" stroke="#FFFFFF" stroke-opacity="0.15"/>
{featured_rows}

    <rect x="24" y="272" width="158" height="72" rx="18" fill="#FFFFFF" fill-opacity="0.09" stroke="#FFFFFF" stroke-opacity="0.13"/>
    <text x="48" y="302" fill="#E5E7EB" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="700">
      Skills
    </text>
    <text x="48" y="330" fill="#FFFFFF" font-family="Segoe UI, Arial, sans-serif" font-size="30" font-weight="850">
      {total_skills_text}
    </text>

    <rect x="208" y="272" width="158" height="72" rx="18" fill="#FFFFFF" fill-opacity="0.09" stroke="#FFFFFF" stroke-opacity="0.13"/>
    <text x="232" y="302" fill="#E5E7EB" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="700">
      Categories
    </text>
    <text x="232" y="330" fill="#FFFFFF" font-family="Segoe UI, Arial, sans-serif" font-size="30" font-weight="850">
      {total_categories_text}
    </text>
  </g>

  <g transform="translate(1122 170)" filter="url(#smallShadow)">
    <rect x="0" y="0" width="72" height="236" rx="22" fill="#020617" fill-opacity="0.38" stroke="#FFFFFF" stroke-opacity="0.12"/>
    <path d="M36 32V190" stroke="#94A3B8" stroke-width="4" stroke-linecap="round"/>
    <circle cx="36" cy="48" r="11" fill="#60A5FA"/>
    <circle cx="36" cy="112" r="11" fill="#34D399"/>
    <circle cx="36" cy="176" r="11" fill="#FBBF24"/>
  </g>

  <g transform="translate(1058 456)">
    <path d="M0 28H74" stroke="#A7F3D0" stroke-width="5" stroke-linecap="round"/>
    <path d="M54 10L76 28L54 46" stroke="#A7F3D0" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
    <text x="-196" y="36" fill="#D1FAE5" font-family="Segoe UI, Arial, sans-serif" font-size="20" font-weight="750">
      source-driven updates
    </text>
  </g>
</svg>
'''


def generate_banner_from_catalog(catalog_path: Path, output_path: Path) -> None:
    catalog = load_catalog(catalog_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_banner(catalog), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the README SVG banner from docs/catalog.json.")
    parser.add_argument("--catalog", default="docs/catalog.json")
    parser.add_argument("--output", default=".github/assets/repo-banner.svg")
    args = parser.parse_args()

    catalog_path = (REPO_ROOT / args.catalog).resolve()
    output_path = (REPO_ROOT / args.output).resolve()
    generate_banner_from_catalog(catalog_path, output_path)
    print(f"Wrote banner: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
