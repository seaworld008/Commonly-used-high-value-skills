# Storage Format Reference

Current runtime boundaries: use selected `config.database.path` (`TRANSCRIPT_FIXER_DB_PATH`, otherwise `TRANSCRIPT_FIXER_CONFIG_DIR/corrections.db`, default directory `~/.transcript-fixer`). Default SQL paths below are illustrative. Commands run from the skill root; reuse authorized setup. Repository construction can initialize schema/WAL, so API/SQL management examples are not zero-write checks. `--validate` reads a private snapshot without active journals, reports missing tables or unverified active journal sidecars, and never repairs user state.

Learning/auto-approval default off independently of legacy schema settings. Core CLI has no import/export options; use reviewed Service API examples below only for authorized maintenance. Review/approval CLI handlers are placeholders. Stage 2 includes dictionary processing and produces `*_stage1.md` plus `*_stage2.md`; Stage 3 only prints a hint. HTML is generated explicitly by `scripts/generate_word_diff.py original.md corrected.md output.html`, with browser opening off by default.

This document describes the SQLite database format used by transcript-fixer v2.0.

## Table of Contents

- [Database Location](#database-location)
- [Database Schema](#database-schema)
  - [Core Tables](#core-tables)
  - [Views](#views)
- [Querying the Database](#querying-the-database)
  - [Using Python API](#using-python-api)
  - [Using SQLite CLI](#using-sqlite-cli)
- [Import/Export](#importexport)
  - [Export to JSON](#export-to-json)
  - [Import from JSON](#import-from-json)
- [Backup Strategy](#backup-strategy)
  - [Automatic Backups](#automatic-backups)
  - [Manual Backups](#manual-backups)
  - [Version Control](#version-control)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
  - [Database Locked](#database-locked)
  - [Corrupted Database](#corrupted-database)
  - [Missing Tables](#missing-tables)

## Database Location

**Path**: `~/.transcript-fixer/corrections.db`

**Type**: SQLite 3 database with ACID guarantees

## Database Schema

### Core Tables

#### corrections

Main correction dictionary storage.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| from_text | TEXT | NOT NULL | Original (incorrect) text |
| to_text | TEXT | NOT NULL | Corrected text |
| domain | TEXT | DEFAULT 'general' | Correction domain |
| source | TEXT | CHECK IN ('manual', 'learned', 'imported') | Origin of correction |
| confidence | REAL | CHECK 0.0-1.0 | Confidence score |
| added_by | TEXT | | User who added |
| added_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When added |
| usage_count | INTEGER | DEFAULT 0, CHECK >= 0 | Times used |
| last_used | TIMESTAMP | | Last usage time |
| notes | TEXT | | Optional notes |
| is_active | BOOLEAN | DEFAULT 1 | Soft delete flag |

**Unique Constraint**: `(from_text, domain)`

**Indexes**: domain, source, added_at, is_active, from_text

#### context_rules

Regex-based context-aware correction rules.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| pattern | TEXT | NOT NULL, UNIQUE | Regex pattern |
| replacement | TEXT | NOT NULL | Replacement text |
| description | TEXT | | Rule explanation |
| priority | INTEGER | DEFAULT 0 | Higher = applied first |
| is_active | BOOLEAN | DEFAULT 1 | Enable/disable |
| added_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When added |
| added_by | TEXT | | User who added |

**Indexes**: priority (DESC), is_active

#### correction_history

Audit log for all correction runs.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| filename | TEXT | NOT NULL | File corrected |
| domain | TEXT | NOT NULL | Domain used |
| run_timestamp | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When run |
| original_length | INTEGER | CHECK >= 0 | Original file size |
| stage1_changes | INTEGER | CHECK >= 0 | Dictionary changes |
| stage2_changes | INTEGER | CHECK >= 0 | AI changes |
| model | TEXT | | AI model used |
| execution_time_ms | INTEGER | | Runtime in ms |
| success | BOOLEAN | DEFAULT 1 | Success flag |
| error_message | TEXT | | Error if failed |

**Indexes**: run_timestamp (DESC), domain, success

#### correction_changes

Detailed changes made in each run.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| history_id | INTEGER | FOREIGN KEY → correction_history | Parent run |
| line_number | INTEGER | | Line in file |
| from_text | TEXT | NOT NULL | Original text |
| to_text | TEXT | NOT NULL | Corrected text |
| rule_type | TEXT | CHECK IN ('context', 'dictionary', 'ai') | Rule type |
| rule_id | INTEGER | | Reference to rule |
| context_before | TEXT | | Text before |
| context_after | TEXT | | Text after |

**Foreign Key**: history_id → correction_history.id (CASCADE DELETE)

**Indexes**: history_id, rule_type

#### learned_suggestions

AI-detected patterns pending review.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| from_text | TEXT | NOT NULL | Pattern detected |
| to_text | TEXT | NOT NULL | Suggested correction |
| domain | TEXT | DEFAULT 'general' | Domain |
| frequency | INTEGER | CHECK > 0 | Times seen |
| confidence | REAL | CHECK 0.0-1.0 | Confidence score |
| first_seen | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | First occurrence |
| last_seen | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last occurrence |
| status | TEXT | CHECK IN ('pending', 'approved', 'rejected') | Review status |
| reviewed_at | TIMESTAMP | | When reviewed |
| reviewed_by | TEXT | | Who reviewed |

**Unique Constraint**: `(from_text, to_text, domain)`

**Indexes**: status, domain, confidence (DESC), frequency (DESC)

#### suggestion_examples

Example occurrences of learned patterns.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| suggestion_id | INTEGER | FOREIGN KEY → learned_suggestions | Parent suggestion |
| filename | TEXT | NOT NULL | File where found |
| line_number | INTEGER | | Line number |
| context | TEXT | NOT NULL | Surrounding text |
| occurred_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When found |

**Foreign Key**: suggestion_id → learned_suggestions.id (CASCADE DELETE)

**Index**: suggestion_id

#### system_config

System configuration key-value store.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| key | TEXT | PRIMARY KEY | Config key |
| value | TEXT | NOT NULL | Config value |
| value_type | TEXT | CHECK IN ('string', 'int', 'float', 'boolean', 'json') | Value type |
| description | TEXT | | Config description |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update |

**Default Values**:
- `schema_version`: "2.0"
- `api_provider`: "GLM"
- `api_model`: "GLM-4.6"
- `default_domain`: "general"
- `auto_learn_enabled`: "true"
- `learning_frequency_threshold`: "3"
- `learning_confidence_threshold`: "0.8"

#### audit_log

Comprehensive audit trail for all operations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| timestamp | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When occurred |
| action | TEXT | NOT NULL | Action type |
| entity_type | TEXT | NOT NULL | Entity affected |
| entity_id | INTEGER | | Entity ID |
| user | TEXT | | User who performed |
| details | TEXT | | Action details |
| success | BOOLEAN | DEFAULT 1 | Success flag |
| error_message | TEXT | | Error if failed |

**Indexes**: timestamp (DESC), action, entity_type, success

### Views

#### active_corrections

Quick access to active corrections.

```sql
SELECT id, from_text, to_text, domain, source, confidence, usage_count, last_used, added_at
FROM corrections
WHERE is_active = 1
ORDER BY domain, from_text;
```

#### pending_suggestions

Suggestions pending review with example count.

```sql
SELECT s.id, s.from_text, s.to_text, s.domain, s.frequency, s.confidence,
       s.first_seen, s.last_seen, COUNT(e.id) as example_count
FROM learned_suggestions s
LEFT JOIN suggestion_examples e ON s.id = e.suggestion_id
WHERE s.status = 'pending'
GROUP BY s.id
ORDER BY s.confidence DESC, s.frequency DESC;
```

#### correction_statistics

Statistics per domain.

```sql
SELECT domain,
       COUNT(*) as total_corrections,
       COUNT(CASE WHEN source = 'manual' THEN 1 END) as manual_count,
       COUNT(CASE WHEN source = 'learned' THEN 1 END) as learned_count,
       COUNT(CASE WHEN source = 'imported' THEN 1 END) as imported_count,
       SUM(usage_count) as total_usage,
       MAX(added_at) as last_updated
FROM corrections
WHERE is_active = 1
GROUP BY domain;
```

## Querying the Database

### Using Python API

```python
from pathlib import Path
import sys
sys.path.insert(0, "scripts")
from core import CorrectionRepository, CorrectionService
from utils.config import get_config

# Initialize
db_path = get_config().database.path
repository = CorrectionRepository(db_path)
service = CorrectionService(repository)

# Add correction
service.add_correction("错误", "正确", domain="general")

# Get corrections
corrections = service.get_corrections(domain="general")

# Get statistics
stats = service.get_statistics(domain="general")
print(f"Total: {stats['total_corrections']}")

# Close
service.close()
```

### Using SQLite CLI

```bash
# Open database
sqlite3 ~/.transcript-fixer/corrections.db

# View active corrections
SELECT from_text, to_text, domain FROM active_corrections;

# View statistics
SELECT * FROM correction_statistics;

# View pending suggestions
SELECT * FROM pending_suggestions;

# Check schema version
SELECT value FROM system_config WHERE key = 'schema_version';
```

## Import/Export

### Export to JSON

Insert the following snippets before `service.close()` in the initialized-service example above (do not call the private CLI `_get_service` from an unrelated script). Keep the service open for exchange and close it afterward. Constructor/schema effects remain authorized maintenance, not preflight.

```python
corrections = service.export_corrections(domain="general")

# Write to file
import json
with open("export.json", "w", encoding="utf-8") as f:
    json.dump({
        "version": "2.0",
        "domain": "general",
        "corrections": corrections
    }, f, ensure_ascii=False, indent=2)
```

### Import from JSON

```python
import json

with open("import.json", "r", encoding="utf-8") as f:
    data = json.load(f)

inserted, updated, skipped = service.import_corrections(
    corrections=data["corrections"],
    domain=data.get("domain", "general"),
    merge=True,
    validate_all=True
)

print(f"Imported: {inserted} new, {updated} updated, {skipped} skipped")
```

## Backup Strategy

### Automatic Backups

The system maintains database integrity through SQLite's ACID guarantees and automatic journaling.

### Manual Backups

Copying only the main file is valid only after writers stop and all committed changes are in that file. Active WAL must be included in a consistent backup; prefer SQLite backup through an authorized maintenance connection. Never delete sidecars to simplify a copy.

```bash
# Backup database
cp ~/.transcript-fixer/corrections.db ~/backups/corrections_$(date +%Y%m%d).db

# Or use SQLite backup
sqlite3 ~/.transcript-fixer/corrections.db ".backup ~/backups/corrections.db"
```

### Version Control

**Recommended**: Use Git for configuration and export files, but NOT for the database:

```bash
# .gitignore
*.db
*.db-journal
*.bak
```

Instead, export corrections periodically:

```bash
# Prepare corrections_backup.json using the reviewed Service export example above
git add corrections_backup.json
git commit -m "Backup corrections"
```

## Best Practices

1. **Regular Exports**: Export to JSON weekly for team sharing
2. **Database Backups**: Backup `.db` file before major changes
3. **Use Transactions**: All modifications use ACID transactions automatically
4. **Soft Deletes**: Records are marked inactive, not deleted (preserves audit trail)
5. **Validate**: Run `--validate` after manual database changes
6. **Statistics**: Check usage patterns via `correction_statistics` view
7. **Cleanup**: Old history can be archived (query by `run_timestamp`)

## Troubleshooting

### Database Locked

Do not run VACUUM/recreate as an automatic diagnostic. Wait for authorized writers to finish and preserve a consistent backup. `--validate` explicitly refuses WAL/SHM/journal sidecars; it does not checkpoint or recover the source.

### Corrupted Database

Keep the original database and relevant sidecars intact. In authorized recovery, work on a private consistent copy, review recovered rows/constraints and compare counts before replacement; never treat a repaired copy as proof that the original was healthy. See troubleshooting.md.

### Missing Tables

Record missing tables as an error. Repository construction or --init can modify schema and is not validation. Review an authorized migration/recovery on a backup first; do not delete the original or silently create tables to make the check pass.
