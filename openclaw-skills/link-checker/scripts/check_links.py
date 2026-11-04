#!/usr/bin/env python3
"""Check absolute URLs in text files: status, redirect chain, and simple risk hints.

Read-only: it sends GET/HEAD requests to the URLs found in the given files and
prints a TSV or JSON report. It never follows more than --max-redirects hops,
never downloads response bodies beyond the headers, and waits --delay seconds
between requests to the same host.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

URL_RE = re.compile(r"https?://[^\s)\"'<>\]`]+")
RISKY_EXT = (".exe", ".scr", ".msi", ".apk", ".dmg", ".bat", ".cmd", ".jar")
SHORTENERS = {"bit.ly", "t.co", "tinyurl.com", "goo.gl", "is.gd", "ow.ly", "buff.ly"}
USER_AGENT = "link-checker-skill/1.1 (+https://github.com/seaworld008/Commonly-used-high-value-skills)"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: D401 - stdlib hook
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def extract(paths: list[Path]) -> list[tuple[str, str]]:
    found: dict[str, str] = {}
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            print(f"skip {path}: {exc}", file=sys.stderr)
            continue
        for number, line in enumerate(lines, 1):
            for match in URL_RE.findall(line):
                url = match.rstrip(".,;:")
                found.setdefault(url, f"{path}:{number}")
    return [(url, where) for url, where in found.items()]


def request(url: str, method: str, timeout: float) -> tuple[int | None, str | None, str]:
    req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    try:
        with OPENER.open(req, timeout=timeout) as resp:
            return resp.status, None, resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Location"), exc.headers.get("Content-Type", "")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        return None, None, f"error: {reason}"


def check(url: str, timeout: float, max_redirects: int) -> dict:
    chain: list[dict] = []
    current = url
    for _ in range(max_redirects + 1):
        status, location, ctype = request(current, "HEAD", timeout)
        if status in (403, 405, 501):
            status, location, ctype = request(current, "GET", timeout)
        chain.append({"url": current, "status": status})
        if status in (301, 302, 303, 307, 308) and location:
            current = urllib.parse.urljoin(current, location)
            continue
        break
    final = chain[-1]
    hints = []
    start_host = urllib.parse.urlsplit(url).hostname or ""
    final_host = urllib.parse.urlsplit(final["url"]).hostname or ""
    if url.startswith("http://"):
        hints.append("plain-http")
    if start_host in SHORTENERS:
        hints.append("shortener")
    if "xn--" in start_host or "xn--" in final_host:
        hints.append("punycode")
    if final_host and start_host and final_host.split(".")[-2:] != start_host.split(".")[-2:]:
        hints.append("cross-domain-redirect")
    if any(hop["status"] in (301, 308) for hop in chain[:-1]):
        hints.append("permanent-redirect")
    if len(chain) - 1 > 3:
        hints.append("long-redirect-chain")
    if urllib.parse.urlsplit(final["url"]).path.lower().endswith(RISKY_EXT):
        hints.append("executable-download")
    status = final["status"]
    if status is None or (status >= 400 and status not in (401, 403, 429)):
        verdict = "broken"
    elif status in (401, 403, 429) or hints or status in (301, 302, 303, 307, 308):
        verdict = "review"
    else:
        verdict = "pass"
    return {
        "url": url,
        "final_url": final["url"],
        "status": status,
        "redirects": len(chain) - 1,
        "chain": chain,
        "content_type": ctype,
        "hints": hints,
        "verdict": verdict,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path, help="Markdown, HTML, or text files to scan")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--max-redirects", type=int, default=10)
    parser.add_argument("--delay", type=float, default=0.5, help="seconds between requests to one host")
    parser.add_argument("--json", action="store_true", help="print JSON instead of TSV")
    parser.add_argument("--list-only", action="store_true", help="only extract URLs, send no requests")
    args = parser.parse_args()

    urls = extract(args.files)
    if args.list_only:
        for url, where in urls:
            print(f"{where}\t{url}")
        return 0

    last_hit: dict[str, float] = {}
    results = []
    for url, where in urls:
        host = urllib.parse.urlsplit(url).hostname or ""
        wait = args.delay - (time.monotonic() - last_hit.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        result = check(url, args.timeout, args.max_redirects)
        last_hit[host] = time.monotonic()
        result["where"] = where
        results.append(result)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("verdict\tstatus\tredirects\twhere\turl\tfinal_url\thints")
        for r in results:
            print(f"{r['verdict']}\t{r['status']}\t{r['redirects']}\t{r['where']}\t{r['url']}\t{r['final_url']}\t{','.join(r['hints'])}")
    return 1 if any(r["verdict"] == "broken" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
