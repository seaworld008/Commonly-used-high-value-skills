"""Offline integration checks for provider selection and incomplete Input Guard scans."""

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


GUARD = Path(__file__).resolve().parents[1] / "skills/openclaw-memory-and-safety/input-guard/scripts"
MODELS = {
    "OPENAI_API_KEY": "openai-fixture", "INPUT_GUARD_OPENAI_MODEL": "openai-model",
    "ANTHROPIC_API_KEY": "anthropic-fixture", "INPUT_GUARD_ANTHROPIC_MODEL": "anthropic-model",
}
BUNDLED = {"categories": [{"id": "manipulation", "name": "Bundled", "threats": [{"name": "Bundled threat"}]}]}
FRESH = {"categories": [{"name": "Fresh", "threats": [{"name": "Fresh threat"}]}]}


class RequestError(Exception):
    pass


class RequestTimeout(RequestError):
    pass


def load_script(name, monkeypatch):
    spec = importlib.util.spec_from_file_location(name, GUARD / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def guard(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(os, "environ", {})
    monkeypatch.setattr(sys, "path", sys.path.copy())
    http = SimpleNamespace(post=Mock(), get=Mock(),
                           exceptions=SimpleNamespace(Timeout=RequestTimeout, RequestException=RequestError))
    monkeypatch.setitem(sys.modules, "requests", http)
    taxonomy = load_script("get_taxonomy", monkeypatch)
    package = tmp_path / "package"
    package.mkdir()
    bundled = package / "taxonomy.json"
    bundled.write_text(json.dumps(BUNDLED))
    monkeypatch.setattr(taxonomy, "SKILL_ROOT", package)
    monkeypatch.setattr(taxonomy, "TAXONOMY_FILE", bundled)

    scanner = load_script("llm_scanner", monkeypatch)
    scan = load_script("scan", monkeypatch)
    gateway = Mock()
    monkeypatch.setattr(scanner.subprocess, "run", gateway)

    def cli(module, *args):
        monkeypatch.setattr(sys, "argv", [module.__name__, *args])
        try:
            module.main()
            code = 0
        except SystemExit as exc:
            code = exc.code
        out, err = capsys.readouterr()
        return code, out, err

    return SimpleNamespace(http=http, gateway=gateway, scan=scan, taxonomy=taxonomy, bundled=bundled,
                           cache=tmp_path / "external" / "cache.json", cli=cli)


def reply(provider, verdict="SAFE", severity="SAFE"):
    content = json.dumps({"verdict": verdict, "severity": severity, "confidence": 0.9, "reasoning": "Fixture assessment.",
                          "threats": [] if verdict == "SAFE" else [
                              {"category": "manipulation", "threat_type": "Bundled threat",
                               "description": "Fixture finding.", "evidence": "fixture"}]})
    return ({"choices": [{"message": {"content": content}}]} if provider == "openai"
            else {"content": [{"text": content}]})


@pytest.mark.parametrize("provider,env", [
    ("openai", {"ANTHROPIC_API_KEY": "other", "ANTHROPIC_MODEL": "other-model"}),
    ("anthropic", {"OPENAI_API_KEY": "other", "OPENAI_MODEL": "other-model"}),
    ("anthropic", {"ANTHROPIC_API_KEY": "fixture", "OPENAI_MODEL": "other-model"}),
    ("openai", {}), (None, {}),
    ("openai", {"INPUT_GUARD_CREDENTIAL_SOURCE": "unknown", **MODELS}),
])
def test_missing_matching_configuration_stops_before_io(guard, provider, env):
    os.environ.update(env)
    flags = ["--llm-provider", provider] if provider else []
    code, out, _ = guard.cli(guard.scan, "fixture content", "--llm-only", "--json", *flags)
    assert code != 0 and json.loads(out)["llm"]["verdict"] == "ERROR"
    guard.http.post.assert_not_called()
    guard.http.get.assert_not_called()
    guard.gateway.assert_not_called()


@pytest.mark.parametrize("provider,flags,model", [
    ("openai", [], "openai-model"),
    ("openai", ["--llm-provider", "openai"], "openai-model"),
    ("anthropic", ["--llm-provider", "anthropic"], "anthropic-model"),
    ("anthropic", ["--llm-provider", "anthropic", "--llm-model", "explicit"], "explicit"),
])
def test_selected_vendor_receives_only_its_configuration(guard, provider, flags, model):
    os.environ.update(MODELS)
    if model == "explicit":
        del os.environ["INPUT_GUARD_ANTHROPIC_MODEL"]
    guard.http.post.return_value.json.return_value = reply(provider)
    code, out, _ = guard.cli(guard.scan, "fixture content", "--llm-only", "--quiet", *flags)
    assert code == 0 and out.strip() == "SAFE 0"
    guard.gateway.assert_not_called()
    guard.http.get.assert_not_called()
    args, kw = guard.http.post.call_args
    assert guard.http.post.call_count == 1 and kw["json"]["model"] == model
    if provider == "anthropic":
        assert args == ("https://api.anthropic.com/v1/messages",)
        assert kw["headers"]["x-api-key"] == "anthropic-fixture"
        assert "Authorization" not in kw["headers"]
    else:
        assert args == ("https://api.openai.com/v1/chat/completions",)
        assert kw["headers"]["Authorization"] == "Bearer openai-fixture"


@pytest.mark.parametrize("matching", [True, False])
def test_gateway_only_when_selected_and_no_source_mixing(guard, matching):
    os.environ.update(MODELS, INPUT_GUARD_CREDENTIAL_SOURCE="gateway")
    env = {"OPENAI_API_KEY": "gateway-openai", "OPENAI_MODEL": "gateway-model"}
    if matching:
        env.update(ANTHROPIC_API_KEY="gateway-anthropic", ANTHROPIC_MODEL="gateway-selected")
    guard.gateway.return_value.stdout = json.dumps({"env": env})
    guard.http.post.return_value.json.return_value = reply("anthropic", "MALICIOUS", "HIGH")
    code, out, _ = guard.cli(guard.scan, "fixture", "--llm-only", "--llm-provider", "anthropic", "--json")
    guard.gateway.assert_called_once()
    assert guard.gateway.call_args.args == (["openclaw", "gateway", "config.get"],)
    if matching:
        assert code == 1 and json.loads(out)["severity"] == "HIGH"
        _, kw = guard.http.post.call_args
        assert kw["headers"]["x-api-key"] == "gateway-anthropic" and kw["json"]["model"] == "gateway-selected"
    else:
        assert code != 0 and json.loads(out)["llm"]["verdict"] == "ERROR"
        guard.http.post.assert_not_called()


@pytest.mark.parametrize("flag", ["--quiet", "--json", None])
@pytest.mark.parametrize("failure", [RequestTimeout, RequestError, RuntimeError, None])
def test_llm_incomplete_scan_is_error_in_every_format(guard, flag, failure):
    os.environ.update(MODELS)
    if failure is None:
        guard.http.post.return_value.json.return_value = {"choices": []}
    else:
        guard.http.post.side_effect = failure("fixture-private-detail")
    flags = [flag] if flag else []
    code, out, err = guard.cli(guard.scan, "--llm-only", "fixture", *flags)
    assert code == 2 and "SAFE" not in out + err and "fixture-private-detail" not in out + err
    if flag == "--json":
        report = json.loads(out)
        assert report["severity"] == report["llm"]["verdict"] == "ERROR" and report["score"] is None
    elif flag == "--quiet":
        assert out.strip() == "ERROR"
    else:
        assert "ERROR" in out + err
    guard.http.post.assert_called_once()
    guard.gateway.assert_not_called()


@pytest.mark.parametrize("invalid", [{"message": "error"}, [], {"categories": []}, {"categories": {}},
                                     {"categories": [None]}, {"categories": [{"name": "   "}]},
                                     {"categories": [{"name": "x", "threats": {}}]},
                                     {"categories": [{"name": "x", "threats": ["bad"]}]}])
def test_invalid_refresh_preserves_old_cache_and_load_falls_back(guard, invalid):
    os.environ["PROMPTINTEL_API_KEY"] = "fixture"
    guard.cache.parent.mkdir()
    original = json.dumps(FRESH, indent=4).encode() + b"\n"
    guard.cache.write_bytes(original)
    guard.http.get.return_value.json.return_value = {"data": invalid}
    code, out, _ = guard.cli(guard.taxonomy, "refresh", "--cache-file", str(guard.cache))
    assert code != 0 and "updated" not in out
    assert guard.cache.read_bytes() == original and list(guard.cache.parent.iterdir()) == [guard.cache]

    guard.cache.write_text(json.dumps(invalid))
    os.environ.update(INPUT_GUARD_TAXONOMY_CACHE=str(guard.cache), OPENAI_API_KEY="fixture")
    guard.http.post.return_value.json.return_value = reply("openai")
    code, out, _ = guard.cli(guard.scan, "fixture", "--llm-only", "--quiet")
    assert code == 0 and out.strip() == "SAFE 0"
    prompt = guard.http.post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "Bundled threat" in prompt
    assert json.loads(guard.cache.read_text()) == invalid
    guard.http.get.assert_called_once()


@pytest.mark.parametrize("wrapped", [True, False])
def test_valid_refresh_and_readonly_defaults(guard, wrapped):
    os.environ["PROMPTINTEL_API_KEY"] = "fixture"
    original = guard.bundled.read_bytes()
    code, _, _ = guard.cli(guard.taxonomy, "refresh")
    assert code != 0
    guard.cli(guard.taxonomy, "clear")
    guard.http.get.assert_not_called()
    alias = guard.cache.with_suffix(".alias")
    alias.parent.mkdir()
    alias.symlink_to(guard.bundled)
    with pytest.raises(ValueError, match="outside the skill"):
        guard.taxonomy.get_taxonomy(force_refresh=True, cache_file=alias)
    guard.http.get.assert_not_called()

    guard.http.get.return_value.json.return_value = {"data": FRESH} if wrapped else FRESH
    code, out, _ = guard.cli(guard.taxonomy, "fetch", "--cache-file", str(guard.cache))
    assert code == 0 and "1 categories" in out and json.loads(guard.cache.read_text()) == FRESH
    code, out, _ = guard.cli(guard.taxonomy, "prompt", "--cache-file", str(guard.cache))
    assert code == 0 and "Fresh threat" in out and guard.bundled.read_bytes() == original
    guard.http.get.assert_called_once()
