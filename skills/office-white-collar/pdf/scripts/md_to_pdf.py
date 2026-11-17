#!/usr/bin/env python3
# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Render UTF-8 Markdown with installed markdown-it-py and PyMuPDF.

No browser, shell, network fetch, raw HTML or document-supplied CSS is used.
Chinese fallback fonts, headings, nested lists, tables and fenced code are
handled by MuPDF's HTML layout engine. Images are disabled unless the caller
supplies an explicit local resource root. Only decoded raster images contained
in that root are passed to the renderer. Install dependencies separately.

CLI: md_to_pdf.py INPUT.md [OUTPUT.pdf] [--resource-root DIRECTORY]
The output defaults to INPUT.pdf. A completed, parsed PDF replaces the output
atomically; input files and previous output survive rendering failures.
"""

import argparse
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import unquote, urlsplit


CSS = """
body { font-family: sans-serif; font-size: 11pt; line-height: 1.5; }
h1 { font-size: 24pt; } h2 { font-size: 18pt; } h3 { font-size: 14pt; }
p, li { overflow-wrap: anywhere; }
pre { font-family: monospace; font-size: 9pt; white-space: pre-wrap;
      background-color: #f2f2f2; padding: 8pt; }
code { font-family: monospace; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0; }
th, td { border: 0.5pt solid #aaaaaa; padding: 5pt; }
th { background-color: #eeeeee; }
blockquote { border-left: 2pt solid #888888; padding-left: 10pt; }
img { max-width: 100%; }
"""


def _ensure_list_spacing(text):
    """Normalize line endings; CommonMark parses lists without injected blanks."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _dependencies():
    try:
        import pymupdf as fitz
        from markdown_it import MarkdownIt
    except ImportError as exc:
        raise RuntimeError("Rendering requires installed PyMuPDF and markdown-it-py") from exc
    return fitz, MarkdownIt


def _safe_output(source, output):
    if output.is_symlink() or (output.exists() and not output.is_file()):
        raise ValueError(f"Output must be a regular file, not a symlink/directory: {output}")
    if source.resolve() == output.resolve() or (output.exists() and os.path.samefile(source, output)):
        raise ValueError("Input and output must be different files")


def _prepare_images(tokens, source, resource_root, assets):
    """Give the layout engine only re-encoded, explicitly authorized images."""
    root = Path(resource_root).resolve(strict=True) if resource_root is not None else None
    if root is not None and not root.is_dir():
        raise ValueError("Resource root must be a directory")
    count = 0
    pending = list(tokens)
    while pending:
        token = pending.pop()
        pending.extend(token.children or [])
        if token.type == "link_open":
            href = token.attrGet("href") or ""
            if not href.startswith("#") and urlsplit(href).scheme.lower() not in {"http", "https", "mailto"}:
                raise ValueError("Only web, mailto and document-fragment links are supported")
        if token.type != "image":
            continue
        if root is None:
            raise ValueError("Images are disabled; authorize a local --resource-root")
        uri = urlsplit(token.attrGet("src") or "")
        if uri.scheme or uri.netloc or uri.query or uri.fragment:
            raise ValueError("Only local raster image paths are allowed; network/data URLs are disabled")
        relative = Path(unquote(uri.path))
        if relative.is_absolute():
            raise ValueError("Image paths must be relative to the Markdown file")
        path = (source.parent / relative).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("Image escapes the authorized resource root")
        try:
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("Local images require installed Pillow") from exc
        with Image.open(path) as picture:
            if picture.format not in {"PNG", "JPEG", "WEBP", "GIF"}:
                raise ValueError("Only PNG, JPEG, WEBP and GIF raster images are supported")
            if picture.width * picture.height > 40_000_000:
                raise ValueError("Image exceeds 40 million pixels")
            picture.load()
            name = f"asset-{count}.png"
            picture.convert("RGBA").save(assets / name)
        token.attrSet("src", name)
        count += 1


def markdown_to_pdf(md_file, pdf_file, *, resource_root=None):
    """Return the published Path, or raise without replacing previous output."""
    source = Path(md_file).absolute()
    output = Path(pdf_file).absolute()
    if not source.is_file():
        raise FileNotFoundError(source)
    _safe_output(source, output)
    text = _ensure_list_spacing(source.read_text(encoding="utf-8"))
    if not text.strip():
        raise ValueError("Markdown input is empty")
    fitz, MarkdownIt = _dependencies()
    parser = MarkdownIt("commonmark", {"html": False}).enable("table").enable("strikethrough")
    tokens = parser.parse(text)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".markdown-pdf-", dir=output.parent) as work:
        stage = Path(work)
        assets = stage / "assets"
        assets.mkdir()
        _prepare_images(tokens, source, resource_root, assets)
        body = parser.renderer.render(tokens, parser.options, {})
        story = fitz.Story(html=body, user_css=CSS, archive=fitz.Archive(str(assets)))
        pending = stage / "document.pdf"
        def next_page(number, occupied):
            if number >= 2000:
                raise RuntimeError("Layout exceeded 2000 pages; content may not fit the page")
            if number and fitz.Rect(occupied).is_empty:
                raise RuntimeError("Content cannot fit the page")
            return (fitz.Rect(0, 0, 595.276, 841.890),
                    fitz.Rect(42, 42, 553.276, 799.890), None)

        # This public API preserves HTTP/mail links as PDF annotations without
        # fetching them. The only renderer archive is our normalized raster set.
        with story.write_with_links(next_page) as result:
            pages = len(result)
            result.save(pending)
        with fitz.open(pending) as document:
            if document.needs_pass or len(document) != pages or not pages:
                raise RuntimeError("Renderer did not create a complete readable PDF")
            for page in document:
                page.get_text()  # Parse actual page content, not just the PDF header.
        _safe_output(source, output)
        os.replace(pending, output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("md_file")
    parser.add_argument("pdf_file", nargs="?")
    parser.add_argument("--resource-root", help="Explicitly authorize local raster images under this directory")
    args = parser.parse_args()
    output = args.pdf_file or str(Path(args.md_file).with_suffix(".pdf"))
    try:
        path = markdown_to_pdf(args.md_file, output, resource_root=args.resource_root)
    except Exception as exc:
        print(f"Conversion failed: {exc}", file=sys.stderr)
        return 1
    print(f"Created PDF: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
