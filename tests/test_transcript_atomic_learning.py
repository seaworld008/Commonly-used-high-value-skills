"""Exercise the public transcript CLI with local files and a synthetic AI response."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest


SCRIPTS = (Path(__file__).resolve().parents[1] /
           "skills/office-white-collar/transcript-fixer/scripts")
CLI = SCRIPTS / "fix_transcription.py"

# Run the public CLI in a fresh interpreter. Only substitute the AI result.
# File size errors, command dispatch and all database operations are real.
LAUNCHER = """
import json, os, runpy, sys
from pathlib import Path
sys.argv = sys.argv[1:]
sys.path.insert(0, str(Path(sys.argv[0]).parent))
if "TEST_FILE_LIMIT" in os.environ:
    import resource, signal
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    limit = int(os.environ["TEST_FILE_LIMIT"])
    resource.setrlimit(resource.RLIMIT_FSIZE, (limit, limit))
if "TEST_AI_RESULT" in os.environ:
    from core.ai_processor_async import AIProcessorAsync, AIChange
    result = json.loads(os.environ["TEST_AI_RESULT"])
    def process(self, text):
        if "metadata" in result:
            self.last_run_metadata = result["metadata"]
        else:
            self.__dict__.pop("last_run_metadata", None)
        changes = [AIChange(1, before, after, 0.99) for before, after in result.get("changes", [])]
        return result.get("text", text), changes
    AIProcessorAsync.process = process
runpy.run_path(sys.argv[0], run_name="__main__")
"""


def run_cli(root, *args, ai=None, limit=None, learning=False, auto=False):
    env = {
        "PATH": os.defpath,
        "HOME": str(root),
        "TMPDIR": str(root),
        "GLM_API_KEY": "synthetic-test-key",
        "TRANSCRIPT_FIXER_CONFIG_DIR": str(root / "store"),
        "TRANSCRIPT_FIXER_OUTPUT_MANIFEST": str(root / "receipt.json"),
        "TRANSCRIPT_FIXER_ENABLE_LEARNING": str(int(learning)),
        "TRANSCRIPT_FIXER_AUTO_APPROVE": str(int(auto)),
    }
    if ai is not None:
        env["TEST_AI_RESULT"] = json.dumps(ai)
    if limit is not None:
        if os.name != "posix":
            pytest.skip("uses RLIMIT_FSIZE")
        env["TEST_FILE_LIMIT"] = str(limit)
    return subprocess.run([sys.executable, "-B", "-c", LAUNCHER, str(CLI), *map(str, args)],
                          cwd=root, env=env, capture_output=True, text=True, timeout=30)


def outputs(root):
    return json.loads((root / "receipt.json").read_text())["outputs"]


@pytest.mark.parametrize("stage", [1, 2])
def test_disk_failure_preserves_previous_delivery_and_receipts(tmp_path, stage):
    source = tmp_path / "source.md"
    large = "abcdef0123456789\n" * 100
    original = large if stage == 1 else "short input"
    source.write_text(original)
    dest = tmp_path / "out"
    dest.mkdir()
    first, second = [dest / f"source_stage{i}.md" for i in (1, 2)]
    first.write_bytes(b"first old")
    second.write_bytes(b"second old")
    args = ["--input", source, "--output", dest, "--stage", stage]
    limit = 128 if stage == 1 else 1024
    failed = run_cli(tmp_path, *args, ai={"text": large}, limit=limit)
    assert failed.returncode != 0
    assert "File too large" in failed.stderr + failed.stdout
    assert source.read_text() == original
    assert second.read_bytes() == b"second old"
    assert first.read_bytes() == (b"first old" if stage == 1 else original.encode())
    assert outputs(tmp_path) == ([] if stage == 1 else [str(first)])
    assert set(dest.iterdir()) == {first, second}

    success = run_cli(tmp_path, *args, ai={"text": large})
    assert success.returncode == 0, success.stderr
    assert source.read_text() == first.read_text() == original
    assert second.read_bytes() == (b"second old" if stage == 1 else large.encode())
    assert outputs(tmp_path) == [str(p) for p in (first, second)[:stage]]
    assert set(dest.iterdir()) == {first, second}
    assert not (tmp_path / "store").exists()


def test_failed_replace_cleans_own_staging_file(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("original")
    dest = tmp_path / "out"
    blocked = dest / "source_stage1.md"
    blocked.mkdir(parents=True)
    sentinel = blocked / "keep"
    sentinel.write_bytes(b"previous data")
    result = run_cli(tmp_path, "--input", source, "--output", dest, "--stage", 1)
    assert result.returncode != 0
    assert "Text output not saved" in result.stdout
    assert outputs(tmp_path) == []
    assert source.read_text() == "original" and sentinel.read_bytes() == b"previous data"
    assert set(dest.iterdir()) == {blocked}


def test_failed_receipt_update_keeps_prior_stage_list(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("short")
    first, second = [tmp_path / f"source_stage{i}.md" for i in (1, 2)]
    limit = len(json.dumps({"outputs": [str(first)]}).encode())
    result = run_cli(tmp_path, "--input", source, "--stage", 2, ai={"text": "finished"}, limit=limit)
    assert result.returncode != 0
    assert outputs(tmp_path) == [str(first)]
    assert first.read_text() == source.read_text() == "short"
    assert second.read_text() == "finished"
    assert "Output receipt not updated" in result.stdout
    assert f"Text output saved: {second}" in result.stdout


@pytest.mark.parametrize("metadata,model,chunks", [
    ({"models_used": ["GLM-4.5-Air"], "chunks_processed": 1}, "GLM-4.5-Air", "1"),
    ({"models_used": ["primary", "fallback"], "chunks_processed": 3}, "primary, fallback", "3"),
    (None, "unknown", "unknown"),
    ({"models_used": [], "chunks_processed": 0}, "unknown", "0"),
])
def test_actual_models_and_chunks_with_no_edits(tmp_path, metadata, model, chunks):
    source = tmp_path / "source.md"
    source.write_text("already correct")
    ai = {"metadata": metadata} if metadata is not None else {}
    result = run_cli(tmp_path, "--input", source, "--stage", 2, ai=ai, learning=True)
    assert result.returncode == 0, result.stderr
    with sqlite3.connect(tmp_path / "store/corrections.db") as conn:
        assert conn.execute("SELECT model, stage2_changes FROM correction_history").fetchall() == [(model, 0)]
    assert f"Processed {chunks} chunk" in result.stdout
    assert (tmp_path / "source_stage2.md").read_text() == source.read_text()


@pytest.mark.parametrize("failure", [None, "insert", "log"])
def test_learning_result_matches_durable_text_history_and_dictionary(tmp_path, failure):
    seeded = run_cli(tmp_path, "--add", "old", "prior")
    assert seeded.returncode == 0, seeded.stderr
    db = tmp_path / "store/corrections.db"
    log = tmp_path / "store/learned/auto_approved.json"
    log.parent.mkdir()
    limit = 1024 * 1024 if failure == "log" else None
    previous = {"auto_approved": [{"from": "prior", "to": "p" * ((limit or 100) - 50)}]}
    log.write_text(json.dumps(previous))
    previous_bytes = log.read_bytes()
    if failure == "insert":
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TRIGGER reject_insert BEFORE INSERT ON corrections "
                         "BEGIN SELECT RAISE(ABORT, 'synthetic insert failure'); END")

    source = tmp_path / "source.md"
    source.write_text("wrong " * 6)
    ai = {"text": "right " * 6, "changes": [["wrong", "right"]] * 6,
          "metadata": {"models_used": ["test-model"], "chunks_processed": 1}}
    result = run_cli(tmp_path, "--input", source, "--stage", 2, ai=ai,
                     learning=True, auto=True, limit=limit)

    assert outputs(tmp_path) == [str(tmp_path / f"source_stage{i}.md") for i in (1, 2)]
    assert source.read_text() == (tmp_path / "source_stage1.md").read_text() == "wrong " * 6
    assert (tmp_path / "source_stage2.md").read_text() == ai["text"]
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT model, stage2_changes FROM correction_history").fetchall() == [("test-model", 6)]
        assert conn.execute("SELECT COUNT(*) FROM correction_changes WHERE rule_type='ai'").fetchone() == (6,)
        dictionary = dict(conn.execute("SELECT from_text, to_text FROM corrections"))
    expected = {"old": "prior"}
    if failure != "insert":
        expected["wrong"] = "right"
    assert dictionary == expected
    if failure:
        assert result.returncode != 0
        assert log.read_bytes() == previous_bytes
        assert "Learning failed" in result.stdout
        assert "Text output saved" in result.stdout and "History saved" in result.stdout
        assert "Correction complete!" not in result.stdout
    else:
        assert result.returncode == 0, result.stderr
        assert "Correction complete!" in result.stdout
        approved = json.loads(log.read_text())["auto_approved"]
        assert approved[:-1] == previous["auto_approved"]
        assert (approved[-1]["from"], approved[-1]["to"]) == ("wrong", "right")
    assert {p.name for p in log.parent.iterdir()} <= {log.name, ".auto_approved.lock"}


def test_later_insert_failure_records_only_committed_patterns(tmp_path):
    seeded = run_cli(tmp_path, "--add", "old", "prior")
    assert seeded.returncode == 0, seeded.stderr
    db = tmp_path / "store/corrections.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TRIGGER reject_second BEFORE INSERT ON corrections "
                     "WHEN NEW.from_text = 'two' BEGIN SELECT RAISE(ABORT, 'rejected'); END")
    source = tmp_path / "source.md"
    source.write_text("one two " * 6)
    ai = {"text": "first second " * 6, "changes": [["one", "first"], ["two", "second"]] * 6}
    result = run_cli(tmp_path, "--input", source, "--stage", 2, ai=ai, learning=True, auto=True)
    assert result.returncode != 0 and "Learning failed" in result.stdout
    with sqlite3.connect(db) as conn:
        assert dict(conn.execute("SELECT from_text, to_text FROM corrections")) == {"old": "prior", "one": "first"}
        assert conn.execute("SELECT stage2_changes FROM correction_history").fetchall() == [(12,)]
    approved = json.loads((tmp_path / "store/learned/auto_approved.json").read_text())["auto_approved"]
    assert [row["from"] for row in approved] == ["one"]
