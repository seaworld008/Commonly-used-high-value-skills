#!/usr/bin/env python3
"""
Taxonomy Cache — Loads and optionally refreshes the MoltThreats LLM Security
Threats Classification taxonomy.

The taxonomy ships as taxonomy.json in the skill root directory and works
out of the box with no API key. When PROMPTINTEL_API_KEY is set, the file
is refreshed from the MoltThreats API (at most once per 24 hours).
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any

SKILL_ROOT = Path(__file__).parent.parent
TAXONOMY_FILE = SKILL_ROOT / "taxonomy.json"
REFRESH_TTL_SECONDS = 86400  # 24 hours

API_BASE = "https://api.promptintel.novahunting.ai/api/v1"


def get_api_key() -> Optional[str]:
    """Get PromptIntel API key from environment."""
    return os.environ.get("PROMPTINTEL_API_KEY")


def fetch_taxonomy(api_key: str) -> Dict[str, Any]:
    """Fetch taxonomy from MoltThreats API."""
    response = requests.get(
        f"{API_BASE}/taxonomy",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def _needs_refresh() -> bool:
    """Check if taxonomy.json is older than the refresh TTL."""
    if not TAXONOMY_FILE.exists():
        return True
    try:
        mtime = TAXONOMY_FILE.stat().st_mtime
        return (time.time() - mtime) > REFRESH_TTL_SECONDS
    except OSError:
        return True


def get_taxonomy(force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """
    Get taxonomy data.

    Loads from taxonomy.json (shipped with the skill). If PROMPTINTEL_API_KEY
    is set and the file is older than 24h (or force_refresh=True), refreshes
    from the API and overwrites the file.

    Returns None only if taxonomy.json doesn't exist and no API key is set.
    """
    api_key = get_api_key()

    # Refresh from API if key is available and file is stale
    if api_key and (force_refresh or _needs_refresh()):
        try:
            result = fetch_taxonomy(api_key)
            taxonomy = result.get("data", result)
            with open(TAXONOMY_FILE, "w") as f:
                json.dump(taxonomy, f, indent=2)
            return taxonomy
        except Exception as e:
            print(f"[taxonomy] API refresh failed: {e}", file=sys.stderr)
            # Fall through to load existing file

    # Load from file
    if TAXONOMY_FILE.exists():
        try:
            with open(TAXONOMY_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[taxonomy] Failed to read {TAXONOMY_FILE}: {e}", file=sys.stderr)
            return None

    return None


def build_threat_reference(taxonomy: Dict[str, Any]) -> str:
    """
    Build a concise threat reference string from taxonomy data
    for inclusion in the LLM detector prompt.
    """
    if not taxonomy:
        return ""

    lines = []
    categories = taxonomy.get("categories", [])

    for cat in categories:
        cat_name = cat.get("name", "Unknown")
        cat_desc = cat.get("description", "")
        lines.append(f"\n## {cat_name}")
        lines.append(f"{cat_desc}")

        for threat in cat.get("threats", []):
            name = threat.get("name", "")
            desc = threat.get("description", "")
            example = threat.get("example", "")
            lines.append(f"- **{name}**: {desc}")
            if example:
                lines.append(f"  Example: \"{example}\"")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Taxonomy Manager")
    parser.add_argument("action", choices=["fetch", "show", "prompt", "clear"],
                        help="fetch=refresh from API, show=display taxonomy, prompt=show LLM reference, clear=delete file")
    args = parser.parse_args()

    if args.action == "fetch":
        if not get_api_key():
            print("❌ PROMPTINTEL_API_KEY not set — cannot fetch from API")
            sys.exit(1)
        taxonomy = get_taxonomy(force_refresh=True)
        if taxonomy:
            print(f"✅ Taxonomy updated ({len(taxonomy.get('categories', []))} categories)")
        else:
            print("❌ Failed to fetch taxonomy")
            sys.exit(1)

    elif args.action == "show":
        taxonomy = get_taxonomy()
        if taxonomy:
            print(json.dumps(taxonomy, indent=2))
        else:
            print("No taxonomy available")
            sys.exit(1)

    elif args.action == "prompt":
        taxonomy = get_taxonomy()
        if taxonomy:
            print(build_threat_reference(taxonomy))
        else:
            print("No taxonomy available")
            sys.exit(1)

    elif args.action == "clear":
        if TAXONOMY_FILE.exists():
            TAXONOMY_FILE.unlink()
            print("✅ taxonomy.json deleted")
        else:
            print("No taxonomy file to clear")
