#!/usr/bin/env python3
"""
Taxonomy Cache — Loads and optionally refreshes the MoltThreats LLM Security
Threats Classification taxonomy.

Reads use the bundled taxonomy.json or a selected cache. Use fetch with
--cache-file or INPUT_GUARD_TAXONOMY_CACHE to refresh an external cache.
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

SKILL_ROOT = Path(__file__).parent.parent
TAXONOMY_FILE = SKILL_ROOT / "taxonomy.json"

API_BASE = "https://api.promptintel.novahunting.ai/api/v1"


def get_api_key() -> Optional[str]:
    """Get PromptIntel API key from environment."""
    return os.environ.get("PROMPTINTEL_API_KEY")


def fetch_taxonomy(api_key: str) -> Dict[str, Any]:
    """Fetch taxonomy from MoltThreats API."""
    import requests

    response = requests.get(
        f"{API_BASE}/taxonomy",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def selected_cache(cache_file=None) -> Optional[Path]:
    value = cache_file or os.environ.get("INPUT_GUARD_TAXONOMY_CACHE")
    if value:
        path = Path(value)
        root = SKILL_ROOT.resolve()
        parent = path.parent.resolve()
        if parent == root or root in parent.parents or root in path.resolve().parents:
            raise ValueError("Select a taxonomy cache outside the skill directory")
        return path
    return None


def validate_taxonomy(taxonomy):
    """Check the fields consumed by build_threat_reference before use or storage."""
    categories = taxonomy.get("categories") if isinstance(taxonomy, dict) else None
    if not isinstance(categories, list) or not categories:
        raise ValueError("Taxonomy requires a nonempty categories list")

    def named_entry(entry):
        return (isinstance(entry, dict) and isinstance(entry.get("name"), str)
                and entry["name"].strip() and isinstance(entry.get("description", ""), str))

    for category in categories:
        if not named_entry(category) or not isinstance(category.get("threats", []), list):
            raise ValueError("Invalid taxonomy category")
        for threat in category.get("threats", []):
            if not named_entry(threat) or not isinstance(threat.get("example", ""), str):
                raise ValueError("Invalid taxonomy threat")
    return taxonomy


def get_taxonomy(force_refresh: bool = False, cache_file=None) -> Optional[Dict[str, Any]]:
    """Read a selected cache or the bundled taxonomy. Only an explicit refresh writes."""
    cache = selected_cache(cache_file)
    if force_refresh:
        api_key = get_api_key()
        if not api_key:
            print("❌ PROMPTINTEL_API_KEY not set — cannot fetch from API", file=sys.stderr)
            return None
        if cache is None:
            print("Select a cache with --cache-file or INPUT_GUARD_TAXONOMY_CACHE", file=sys.stderr)
            return None
        temporary = None
        try:
            result = fetch_taxonomy(api_key)
            taxonomy = validate_taxonomy(result.get("data", result) if isinstance(result, dict) else result)
            cache.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", dir=cache.parent, delete=False) as f:
                temporary = Path(f.name)
                json.dump(taxonomy, f, indent=2)
            temporary.replace(cache)
            return taxonomy
        except Exception:
            print("[taxonomy] API refresh failed", file=sys.stderr)
            return None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    for path in (cache, TAXONOMY_FILE):
        if path is None:
            continue
        try:
            with path.open() as f:
                return validate_taxonomy(json.load(f))
        except FileNotFoundError:
            continue
        except (ValueError, OSError) as e:
            print(f"[taxonomy] Failed to read {path}: {e}", file=sys.stderr)

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


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Taxonomy Manager")
    parser.add_argument("action", choices=["fetch", "refresh", "show", "prompt", "clear"],
                        help="fetch/refresh=update cache from API, show=display taxonomy, prompt=show LLM reference, clear=delete cache")
    parser.add_argument("--cache-file", type=Path,
                        help="external cache file (or set INPUT_GUARD_TAXONOMY_CACHE)")
    args = parser.parse_args()
    if args.action in ("fetch", "refresh"):
        taxonomy = get_taxonomy(force_refresh=True, cache_file=args.cache_file)
        if taxonomy:
            print(f"✅ Taxonomy updated ({len(taxonomy.get('categories', []))} categories)")
        else:
            print("❌ Failed to fetch taxonomy")
            sys.exit(1)

    elif args.action == "show":
        taxonomy = get_taxonomy(cache_file=args.cache_file)
        if taxonomy:
            print(json.dumps(taxonomy, indent=2))
        else:
            print("No taxonomy available")
            sys.exit(1)

    elif args.action == "prompt":
        taxonomy = get_taxonomy(cache_file=args.cache_file)
        if taxonomy:
            print(build_threat_reference(taxonomy))
        else:
            print("No taxonomy available")
            sys.exit(1)

    elif args.action == "clear":
        cache = selected_cache(args.cache_file)
        if cache and cache.exists():
            cache.unlink()
            print(f"✅ Cache deleted: {cache}")
        else:
            print("No taxonomy file to clear")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        sys.exit(str(exc))
