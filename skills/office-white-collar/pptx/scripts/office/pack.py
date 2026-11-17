# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Lossless, bounded OOXML packaging. Temporary files stay under TMPDIR."""

import argparse
import importlib.util
import os
from pathlib import Path
import stat
import sys
import tempfile
import unicodedata
import zipfile
import zlib
from xml.parsers import expat

import defusedxml.minidom

MAX_FILES = 10000
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_XML_BYTES = 16 * 1024 * 1024
MAX_RATIO = 1000
MAX_XML_NODES = 100000
MAX_XML_DEPTH = 128
FAMILIES = {".docx": "word/document.xml", ".pptx": "ppt/presentation.xml",
            ".xlsx": "xl/workbook.xml"}


def _temp_root():
    root = Path(os.environ.get("TMPDIR") or tempfile.gettempdir())
    if not root.is_dir():
        raise ValueError("TMPDIR must name an existing directory")
    return root


def _load_local(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse_xml(data):
    if len(data) > MAX_XML_BYTES:
        raise ValueError("XML part exceeds size limit")
    # Bound structure before constructing a DOM, including attribute-heavy XML.
    parser = expat.ParserCreate()
    depth = nodes = 0
    def reject(*args):
        raise ValueError("XML DTD/entities are not allowed")
    def count(extra=1):
        nonlocal nodes
        nodes += extra
        if nodes > MAX_XML_NODES:
            raise ValueError("XML node count exceeds limit")
    def start(name, attrs):
        nonlocal depth
        count(1 + len(attrs))
        depth += 1
        if depth > MAX_XML_DEPTH:
            raise ValueError("XML nesting exceeds limit")
    def end(name):
        nonlocal depth
        depth -= 1
    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CommentHandler = lambda text: count()
    parser.ProcessingInstructionHandler = lambda target, text: count()
    parser.StartDoctypeDeclHandler = reject
    parser.EntityDeclHandler = reject
    parser.ExternalEntityRefHandler = reject
    parser.Parse(data, True)
    return defusedxml.minidom.parseString(
        data, forbid_dtd=True, forbid_entities=True, forbid_external=True)


def _xml_name(name):
    return Path(name).suffix.lower() in (".xml", ".rels")


def _part_name(name):
    if not name or "\\" in name or ":" in name or "\x00" in name:
        raise ValueError(f"unsafe package path: {name!r}")
    if name.startswith("/"):
        raise ValueError(f"absolute package path: {name!r}")
    parts = name.rstrip("/").split("/")
    if any(p in ("", ".", "..") or p.endswith((" ", ".")) for p in parts):
        raise ValueError(f"unsafe package path: {name!r}")
    if any(any(ord(c) < 32 for c in p) for p in parts):
        raise ValueError("control character in package path")
    return "/".join(parts)


def _check_names(entries):
    """Check explicit entries, implicit directories and portable collisions."""
    known = {}
    for name, directory in entries:
        name = _part_name(name)
        key = unicodedata.normalize("NFC", name).casefold()
        if key in known:
            raise ValueError(f"duplicate/conflicting package path: {name}")
        known[key] = (name, directory)
    spellings = {}
    for name, directory in known.values():
        parts = name.split("/")
        for i in range(1, len(parts) + 1):
            prefix = "/".join(parts[:i])
            folded = unicodedata.normalize("NFC", prefix).casefold()
            if folded in spellings and spellings[folded] != prefix:
                raise ValueError(f"ambiguous package directory: {prefix}")
            spellings[folded] = prefix
            if i < len(parts) and folded in known and not known[folded][1]:
                raise ValueError(f"file/directory conflict: {prefix}")


def _safe_directory(path):
    path = Path(os.path.abspath(path))
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError(f"symlink path not allowed: {parent}")
    return path


def _inventory(directory):
    directory = _safe_directory(directory)
    if not directory.is_dir():
        raise ValueError("input must be a directory")
    entries, files, total = [], [], 0
    def unreadable(error):
        raise error
    for parent, dirs, names in os.walk(directory, followlinks=False, onerror=unreadable):
        for name in sorted(dirs + names):
            path = Path(parent) / name
            mode = path.lstat().st_mode
            is_dir = stat.S_ISDIR(mode)
            if not (is_dir or stat.S_ISREG(mode)):
                raise ValueError(f"special file or symlink not allowed: {path}")
            relative = path.relative_to(directory).as_posix()
            entries.append((relative, is_dir))
            if len(entries) > MAX_FILES:
                raise ValueError("package entry count exceeds limit")
            if not is_dir:
                size = path.stat().st_size
                total += size
                if size > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                    raise ValueError("package size exceeds limit")
                files.append((path, relative))
    _check_names(entries)
    return files


def _read_regular(path, limit=MAX_FILE_BYTES):
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("not a regular file")
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("part exceeds size limit")
    return data


def _check_package(directory, suffix):
    required = ("[Content_Types].xml", "_rels/.rels", FAMILIES[suffix])
    if any(not (directory / name).is_file() for name in required):
        raise ValueError(f"missing required {suffix} package parts")


def _condense_xml(xml_file):
    """Check XML; deliberately retain every original whitespace byte."""
    _parse_xml(_read_regular(xml_file, MAX_XML_BYTES)).unlink()


def _write_document(path, document):
    """Serialize in TMPDIR, then replace a single XML file atomically."""
    path = _safe_directory(path)
    data = document.toxml(encoding="UTF-8")
    _parse_xml(data).unlink()
    fd, name = tempfile.mkstemp(prefix="office-xml-", dir=_temp_root())
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        temporary.chmod(stat.S_IMODE(path.stat().st_mode))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _run_validation(unpacked_dir, original_file, suffix, infer_author_func=None):
    # Lazy import: validation is optional. Never repair the source tree.
    if __package__:
        from . import validators
    else:
        import validators
    cls = {".docx": "DOCXSchemaValidator", ".pptx": "PPTXSchemaValidator",
           ".xlsx": "BaseSchemaValidator"}[suffix]
    base = getattr(validators, cls)(Path(unpacked_dir), original_file=original_file)
    checks = [base]
    if suffix == ".docx" and original_file:
        if infer_author_func is None:
            helper = _load_local(Path(__file__).parent / "helpers/simplify_redlines.py",
                                 "_office_redlines")
            infer_author_func = helper.infer_author
        author = infer_author_func(unpacked_dir, original_file)
        # None is valid for unchanged documents and multiple authors. The real
        # validator compares all new revisions with the original, including
        # author/date/text attribution; inference never gates that comparison.
        checks.append(validators.RedliningValidator(
            Path(unpacked_dir), original_file, author=author))
    return all(check.validate() for check in checks)


def pack(input_directory, output_file, original_file=None, validate=True,
         infer_author_func=None):
    """Return (success, message); publish only a completely checked ZIP."""
    try:
        source = _safe_directory(input_directory)
        output = _safe_directory(output_file)
        suffix = output.suffix.lower()
        if suffix not in FAMILIES:
            raise ValueError("output extension must be .docx, .pptx, or .xlsx")
        if output.is_relative_to(source):
            raise ValueError("output cannot be inside the source tree")
        if not output.parent.is_dir() or (output.exists() and not output.is_file()):
            raise ValueError("output parent must exist; output must be a regular file")
        with tempfile.TemporaryDirectory(prefix="office-pack-", dir=_temp_root(),
                                         ignore_cleanup_errors=True) as tmp:
            stage = Path(tmp).resolve() / "parts"
            stage.mkdir()
            total = 0
            for path, name in _inventory(source):
                data = _read_regular(path)
                total += len(data)
                if total > MAX_TOTAL_BYTES:
                    raise ValueError("package size exceeds limit")
                if _xml_name(name):
                    _parse_xml(data).unlink()
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            _check_package(stage, suffix)
            if validate and not _run_validation(stage, original_file, suffix, infer_author_func):
                raise ValueError("package validation failed")
            files = _inventory(stage)
            _check_package(stage, suffix)
            archive = Path(tmp) / "package.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as dest:
                for path, name in sorted(files, key=lambda pair: pair[1]):
                    data = _read_regular(path)
                    if _xml_name(name):
                        _parse_xml(data).unlink()
                    compression = zipfile.ZIP_DEFLATED
                    # Do not emit a package that our own bomb policy rejects.
                    if len(data) > 1024 * 1024 and (
                        len(data) / max(len(zlib.compress(data)) - 6, 1) > MAX_RATIO
                    ):
                        compression = zipfile.ZIP_STORED
                    dest.writestr(name, data, compress_type=compression)
            if output.exists():
                archive.chmod(stat.S_IMODE(output.stat().st_mode))
            os.replace(archive, output)
        return True, f"Packed {len(files)} parts into {output}"
    except Exception as exc:
        return False, f"Error: {exc}"


def _boolean(value):
    if isinstance(value, bool):
        return value
    if value.lower() in ("true", "1", "yes"):
        return True
    if value.lower() in ("false", "0", "no"):
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_directory")
    parser.add_argument("output_file")
    parser.add_argument("--original")
    parser.add_argument("--validate", type=_boolean, nargs="?", const=True, default=True)
    args = parser.parse_args()
    success, message = pack(args.input_directory, args.output_file, args.original, args.validate)
    print(message, file=sys.stdout if success else sys.stderr)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
