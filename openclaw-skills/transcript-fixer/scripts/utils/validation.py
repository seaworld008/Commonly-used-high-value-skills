#!/usr/bin/env python3
"""
Read-only structural validation of the selected existing dictionary.

Inspects a private snapshot without active journal sidecars and process credential presence. Never
constructs a write-capable Repository, initializes schema, or repairs user data.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path


def _database_stamp(path: Path) -> tuple[int, ...]:
    stat = path.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def _check_sidecars(db_path: Path) -> None:
    # Opening even mode=ro on a WAL database can create/update -shm. Never open
    # the user database in SQLite, and never discard an existing WAL/journal.
    if any(db_path.with_name(db_path.name + suffix).exists()
           for suffix in ('-wal', '-shm', '-journal')):
        raise RuntimeError('Database not verified: WAL/shared-memory/journal sidecar present; '
                           'use a quiescent, consistent non-WAL copy for validation')


def _inspect_database(db_path: Path) -> tuple[list[str], int | None]:
    """Inspect an unchanged private snapshot; never initialize schema.

    An idle, checkpointed WAL database without sidecars can be copied safely.
    Refuse active journals and verify source identity throughout the inspection.
    No checkpoint, journal-mode change, or recovery touches the user database.
    """
    _check_sidecars(db_path)
    before = _database_stamp(db_path)
    with tempfile.TemporaryDirectory(prefix='transcript-validation-') as task_dir:
        snapshot = Path(task_dir) / 'database.db'
        shutil.copyfile(db_path, snapshot)
        _check_sidecars(db_path)
        if _database_stamp(db_path) != before:
            raise RuntimeError('Database not verified: changed during snapshot; retry when idle')
        with snapshot.open('rb') as source:
            header = source.read(100)
        if len(header) < 100 or header[:16] != b'SQLite format 3\x00':
            raise ValueError('Not a valid SQLite database header')
        with closing(sqlite3.connect(snapshot.as_uri() + '?mode=ro&immutable=1', uri=True)) as conn:
            integrity = conn.execute('PRAGMA integrity_check').fetchall()
            if integrity != [('ok',)]:
                # Do not print database-controlled text or transcript contents.
                raise ValueError('SQLite integrity check failed')
            tables = [row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")]
            count = (conn.execute('SELECT COUNT(*) FROM corrections').fetchone()[0]
                     if 'corrections' in tables else None)
        _check_sidecars(db_path)
        if _database_stamp(db_path) != before:
            raise RuntimeError('Database not verified: changed during inspection; retry when idle')
    return tables, count


def validate_configuration() -> tuple[list[str], list[str]]:
    """
    Validate transcript-fixer configuration.

    Returns:
        Tuple of (errors, warnings) as string lists
    """
    # Use the same selected Config instance as CLI correction/maintenance.
    from utils.config import get_config

    config = get_config()
    config_dir = config.paths.config_dir
    db_path = config.database.path

    errors = []
    warnings = []

    print("🔍 Validating transcript-fixer configuration...\n")

    print(f"Selected database: {db_path}")
    if not config_dir.exists():
        warnings.append(f"Configuration directory not found: {config_dir}")
        print(f"⚠️  {warnings[-1]}")
    else:
        print(f"✅ Configuration directory exists: {config_dir}")

    # Validate SQLite database
    if db_path.is_file():
        try:
            tables, count = _inspect_database(db_path)

            expected_tables = [
                'corrections', 'context_rules', 'correction_history',
                'correction_changes', 'learned_suggestions', 'suggestion_examples',
                'system_config', 'audit_log'
            ]

            missing_tables = [t for t in expected_tables if t not in tables]
            if missing_tables:
                errors.append(f"Database missing tables: {missing_tables}")
                print(f"❌ {errors[-1]}")
            else:
                print(f"✅ All {len(expected_tables)} tables present")
                print(f"✅ SQLite snapshot integrity checked: {count} corrections")

        except Exception as e:
            errors.append(f"Database validation failed: {e}")
            print(f"❌ {errors[-1]}")
    else:
        errors.append(f"Database not found or not a regular file: {db_path}")
        print(f"❌ {errors[-1]}")

    # Check API key
    api_key = os.getenv("GLM_API_KEY")
    if not api_key:
        warnings.append("GLM_API_KEY environment variable not set")
        print("⚠️  GLM_API_KEY not set (required for Stage 2 AI corrections)")
    else:
        print("✅ GLM_API_KEY is set")

    return errors, warnings


def print_validation_summary(errors: list[str], warnings: list[str]) -> int:
    """
    Print validation summary and return exit code.

    Returns:
        0 if valid, 1 if errors found
    """
    print("\n" + "=" * 60)

    if errors:
        print(f"❌ {len(errors)} error(s) found:")
        for err in errors:
            print(f"   - {err}")
        print("\n💡 Fix errors and run --validate again")
        print("=" * 60)
        return 1
    elif warnings:
        print(f"⚠️  {len(warnings)} warning(s):")
        for warn in warnings:
            print(f"   - {warn}")
        print("\n✅ Configuration is valid (with warnings)")
        print("=" * 60)
        return 0
    else:
        print("✅ All checks passed! Configuration is valid.")
        print("=" * 60)
        return 0


def main():
    """Run validation as standalone script"""
    errors, warnings = validate_configuration()
    exit_code = print_validation_summary(errors, warnings)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
