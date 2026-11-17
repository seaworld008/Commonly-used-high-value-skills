#!/usr/bin/env python3
"""
CLI Commands - Command Handler Functions

SINGLE RESPONSIBILITY: Handle CLI command execution

All cmd_* functions take parsed args and execute the requested operation.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import stat
import sys
import tempfile
from contextlib import closing
from pathlib import Path

from core import (
    CorrectionRepository,
    CorrectionService,
    DictionaryProcessor,
    AIProcessor,
    LearningEngine,
)
from utils import validate_configuration, print_validation_summary
from utils.health_check import HealthChecker, CheckLevel, format_health_output
from utils.metrics import get_metrics, format_metrics_summary
from utils.config import get_config
from utils.db_migrations_cli import create_migration_cli


def _get_service() -> CorrectionService:
    """Get configured CorrectionService instance."""
    # P1-5 FIX: Use centralized configuration
    config = get_config()
    config.database.path.parent.mkdir(parents=True, exist_ok=True)
    repository = CorrectionRepository(config.database.path)
    return CorrectionService(repository)


def _read_dictionary(db_path: Path, domain: str):
    """Read a private snapshot: SQLite mode=ro can still create WAL sidecars."""
    if not db_path.is_file():
        return {}, []

    sources = [db_path, db_path.with_name(db_path.name + "-wal")]

    def stamps():
        result = []
        for source in sources:
            try:
                stat = source.stat()
                result.append((stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns))
            except FileNotFoundError:
                result.append(None)
        return result

    with tempfile.TemporaryDirectory(prefix="transcript-dictionary-") as task_dir:
        before = stamps()
        for source, stamp in zip(sources, before):
            if stamp is not None:
                shutil.copyfile(source, Path(task_dir) / source.name)
        if stamps() != before:
            raise RuntimeError("Dictionary changed during snapshot; retry correction")
        snapshot = Path(task_dir) / db_path.name
        with closing(sqlite3.connect(snapshot.as_uri() + "?mode=ro", uri=True)) as conn:
            corrections = dict(conn.execute(
                "SELECT from_text, to_text FROM corrections WHERE is_active = 1 AND domain = ?",
                (domain,),
            ))
            rules = [
                {"pattern": row[0], "replacement": row[1], "description": row[2]}
                for row in conn.execute(
                    "SELECT pattern, replacement, description FROM context_rules "
                    "WHERE is_active = 1 ORDER BY priority DESC"
                )
            ]
    return corrections, rules


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize ~/.transcript-fixer/ directory"""
    service = _get_service()
    service.initialize()


def cmd_add_correction(args: argparse.Namespace) -> None:
    """Add a single correction"""
    service = _get_service()
    try:
        service.add_correction(args.from_text, args.to_text, args.domain)
        print(f"✅ Added: '{args.from_text}' → '{args.to_text}' (domain: {args.domain})")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def cmd_list_corrections(args: argparse.Namespace) -> None:
    """List all corrections"""
    service = _get_service()
    corrections = service.get_corrections(args.domain)

    print(f"\n📋 Corrections (domain: {args.domain})")
    print("=" * 60)
    for wrong, correct in sorted(corrections.items()):
        print(f"  '{wrong}' → '{correct}'")
    print(f"\nTotal: {len(corrections)} corrections\n")


def _write_atomic_text(path: Path, text: str) -> None:
    """Publish a closed, fully written file without truncating its predecessor."""
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        mode = 0
    staged = tempfile.NamedTemporaryFile(dir=path.parent, mode="w", encoding="utf-8", delete=False)
    try:
        with staged:
            staged.write(text)
            staged.flush()
            if stat.S_ISREG(mode):
                os.chmod(staged.name, mode & 0o777)
            os.fsync(staged.fileno())
        os.replace(staged.name, path)
    except BaseException:
        Path(staged.name).unlink(missing_ok=True)
        raise


def cmd_run_correction(args: argparse.Namespace) -> None:
    """Run the correction workflow"""
    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Error: File not found: {input_path}")
        sys.exit(1)

    # Setup output directory
    output_dir = Path(args.output) if args.output else input_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # The wrapper supplies a private path, never a scan of existing output files.
    generated_outputs = []
    manifest_path = os.environ.get("TRANSCRIPT_FIXER_OUTPUT_MANIFEST")

    def record_output(path=None):
        if path is not None:
            generated_outputs.append(str(path.resolve()))
        if manifest_path:
            _write_atomic_text(Path(manifest_path), json.dumps({"outputs": generated_outputs}))

    def deliver(path: Path, text: str) -> None:
        try:
            _write_atomic_text(path, text)
        except OSError as exc:
            print(f"❌ Text output not saved: {path} ({exc})")
            sys.exit(1)
        try:
            record_output(path)
        except OSError as exc:
            print(f"❌ Output receipt not updated ({exc})")
            print(f"💾 Text output saved: {path}")
            sys.exit(1)
        print(f"💾 Saved: {path.name}\n")

    record_output()

    # Ordinary correction does not authorize a persistent learning store.
    config = get_config()
    service = None
    try:
        if config.features.enable_learning:
            service = _get_service()
            corrections = service.get_corrections(args.domain)
            context_rules = service.load_context_rules()
        else:
            corrections, context_rules = _read_dictionary(config.database.path, args.domain)

        # Read input file
        print(f"📖 Reading: {input_path.name}")
        with open(input_path, 'r', encoding='utf-8') as f:
            original_text = f.read()
        print(f"   File size: {len(original_text):,} characters\n")

        # Stage 1: Dictionary corrections
        stage1_changes = []
        stage1_text = original_text
        if args.stage >= 1:
            print("=" * 60)
            print("🔧 Stage 1: Dictionary Corrections")
            print("=" * 60)

            processor = DictionaryProcessor(corrections, context_rules)
            stage1_text, stage1_changes = processor.process(original_text)

            summary = processor.get_summary(stage1_changes)
            print(f"✓ Applied {summary['total_changes']} corrections")
            print(f"  - Dictionary: {summary['dictionary_changes']}")
            print(f"  - Context rules: {summary['context_rule_changes']}")

            stage1_file = output_dir / f"{input_path.stem}_stage1.md"
            deliver(stage1_file, stage1_text)

        # Stage 2: AI corrections
        stage2_changes = []
        stage2_text = stage1_text
        if args.stage >= 2:
            print("=" * 60)
            print("🤖 Stage 2: AI Corrections")
            print("=" * 60)

            # Check API key
            api_key = os.environ.get("GLM_API_KEY")
            if not api_key:
                print("❌ Error: GLM_API_KEY environment variable not set")
                print("   Set it with: export GLM_API_KEY='your-key'")
                sys.exit(1)

            ai_processor = AIProcessor(api_key)
            try:
                stage2_text, stage2_changes = ai_processor.process(stage1_text)
            except Exception as exc:
                # Provider exceptions can contain request bodies. Report the state,
                # not their message; the processor retains exception causes.
                print(f"❌ AI correction failed ({type(exc).__name__}); Stage 2 not generated")
                sys.exit(1)

            metadata = getattr(ai_processor, "last_run_metadata", None)
            if not isinstance(metadata, dict):
                metadata = {}
            chunks = metadata.get("chunks_processed")
            if chunks is None:
                chunks = "unknown"
            models = metadata.get("models_used") or []
            model = ", ".join(dict.fromkeys(models)) or "unknown"
            unit = "chunk" if chunks == 1 else "chunks"
            print(f"✓ Processed {chunks} {unit} ({len(stage2_changes)} changes)\n")

            stage2_file = output_dir / f"{input_path.stem}_stage2.md"
            deliver(stage2_file, stage2_text)

            # History contains transcript text; persist it only with learning enabled.
            if config.features.enable_learning:
                try:
                    service.save_history(
                        filename=str(input_path),
                        domain=args.domain,
                        original_length=len(original_text),
                        stage1_changes=len(stage1_changes),
                        stage2_changes=len(stage2_changes),
                        model=model,
                        changes=stage1_changes + stage2_changes
                    )
                except Exception as exc:
                    print(f"❌ History not saved ({type(exc).__name__}); learning skipped")
                    print(f"💾 Text output saved: {stage2_file}")
                    sys.exit(1)

            if config.features.enable_learning and stage2_changes:
                print("=" * 60)
                print("🎓 Learning System: Analyzing AI Corrections")
                print("=" * 60)

                config_dir = config.paths.config_dir
                try:
                    learning = LearningEngine(
                        history_dir=config_dir / "history",
                        learned_dir=config_dir / "learned",
                        correction_service=service,
                        enable_learning=config.features.enable_learning,
                        enable_auto_approval=config.features.enable_auto_approval,
                    )
                    stats = learning.analyze_and_auto_approve(stage2_changes, args.domain)
                except Exception as exc:
                    print(f"❌ Learning failed ({type(exc).__name__}); dictionary updates may be partial")
                    print(f"💾 Text output saved: {stage2_file}")
                    print(f"💾 History saved: {config.database.path}")
                    sys.exit(1)

                print(f"📊 Analysis Results:")
                print(f"   Total changes: {stats['total_changes']}")
                print(f"   Unique patterns: {stats['unique_patterns']}")

                if stats['auto_approved'] > 0:
                    print(f"   ✅ Auto-approved: {stats['auto_approved']} patterns")
                    print(f"      (Added to dictionary for next run)")

                if stats['pending_review'] > 0:
                    print(f"   ⏳ Pending review: {stats['pending_review']} patterns")
                    print("      (CLI review/approval is not implemented; dictionary unchanged)")
                    for suggestion in stats.get('suggestions', []):
                        print(f"      {suggestion['from']} → {suggestion['to']}")

                if stats.get('savings_potential'):
                    print(f"\n   💰 {stats['savings_potential']}")

                print()

        # Stage 3: Generate diff report
        if args.stage >= 3:
            print("=" * 60)
            print("📊 Stage 3: Diff Report (not generated automatically)")
            print("=" * 60)
            print("   Run scripts/generate_word_diff.py explicitly to create visual comparison\n")

        print("✅ Correction complete!")

    finally:
        if service is not None:
            service.close()


def cmd_review_learned(args: argparse.Namespace) -> None:
    """Review learned suggestions"""
    # TODO: Implement learning engine with SQLite backend
    print("⚠️  Learning engine not yet implemented with SQLite backend")
    print("   This feature will be added in a future update")


def cmd_approve(args: argparse.Namespace) -> None:
    """Approve a learned suggestion"""
    # TODO: Implement learning engine with SQLite backend
    print("⚠️  Learning engine not yet implemented with SQLite backend")
    print("   This feature will be added in a future update")


def cmd_validate(args: argparse.Namespace) -> None:
    """Validate configuration and JSON files"""
    errors, warnings = validate_configuration()
    exit_code = print_validation_summary(errors, warnings)
    if exit_code != 0:
        sys.exit(exit_code)


def cmd_health(args: argparse.Namespace) -> None:
    """
    Perform system health check

    CRITICAL FIX (P1-4): Production-grade health monitoring
    """
    # Parse check level
    level_map = {
        'basic': CheckLevel.BASIC,
        'standard': CheckLevel.STANDARD,
        'deep': CheckLevel.DEEP
    }
    level = level_map.get(args.level, CheckLevel.STANDARD)

    # Run health check
    checker = HealthChecker()
    health = checker.check_health(level=level)

    # Output format
    if args.format == 'json':
        print(health.to_json())
    else:
        output = format_health_output(health, verbose=args.verbose)
        print(output)

    # Exit with appropriate code
    if health.status.value == 'unhealthy':
        sys.exit(1)
    elif health.status.value == 'degraded':
        sys.exit(2)
    else:
        sys.exit(0)


def cmd_metrics(args: argparse.Namespace) -> None:
    """
    Display collected metrics

    CRITICAL FIX (P1-7): Production-grade metrics and observability
    """
    metrics = get_metrics()

    # Output format
    if args.format == 'json':
        print(metrics.to_json())
    elif args.format == 'prometheus':
        print(metrics.to_prometheus())
    else:
        # Text summary
        summary = metrics.get_summary()
        output = format_metrics_summary(summary)
        print(output)


def cmd_config(args: argparse.Namespace) -> None:
    """
    Configuration management commands

    CRITICAL FIX (P1-5): Production-grade configuration management
    """
    from utils.config import create_example_config, Environment

    if args.action == 'show':
        # Display current configuration
        config = get_config()
        output = {
            'environment': config.environment.value,
            'database_path': str(config.database.path),
            'config_dir': str(config.paths.config_dir),
            'api_key_set': config.api.api_key is not None,
            'debug': config.debug,
            'features': {
                'learning': config.features.enable_learning,
                'metrics': config.features.enable_metrics,
                'health_checks': config.features.enable_health_checks,
                'rate_limiting': config.features.enable_rate_limiting,
                'caching': config.features.enable_caching,
                'auto_approval': config.features.enable_auto_approval,
            }
        }
        print('Current Configuration:')
        for key, value in output.items():
            print(f'  {key}: {value}')

    elif args.action == 'create-example':
        # Create example config file
        output_path = Path(args.path) if args.path else get_config().paths.config_dir / 'config.json'
        create_example_config(output_path)
        print(f'Example config created: {output_path}')

    elif args.action == 'validate':
        # Validate configuration
        config = get_config()
        errors, warnings = config.validate()

        print('Configuration Validation:')
        if errors:
            print('  Errors:')
            for error in errors:
                print(f'    ❌ {error}')
            sys.exit(1)
        if warnings:
            print('  Warnings:')
            for warning in warnings:
                print(f'    ⚠️  {warning}')
        if not errors and not warnings:
            print('  ✅ Configuration is valid')
        sys.exit(0 if not errors else 1)

    elif args.action == 'set-env':
        # Set environment
        if args.env not in [e.value for e in Environment]:
            print(f'Invalid environment: {args.env}')
            print(f'Valid environments: {", ".join(e.value for e in Environment)}')
            sys.exit(1)

        print(f'Environment set to: {args.env}')
        print('To make this permanent, set TRANSCRIPT_FIXER_ENV environment variable:')


def cmd_migration(args: argparse.Namespace) -> None:
    """
    Database migration commands (P1-6 fix)

    CRITICAL FIX (P1-6): Production database migration system
    """
    migration_cli = create_migration_cli()

    if args.action == 'status':
        migration_cli.cmd_status(args)
    elif args.action == 'history':
        migration_cli.cmd_history(args)
    elif args.action == 'migrate':
        migration_cli.cmd_migrate(args)
    elif args.action == 'rollback':
        migration_cli.cmd_rollback(args)
    elif args.action == 'plan':
        migration_cli.cmd_plan(args)
    elif args.action == 'validate':
        migration_cli.cmd_validate(args)
    elif args.action == 'create':
        migration_cli.cmd_create_migration(args)
    else:
        print("Unknown migration action")
        sys.exit(1)


def cmd_audit_retention(args: argparse.Namespace) -> None:
    """
    Audit log retention management commands (P1-11 fix)

    CRITICAL FIX (P1-11): Production-grade audit log retention and compliance
    """
    from utils.audit_log_retention import get_retention_manager
    import json

    # Get retention manager with configured database path
    config = get_config()
    manager = get_retention_manager(config.database.path)

    if args.action == 'cleanup':
        # Clean up expired audit logs
        entity_type = getattr(args, 'entity_type', None)
        dry_run = getattr(args, 'dry_run', False)

        if dry_run:
            print("🔍 DRY RUN MODE - No actual changes will be made\n")

        print("🧹 Cleaning up expired audit logs...")
        results = manager.cleanup_expired_logs(entity_type=entity_type, dry_run=dry_run)

        if not results:
            print("ℹ️  No cleanup operations performed (permanent retention or no expired logs)")
            return

        print("\n📊 Cleanup Results:")
        print("=" * 70)

        for result in results:
            status = "✅ Success" if result.success else "❌ Failed"
            print(f"\n{result.entity_type}: {status}")
            print(f"  Scanned: {result.records_scanned}")
            print(f"  Deleted: {result.records_deleted}")
            print(f"  Archived: {result.records_archived}")
            print(f"  Anonymized: {result.records_anonymized}")
            print(f"  Execution time: {result.execution_time_ms}ms")

            if result.errors:
                print(f"  Errors: {', '.join(result.errors)}")

        print()

    elif args.action == 'report':
        # Generate compliance report
        print("📋 Generating compliance report...\n")
        report = manager.generate_compliance_report()

        print("=" * 70)
        print("AUDIT LOG COMPLIANCE REPORT")
        print("=" * 70)
        print(f"Report Date: {report.report_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Compliance Status: {'✅ COMPLIANT' if report.is_compliant else '❌ NON-COMPLIANT'}")
        print(f"\nTotal Audit Logs: {report.total_audit_logs:,}")

        if report.oldest_log_date:
            print(f"Oldest Log: {report.oldest_log_date.strftime('%Y-%m-%d %H:%M:%S')}")
        if report.newest_log_date:
            print(f"Newest Log: {report.newest_log_date.strftime('%Y-%m-%d %H:%M:%S')}")

        print(f"\nStorage: {report.storage_size_mb:.2f} MB")
        print(f"Archived Files: {report.archived_logs_count}")

        print("\nLogs by Entity Type:")
        for entity_type, count in sorted(report.logs_by_entity_type.items()):
            print(f"  {entity_type}: {count:,}")

        if report.retention_violations:
            print("\n⚠️  Retention Violations:")
            for violation in report.retention_violations:
                print(f"  • {violation}")
            print("\nRun 'audit-retention cleanup' to resolve violations")

        print()

        # JSON output option
        if getattr(args, 'format', 'text') == 'json':
            print(json.dumps(report.to_dict(), indent=2))

    elif args.action == 'policies':
        # Show retention policies
        print("📜 Retention Policies:")
        print("=" * 70)

        policies = manager.load_retention_policies()

        for entity_type, policy in sorted(policies.items()):
            status = "✅ Active" if policy.is_active else "❌ Inactive"
            days_str = "PERMANENT" if policy.retention_days == -1 else f"{policy.retention_days} days"

            print(f"\n{entity_type}: {status}")
            print(f"  Retention: {days_str}")
            print(f"  Strategy: {policy.strategy.value.upper()}")

            if policy.critical_action_retention_days:
                crit_days = policy.critical_action_retention_days
                print(f"  Critical Actions: {crit_days} days (extended)")

            if policy.description:
                print(f"  Description: {policy.description}")

        print()

    elif args.action == 'restore':
        # Restore from archive
        archive_file = Path(getattr(args, 'archive_file', ''))

        if not archive_file:
            print("❌ Error: --archive-file required for restore action")
            sys.exit(1)

        if not archive_file.exists():
            print(f"❌ Error: Archive file not found: {archive_file}")
            sys.exit(1)

        verify_only = getattr(args, 'verify_only', False)

        if verify_only:
            print(f"🔍 Verifying archive: {archive_file.name}")
            count = manager.restore_from_archive(archive_file, verify_only=True)
            print(f"✅ Archive is valid: contains {count} log entries")
        else:
            print(f"📦 Restoring from archive: {archive_file.name}")
            count = manager.restore_from_archive(archive_file, verify_only=False)
            print(f"✅ Restored {count} log entries")

        print()

    else:
        print(f"❌ Unknown audit-retention action: {args.action}")
        print("Valid actions: cleanup, report, policies, restore")
        sys.exit(1)
