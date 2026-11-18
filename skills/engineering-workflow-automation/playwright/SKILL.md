---
name: playwright
description: 'Use when the task requires automating a real browser from the terminal (navigation, form filling, snapshots, screenshots, data extraction, UI-flow debugging) via `playwright-cli` or the bundled wrapper script.'
zh_description: "需要在终端用 playwright-cli 自动化真实浏览器时使用：页面导航、表单填写、快照截图、数据提取和界面流程调试。"
version: "1.0.3"
author: "OpenAI contributors; local curators"
source: "https://github.com/openai/skills"
source_url: "https://github.com/openai/skills/blob/49f948faa9258a0c61caceaf225e179651397431/skills/.curated/playwright/SKILL.md"
license: "Apache-2.0"
tags: '["automation", "playwright", "workflow"]'
created_at: "2026-03-04"
updated_at: "2026-11-18"
quality: 4
complexity: "intermediate"
---

# Playwright CLI Skill

Drive a real browser using an already available, supported `playwright-cli` or
host browser capability. Match the commands and documentation to that version.
Treat this skill as CLI-first automation. Do not pivot to `@playwright/test` unless the user explicitly asks for test files.

## Capability Discovery

`@playwright/cli` and `@playwright/mcp` are different packages and interfaces.
The reviewed Playwright MCP release is 0.0.85; it does not establish the CLI's
version or command support. Native Browser/Chrome plugins use their host's
current tools and lifecycle documentation. Keep refs and session handles within
the chosen backend instead of translating them by name.

Check the project's installed CLI and the host's browser tools before choosing
an execution path. Missing `npx` alone is not a reason to stop all work. If a
dependency must be acquired, reuse existing installation authorization, choose
a compatible fixed version and an isolated local runner; do not install globally
as a loading side effect. Without browser capability, complete independent static
work and state which browser acceptance checks were not run.

## Skill path (set once)

```bash
PWCLI="/absolute/path/to/verified/installed/playwright-cli"
```

Resolve `PWCLI` from the selected installed CLI; keep host environment variables
unchanged. Resolve any bundled helper from the actual loaded skill directory.

## Quick start

Use the verified installed CLI selected above:

```bash
"$PWCLI" open https://playwright.dev --headed
"$PWCLI" snapshot
"$PWCLI" click e15
"$PWCLI" type "Playwright"
"$PWCLI" press Enter
"$PWCLI" screenshot
```

Use only commands supported by that CLI version. Installation, if necessary,
is a separate scoped dependency change under existing authorization.

## Core workflow

1. Open the page.
2. Snapshot to get stable element refs.
3. Interact using refs from the latest snapshot.
4. Re-snapshot after navigation or significant DOM changes.
5. Capture artifacts (screenshot, pdf, traces) when useful.

Minimal loop:

```bash
"$PWCLI" open https://example.com
"$PWCLI" snapshot
"$PWCLI" click e3
"$PWCLI" snapshot
```

## When to snapshot again

Snapshot again after:

- navigation
- clicking elements that change the UI substantially
- opening/closing modals or menus
- tab switches

Refs can go stale. When a command fails due to a missing ref, snapshot again.

## Recommended patterns

### Form fill and submit

```bash
"$PWCLI" open https://example.com/form
"$PWCLI" snapshot
"$PWCLI" fill e1 "user@example.com"
"$PWCLI" fill e2 "password123"
"$PWCLI" click e3
"$PWCLI" snapshot
```

### Debug a UI flow with traces

```bash
"$PWCLI" open https://example.com --headed
"$PWCLI" tracing-start
# ...interactions...
"$PWCLI" tracing-stop
```

### Multi-tab work

```bash
"$PWCLI" tab-new https://example.com
"$PWCLI" tab-list
"$PWCLI" tab-select 0
"$PWCLI" snapshot
```

## Wrapper script

The bundled `scripts/playwright_cli.sh` actually executes
`npx --yes --package @playwright/cli playwright-cli`: it may download an unpinned
package even for `--help`. It preserves explicit `--session` or injects
`PLAYWRIGHT_CLI_SESSION`, but does not enforce a fixed dependency version.
Use an existing verified CLI directly; use a separately pinned local invocation
only when acquisition is authorized. Do not treat the wrapper as an offline or
version-locked runner. For the selected CLI:

```bash
"$PWCLI" --help
```

Keep the session and fresh-snapshot loop with the selected supported runner.

## References

Open only what you need:

- CLI command reference: `references/cli.md`
- Practical workflows and troubleshooting: `references/workflows.md`

## Guardrails

- Always snapshot before referencing element ids like `e12`.
- Re-snapshot when refs seem stale.
- Prefer explicit commands over `eval` and `run-code` unless needed.
- When you do not have a fresh snapshot, use placeholder refs like `eX` and say why; do not bypass refs with `run-code`.
- Use `--headed` when a visual check will help.
- When capturing artifacts in this repo, use `output/playwright/` and avoid introducing new top-level artifact folders.
- Default to CLI commands and workflows, not Playwright test specs.
