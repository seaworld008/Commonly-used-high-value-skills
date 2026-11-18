---
name: modern-web-guidance
description: 'Find and apply Google Chrome Modern Web Guidance for native HTML/CSS/JavaScript patterns, browser compatibility, accessibility and performance, or review legacy web patterns when modernization is requested.'
zh_description: "按需检索 Google 现代 Web 指南，选择原生 HTML/CSS/API，核对浏览器兼容性、回退、无障碍与性能。"
version: "1.0.0"
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

Use for a concrete web-platform choice: dialogs/popovers, responsive layout,
forms, animation, accessibility, browser APIs or Core Web Vitals. Also use for
an explicitly requested modernization audit of existing HTML/CSS/client JavaScript.
It complements browser verification tools; it does not control a browser.

Backend code, build configuration, copy edits and unrelated framework questions
do not require a web-platform search. Follow the user's selected framework and
browser support policy rather than expanding the task to every guide topic.

## Runner and version

Reviewed CLI: **modern-web-guidance 1.0.1**, requiring Node >=22.
This skill's local version is independent of the CLI and guidance corpus.
Use an existing compatible runner. If acquisition is necessary, reuse the
task's installation/network authorization and use a scoped, pinned invocation:

```bash
npx --yes modern-web-guidance@1.0.1 --version
npx --yes modern-web-guidance@1.0.1 --help
```

On Windows the executable may be `npx.cmd`. The command can download a package;
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
