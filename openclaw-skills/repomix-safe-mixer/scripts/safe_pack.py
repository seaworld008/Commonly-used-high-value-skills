#!/usr/bin/env python3
"""
Safe packaging workflow for repomix.

Packs only after the scanner completes without findings.
"""

import sys
import subprocess
import json
from pathlib import Path

def run_secret_scan(directory: Path, exclude_patterns: list = None):
    """Run secret scanner and return findings."""
    script_dir = Path(__file__).parent
    scan_script = script_dir / 'scan_secrets.py'

    cmd = [sys.executable, str(scan_script), str(directory), '--json']

    if exclude_patterns:
        cmd.extend(['--exclude'] + exclude_patterns)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode not in (0, 1) or result.stderr.strip():
            raise ValueError
        findings = json.loads(result.stdout)
        if not isinstance(findings, list) or bool(findings) != (result.returncode == 1):
            raise ValueError
        for finding in findings:
            if not (isinstance(finding, dict)
                    and isinstance(finding.get('file'), str)
                    and type(finding.get('line')) is int and finding['line'] > 0
                    and isinstance(finding.get('type'), str)
                    and finding.get('match') == '[REDACTED]'
                    and finding.get('context') == '[REDACTED]'):
                raise ValueError
    except (OSError, ValueError, subprocess.SubprocessError):
        print("Error: Secret scan failed or returned an invalid report. Packaging stopped.", file=sys.stderr)
        sys.exit(2)

    return findings

def print_findings_report(findings: list):
    """Print human-readable findings report."""
    if not findings:
        print("✅ No secrets detected!\n")
        return

    print(f"\n⚠️  Security Scan Found {len(findings)} Potential Secrets:\n")

    # Group by type
    by_type = {}
    for finding in findings:
        type_name = finding['type']
        if type_name not in by_type:
            by_type[type_name] = []
        by_type[type_name].append(finding)

    # Print by type
    for secret_type in sorted(by_type.keys()):
        count = len(by_type[secret_type])
        print(f"🔴 {secret_type}: {count} instance(s)")
        for finding in by_type[secret_type][:3]:  # Show first 3
            print(f"   - {finding['file']}:{finding['line']}")
            print("     Match: [REDACTED]")
        if len(by_type[secret_type]) > 3:
            print(f"   ... and {len(by_type[secret_type]) - 3} more\n")
        else:
            print()

def run_repomix(directory: Path, output_file: Path = None, config_file: Path = None):
    """Run repomix to package the directory."""
    cmd = ['repomix']

    if config_file and config_file.exists():
        cmd.extend(['--config', str(config_file)])

    if output_file:
        cmd.extend(['--output', str(output_file)])

    # Change to directory before running repomix
    result = subprocess.run(cmd, cwd=directory, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: repomix failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(1)

    print(result.stdout)
    return result

def main():
    if len(sys.argv) < 2:
        print("Usage: safe_pack.py <directory> [--output file.xml] [--config repomix.config.json] [--force] [--exclude pattern1 pattern2 ...]")
        print("\nOptions:")
        print("  --output <file>     Output file path for repomix")
        print("  --config <file>     Repomix config file")
        print("  --force             Accepted for compatibility; a clean scan is required")
        print("  --exclude <patterns> Patterns to exclude from secret scanning")
        print("\nExamples:")
        print("  safe_pack.py ./my-project")
        print("  safe_pack.py ./my-project --output package.xml")
        print(r"  safe_pack.py ./my-project --exclude '.*test.*' '.*\.example'")
        sys.exit(1)

    directory = Path(sys.argv[1]).resolve()

    if not directory.is_dir():
        print(f"Error: {directory} is not a directory", file=sys.stderr)
        sys.exit(1)

    # Parse arguments
    output_file = None
    config_file = None
    exclude_patterns = []

    if '--output' in sys.argv:
        output_idx = sys.argv.index('--output')
        if output_idx + 1 < len(sys.argv):
            output_file = Path(sys.argv[output_idx + 1])

    if '--config' in sys.argv:
        config_idx = sys.argv.index('--config')
        if config_idx + 1 < len(sys.argv):
            config_file = Path(sys.argv[config_idx + 1])

    if '--exclude' in sys.argv:
        exclude_idx = sys.argv.index('--exclude')
        exclude_patterns = [
            arg for arg in sys.argv[exclude_idx + 1:]
            if not arg.startswith('--') and arg != str(directory)
        ]

    print(f"🔍 Scanning {directory} for hardcoded secrets...\n")

    # Step 1: Scan for secrets
    findings = run_secret_scan(directory, exclude_patterns)

    # Step 2: Report findings
    print_findings_report(findings)

    # Step 3: Decision point
    if findings:
        print("❌ Cannot pack: Secrets detected!")
        print("Review the findings and run the scan again after cleanup.")
        sys.exit(1)

    # Step 4: Pack with repomix
    print(f"📦 Packing {directory} with repomix...\n")
    run_repomix(directory, output_file, config_file)

    print("\n✅ Packaging complete!")

    print("   No matches in the scanned scope. Review the package file list before sharing.")

if __name__ == '__main__':
    main()
