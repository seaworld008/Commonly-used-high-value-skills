---
name: linear
description: 'Manage Linear issues, projects, and teams with an API-first workflow. Uses the GraphQL API by default and can fall back to the Linear MCP server when it is already configured.'
version: "2.0.0"
author: "seaworld008"
source: "adapted-from-hermes-agent"
source_url: "https://github.com/NousResearch/hermes-agent/blob/main/skills/productivity/linear/SKILL.md"
tags: '["graphql", "issues", "linear", "mcp", "productivity", "project-management"]'
created_at: "2026-03-04"
updated_at: "2026-04-13"
quality: 4
complexity: "intermediate"
license: "MIT"
metadata:
short-description: 'Manage Linear with GraphQL API first, MCP second'
---

# Linear

## When to Use

Use this skill when the user wants to:

- read, search, create, or update Linear issues
- triage bugs or organize backlog state
- assign work, set priority, labels, or due dates
- create or inspect projects and team workflow states
- automate repeatable Linear operations from the terminal

## Recommended Approach

Prefer the **Linear GraphQL API** first.

Why:

- it works even when the Linear MCP server is not installed
- it is explicit and scriptable
- it gives full control over issue fields, workflow states, and pagination
- it is easier to debug than opaque tool-calling failures

Use the **Linear MCP server** only when:

- the user already has it connected
- the task benefits from natural-language tool invocation over direct API calls
- OAuth is already working and there is no reason to switch

## Prerequisites

### API-first mode

You need:

- a Linear personal API key
- `curl`

Set the API key:

```bash
export LINEAR_API_KEY="lin_api_xxx"
```

Get it from:

- Linear Settings
- API
- Personal API keys

### MCP fallback mode

If the user prefers MCP and it is not connected yet:

```bash
codex mcp add linear --url https://mcp.linear.app/mcp
codex --enable rmcp_client
codex mcp login linear
```

After login they need to restart Codex before using the MCP path.

## API Basics

- Endpoint: `https://api.linear.app/graphql`
- Method: `POST`
- Auth header: `Authorization: $LINEAR_API_KEY`
- Content type: `application/json`

Base request pattern:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ viewer { id name email } }"}' | python -m json.tool
```

Important:

- GraphQL can return HTTP 200 with an `errors` array, so always inspect the body
- issue identifiers like `ENG-123` are often easier to use than UUIDs for reads
- updates to status require the target `stateId`, not just the state name

## Workflow States

Linear workflow state `type` values:

- `triage`
- `backlog`
- `unstarted`
- `started`
- `completed`
- `canceled`

Priority values:

- `0` none
- `1` urgent
- `2` high
- `3` medium
- `4` low

## Core Workflow

Follow this order for most tasks:

1. Identify the target team
2. Fetch workflow states for that team
3. Search or inspect relevant issues
4. Apply changes with explicit IDs
5. Summarize what changed and what remains open

## Common Queries

### Get current user

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ viewer { id name email } }"}' | python -m json.tool
```

### List teams

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ teams { nodes { id name key } } }"}' | python -m json.tool
```

### List workflow states for a team

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ workflowStates(filter:{ team:{ key:{ eq:\"ENG\" } } }) { nodes { id name type } } }"}' | python -m json.tool
```

### Search issues

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ issueSearch(query:\"login bug\", first:10) { nodes { id identifier title state { name type } assignee { name } url } } }"}' | python -m json.tool
```

### Get one issue

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ issue(id:\"ENG-123\") { id identifier title description priority dueDate state { id name type } assignee { id name } labels { nodes { id name } } project { id name } url } }"}' | python -m json.tool
```

### List projects

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ projects(first:20) { nodes { id name progress lead { name } url } } }"}' | python -m json.tool
```

## Common Mutations

### Create issue

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query":"mutation($input: IssueCreateInput!) { issueCreate(input:$input) { success issue { id identifier title url } } }",
    "variables":{
      "input":{
        "teamId":"TEAM_UUID",
        "title":"Fix login redirect bug",
        "description":"Redirect loses the next parameter",
        "priority":2
      }
    }
  }' | python -m json.tool
```

### Update status

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { issueUpdate(id:\"ENG-123\", input:{ stateId:\"STATE_UUID\" }) { success issue { identifier state { name type } } } }"}' | python -m json.tool
```

### Assign issue

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { issueUpdate(id:\"ENG-123\", input:{ assigneeId:\"USER_UUID\" }) { success issue { identifier assignee { name } } } }"}' | python -m json.tool
```

### Set priority

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { issueUpdate(id:\"ENG-123\", input:{ priority:1 }) { success issue { identifier priority } } }"}' | python -m json.tool
```

### Add comment

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { commentCreate(input:{ issueId:\"ISSUE_UUID\", body:\"Root cause identified and fix in progress.\" }) { success comment { id body } } }"}' | python -m json.tool
```

### Set due date

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { issueUpdate(id:\"ENG-123\", input:{ dueDate:\"2026-04-20\" }) { success issue { identifier dueDate } } }"}' | python -m json.tool
```

## Practical Patterns

### Bug triage

1. Query team workflow states
2. Search for matching issues
3. Raise priority for user-facing regressions
4. Move urgent issues into a `started` state
5. Add a short triage comment with rationale

### Sprint planning

1. List backlog items for a team
2. Filter by priority or labels
3. Assign owners
4. Add due dates or attach to a project
5. Summarize remaining backlog risk

### Status cleanup

1. Find issues in `started`
2. Identify stale assignees or overdue items
3. Add follow-up comments
4. Move blocked or abandoned work out of `started`

## Pagination

Linear uses cursor pagination:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ issues(first:20) { nodes { identifier title } pageInfo { hasNextPage endCursor } } }"}' | python -m json.tool
```

Use the returned `endCursor` as `after:"CURSOR"` in the next request.

## MCP Fallback

If the user already has Linear MCP working, you can still use it for:

- fast natural-language listing and search
- team and project lookups
- small updates where raw GraphQL adds no value

Prefer API mode if:

- you need reproducible curl commands
- the MCP server is not available
- you need explicit control of fields and IDs
- you are debugging authentication or workflow-state issues

## Troubleshooting

- `Unauthorized` means the API key is missing or invalid
- HTTP 200 with GraphQL `errors` means the request shape is wrong
- unknown workflow status usually means you passed a name instead of `stateId`
- no search results may mean wrong team key or stale identifier
- if MCP is configured but failing on Windows, prefer API mode instead of blocking on WSL transport

## Notes

- This skill is intentionally API-first because it is more portable than MCP-only workflows
- If you later want parity with Hermes upstream provenance, map this skill to the Hermes Linear source rather than treating it as purely in-house
