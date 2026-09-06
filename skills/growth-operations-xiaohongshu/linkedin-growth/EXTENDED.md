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
| `cli-accounts` | Ask the user for their Linked API Token and Identification Token (link: https://app.linkedapi.io), then `linkedin setup --linked-api-token=<a> --identification-token=<b>`. Repeat per LinkedIn account they want connected. |
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

**7. Enable the background scheduler (only after at least one account is registered):**

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

**8. Tell the user the next step and offer to do it.** Setup alone sends nothing — the
pipeline is empty until leads are imported. End onboarding with a concrete call to action,
e.g.: "You're all set. To start, give me a LinkedIn or Sales Navigator search URL (or
search filters) and a name for the list, and I'll import and qualify your first batch of
leads." If the user provides one, proceed straight into **Phase A** below. Do not end the
setup conversation without this prompt.
