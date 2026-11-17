#!/usr/bin/env python3
# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Render DOCX to a real PDF and page-N.png files using installed engines.

LibreOffice is selected by SOFFICE_BINARY or PATH; PyMuPDF reads and rasterizes
PDFs. No browser, global profile, macro installation or sandbox override is
used. A new private profile disables macros. DOCX preflight rejects macros,
embedded objects, external relationships/resources and unsafe dynamic fields;
unsupported documents fail rather than silently weakening that boundary.

Default output: INPUT's sibling directory named INPUT's stem. The directory
contains STEM.pdf and page-1.png ... page-N.png. --dpi overrides --width and
--height; otherwise one DPI is calculated from ALL actual PDF page dimensions
so every PNG fits the requested pixel bounds (default 1600 by 2000).
Existing generated pages are replaced only after all pages validate; unrelated
files are preserved. Publication failures restore prior outputs. Callers must
serialize simultaneous writes to the same output directory.
"""

import argparse
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit
import zipfile


SAFE_FIELDS = {"PAGE", "NUMPAGES", "SECTION", "SECTIONPAGES", "REF", "PAGEREF", "SEQ", "TOC"}
RASTER_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp"}


class PublicationError(RuntimeError):
    """Incomplete publication with explicit recovery and partial-output evidence."""

    def __init__(self, message, outputs, recovery_dir):
        super().__init__(message)
        self.outputs = outputs
        self.recovery_dir = recovery_dir


def _fitz():
    try:
        import pymupdf as fitz
    except ImportError as exc:
        raise RuntimeError("PDF inspection/rendering requires installed PyMuPDF") from exc
    return fitz


def _office_binary():
    name = os.environ.get("SOFFICE_BINARY", "soffice")
    binary = shutil.which(name)
    if not binary:
        raise RuntimeError("LibreOffice is unavailable; install it separately or set SOFFICE_BINARY")
    return binary


def ensure_system_tools():
    """Check installed dependencies without starting Office or installing tools."""
    _fitz()
    _office_binary()
    try:
        import PIL.Image  # noqa: F401
        import defusedxml.ElementTree  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("DOCX rendering requires installed Pillow and defusedxml") from exc


def _safe_field(instruction):
    words = instruction.strip().split()
    if not words or words[0].upper() not in SAFE_FIELDS:
        raise ValueError("DOCX contains an unsupported dynamic field; external updates are forbidden")


def _inspect_docx(path):
    """Inspect bounded ZIP/XML data without extracting or executing its content."""
    from defusedxml import ElementTree as ET
    sizes = []
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = {info.filename for info in entries}
        if len(entries) > 10000 or len(entries) != len(names):
            raise ValueError("DOCX has too many or duplicate ZIP members")
        if sum(info.file_size for info in entries) > 256 * 1024 * 1024:
            raise ValueError("DOCX expands beyond the 256 MiB limit")
        if "word/document.xml" not in names or "[Content_Types].xml" not in names:
            raise ValueError("Expected a DOCX OOXML package")
        for info in entries:
            name = info.filename
            pure = PurePosixPath(name)
            if pure.is_absolute() or ".." in pure.parts or "\\" in name or info.flag_bits & 1:
                raise ValueError("Unsafe or encrypted ZIP member")
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("ZIP symlinks are not supported")
            if info.is_dir():
                continue
            lower = name.lower()
            if any(marker in lower for marker in ("vbaproject", "activex/", "embeddings/", "macros/")):
                raise ValueError("DOCX macros and embedded executable objects are forbidden")
            suffix = ".rels" if pure.name == ".rels" else pure.suffix.lower()
            if suffix in RASTER_EXTENSIONS:
                from PIL import Image
                import io
                with Image.open(io.BytesIO(archive.read(info))) as picture:
                    if picture.format not in {"PNG", "JPEG", "GIF", "BMP", "TIFF", "WEBP"}:
                        raise ValueError("Embedded image must be a raster format")
                    if picture.width * picture.height > 40_000_000:
                        raise ValueError("Embedded image is too large")
                    picture.verify()
                continue
            if suffix not in {".xml", ".rels"}:
                raise ValueError(f"Unsupported package resource (cannot verify safely): {name}")
            root = ET.fromstring(archive.read(info))
            fields = []
            for element in root.iter():
                local = element.tag.rsplit("}", 1)[-1]
                attrs = {key.rsplit("}", 1)[-1]: value for key, value in element.attrib.items()}
                if local in {"altChunk", "OLEObject", "object", "control", "subDoc", "attachedTemplate", "mailMerge", "saveThroughXslt"}:
                    raise ValueError(f"Unsupported active DOCX content: {local}")
                if any(key.lower() in {"href", "src"} and value for key, value in attrs.items()):
                    raise ValueError("Inline external resource references are forbidden")
                if local in {"Override", "Default"}:
                    content_type = attrs.get("ContentType", "").lower()
                    if any(marker in content_type for marker in ("macroenabled", "vba", "activex", "oleobject")):
                        raise ValueError("Macro-enabled/active package content is forbidden")
                if local == "Relationship":
                    if attrs.get("TargetMode", "").lower() == "external":
                        # Ordinary hyperlinks are annotations, not fetched
                        # rendering resources. Keep them while blocking linked
                        # images, templates, workbooks and active content.
                        link_type = attrs.get("Type", "")
                        link = urlsplit(attrs.get("Target", ""))
                        if (link_type in {
                                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                                "http://purl.oclc.org/ooxml/officeDocument/relationships/hyperlink",
                            } and link.scheme.lower() in {"http", "https", "mailto"}
                                and not link.username and not link.password
                                and (link.netloc if link.scheme.lower() != "mailto" else link.path)
                                and not any(ord(char) < 32 for char in attrs.get("Target", ""))):
                            continue
                        raise ValueError("External DOCX relationships are forbidden (including linked images/templates)")
                    target = unquote(attrs.get("Target", ""))
                    uri = urlsplit(target)
                    if uri.scheme or uri.netloc or uri.query or uri.fragment or "\\" in target:
                        raise ValueError("Invalid internal DOCX relationship")
                    base = "" if name == "_rels/.rels" else name.rsplit("/_rels/", 1)[0]
                    resolved = posixpath.normpath(target.lstrip("/") if target.startswith("/") else posixpath.join(base, target))
                    if resolved.startswith("../") or resolved not in names:
                        raise ValueError("DOCX relationship escapes or refers to a missing package resource")
                if local == "fldSimple":
                    _safe_field(attrs.get("instr", ""))
                if local == "fldChar":
                    kind = attrs.get("fldCharType")
                    if kind == "begin":
                        fields.append([])
                    elif kind in {"separate", "end"} and fields:
                        if fields[-1] is not None:
                            _safe_field("".join(fields[-1]))
                        if kind == "end":
                            fields.pop()
                        else:
                            fields[-1] = None
                if local == "instrText":
                    if not fields or fields[-1] is None:
                        raise ValueError("Unscoped DOCX field instruction")
                    fields[-1].append(element.text or "")
                if local == "pgSz" and name == "word/document.xml":
                    width, height = int(attrs.get("w", 0)), int(attrs.get("h", 0))
                    if width <= 0 or height <= 0:
                        raise ValueError("Invalid OOXML page dimensions")
                    sizes.append((width / 20, height / 20))  # twips to PDF points
            if fields:
                raise ValueError("Unclosed DOCX field instruction")
    return sizes


def _bounded_dpi(sizes, max_w_px, max_h_px):
    if max_w_px <= 0 or max_h_px <= 0 or not sizes:
        raise ValueError("Positive pixel bounds and explicit page dimensions are required")
    ratios = []
    for width, height in sizes:
        if not all(math.isfinite(value) and value > 0 for value in (width, height)):
            raise ValueError("Invalid page dimensions")
        ratios.extend((max_w_px * 72 / width, max_h_px * 72 / height))
    dpi = math.floor(min(ratios))
    if dpi < 1:
        raise ValueError("Requested bounds are smaller than the page at 1 DPI")
    return dpi


def calc_dpi_via_ooxml_docx(input_path, max_w_px, max_h_px):
    """Use all explicit section sizes (twips); fail if no page size is declared."""
    return _bounded_dpi(_inspect_docx(input_path), max_w_px, max_h_px)


def _pdf_sizes(path):
    with _fitz().open(path) as document:
        if document.needs_pass or not document.is_pdf or not len(document):
            raise ValueError("Expected a nonempty, unencrypted PDF")
        sizes = []
        for page in document:
            sizes.append((page.rect.width, page.rect.height))
            page.get_text()
        return sizes


def calc_dpi_via_pdf(input_path, max_w_px, max_h_px):
    """Use actual rotated page rectangles, including mixed paper sizes."""
    return _bounded_dpi(_pdf_sizes(input_path), max_w_px, max_h_px)


def _soffice_env():
    # Resolve the audited sibling helper, never an unrelated `office` on sys.path.
    helper = Path(__file__).parent / "office" / "soffice.py"
    spec = importlib.util.spec_from_file_location("document_renderer_soffice_env", helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.get_soffice_env()


def run_cmd_no_check(cmd):
    """Run argv directly, with a finite timeout and the audited Office environment."""
    return subprocess.run(list(cmd), env=_soffice_env(), capture_output=True, text=True, timeout=120)


def _output_guard(source, target):
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise ValueError(f"Output is not a regular file: {target}")
    if source.resolve() == target.resolve() or (target.exists() and os.path.samefile(source, target)):
        raise ValueError("Output would overwrite an input file")


def convert_to_pdf(doc_path, user_profile, convert_tmp_dir, stem):
    """Return a validated PDF Path. `user_profile` must be new and inside staging.

    The caller supplies a staging directory, never a user's LibreOffice profile.
    The input is snapshotted, inspected and passed read-only to Office. External
    resource and field rejection is independent of profile setting defaults.
    """
    source = Path(doc_path).absolute()
    root = Path(convert_tmp_dir).absolute()
    profile = Path(user_profile).absolute()
    if source.suffix.lower() != ".docx" or not source.is_file():
        raise ValueError("Conversion requires an existing .docx file")
    if not stem or stem in {".", ".."} or Path(stem).name != stem or "/" in stem or "\\" in stem:
        raise ValueError("PDF stem must be a single filename")
    if profile.exists() or profile.is_symlink() or not profile.resolve().is_relative_to(root.resolve()) or profile.resolve() == root.resolve():
        raise ValueError("A new private profile inside the conversion directory is required")
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"{stem}.pdf"
    _output_guard(source, destination)
    with tempfile.TemporaryDirectory(prefix=".office-convert-", dir=root) as work:
        work = Path(work)
        snapshot = work / "input.docx"
        shutil.copyfile(source, snapshot)
        _inspect_docx(snapshot)
        snapshot.chmod(0o400)
        profile.mkdir(mode=0o700)
        try:
            (profile / "user").mkdir(mode=0o700)
            (profile / "user" / "registrymodifications.xcu").write_text(
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<oor:items xmlns:oor="http://openoffice.org/2001/registry">'
                '<item oor:path="/org.openoffice.Office.Common/Security/Scripting">'
                '<prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop>'
                '<prop oor:name="DisableMacrosExecution" oor:op="fuse"><value>true</value></prop>'
                '</item></oor:items>', encoding="utf-8")
            command = [_office_binary(), f"-env:UserInstallation={profile.as_uri()}",
                       "--headless", "--norestore", "--nodefault", "--nofirststartwizard",
                       "--convert-to", "pdf:writer_pdf_Export", "--outdir", str(work), str(snapshot)]
            result = run_cmd_no_check(command)
            if result.returncode:
                raise RuntimeError(f"LibreOffice exited {result.returncode}: {result.stderr.strip()}")
            produced = work / "input.pdf"
            if not produced.is_file() or produced.is_symlink():
                raise RuntimeError("LibreOffice returned without a new PDF")
            _pdf_sizes(produced)
            _output_guard(source, destination)
            os.replace(produced, destination)
        finally:
            shutil.rmtree(profile)
    return destination


def _publish(source, output_dir, stage, names):
    """Publish a validated set; rollback handled failures, retain unrecovered backups."""
    prior_pages = {path.name for path in output_dir.iterdir() if re.fullmatch(r"page-\d+\.png", path.name)}
    affected = sorted(set(names) | prior_pages)
    for name in affected:
        _output_guard(source, output_dir / name)
    backups = stage / "previous"
    backups.mkdir()
    saved, installed = [], []
    try:
        for name in affected:
            target = output_dir / name
            if target.exists():
                os.replace(target, backups / name)
                saved.append(name)
        for name in names:
            os.replace(stage / name, output_dir / name)
            installed.append(name)
    except BaseException as failure:
        recovery_errors = []
        for name in reversed(installed):
            try:
                (output_dir / name).unlink()
            except OSError as exc:
                recovery_errors.append(f"remove {name}: {exc}")
        for name in saved:
            try:
                os.replace(backups / name, output_dir / name)
            except OSError as exc:
                recovery_errors.append(f"restore {name}: {exc}")
        if recovery_errors:
            remaining = [str(output_dir / name) for name in installed
                         if (output_dir / name).is_file()
                         and (name not in saved or (backups / name).exists())]
            recovery = str(stage) if any(backups.iterdir()) else None
            raise PublicationError("Publication failed; recovery needs attention: "
                                   + "; ".join(recovery_errors), remaining, recovery) from failure
        raise


def _render(doc_path, out_dir, dpi=None, *, width=1600, height=2000):
    if dpi is not None and (not isinstance(dpi, int) or isinstance(dpi, bool) or not 1 <= dpi <= 2400):
        raise ValueError("DPI must be an integer between 1 and 2400")
    if dpi is None and (width <= 0 or height <= 0):
        raise ValueError("Pixel width and height must be positive")
    source = Path(doc_path).absolute()
    output = Path(out_dir).absolute()
    if not source.is_file():
        raise FileNotFoundError(source)
    if output.is_symlink() or (output.exists() and not output.is_dir()):
        raise ValueError("Output directory must be a real directory")
    output.mkdir(parents=True, exist_ok=True)
    pdf_name = source.stem + ".pdf"
    _output_guard(source, output / pdf_name)
    stage = Path(tempfile.mkdtemp(prefix=".docx-render-", dir=output))
    keep_stage = False
    try:
        pdf = stage / pdf_name
        if source.suffix.lower() == ".pdf":
            shutil.copyfile(source, pdf)
        else:
            conversion = stage / "conversion"
            conversion.mkdir()
            converted = convert_to_pdf(source, conversion / "profile", conversion, source.stem)
            os.replace(converted, pdf)
        sizes = _pdf_sizes(pdf)
        actual_dpi = dpi if dpi is not None else _bounded_dpi(sizes, width, height)
        if not isinstance(actual_dpi, int) or isinstance(actual_dpi, bool) or not 1 <= actual_dpi <= 2400:
            raise ValueError("DPI must be an integer between 1 and 2400")
        for w, h in sizes:
            if math.ceil(w * actual_dpi / 72) * math.ceil(h * actual_dpi / 72) > 40_000_000:
                raise ValueError("Requested page raster exceeds 40 million pixels")
        from PIL import Image
        names = [pdf_name]
        dimensions = []
        with _fitz().open(pdf) as document:
            for index, page in enumerate(document, 1):
                name = f"page-{index}.png"
                pixmap = page.get_pixmap(dpi=actual_dpi, alpha=False)
                pixmap.save(str(stage / name))
                with Image.open(stage / name) as picture:
                    picture.load()
                    if picture.format != "PNG" or picture.size != (pixmap.width, pixmap.height):
                        raise RuntimeError(f"Invalid page image: {index}")
                    if dpi is None and (picture.width > width or picture.height > height):
                        raise RuntimeError("Rendered image exceeds requested pixel bounds")
                    dimensions.append(list(picture.size))
                names.append(name)
        if len(names) - 1 != len(sizes):
            raise RuntimeError("PNG count does not match PDF page count")
        try:
            _publish(source, output, stage, names)
        except BaseException:
            # A failed rollback must not erase the only remaining old files.
            keep_stage = (stage / "previous").exists() and any((stage / "previous").iterdir())
            if keep_stage:
                print(f"Recovery files retained at {stage}", file=sys.stderr)
            raise
        return {"status": "success", "dpi": actual_dpi, "pages": len(sizes),
                "dimensions": dimensions, "outputs": [str(output / name) for name in names]}
    finally:
        if not keep_stage:
            shutil.rmtree(stage)


def rasterize(doc_path, out_dir, dpi):
    """Return page PNG Paths after the complete PDF/PNG set has been published."""
    result = _render(doc_path, out_dir, dpi)
    return [Path(path) for path in result["outputs"] if path.endswith(".png")]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_path", type=str)
    parser.add_argument("--output_dir", type=str)
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=2000)
    parser.add_argument("--dpi", type=int)
    args = parser.parse_args()
    source = Path(args.input_path)
    output = args.output_dir or str(source.with_suffix(""))
    try:
        result = _render(source, output, args.dpi, width=args.width, height=args.height)
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc),
                          "outputs": getattr(exc, "outputs", []),
                          "recovery_dir": getattr(exc, "recovery_dir", None)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
