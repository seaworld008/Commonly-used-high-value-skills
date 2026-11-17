"""Check the CLI streams using synthetic responses and credentials."""

import io
import json
import runpy
import sys
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from pathlib import Path

import pytest


SCRIPT = (Path(__file__).resolve().parents[1] / "skills/security-and-reliability"
          / "sentry/scripts/sentry_api.py")


@pytest.fixture
def cli(monkeypatch):
    monkeypatch.setenv("SENTRY_AUTH_TOKEN", "fixture-auth-marker")
    monkeypatch.setenv("SENTRY_BASE_URL", "https://sentry.invalid")
    monkeypatch.setattr(time, "sleep", lambda _: None)

    def invoke(send, *flags):
        monkeypatch.setattr(urllib.request, "urlopen", send)
        monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--org", "fixture-org",
                                          "--project", "fixture-project", *flags,
                                          "list-issues", "--query", "fixture-private-query"])
        runpy.run_path(str(SCRIPT), run_name="__main__")

    return invoke


@pytest.mark.parametrize("status,body,flags,attempts", [
    (403, b'{"detail":"fixture-auth-marker","email":"person@example.invalid"}', [], 1),
    (502, b"<html>fixture-private-text 192.0.2.1</html>", ["--no-redact"], 2),
    (499, b"fixture-private-text", [], 1),
])
def test_http_error_prints_only_status_and_public_summary(cli, capsys, status, body, flags, attempts):
    streams = []

    def send(req):
        stream = io.BytesIO(body)
        streams.append(stream)
        raise urllib.error.HTTPError(req.full_url, status, "fixture-private-reason", {}, stream)

    with pytest.raises(SystemExit) as result:
        cli(send, *flags)
    output = capsys.readouterr()
    phrase = HTTPStatus(status).phrase if status in (403, 502) else "Request failed"
    assert result.value.code == 1 and not output.out
    assert output.err == f"Error: HTTP {status}: {phrase}\n"
    assert len(streams) == attempts and all(stream.closed for stream in streams)


def test_network_error_does_not_echo_url_or_reason(cli, capsys):
    def send(req):
        raise urllib.error.URLError("fixture-private-reason")

    with pytest.raises(SystemExit) as result:
        cli(send)
    output = capsys.readouterr()
    assert result.value.code == 1 and not output.out
    assert output.err == "Error: Network error contacting Sentry\n"


def test_success_still_redacts_nested_json(cli, capsys):
    def send(req):
        data = [{"email": "person@example.invalid", "detail": ["person@example.invalid 192.0.2.1"]}]
        resp = io.BytesIO(json.dumps(data).encode())
        resp.headers = {}
        return resp

    cli(send)
    output = capsys.readouterr()
    assert not output.err
    assert json.loads(output.out) == [{"email": "[REDACTED]", "detail": ["[REDACTED_EMAIL] [REDACTED_IP]"]}]
