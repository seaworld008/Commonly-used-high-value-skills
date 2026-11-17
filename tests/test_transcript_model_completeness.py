"""Offline response-contract tests: real processor, HTTPX transport and core CLI.

Run with --basetemp under the task's TMPDIR; no real provider or accuracy eval.
"""
import asyncio
import builtins
import importlib
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import types

import httpx
import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/office-white-collar/transcript-fixer/scripts"
TEXT = "第一句话。第二句话。"
KEY = "synthetic-completeness-key"


def message(*texts, **extra):
    return {"type": "message", "role": "assistant", "stop_reason": "end_turn",
            "content": [{"type": "text", "text": text} for text in texts], **extra}


BAD_RESPONSES = [
    pytest.param(message(""), id="empty-text"),
    pytest.param(message(" \n\t"), id="whitespace-text"),
    pytest.param(message("第一句话。", stop_reason="max_tokens"), id="truncated"),
    pytest.param(message(TEXT, stop_reason=None), id="unfinished"),
    pytest.param(message(TEXT, stop_reason="pause_turn"), id="paused"),
    pytest.param(message(TEXT, stop_reason="stop_sequence"), id="unrequested-stop"),
    pytest.param(message(TEXT, stop_reason="tool_use"), id="tool-stop"),
    pytest.param(message(TEXT, stop_reason="refusal"), id="refusal-stop"),
    pytest.param(message(TEXT, stop_reason="unknown"), id="unknown-stop"),
    pytest.param({"content": [{"type": "text", "text": TEXT}]}, id="missing-stop"),
    pytest.param(message(TEXT, status="incomplete"), id="incomplete-status"),
    pytest.param(message(TEXT, incomplete_details={"reason": "max_tokens"}), id="incomplete-details"),
    pytest.param(message(TEXT, incomplete=True), id="incomplete-flag"),
    pytest.param(message(TEXT, error={"message": "PRIVATE_PROVIDER_BODY"}), id="top-error"),
    pytest.param(message(TEXT, type="error"), id="error-type"),
    pytest.param(message(TEXT, role="user"), id="wrong-role"),
    pytest.param(message(content=[]), id="no-blocks"),
    pytest.param(message(content=None), id="null-content"),
    pytest.param(message(content="not blocks"), id="string-content"),
    pytest.param(message(content=[None]), id="null-block"),
    pytest.param(message(content=[{"text": TEXT}]), id="missing-block-type"),
    pytest.param(message(content=[{"type": "text", "text": 42}]), id="nonstring-text"),
    pytest.param(message(content=[{"type": "text"}]), id="missing-text"),
    pytest.param(message(TEXT, content=[{"type": "text", "text": TEXT},
                                      {"type": "error", "message": "PRIVATE_PROVIDER_BODY"}]), id="later-error"),
    pytest.param(message(TEXT, content=[{"type": "text", "text": TEXT},
                                      {"type": "tool_use", "id": "synthetic"}]), id="later-tool"),
    pytest.param(message(TEXT, content=[{"type": "text", "text": TEXT},
                                      {"type": "text", "text": None}]), id="later-invalid-text"),
    pytest.param(message(content=[{"type": "text", "text": TEXT,
                                  "error": "PRIVATE_PROVIDER_BODY"}]), id="text-with-error"),
    pytest.param(message(TEXT, content=[{"type": "thinking", "thinking": None},
                                      {"type": "text", "text": TEXT}]), id="invalid-reasoning"),
    pytest.param(message(TEXT, content=[{"type": "text", "text": TEXT},
                                      {"type": "future_unknown_block"}]), id="unknown-block"),
    pytest.param(message(content=[{"type": "thinking", "thinking": "synthetic"}]), id="no-output-text"),
    pytest.param([], id="nonobject-json"),
]


@pytest.fixture
def processor_module(monkeypatch):
    # Namespace packages isolate imports from other tests, without stubbing logic.
    package = "_transcript_completeness_core"
    for name, path in ((package, SCRIPTS / "core"), ("utils", SCRIPTS / "utils")):
        namespace = types.ModuleType(name)
        namespace.__path__ = [str(path)]
        monkeypatch.setitem(sys.modules, name, namespace)
    for name in ("utils.logging_config", "utils.retry_logic"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.setattr(sys, "path", sys.path.copy())
    module = importlib.import_module(package + ".ai_processor_async")
    yield module
    for name in list(sys.modules):
        if name.startswith(package + ".") or name in ("utils.logging_config", "utils.retry_logic"):
            del sys.modules[name]


def install_transport(module, monkeypatch, handler):
    """Replace only HTTP transport; keep request encoding and response parsing real."""
    real_client = httpx.AsyncClient
    clients = []

    def client(**kwargs):
        # Separate tests exercise production defaults with h2 unavailable.
        kwargs["http2"] = False
        kwargs["trust_env"] = False
        result = real_client(transport=httpx.MockTransport(handler), **kwargs)
        clients.append(result)
        return result

    monkeypatch.setattr(module.httpx, "AsyncClient", client)
    return clients


@pytest.mark.parametrize("bad", BAD_RESPONSES)
@pytest.mark.parametrize("fallback_ok", [True, False], ids=["fallback-recovers", "both-invalid"])
def test_invalid_success_response_falls_back_once_or_fails(
    bad, fallback_ok, processor_module, monkeypatch, caplog
):
    processor = processor_module.AIProcessorAsync(KEY, base_url="https://provider.invalid")
    calls = []

    def handler(request):
        model = json.loads(request.content)["model"]
        calls.append(model)
        body = message(TEXT) if fallback_ok and model == processor.fallback_model else bad
        return httpx.Response(200, json=body)

    clients = install_transport(processor_module, monkeypatch, handler)
    with caplog.at_level(logging.DEBUG):
        if fallback_ok:
            assert processor.process(TEXT) == (TEXT, [])
            assert processor.last_run_metadata == {
                "models_used": [processor.fallback_model], "chunks_processed": 1}
        else:
            with pytest.raises(RuntimeError, match="AI correction failed for 1/1"):
                processor.process(TEXT)
            assert processor.last_run_metadata == {}
    assert calls == [processor.model, processor.fallback_model]
    assert all(client.is_closed for client in clients)
    assert processor._http_client is None
    assert all(secret not in str(record.__dict__) for record in caplog.records
               for secret in (KEY, TEXT, "PRIVATE_PROVIDER_BODY"))


@pytest.mark.parametrize("body", [
    message(TEXT),
    message("第一句话。", "第二句话。"),
    message("", "第一句话。", "第二句话。", ""),
    message(content=[{"type": "thinking", "thinking": "synthetic reasoning"},
                     {"type": "text", "text": "第一句话。"},
                     {"type": "redacted_thinking", "data": "synthetic"},
                     {"type": "text", "text": "第二句话。"}]),
])
def test_all_text_blocks_are_joined_without_invented_separators(
    body, processor_module, monkeypatch
):
    processor = processor_module.AIProcessorAsync(KEY)
    calls = []

    def handler(request):
        calls.append(json.loads(request.content)["model"])
        return httpx.Response(200, json=body)

    install_transport(processor_module, monkeypatch, handler)
    assert processor.process(TEXT) == (TEXT, [])
    assert calls == [processor.model]
    assert processor.last_run_metadata == {"models_used": [processor.model], "chunks_processed": 1}


@pytest.mark.parametrize("failure", ["http-400", "invalid-json", "http-503"])
def test_transport_errors_retain_existing_retry_and_fallback_policy(
    failure, processor_module, monkeypatch
):
    processor = processor_module.AIProcessorAsync(KEY)
    calls = []

    def handler(request):
        model = json.loads(request.content)["model"]
        calls.append(model)
        if model != processor.model:
            return httpx.Response(200, json=message(TEXT))
        if failure == "invalid-json":
            return httpx.Response(200, text="not-json")
        return httpx.Response(503 if failure == "http-503" else 400,
                              json={"error": "synthetic provider failure"})

    async def no_wait(_):
        pass

    monkeypatch.setattr(processor_module.asyncio, "sleep", no_wait)
    install_transport(processor_module, monkeypatch, handler)
    assert processor.process(TEXT) == (TEXT, [])
    attempts = 3 if failure == "http-503" else 1
    assert calls == [processor.model] * attempts + [processor.fallback_model]
    assert processor.last_run_metadata == {"models_used": [processor.fallback_model], "chunks_processed": 1}


@pytest.mark.parametrize("fallback", ["", "GLM-4.6"])
def test_invalid_response_without_distinct_fallback_fails_once(
    fallback, processor_module, monkeypatch
):
    processor = processor_module.AIProcessorAsync(KEY, fallback_model=fallback)
    calls = []

    def handler(request):
        calls.append(json.loads(request.content)["model"])
        return httpx.Response(200, json=message(""))

    install_transport(processor_module, monkeypatch, handler)
    with pytest.raises(RuntimeError, match="1/1"):
        processor.process(TEXT)
    assert calls == [processor.model]
    assert processor.last_run_metadata == {}


def test_completed_correction_keeps_public_change_tuple(processor_module, monkeypatch):
    processor = processor_module.AIProcessorAsync(KEY)
    install_transport(processor_module, monkeypatch,
                      lambda request: httpx.Response(200, json=message("会议记录")))
    corrected, changes = processor.process("会议记绿")
    assert corrected == "会议记录"
    assert len(changes) == 1
    assert changes[0].from_text == "绿"
    assert changes[0].to_text == "录"
    assert processor.last_run_metadata == {"models_used": [processor.model], "chunks_processed": 1}


def test_multichunk_metadata_and_reused_processor_failure(processor_module, monkeypatch):
    processor = processor_module.AIProcessorAsync(KEY, max_concurrent=2)
    processor.max_chunk_size = 3
    text = "甲句。\n\n乙句。\n\n丙句。\n\n丁句。"
    failure = False
    calls = []

    async def handler(request):
        data = json.loads(request.content)
        chunk = data["messages"][0]["content"].rsplit("\n\n", 1)[-1]
        calls.append((chunk, data["model"]))
        # Force completion order to differ from source order.
        await asyncio.sleep(0.002 if chunk == "甲句。" else 0)
        bad = chunk == "乙句。" and (failure or data["model"] == processor.model)
        return httpx.Response(200, json=message("", stop_reason="max_tokens") if bad else message(chunk))

    install_transport(processor_module, monkeypatch, handler)
    assert processor.process(text) == (text, [])
    assert processor.last_run_metadata == {
        "models_used": [processor.model, processor.fallback_model], "chunks_processed": 4}
    assert len(calls) == 5
    failure = True
    with pytest.raises(RuntimeError, match="1/4"):
        processor.process(text)
    assert processor.last_run_metadata == {}
    assert processor._http_client is None


def test_empty_input_has_zero_completed_chunks(processor_module, monkeypatch):
    processor = processor_module.AIProcessorAsync(KEY)
    processor.last_run_metadata = {"models_used": ["old"], "chunks_processed": 99}

    def forbidden(**kwargs):
        raise AssertionError("empty input must not request a model")

    monkeypatch.setattr(processor_module.httpx, "AsyncClient", forbidden)
    assert processor.process("") == ("", [])
    assert processor.last_run_metadata == {"models_used": [], "chunks_processed": 0}


@pytest.mark.parametrize("fallback", [False, True])
def test_default_client_works_when_h2_import_is_unavailable(fallback, processor_module, monkeypatch):
    original_import = builtins.__import__

    def without_h2(name, *args, **kwargs):
        if name == "h2" or name.startswith("h2."):
            raise ImportError("synthetic missing optional h2")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_h2)
    processor = processor_module.AIProcessorAsync(KEY)
    calls = []

    async def offline_send(transport, request):
        model = json.loads(request.content)["model"]
        calls.append(model)
        if fallback and model == processor.model:
            return httpx.Response(400, json={"error": "synthetic"})
        return httpx.Response(200, json=message(TEXT))

    # Keep production AsyncClient construction unchanged. Replace only its final
    # transport send, so h2 absence is exercised across a full correction run.
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", offline_send)
    assert processor.process(TEXT) == (TEXT, [])
    assert calls == [processor.model] + ([processor.fallback_model] if fallback else [])
    assert processor.last_run_metadata == {
        "models_used": [processor.fallback_model if fallback else processor.model], "chunks_processed": 1}
    assert processor._http_client is None


# The subprocess executes the actual CLI entry/parser/handlers against real files.
# Only the provider transport is synthetic; no sockets, account or service needed.
CLI_RUNNER = r'''
import json
from pathlib import Path
import runpy
import sys
import httpx

scripts, responses_path, calls_path, *cli_args = sys.argv[1:]
bodies = json.loads(Path(responses_path).read_text())
calls = []

def handler(request):
    calls.append(json.loads(request.content)["model"])
    Path(calls_path).write_text(json.dumps(calls))
    return httpx.Response(200, json=bodies[min(len(calls) - 1, len(bodies) - 1)])

real_init = httpx.AsyncClient.__init__
def offline_init(self, *args, **kwargs):
    kwargs.update(transport=httpx.MockTransport(handler), http2=False, trust_env=False)
    real_init(self, *args, **kwargs)
httpx.AsyncClient.__init__ = offline_init
sys.path.insert(0, scripts)
sys.argv = [str(Path(scripts) / "fix_transcription.py"), *cli_args]
runpy.run_path(sys.argv[0], run_name="__main__")
'''


@pytest.mark.parametrize("mode", ["empty", "truncated", "multi", "recover", "single"])
def test_real_cli_preserves_old_stage2_on_incomplete_models(mode, tmp_path):
    runner = tmp_path / "offline_cli.py"
    runner.write_text(CLI_RUNNER)
    source = tmp_path / "input.md"
    source.write_text(TEXT)
    stage2 = tmp_path / "input_stage2.md"
    stage2.write_text("OLD-VALID-STAGE-2")
    bad = message("") if mode == "empty" else message("第一句话。", stop_reason="max_tokens")
    bodies = ([bad, bad] if mode in ("empty", "truncated") else
              [bad, message(TEXT)] if mode == "recover" else
              [message("第一句话。", "第二句话。")] if mode == "multi" else [message(TEXT)])
    responses, calls, manifest = [tmp_path / name for name in ("responses.json", "calls.json", "manifest.json")]
    responses.write_text(json.dumps(bodies))
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("TRANSCRIPT_FIXER_") and key not in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL")}
    env.update(GLM_API_KEY=KEY, TRANSCRIPT_FIXER_CONFIG_DIR=str(tmp_path / "config"),
               TRANSCRIPT_FIXER_DB_PATH=str(tmp_path / "dictionary.db"),
               TRANSCRIPT_FIXER_ENABLE_LEARNING="0", TRANSCRIPT_FIXER_OUTPUT_MANIFEST=str(manifest),
               PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run([sys.executable, str(runner), str(SCRIPTS), str(responses), str(calls),
                             "--input", str(source), "--stage", "2"],
                            env=env, cwd=tmp_path, text=True, capture_output=True, timeout=30)
    failed = mode in ("empty", "truncated")
    assert result.returncode == (1 if failed else 0), result.stdout + result.stderr
    assert source.read_text() == TEXT
    assert (tmp_path / "input_stage1.md").read_text() == TEXT
    assert stage2.read_text() == ("OLD-VALID-STAGE-2" if failed else TEXT)
    assert ("Correction complete!" in result.stdout) is not failed
    outputs = json.loads(manifest.read_text())["outputs"]
    assert (str(stage2) in outputs) is not failed
    assert json.loads(calls.read_text()) == (["GLM-4.6", "GLM-4.5-Air"]
                                            if failed or mode == "recover" else ["GLM-4.6"])
    assert KEY not in result.stdout + result.stderr
    assert TEXT not in result.stdout + result.stderr
