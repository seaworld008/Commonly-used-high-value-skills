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
DIR_FD_SUPPORTED = (os.open in os.supports_dir_fd and os.stat in os.supports_dir_fd
                    and os.stat in os.supports_follow_symlinks)


class ScanRoot:
    """Pin the initial root inode and every ancestor; never rebase a scan."""

    def __init__(self, directory, expected=None):
        # An inherited identity already names a canonical path. Resolving it
        # again would let a replacement link redefine the authorization root.
        self.path = (Path(directory).absolute() if expected is not None
                     else Path(directory).resolve(strict=True))
        self.fd = None
        self._fds = []
        self.identities = None
        if expected is not None:
            identities = expected.get('identities') if isinstance(expected, dict) else None
            if (not isinstance(expected, dict) or expected.get('path') != str(self.path)
                    or not isinstance(identities, list)
                    or len(identities) != len(self.path.parts)
                    or any(not isinstance(pair, list) or len(pair) != 2
                           or any(type(value) is not int or value < 0 for value in pair)
                           for pair in identities)):
                raise OSError("Invalid scan root identity")
            self.identities = [tuple(pair) for pair in identities]

    @staticmethod
    def identity(info):
        return info.st_dev, info.st_ino

    def _open_chain(self):
        if (not DIR_FD_SUPPORTED
                or not all(hasattr(os, flag) for flag in
                           ('O_DIRECTORY', 'O_NOFOLLOW', 'O_NONBLOCK'))):
            raise OSError("Safe directory-relative opens are unavailable")
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        fds = [os.open(self.path.anchor, flags)]
        identities = []
        try:
            for index, part in enumerate(self.path.parts):
                fd = fds[-1]
                if index:
                    before = os.stat(part, dir_fd=fd, follow_symlinks=False)
                    fd = os.open(part, flags, dir_fd=fd)
                    fds.append(fd)
                    if self.identity(os.fstat(fd)) != self.identity(before):
                        raise OSError("Scan root component changed during open")
                info = os.fstat(fd)
                if not stat.S_ISDIR(info.st_mode):
                    raise OSError("Scan root component is not a directory")
                identity = self.identity(info)
                if self.identities is not None and identity != self.identities[index]:
                    raise OSError("Scan root or ancestor changed")
                identities.append(identity)
            return fds, identities
        except BaseException:
            for fd in reversed(fds):
                os.close(fd)
            raise

    def __enter__(self):
        before = self.path.stat()
        # Retain ancestors too, so their inode numbers cannot be recycled
        # while a child checks the identity handed off by its parent.
        self._fds, self.identities = self._open_chain()
        self.fd = self._fds[-1]
        try:
            if self.identity(before) != self.identities[-1]:
                raise OSError("Scan root changed during initialization")
            self.verify()
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *unused):
        for fd in reversed(self._fds):
            os.close(fd)
        self._fds = []
        self.fd = None

    def __fspath__(self):
        return str(self.path)

    def verify(self):
        fds, _ = self._open_chain()
        try:
            if self.identity(os.fstat(self.fd)) != self.identities[-1]:
                raise OSError("Pinned scan root changed")
        finally:
            for fd in reversed(fds):
                os.close(fd)

    def snapshot(self):
        return {'path': str(self.path), 'identities': self.identities}

    def enter_for_pack(self):
        """Child-only cwd setup: validate and use the pinned inode before exec."""
        self.verify()
        os.fchdir(self.fd)
        self.verify()


@contextmanager
def pinned_scan_root(directory):
    if isinstance(directory, ScanRoot):
        directory.verify()
        yield directory
        directory.verify()
    else:
        with ScanRoot(directory) as root:
            yield root
            root.verify()

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
    with pinned_scan_root(base_dir) as root:
        with _open_scannable_file(file_path, root) as stream:
            yield stream


@contextmanager
def _open_scannable_file(file_path: Path, anchor: ScanRoot):
    root = anchor.path
    try:
        resolved = file_path.resolve(strict=True)
        relative = resolved.relative_to(root)
    except (ValueError, RuntimeError) as error:
        raise OSError("Scan target is outside the root or has a link cycle") from error
    before = resolved.stat()
    if not stat.S_ISREG(before.st_mode):
        raise OSError("Scan target is not a regular file")

    # Anchor every component so replaced parents cannot redirect the open.
    anchor.verify()
    directory_fd = os.dup(anchor.fd)
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
        anchor.verify()
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
    with pinned_scan_root(directory) as anchor:
        return _scan_directory(anchor, exclude_patterns)


def _scan_directory(anchor: ScanRoot, exclude_patterns):
    findings = []
    exclude_patterns = exclude_patterns or []

    def traversal_error(error):
        raise error

    if not hasattr(os, 'fwalk'):
        raise OSError("Safe descriptor-relative traversal is unavailable")
    # Directory enumeration must use the same anchor as file reads. A path-
    # based walk could otherwise list a replacement tree before verification.
    for root, dirs, files, _ in os.fwalk('.', dir_fd=anchor.fd,
                                        onerror=traversal_error, follow_symlinks=False):
        anchor.verify()
        root_path = anchor.path / root

        # Skip if matches exclude pattern
        if any(re.search(pattern, str(root_path)) for pattern in exclude_patterns):
            dirs[:] = []
            continue

        dirs[:] = [d for d in dirs if d not in SKIP_DIRS
                   and not any(re.search(pattern, str(root_path / d))
                               for pattern in exclude_patterns)]
        # fwalk skips linked directories; do not silently claim a full scan.
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

            file_findings = scan_file(file_path, anchor)
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

    directory = Path(sys.argv[1])

    # Parse arguments
    json_output = '--json' in sys.argv
    exclude_patterns = []

    if '--exclude' in sys.argv:
        exclude_idx = sys.argv.index('--exclude')
        exclude_patterns = [arg for arg in sys.argv[exclude_idx + 1:] if not arg.startswith('--')]

    # Scan
    try:
        expected = None
        if '--root-identity' in sys.argv:
            # Internal handoff from safe_pack; the parent keeps the root FD
            # alive, preventing inode reuse while the child validates it.
            expected = json.loads(sys.argv[sys.argv.index('--root-identity') + 1])
            if not isinstance(expected, dict):
                raise ValueError("Invalid inherited root identity")
        with ScanRoot(directory, expected) as root:
            directory = root.path
            findings = scan_directory(root, exclude_patterns)
            root.verify()
    except (OSError, UnicodeError, ValueError, IndexError, RuntimeError, re.error):
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
