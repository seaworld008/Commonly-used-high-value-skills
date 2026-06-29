---
name: pdf-creator
description: 'Create PDF documents from markdown with proper Chinese font support using weasyprint. This skill should be used when converting markdown to PDF, generating formal documents (legal, trademark filings, reports), or when Chinese typography is required. Triggers include "convert to PDF", "generate PDF", "markdown to PDF", or any request for creating printable documents.'
zh_description: "用于将 Markdown 转为支持中文字体和正式排版的 PDF 文档。"
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["creator", "pdf"]'
created_at: "2026-03-04"
updated_at: "2026-06-29"
quality: 2
complexity: "intermediate"
---

# PDF Creator

Create professional PDF documents from markdown with proper Chinese font support.

## Quick Start

Convert a single markdown file:

```bash
cd /Users/tiansheng/Workspace/python/claude-code-skills/pdf-creator
uv run --with weasyprint --with markdown scripts/md_to_pdf.py input.md output.pdf
```

Batch convert multiple files:

```bash
uv run --with weasyprint --with markdown scripts/batch_convert.py *.md --output-dir ./pdfs
```

macOS ARM (Homebrew) 的 `DYLD_LIBRARY_PATH` 会自动检测配置，无需手动设置。

## Font Configuration

The scripts use these Chinese fonts (with fallbacks):

| Font Type | Primary | Fallbacks |
|-----------|---------|-----------|
| Body text | Songti SC | SimSun, STSong, Noto Serif CJK SC |
| Headings | Heiti SC | SimHei, STHeiti, Noto Sans CJK SC |

## Output Specifications

- **Page size**: A4
- **Margins**: 2.5cm top/bottom, 2cm left/right
- **Body font**: 12pt, 1.8 line height
- **Max file size**: Designed to stay under 2MB for form submissions

## Common Use Cases

1. **Legal documents**: Trademark filings, contracts, evidence lists
2. **Reports**: Business reports, technical documentation
3. **Formal letters**: Official correspondence requiring print format

## Recommended Workflow

1. Confirm the target document type, required page size, language mix, and whether the PDF will be printed, uploaded, or archived.
2. Normalize the source markdown before conversion: use one H1 title, hierarchical headings, explicit tables, and local image paths.
3. Keep legal or filing documents conservative: avoid decorative fonts, low-contrast colors, complex backgrounds, or CSS that may rasterize text.
4. Run a single-file conversion first, inspect the output visually, then batch convert only after the style and font behavior are verified.
5. Preserve the markdown source next to the generated PDF so future edits are reproducible and the PDF is treated as an output artifact.

## Markdown Preparation Checklist

- Use UTF-8 source files and avoid mixed encodings copied from word processors.
- Prefer standard markdown tables for tabular evidence, dates, fees, or filing metadata.
- Use relative image paths and verify every image exists before conversion.
- Escape literal angle brackets, underscores, and pipes when they are part of legal names or evidence text.
- Keep very wide tables out of A4 portrait PDFs; split them or use landscape-specific styling if needed.
- Add explicit page-break markers only when the receiving authority or template requires stable pagination.

## Validation Checklist

- Open the generated PDF locally and confirm Chinese characters are selectable text, not boxes or rasterized screenshots.
- Check that headings, numbered lists, tables, and links render in the expected order.
- Confirm file size constraints before upload, especially for trademark, legal, visa, or government filing portals.
- Print or preview at 100% scale when margins, signatures, seals, or stamps matter.
- If the PDF will be submitted externally, compare the first and last pages against the source markdown after every regeneration.

## Boundary Conditions

- Do not use this skill for interactive forms, digitally signed PDFs, OCR repair, or scanned-document cleanup.
- Do not manually edit generated PDFs when the source markdown can be corrected and regenerated.
- If exact Word/PowerPoint layout preservation is required, use a document-conversion workflow instead of markdown-to-PDF.
- If the document contains confidential filings, keep temporary files local and avoid uploading assets to third-party converters.

## Troubleshooting

**Problem**: Chinese characters display as boxes
**Solution**: Ensure Songti SC or other Chinese fonts are installed on the system

**Problem**: `weasyprint` import error
**Solution**: Run with `uv run --with weasyprint --with markdown` to ensure dependencies

**Problem**: Tables overflow the page
**Solution**: Reduce column count, abbreviate headers, split the table by topic, or add a narrow-table CSS rule before conversion.

**Problem**: Images are missing in the PDF
**Solution**: Resolve image paths relative to the markdown file, avoid remote-only image URLs, and rerun conversion from the project root.

**Problem**: Output looks different on another machine
**Solution**: Check installed font names and WeasyPrint version, then pin the conversion command in a script for repeatability.
