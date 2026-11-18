from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "sync_all_upstream_skills.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "sync_all_upstream_skills",
        SCRIPT_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_check_uses_only_governed_v2_sync_entrypoint():
    module = load_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        with mock.patch.object(module, "run", return_value=0) as run:
            assert module.main(["--repo-root", tmpdir]) == 0

    commands = [call.args[0] for call in run.call_args_list]
    assert commands == [
        (module.PYTHON, "scripts/check_browser_foundations.py"),
        (module.PYTHON, "scripts/sync_upstream.py", "--check-only"),
    ]


def test_apply_pipeline_uses_full_pytest_and_no_legacy_importers():
    module = load_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        with mock.patch.object(module, "run", return_value=0) as run:
            assert (
                module.main(
                    [
                        "--repo-root",
                        tmpdir,
                        "--apply",
                        "--run-pipeline",
                    ]
                )
                == 0
            )

    commands = [call.args[0] for call in run.call_args_list]
    assert commands[0] == (module.PYTHON, "scripts/check_browser_foundations.py")
    assert commands[1] == (module.PYTHON, "scripts/sync_upstream.py", "--apply")
    assert commands[2:] == [(module.PYTHON, "scripts/validate_repository.py", "--refresh")]
    flattened = "\n".join(" ".join(command) for command in commands)
    assert "sync_addyosmani_agent_skills.py" not in flattened
    assert "sync_simota_agent_skills.py" not in flattened
    assert "sync_codex_skills.py" not in flattened


def test_apply_preserves_degraded_state_and_runs_pipeline_after_writes():
    module = load_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        with (
            mock.patch.object(
                module,
                "repository_digest",
                side_effect=["before", "after"],
            ),
            mock.patch.object(
                module,
                "run",
                side_effect=[0, 2] + [0] * len(module.POST_SYNC_PIPELINE),
            ) as run,
        ):
            assert (
                module.main(
                    [
                        "--repo-root",
                        tmpdir,
                        "--apply",
                        "--run-pipeline",
                    ]
                )
                == 2
            )
    assert len(run.call_args_list) == 2 + len(module.POST_SYNC_PIPELINE)


def test_apply_preserves_failed_state_without_install_or_unwritten_pipeline():
    module = load_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        with (
            mock.patch.object(
                module,
                "repository_digest",
                side_effect=["same", "same"],
            ),
            mock.patch.object(module, "run", return_value=1) as run,
        ):
            assert (
                module.main(
                    [
                        "--repo-root",
                        tmpdir,
                        "--apply",
                        "--run-pipeline",
                    ]
                )
                == 1
            )
    assert len(run.call_args_list) == 1
