---
name: codebase-inspection
description: 'Use when a user needs reproducible repository sizing, language composition, file counts, or code-versus-comment ratios with pygount; record exclusions and verify measurement scope before interpreting results.'
zh_description: "用于用 pygount 检查代码行数、语言构成、仓库规模和代码/注释比例。"
version: "1.0.1"
author: Hermes Agent
source: "github:NousResearch/hermes-agent"
source_url: "https://github.com/NousResearch/hermes-agent/blob/main/skills/software-development/codebase-inspection/SKILL.md"
license: MIT
tags: '[LOC, Code Analysis, pygount, Codebase, Metrics, Repository]'
created_at: "2026-04-13"
updated_at: "2026-08-31"
quality: 4
complexity: "intermediate"
platforms: '[linux, macos, windows]'
metadata:
  hermes:
    tags: [LOC, Code Analysis, pygount, Codebase, Metrics, Repository]
    related_skills: [github-repo-management]
prerequisites:
  commands: [pygount]
---

# Codebase Inspection with pygount

Analyze repositories for lines of code, language breakdown, file counts, and code-vs-comment ratios using `pygount`.

## When to Use

- User asks for LOC (lines of code) count
- User wants a language breakdown of a repo
- User asks about codebase size or composition
- User wants code-vs-comment ratios
- General "how big is this repo" questions

## Prerequisites

```bash
python3 -m venv /path/to/approved-tools/pygount-venv
/path/to/approved-tools/pygount-venv/bin/python -m pip install pygount
/path/to/approved-tools/pygount-venv/bin/pygount --version
```

Choose a new, approved environment path; do not overwrite an existing environment
or bypass externally managed Python protections. Use its `pygount` executable
in the examples below, or activate that environment first.

## 1. Basic Summary (Most Common)

Get a full language breakdown with file counts, code lines, and comment lines:

```bash
cd /path/to/repo
pygount --format=summary \
  --folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,.eggs,*.egg-info" \
  .
```

**IMPORTANT:** Always use `--folders-to-skip` to exclude dependency/build directories, otherwise pygount will crawl them and take a very long time or hang.

## 2. Common Folder Exclusions

Adjust based on the project type:

```bash
# Python projects
--folders-to-skip=".git,venv,.venv,__pycache__,.cache,dist,build,.tox,.eggs,.mypy_cache"

# JavaScript/TypeScript projects
--folders-to-skip=".git,node_modules,dist,build,.next,.cache,.turbo,coverage"

# General catch-all
--folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,vendor,third_party"
```

## 3. Filter by Specific Language

```bash
# Only count Python files
pygount --suffix=py --format=summary .

# Only count Python and YAML
pygount --suffix=py,yaml,yml --format=summary .
```

## 4. Detailed File-by-File Output

```bash
# Default format shows per-file breakdown
pygount --folders-to-skip=".git,node_modules,venv" .

# Sort by code lines (pipe through sort)
pygount --folders-to-skip=".git,node_modules,venv" . | sort -t$'\t' -k1 -nr | head -20
```

## 5. Output Formats

```bash
# Summary table (default recommendation)
pygount --format=summary .

# JSON output for programmatic use
pygount --format=json .

# Pipe-friendly: Language, file count, code, docs, empty, string
pygount --format=summary . 2>/dev/null
```

## 6. Interpreting Results

The summary table columns:
- **Language** — detected programming language
- **Files** — number of files of that language
- **Code** — lines of actual code (executable/declarative)
- **Comment** — lines that are comments or documentation
- **%** — percentage of total

Special pseudo-languages:
- `__empty__` — empty files
- `__binary__` — binary files (images, compiled, etc.)
- `__generated__` — auto-generated files (detected heuristically)
- `__duplicate__` — files with identical content
- `__unknown__` — unrecognized file types

## Pitfalls

1. **Always exclude .git, node_modules, venv** — without `--folders-to-skip`, pygount will crawl everything and may take minutes or hang on large dependency trees.
2. **Markup classification varies** — do not assume all Markdown is counted as comments. Inspect the installed version's output and lexer behavior.
3. **Logical versus physical lines** — pygount classification and `wc -l` measure different things. Label physical-line counts separately instead of treating them as a correction.
4. **Large monorepos** — for very large repos, consider using `--suffix` to target specific languages rather than scanning everything.

<!-- LOCAL-CURATION-SUPPLEMENT:START -->
## Measurement Contract

Before scanning, agree on the repository root and the population being measured.
A language summary over application code is not comparable to a summary that
also includes generated exports, vendored libraries, test fixtures, and caches.
Record whether tests and documentation belong in the requested population.
Explicit folder patterns replace pygount defaults; include `[...]` when you want
to extend its defaults, then add project-specific exclusions.

## Common Patterns: Comparable Snapshots

```text
revision: full commit SHA, or explicitly identified dirty checkout
tool: pygount version
scope: absolute root and included subdirectories
exclusions: exact folder and filename patterns
duplicate policy: default deduplication or explicit --duplicates
outputs: summary plus JSON, stored outside the measured tree
errors: unknown, binary, generated, duplicate and error file counts
```

Compare snapshots only when these settings agree. If the tree is dirty, report
that fact without stashing, discarding, or committing the user's changes.
Use JSON for downstream parsing: human-readable summary column widths vary.
Inspect a few representative files, including a generated file and a duplicate,
before using totals to justify a migration or capacity decision.

## Acceptance and Boundaries

- The command exits successfully and the output describes the intended root.
- Excluded dependencies are absent from the detailed file listing.
- Parse errors and unknown languages are reported, not silently folded into zero.
- Code-to-comment ratios state their denominator and treatment of empty lines.
- Two scans of an unchanged tree with identical settings yield identical counts.
- A file count or LOC change is not evidence of quality, risk, or productivity.
- Analysis is read-only; do not run repository code or upload private source.

Command semantics were checked against the primary
[pygount usage documentation](https://github.com/roskakori/pygount/blob/main/docs/usage.md).
Recheck installed help before relying on new flags.
<!-- LOCAL-CURATION-SUPPLEMENT:END -->
