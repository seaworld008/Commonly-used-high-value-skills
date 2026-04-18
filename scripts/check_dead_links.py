#!/usr/bin/env python3
"""Scan repo markdown files for dead external links.

Collects every http(s) URL mentioned in human-authored markdown files,
deduplicates them, and issues HEAD requests (with GET fallback) to detect
4xx/5xx responses. Intended for a monthly CI run that opens an issue rather
than gates pushes.

Usage:
    python scripts/check_dead_links.py --output docs/sources/reports/dead-links.json
    python scripts/check_dead_links.py --fail-on-dead   # exit 1 if any dead
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
URL_RE = re.compile(r"https?://[^\s\)\]\}'\"<>`]+")
# Ignore URLs that are documented examples, anchors to bug trackers, or
# known-permissive hosts that reject HEAD probes.
IGNORE_HOSTS = {
    "localhost",
    "127.0.0.1",
    "example.com",
    "example.org",
    "your-org.com",
    "schemas.openxmlformats.org",
}
IGNORE_HOST_SUFFIXES = (".internal", ".example.com")
IGNORE_URL_SNIPPETS = (
    "${",
    "{zone_id",
    "ZONE_ID",
    "your-app.vercel.app",
    "your-cache-server.internal",
    "agents.internal",
    "api.example.com",
    "api.service.com",
    "api.tasks.example.com",
    "app-name-",
    "old.com/",
    "broken.link",
    "competitor.com",
    "docs.myapp.com",
    "arxiv.org/abs/ID",
    "arXiv:ID",
    "DOI:10.1234/example",
    "staging.myapp.com",
    "your-project-ref.supabase.co",
    "suspect.xyz/login",
    "some-mcp-server.com",
    "mcp.internal.company.com",
    "mcp.mycompany.com",
    "vault.internal.company.com",
    "mcp.render.com/mcp",
    "bit.ly/3xyz",
    ":fileKey",
    ":fileName",
)
# Treat these codes as ok; some servers block HEAD or require cookies.
ACCEPTED_CODES = {200, 201, 202, 203, 204, 301, 302, 303, 307, 308, 400, 401, 403, 405, 429}
SCAN_GLOBS = (
    "README.md",
    "README.en.md",
    "docs/**/*.md",
    "skills/*/*/SKILL.md",
)
IGNORE_PATH_FRAGMENTS = (
    "openclaw-skills/",
    "docs/TAGS-INDEX.md",
    "docs/sources/reports/",
    "skills/.system/",
    "plugins/cache/",
)

PLACEHOLDER_PATH_PATTERNS = (
    "/user/repo",
    "/username/repo",
    "/org/repo",
    "/myorg/web-app",
    "/status/ID",
    "/status/123",
    "/article/123",
    "/pdf/ID",
)


def iter_markdown_files() -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for pattern in SCAN_GLOBS:
        for path in REPO_ROOT.glob(pattern):
            if not path.is_file():
                continue
            rel = str(path.relative_to(REPO_ROOT))
            if any(fragment in rel for fragment in IGNORE_PATH_FRAGMENTS):
                continue
            if path not in seen:
                seen.add(path)
                files.append(path)
    return sorted(files)


def should_ignore_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if host in IGNORE_HOSTS or any(host.endswith(suffix) for suffix in IGNORE_HOST_SUFFIXES):
        return True
    if any(snippet in url for snippet in IGNORE_URL_SNIPPETS):
        return True
    if any(ch in url for ch in ("{", "}", "[", "]", "\\")):
        return True
    if any(pattern in parsed.path for pattern in PLACEHOLDER_PATH_PATTERNS):
        return True
    return False


def collect_urls() -> dict[str, set[str]]:
    """Return {url: {repo_paths_that_reference_it}}."""
    urls: dict[str, set[str]] = {}
    for md_file in iter_markdown_files():
        text = md_file.read_text(encoding="utf-8", errors="replace")
        for m in URL_RE.finditer(text):
            url = m.group(0).rstrip(".,;:)")
            if should_ignore_url(url):
                continue
            urls.setdefault(url, set()).add(str(md_file.relative_to(REPO_ROOT)))
    return urls


def curl_probe(url: str, method: str, timeout: int) -> tuple[int | None, str]:
    curl = shutil.which("curl")
    if not curl:
        return None, "curl unavailable"
    cmd = [
        curl,
        "--silent",
        "--show-error",
        "--location",
        "--output",
        "/dev/null",
        "--write-out",
        "%{http_code}",
        "--user-agent",
        "skills-deadlink-bot/1.0",
        "--max-time",
        str(timeout),
        "--request",
        method,
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    code_text = (proc.stdout or "").strip()
    if proc.returncode == 0 and code_text.isdigit():
        status = int(code_text)
        if status != 0:
            return status, ""
    return None, (proc.stderr or f"curl rc={proc.returncode} code={code_text}").strip()


def probe(url: str, timeout: int = 10) -> tuple[str, int | None, str]:
    if shutil.which("curl"):
        for method in ("HEAD", "GET"):
            status, err = curl_probe(url, method, timeout)
            if status is not None:
                return url, status, ""
            if method == "GET":
                return url, None, err
    headers = {"User-Agent": "skills-deadlink-bot/1.0"}
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return url, resp.getcode(), ""
        except urllib.error.HTTPError as exc:
            if method == "GET":
                return url, exc.code, str(exc)
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if method == "GET":
                return url, None, str(exc)
            continue
    return url, None, "unreachable"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="docs/sources/reports/dead-links.json")
    parser.add_argument("--fail-on-dead", action="store_true")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    urls = collect_urls()
    print(f"Collected {len(urls)} unique URLs from repo markdown files")

    results: list[dict] = []
    dead: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(probe, u): u for u in sorted(urls)}
        for i, fut in enumerate(as_completed(futures), 1):
            url, status, err = fut.result()
            ok = status in ACCEPTED_CODES
            row = {
                "url": url,
                "status": status,
                "error": err,
                "ok": ok,
                "refs": sorted(urls[url])[:3],
                "ref_count": len(urls[url]),
            }
            results.append(row)
            if not ok:
                dead.append(row)
            if i % 50 == 0:
                print(f"  probed {i}/{len(urls)}", file=sys.stderr)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total": len(results),
        "dead_count": len(dead),
        "dead": dead,
        "all": results,
    }
    out = REPO_ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out.relative_to(REPO_ROOT)}  (dead: {len(dead)}/{len(results)})")

    if args.fail_on_dead and dead:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
