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
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.client import InvalidURL
from pathlib import Path

URL_RE = re.compile(r"https?://[^\s)\"'<>\]`]+")
RISKY_EXT = (".exe", ".scr", ".msi", ".apk", ".dmg", ".bat", ".cmd", ".jar")
SHORTENERS = {"bit.ly", "t.co", "tinyurl.com", "goo.gl", "is.gd", "ow.ly", "buff.ly"}
USER_AGENT = "link-checker-skill/1.1 (+https://github.com/seaworld008/Commonly-used-high-value-skills)"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        # Defer to HTTPError without urllib parsing or following Location.
        return None

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302


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


def request(url: str, method: str, timeout: float, host: str,
            delay: float, last_hit: dict[str, float]) -> tuple[int | None, str | None, str]:
    req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    if host in last_hit:
        wait = delay - (time.monotonic() - last_hit[host])
        if wait > 0:
            time.sleep(wait)
    last_hit[host] = time.monotonic()
    try:
        with OPENER.open(req, timeout=timeout) as resp:
            return resp.status, None, resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, exc.headers.get("Location"), exc.headers.get("Content-Type", "")
    except (InvalidURL, UnicodeError):
        return None, None, "invalid-url"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        if isinstance(reason, ssl.SSLError):
            return None, None, "tls-error"
        return None, None, f"error: {reason}"


def http_target(url: str) -> urllib.parse.SplitResult:
    if re.search(r"[\x00-\x20\x7f]", url):
        raise ValueError("invalid-url")
    try:
        parts = urllib.parse.urlsplit(url)
        _ = parts.port  # validate the port syntax and range
        host = parts.hostname
    except ValueError:
        raise ValueError("invalid-url") from None
    if parts.scheme not in ("http", "https"):
        raise ValueError("unsupported-scheme")
    # urllib.request unquotes the authority before sending it. Accept only an
    # unambiguous host and optional port for the hostname comparison below.
    if not host or any(c in parts.netloc for c in ("@", "%", "\\")):
        raise ValueError("invalid-url")
    if "[" in parts.netloc and not re.fullmatch(r"\[[^\]]+\](?::[0-9]+)?", parts.netloc):
        raise ValueError("invalid-url")
    return parts


def check(url: str, timeout: float, max_redirects: int, delay: float = 0.5,
          last_hit: dict[str, float] | None = None) -> dict:
    if last_hit is None:
        last_hit = {}
    chain: list[dict] = []
    current = url
    hints = []
    ctype = ""
    start_host = None
    final_path = ""
    while True:
        try:
            target = http_target(current)
        except ValueError as exc:
            hints.append(str(exc))
            break
        host = target.hostname
        if start_host is None:
            start_host = host
        if host != start_host:
            hints.append("cross-domain-redirect")
            break
        if chain and len(chain) > max_redirects:
            break
        final_path = target.path
        if target.scheme == "http" and "plain-http" not in hints:
            hints.append("plain-http")
        status, location, ctype = request(current, "HEAD", timeout, host, delay, last_hit)
        if status in (403, 405, 501):
            status, location, ctype = request(current, "GET", timeout, host, delay, last_hit)
        chain.append({"url": current, "status": status})
        if status in (301, 302, 303, 307, 308) and location:
            chain[-1]["location"] = location
            try:
                current = urllib.parse.urljoin(current, location)
            except ValueError:
                hints.append("invalid-url")
                break
            continue
        break
    final = chain[-1] if chain else {"url": url, "status": None}
    if start_host in SHORTENERS:
        hints.append("shortener")
    if "xn--" in (start_host or ""):
        hints.append("punycode")
    if any(hop["status"] in (301, 308) and "location" in hop for hop in chain):
        hints.append("permanent-redirect")
    if len(chain) - 1 > 3:
        hints.append("long-redirect-chain")
    if final_path.lower().endswith(RISKY_EXT):
        hints.append("executable-download")
    status = final["status"]
    if status is None and ctype in ("tls-error", "invalid-url"):
        hints.append(ctype)
        verdict = "review"
    elif not chain:
        verdict = "review"
    elif status is None or (status >= 400 and status not in (401, 403, 429)):
        verdict = "broken"
    elif status in (401, 403, 429) or hints or status in (301, 302, 303, 307, 308):
        verdict = "review"
    else:
        verdict = "pass"
    return {
        "url": url,
        "final_url": final["url"],
        "status": status,
        "redirects": max(0, len(chain) - 1),
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
        result = check(url, args.timeout, args.max_redirects, args.delay, last_hit)
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
