"""Record urllib's outgoing requests and advance a clock without using sockets."""

import importlib.util
import io
import json
import ssl
import sys
import urllib.error
import urllib.request
import urllib.response
from email.message import Message
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = (Path(__file__).resolve().parents[1] / "skills/security-and-reliability"
          / "link-checker/scripts/check_links.py")
START = "https://one.co.uk/guide"


@pytest.fixture
def checker(monkeypatch):
    spec = importlib.util.spec_from_file_location("check_links", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    now = 0.0
    calls = []
    replies = []

    def sleep(seconds):
        nonlocal now
        now += seconds

    def send(handler, connection, req, **kwargs):
        calls.append((req.full_url, req.get_method(), now))
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        status, location = reply
        headers = Message()
        if location:
            headers["Location"] = location
        response = urllib.response.addinfourl(io.BytesIO(), headers, req.full_url, status)
        response.msg = "fixture"
        return response

    open_request = module.OPENER.open

    def open_http(req, **kwargs):
        assert req.type in ("http", "https"), "unexpected non-HTTP transport"
        return open_request(req, **kwargs)

    monkeypatch.setattr(module.OPENER, "open", open_http)
    monkeypatch.setattr(module, "time", SimpleNamespace(monotonic=lambda: now, sleep=sleep))
    monkeypatch.setattr(urllib.request.AbstractHTTPHandler, "do_open", send)
    return module, replies, calls


@pytest.mark.parametrize("location,hint", [
    ("//two.co.uk/path", "cross-domain-redirect"),
    ("https://sub.one.co.uk/path", "cross-domain-redirect"),
    ("file:///fixture", "unsupported-scheme"),
    ("ftp://one.co.uk/doc", "unsupported-scheme"),
    ("https://[broken", "invalid-url"),
    ("https://one.co.uk:invalid/path", "invalid-url"),
    ("/invalid path", "invalid-url"),
])
def test_redirect_boundary_after_same_host_hop(checker, location, hint):
    module, replies, calls = checker
    replies.extend([(302, "/step"), (302, location)])
    result = module.check(START, 5, 10)
    assert [url for url, _, _ in calls] == [START, "https://one.co.uk/step"]
    assert result["verdict"] == "review" and hint in result["hints"]
    assert result["redirects"] == 1 and result["status"] == 302
    assert result["final_url"] == calls[-1][0]
    assert result["chain"][-1]["location"] == location


@pytest.mark.parametrize("url", ["file:///fixture", "ftp://one.co.uk/", "https://[invalid"])
def test_invalid_initial_target_has_no_requests(checker, url):
    module, _, calls = checker
    result = module.check(url, 5, 10)
    assert not calls and not result["chain"] and result["status"] is None
    assert result["verdict"] == "review"


def test_cli_rate_limit_for_every_request(checker, tmp_path, monkeypatch, capsys):
    module, replies, calls = checker
    other = "https://other.test/guide"
    last = "https://one.co.uk/last"
    links = tmp_path / "input.md"
    links.write_text("\n".join([START, other, last]), encoding="utf-8")
    replies.extend([(405, None), (302, "//ONE.co.uk/next"), (200, None),
                    (200, None), (200, None)])
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), str(links), "--delay", "2", "--json"])
    assert module.main() == 0
    assert calls == [(START, "HEAD", 0), (START, "GET", 2),
                     ("https://ONE.co.uk/next", "HEAD", 4),
                     (other, "HEAD", 4), (last, "HEAD", 6)]
    assert [row["verdict"] for row in json.loads(capsys.readouterr().out)] == ["pass"] * 3


@pytest.mark.parametrize("failure,verdict", [
    (urllib.error.URLError(ssl.SSLCertVerificationError("fixture")), "review"),
    (ssl.SSLError("fixture"), "review"),
    (urllib.error.URLError("fixture DNS failure"), "broken"),
    (TimeoutError("fixture"), "broken"),
])
def test_transport_failures_on_get_fallback(checker, failure, verdict):
    module, replies, calls = checker
    replies.extend([(405, None), failure])
    result = module.check(START, 5, 10)
    assert [method for _, method, _ in calls] == ["HEAD", "GET"]
    assert result["status"] is None and result["verdict"] == verdict
    assert ("tls-error" in result["hints"]) == (verdict == "review")


def test_redirect_limit_does_not_send_extra_request(checker):
    module, replies, calls = checker
    replies.append((302, "/next"))
    result = module.check(START, 5, 0)
    assert len(calls) == 1 and result["redirects"] == 0
    assert result["verdict"] == "review"


def test_list_only_sends_no_requests(checker, tmp_path, monkeypatch, capsys):
    module, _, calls = checker
    links = tmp_path / "input.md"
    links.write_text(START, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--list-only", str(links)])
    assert module.main() == 0
    assert not calls and START in capsys.readouterr().out
