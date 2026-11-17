---
name: transcript-fixer
description: 'Correct speech-recognition errors, homophones, and mixed Chinese/English terminology in transcripts while preserving source meaning and speaker attribution.'
zh_description: "修正语音识别错误、同音词和中英文混合术语。"
version: "1.0.3"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["fixer", "transcript"]'
created_at: "2026-03-04"
updated_at: "2026-11-18"
quality: 4
complexity: "intermediate"
---

# Transcript Fixer

Correct speech-to-text transcription errors through dictionary-based rules, AI-powered corrections, and automatic pattern detection. Maintain a reusable correction dictionary only when persistence is explicitly in scope.

## When to Use This Skill

- Correcting ASR/STT errors in meeting notes, lectures, or interviews
- Building domain-specific correction dictionaries
- Fixing Chinese/English homophone errors or technical terminology
- Collaborating on shared correction knowledge bases

## Prerequisites

Use an available Python environment that satisfies the scripts' dependencies; `uv` is one option. Install tools only within existing task authorization. Keep original transcripts unchanged and write corrections to the requested output path.

Run commands from this skill's root. `requirements.txt` and the enhanced uv wrapper share `httpx>=0.24.0` and `filelock>=3.13.0`; HTTP/2 is an optional optimization, so the provider implementation must also work without h2. Dependency declarations alone do not verify actual client construction or provider availability. Reuse existing setup authorization and environment.

## Quick Start

For a one-off correction, inspect the supplied transcript and apply source-supported terminology fixes to a separate output. Mark uncertain substitutions rather than inventing meaning or speaker identities. Review the diff against the original.

### Current CLI Boundaries

- The enhanced wrapper reads only an explicitly supplied process `GLM_API_KEY`; it does not search shell startup files or unrelated credentials. Missing credentials are a configuration gap, not permission to search login files.
- The wrapper does not open a browser by default. Use `--auto-open` only when browser opening is requested and permitted. It does not create the diff itself.
- Learning is disabled by default. Persistence and automatic approval are separately gated by `enable_learning` and `enable_auto_approval`; enable them only within authorized dictionary maintenance. With learning disabled, an existing dictionary is read through a private snapshot, without writing global WAL sidecars.
- `--review-learned` and `--approve` are placeholder handlers that print "not yet implemented". They do not review or approve suggestions.
- Stage 3 only prints a diff-generation hint. It does not create `*_对比.html`.

### Explicit Dictionary Maintenance

Only when initializing or updating the configured persistent dictionary is authorized:

```bash
uv run scripts/fix_transcription.py --init
uv run scripts/fix_transcription.py --add "错误词" "正确词" --domain general
```

AI processing uses `--input meeting.md --stage 2` (or `3`) within the authorized provider/data-sharing scope. It does not require global learning authorization: learning is off by default, and only separately enabled, approved reusable corrections enter the configured dictionary.

**Actual processing outputs**:
- `*_stage1.md`: dictionary corrections for every stage (1, 2, or 3).
- `*_stage2.md`: AI-processed text when the AI stage completes; verify against source.
- HTML diff: a separate explicit operation, not a guaranteed pipeline output.

**Generate word-level diff** from the source and corrected file:

```bash
uv run scripts/generate_word_diff.py original.md corrected.md output.html
```

This creates an HTML comparison for review. Open it only when browser access is allowed and requested; its existence does not prove that proposed corrections are accurate.

## Example Session

**Input transcript** (`meeting.md`):
```
今天我们讨论了巨升智能的最新进展。
股价系统需要优化，目前性能不够好。
```

**After Stage 1** (`meeting_stage1.md`):
```
今天我们讨论了具身智能的最新进展。  ← "巨升"→"具身" corrected
股价系统需要优化,目前性能不够好。  ← Unchanged (not in dictionary)
```

**After Stage 2** (`meeting_stage2.md`):
```
今天我们讨论了具身智能的最新进展。
框架系统需要优化，目前性能不够好。  ← "股价"→"框架" corrected by AI
```

**Review candidate (illustrative, not an executed learning result):**

`股价` → `框架` may fit the surrounding technical context. Confirm it against the original audio/context before accepting; do not persist a context-specific substitution automatically.

## Core Workflow

1. Preserve the original transcript and identify the authorized correction/output scope.
2. Apply dictionary or contextual corrections with uncertainty markers and speaker attribution intact.
3. Review decisions, names, numbers and changed wording against the source.
4. Explicitly generate the word-level diff when needed.
5. Persist only approved reusable corrections in an authorized store. Use the selected configuration/dictionary directory; the learner checks learning and auto-approval independently and defaults to review-only behavior.

**CLI stages**: 1 = dictionary; 2 = dictionary then AI; 3 = both plus a printed diff hint. Pass the original transcript directly, including for Stage 2. Stages do not implement a complete approval workflow.
**Domains**: `general`, `embodied_ai`, `finance`, `medical`; the core CLI also accepts user-selected valid domain names, while the wrapper restricts choices to these four.

See `references/workflow_guide.md` for detailed workflows, `references/script_parameters.md` for complete CLI reference, and `references/team_collaboration.md` for collaboration patterns.

## Critical Workflow: Dictionary Iteration

Correction does not authorize global learning. Save only user-approved, reusable corrections when dictionary maintenance is in scope; otherwise return review-only suggestions. For authorized dictionary additions:
```bash
uv run scripts/fix_transcription.py --add "错误词" "正确词" --domain general
```

See `references/iteration_workflow.md` for complete iteration guide with checklist.

## AI Fallback Strategy

When GLM API is unavailable, inspect the failure exit status and this run's output manifest. There is no guaranteed host-specific fallback marker. Missing credentials and provider failures return 1; argument-parser errors can return 2. A failed AI stage may leave a completed Stage 1, which is partial delivery.

The current host can then:
1. Analyze the supplied text for ASR errors.
2. Correct within the authorized output scope using available tools.
3. Return uncertain/reusable candidates for review; persist only approved corrections when authorized.

## Database Operations

**MUST read `references/database_schema.md` before any database operations.**

Quick reference:
```bash
# View all corrections
sqlite3 ~/.transcript-fixer/corrections.db "SELECT * FROM active_corrections;"

# Check schema version
sqlite3 ~/.transcript-fixer/corrections.db "SELECT value FROM system_config WHERE key='schema_version';"
```

## Stages

| Stage | Description | Speed | Cost |
|-------|-------------|-------|------|
| 1 | Dictionary only | Instant | Free |
| 2 | Dictionary then AI | Provider-dependent | API calls |
| 3 | Same as 2, plus diff hint | Provider-dependent | API calls |

## Bundled Resources

**Scripts:**
- `scripts/ensure_deps.py` - Optional standalone environment installer
- `scripts/fix_transcript_enhanced.py` - Wrapper using explicit environment credentials and a private current-run output manifest; browser opening is opt-in
- `scripts/fix_transcription.py` - Core CLI (for automation); `TRANSCRIPT_FIXER_OUTPUT_MANIFEST` can select a private JSON receipt path with an `outputs` list
- `scripts/generate_word_diff.py` - Generate word-level diff HTML for reviewing corrections
- `scripts/examples/bulk_import.py` - Bulk import example

**References** (load as needed):
- **Critical**: `database_schema.md` (read before DB operations), `iteration_workflow.md` (dictionary iteration best practices)
- Getting started: `installation_setup.md`, `glm_api_setup.md`, `workflow_guide.md`
- Daily use: `quick_reference.md`, `script_parameters.md`, `dictionary_guide.md`
- Advanced: `sql_queries.md`, `file_formats.md`, `architecture.md`, `best_practices.md`
- Operations: `troubleshooting.md`, `team_collaboration.md`

## Troubleshooting

Verify setup health with `uv run scripts/fix_transcription.py --validate`. Common issues:
- Missing database → Initialize only when persistent dictionary setup is authorized; otherwise continue direct correction
- Missing API key → Safely inject the process environment; check presence only using the Python process-internal check in `references/glm_api_setup.md`, including under shell xtrace
- Permission errors → Check the selected dictionary path and ownership

Validation targets `config.database.path`: `TRANSCRIPT_FIXER_DB_PATH`, otherwise `TRANSCRIPT_FIXER_CONFIG_DIR/corrections.db` (default directory `~/.transcript-fixer`). It never initializes, migrates, or writes the user database/sidecars. Missing or invalid databases/tables return 1. Quiescent files without sidecars are checked through a private immutable snapshot; source changes or WAL/SHM/journal sidecars return 1 as explicitly not verified. Do not delete sidecars to bypass this boundary; provide a quiescent consistent copy without active journals within authorized maintenance. Structural validation does not prove provider availability or semantic accuracy.

See `references/troubleshooting.md` for detailed error resolution and `references/glm_api_setup.md` for API configuration.
