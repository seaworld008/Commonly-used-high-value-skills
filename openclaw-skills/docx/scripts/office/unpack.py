# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Unpack DOCX, PPTX and XLSX using private, bounded staging."""

import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import zipfile

_spec = importlib.util.spec_from_file_location(
    "_office_package_io", Path(__file__).with_name("pack.py"))
_io = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_io)


def _pretty_print_xml(xml_file):
    # Generic pretty-printers insert whitespace into mixed content.
    _io._condense_xml(xml_file)


def _escape_smart_quotes(xml_file):
    # Unicode quotes are legal XML characters; retain user text verbatim.
    _io._condense_xml(xml_file)


def _members(archive):
    members = archive.infolist()
    if len(members) > _io.MAX_FILES:
        raise ValueError("archive entry count exceeds limit")
    total = 0
    for member in members:
        if member.orig_filename != member.filename:
            raise ValueError("truncated archive path")
        _io._part_name(member.filename)
        mode = member.external_attr >> 16
        kind = stat.S_IFMT(mode)
        allowed = (0, stat.S_IFDIR) if member.is_dir() else (0, stat.S_IFREG)
        if kind not in allowed or member.flag_bits & 1:
            raise ValueError("special, symlink, or encrypted archive entry")
        if member.is_dir() and member.file_size:
            raise ValueError("directory entry has content")
        total += member.file_size
        if member.file_size > _io.MAX_FILE_BYTES or total > _io.MAX_TOTAL_BYTES:
            raise ValueError("archive expanded size exceeds limit")
        if member.file_size > 1024 * 1024 and (
            member.file_size / max(member.compress_size, 1) > _io.MAX_RATIO
        ):
            raise ValueError("archive compression ratio exceeds limit")
    _io._check_names((m.filename, m.is_dir()) for m in members)
    return members


def unpack(input_file, output_directory, merge_runs=True, simplify_redlines=True):
    """Return (success, message); restore existing output on publish failure."""
    try:
        source = _io._safe_directory(input_file)
        output = _io._safe_directory(output_directory)
        suffix = source.suffix.lower()
        if suffix not in _io.FAMILIES or not source.is_file():
            raise ValueError("input must be a .docx, .pptx, or .xlsx file")
        if source.stat().st_size > _io.MAX_TOTAL_BYTES:
            raise ValueError("archive file size exceeds limit")
        if source.is_relative_to(output):
            raise ValueError("input cannot be inside output directory")
        if not output.parent.is_dir() or (output.exists() and not output.is_dir()):
            raise ValueError("output parent must exist; output must be a directory")
        # Own cleanup explicitly: an unrecovered backup must outlive this call.
        tmp = Path(tempfile.mkdtemp(prefix="office-unpack-", dir=_io._temp_root())).resolve()
        preserve_backup = False
        try:
            stage = tmp / "parts"
            stage.mkdir()
            count = 0
            with zipfile.ZipFile(source) as archive:
                for member in _members(archive):
                    target = stage / member.filename
                    if member.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    limit = _io.MAX_XML_BYTES if _io._xml_name(member.filename) else _io.MAX_FILE_BYTES
                    with archive.open(member) as stream:
                        data = stream.read(limit + 1)
                    if len(data) > limit or len(data) != member.file_size:
                        raise ValueError("archive member size mismatch or size limit")
                    if _io._xml_name(member.filename):
                        _io._parse_xml(data).unlink()
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    count += 1
            _io._check_package(stage, suffix)
            stats = []
            if suffix == ".docx":
                for enabled, name in ((merge_runs, "merge_runs"),
                                      (simplify_redlines, "simplify_redlines")):
                    if enabled:
                        module = _io._load_local(Path(__file__).parent / f"helpers/{name}.py",
                                                 f"_office_{name}")
                        changed, message = getattr(module, name)(str(stage))
                        if message.startswith("Error"):
                            raise ValueError(message)
                        stats.append(message)
            # No destination changes before the same-filesystem check.
            if stage.stat().st_dev != output.parent.stat().st_dev:
                raise ValueError("TMPDIR and output must share a filesystem for atomic publication")
            backup = tmp / "previous-output"
            existed = output.exists()
            if existed:
                os.replace(output, backup)
                preserve_backup = True
            try:
                os.replace(stage, output)
            except BaseException as publish_error:
                if existed:
                    try:
                        # A different process may have created another output.
                        # Never replace that directory or follow a new symlink.
                        if output.exists() or output.is_symlink():
                            raise FileExistsError(f"output appeared during rollback: {output}")
                        os.replace(backup, output)
                    except BaseException as restore_error:
                        raise RuntimeError(
                            f"publication failed: {publish_error}; "
                            f"rollback failed: {restore_error}; "
                            f"previous output preserved at {backup}"
                        ) from restore_error
                    preserve_backup = False
                raise
            preserve_backup = False
        finally:
            if not preserve_backup:
                shutil.rmtree(tmp, ignore_errors=True)
        detail = "; ".join(stats)
        return True, f"Unpacked {count} parts into {output}" + (f"; {detail}" if detail else "")
    except Exception as exc:
        return False, f"Error: {exc}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file")
    parser.add_argument("output_directory")
    parser.add_argument("--merge-runs", type=_io._boolean, nargs="?", const=True, default=True)
    parser.add_argument("--simplify-redlines", type=_io._boolean, nargs="?", const=True, default=True)
    args = parser.parse_args()
    success, message = unpack(args.input_file, args.output_directory,
                              args.merge_runs, args.simplify_redlines)
    print(message, file=sys.stdout if success else sys.stderr)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
