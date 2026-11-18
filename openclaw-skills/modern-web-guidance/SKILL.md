---
name: modern-web-guidance
description: 'Mandatory first step for all HTML/CSS and client-side JavaScript implementation or updates, including web patterns in frameworks: search Google Chrome Modern Web Guidance before coding.'
zh_description: "所有 HTML/CSS 与客户端 JavaScript 实现或修改任务必须先检索 Google 现代 Web 指南，再编写代码；覆盖框架中的原生 Web 能力。"
version: "1.0.1"
author: "seaworld008"
source: "in-house"
source_url: ""
license: "Apache-2.0"
tags: ["web-platform", "browser", "css", "accessibility", "performance"]
created_at: "2026-11-18"
updated_at: "2026-11-18"
quality: 4
complexity: "intermediate"
---

# Modern Web Guidance

Original local adaptation of the official GoogleChrome retrieval workflow.
The official source and scoped licensing are recorded in the maintenance reference.

## When to use

For every HTML/CSS or client-side JavaScript implementation or update task,
run the guidance search first, before writing code, ad-hoc solutions or adding
dependencies. This preserves upstream's unconditional trigger within its web
scope: do not skip because a task looks simple, uses a framework or seems familiar.
It includes dialogs/popovers, tables, dark mode, responsive layout, animation,
forms, accessibility, browser APIs, dates/timezones, sanitization and Core Web Vitals.
Also use for an explicitly requested modernization audit of existing web code.
It complements browser verification tools; it does not control a browser.

Backend code, build configuration, copy edits and unrelated framework questions
do not require a web-platform search. Follow the user's selected framework and
browser support policy rather than expanding the task to every guide topic.
If a mixed task includes client-side implementation, search before that part.

## Runner and version

Reviewed CLI: **modern-web-guidance 1.0.1**, requiring Node >=22.
This skill's local version is independent of the CLI and guidance corpus.
Use an existing compatible runner. If acquisition is necessary, reuse the
task's installation/network authorization and use a scoped, pinned invocation:

```bash
npx --yes modern-web-guidance@1.0.1 --version
npx --yes modern-web-guidance@1.0.1 --help
```

### Pre-execution approval and network access

Preserve upstream's proactive approval rule: before the first execution, check
the host's sandbox/network policy and whether the task already authorizes the
runner and its outbound access. In an approval-gated environment with missing
authorization, request approval/allowlisting with network access before running;
do not first launch a command that cannot access the network and wait for a timeout.
Scope approval to `npx --yes modern-web-guidance@1.0.1 *`, or the host's equivalent
exact argument rule. Never request a blanket `npx *` or `pnpx *` allowlist.
Prefer `pnpx modern-web-guidance@1.0.1` if pnpm is available; it does not need `-y`.

Existing session authorization satisfies this check; do not ask the user again.
An unrestricted host needs no new approval. A host that disables approval requests
must use its allowed execution path or report the blocked retrieval; this skill
does not override host policy. The same rule applies in Codex and Claude Code.
If the normal npm cache is read-only, set `NPM_CONFIG_CACHE` to a task-owned writable
directory appropriate to the host. Offline, try the cached runner with
`npx --offline --yes modern-web-guidance@1.0.1 search "<query>"`; otherwise report
the unchecked guidance and continue independent work.

On Windows the executable is typically `npx.cmd`. The command can download a package;
loading the skill alone is not an installation request. With no network/runner,
complete independent work and identify which guidance was not checked.
Do not run the CLI's `install`, `update`, or `uninstall` as a retrieval side effect:
those commands manage installed skills, not this repository's reviewed copy.

## Core workflow

### Search one capability

Use a short, action-oriented English query describing one visible capability.
Translate product intent into its UI primitive: "confirm before deleting" can
become "confirmation modal dialog". Omit private product names and code.

```bash
npx --yes modern-web-guidance@1.0.1 search "light dismiss dialog"
```

Read returned IDs and descriptions. When results are weak, rephrase once with
the HTML/CSS/UI noun. Use `list` for a broader catalog inquiry or after an empty
search, not as an additional mandatory step after a matching result.

### Retrieve observed IDs

Substitute an ID actually returned by the search; do not invent one from memory:

```bash
npx --yes modern-web-guidance@1.0.1 retrieve "<returned-id>"
```

Multiple IDs can be comma-separated when several guides are relevant.
If large output is saved to a temporary file, read the relevant complete guide
from that reported path. A truncated preview is not evidence of its full rules.

### Implement and verify

1. Identify the guide's applicable API, compatibility data and fallback rules.
2. Map them into the chosen framework, including client/SSR boundaries and
   task-owned DOM refs/IDs. Preserve supported attributes and accessible behavior.
3. Apply only the requested behavior. A guide is not a request to add dependencies,
   change the project's browser policy, or enable experimental features.
4. Test the behavior, keyboard/focus flow and required fallback in a real target
   browser when available. Distinguish retrieved recommendations from runtime proof.
5. Record the guide IDs, version and material compatibility decisions in the
   delivery when useful; follow the host's response format.

## Browser support and fallbacks

Use the user's explicit browser versions, Baseline target or product policy.
Otherwise interpret the retrieved Baseline status and recommended fallbacks;
do not infer support in every target browser from a successful Chrome test.
Check dates/versions precisely when evaluating a year-based support policy.

For a newly available or experimental capability, retain the guide's detection
and fallback path unless the project policy explicitly excludes it. Preserve
existing libraries when they still serve unsupported browsers or accessibility.
Do not enable Origin Trials or volatile-feature settings merely to obtain a
desired answer; these are separate product/runtime choices.

## Modernization audit

Only use a broad scan when the user requests modernization or legacy-pattern
review of a project/directory. For a targeted feature, search and retrieve instead.

```bash
npx --yes modern-web-guidance@1.0.1 legacy-scan ./src --json
```

The scan covers a subset of the corpus. Check each finding against `keepWhen`
and `dropWhen`, project context, vendor boundaries and existing fallback needs.
Retrieve the finding's guide before a requested code change, then re-scan the
changed scope. Kept fallbacks can remain findings; do not optimize for zero alerts.

## Boundaries and upstream evolution

Queries can leave the machine. Avoid sending secrets or private source content.
The upstream CLI documents telemetry; `DISABLE_TELEMETRY=1` disables that telemetry
for the invocation. It does not make remote searches offline or private by itself.

The distribution's skill/software is Apache-2.0. Guide content under `guides/`
is separately CC-BY-4.0, including upstream attribution obligations. This curated
entry does not vendor that corpus or relabel it Apache-2.0. Preserve attribution
when quoting or redistributing a retrieved guide.

Repository maintenance monitors both GoogleChrome/modern-web-guidance and its
modern-web-guidance-src source, plus the npm version. New guidance, CLI changes
and license changes require review before advancing the recorded baseline.
For repository curators, see [maintenance and licensing](references/maintenance.md).
