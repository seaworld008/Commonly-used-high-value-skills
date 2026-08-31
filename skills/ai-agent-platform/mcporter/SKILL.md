---
name: mcporter
description: 'Use when a user explicitly needs terminal-based MCP discovery, schema inspection, authentication diagnostics, or scripted tool calls through mcporter; verify server trust, argument schemas, and mutation authority before execution.'
zh_description: "用于通过 mcporter CLI 列出、配置、鉴权和调用 MCP 服务器或工具。"
version: "1.0.2"
author: community
source: "github:NousResearch/hermes-agent"
source_url: "https://github.com/NousResearch/hermes-agent/blob/main/optional-skills/mcp/mcporter/SKILL.md"
license: MIT
tags: '[MCP, Tools, API, Integrations, Interop]'
created_at: "2026-04-13"
updated_at: "2026-08-31"
quality: 4
complexity: "intermediate"
platforms: '[linux, macos, windows]'
metadata:
  hermes:
    tags: [MCP, Tools, API, Integrations, Interop]
    homepage: https://mcporter.dev
prerequisites:
  commands: [npx]
---

# mcporter

Use `mcporter` to discover, call, and manage [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) servers and tools directly from the terminal.

## Prerequisites

Requires Node.js:
```bash
# No install needed (runs via npx)
npx mcporter list

# Or install globally
npm install -g mcporter
```

## Quick Start

```bash
# List MCP servers already configured on this machine
mcporter list

# List tools for a specific server with schema details
mcporter list <server> --schema

# Call a tool
mcporter call <server.tool> key=value
```

## Discovering MCP Servers

mcporter auto-discovers servers configured by other MCP clients (Claude Desktop, Cursor, etc.) on the machine. To find new servers to use, browse registries like [mcpfinder.dev](https://mcpfinder.dev) or [mcp.so](https://mcp.so), then connect ad-hoc:

```bash
# Connect to any MCP server by URL (no config needed)
mcporter list --http-url https://some-mcp-server.com --name my_server

# Or run a stdio server on the fly
mcporter list --stdio "npx -y @modelcontextprotocol/server-filesystem" --name fs
```

## Calling Tools

```bash
# Key=value syntax
mcporter call linear.list_issues team=ENG limit:5

# Function syntax
mcporter call "linear.create_issue(title: \"Bug fix needed\")"

# Ad-hoc HTTP server (no config needed)
mcporter call https://api.example.com/mcp.fetch url=https://example.com

# Ad-hoc stdio server
mcporter call --stdio "bun run ./server.ts" scrape url=https://example.com

# JSON payload
mcporter call <server.tool> --args '{"limit": 5}'

# Machine-readable output (recommended for Hermes)
mcporter call <server.tool> key=value --output json
```

## Auth and Config

```bash
# OAuth login for a server
mcporter auth <server | url> [--reset]

# Manage config
mcporter config list
mcporter config get <key>
mcporter config add <server>
mcporter config remove <server>
mcporter config import <path>
```

Config file location: `./config/mcporter.json` (override with `--config`).

## Daemon

For persistent server connections:
```bash
mcporter daemon start
mcporter daemon status
mcporter daemon stop
mcporter daemon restart
```

## Code Generation

```bash
# Generate a CLI wrapper for an MCP server
mcporter generate-cli --server <name>
mcporter generate-cli --command <url>

# Inspect a generated CLI
mcporter inspect-cli <path> [--json]

# Generate TypeScript types/client
mcporter emit-ts <server> --mode client
mcporter emit-ts <server> --mode types
```

## Notes

- Use `--output json` for structured output that's easier to parse
- Ad-hoc servers (HTTP URL or `--stdio` command) work without any config — useful for one-off calls
- OAuth auth may require interactive browser flow — use `terminal(command="mcporter auth <server>", pty=true)` if needed

<!-- LOCAL-CURATION-SUPPLEMENT:START -->
## Safe Terminal Workflow

Prefer an already connected native MCP tool when it meets the request. MCPorter
is useful for terminal automation, protocol diagnosis, and repeatable scripts;
it is not a reason to install another integration for an already supported task.
Tool names above are illustrative, not a promise that a server exports them.
Map the terminal example to the actual host's tool schema rather than assuming
a tool literally named `terminal` exists.

1. Identify the approved server and the configuration source that registered it.
2. Inspect configuration before connecting: discovery can launch a local stdio
   process, inherit credentials, or contact a remote system.
3. Confirm executable, package version, working directory, and allowed roots.
4. List the selected server's schema; do not guess tools or required arguments.
5. Choose one read-only operation with a bounded result to verify the connection.
6. Perform a mutation only when the user authorized its exact resource and scope.
7. Read back the changed object through a separate read operation when available.

## Common Patterns: Evidence Record

```text
server: approved configuration name and transport
configuration source: project, home, or explicitly reviewed import
operation: discovered tool name and read/write classification
arguments: schema-validated values with credentials redacted
result: protocol error state plus application result
verification: target resource read-back, or explicit unavailable status
```

Use `mcporter config list` to inspect configuration and
`mcporter list <server> --schema` for a selected, trusted server. Replace
`<server>` with an observed name, not a copied example. Review configuration
imports instead of assuming every server configured by another client is trusted.

## Acceptance and Recovery

- A zero shell exit status alone does not prove the tool succeeded; inspect MCP
  error content, `isError` when returned, and the application's result fields.
- Never retry a timed-out write blindly: it may already have committed. Read
  the resource or use a server-supported idempotency key before retrying.
- Do not put tokens in command-line arguments, screenshots, or saved evidence.
- Authentication, config changes, package execution, and daemon startup each
  require task scope; a request to inspect tools does not authorize all four.
- Keep ad-hoc discovery ephemeral; do not persist servers without authorization.
- Failure to connect is a blocker to report, not permission to weaken TLS checks,
  expand filesystem access, or choose a different account.

The primary [MCPorter documentation](https://github.com/steipete/mcporter)
defines current flags and import behavior. Check local `--help` for the installed
version before using examples in automation.
<!-- LOCAL-CURATION-SUPPLEMENT:END -->
