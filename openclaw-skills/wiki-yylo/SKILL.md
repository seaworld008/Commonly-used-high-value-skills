---
name: wiki-yylo
description: 'Use YYLO Ledger wiki Records as durable project knowledge. Search before creating, classify information correctly, and make revision-safe Markdown updates without editing Ledger storage directly.'
zh_description: "把 YYLO Ledger wiki 记录当作持久项目知识：先检索后创建、按记录类型正确分类，并通过修订安全契约更新 Markdown。"
version: "2.0.0"
author: yylo-dev
source: github:yylo-dev/yylo-skills
source_url: "https://github.com/yylo-dev/yylo-skills/tree/506edfd8d3fab524df2fdbc0bc739af876c95aa1/skills/wiki-yylo"
license: MIT
tags: '[yylo, wiki, knowledge-management, markdown, cli]'
created_at: "2026-09-11"
updated_at: "2026-09-11"
quality: 3
complexity: intermediate
---

# Use YYLO wiki Records

Treat Ledger as the source of truth. Use `yy ledger` in a YYLO controller and
`yylo-ledger` in a standalone Ledger project. Inspect `COMMAND wiki --help` before
acting; if `wiki` is absent, the installed Ledger version does not expose native
Record commands and must not be bypassed with direct file edits.

## Choose the right record

Before writing, decide where the information belongs:

- **Wiki**: durable explanatory project or domain knowledge that future work must discover.
- **Task**: scoped requested work, status, dependencies, acceptance criteria, and completion evidence.
- **Workflow**: validated structured steps, not prose guidance.
- **Artifact**: generated evidence, reports, receipts, logs, model output, or binary payloads.
- **Source documentation**: documentation released and versioned with product code.

Do not put secrets, caches, session transcripts, temporary status, bulky generated
evidence, or owner-only operational receipts in a wiki.

## Quick reference: discover before creating

Use bounded summary searches first. Resolve records by immutable ID whenever one
is known; slugs and aliases are discovery conveniences, not replacement identity.

```bash
yy ledger wiki search --text "deployment policy" --projection summary --limit 20 -f json
yy ledger wiki get RECORD_ID -f json
yy ledger wiki get RECORD_ID --raw
```

Use `--scope archive|all` only when the request requires cold records. Request
`full` projection only when payload bytes are necessary.

## Create durable Markdown

Use a file or stdin for substantial or shell-sensitive content:

```bash
yy ledger wiki create --title "Service ownership" --file ownership.md
yy ledger wiki create --title "Incident notes" --file - < incident-notes.md
```

Choose a stable title, namespace, slug, aliases, and relations deliberately. Keep
one topic per Record and link related immutable Record IDs rather than duplicating
truth.

## Update safely

1. Read the current Record and revision.
2. Preserve its immutable ID and inspect history when intent is unclear.
3. Follow `wiki update --help` for the installed compare-and-replace controls.
4. Supply the expected revision and required preimage/digest evidence.
5. Use file transport; do not rewrite Ledger files yourself.
6. Read back the resulting revision and receipt.

A revision or preimage mismatch means the source changed: reread and reconcile.
Never force past concurrent edits. Archive is a lifecycle transition, not delete.

Use `--front-matter` only for canonical front-matter interchange and `--rendered`
for inert, HTML-escaped rendering. Use `history RECORD_ID` to understand revisions;
do not infer history from the latest payload alone.

## Project wiki boundary

Portable controller guidance may live under the controller wiki, while project
and domain pages retain project-owned paths. Package-managed and project-owned
pages can coexist. Migration, runtime replacement, exceptional merge recovery,
release, deployment, and cold-archive maintenance remain authoritative runbooks,
not content to summarize into an everyday global skill.

## Complete request

$ARGUMENTS
