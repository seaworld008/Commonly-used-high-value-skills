---
name: docs-cleaner
description: 'Consolidates redundant documentation while preserving all valuable content. This skill should be used when users want to clean up documentation bloat, merge redundant docs, reduce documentation sprawl, or consolidate multiple files covering the same topic. Triggers include "clean up docs", "consolidate documentation", "too many doc files", "merge these docs", or when documentation exceeds 500 lines across multiple files covering similar topics.'
zh_description: "用于合并冗余文档、减少文档膨胀，并在保留有效内容的前提下整理知识库。"
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["cleaner", "docs", "productivity"]'
created_at: "2026-03-04"
updated_at: "2026-06-29"
quality: 3
complexity: "intermediate"
---

# Documentation Cleaner

Consolidate redundant documentation while preserving 100% of valuable content.

## Core Principle

**Critical evaluation before deletion.** Never blindly delete. Analyze each section's unique value before proposing removal. The goal is reduction without information loss.

## Workflow

### Phase 1: Discovery

1. Identify all documentation files covering the topic
2. Count total lines across files
3. Map content overlap between documents

### Phase 2: Value Analysis

For each document, create a section-by-section analysis table:

| Section | Lines | Value | Reason |
|---------|-------|-------|--------|
| API Reference | 25 | Keep | Unique endpoint documentation |
| Setup Steps | 40 | Condense | Verbose but essential |
| Test Results | 30 | Delete | One-time record, not reference |

Value categories:
- **Keep**: Unique, essential, frequently referenced
- **Condense**: Valuable but verbose
- **Delete**: Duplicate, one-time, self-evident, outdated

See `references/value_analysis_template.md` for detailed criteria.

### Phase 3: Consolidation Plan

Propose target structure:

```
Before: 726 lines (3 files, high redundancy)
After:  ~100 lines (1 file + reference in CLAUDE.md)
Reduction: 86%
Value preserved: 100%
```

### Phase 4: Execution

1. Create consolidated document with all valuable content
2. Delete redundant source files
3. Update references (CLAUDE.md, README, imports)
4. Verify no broken links

## Value Preservation Checklist

Before finalizing, confirm preservation of:

- [ ] Essential procedures (setup, configuration)
- [ ] Key constraints and gotchas
- [ ] Troubleshooting guides
- [ ] Technical debt / roadmap items
- [ ] External links and references
- [ ] Debug tips and code snippets

## Anti-Patterns

| Pattern | Problem | Solution |
|---------|---------|----------|
| Blind deletion | Loses valuable information | Section-by-section analysis first |
| Keeping everything | No reduction achieved | Apply value criteria strictly |
| Multiple sources of truth | Future divergence | Single authoritative location |
| Orphaned references | Broken links | Update all references after consolidation |

## Output Artifacts

A successful cleanup produces:

1. **Consolidated document** - Single source of truth
2. **Value analysis** - Section-by-section justification
3. **Before/after metrics** - Lines reduced, value preserved
4. **Updated references** - CLAUDE.md or README with pointer to new location

## Decision Rules

Use deletion only when all of these are true:

- The content is duplicated elsewhere or no longer accurate.
- The replacement location is clear and linked.
- No active workflow, script, or contributor guide depends on the old path.
- The user can review the before/after structure.

Prefer consolidation when documents contain overlapping but non-identical procedures. Prefer archival when the content is historically useful but no longer operational. Prefer leaving content in place when ownership, accuracy, or downstream references are uncertain.

## Verification Commands

After cleanup, run project-appropriate checks:

```bash
rg "old-document-name|old/path" .
rg "TODO|TBD|placeholder" docs README.md
```

For documentation sites, also run the site build or link checker when available. Report both the reduction achieved and the content that was intentionally preserved.

## Review Notes

Documentation cleanup should be reversible until the user accepts the new structure. Prefer a small staged change when removing high-traffic docs: first add redirects or pointers, then remove duplicates after references are updated. If docs are generated, update the source template or generator instead of editing generated pages directly.

When the cleanup affects onboarding, run a quick reader test: can a new contributor still find setup, architecture, commands, troubleshooting, and ownership information within two clicks from the main README?
