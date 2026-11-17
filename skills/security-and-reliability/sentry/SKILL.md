---
name: sentry
description: Read Sentry issues and events with a scoped token to summarize production error trends and event details.
zh_description: "只读查询 Sentry issues 与 events，汇总线上错误趋势和事件详情。"
version: "1.0.3"
author: "OpenAI contributors; local curators"
source: "https://github.com/openai/skills"
source_url: "https://github.com/openai/skills/blob/49f948faa9258a0c61caceaf225e179651397431/skills/.curated/sentry/SKILL.md"
license: "Apache-2.0"
tags: '["security", "sentry"]'
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 4
complexity: "intermediate"
---

# Sentry (Read-only Observability)

## Quick start

- Use a locally configured read-only token with the required project and event scopes.
- Set `SENTRY_AUTH_TOKEN` as an env var.
- Optional defaults: `SENTRY_ORG`, `SENTRY_PROJECT`, `SENTRY_BASE_URL`.
- Defaults: org/project `{your-org}`/`{your-project}`, time range `24h`, environment `prod`, limit 20 (max 50).
- Always call the Sentry API (no heuristics, no caching).

If the token is missing, give the user these steps:
1. Create a Sentry auth token: https://sentry.io/settings/account/api/auth-tokens/
2. Create a token with read-only scopes such as `project:read`, `event:read`, and `org:read`.
3. Set `SENTRY_AUTH_TOKEN` as an environment variable in their system.
4. Offer to guide them through setting the environment variable for their OS/shell if needed.
- Never ask the user to paste the full token in chat. Ask them to set it locally and confirm when ready.

## Core tasks (use bundled script)

Use `scripts/sentry_api.py` for deterministic API calls. It handles pagination and retries once on transient errors.

### Optional installed CLI

The newer `sentry` CLI is an alternative only when already installed and compatible. Check its local version/help for the required command and flags; do not confuse it with `sentry-cli` or install it automatically with a remote shell pipeline.

- Keep the bundled helper as the default. Its `issue-detail` and `issue-events` take numeric IDs; the newer CLI's `issue view` and `issue events` use short IDs such as `ABC-123`. Do not pass one interface's identifier to the other.
- Establish the explicit org/project, environment, and read-only authentication first. Do not rely on project auto-discovery or read `.env` files by default. If the installed CLI cannot avoid unauthorized discovery, use the helper instead.
- After verifying local help, an explicit scoped list query is `sentry issue list {your-org}/{your-project} --query "is:unresolved environment:prod" --period 24h --limit 20 --json`. Use `--fields` only if supported, and redact the selected output before sharing it; JSON output is not automatic sanitization.
- Match the actual environment name: `prod` and `production` are different filters, not aliases. Preserve the helper's existing defaults unless the task specifies otherwise.
- Restrict this path to read queries. `issue explain` and `issue plan` invoke service-side AI workflows and are outside routine read-only inspection; do not treat them as local analysis or run them without applicable authorization.

## Script location

```bash
# From the current installed skill directory:
SENTRY_API="$PWD/scripts/sentry_api.py"
```

Pass global options such as `--org` and `--project` before the subcommand.

### 1) List issues (ordered by most recent)

```bash
python3 "$SENTRY_API" --org {your-org} --project {your-project} list-issues \
  --environment prod \
  --time-range 24h \
  --limit 20 \
  --query "is:unresolved"
```

### 2) Resolve an issue short ID to issue ID

```bash
python3 "$SENTRY_API" --org {your-org} --project {your-project} list-issues \
  --query "ABC-123" \
  --limit 1
```

Use the returned `id` for issue detail or events.

### 3) Issue detail

```bash
python3 "$SENTRY_API" \
  issue-detail \
  1234567890
```

### 4) Issue events

```bash
python3 "$SENTRY_API" \
  issue-events \
  1234567890 \
  --limit 20
```

### 5) Event detail (no stack traces by default)

```bash
python3 "$SENTRY_API" --org {your-org} --project {your-project} event-detail \
  abcdef1234567890
```

## API requirements

Always use these endpoints (GET only):

- List issues: `/api/0/projects/{org_slug}/{project_slug}/issues/`
- Issue detail: `/api/0/issues/{issue_id}/`
- Events for issue: `/api/0/issues/{issue_id}/events/`
- Event detail: `/api/0/projects/{org_slug}/{project_slug}/events/{event_id}/`

## Inputs and defaults

- `org_slug`, `project_slug`: default to `{your-org}`/`{your-project}` (avoid non-prod orgs).
- `time_range`: default `24h` (pass as `statsPeriod`).
- `environment`: default `prod`.
- `limit`: default 20, max 50 (paginate until limit reached).
- `search_query`: optional `query` parameter.
- `issue_short_id`: resolve via list-issues query first.

## Output formatting rules

- Issue list: show title, short_id, status, first_seen, last_seen, count, environments, top_tags; order by most recent.
- Event detail: include culprit, timestamp, environment, release, url.
- If no results, state explicitly.
- Redact PII in output (emails, IPs). Do not print raw stack traces.
- The bundled helper sanitizes HTTP/network failures to status and public summaries, without echoing response bodies or request URLs. Preserve that behavior and its default PII redaction; do not use `--no-redact` for shared reports. Alternative CLI output still needs explicit sanitization. Never echo tokens.

## Golden test inputs

- Org: `{your-org}`
- Project: `{your-project}`
- Issue short ID: `{ABC-123}`

Example prompt: “List the top 10 open issues for prod in the last 24h.”
Expected: ordered list with titles, short IDs, counts, last seen.
