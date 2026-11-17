"""Exercise CLI credential recipients, redirects and image receipts without sockets."""

import base64
import io
import json
import os
import runpy
import shutil
import subprocess
import sys
import time
import urllib.request
from email.message import Message
from http.client import InvalidURL
from pathlib import Path
from urllib.response import addinfourl

import pytest


SKILLS = Path(__file__).resolve().parents[1] / "skills"
SENTRY = SKILLS / "security-and-reliability/sentry/scripts/sentry_api.py"
IMAGE = SKILLS / "multimodal-media/gpt-image2/scripts/gpt-image2.mjs"
PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC"
SECRET = "synthetic-private-marker"
SIGNED_URL = f"https://objects.invalid/{SECRET}.png?signature={SECRET}"


@pytest.fixture
def sentry(monkeypatch, capsys):
    monkeypatch.setenv("SENTRY_AUTH_TOKEN", "fixture-key")
    monkeypatch.setenv("SENTRY_ORG", "local-org")
    monkeypatch.setenv("SENTRY_PROJECT", "local-project")
    monkeypatch.setenv("SENTRY_BASE_URL", "https://sentry.invalid")
    monkeypatch.setattr(urllib.request, "getproxies", lambda: {})
    monkeypatch.setattr(time, "sleep", lambda _: None)

    def invoke(routes, *args):
        hops = []

        def transport(handler, connection, req, **kwargs):
            hops.append((req.full_url, req.get_header("Authorization")))
            route = routes[len(hops) - 1]
            if isinstance(route, Exception):
                raise route
            status, location, payload = route
            headers = Message()
            if location:
                headers["Location"] = location
            response = addinfourl(io.BytesIO(json.dumps(payload).encode()), headers, req.full_url, status)
            response.msg = "fixture status"
            return response

        monkeypatch.setattr(urllib.request.AbstractHTTPHandler, "do_open", transport)
        monkeypatch.setattr(sys, "argv", [str(SENTRY), *args])
        try:
            runpy.run_path(str(SENTRY), run_name="__main__")
            code = 0
        except SystemExit as exc:
            code = exc.code
        out, err = capsys.readouterr()
        return hops, code, out, err

    return invoke


@pytest.mark.parametrize("location", [
    "https://other.invalid/private", "//other.invalid/next",
    "https://sentry.invalid:8443/private", "http://sentry.invalid/private",
    "https://name@sentry.invalid/private",
])
def test_sentry_rejects_redirect_before_next_request(sentry, location):
    routes = [(302, "/same-origin", None), (307, location, None), (200, None, {})]
    hops, code, out, err = sentry(routes, "issue-detail", "42")
    assert hops == [("https://sentry.invalid/api/0/issues/42/", "Bearer fixture-key"),
                    ("https://sentry.invalid/same-origin", "Bearer fixture-key")]
    assert code != 0 and not out
    assert "redirect" in err.lower() or "Invalid Sentry URL" in err
    assert location not in err


@pytest.mark.parametrize("base,target", [
    ("https://sentry.invalid", "https://SENTRY.invalid:443/next"),
    ("http://sentry.invalid:80", "http://sentry.invalid/next"),
    ("https://[::1]:444", "https://[::1]:444/next"),
])
def test_sentry_same_origin_retains_auth_and_redaction(sentry, base, target):
    routes = [(302, target, None), (200, None, {"email": "fixture@example.invalid"})]
    hops, code, out, err = sentry(routes, "--base-url", base, "issue-detail", "42")
    assert hops == [(base + "/api/0/issues/42/", "Bearer fixture-key"), (target, "Bearer fixture-key")]
    assert code == 0 and not err and json.loads(out) == {"email": "[REDACTED]"}


@pytest.mark.parametrize("args", [
    ["--org", "invalid org", "list-issues", "--query", SECRET],
    ["--project", "one/two", "list-issues", "--query", SECRET],
    ["--base-url", f"https://sentry.invalid:bad/{SECRET}", "issue-detail", "1"],
    ["--base-url", f"https://sentry.invalid?query={SECRET}", "issue-detail", "1"],
    ["issue-detail", ".."], ["issue-events", "1/other"], ["event-detail", f"id?query={SECRET}"],
])
def test_sentry_invalid_inputs_are_local_errors(sentry, args):
    hops, code, out, err = sentry([], *args)
    assert hops == [] and code != 0 and not out
    assert "Invalid Sentry" in err and "Traceback" not in err and SECRET not in err


def test_sentry_error_after_retry_is_summarized(sentry):
    hops, code, out, err = sentry([(502, None, SECRET), (403, None, SECRET)], "issue-detail", "1")
    assert len(hops) == 2 and code != 0 and not out and err == "Error: HTTP 403: Forbidden\n"


def test_sentry_transport_validation_error_is_summarized(sentry):
    hops, code, out, err = sentry([InvalidURL(SECRET)], "list-issues", "--query", SECRET)
    assert len(hops) == 1 and code != 0 and not out
    assert "Invalid Sentry" in err and SECRET not in err and "Traceback" not in err


@pytest.fixture
def image_cli(tmp_path):
    script = shutil.copy(IMAGE, tmp_path)
    home = tmp_path / "fixture-home"
    config = home / ".codex"
    config.mkdir(parents=True)
    (config / "auth.json").write_text('{"OPENAI_API_KEY":"fixture-key"}')
    mock = tmp_path / "transport.cjs"
    mock.write_text("""
        const fs = require("node:fs");
        const fixture = JSON.parse(process.env.FIXTURE);
        global.fetch = async (url, opts) => {
          const auth = new Headers(opts.headers).get("authorization");
          fs.appendFileSync("calls", JSON.stringify([url, opts.method, auth]) + "\\n");
          if (opts.method === "POST") {
            return Response.json(fixture.payload, {status: fixture.apiStatus});
          }
          return new Response(Buffer.from(fixture.download, "base64"), {
            status: fixture.downloadStatus, headers: {"content-type": "image/png"}
          });
        };
    """)

    def invoke(payload, *flags, config_text=None, api_status=200, download_status=200):
        if config_text is not None:
            (config / "config.toml").write_text(config_text)
            auth = ["--use-codex-auth"]
        else:
            auth = ["--base-url", "https://active.invalid/v1", "--api-key", "fixture-key"]
        response = {"payload": payload, "apiStatus": api_status, "downloadStatus": download_status,
                    "download": PNG if download_status == 200 else base64.b64encode(SECRET.encode()).decode()}
        result = subprocess.run(
            ["node", "--require", mock, script, "fixture", "--out-dir", "out", *auth, *flags],
            cwd=tmp_path, capture_output=True, text=True, timeout=15,
            env={"PATH": os.environ["PATH"], "HOME": str(home), "TMPDIR": str(tmp_path),
                 "FIXTURE": json.dumps(response)},
        )
        call_log = tmp_path / "calls"
        calls = [json.loads(line) for line in call_log.read_text().splitlines()] if call_log.exists() else []
        return result, calls, sorted((tmp_path / "out").glob("*"))

    return invoke


@pytest.mark.parametrize("config", [
    'model_provider = "openai"\n[model_providers.retired]\nbase_url = "https://retired.invalid"',
    '[model_providers.retired]\nbase_url = "https://retired.invalid"',
    'model_provider = "one"\n[model_providers.one]\n[model_providers.old] # retired\nbase_url = "https://retired.invalid"',
    'model_provider = "one"\n[model_providers.one]\nbase_url = "ftp://old.invalid"',
    'model_provider = "one"\n[model_providers.one]\nbase_url = "https:///old.invalid"',
    'model_provider = "one"\nnotes = """\n[model_providers.one]\nbase_url = "https://retired.invalid"\n"""',
])
def test_image_requires_an_active_http_address(image_cli, config):
    result, calls, files = image_cli({"data": [{"b64_json": PNG}]}, config_text=config)
    assert result.returncode != 0 and not calls and not files
    assert "地址" in result.stderr and "retired.invalid" not in result.stdout


def test_image_uses_selected_provider_and_signed_download_privately(image_cli):
    config = ('model_provider = "one"\n[model_providers.one] # active\nbase_url = "https://active.invalid/v1"\n'
              '[model_providers.retired]\nbase_url = "https://retired.invalid"')
    result, calls, files = image_cli({"data": [{"url": SIGNED_URL, "revised_prompt": SIGNED_URL}]}, config_text=config)
    assert result.returncode == 0 and SECRET not in result.stdout + result.stderr
    assert calls == [["https://active.invalid/v1/images/generations", "POST", "Bearer fixture-key"],
                     [SIGNED_URL, "GET", None]]
    assert len(files) == 1 and files[0].read_bytes() == base64.b64decode(PNG)


@pytest.mark.parametrize("payload", [None, {"data": {}}, {"data": []}, {"data": [{}]}, {"data": [None]},
                                     {"data": [{"b64_json": "%%%"}]}, {"data": [{"b64_json": "aGVsbG8="}]},
                                     {"data": [{"b64_json": f"data:image/jpeg;base64,{PNG}"}]}])
def test_image_unusable_payload_is_not_success(image_cli, payload):
    result, calls, files = image_cli(payload)
    assert result.returncode != 0 and len(calls) == 1 and not files
    assert "已保存 0 张" in result.stderr


@pytest.mark.parametrize("api_status,download_status", [(403, 200), (200, 403)])
def test_image_http_errors_omit_signed_urls_and_body(image_cli, api_status, download_status):
    result, calls, files = image_cli({"data": [{"url": SIGNED_URL}], "message": SECRET},
                                    api_status=api_status, download_status=download_status)
    assert result.returncode != 0 and not files and len(calls) == (1 if api_status == 403 else 2)
    assert "HTTP 403" in result.stderr and SECRET not in result.stdout + result.stderr


@pytest.mark.parametrize("data", [[{}, {"b64_json": PNG}], [{"b64_json": PNG}]])
def test_image_partial_result_reports_files_and_missing_count(image_cli, data):
    result, _, files = image_cli({"data": data}, "-n", "2")
    assert result.returncode != 0 and "已保存 1 张，预期 2 张，缺少 1 张" in result.stderr
    assert len(files) == 1 and files[0].read_bytes() == base64.b64decode(PNG)


def test_image_reference_keeps_first_data_url(image_cli, tmp_path):
    reference = tmp_path / "reference.png"
    reference.write_bytes(base64.b64decode(PNG))
    result, calls, files = image_cli({"data": [{"b64_json": f"data:image/png;base64,{PNG}"},
                                               {"url": SIGNED_URL}]}, "--image", str(reference), "-n", "3")
    assert result.returncode == 0 and len(files) == 1 and files[0].read_bytes() == reference.read_bytes()
    assert calls == [["https://active.invalid/v1/images/edits", "POST", "Bearer fixture-key"]]
