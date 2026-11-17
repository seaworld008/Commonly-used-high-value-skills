"""Offline CLI regressions using temporary files, real SQLite and a search executable stub."""

from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess

import pytest


SKILL = Path(__file__).resolve().parents[1] / "skills/growth-operations-xiaohongshu/linkedin-growth"
PEOPLE = [{"hashedUrl": "one", "name": "First"}, {"hashedUrl": "two", "name": "Second"}]
DECISIONS = [
    {"hashed_url": "one", "suitable": True, "reasoning": "Matches the ICP role"},
    {"hashed_url": "two", "suitable": False, "reasoning": "Excluded role"},
]

# Fallback when the native dependency is absent. SQLite executes every production
# statement and constraint, with a real read-only connection and transaction rollback.
SQLITE_ADAPTER = """
import { DatabaseSync } from 'node:sqlite';
export default class Database extends DatabaseSync {
  constructor(path, {readonly = false} = {}) { super(path, {readOnly: readonly}); }
  pragma(statement) { return this.prepare('PRAGMA ' + statement).all(); }
  transaction(fn) {
    return (...args) => {
      this.exec('BEGIN');
      try {
        const result = fn(...args);
        this.exec('COMMIT');
        return result;
      } catch (err) {
        this.exec('ROLLBACK');
        throw err;
      }
    };
  }
}
"""


class ImportCLI:
    def __init__(self, root):
        self.skill = root / "skill"
        for folder in ("scripts", "config"):
            shutil.copytree(SKILL / folder, self.skill / folder)
        package = self.skill / "node_modules/better-sqlite3"
        package.parent.mkdir()
        installed = subprocess.run(
            ["node", "-p", "require.resolve('better-sqlite3/package.json')"],
            cwd=SKILL, capture_output=True, text=True,
        )
        if installed.returncode == 0:
            package.symlink_to(Path(installed.stdout.strip()).parent, target_is_directory=True)
        else:
            package.mkdir()
            (package / "package.json").write_text('{"type":"module","exports":"./driver.mjs"}')
            (package / "driver.mjs").write_text(SQLITE_ADAPTER)

        binary = root / "bin"
        binary.mkdir()
        fake = binary / "linkedin"
        fake.write_text(
            '#!/bin/sh\ncase "$1 $2" in "navigator person"|"workflow run") ;; *) exit 91 ;; esac\n'
            'cat >/dev/null\ncat "$SEARCH_RECEIPT"\n'
        )
        fake.chmod(0o755)
        self.data = root / "data"
        self.path = self.data / "db.sqlite"
        self.receipt = root / "receipt.json"
        self.env = {
            "HOME": str(root), "TMPDIR": str(root), "PATH": f"{binary}{os.pathsep}{os.environ['PATH']}",
            "LEADS_DATA_DIR": str(self.data), "LEADS_DB_PATH": str(self.path),
            "SEARCH_RECEIPT": str(self.receipt),
        }

    def run(self, script, *args, success=True):
        proc = subprocess.run(
            ["node", f"scripts/{script}.mjs", *args, "--json"], cwd=self.skill, env=self.env,
            capture_output=True, text=True, timeout=15,
        )
        assert (proc.returncode == 0) == success, (proc.stdout, proc.stderr)
        body = json.loads(proc.stdout)
        assert body["success"] is success, body
        return body["data"] if success else body["error"]["message"]

    def initialize(self):
        self.run("db", "init")
        with closing(sqlite3.connect(self.path)) as db, db:
            db.executemany("INSERT INTO accounts(name, cli_account) VALUES(?, ?)",
                           [("sender-a", "fake-a"), ("sender-b", "fake-b")])
            db.execute("UPDATE import_state SET last_assigned_account = 'sender-b'")

    def prepare(self, data=PEOPLE, *, url=False, success=True, outer=True):
        self.receipt.write_text(json.dumps({"success": outer, "data": data}))
        route = ["--search-url", "https://fixture.invalid/search"] if url else ["--term", "role"]
        return self.run("import", "prepare", "--searcher", "sender-a", "--list", "test",
                        "--limit", "2", *route, success=success)

    def commit(self, batch, decisions, *, success=True):
        results = Path(batch["expected_result_file"])
        results.write_text(json.dumps(decisions))
        return self.run("import", "commit", "--batch", batch["batch_id"], "--results", str(results),
                        success=success)

    def snapshot(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            return tuple(db.iterdump())


@pytest.fixture
def cli(tmp_path):
    return ImportCLI(tmp_path)


@pytest.mark.parametrize(("decisions", "message"), [
    ([DECISIONS[0], {**DECISIONS[1], "suitable": "false"}], "boolean"),
    ([DECISIONS[0], {**DECISIONS[1], "suitable": 0}], "boolean"),
    ([DECISIONS[0], {"hashed_url": "two"}], "boolean"),
    (DECISIONS[:1], "missing"),
    ([DECISIONS[0], DECISIONS[0]], "duplicate"),
    ([DECISIONS[0], {**DECISIONS[1], "hashed_url": "other"}], "unknown"),
    ([DECISIONS[0], {}], "hashed_url"),
])
def test_invalid_qualification_preserves_batch_and_can_retry(cli, decisions, message):
    cli.initialize()
    batch = cli.prepare()
    before = cli.snapshot()
    assert message in cli.commit(batch, decisions, success=False).lower()
    assert cli.snapshot() == before
    stats = cli.commit(batch, list(reversed(DECISIONS)))
    assert (stats["suitable"], stats["unsuitable"], stats["assigned"]) == (1, 1, 1)
    with closing(sqlite3.connect(cli.path)) as db, db:
        assert db.execute("SELECT hashed_url, owner_account, status FROM leads").fetchall() == [
            ("one", "sender-a", "not_connected")]
        assert db.execute("SELECT state, committed_count FROM import_batches").fetchone() == ("committed", 1)
    committed = cli.snapshot()
    assert "committed" in cli.commit(batch, DECISIONS, success=False)
    assert cli.snapshot() == committed


@pytest.mark.parametrize("damage", ["truncate", "duplicate", "missing-id"])
def test_damaged_candidate_file_cannot_close_batch(cli, damage):
    cli.initialize()
    batch = cli.prepare()
    path = Path(batch["candidate_file"])
    candidates = json.loads(path.read_text())
    decisions = DECISIONS
    if damage == "truncate":
        candidates.pop()
        decisions = DECISIONS[:1]
    elif damage == "duplicate":
        candidates[1]["hashed_url"] = "one"
    else:
        del candidates[1]["hashed_url"]
    path.write_text(json.dumps(candidates))
    before = cli.snapshot()
    cli.commit(batch, decisions, success=False)
    assert cli.snapshot() == before


@pytest.mark.parametrize("name", [None, "  "])
def test_selected_candidate_needs_name_but_excluded_candidate_can_be_incomplete(cli, name):
    cli.initialize()
    batch = cli.prepare([PEOPLE[0], {"hashedUrl": "two", "name": name}])
    before = cli.snapshot()
    error = cli.commit(batch, [DECISIONS[0], {**DECISIONS[1], "suitable": True}], success=False)
    assert "two" in error and "full_name" in error
    assert cli.snapshot() == before
    assert cli.commit(batch, DECISIONS)["assigned"] == 1


def test_duplicate_from_another_import_preserves_existing_lead(cli):
    cli.initialize()
    batch = cli.prepare()
    with closing(sqlite3.connect(cli.path)) as db, db:
        db.execute("INSERT INTO leads(hashed_url,full_name,owner_account,status) VALUES "
                   "('one','Earlier name','sender-b','connected')")
    stats = cli.commit(batch, [DECISIONS[0], {**DECISIONS[1], "suitable": True}])
    assert (stats["assigned"], stats["skippedExisting"]) == (1, 1)
    with closing(sqlite3.connect(cli.path)) as db, db:
        assert db.execute("SELECT full_name, owner_account, status FROM leads ORDER BY hashed_url").fetchall() == [
            ("Earlier name", "sender-b", "connected"), ("Second", "sender-a", "not_connected")]


@pytest.mark.parametrize(("raise_args", "error_text"), [
    ("ABORT, 'fixture constraint failure'", "fixture constraint failure"),
    ("IGNORE", "Could not insert selected candidate 'two'"),
])
def test_unexpected_insert_failure_rolls_back_every_row(cli, raise_args, error_text):
    cli.initialize()
    batch = cli.prepare()
    with closing(sqlite3.connect(cli.path)) as db, db:
        db.execute(f"""CREATE TRIGGER fixture BEFORE INSERT ON leads WHEN NEW.hashed_url = 'two'
                       BEGIN SELECT RAISE({raise_args}); END""")
    before = cli.snapshot()
    error = cli.commit(batch, [{**r, "suitable": True} for r in DECISIONS], success=False)
    assert error_text in error
    assert cli.snapshot() == before


@pytest.mark.parametrize(("outer", "data", "url"), [
    (False, PEOPLE, False),
    ("false", PEOPLE, False),
    (True, {"actionType": "nv.searchPeople", "success": False}, True),
    (True, {"actionType": "nv.searchPeople", "success": False, "data": []}, True),
    (True, {"success": True, "data": {}}, True),
    (True, {"data": []}, True),
    (True, {"actionType": "other", "success": True, "data": []}, True),
    (True, [PEOPLE[0], PEOPLE[0]], False),
    (True, [{"name": "No identifier"}], False),
    (True, {}, False),
])
def test_failed_or_unknown_search_does_not_persist_batch(cli, outer, data, url):
    cli.initialize()
    before = cli.snapshot()
    cli.prepare(data, outer=outer, url=url, success=False)
    assert cli.snapshot() == before
    assert not list(cli.data.rglob("qualify-*.json"))


@pytest.mark.parametrize("url", [False, True])
def test_successful_empty_search_is_recorded(cli, url):
    cli.initialize()
    data = {"actionType": "nv.searchPeople", "success": True, "data": []} if url else []
    batch = cli.prepare(data, url=url)
    assert batch["found_total"] == batch["candidates_to_qualify"] == 0
    assert json.loads(Path(batch["candidate_file"]).read_text()) == []
    assert cli.run("import", "show", "--batch", batch["batch_id"])["state"] == "pending_qualification"


@pytest.mark.parametrize(("script", "args"), [("import", ["list"]), ("query", ["--sql", "SELECT 1"])])
def test_readonly_missing_store_does_not_create_directories(cli, script, args):
    cli.run(script, *args, success=False)
    assert not cli.data.exists()


@pytest.mark.parametrize(("script", "args"), [("import", ["list"]), ("query", ["--sql", "SELECT 1"])])
@pytest.mark.parametrize("versioned", [True, False])
def test_readonly_old_store_requires_writer_and_preserves_data(cli, script, args, versioned):
    cli.initialize()
    with closing(sqlite3.connect(cli.path)) as db, db:
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("DROP TABLE settings")
        if versioned:
            db.execute("DELETE FROM schema_version WHERE version=3")
        else:
            db.execute("DROP TABLE schema_version")
    before = cli.path.read_bytes()
    assert "migrat" in cli.run(script, *args, success=False).lower()
    assert cli.path.read_bytes() == before
    assert list(cli.data.iterdir()) == [cli.path]
    assert cli.run("db", "migrate")["schema_version"] == 3
    assert cli.run("import", "list") == []
    assert cli.run("query", "--sql", "SELECT name FROM accounts ORDER BY name") == [
        {"name": "sender-a"}, {"name": "sender-b"}]


def test_icp_prompt_uses_session_scope_and_prepare_preserves_global_setting(cli):
    cli.initialize()
    with closing(sqlite3.connect(cli.path)) as db, db:
        db.execute("INSERT INTO settings VALUES ('icp_definition', 'Saved ICP')")
    batch = cli.prepare()
    assert batch["icp_definition"] == "Saved ICP"
    prompt = " ".join(Path(batch["qualification_prompt"]).read_text().lower().split())
    assert "session" in prompt
    assert "only when saving settings is in scope" in prompt
    assert cli.run("query", "--sql", "SELECT value FROM settings WHERE key='icp_definition'") == [
        {"value": "Saved ICP"}]
