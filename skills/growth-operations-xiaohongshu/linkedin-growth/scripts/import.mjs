#!/usr/bin/env node
import { writeFileSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { randomUUID } from 'node:crypto';
import { parseArgs, requireFlag } from './lib/args.mjs';
import { withDb } from './lib/db.mjs';
import { ok, fail, info } from './lib/output.mjs';
import { runLinkedin } from './lib/cli.mjs';
import { tmpDir, ensureDir } from './lib/paths.mjs';
import { qualificationPromptPath, defaults } from './lib/config.mjs';
import { getSetting } from './lib/settings.mjs';

const { positional, flags } = parseArgs();
const cmd = positional[0];

try {
  switch (cmd) {
    case 'prepare':
      await prepare();
      break;
    case 'commit':
      commit();
      break;
    case 'list':
      list();
      break;
    case 'show':
      show();
      break;
    case 'abort':
      abort();
      break;
    default:
      fail(
        'Usage:\n' +
          '  import.mjs prepare --searcher <db-account> --list <name> --limit <N|max> [--type nv|st] [--search-url <url>] [--term ...] [filter flags...]\n' +
          '  import.mjs commit --batch <id> --results <file>\n' +
          '  import.mjs list [--state pending_qualification|committed|aborted]\n' +
          '  import.mjs show --batch <id>\n' +
          '  import.mjs abort --batch <id>',
        5,
      );
  }
} catch (err) {
  fail(err.message);
}

async function prepare() {
  const searcherName = requireFlag(flags, 'searcher');
  const listName = requireFlag(flags, 'list');
  const type = String(flags.type ?? 'nv').toLowerCase();
  if (!['nv', 'st'].includes(type)) throw new Error('--type must be nv or st');

  const searchUrl = flags['search-url'] ? String(flags['search-url']) : undefined;
  const { limit, capApplied } = resolveLimit(flags.limit, type);

  const account = withDb(
    (db) => db.prepare('SELECT * FROM accounts WHERE name = ?').get(searcherName),
  );
  if (!account) throw new Error(`Searcher account '${searcherName}' not found in DB`);

  info(`Running ${type === 'nv' ? 'Sales Navigator' : 'regular'} search via ${account.cli_account}...`);

  let cliResult;
  if (searchUrl) {
    const def = {
      actionType: type === 'nv' ? 'nv.searchPeople' : 'st.searchPeople',
      customSearchUrl: searchUrl,
    };
    if (limit) def.limit = limit;
    cliResult = await runLinkedin(['workflow', 'run'], {
      cliAccount: account.cli_account,
      input: JSON.stringify(def),
    });
  } else {
    const args = type === 'nv' ? ['navigator', 'person', 'search'] : ['person', 'search'];
    if (flags.term) args.push('--term', String(flags.term));
    if (limit) args.push('--limit', String(limit));
    for (const f of [
      'first-name',
      'last-name',
      'position',
      'locations',
      'industries',
      'current-companies',
      'previous-companies',
      'schools',
    ]) {
      if (flags[f]) args.push(`--${f}`, String(flags[f]));
    }
    if (type === 'nv' && flags['years-of-experience']) {
      args.push('--years-of-experience', String(flags['years-of-experience']));
    }
    cliResult = await runLinkedin(args, { cliAccount: account.cli_account });
  }

  if (!cliResult.ok) {
    throw new Error(
      `linkedin search failed (exit ${cliResult.exitCode}): ${cliResult.stderr || cliResult.error || 'no stderr'}`,
    );
  }
  if (!cliResult.json) throw new Error('linkedin returned non-JSON output');
  const items = extractSearchItems(cliResult.json, type);
  const normalized = indexCandidates(items.map((it) => normalizeCandidate(it, type)));

  if (normalized.size === 0) {
    info('Search returned 0 candidates.');
  }

  const batchId = randomUUID();
  const dir = ensureDir(tmpDir());
  const candidateFile = join(dir, `qualify-${batchId}.candidates.json`);
  const resultFile = join(dir, `qualify-${batchId}.results.json`);

  // Filter out candidates already present in DB to save qualification work
  const { newCandidates, alreadyExisting } = withDb(
    (db) => {
      const stmt = db.prepare('SELECT 1 FROM leads WHERE hashed_url = ?');
      const fresh = [];
      let existing = 0;
      for (const c of normalized.values()) {
        if (stmt.get(c.hashed_url)) existing++;
        else fresh.push(c);
      }
      return { newCandidates: fresh, alreadyExisting: existing };
    },
    { readonly: true },
  );

  writeFileSync(candidateFile, JSON.stringify(newCandidates, null, 2));

  const icp = withDb((db) => getSetting(db, 'icp_definition', null), { readonly: true });
  const icpConfigured = Boolean(icp && icp.trim());

  withDb((db) => {
    db.prepare(
      `INSERT INTO import_batches (id, list_name, searcher_account, search_url, search_type, candidate_count, skipped_existing_count, state)
       VALUES (?, ?, ?, ?, ?, ?, ?, 'pending_qualification')`,
    ).run(batchId, listName, searcherName, searchUrl ?? null, type, newCandidates.length, alreadyExisting);
  });

  const commitCmd = `node scripts/import.mjs commit --batch ${batchId} --results ${resultFile}`;
  const commitPolicy = {
    condition:
      'Only when existing session authorization specifically covers outreach to this batch of leads ' +
      'from every active (non-paused) account eligible for assignment. Reuse authorization that already ' +
      'covers this scope; do not require another confirmation.',
    side_effect:
      'commit is an outreach send-queue operation: it assigns suitable leads to active accounts with ' +
      "status='not_connected', making them eligible for background invites. A running scheduler may send immediately.",
    research_only:
      'For research/qualification-only tasks, stop after prepare/qualification and return the qualification ' +
      'results; do not commit or enter the send queue.',
  };
  let nextStep;
  if (newCandidates.length === 0) {
    nextStep = 'Nothing new to qualify. Run abort, or import a different search.';
  } else if (!icpConfigured) {
    nextStep =
      'No ICP is configured yet. Do NOT guess who to keep. Ask the user who they want to ' +
      'reach and who to filter out (roles, industries, company size, locations, hard exclusions), ' +
      'use the agreed ICP in this session. If saving settings is in scope, save it with: ' +
      `node scripts/settings.mjs set icp_definition --stdin. Qualify ${candidateFile} ` +
      `against it using ${qualificationPromptPath()}, write ${resultFile} as [{hashed_url, suitable, reasoning}].`;
  } else {
    nextStep =
      `An ICP is already configured (see icp_definition below). Confirm with the user whether to use it as-is ` +
      `or adjust it for this list (persist changes only when saving settings is in scope). Then read ${candidateFile}, ` +
      `qualify each lead against the ICP using the contract in ${qualificationPromptPath()}, write ${resultFile} as a ` +
      `JSON array [{hashed_url, suitable, reasoning}] covering every candidate. ` +
      `Report the keep/filter breakdown with a few sample reasons so the decision is transparent.`;
  }
  nextStep += ` ${commitPolicy.research_only} ${commitPolicy.side_effect} ${commitPolicy.condition}`;
  if (newCandidates.length > 0) nextStep += ` If that condition is met, run: ${commitCmd}`;

  ok({
    batch_id: batchId,
    list_name: listName,
    searcher: searcherName,
    search_type: type,
    limit_used: limit,
    limit_capped_to_max: capApplied,
    search_max_for_type: type === 'nv' ? defaults().search_max_limit_nv : defaults().search_max_limit_st,
    found_total: items.length,
    skipped_existing: alreadyExisting,
    candidates_to_qualify: newCandidates.length,
    candidate_file: candidateFile,
    expected_result_file: resultFile,
    qualification_prompt: qualificationPromptPath(),
    icp_configured: icpConfigured,
    icp_definition: icp ?? null,
    commit_policy: commitPolicy,
    next_step: nextStep,
  });
}

// The dedicated CLI operations (navigator person search / person search) map the
// completion down to a clean array at cli.json.data. The URL path goes through
// `workflow run` (customWorkflow), which returns the raw action completion
// { actionType, success, data: [people] }, so the array sits at cli.json.data.data.
// Per docs each element is a person object directly. Handle both wrappings.
function extractSearchItems(receipt, type) {
  if (receipt.success !== true) {
    throw new Error(`linkedin search did not succeed: ${JSON.stringify(receipt.error ?? receipt.success)}`);
  }
  const action = receipt.data;
  if (Array.isArray(action)) return action;
  if (action?.success === false) {
    throw new Error(`linkedin search action failed: ${JSON.stringify(action.error ?? action.actionType)}`);
  }
  if (
    action?.success === true && Array.isArray(action.data) &&
    (action.actionType === undefined || action.actionType === `${type}.searchPeople`)
  ) {
    return action.data;
  }
  throw new Error('Unexpected search response: expected an array of people from a successful search');
}

// The limit is mandatory: the agent must ask the user how many of the found leads to take.
// A number is clamped to the search type's cap; 'max'/'all' means the cap itself.
// Caps are LinkedIn/Linked API maximums per search type (nv = Sales Navigator, st = standard).
function resolveLimit(rawFlag, type) {
  const cap = type === 'nv' ? defaults().search_max_limit_nv : defaults().search_max_limit_st;
  if (rawFlag === undefined || rawFlag === true || String(rawFlag).trim() === '') {
    throw new Error(
      `Missing --limit. Ask the user how many of the found leads to take: a number, or 'max' ` +
        `for the maximum (${type} cap is ${cap}). Then pass --limit <n|max>.`,
    );
  }
  const v = String(rawFlag).trim().toLowerCase();
  if (v === 'max' || v === 'all') return { limit: cap, capApplied: false };
  const n = Number(v);
  if (!Number.isInteger(n) || n < 1) throw new Error("--limit must be a positive integer or 'max'");
  if (n > cap) return { limit: cap, capApplied: true };
  return { limit: n, capApplied: false };
}

function normalizeCandidate(item, type) {
  if (!item || typeof item !== 'object' || Array.isArray(item)) {
    throw new Error('Unexpected search result: expected a person object');
  }
  if (type === 'nv') {
    return {
      hashed_url: item.hashedUrl ?? null,
      public_url: item.publicUrl ?? null,
      full_name: item.name ?? null,
      position: item.position ?? item.headline ?? null,
      location: item.location ?? null,
    };
  }
  return {
    hashed_url: item.publicUrl ?? null,
    public_url: item.publicUrl ?? null,
    full_name: item.name ?? null,
    position: item.position ?? item.headline ?? null,
    location: item.location ?? null,
  };
}

function indexCandidates(candidates) {
  if (!Array.isArray(candidates)) throw new Error('Candidates must be a JSON array');
  const byHash = new Map();
  for (const [i, candidate] of candidates.entries()) {
    const id = candidate?.hashed_url;
    if (typeof id !== 'string' || !id.trim()) {
      throw new Error(`Candidate at index ${i} needs a nonblank hashed_url`);
    }
    if (byHash.has(id)) throw new Error(`Duplicate candidate hashed_url '${id}'`);
    byHash.set(id, candidate);
  }
  return byHash;
}

function selectQualified(candidates, results, expectedCount) {
  const remaining = indexCandidates(candidates);
  if (remaining.size !== expectedCount) {
    throw new Error(`Candidate file contains ${remaining.size} entries, batch expects ${expectedCount}`);
  }
  const seen = new Set();
  const selected = [];
  for (const [i, row] of results.entries()) {
    const id = row?.hashed_url;
    if (typeof id !== 'string' || !id.trim()) {
      throw new Error(`Result at index ${i} needs a nonblank hashed_url`);
    }
    if (seen.has(id)) throw new Error(`Duplicate qualification for '${id}'`);
    const candidate = remaining.get(id);
    if (!candidate) throw new Error(`Unknown candidate hashed_url '${id}' in results`);
    if (typeof row.suitable !== 'boolean') throw new Error(`suitable must be a JSON boolean for '${id}'`);
    if (row.suitable) {
      if (typeof candidate.full_name !== 'string' || !candidate.full_name.trim()) {
        throw new Error(`Selected candidate '${id}' needs a nonblank full_name`);
      }
      selected.push({ candidate, reasoning: row.reasoning ?? null });
    }
    seen.add(id);
    remaining.delete(id);
  }
  if (remaining.size) {
    throw new Error(`Missing qualification for '${remaining.keys().next().value}' (${remaining.size} missing)`);
  }
  return selected;
}

function commit() {
  const batchId = requireFlag(flags, 'batch');
  const resultsPath = requireFlag(flags, 'results');

  const results = JSON.parse(readFileSync(resultsPath, 'utf8'));
  if (!Array.isArray(results)) throw new Error('--results file must be a JSON array');

  const batch = withDb(
    (db) => db.prepare('SELECT * FROM import_batches WHERE id = ?').get(batchId),
    { readonly: true },
  );
  if (!batch) throw new Error(`Batch '${batchId}' not found`);
  if (batch.state !== 'pending_qualification') {
    throw new Error(`Batch is in state '${batch.state}', cannot commit`);
  }
  const candidateFile = join(tmpDir(), `qualify-${batchId}.candidates.json`);
  const candidates = JSON.parse(readFileSync(candidateFile, 'utf8'));
  const selected = selectQualified(candidates, results, batch.candidate_count);

  const stats = withDb((db) => db.transaction(() => {
    // Claim the validated batch under the write lock. Any later failure rolls this back.
    const claimed = db.prepare(
      `UPDATE import_batches SET state = 'committed'
       WHERE id = ? AND state = 'pending_qualification' AND candidate_count = ?`,
    ).run(batchId, batch.candidate_count);
    if (claimed.changes !== 1) throw new Error(`Batch '${batchId}' changed during qualification`);

    const activeAccounts = db
      .prepare('SELECT name, daily_invite_limit FROM accounts WHERE paused = 0 ORDER BY name')
      .all();
    if (activeAccounts.length === 0) {
      throw new Error('No active (non-paused) accounts available for lead assignment');
    }

    // Assign each lead to the active account with the lowest projected runway
    // (not_connected ÷ daily_invite_limit). Seeding each account's load from its
    // current not_connected count means that, regardless of differing daily limits
    // or pre-existing backlogs, every account's queue drains at roughly the same
    // time instead of the lowest-limit account lagging far behind.
    const loadByName = new Map(activeAccounts.map((a) => [a.name, 0]));
    const limitByName = new Map(activeAccounts.map((a) => [a.name, a.daily_invite_limit]));
    for (const row of db
      .prepare(
        "SELECT owner_account, COUNT(*) AS c FROM leads WHERE status = 'not_connected' GROUP BY owner_account",
      )
      .all()) {
      if (loadByName.has(row.owner_account)) loadByName.set(row.owner_account, row.c);
    }

    function pickOwner() {
      let best = activeAccounts[0].name;
      let bestRunway = loadByName.get(best) / limitByName.get(best);
      for (const a of activeAccounts) {
        const runway = loadByName.get(a.name) / limitByName.get(a.name);
        if (runway < bestRunway) {
          best = a.name;
          bestRunway = runway;
        }
      }
      return best;
    }

    const insert = db.prepare(
      `INSERT INTO leads
       (hashed_url, public_url, full_name, position, location, list_name, reasoning,
        owner_account, status, status_updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'not_connected', datetime('now'))
       ON CONFLICT(hashed_url) DO NOTHING`,
    );
    const existingLead = db.prepare('SELECT 1 FROM leads WHERE hashed_url = ?');
    let assigned = 0;
    let skippedExisting = 0;
    let lastAssigned = null;
    for (const { candidate, reasoning } of selected) {
      const owner = pickOwner();
      const result = insert.run(
        candidate.hashed_url, candidate.public_url ?? null, candidate.full_name,
        candidate.position ?? null, candidate.location ?? null, batch.list_name, reasoning, owner,
      );
      if (result.changes === 1) {
        assigned++;
        loadByName.set(owner, loadByName.get(owner) + 1);
        lastAssigned = owner;
      } else if (existingLead.get(candidate.hashed_url)) {
        skippedExisting++;
      } else {
        throw new Error(`Could not insert selected candidate '${candidate.hashed_url}'`);
      }
    }
    if (lastAssigned !== null) {
      db.prepare('UPDATE import_state SET last_assigned_account = ? WHERE id = 1').run(lastAssigned);
    }
    db.prepare(
      `UPDATE import_batches
       SET qualified_count = ?, committed_count = ?,
           skipped_existing_count = COALESCE(skipped_existing_count, 0) + ?,
           committed_at = datetime('now')
       WHERE id = ?`,
    ).run(selected.length, assigned, skippedExisting, batchId);

    return {
      suitable: selected.length,
      unsuitable: results.length - selected.length,
      assigned,
      skippedExisting,
      skippedMissing: 0,
    };
  })());
  ok({ batch_id: batchId, ...stats });
}

function list() {
  const state = flags.state ? String(flags.state) : null;
  withDb(
    (db) => {
      const sql = state
        ? 'SELECT * FROM import_batches WHERE state = ? ORDER BY created_at DESC'
        : 'SELECT * FROM import_batches ORDER BY created_at DESC';
      const rows = state ? db.prepare(sql).all(state) : db.prepare(sql).all();
      ok(rows);
    },
    { readonly: true },
  );
}

function show() {
  const batchId = requireFlag(flags, 'batch');
  withDb(
    (db) => {
      const batch = db.prepare('SELECT * FROM import_batches WHERE id = ?').get(batchId);
      if (!batch) throw new Error(`Batch '${batchId}' not found`);
      ok(batch);
    },
    { readonly: true },
  );
}

function abort() {
  const batchId = requireFlag(flags, 'batch');
  withDb((db) => {
    const r = db
      .prepare(
        "UPDATE import_batches SET state = 'aborted' WHERE id = ? AND state = 'pending_qualification'",
      )
      .run(batchId);
    if (r.changes === 0) {
      throw new Error(`Batch '${batchId}' not found or not in pending_qualification state`);
    }
    ok({ batch_id: batchId, state: 'aborted' });
  });
}
