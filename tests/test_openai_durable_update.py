"""Offline image CLI compatibility checks; SDK clients are replaced in process."""

import base64
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import sys

import pytest


SCRIPT = (Path(__file__).resolve().parents[1]
          / "skills/multimodal-media/imagegen/scripts/image_gen.py")


@pytest.fixture
def cli(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("durable_image_cli", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    for name in ("_create_client", "_create_async_client"):
        monkeypatch.setattr(module, name, Mock(side_effect=AssertionError("unexpected SDK client")))

    def run(*flags):
        monkeypatch.setattr(sys, "argv", [str(SCRIPT), *flags])
        return module.main()

    return module, run


def read_previews(text):
    decoder = json.JSONDecoder()
    result = []
    while text.strip():
        text = text.lstrip()
        value, end = decoder.raw_decode(text)
        result.append(value)
        text = text[end:]
    return result


def test_generate_dry_run_paths_and_normalized_format(cli, capsys, tmp_path):
    module, run = cli
    run("generate", "--prompt", "fixture", "--n", "2", "--output-format", "jpg",
        "--out", "hero.jpeg", "--downscale-max-dim", "100", "--dry-run")
    preview = json.loads(capsys.readouterr().out)
    assert preview["model"] == "gpt-image-1.5"
    assert preview["output_format"] == "jpeg"
    assert preview["outputs"] == ["hero-1.jpeg", "hero-2.jpeg"]
    assert preview["outputs_downscaled"] == ["hero-1-web.jpeg", "hero-2-web.jpeg"]
    module._create_client.assert_not_called()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("fidelity", [None, "low", "high"])
def test_edit_dry_run_preserves_input_order_mask_and_fidelity(cli, capsys, tmp_path, fidelity):
    module, run = cli
    # Paths are enough for this CLI's preview; pixel/mask validity is not claimed.
    for name in ("target.png", "reference.png", "mask.png"):
        (tmp_path / name).write_bytes(b"synthetic-path-only-fixture")
    flags = [] if fidelity is None else ["--input-fidelity", fidelity]
    run("edit", "--image", "target.png", "--image", "reference.png", "--mask", "mask.png",
        "--prompt", "change background only", "--out-dir", "previews", "--dry-run", *flags)
    preview = json.loads(capsys.readouterr().out)
    assert preview["image"] == ["target.png", "reference.png"]
    assert preview["mask"] == "mask.png"
    assert preview["output_format"] == "png"
    assert preview["outputs"] == ["previews/image_1.png"]
    assert preview.get("input_fidelity") == fidelity
    if fidelity is None:
        assert "input_fidelity" not in preview
    assert not list((tmp_path / "previews").iterdir())
    module._create_client.assert_not_called()


def test_invalid_edit_fidelity_fails_before_sdk(cli, capsys, tmp_path):
    module, run = cli
    (tmp_path / "target.png").write_bytes(b"fixture")
    with pytest.raises(SystemExit) as error:
        run("edit", "--image", "target.png", "--prompt", "fixture",
            "--input-fidelity", "ultra", "--dry-run")
    assert error.value.code == 1
    assert "input-fidelity must be one of low or high" in capsys.readouterr().err
    module._create_client.assert_not_called()


@pytest.mark.parametrize("model", ["gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini"])
def test_model_family_preview_preserves_explicit_choice(cli, capsys, model):
    _, run = cli
    run("generate", "--prompt", "fixture", "--model", model, "--dry-run")
    preview = json.loads(capsys.readouterr().out)
    assert preview["model"] == model
    assert preview["outputs"] == ["output.png"]  # Existing local default remains stable.
    assert preview["output_format"] == "png"


def test_non_image_model_rejected_before_sdk(cli, capsys):
    module, run = cli
    with pytest.raises(SystemExit) as error:
        run("generate", "--prompt", "fixture", "--model", "text-model", "--dry-run")
    assert error.value.code == 1
    assert "model must be a GPT Image model" in capsys.readouterr().err
    module._create_client.assert_not_called()


def test_batch_preview_applies_per_job_format_and_model(cli, tmp_path, capsys):
    module, run = cli
    jobs = tmp_path / "jobs.jsonl"
    jobs.write_text(json.dumps({"prompt": "one", "out": "one.png"}) + "\n"
                    + json.dumps({"prompt": "two", "model": "gpt-image-1-mini",
                                  "output_format": "jpg", "out": "two.jpeg", "n": 2}) + "\n")
    run("generate-batch", "--input", str(jobs), "--out-dir", "batch", "--dry-run")
    previews = read_previews(capsys.readouterr().out)
    assert [p["output_format"] for p in previews] == ["png", "jpeg"]
    assert previews[1]["model"] == "gpt-image-1-mini"
    assert previews[0]["outputs"] == ["batch/one.png"]
    assert previews[1]["outputs"] == ["batch/two-1.jpeg", "batch/two-2.jpeg"]
    module._create_async_client.assert_not_called()
    assert not list((tmp_path / "batch").iterdir())


def test_batch_rejects_non_image_model_override(cli, tmp_path, capsys):
    module, run = cli
    jobs = tmp_path / "jobs.jsonl"
    jobs.write_text(json.dumps({"prompt": "fixture", "model": "text-model"}) + "\n")
    with pytest.raises(SystemExit) as error:
        run("generate-batch", "--input", str(jobs), "--out-dir", "batch", "--dry-run")
    assert error.value.code == 1
    assert "model must be a GPT Image model" in capsys.readouterr().err
    module._create_async_client.assert_not_called()


@pytest.mark.parametrize("command", ["generate", "edit", "generate-batch"])
@pytest.mark.parametrize("format_arg,expected", [(None, "png"), ("jpg", "jpeg")])
def test_normalized_format_reaches_mock_sdk(cli, monkeypatch, tmp_path, command, format_arg, expected):
    module, run = cli
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    seen = []

    def respond(**payload):
        seen.append(payload)
        return SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(b"fixture").decode())])

    async def respond_async(**payload):
        return respond(**payload)

    monkeypatch.setattr(module, "_create_client", lambda: SimpleNamespace(
        images=SimpleNamespace(generate=respond, edit=respond)))
    monkeypatch.setattr(module, "_create_async_client", lambda: SimpleNamespace(
        images=SimpleNamespace(generate=respond_async)))
    write = Mock()
    monkeypatch.setattr(module, "_decode_write_and_downscale", write)
    flags = [] if format_arg is None else ["--output-format", format_arg]
    if command == "generate-batch":
        jobs = tmp_path / "jobs.jsonl"
        job = {"prompt": "fixture"}
        if format_arg:
            job["output_format"] = format_arg
        jobs.write_text(json.dumps(job) + "\n")
        run(command, "--input", str(jobs), "--out-dir", "batch")
    elif command == "edit":
        (tmp_path / "target.png").write_bytes(b"fixture")
        run(command, "--prompt", "fixture", "--image", "target.png", *flags)
    else:
        run(command, "--prompt", "fixture", *flags)
    assert len(seen) == 1 and seen[0]["output_format"] == expected
    assert write.call_args.kwargs["output_format"] == expected
    assert "outputs" not in seen[0] and "outputs_downscaled" not in seen[0]
