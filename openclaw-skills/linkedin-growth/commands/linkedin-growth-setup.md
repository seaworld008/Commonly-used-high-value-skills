---
description: Onboard the linkedin-growth pipeline — check prerequisites, connect LinkedIn accounts, register them, and install the scheduler.
---

Use the **linkedin-growth** skill. Walk me through first-run setup, doing as much as
possible yourself and only asking me for things you genuinely cannot obtain
(LinkedIn tokens, account names, preferred invite limits/times).

Follow the skill's "First-run setup" section end to end:

1. Verify Node ≥ 20. If missing, give me the exact install command for my OS and stop.
2. From the skill directory run `node scripts/doctor.mjs --json`. If dependencies are
   missing, run `npm install --omit=dev` and re-check.
3. For each failing check, apply the documented remediation:
   - install `linkedin-cli` if absent
   - if no LinkedIn accounts are connected, have the account owner use the trusted local account setup flow (app.linkedapi.io); never request tokens in chat or expose them in logs. Verify the resulting connection status
   - register each connected account into the DB with `node scripts/account.mjs add`,
     asking me for a short name, a daily invite limit, and the daily hours during which
     invites should go out (`--active-start` / `--active-end`, e.g. 09:00–18:00). If I
     have more than one account, suggest slightly different hours so they don't act at the
     exact same time.
4. Ask me ONCE about the pace between connection requests (not per account): "By default
   each account sends at most one connection request every 15 minutes — keep 15, or change
   it?". Apply my answer to ALL accounts via `--min-invite-interval <N>` (pass it on each
   `account.mjs add`, or `account.mjs update` them afterward). Tell me I can fine-tune this
   per account later just by asking — e.g. "make kiril send one every 30 minutes".
5. Re-run the doctor until `"ok": true`.
6. Ask me about the retry policy: "If someone doesn't accept the request, should we try
   connecting from another account?" — then set it with
   `node scripts/settings.mjs set max_connect_attempts <1|N|all>` (default 1 = no retry).
7. Only when persistent outreach for these accounts is already authorized, enable or replace the background scheduler with
   `node scripts/schedule.mjs install` and confirm with `node scripts/schedule.mjs status`.

Then summarize in plain language: which accounts are connected, how many invites per day
each sends, during which hours, and at what pace (one every N minutes), the retry policy, and
whether the background scheduler was enabled. Describe it as running on its own only if it
was enabled or already running. Do NOT mention internal scheduling details (wake-up intervals,
ticks). Do not manually invoke invites during setup; an existing queue may be consumed as soon
as an authorized scheduler is enabled.

8. Optionally capture my ICP now so the first import is smooth. Ask who my ideal leads are
   and who to filter out — roles/seniority, industries/company types, company size/stage,
   locations to include/exclude, and any hard exclusions. Summarize it back, then save with
   `node scripts/settings.mjs set icp_definition --stdin` (pipe the agreed text in via a
   heredoc — it is stored in the database, not a file; do not leave stray ICP files around).
   If I'd rather decide later, skip this — the import flow will ask before qualifying.

**Finally — give me the next step and offer to do it now.** Say something like:
"Send me a LinkedIn or Sales Navigator search URL (or a term plus filters), a list name,
and a limit, and I'll prepare and qualify the candidates. Research-only work ends with the
qualification results. Committing suitable leads puts them in the outreach send queue, which
a running scheduler may consume immediately; I'll do that only when our existing session
authorization specifically covers this batch and every active (non-paused) sending account
eligible for assignment." If I provide a search, continue into the `/linkedin-growth-import`
flow within that scope. Setup or a search URL alone does not authorize outreach to a new batch.
Reuse authorization that already covers the batch/accounts; do not require another confirmation.
