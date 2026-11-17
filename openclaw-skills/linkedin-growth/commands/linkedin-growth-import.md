---
description: Search and qualify LinkedIn / Sales Navigator leads; commit to the outreach send queue only with existing authorization for this batch and the sending accounts.
argument-hint: "[search URL or term plus filters] [list name]"
---

Use the **linkedin-growth** skill to run a Phase A import. Arguments: $ARGUMENTS

Drive the import flow within the requested scope. Research/qualification-only tasks stop
after prepare/qualification and return the qualification results without entering the send queue.

1. Determine the inputs. If I gave a search URL, detect the type (URL containing
   `/sales/` → `nv`, otherwise `st`). For a native search, require `--term` and optionally add filters. Ask me for
   anything missing: which account should run the search (`--searcher`), and a list name
   (`--list`). If I have more than one account, confirm the searcher with me.
2. Resolve the limit — reuse a number or "max" already supplied for this task; ask only if
   missing (Sales Navigator caps at 2500, standard search at 1000). Do not assume a default.
3. Run `node scripts/import.mjs prepare --searcher <acct> --list "<name>" --type <nv|st>
   --limit <N|max>` with either `--search-url "<url>"` or `--term` plus optional filters. (`--limit` is
   required; a number above the cap is clamped and reported as `limit_capped_to_max`.)
   `prepare` writes local batch/candidate records, so use it only when those writes are in scope.
4. **Settle the ICP before qualifying** (this is the filtering step — make it explicit, not
   silent). The `prepare` output tells you whether an ICP is configured:
   - If none is configured, interview me: which roles/seniority to target, which
     industries/company types fit, company size/stage if relevant, locations to include or
     exclude, and any hard exclusions. Summarize what you heard and use it in this session.
     Only when saving settings is in scope, save it with
     `node scripts/settings.mjs set icp_definition --stdin` (pipe the text via a heredoc — it
     is stored in the database, not a file; do not leave stray ICP files in the repo or tmp).
   - If one is configured, show it to me in plain language and ask whether to use it as-is or
     adjust it for this list (persist changes only when saving settings is in scope).
5. Read the returned candidate file and qualify every candidate **against my ICP**, using the
   output contract in `config/qualification-prompt.md`. For more than ~25 candidates, chunk
   the work in the current session or use available, authorized delegation. Produce a JSON array
   `[{hashed_url, suitable, reasoning}]` covering every candidate (reasoning must cite the ICP
   criterion that drove the decision), and write it to the expected result file path.
6. **Commit to the send queue only for authorized outreach.** Run
   `node scripts/import.mjs commit --batch <id> --results <file>` only when existing session
   authorization specifically covers outreach to this batch of leads from every active
   (non-paused) account eligible for assignment. Reuse authorization that already covers this
   scope; do not require another confirmation. Otherwise return the qualification results and stop.
7. Report transparently: how many were found, skipped as duplicates, kept vs filtered, and a few
   concrete sample reasons from both sides. After authorized commit, also report how the new
   leads were distributed across accounts and that they are now eligible for invites.

`commit` is an outreach send-queue operation: it assigns suitable leads to active accounts
with `status='not_connected'`, making them eligible for background invites. A running scheduler
may send immediately. The import process need not call the invite API itself for this side effect
to occur; `commit` has no research-only mode.
