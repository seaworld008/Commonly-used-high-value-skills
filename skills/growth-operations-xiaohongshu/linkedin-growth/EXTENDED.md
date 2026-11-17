Setup scope: follow this section only when installation/account setup is requested or already authorized. Research and import preparation do not authorize changing global packages, connecting additional accounts, or installing/replacing a persistent scheduler. Reuse the existing connection first.

# Extended procedures and examples

Use [SKILL.md](SKILL.md) to select the task. Read only the sections it links for the current step.

<a id="section-1"></a>

## First-run setup

**1. Verify Node ≥ 20:** `node --version`.
If missing — print the OS-specific install command and stop:
- macOS: `brew install node`
- Linux: `apt install nodejs` / `dnf install nodejs` / etc., or nvm
- Windows: `winget install OpenJS.NodeJS.LTS`

**2. From this skill's directory, run:**

```bash
node scripts/doctor.mjs --json
```

If the output is `Cannot find module 'better-sqlite3'`:

```bash
npm install --omit=dev
```

Then re-run doctor. (Alternative: `node scripts/doctor.mjs --fix` does this automatically.)

**3. For each FAIL in the doctor output, apply the remediation:**

| Check name | Remediation |
|------------|-------------|
| `linkedin-cli` | `npm install -g @linkedapi/linkedin-cli` |
| `cli-accounts` | Have the account owner configure the requested account through the trusted local CLI setup flow at https://app.linkedapi.io; do not request tokens in chat, print them, or store them in shared command history. Check connection status afterward. |
| `db` | Auto-fixed by any script on first invocation, or explicitly: `node scripts/db.mjs init` |
| `db-accounts` | Run `linkedin account list` (prints a table; the `*` marks the active account) and register each one here: `node scripts/account.mjs add --name <short-name> --cli-account "<exact name from linkedin account list>"`. The short name is what every other command takes; the cli-account is the mapping. |
| `scheduler` | Should pass automatically. On headless Linux without systemd-user, doctor falls back to `cron`. |

**4. Re-run `node scripts/doctor.mjs --json` until `"ok": true`.**

**5. Set the connection pace — ask once, apply to all accounts.** Ask the user a single
question (not per account): "By default each account sends at most one connection request
every 15 minutes — keep 15, or change it?". Apply their answer to every account via
`--min-invite-interval <N>` (either pass it on each `account.mjs add`, or
`account.mjs update --name <acct> --min-invite-interval <N>` for all afterward). Default is
15. Let the user know they can fine-tune it per account later just by asking (e.g. "make
kiril one every 30 minutes") — it is a per-account setting, this question just sets a common
value for everyone.

**6. Set the retry policy.** Ask the user: "If someone doesn't accept the request, should
we try connecting from another account? (no / a specific number of accounts / all of them)".
Then:

```bash
node scripts/settings.mjs set max_connect_attempts 1      # no retry (default)
node scripts/settings.mjs set max_connect_attempts 2      # original + 1 more
node scripts/settings.mjs set max_connect_attempts all    # every account
```

**7. Enable or replace the background scheduler only when persistent outreach for the selected accounts is in the existing authorization:**

```bash
node scripts/schedule.mjs install
```

This installs one platform-native background task that keeps the pipeline running
on its own. When talking to the user, describe it as "the pipeline now runs in the
background and sends invites during each account's active hours" — do not expose the
scheduler's internal wake-up frequency (the tick) or other plumbing. (The invite *pace*
from step 5 — "one connect every N minutes" — is a real user-facing setting and fine to
discuss; it's the tick's 5-minute heartbeat that stays hidden.) See the **Phase B** and
**Scheduler** sections below for how it actually works.

Enabling an authorized scheduler may immediately consume an existing send queue; setup does
not guarantee that the queue is empty. Report the actual scheduler state without manually
invoking invites during setup.

**8. Tell the user the next step and offer to do it.** End onboarding with a concrete call
to action, e.g.: "Give me a LinkedIn or Sales Navigator search URL (or a term plus optional
filters), a list name, and a limit, and I'll prepare and qualify the candidates. Research-only
work ends with the qualification results. Committing suitable leads puts them in the outreach
send queue, which a running scheduler may consume immediately; I'll do that only when our
existing session authorization specifically covers this batch and every active (non-paused)
sending account eligible for assignment." If the user provides a search, proceed into Phase A
within that scope. Setup or a search URL alone does not authorize outreach to a new batch.
Reuse authorization that already covers the batch/accounts; do not require another confirmation.

`node scripts/import.mjs commit --batch <id> --results <file>` is an outreach send-queue
operation: it assigns suitable leads to active accounts with `status='not_connected'`, making
them eligible for background invites. For research/qualification-only tasks, stop after
prepare/qualification and return the qualification results without committing. There is no
research-only commit mode.

Import input contract: provide a typed search URL, or a term with optional filters; filters alone are insufficient. In CLI ≥ 1.2.24, list values containing commas use one JSON-array argument.
