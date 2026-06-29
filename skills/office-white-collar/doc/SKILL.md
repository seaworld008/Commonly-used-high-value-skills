---
name: doc
description: 'Use when the task involves reading, creating, or editing `.docx` documents, especially when formatting or layout fidelity matters; prefer `python-docx` plus the bundled `scripts/render_docx.py` for visual checks.'
zh_description: "用于读取、创建和编辑 `.docx` 文档，尤其适合需要格式和版面保真时。"
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["doc"]'
created_at: "2026-03-04"
updated_at: "2026-06-29"
quality: 3
complexity: "intermediate"
---

# DOCX Skill

## When to use
- Read or review DOCX content where layout matters (tables, diagrams, pagination).
- Create or edit DOCX files with professional formatting.
- Validate visual layout before delivery.

## Workflow
1. Prefer visual review (layout, tables, diagrams).
   - If `soffice` and `pdftoppm` are available, convert DOCX -> PDF -> PNGs.
   - Or use `scripts/render_docx.py` (requires `pdf2image` and Poppler).
   - If these tools are missing, install them or ask the user to review rendered pages locally.
2. Use `python-docx` for edits and structured creation (headings, styles, tables, lists).
3. After each meaningful change, re-render and inspect the pages.
4. If visual review is not possible, extract text with `python-docx` as a fallback and call out layout risk.
5. Keep intermediate outputs organized and clean up after final approval.

## Temp and output conventions
- Use `tmp/docs/` for intermediate files; delete when done.
- Write final artifacts under `output/doc/` when working in this repo.
- Keep filenames stable and descriptive.

## Dependencies (install if missing)
Prefer `uv` for dependency management.

Python packages:
```
uv pip install python-docx pdf2image
```
If `uv` is unavailable:
```
python3 -m pip install python-docx pdf2image
```
System tools (for rendering):
```
# macOS (Homebrew)
brew install libreoffice poppler

# Ubuntu/Debian
sudo apt-get install -y libreoffice poppler-utils
```

If installation isn't possible in this environment, tell the user which dependency is missing and how to install it locally.

## Environment
No required environment variables.

## Rendering commands
DOCX -> PDF:
```
soffice -env:UserInstallation=file:///tmp/lo_profile_$$ --headless --convert-to pdf --outdir $OUTDIR $INPUT_DOCX
```

PDF -> PNGs:
```
pdftoppm -png $OUTDIR/$BASENAME.pdf $OUTDIR/$BASENAME
```

Bundled helper:
```
python3 scripts/render_docx.py /path/to/file.docx --output_dir /tmp/docx_pages
```

## Quality expectations
- Deliver a client-ready document: consistent typography, spacing, margins, and clear hierarchy.
- Avoid formatting defects: clipped/overlapping text, broken tables, unreadable characters, or default-template styling.
- Charts, tables, and visuals must be legible in rendered pages with correct alignment.
- Use ASCII hyphens only. Avoid U+2011 (non-breaking hyphen) and other Unicode dashes.
- Citations and references must be human-readable; never leave tool tokens or placeholder strings.

## Final checks
- Re-render and inspect every page at 100% zoom before final delivery.
- Fix any spacing, alignment, or pagination issues and repeat the render loop.
- Confirm there are no leftovers (temp files, duplicate renders) unless the user asks to keep them.

## Editing Checklist

When modifying an existing `.docx`:

- Preserve section breaks, headers, footers, page numbers, and table structure unless the user asks for layout changes.
- Make a clear distinction between content edits and formatting edits.
- Avoid rebuilding the whole document when a targeted `python-docx` edit can preserve layout.
- For tables, check merged cells, repeated header rows, and column widths after rendering.
- For legal, finance, or policy documents, avoid automatic paraphrasing unless explicitly requested.
- Keep source data and generated render previews in predictable temporary paths.

## Acceptance Criteria

A document task is not complete until:

- The file opens without repair prompts.
- Rendered pages match the intended visual layout.
- Chinese, symbols, bullets, and numbering display correctly.
- The final filename is clear and does not overwrite the user's original unless requested.
- Any limitations, such as unavailable fonts or missing LibreOffice, are reported plainly.
