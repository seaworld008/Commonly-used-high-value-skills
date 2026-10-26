#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""List or resolve the SECURITY_MODEL.md policy chain for a repository path.

Locally hardened from the Sentry Python resolver at d12f250460ffd961f549dbebf7eeb0cf4afd4c2e (Apache-2.0).
Derived from the resolve-security-md helper in openai/codex-security
(Apache-2.0). Rewritten as a dependency-free Python script; adds --ref so
diff reviews can read policy from a trusted base revision, and warns about
hidden or bidirectional control characters.

Usage:
  uv run scripts/resolve_security_model.py list    --repo PATH [--ref REF]
  uv run scripts/resolve_security_model.py resolve --repo PATH --scope PATH [--ref REF] [--show-hidden]
  uv run scripts/resolve_security_model.py check   --repo PATH [--scope PATH] [--ref REF]

check reports backticked file paths and code symbols in the policies that no
longer exist in the repository, so a policy cannot silently go stale.

Exit codes: 0 success, 1 check found stale references, 2 error. Warnings go to stderr; results go to stdout.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import posixpath
import re
import stat
import subprocess
import sys
import unicodedata
from pathlib import Path, PurePosixPath

DEFAULT_NAME = "SECURITY_MODEL.md"
MAX_BYTES = 1024 * 1024  # hard limit, policy is skipped and reported
WARN_BYTES = 64 * 1024  # soft limit, large policies crowd out code in context
MAX_HIDDEN_DETAILS = 20  # per policy; counting continues after this budget
PRUNE_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".tox", ".mypy_cache"}

# Reference check: inline code spans that look like file paths or code symbols.
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_SKIP_TOKEN = re.compile(r"[\s=<>\"'#{}\[\],;:@|$\\]|://|^-")
_INV_ID = re.compile(r"^INV-\d+$")
_FILE_EXT = re.compile(r"\.(py|pyi|md|toml|ya?ml|json|ts|tsx|js|mjs|sh|cfg|ini|txt|sql|lock)$")
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")

# Characters that change how text renders without being visible: bidi
# overrides/isolates, zero-width characters, and other format/control chars.
_ALLOWED_CONTROLS = {"\n", "\r", "\t"}
# Joiners are used in ordinary scripts and emoji; emoji tags encode flags.
_ALLOWED_FORMATS = {"\u200c", "\u200d"}


class PolicyError(Exception):
    pass


def warn(message: str) -> None:
    print(f"resolve_security_model: warning: {message}", file=sys.stderr)


def is_hidden(ch: str) -> bool:
    if ch in _ALLOWED_CONTROLS or ch in _ALLOWED_FORMATS or 0xE0020 <= ord(ch) <= 0xE007F:
        return False
    return unicodedata.category(ch) in {"Cc", "Cf", "Zl", "Zp"}


def hidden_report(text: str) -> tuple[list[str], int]:
    findings = []
    total = 0
    line = 1
    col = 0
    for index, ch in enumerate(text):
        if index == 0 and ch == "\ufeff":  # a leading BOM is harmless
            continue
        col += 1
        if ch == "\n":
            line += 1
            col = 0
            continue
        if is_hidden(ch):
            total += 1
            if len(findings) < MAX_HIDDEN_DETAILS:
                name = unicodedata.name(ch, "UNNAMED")
                findings.append(f"line {line} col {col}: U+{ord(ch):04X} {name}")
    return findings, total


def show_hidden(text: str) -> str:
    return "".join(f"<U+{ord(c):04X}>" if is_hidden(c) else c for c in text)


def run_git(repo: Path, *args: str, binary: bool = False) -> bytes | str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
        ).stdout
    except FileNotFoundError as exc:
        raise PolicyError("git is not installed") from exc
    except subprocess.CalledProcessError as exc:
        raise PolicyError(exc.stderr.decode("utf-8", "replace").strip()) from exc
    return out if binary else out.decode("utf-8")


def git_context(repo: Path) -> tuple[Path, str] | None:
    """Return (toplevel, prefix) when repo is inside a git work tree."""
    try:
        top = run_git(repo, "rev-parse", "--show-toplevel").removesuffix("\n")
        prefix = run_git(repo, "rev-parse", "--show-prefix").removesuffix("\n")
    except PolicyError:
        return None
    return Path(top), prefix


def decode_policy(data: bytes, source: str) -> str:
    if len(data) > MAX_BYTES:
        raise PolicyError(f"{source} exceeds 1 MiB; review it manually")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PolicyError(f"{source} is not valid UTF-8") from exc
    if len(data) > WARN_BYTES:
        warn(f"{source} is {len(data)} bytes; consider condensing it")
    details, total = hidden_report(text)
    for item in details:
        warn(f"{source}: hidden character at {item}")
    if total > len(details):
        warn(f"{source}: {total - len(details)} additional hidden characters omitted ({total} total)")
    return text


class Source:
    """Reads policy files from the working tree or from a git revision."""

    def __init__(self, repo: Path, name: str, ref: str | None):
        self.repo = repo.resolve()
        if not self.repo.is_dir():
            raise PolicyError(f"repo is not a directory: {repo}")
        self.name = name
        self.ref = None
        self.ref_label = ref
        self._warned_symlinks: set[str] = set()
        if ref is not None and not ref.strip():
            raise PolicyError("--ref must not be empty or whitespace")
        self.git = git_context(self.repo)
        if ref is not None and not self.git:
            raise PolicyError("--ref requires a git repository")
        if ref is not None:
            oid = run_git(self.repo, "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}").strip()
            if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", oid):
                raise PolicyError("--ref did not resolve to a full commit OID")
            self.ref = oid

    # -- listing -------------------------------------------------------
    def list(self) -> list[str]:
        if self.git:
            top, prefix = self.git
            if self.ref:
                return sorted(p for p in self._tree_files() if PurePosixPath(p).name == self.name and not self._disclosure(p))
            else:
                raw = run_git(self.repo, "ls-files", "-z", "-co", "--exclude-standard", binary=True)
            paths = [p.decode("utf-8", "surrogateescape") for p in raw.split(b"\0") if p]
            if self.ref and prefix:
                paths = [p[len(prefix):] for p in paths if p.startswith(prefix)]
            found = [p for p in paths if PurePosixPath(p).name == self.name and not self._disclosure(p)]
            if not self.ref:
                found = [p for p in found if self._safe_worktree_file(p)]
            return sorted(found)
        return sorted(self._walk())

    def _walk(self) -> list[str]:
        found = []
        for dirpath, dirnames, filenames in os.walk(self.repo, followlinks=False):
            dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS]
            if self.name in filenames:
                rel = Path(dirpath, self.name).relative_to(self.repo).as_posix()
                if not self._disclosure(rel) and self._safe_worktree_file(rel):
                    found.append(rel)
        return found

    def _disclosure(self, rel: str) -> bool:
        """GitHub treats these SECURITY.md locations as the disclosure policy."""
        return self.name == "SECURITY.md" and rel in {"SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md"}

    def _safe_worktree_file(self, rel: str) -> bool:
        path = self.repo / rel
        try:
            real = path.resolve(strict=True)
        except (OSError, RuntimeError):
            return False
        if not real.is_relative_to(self.repo):
            warn(f"{rel} resolves outside the repository; ignored")
            return False
        try:
            return stat.S_ISREG(real.stat().st_mode)
        except OSError:
            return False

    def _open_worktree_file(self, rel: str):
        """Validate before opening; nonblocking open/fstat also reject special files.

        This is not a guarantee against arbitrary concurrent directory replacement.
        """
        if not self._safe_worktree_file(rel):
            return None
        try:
            path = (self.repo / rel).resolve(strict=True)
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0))
        except (OSError, RuntimeError):
            return None
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            return None
        return os.fdopen(fd, "rb")

    def _tree_files(self) -> dict[str, str]:
        """Cache only regular blobs from the pinned commit, scoped to repo."""
        if not hasattr(self, "_tree_cache"):
            top, prefix = self.git  # type: ignore[misc]
            raw = run_git(top, "ls-tree", "-r", "-z", self.ref, binary=True)
            self._tree_cache: dict[str, str] = {}
            for entry in raw.split(b"\0"):
                if not entry:
                    continue
                metadata, path = entry.split(b"\t", 1)
                mode, kind, oid = metadata.split()
                path = path.decode("utf-8", "surrogateescape")
                if not path.startswith(prefix):
                    continue
                rel = path[len(prefix):]
                if mode == b"120000" and PurePosixPath(rel).name == self.name:
                    if rel not in self._warned_symlinks:
                        warn(f"{rel} is a historical symlink; ignored")
                        self._warned_symlinks.add(rel)
                if mode in {b"100644", b"100755"} and kind == b"blob":
                    self._tree_cache[rel] = oid.decode("ascii")
        return self._tree_cache

    # -- reading -------------------------------------------------------
    def read(self, rel: str) -> str | None:
        if self.ref:
            top, prefix = self.git  # type: ignore[misc]
            oid = self._tree_files().get(rel)
            if oid is None:
                return None
            if int(run_git(top, "cat-file", "-s", oid).strip()) > MAX_BYTES:
                raise PolicyError(f"{rel} exceeds 1 MiB; review it manually")
            return decode_policy(run_git(top, "cat-file", "blob", oid, binary=True), rel)
        fh = self._open_worktree_file(rel)
        if fh is None:
            return None
        with fh:
            data = fh.read(MAX_BYTES + 1)
        return decode_policy(data, rel)

    def is_dir(self, rel: str) -> bool:
        # A scope missing at this revision (a file the PR adds, or one it
        # deletes) is treated as a file, so its parent directories still
        # give the chain. A new directory has no policy of its own there.
        if self.ref:
            top, prefix = self.git  # type: ignore[misc]
            target = f"{self.ref}:{prefix}{rel}" if rel else f"{self.ref}:{prefix}"
            try:
                return run_git(top, "cat-file", "-t", target).strip() == "tree"
            except PolicyError:
                warn(f"{rel} does not exist at {self.ref_label}; using its parent directories")
                return False
        path = self.repo / rel
        if not path.exists():
            warn(f"{rel} does not exist; using its parent directories")
            return False
        return path.is_dir()

    def relative_scope(self, scope: str) -> str:
        raw = Path(os.path.expanduser(scope))
        absolute = raw if raw.is_absolute() else self.repo / raw
        resolved = Path(os.path.normpath(absolute))
        if not self.ref and resolved.exists():
            resolved = resolved.resolve()
        if not resolved.is_relative_to(self.repo):
            raise PolicyError(f"scope is outside the repository: {scope}")
        rel = resolved.relative_to(self.repo).as_posix()
        return "" if rel == "." else rel

    # -- chain ---------------------------------------------------------
    def resolve(self, scope: str, visible: bool) -> str:
        rel = self.relative_scope(scope)
        target = rel if (rel == "" or self.is_dir(rel)) else str(PurePosixPath(rel).parent)
        target = "" if target == "." else target
        parts = PurePosixPath(target).parts if target else ()
        directories = [""] + ["/".join(parts[: i + 1]) for i in range(len(parts))]
        sections = []
        for directory in directories:
            policy_rel = f"{directory}/{self.name}" if directory else self.name
            if self._disclosure(policy_rel):
                continue
            content = self.read(policy_rel)
            if content is None or not content.strip():
                continue
            if visible:
                content = show_hidden(content)
            section = f"## Policy source: {json.dumps(policy_rel)}\n\n{content}"
            if not section.endswith("\n"):
                section += "\n"
            sections.append(section)
        if not sections:
            warn(f"no {self.name} applies to {rel or '.'}")
        return "\n".join(sections)

    def chain(self, scope: str) -> list[str]:
        rel = self.relative_scope(scope)
        target = rel if (rel == "" or self.is_dir(rel)) else str(PurePosixPath(rel).parent)
        parts = PurePosixPath(target).parts if target not in {"", "."} else ()
        candidates = [self.name] + ["/".join(parts[: i + 1]) + f"/{self.name}" for i in range(len(parts))]
        return [c for c in candidates if not self._disclosure(c) and self.read(c) is not None]

    # -- reference check -----------------------------------------------
    def files(self) -> list[str]:
        if self.git:
            top, prefix = self.git
            if self.ref:
                return list(self._tree_files())
            raw = run_git(self.repo, "ls-files", "-z", "-co", "--exclude-standard", binary=True)
            paths = [p.decode("utf-8", "surrogateescape") for p in raw.split(b"\0") if p]
            return [p for p in paths if self._safe_worktree_file(p)]
        out = []
        for dirpath, dirnames, filenames in os.walk(self.repo, followlinks=False):
            dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS]
            for f in filenames:
                rel = Path(dirpath, f).relative_to(self.repo).as_posix()
                if self._safe_worktree_file(rel):
                    out.append(rel)
        return out

    def _text_contains(self, needle: str, word: bool) -> bool:
        """Search repository files, excluding policy files, for a reference."""
        files = [p for p in self._file_cache if PurePosixPath(p).name != self.name]
        if self.git:
            args = ["--literal-pathspecs", "grep", "-q", "-I", "-F"] + (["-w"] if word else [])
            if not self.ref:
                args.append("--untracked")
            args += ["-e", needle]
            if self.ref:
                args.append(self.ref)
            # An empty pathspec would search everything. Bound argv size too.
            for start in range(0, len(files), 100):
                result = subprocess.run(["git", "-C", str(self.repo), *args, "--", *files[start:start + 100]], capture_output=True)
                if result.returncode > 1:
                    raise PolicyError(result.stderr.decode("utf-8", "replace").strip())
                if result.returncode == 0:
                    return True
            return False
        pattern = re.compile((r"\b%s\b" if word else "%s") % re.escape(needle))
        for rel in files:
            try:
                fh = self._open_worktree_file(rel)
                if fh is None:
                    continue
                with fh:
                    if pattern.search(fh.read(MAX_BYTES).decode("utf-8", "ignore")):
                        return True
            except OSError:
                continue
        return False

    def check(self, scope: str | None) -> list[str]:
        """Report backticked file paths and code symbols that no longer exist."""
        policies = self.chain(scope) if scope else self.list()
        self._file_cache = self.files()
        file_set = set(self._file_cache)
        problems = []
        for policy in policies:
            content = self.read(policy) or ""
            base = str(PurePosixPath(policy).parent)
            in_fence = False
            for lineno, line in enumerate(content.splitlines(), 1):
                if line.lstrip().startswith("```"):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue
                for token in _INLINE_CODE.findall(line):
                    kind, found = self._check_token(token, base, file_set)
                    if kind and not found:
                        problems.append(f"{policy}:{lineno}: `{token}` not found ({kind})")
        return problems

    def _check_token(self, token: str, base: str, file_set: set[str]) -> tuple[str | None, bool]:
        token = token.strip()
        # Qualified names (`CacheKey::from_scoped_file`) are checked like dotted ones.
        token = re.sub(r"(?<=\w)::(?=\w)", ".", token)
        if _SKIP_TOKEN.search(token) or _INV_ID.match(token) or len(token) < 3:
            return None, True
        token = re.sub(r"\(.*\)$", "", token)
        if token.startswith("/"):
            return "literal", self._text_contains(token, word=False)
        if "/" in token or _FILE_EXT.search(token):
            candidates = [token] if base in {"", "."} else [token, f"{base}/{token}"]
            # Authors often write paths relative to a package root
            # (`api/authentication.py` for `src/sentry/api/authentication.py`),
            # so a match on the trailing path segments also counts.
            for cand in candidates:
                # Git trees use normalized POSIX paths even on Windows. Never
                # consult the working tree to resolve a trusted revision.
                cand = posixpath.normpath(cand)
                if cand == ".." or cand.startswith("../") or cand.startswith("/"):
                    continue
                if any(ch in cand for ch in "*?["):
                    if any(fnmatch.fnmatchcase(f, cand) or fnmatch.fnmatchcase(f, f"*/{cand}") for f in file_set):
                        return "path", True
                elif any(
                    f == cand or f.startswith(cand + "/") or f.endswith("/" + cand) or f"/{cand}/" in f
                    for f in file_set
                ):
                    return "path", True
                if not self.ref and self._exists_in_worktree(cand):
                    return "path", True  # reached through a tracked symlink
            return "path", False
        segments = [s for s in token.split(".") if len(s) >= 3]
        if not segments or not all(_IDENT.match(s) for s in segments):
            return None, True
        return "symbol", all(self._text_contains(s, word=True) for s in segments)

    def _exists_in_worktree(self, rel: str) -> bool:
        return self._safe_worktree_file(rel)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    for cmd in ("list", "resolve", "check"):
        p = sub.add_parser(cmd, allow_abbrev=False)
        p.add_argument("--repo", required=True, help="repository or component root")
        p.add_argument("--ref", help="read policies from this git revision (use the PR base for diff reviews)")
        p.add_argument("--name", default=DEFAULT_NAME, help=f"policy filename (default {DEFAULT_NAME})")
        if cmd == "resolve":
            p.add_argument("--scope", required=True, help="file or directory being reviewed")
            p.add_argument("--show-hidden", action="store_true", help="render hidden characters as <U+XXXX>")
        if cmd == "check":
            p.add_argument("--scope", help="check only the chain for this path (default: every policy)")
    args = parser.parse_args(argv)
    if "/" in args.name or "\\" in args.name or args.name in {"", ".", ".."}:
        parser.error("--name must be a bare filename")
    try:
        source = Source(Path(os.path.expanduser(args.repo)), args.name, args.ref)
        if args.command == "list":
            print(json.dumps(source.list(), ensure_ascii=True))
        elif args.command == "check":
            problems = source.check(args.scope)
            for problem in problems:
                print(problem)
            return 1 if problems else 0
        else:
            sys.stdout.write(source.resolve(args.scope, args.show_hidden))
    except PolicyError as exc:
        print(f"resolve_security_model: error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
