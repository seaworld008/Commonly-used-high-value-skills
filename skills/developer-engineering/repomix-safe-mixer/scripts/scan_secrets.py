#!/usr/bin/env python3
"""
Security scanner for detecting hardcoded credentials in code.

Scans a directory for common credential patterns and reports findings.
"""

import os
import re
import sys
import json
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import List, Dict

# Common secret patterns (regex)
SECRET_PATTERNS = {
    'aws_access_key': r'(?i)AKIA[0-9A-Z]{16}',
    'aws_secret_key': r'(?i)(?:aws_secret|aws.{0,20}secret).{0,20}[=:]\s*["\']?([0-9a-zA-Z/+=]{40})["\']?',
    'supabase_url': r'https://[a-z]{20}\.supabase\.co',
    'supabase_anon_key': r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*',
    'stripe_key': r'(?:sk|pk)_(live|test)_[0-9a-zA-Z]{24,}',
    'cloudflare_api_token': r'(?i)(?:cloudflare|cf).{0,20}(?:token|key).{0,20}[=:]\s*["\']?([a-zA-Z0-9_-]{40,})["\']?',
    'turnstile_key': r'0x[0-9A-F]{22}',
    'generic_api_key': r'(?i)(?:api[_-]?key|apikey).{0,20}[=:]\s*["\']?([0-9a-zA-Z_\-]{20,})["\']?',
    'r2_account_id': r'[0-9a-f]{32}(?=\.r2\.cloudflarestorage\.com)',
    'jwt_token': r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}',
    'private_key': r'-----BEGIN (?:(?:RSA|EC|OPENSSH|DSA|ENCRYPTED) )?PRIVATE KEY-----',
    'oauth_secret': r'(?i)(?:client_secret|oauth).{0,20}[=:]\s*["\']?([0-9a-zA-Z_\-]{20,})["\']?',
}

# File extensions to scan
SCANNABLE_EXTENSIONS = {
    '.ts', '.tsx', '.js', '.jsx', '.py', '.md', '.json', '.yaml', '.yml',
    '.env', '.pem', '.key',
    '.sh', '.bash', '.zsh', '.sql', '.go', '.java', '.rb', '.php', '.cs'
}

# Directories to skip
SKIP_DIRS = {
    'node_modules', '.git', '.venv', 'venv', '__pycache__', 'dist', 'build',
    '.next', '.nuxt', 'vendor', 'target', 'bin', 'obj', '.terraform'
}
REDACTED = '[REDACTED]'

class SecretFinding:
    """Represents a detected secret."""
    def __init__(self, file_path: str, line_num: int, pattern_name: str):
        self.file_path = file_path
        self.line_num = line_num
        self.pattern_name = pattern_name

    def to_dict(self) -> Dict:
        return {
            'file': self.file_path,
            'line': self.line_num,
            'type': self.pattern_name,
            'match': REDACTED,
            'context': REDACTED,
        }

@contextmanager
def open_scannable_file(file_path: Path, base_dir: Path):
    """Open only a regular file beneath the root, including during path races."""
    root = base_dir.resolve(strict=True)
    try:
        resolved = file_path.resolve(strict=True)
        relative = resolved.relative_to(root)
    except (ValueError, RuntimeError) as error:
        raise OSError("Scan target is outside the root or has a link cycle") from error
    before = resolved.stat()
    if not stat.S_ISREG(before.st_mode):
        raise OSError("Scan target is not a regular file")

    # Anchor every component so replaced parents cannot redirect the open.
    directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    fd = None
    try:
        for part in relative.parts[:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        fd = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=directory_fd)
        opened = os.fstat(fd)
        if (not stat.S_ISREG(opened.st_mode)
                or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)):
            raise OSError("Scan target changed during open")
        # Verify the visible path again after acquiring the FD, before reading.
        try:
            current = file_path.resolve(strict=True)
            current.relative_to(root)
        except (ValueError, RuntimeError) as error:
            raise OSError("Scan target moved outside the root") from error
        visible = current.stat()
        if (current != resolved or not stat.S_ISREG(visible.st_mode)
                or (visible.st_dev, visible.st_ino) != (opened.st_dev, opened.st_ino)):
            raise OSError("Scan target changed during open")
        stream = os.fdopen(fd, 'r', encoding='utf-8')
        fd = None  # The stream now owns the descriptor.
        with stream:
            yield stream
    finally:
        if fd is not None:
            os.close(fd)
        os.close(directory_fd)


def scan_file(file_path: Path, base_dir: Path) -> List[SecretFinding]:
    """Scan a single file for secrets."""
    findings = []

    with open_scannable_file(file_path, base_dir) as f:
        for line_num, line in enumerate(f, 1):
            for pattern_name, pattern in SECRET_PATTERNS.items():
                matches = re.finditer(pattern, line)
                for match in matches:
                    # Skip common false positives
                    if should_skip_match(line, match.group()):
                        continue

                    findings.append(SecretFinding(
                        file_path=str(file_path.relative_to(base_dir)),
                        line_num=line_num,
                        pattern_name=pattern_name,
                    ))

    return findings

def should_skip_match(line: str, match: str) -> bool:
    """Check if a match should be skipped (likely false positive)."""
    # Skip example/placeholder values
    placeholders = [
        'your-', 'example', 'placeholder', 'xxx', 'yyy', 'zzz',
        'test-', 'demo-', 'sample-', '<YOUR_', '${', 'TODO'
    ]

    line_lower = line.lower()
    match_lower = match.lower()

    for placeholder in placeholders:
        if placeholder in match_lower or placeholder in line_lower:
            return True

    # Skip if in a comment
    if re.search(r'^\s*(?://|#|/\*|\*)', line):
        return True

    return False

def scan_directory(directory: Path, exclude_patterns: List[str] = None) -> List[SecretFinding]:
    """Scan a directory recursively for secrets."""
    findings = []
    exclude_patterns = exclude_patterns or []

    def traversal_error(error):
        raise error

    for root, dirs, files in os.walk(directory, onerror=traversal_error):
        root_path = Path(root)

        # Skip if matches exclude pattern
        if any(re.search(pattern, str(root_path)) for pattern in exclude_patterns):
            dirs[:] = []
            continue

        dirs[:] = [d for d in dirs if d not in SKIP_DIRS
                   and not any(re.search(pattern, str(root_path / d))
                               for pattern in exclude_patterns)]
        # os.walk skips linked directories; do not silently claim a full scan.
        if any((root_path / d).is_symlink() for d in dirs):
            raise OSError("Directory links cannot be scanned completely")

        for file in files:
            file_path = root_path / file

            # Only scan relevant file types
            is_env = file == ".env" or file.startswith(".env.")
            if not is_env and file_path.suffix not in SCANNABLE_EXTENSIONS:
                continue

            # Skip if matches exclude pattern
            if any(re.search(pattern, str(file_path)) for pattern in exclude_patterns):
                continue

            file_findings = scan_file(file_path, directory)
            findings.extend(file_findings)

    return findings

def print_report(findings: List[SecretFinding], directory: Path):
    """Print a human-readable report."""
    if not findings:
        print("✅ No secrets detected!")
        return

    print(f"\n⚠️  Found {len(findings)} potential secrets in {directory}:\n")

    # Group by file
    by_file = {}
    for finding in findings:
        if finding.file_path not in by_file:
            by_file[finding.file_path] = []
        by_file[finding.file_path].append(finding)

    # Print grouped
    for file_path in sorted(by_file.keys()):
        print(f"📄 {file_path}")
        for finding in by_file[file_path]:
            # Keep rule metadata out of text logs; structured JSON retains the type.
            print(f"   Line {finding.line_num}: potential credential")
            print(f"      Match: {REDACTED}")
        print()

def main():
    if len(sys.argv) < 2:
        print("Usage: scan_secrets.py <directory> [--json] [--exclude pattern1 pattern2 ...]")
        print("\nExamples:")
        print("  scan_secrets.py ./my-project")
        print("  scan_secrets.py ./my-project --json")
        print("  scan_secrets.py ./my-project --exclude '.*test.*' '.*example.*'")
        sys.exit(2)

    directory = Path(sys.argv[1]).resolve()

    if not directory.is_dir():
        print(f"Error: {directory} is not a directory", file=sys.stderr)
        sys.exit(2)

    # Parse arguments
    json_output = '--json' in sys.argv
    exclude_patterns = []

    if '--exclude' in sys.argv:
        exclude_idx = sys.argv.index('--exclude')
        exclude_patterns = [arg for arg in sys.argv[exclude_idx + 1:] if not arg.startswith('--')]

    # Scan
    try:
        findings = scan_directory(directory, exclude_patterns)
    except (OSError, UnicodeError, re.error):
        print("Error: Secret scan incomplete. Check file access, encoding and exclusions.", file=sys.stderr)
        sys.exit(2)

    # Output
    if json_output:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        print_report(findings, directory)

    # Exit code
    sys.exit(1 if findings else 0)

if __name__ == '__main__':
    main()
