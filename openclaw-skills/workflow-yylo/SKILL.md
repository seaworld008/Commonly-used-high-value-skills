---
name: workflow-yylo
description: 'Create and maintain validated YYLO Ledger workflow Records while keeping storage, execution, and run evidence as separate explicit boundaries.'
zh_description: "以 YYLO Ledger 工作流记录为中心：安全创建、校验与修订可执行工作流定义，并保持存储、执行与运行证据三类边界分离。"
version: "2.0.0"
author: yylo-dev
source: github:yylo-dev/yylo-skills
source_url: "https://github.com/yylo-dev/yylo-skills/tree/506edfd8d3fab524df2fdbc0bc739af876c95aa1/skills/workflow-yylo"
license: MIT
tags: '[yylo, workflow, validation, agent-automation, cli]'
created_at: "2026-09-11"
updated_at: "2026-09-11"
quality: 2
complexity: intermediate
---

# Use YYLO workflow Records

Treat Ledger as the source of truth for workflow identity, validated definition,
and revision history. Use `yy ledger` in a YYLO controller or `yylo-ledger`
standalone. Inspect `COMMAND workflow --help`; if the namespace is absent, do not
invent it or edit Ledger storage directly.

## Keep three boundaries distinct

1. **Ledger stores and validates workflow data.** It does not execute workflows.
2. **A separately selected YYLO runner executes reviewed workflow data.** Storage
   does not grant execution, network, mutation, release, or deployment authority.
3. **Artifact Records retain run evidence.** Do not overwrite the workflow
   definition with stdout, logs, model output, reports, or receipts.

The read-only Ledger host also has no workflow execution endpoint.

## Discover and inspect

```bash
yy ledger workflow search --text "release verification" --projection summary --limit 20 -f json
yy ledger workflow get RECORD_ID -f json
yy ledger workflow get RECORD_ID --raw
yy ledger workflow get RECORD_ID --validated
```

Prefer immutable IDs after discovery. Use bounded projections and explicit archive
scope. `--validated` emits normalized YAML only after schema validation.

## Author safe workflow data

A workflow v1 document requires a mapping with `schema_version: v1`, a non-empty
`workflow_id`, and a `steps` list whose step IDs are non-empty and unique.

```yaml
schema_version: v1
workflow_id: focused-validation
steps:
  - id: test
    command: ["npm", "test"]
```

Create through file/stdin transport:

```bash
yy ledger workflow create --title "Focused validation" --file workflow.yaml
```

Ledger rejects unsafe or non-portable YAML, including duplicate keys, aliases,
anchors, explicit tags, recursive structures, non-string mapping keys, implicit
date/time values, non-finite numbers, CRLF input, and unsupported values. Never
weaken validation by storing executable shell as an unvalidated substitute.

## Revise safely

Read the current revision and history, then follow the installed
`workflow update --help` compare-and-replace contract. Bind updates to the
expected revision and preimage/digests, validate the result, and read it back.
On drift, stop and reconcile instead of forcing. Archive is non-destructive.

Before execution, freeze the exact workflow Record ID, revision, payload digest,
runner identity, inputs, and granted authorities. After execution, store bounded
outputs under `artifact-yylo` with workflow/run provenance. An execution request
never implies merge, release, publication, deployment, or production authority.

## Complete request

$ARGUMENTS
