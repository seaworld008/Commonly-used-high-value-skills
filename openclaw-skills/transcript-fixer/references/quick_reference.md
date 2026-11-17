# Quick Reference

**Storage**: transcript-fixer uses SQLite database for corrections storage.

**Database location**: current `config.database.path`, selected by `TRANSCRIPT_FIXER_DB_PATH`, otherwise `TRANSCRIPT_FIXER_CONFIG_DIR/corrections.db` (default directory `~/.transcript-fixer`). Commands run from the skill root. SQL paths below illustrate that default; substitute the selected path. Reuse existing authorized setup.

Stage 2 cumulatively runs dictionary then AI on the original, producing `*_stage1.md` and `*_stage2.md`; Stage 3 only adds a diff hint. Generate HTML with `python scripts/generate_word_diff.py original.md corrected.md output.html`. Default learning/auto-approval/browser opening are disabled; review/approval CLI commands are placeholders. See `script_parameters.md` for actual outputs, current-run manifests and exit codes.

## Quick Start Examples

### Adding Corrections via CLI

```bash
# Add a simple correction
uv run scripts/fix_transcription.py --add "巨升智能" "具身智能" --domain embodied_ai

# Add corrections for specific domain
uv run scripts/fix_transcription.py --add "奇迹创坛" "奇绩创坛" --domain general
uv run scripts/fix_transcription.py --add "矩阵公司" "初创公司" --domain general
```

### Adding Corrections via SQL

```bash
sqlite3 ~/.transcript-fixer/corrections.db

# Insert corrections
INSERT INTO corrections (from_text, to_text, domain, source)
VALUES ('巨升智能', '具身智能', 'embodied_ai', 'manual');

INSERT INTO corrections (from_text, to_text, domain, source)
VALUES ('巨升', '具身', 'embodied_ai', 'manual');

INSERT INTO corrections (from_text, to_text, domain, source)
VALUES ('奇迹创坛', '奇绩创坛', 'general', 'manual');

# Exit
.quit
```

### Adding Context Rules via SQL

Context rules use regex patterns for context-aware corrections:

```bash
sqlite3 ~/.transcript-fixer/corrections.db

# Add context-aware rules
INSERT INTO context_rules (pattern, replacement, description, priority)
VALUES ('巨升方向', '具身方向', '巨升→具身', 10);

INSERT INTO context_rules (pattern, replacement, description, priority)
VALUES ('巨升现在', '具身现在', '巨升→具身', 10);

INSERT INTO context_rules (pattern, replacement, description, priority)
VALUES ('近距离的去看', '近距离地去看', '的→地 副词修饰', 5);

# Exit
.quit
```

### Adding Corrections via Python API

Save as `add_corrections.py` and run with `uv run add_corrections.py`:

```python
#!/usr/bin/env -S uv run
from pathlib import Path
import sys
sys.path.insert(0, "scripts")
from core import CorrectionRepository, CorrectionService
from utils.config import get_config

# Initialize service
db_path = get_config().database.path
repository = CorrectionRepository(db_path)
service = CorrectionService(repository)

# Add corrections
corrections = [
    ("巨升智能", "具身智能", "embodied_ai"),
    ("巨升", "具身", "embodied_ai"),
    ("奇迹创坛", "奇绩创坛", "general"),
    ("火星营", "火星营", "general"),
    ("矩阵公司", "初创公司", "general"),
    ("股价", "框架", "general"),
    ("三观", "三关", "general"),
]

for from_text, to_text, domain in corrections:
    service.add_correction(from_text, to_text, domain)
    print(f"✅ Added: '{from_text}' → '{to_text}' (domain: {domain})")

# Close connection
service.close()
```

## Bulk Import Example

Use the provided bulk import script for importing multiple corrections:

```bash
uv run scripts/examples/bulk_import.py
```

## Querying the Database

Direct SQLite and Repository examples are authorized dictionary-management operations, not zero-write preflight. For unchanged existing structure use `python scripts/fix_transcription.py --validate`; missing/invalid tables fail, active WAL/SHM/journal sidecars explicitly remain unverified. Do not initialize or delete sidecars to make validation pass.

### View Active Corrections

```bash
sqlite3 ~/.transcript-fixer/corrections.db "SELECT from_text, to_text, domain FROM active_corrections;"
```

### View Statistics

```bash
sqlite3 ~/.transcript-fixer/corrections.db "SELECT * FROM correction_statistics;"
```

### View Context Rules

```bash
sqlite3 ~/.transcript-fixer/corrections.db "SELECT pattern, replacement, priority FROM context_rules WHERE is_active = 1 ORDER BY priority DESC;"
```

## See Also

- `references/file_formats.md` - Complete database schema documentation
- `references/script_parameters.md` - CLI command reference
- `SKILL.md` - Main user documentation
