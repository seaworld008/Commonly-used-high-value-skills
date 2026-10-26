---
name: linkedin
description: 'General-purpose LinkedIn automation – fetch profiles, search people and companies, send messages, manage connections, create posts, and more. Use when the user wants to interact with LinkedIn.'
zh_description: "通过 Linked API 搜索领英资料、管理连接、消息与内容发布。"
version: "1.0.4"
author: vprudnikoff
source: github:Linked-API/linkedin-skills
source_url: "https://github.com/Linked-API/linkedin-skills/blob/e46beb9aea0af3896fd49dd7b39cff1061bf8f6d/linkedin/SKILL.md"
license: MIT
tags: '[linkedin, automation, social-media, outreach, cli]'
created_at: "2026-07-10"
updated_at: "2026-10-26"
quality: 5
complexity: intermediate
---

# LinkedIn Skill

You have access to `linkedin` – a CLI tool for LinkedIn automation. Use it to fetch profiles, search people and companies, send messages, manage connections, create posts, react, comment, and more.

Each command sends a request to Linked API, which runs a real cloud browser to perform the action on LinkedIn. Operations are **not instant** – expect 30 seconds to several minutes depending on complexity.

If `linkedin` is not available, install it:

```bash
npm install -g @linkedapi/linkedin-cli
```

## Authentication

If a command fails with exit code 2 (authentication error), ask the user to set up their account:

1. Go to [app.linkedapi.io](https://app.linkedapi.io) and sign up or log in
2. Connect their LinkedIn account
3. Copy the **Linked API Token** and **Identification Token** from the dashboard

The account owner completes authentication in their own secure local setup. Do not ask for tokens in chat or place them in command arguments. Inspect the installed CLI help for its supported secure configuration path; the following is a local setup responsibility, not an agent command:

```text
Account owner: configure Linked API and Identification credentials locally.
Agent: retry only after the configured CLI reports authentication is available.
```

## Global Flags

Always use `--json` and `-q` for machine-readable output:

```bash
LINKEDAPI_CLIENT=skill:linkedin linkedin <command> --json -q
```

When using this skill, run every `linkedin ...` example below with the
`LINKEDAPI_CLIENT=skill:linkedin` prefix so Linked API can attribute usage to the skill.

| Flag | Description |
|------|-------------|
| `--json` | Structured JSON output |
| `--quiet` / `-q` | Suppress stderr progress messages |
| `--fields name,url,...` | Select specific fields in output |
| `--no-color` | Disable colors |
| `--account "Name"` | Use a specific account for this command |

## Output Format

Read [the detailed procedure and examples](EXTENDED.md#section-4) when working on this part of the task.

## Commands

### Fetch a Person Profile

Read [the detailed procedure and examples](EXTENDED.md#section-3) when working on this part of the task.

### Endorse a Person's Skills

```bash
linkedin person endorse <url> --skill 'Project Management' --json -q
linkedin person endorse <url> --pattern manage --pattern '^scrum$' --json -q
linkedin person endorse <url> --all --json -q
```

Choose exactly one of `--skill`, `--pattern` or `--all`:
- Use `--skill` for one exact skill name; letter case and extra spaces are ignored.
- Use repeatable `--pattern` to select skills matching any of the patterns. Patterns use RE2, are case-insensitive and match anywhere in the name. Anchor with `^…$` to match a whole name. Provide 1-20 patterns, each 1-200 characters; lookaround and backreferences are unsupported.
- Use `--all` only when the user wants every skill endorsed. It omits the patterns parameter; never send an empty patterns array.

Skill names are in the profile owner's language, regardless of your own LinkedIn language. Fetch the profile with `--skills` first when you need to discover the names; a German profile may list `Projektmanagement` rather than `Project Management`.

Only **1st-degree connections** can receive endorsements. An already-endorsed skill stays endorsed and counts as success. Each successful endorsement, including an existing one, counts toward the account's `stEndorsements` limit. With `--pattern` or `--all`, check every item's `success` and `error.type` in `data`: a failed skill does not stop the others, and `limitExceeded` can affect only part of the result.


Endorsements are external account writes. Execute only for the authorized account, selected people/skills and approved batch scope. Enabling ongoing inbox sync is a separate persistent operation.

### Search People

```bash
linkedin person search [flags] --json -q
```

| Flag | Description |
|------|-------------|
| `--term` | Search keyword or phrase |
| `--limit` | Max results |
| `--first-name` | Filter by first name |
| `--last-name` | Filter by last name |
| `--position` | Filter by job position |
| `--locations` | Comma-separated locations |
| `--industries` | Comma-separated industries |
| `--current-companies` | Comma-separated current company names |
| `--previous-companies` | Comma-separated previous company names |
| `--schools` | Comma-separated school names |
| `--connection-degrees` | Comma-separated connection degrees: `1st`, `2nd`, `3rd+` |

```bash
linkedin person search --term "product manager" --locations "San Francisco" --json -q
linkedin person search --current-companies "Google" --position "Engineer" --limit 20 --json -q
```

### Fetch a Company

Read [the detailed procedure and examples](EXTENDED.md#section-1) when working on this part of the task.

### Search Companies

```bash
linkedin company search [flags] --json -q
```

| Flag | Description |
|------|-------------|
| `--term` | Search keyword |
| `--limit` | Max results |
| `--sizes` | Comma-separated sizes: `1-10`, `11-50`, `51-200`, `201-500`, `501-1000`, `1001-5000`, `5001-10000`, `10001+` |
| `--locations` | Comma-separated locations |
| `--industries` | Comma-separated industries |

```bash
linkedin company search --term "fintech" --sizes "11-50,51-200" --json -q
```

### Send a Message

```bash
linkedin message send <person-url> '<text>' --json -q
```

Text up to 1900 characters. Wrap the message in single quotes to avoid shell interpretation issues.

```bash
linkedin message send https://www.linkedin.com/in/username 'Hey, loved your latest post!' --json -q
```

### Inbox

To read messages use `inbox get`. Call `message get` only when you need a person's earlier history, and never repeat it to check for new messages.

Enable inbox monitoring once per account, before sending messages whose replies you need – it captures only messages that arrive after it is on:

```bash
linkedin inbox sync --json -q          # standard inbox
linkedin inbox sync --nv --json -q     # Sales Navigator inbox
```

New messages from everyone, with an advancing `--since`:

```bash
linkedin inbox get --since 2024-01-15T10:30:00Z --json -q
```

The whole known conversation with one person, including history loaded by `message get`:

```bash
linkedin inbox get --person https://www.linkedin.com/in/username --json -q
```

With `--person`, the output has `messages` and `threads`. Each thread has `historyComplete`: if it is `false` and you need earlier messages, run `message get <person-url>` once, then `inbox get --person` again. A hashed person URL (`personHashedUrl` from a message) always matches; a public URL matches only once Linked API knows it, so prefer the hashed URL when messages show `personPublicUrl: null`. Message times are whole minutes: to check for a reply, pass `--type` of your message and `--since` a few minutes before it, take the earliest `us` message in the result (the one you sent, not a later follow-up) and count a `them` message that is not earlier than it; if your message is not in the result yet, the reply is not known yet.

### Get Conversation

```bash
linkedin message get <person-url> [--since TIMESTAMP] --json -q
```

Loads the person's earlier history on the first call, which may take longer; subsequent calls are faster. Prefer `linkedin inbox get --person <url>` to read messages – use this only when you need history from before inbox monitoring was enabled.

```bash
linkedin message get https://www.linkedin.com/in/username --json -q
linkedin message get https://www.linkedin.com/in/username --since 2024-01-15T10:30:00Z --json -q
```

### Connection Management

#### Check connection status

```bash
linkedin connection status <url> --json -q
```

#### Send connection request

```bash
linkedin connection send <url> [--note 'text'] [--email user@example.com] --json -q
```

#### List connections

```bash
linkedin connection list [flags] --json -q
```

| Flag | Description |
|------|-------------|
| `--limit` | Max connections to return |
| `--since` | Only connections made since ISO timestamp (only works when no filter flags are used) |
| `--first-name` | Filter by first name |
| `--last-name` | Filter by last name |
| `--position` | Filter by job position |
| `--locations` | Comma-separated locations |
| `--industries` | Comma-separated industries |
| `--current-companies` | Comma-separated current company names |
| `--previous-companies` | Comma-separated previous company names |
| `--schools` | Comma-separated school names |

```bash
linkedin connection list --limit 50 --json -q
linkedin connection list --current-companies "Google" --position "Engineer" --json -q
linkedin connection list --since 2024-01-01T00:00:00Z --json -q
```

#### List pending outgoing requests

```bash
linkedin connection pending --json -q
```

#### List incoming connection requests

Invitations that others have sent to you (received requests).

```bash
linkedin connection requests --json -q
```

#### Accept an incoming request

```bash
linkedin connection accept <url> --json -q
```

#### Ignore an incoming request

```bash
linkedin connection ignore <url> --json -q
```

#### Withdraw a pending request

```bash
linkedin connection withdraw <url> [--no-unfollow] --json -q
```

By default, withdrawing also unfollows the person. Use `--no-unfollow` to keep following.

#### Remove a connection

```bash
linkedin connection remove <url> --json -q
```

### Posts

#### Fetch a post

```bash
linkedin post fetch <url> [flags] --json -q
```

| Flag | Description |
|------|-------------|
| `--comments` | Include comments |
| `--reactions` | Include reactions |
| `--comments-limit` | Max comments to retrieve (requires `--comments`) |
| `--comments-sort` | Sort order: `mostRelevant` or `mostRecent` (requires `--comments`) |
| `--comments-replies` | Include replies to comments (requires `--comments`) |
| `--reactions-limit` | Max reactions to retrieve (requires `--reactions`) |

```bash
linkedin post fetch https://www.linkedin.com/posts/username_activity-123 --json -q

# With comments sorted by most recent, including replies
linkedin post fetch https://www.linkedin.com/posts/username_activity-123 \
  --comments --comments-sort mostRecent --comments-replies --json -q
```

#### Search posts

```bash
linkedin post search [flags] --json -q
```

| Flag | Description |
|------|-------------|
| `--term` | Search keyword or phrase, up to 50 characters |
| `--limit` | Max results to return, up to 100 |
| `--from-members` | People whose posts to keep |
| `--from-companies` | Companies whose posts to keep |
| `--mentioning-members` | People the post must mention |
| `--mentioning-companies` | Companies the post must mention |
| `--author-companies` | Companies the author works at |

Each actor flag is a comma-separated list. An element is `name` or `name:identifier`, where the identifier is a URN or LinkedIn URL of that person or company and pins the filter to exactly them. A name alone may match a namesake. When an entry cannot be applied, the action fails with `filterNotApplied`; correct or remove it rather than retrying.

```bash
linkedin post search --term "ai" --from-members "Bill Gates,Example Person:urn:li:member:123456789" --json -q
```

#### Create a post

```bash
linkedin post create '<text>' [flags] --json -q
```

| Flag | Description |
|------|-------------|
| `--company-url` | Post on behalf of a company page (requires admin access) |
| `--attachments` | Attachment as `url:type` or `url:type:name`. Types: `image`, `video`, `document`. Can be specified multiple times. |
| `--mention` | One mention, bound to `@[key]` in the text. Format below. Can be specified multiple times, up to 20. |

Attachment limits: up to 9 images, or 1 video, or 1 document. Cannot mix types.

Mention format — write `@[key]` in the text, then describe that key with `--mention` as `key:name` or `key:name:identifier`. Everything after the second `:` is the identifier, so its own colons need no escaping. The identifier is optional and is one of `urn:li:member:<id>`, `urn:li:organization:<id>`, a hashed profile URL, or a hashed company URL; without it LinkedIn's first suggestion for `name` is used, which may not be the entity you meant. Every `@[key]` must have a matching `--mention` and vice versa, and keys cannot repeat.

```bash
linkedin post create 'Excited to share our latest update!' --json -q

# With a document
linkedin post create 'Our Q4 report' \
  --attachments "https://example.com/report.pdf:document:Q4 Report" --json -q

# Mentioning a person
linkedin post create 'Huge thanks to @[author] for the write-up!' \
  --mention "author:Example Person:urn:li:member:123456789" --json -q

# Post as a company
linkedin post create 'Company announcement' \
  --company-url https://www.linkedin.com/company/name --json -q
```

#### Repost a post

```bash
linkedin post repost <url> [flags] --json -q
```

| Flag | Description |
|------|-------------|
| `--text` | Your own commentary (up to 3000 characters). Without it the post is reposted as is. |
| `--mention` | One mention, bound to `@[key]` in `--text`. Same format as for `post create`. Can be specified multiple times, up to 20. |

The repost's own `postUrl` and `postUrn` come back, not those of the post you reposted. They are empty when the repost was published but LinkedIn did not return its address — do not retry, the repost is already live.

`alreadyReposted` is returned only when LinkedIn refuses an instant repost (one without `--text`). LinkedIn does not always refuse a repeat repost: a repost of your own post, or a repost with commentary, can be published again. Keep track of what you have already reposted instead of relying on this error.

```bash
linkedin post repost https://www.linkedin.com/posts/username_activity-123 --json -q

# With commentary
linkedin post repost urn:li:activity:1234567890123456789 \
  --text 'Worth reading, especially the part on onboarding.' --json -q
```

#### React to a post

```bash
linkedin post react <url> --type <reaction> [--company-url <url>] --json -q
```

Reaction types: `like`, `love`, `support`, `celebrate`, `insightful`, `funny`.

```bash
linkedin post react https://www.linkedin.com/posts/username_activity-123 --type like --json -q

# React on behalf of a company
linkedin post react https://www.linkedin.com/posts/username_activity-123 --type celebrate \
  --company-url https://www.linkedin.com/company/name --json -q
```

#### Comment on a post

```bash
linkedin post comment <url> '<text>' [--company-url <url>] --json -q
```

Text up to 1000 characters.

```bash
linkedin post comment https://www.linkedin.com/posts/username_activity-123 'Great insights!' --json -q

# Comment on behalf of a company
linkedin post comment https://www.linkedin.com/posts/username_activity-123 'Well said!' \
  --company-url https://www.linkedin.com/company/name --json -q
```

### Statistics

Read [the detailed commands and examples](EXTENDED.md#statistics) when this feature is needed.

### Sales Navigator

Read [the detailed commands and examples](EXTENDED.md#sales-navigator) when this feature is needed.

### Custom Workflows

Execute a custom workflow definition from a file, stdin, or inline:

```bash
# From file
linkedin workflow run --file workflow.json --json -q

# From stdin
cat workflow.json | linkedin workflow run --json -q

# Inline
echo '{"actions":[...]}' | linkedin workflow run --json -q
```

Check workflow status or wait for completion:

```bash
linkedin workflow status <id> --json -q
linkedin workflow status <id> --wait --json -q
```

See [Building Workflows](https://linkedapi.io/docs/building-workflows/) for the workflow JSON schema.

### Changelog

Read what is new in Linked API. Check it before telling the user that something is not supported yet – the capability may have shipped recently. No authentication is needed:

```bash
linkedin changelog --json -q                       # Every release, newest first
linkedin changelog --since 2026-10-01 --json -q    # Releases from that week on
```

The JSON is the changelog itself, not the usual `success`/`data` envelope: `entries` holds releases, each with a `date` (the Monday of its week) and `items` with `title`, `body` and `docs` (a path on https://linkedapi.io). A release counts as shipped at the end of its week, so `--since` in the middle of a week still returns that week's release – deduplicate by `date`. A malformed `--since` exits with code 5 and the server's message.

### Account Management

```bash
linkedin account list                            # List accounts (* = active)
linkedin account switch "Name"                   # Switch active account
linkedin account rename "Name" --name "New Name" # Rename account
linkedin reset                                   # Remove active account
linkedin reset --all                             # Remove all accounts
```

## Important Behavior

- **Sequential execution.** All operations for an account run one at a time. Multiple requests queue up.
- **Not instant.** A real browser navigates LinkedIn – expect 30 seconds to several minutes per operation.
- **Timestamps in UTC.** All dates and times are in UTC.
- **Single quotes for text arguments.** Use single quotes around message text, post text, and comments to avoid shell interpretation issues with special characters.
- **Action limits.** Per-account limits are configurable on the platform. A `limitExceeded` error means the limit was reached.
- **URL normalization.** All LinkedIn URLs in responses are normalized to `https://www.linkedin.com/...` format without trailing slashes.
- **Null fields.** Fields that are unavailable are returned as `null` or `[]`, not omitted.

<!-- LOCAL-CURATION-SUPPLEMENT:START -->
## Boundaries and Safe Authorization

- Use only LinkedIn accounts that the user owns or is explicitly authorized to operate.
- Treat invitations, messages, posts, reactions, comments, connection changes, account
  changes, and workflows containing any of those steps as external writes. Run them only
  when the user has explicitly requested the specific action. For bulk writes, confirm the
  account, audience, approximate count, content, and timing before execution unless those
  details were already approved in the current request.
- Prefer a preview or a small sample before a bulk operation. Never manufacture consent,
  impersonate another person, or use this skill for deceptive, discriminatory, harassing,
  or indiscriminate outreach.
- Respect LinkedIn controls, applicable law, and organizational policy. Never bypass rate
  limits, CAPTCHAs, account warnings, or access restrictions; stop and report them instead.
- Minimize collection of personal data. Do not expose tokens in chat output, logs, shell
  history, or committed files, and do not retain profile data longer than the task requires.
- If the requested authority, target set, or effect is ambiguous, pause before the first
  write and ask the user to clarify it.
<!-- LOCAL-CURATION-SUPPLEMENT:END -->
