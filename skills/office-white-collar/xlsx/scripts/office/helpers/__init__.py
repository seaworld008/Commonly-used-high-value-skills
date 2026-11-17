# Adapted from anthropics/skills: skills/xlsx/scripts/office/helpers/__init__.py
# Source commit: e4bb5d960d87126ff3b3a8af1a104b7db67560ba (Apache-2.0).
# SPDX-License-Identifier: Apache-2.0
# Local modifications Copyright (c) 2026 seaworld008.
# Local changes: closed dependencies, API compatibility, safe offline validation.
import os
import posixpath
import re
import stat
import tempfile
import urllib.parse
import zipfile
from pathlib import Path, PureWindowsPath

OOXML_FAMILY = {
    ".docx": "docx",
    ".dotx": "docx",
    ".pptx": "pptx",
    ".potx": "pptx",
    ".xlsx": "xlsx",
    ".xltx": "xlsx",
}

_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")

SLIDE_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"


def one_line(text: str, limit: int) -> str:
    return "".join(c if c.isprintable() else c.encode("unicode_escape").decode() for c in text)[:limit]


def names_another_root(name: str) -> bool:
    return bool(PureWindowsPath(name).anchor)


def opc_target(target: str, source_part: str, target_mode: str = "") -> str | None:
    if not target:
        return None
    if target_mode.lower() == "external":
        return None
    target = urllib.parse.unquote(target)

    if _SCHEME_RE.match(target):
        return None

    if "\\" in target:
        raise ValueError(f"relationship target is not a POSIX part name: {target!r}")

    if target.startswith("/"):
        joined = target.lstrip("/")
    else:
        joined = posixpath.join(posixpath.dirname(source_part), target)

    parts: list[str] = []
    for segment in posixpath.normpath(joined).split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            if not parts:
                raise ValueError(f"relationship target escapes the package: {target!r}")
            parts.pop()
        else:
            parts.append(segment)

    if not parts:
        raise ValueError(f"relationship target resolves to nothing: {target!r}")
    if names_another_root("/".join(parts)):
        raise ValueError(f"relationship target is not a part name: {target!r}")
    return "/".join(parts)


def rels_source_part(rels_file: Path, unpacked_dir: Path) -> str:
    owner_dir = rels_file.parent.parent.relative_to(unpacked_dir)
    part = posixpath.join(owner_dir.as_posix(), rels_file.name[: -len(".rels")])
    return part.removeprefix("./")


def part_text(data: bytes) -> str:
    return data.decode("utf-8", "surrogateescape")


XML_SPACE = " \t\r\n"


def rendered_text(text: str, preserve: bool) -> str:
    return text if preserve else text.strip(XML_SPACE)


def safe_extract(zf: zipfile.ZipFile, dest: Path) -> None:
    validate_archive(zf)
    dest = Path(dest)
    assert_regular_path(dest, directory=True)
    check_tree(dest)
    for member in zf.infolist():
        target = dest / member.filename
        assert_regular_path(target, missing=True)
        if target.exists() and not member.is_dir():
            raise ValueError(f"archive would overwrite existing file: {member.filename}")
    for member in zf.infolist():
        zf.extract(member, dest)


def folder_entries(package: Path) -> list[str]:
    with zipfile.ZipFile(package) as zf:
        return [info.filename for info in zf.infolist() if info.is_dir()]


def rezip(src_dir: Path, out_path: Path) -> None:
    check_tree(src_dir)
    assert_regular_path(out_path, missing=True)
    files = sorted(p for p in src_dir.rglob("*") if p.is_file())
    ct = src_dir / "[Content_Types].xml"
    fd, tmp_name = tempfile.mkstemp(
        prefix=out_path.name + ".", suffix=".tmp", dir=out_path.parent
    )
    tmp_out = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as fh:
            with zipfile.ZipFile(fh, "w", zipfile.ZIP_DEFLATED) as zf:
                if ct.exists():
                    zf.write(ct, ct.relative_to(src_dir), compress_type=zipfile.ZIP_STORED)
                for f in files:
                    if f == ct:
                        continue
                    zf.write(f, f.relative_to(src_dir))
        if out_path.exists():
            mode = out_path.stat().st_mode & 0o777
        else:
            umask = os.umask(0)
            os.umask(umask)
            mode = 0o666 & ~umask
        os.chmod(tmp_out, mode)
        os.replace(tmp_out, out_path)
    finally:
        if tmp_out.exists():
            tmp_out.unlink()


# Local safety helpers, Copyright (c) 2026 seaworld008.
def assert_regular_path(path, *, directory=False, missing=False):
    """Reject symbolic links and special files, including in path ancestors."""
    path = Path(path).absolute()
    for item in reversed((path, *path.parents)):
        try:
            mode = item.lstat().st_mode
        except FileNotFoundError:
            if missing:
                continue
            raise
        if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
            raise ValueError(f"symlink or non-regular path not allowed: {item}")
        if item != path and not stat.S_ISDIR(mode):
            raise ValueError(f"parent is not a directory: {item}")
    if path.exists() and directory and not path.is_dir():
        raise ValueError(f"not a directory: {path}")
    return path


def check_tree(root, *, xml=False):
    root = assert_regular_path(root, directory=True)
    for path in root.rglob('*'):
        assert_regular_path(path)
        if xml and path.is_file() and path.name.endswith(('.xml', '.rels')):
            safe_parse(path)
    return root


def validate_archive(zf):
    """Inspect every member before extracting or consuming any package part."""
    seen = set()
    total = 0
    for info in zf.infolist():
        name = info.filename
        parts = name.rstrip('/').split('/')
        mode = stat.S_IFMT(info.external_attr >> 16)
        if (not name or names_another_root(name) or '\\' in name
                or any(p in ('', '.', '..') for p in parts)
                or mode not in (0, stat.S_IFREG, stat.S_IFDIR)
                or (mode == stat.S_IFDIR and not info.is_dir())
                or (mode == stat.S_IFREG and info.is_dir())):
            raise ValueError(f"unsafe archive entry: {name!r}")
        normalized = name.rstrip('/')
        if normalized in seen:
            raise ValueError(f"duplicate archive entry: {name!r}")
        seen.add(normalized)
        total += info.file_size
    if len(seen) > 100000 or total > 512 * 1024 * 1024:
        raise ValueError('package exceeds validation resource limit')
    files = {i.filename for i in zf.infolist() if not i.is_dir()}
    for name in seen:
        if any('/'.join(name.split('/')[:i]) in files for i in range(1, len(name.split('/')))):
            raise ValueError(f"archive file/directory conflict: {name}")


def safe_parse(source):
    """Parse XML without DTDs, external entities, or network access."""
    from io import BytesIO
    from lxml import etree
    if hasattr(source, 'read'):
        data = source.read()
    else:
        data = assert_regular_path(source).read_bytes()
    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)
    document = etree.parse(BytesIO(data), parser)
    if document.docinfo.doctype:
        raise etree.XMLSyntaxError('DTD declarations are forbidden', 0, 0, 0)
    return document
