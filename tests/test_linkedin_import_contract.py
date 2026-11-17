"""Offline CLI regressions: real import/invite code, fixture SQL DB and LinkedIn stub.

No accounts, scheduler, model or network service are used. The DB adapter executes
the production SQL against a temporary SQLite DB; transaction rollback is outside
this test's scope. Command prose assertions supplement, not replace, CLI behavior.
"""

import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys

import pytest


SKILL = Path(__file__).resolve().parents[1] / "skills/growth-operations-xiaohongshu/linkedin-growth"

DB_MOCK = r"""
import { spawnSync } from 'node:child_process';
const bridge = `
import json, os, sqlite3, sys
request = json.load(sys.stdin)
with sqlite3.connect(os.environ['LEADS_DB_PATH']) as db:
    db.row_factory = sqlite3.Row
    cursor = db.execute(request['sql'], request['args'])
    if request['mode'] == 'run':
        result = {'changes': cursor.rowcount, 'lastInsertRowid': cursor.lastrowid}
    elif request['mode'] == 'all':
        result = [dict(row) for row in cursor.fetchall()]
    else:
        row = cursor.fetchone()
        result = dict(row) if row is not None else None
print(json.dumps(result))
`;
function query(sql, args, mode) {
  const result = spawnSync(process.env.PYTHON_TEST_EXEC, ['-c', bridge], {
    input: JSON.stringify({sql, args, mode}), encoding: 'utf8',
  });
  if (result.status !== 0) throw new Error(result.stderr);
  return JSON.parse(result.stdout);
}
const db = {
  prepare: sql => Object.fromEntries(['get', 'all', 'run'].map(mode =>
    [mode, (...args) => query(sql, args, mode)])),
  // Each fixture query commits synchronously; only successful transactions are tested.
  transaction: fn => fn,
};
export function withDb(fn) { return fn(db); }
"""

CLI_MOCK = r"""
import { appendFileSync, readFileSync } from 'node:fs';
export async function runLinkedin(args, options) {
  const action = options.input ? JSON.parse(options.input) : null;
  const call = {args, ...options, action};
  appendFileSync(process.env.MOCK_CLI_LOG, JSON.stringify(call) + '\n');
  const fixture = JSON.parse(readFileSync(process.env.MOCK_SEARCH, 'utf8'));
  const isSearch = ['nv.searchPeople', 'st.searchPeople'].includes(action?.actionType);
  if (isSearch || args.join(' ') === 'navigator person search --term fixture --limit 2' ||
      args.join(' ') === 'person search --term fixture --limit 2') {
    const data = isSearch ? {actionType: action.actionType, success: true, data: fixture} : fixture;
    return {ok: true, exitCode: 0, json: {success: true, data}};
  }
  if (action?.actionType === 'st.openPersonPage' &&
      action.then?.actionType === 'st.sendConnectionRequest') {
    return {ok: true, exitCode: 0, json: {success: true, data: {
      actionType: 'st.openPersonPage', success: true,
      data: {publicUrl: 'https://www.linkedin.com/in/fixture-keep'},
      then: {actionType: 'st.sendConnectionRequest', success: true},
    }}};
  }
  throw new Error('Unexpected mock CLI call: ' + JSON.stringify(call));
}
"""


class ImportFixture:
    def __init__(self, root):
        self.root = root
        self.skill = root / "skill"
        lib = self.skill / "scripts/lib"
        lib.mkdir(parents=True)
        for name in ("import.mjs", "network-invite.mjs"):
            shutil.copyfile(SKILL / "scripts" / name, lib.parent / name)
        for name in ("args", "output", "paths", "config", "settings", "account", "runs", "time"):
            shutil.copyfile(SKILL / f"scripts/lib/{name}.mjs", lib / f"{name}.mjs")
        shutil.copytree(SKILL / "config", self.skill / "config")
        (lib / "db.mjs").write_text(DB_MOCK)
        (lib / "cli.mjs").write_text(CLI_MOCK)
        self.db_path = root / "fixture.sqlite"
        self.log_path = root / "cli.jsonl"
        self.search_path = root / "search.json"
        self.env = {
            "PATH": os.environ["PATH"], "HOME": str(root), "TMPDIR": str(root),
            "LEADS_DATA_DIR": str(root / "data"), "LEADS_DB_PATH": str(self.db_path),
            "PYTHON_TEST_EXEC": sys.executable, "MOCK_CLI_LOG": str(self.log_path),
            "MOCK_SEARCH": str(self.search_path),
        }
        # Use shipped migration SQL, not a second implementation of the DB schema.
        source = (SKILL / "scripts/lib/db.mjs").read_text()
        migrations = re.findall(r"`(\n  CREATE TABLE IF NOT EXISTS.*?)`", source, re.S)
        assert len(migrations) == 2
        with sqlite3.connect(self.db_path) as db:
            for sql in migrations:
                db.executescript(sql)
            db.executemany(
                "INSERT INTO accounts (name, cli_account, paused, daily_invite_limit) VALUES (?, ?, ?, ?)",
                [("sender-a", "fake-a", 0, 5), ("sender-b", "fake-b", 0, 10),
                 ("paused", "fake-paused", 1, 10)],
            )

    def run(self, script, *args, success=True):
        result = subprocess.run(
            ["node", f"scripts/{script}.mjs", *args, "--json"], cwd=self.skill,
            env=self.env, capture_output=True, text=True, timeout=30,
        )
        payload = json.loads(result.stdout)
        assert payload["success"] is success, (result.stdout, result.stderr)
        assert (result.returncode == 0) is success, (result.stdout, result.stderr)
        return payload["data"] if success else payload["error"]

    def sql(self, sql, args=()):
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute(sql, args)]

    def calls(self):
        if not self.log_path.exists():
            return []
        return [json.loads(line) for line in self.log_path.read_text().splitlines()]

    def invites(self):
        return [call for call in self.calls()
                if (call.get("action") or {}).get("then", {}).get("actionType")
                == "st.sendConnectionRequest"]

    def prepare(self, icp, route, search_type, empty=False):
        if icp:
            self.sql("INSERT INTO settings VALUES ('icp_definition', ?)", ("Keep sales leaders",))
        candidates = [] if empty else [
            {"hashedUrl": "fixture-keep", "publicUrl": "https://www.linkedin.com/in/fixture-keep",
             "name": "Fixture Keep", "position": "Head of Sales"},
            {"hashedUrl": "fixture-filter", "publicUrl": "https://www.linkedin.com/in/fixture-filter",
             "name": "Fixture Filter", "position": "Student"},
        ]
        self.search_path.write_text(json.dumps(candidates))
        search_args = ["--term", "fixture"] if route == "native" else [
            "--search-url", "https://www.linkedin.com/sales/search/people?fixture=1"]
        return self.run("import", "prepare", "--searcher", "sender-a", "--list", "fixture",
                        "--limit", "2", "--type", search_type, *search_args)

    def qualify(self, prepared):
        candidates = json.loads(Path(prepared["candidate_file"]).read_text())
        results = [{"hashed_url": candidate["hashed_url"],
                    "suitable": candidate["full_name"] == "Fixture Keep",
                    "reasoning": "Matches sales role" if candidate["full_name"] == "Fixture Keep"
                    else "Student exclusion"} for candidate in candidates]
        Path(prepared["expected_result_file"]).write_text(json.dumps(results))
        return results

    def consume(self):
        # Real invite main(), never schedule.mjs or real CLI/account connections.
        return [self.run("network-invite", "--account", name, "--delay-seconds", "0")
                for name in ("sender-a", "sender-b", "paused")]


@pytest.fixture
def importer(tmp_path):
    if not shutil.which("node"):
        pytest.skip("Node is required for real CLI behavior tests")
    return ImportFixture(tmp_path)


def assert_guidance_contract(prepared):
    policy = prepared["commit_policy"]
    for text in policy.values():
        assert text in prepared["next_step"]
    assert "existing session authorization" in policy["condition"]
    assert "this batch of leads" in policy["condition"]
    assert "every active (non-paused) account" in policy["condition"]
    assert "do not require another confirmation" in policy["condition"]
    assert "status='not_connected'" in policy["side_effect"]
    assert "scheduler may send immediately" in policy["side_effect"]
    assert "return the qualification results" in policy["research_only"]
    assert "do not commit" in policy["research_only"]


@pytest.mark.parametrize("icp", [False, True])
@pytest.mark.parametrize(("route", "search_type"), [("native", "nv"), ("url", "st")])
def test_research_prepare_and_qualification_never_enqueue_or_invite(importer, icp, route, search_type):
    prepared = importer.prepare(icp, route, search_type)
    assert_guidance_contract(prepared)
    assert prepared["icp_configured"] is icp
    assert prepared["candidates_to_qualify"] == 2
    assert len(importer.qualify(prepared)) == 2
    assert importer.sql("SELECT * FROM leads") == []
    assert importer.sql("SELECT state FROM import_batches") == [{"state": "pending_qualification"}]
    summaries = importer.consume()
    assert [result.get("processed", 0) for result in summaries] == [0, 0, 0]
    assert importer.invites() == []
    assert len(importer.calls()) == 1  # Search only, no invitation action.


@pytest.mark.parametrize(("icp", "route", "search_type"), [(False, "native", "nv"), (True, "url", "st")])
def test_authorized_commit_instruction_enqueues_and_real_invite_can_consume(importer, icp, route, search_type):
    prepared = importer.prepare(icp, route, search_type)
    assert_guidance_contract(prepared)
    qualified = importer.qualify(prepared)
    assert importer.invites() == []
    # Simulate the agent following the returned command with existing scoped authorization.
    # No confirmation flag or authorization record is added to the established CLI/DB contract.
    command = prepared["next_step"].split("If that condition is met, run: ", 1)[1]
    argv = shlex.split(command)
    assert argv[:3] == ["node", "scripts/import.mjs", "commit"]
    committed = importer.run("import", *argv[2:])
    assert (committed["suitable"], committed["unsuitable"], committed["assigned"]) == (1, 1, 1)
    assert importer.sql("SELECT hashed_url, owner_account, status FROM leads") == [
        {"hashed_url": qualified[0]["hashed_url"], "owner_account": "sender-a", "status": "not_connected"}]
    assert importer.sql("SELECT state FROM import_batches") == [{"state": "committed"}]
    assert importer.invites() == []  # Consumption is an independent operation.
    summaries = importer.consume()
    assert summaries[0]["pending"] == 1
    assert summaries[1]["processed"] == 0
    assert summaries[2]["skipped"] == "paused"
    assert len(importer.invites()) == 1
    assert importer.invites()[0]["cliAccount"] == "fake-a"
    assert importer.invites()[0]["action"]["personUrl"] == qualified[0]["hashed_url"]
    assert importer.sql("SELECT status FROM leads") == [{"status": "pending"}]
    assert importer.sql("SELECT account, success FROM runs") == [{"account": "sender-a", "success": 1}]


@pytest.mark.parametrize("existing", [False, True])
def test_empty_or_duplicate_only_prepare_does_not_offer_commit(importer, existing):
    if existing:
        importer.sql("INSERT INTO leads (hashed_url, full_name, owner_account, status) VALUES (?, ?, ?, ?)",
                     ("fixture-keep", "Old lead", "paused", "connected"))
        importer.sql("INSERT INTO leads (hashed_url, full_name, owner_account, status) VALUES (?, ?, ?, ?)",
                     ("fixture-filter", "Old filtered lead", "paused", "connected"))
    prepared = importer.prepare(True, "native", "nv", empty=not existing)
    assert_guidance_contract(prepared)
    assert prepared["candidates_to_qualify"] == 0
    assert prepared["skipped_existing"] == (2 if existing else 0)
    assert "node scripts/import.mjs commit" not in prepared["next_step"]
    importer.consume()
    assert importer.invites() == []


def test_import_and_setup_command_entries_agree_with_returned_contract(importer):
    prepared = importer.prepare(True, "native", "nv")
    assert_guidance_contract(prepared)
    command = (SKILL / "commands/linkedin-growth-import.md").read_text()
    match = re.search(r"`(node scripts/import\.mjs commit --batch <id> --results <file>)`", command)
    assert match is not None
    documented = match[1].replace("<id>", prepared["batch_id"]).replace(
        "<file>", prepared["expected_result_file"])
    assert prepared["next_step"].endswith(documented)
    for path in ("commands/linkedin-growth-import.md", "commands/linkedin-growth-setup.md", "EXTENDED.md"):
        prose = " ".join((SKILL / path).read_text().split())
        assert "existing session authorization specifically covers" in prose
        assert "batch" in prose and "(non-paused)" in prose and "eligible for assignment" in prose
        assert "do not require another confirmation" in prose
        assert "qualification results" in prose and "send queue" in prose
        assert "immediately" in prose
        assert "import only stores leads" not in prose
        assert "pipeline is empty until" not in prose
    assert importer.sql("SELECT * FROM leads") == []
    assert importer.invites() == []
