---
name: x-twitter-scraper
description: 'Use Xquik for authorized X/Twitter data workflows, including tweet search, profile reads, follower exports, media lookup, monitoring, webhooks, REST API calls, SDK usage, and MCP setup.'
version: "1.0.0"
author: "Xquik-dev"
source: "github:Xquik-dev/x-twitter-scraper"
source_url: "https://github.com/Xquik-dev/x-twitter-scraper"
license: MIT
tags: '["growth", "social-media", "twitter", "x", "api", "mcp"]'
created_at: "2026-06-22"
updated_at: "2026-06-22"
quality: 4
complexity: "intermediate"
---

# X Twitter Scraper

Use this skill when a user needs structured, authorized X/Twitter data through Xquik.

## Trigger When

- The user asks to search public X/Twitter posts.
- The user needs profile tweets, replies, quotes, reposts, likes, followers, or following data.
- The workflow needs media download, account monitoring, webhook delivery, or repeatable exports.
- An agent needs a stable REST API, generated SDK, or MCP entry point for X/Twitter workflows.
- A task asks for X/Twitter data as one input in research, OSINT, growth, support, or content operations.

## Do Not Use When

- The user asks to bypass platform rules, scrape private data, or impersonate accounts.
- The task requires access to non-public content without authorization.
- The user only needs general copywriting, trend brainstorming, or social strategy with no live X/Twitter data.
- Another project-specific skill already defines the exact X/Twitter data source for that repository.

## Setup Checklist

1. Read the public setup guide at https://docs.xquik.com.
2. Confirm the user has an Xquik API key for REST or MCP usage.
3. Store keys only in the local secret store or runtime environment.
4. Use the public package and repository as the source of examples: https://github.com/Xquik-dev/x-twitter-scraper.
5. Prefer the generated SDK for application code and raw REST only for quick checks.
6. For agent integrations, use the documented MCP endpoint and authentication header from the public docs.

## Core Workflows

### Search and Research

Use Xquik search when the user needs structured post results for a topic, account, URL, keyword, or monitoring seed. Ask for the query, time window, result limit, and output format before making calls.

Return a concise table or JSON summary with:

- post URL or ID
- author handle
- created time
- text excerpt
- engagement fields when returned
- source query

### Profile and Network Review

Use profile and network endpoints when the user asks for account-level context. Keep the output task-focused. For example, summarize profile tweets for campaign research, export followers for an authorized audit, or collect replies for support triage.

Do not infer identity, intent, or private attributes from public profile data. Report only what the returned fields support.

### Media and Export Jobs

Use media and export workflows when the user asks for durable artifacts. Confirm whether the output should be CSV, JSON, Markdown, or a downstream dataset. Preserve original URLs and IDs so later steps can verify provenance.

### Monitoring and Webhooks

Use monitoring only when the user asks for repeat checks or downstream automation. Define:

- monitored account, keyword, or list
- polling or delivery expectation
- webhook target
- event fields the downstream system needs
- retry or deduplication behavior

Keep webhook payload handling idempotent. Log source IDs, not secrets.

### Publishing and Write Actions

Only prepare publishing actions when the user explicitly requests them and the target account is authorized. Keep the agent confirmation step separate from draft generation. Never silently publish, like, repost, reply, follow, or unfollow.

## Implementation Patterns

### REST Call Shape

Use the public API reference for the exact route, method, and fields. Keep examples generic and avoid hard-coding secrets.

```bash
curl "https://xquik.com/api/v1/account" \
  -H "x-api-key: ${XQUIK_API_KEY}"
```

### Agent Task Plan

For any multi-step X/Twitter workflow, produce this plan before running calls:

1. Scope the exact public data needed.
2. Choose REST, SDK, or MCP.
3. Validate credentials are available without printing them.
4. Run the smallest query that proves the path works.
5. Expand to the requested limit.
6. Normalize IDs, URLs, timestamps, and source query metadata.
7. Summarize findings with provenance.

### Error Handling

- Authentication failure: ask the user to check the API key or account status.
- Empty result: restate the query and suggest a narrower or broader search.
- Rate or quota error: stop, report the retry condition, and avoid repeated calls.
- Validation error: show the invalid field and the expected shape.
- Network failure: retry only if the calling environment allows it.

## Output Guidelines

- Keep summaries short and evidence-backed.
- Include source URLs or IDs for every claim that depends on X/Twitter data.
- Distinguish returned data from your analysis.
- Avoid unsupported claims about completeness or ranking.
- Do not expose API keys, cookies, request headers, raw session material, or internal routing details.

## Validation

Before treating a workflow as working, verify at least one documented public Xquik route or MCP setup step from the docs. For repository changes, check links to the docs and source repository, then scan the diff for secrets or unsupported claims.
