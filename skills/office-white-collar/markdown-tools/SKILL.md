---
name: markdown-tools
description: 'Convert PDF, DOCX, PPTX, and other documents to Markdown, preserving tables, images, and structure with the appropriate extraction tool.'
zh_description: "把文档转换为保留结构、表格和图片的 Markdown。"
version: "1.0.2"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["markdown", "tools"]'
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 4
complexity: "intermediate"
---

# Markdown Tools

Convert documents to high-quality markdown with intelligent multi-tool orchestration.

## When to Use

Use this skill when the user wants to:

- convert PDF, DOCX, PPTX, or XLSX into Markdown
- extract images alongside Markdown output
- compare multiple converters for quality
- validate a conversion before downstream LLM use

## Usage

Recommended flow:

```text
choose quick or heavy mode
-> convert with best-fit tool(s)
-> validate output quality
-> extract images if needed
-> merge or refine outputs
```

## Dual Mode Architecture

| Mode | Speed | Quality | Use Case |
|------|-------|---------|----------|
| **Quick** (default) | Fast | Good | Drafts, simple documents |
| **Heavy** | Slower | Heuristic selection | Final documents, complex layouts |

## Quick Start

### Installation

```bash
# Required: PDF/DOCX/PPTX support
uv tool install "markitdown[pdf]"
pip install pymupdf4llm
brew install pandoc
```

### Basic Conversion

```bash
# Quick Mode (default) - fast, single best tool
uv run --with pymupdf4llm --with markitdown scripts/convert.py document.pdf -o output.md

# Heavy Mode - sequential converters, select one complete result and combine image inventories
uv run --with pymupdf4llm --with markitdown scripts/convert.py document.pdf -o output.md --heavy

# Check available tools (current parser requires an input token; list mode does not convert it)
uv run scripts/convert.py document.pdf --list-tools
```

## Tool Selection Matrix

| Format | Quick Mode Tool | Heavy Mode Tools |
|--------|----------------|------------------|
| PDF | pymupdf4llm | pymupdf4llm + markitdown |
| DOCX | pandoc | pandoc + markitdown |
| PPTX | markitdown | markitdown + pandoc |
| XLSX | markitdown | markitdown |

### Tool Characteristics

- **pymupdf4llm**: LLM-optimized PDF conversion with native table detection and image extraction
- **markitdown**: Microsoft's universal converter, good for Office formats
- **pandoc**: Excellent structure preservation for DOCX/PPTX

## Heavy Mode Workflow

Heavy mode runs available converters sequentially, selects one complete Markdown result by heuristic score, and combines image inventories. It does not select or merge the best text segment from each converter.

1. Run applicable converters in sequence.
2. Discard failed or empty results.
3. Score complete Markdown results with the bundled heuristic.
4. Return the highest-scoring complete text and combined image inventory.

A higher score does not prove source completeness. Compare tables, headings and unique passages against the source; another converter may retain text absent from the selected result. For segment-level merging, explicitly use `scripts/merge_outputs.py` (below) and verify against the source.

## Image Extraction

```bash
# Extract images with metadata
uv run --with pymupdf scripts/extract_pdf_images.py document.pdf -o ./assets

# Generate markdown references file
uv run --with pymupdf scripts/extract_pdf_images.py document.pdf --markdown refs.md
```

Output:
- Images: `assets/img_page1_1.png`, `assets/img_page2_1.jpg`
- Metadata: `assets/images_metadata.json` (page, position, dimensions)

## Quality Validation

```bash
# Validate conversion quality
uv run --with pymupdf scripts/validate_output.py document.pdf output.md

# Generate HTML report
uv run --with pymupdf scripts/validate_output.py document.pdf output.md --report report.html
```

### Quality Metrics

| Metric | Pass | Warn | Fail |
|--------|------|------|------|
| Text Retention | >95% | 85-95% | <85% |
| Table Retention | 100% | 90-99% | <90% |
| Image Retention | 100% | 80-99% | <80% |

## Merge Outputs Manually

```bash
# Merge multiple markdown files
python scripts/merge_outputs.py output1.md output2.md -o merged.md

# Show segment attribution
python scripts/merge_outputs.py output1.md output2.md -o merged.md --verbose
```

## Path Conversion (Windows/WSL)

```bash
# Windows → WSL conversion
python scripts/convert_path.py "C:\Users\name\Documents\file.pdf"
# Output: /mnt/c/Users/name/Documents/file.pdf
```

## Common Issues

**"No conversion tools available"**
```bash
# Install all tools
pip install pymupdf4llm
uv tool install "markitdown[pdf]"
brew install pandoc
```

**FontBBox warnings during PDF conversion**
- Harmless font parsing warnings, output is still correct

**Images missing from output**
- Use Heavy Mode for better image preservation
- Or extract separately with `scripts/extract_pdf_images.py`

**Tables broken in output**
- Compare converter outputs against the source; Heavy Mode selects a complete document, not individual tables
- Or validate with `scripts/validate_output.py`

## Bundled Scripts

| Script | Purpose |
|--------|---------|
| `convert.py` | Main orchestrator with Quick/Heavy mode |
| `merge_outputs.py` | Merge multiple markdown outputs |
| `validate_output.py` | Quality validation with HTML report |
| `extract_pdf_images.py` | PDF image extraction with metadata |
| `convert_path.py` | Windows to WSL path converter |

## References

- `references/heavy-mode-guide.md` - Detailed Heavy Mode documentation
- `references/tool-comparison.md` - Tool capabilities comparison
- `references/conversion-examples.md` - Batch operation examples
