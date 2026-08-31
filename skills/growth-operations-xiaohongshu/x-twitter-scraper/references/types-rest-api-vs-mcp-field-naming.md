# Xquik REST and MCP response boundaries

Reviewed against the [official MCP contract](https://docs.xquik.com/mcp/overview)
on 2026-08-31. Do not derive MCP output types from default REST types.

| Meaning | Default REST example | Normalized MCP example |
| --- | --- | --- |
| Creation time | `createdAt` | `created` (Unix seconds, not `created_at`) |
| Next cursor | `nextCursor` | `next_cursor` |
| More pages | Endpoint-specific | `has_more` |
| Retry permission | `safeToRetry` | `safe_to_retry` |
| Write status location | `statusUrl` | `status_url` |

These examples are not a universal recursive key-renaming algorithm. Inspect
the actual operation's schema and response; nested objects may differ.
Preserve identifiers and cursors as opaque strings. Do not convert long IDs to
JavaScript numbers, infer missing fields, or treat a missing page as empty.

For MCP, discover `docs`, `search`, and `execute`. Inspect `spec.paths` with
`search`, then make bounded requests with `execute` and `xquik.request()`.
Keep the transport and schema version in exported results so consumers know
which field contract they received.
