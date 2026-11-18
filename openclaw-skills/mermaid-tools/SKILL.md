---
name: mermaid-tools
description: Extract Mermaid diagrams from Markdown and render PNG images with the bundled tools when a diagram image or batch conversion is needed.
zh_description: "提取 Markdown 中的 Mermaid 图并渲染为图片。"
version: "1.0.3"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: ["mermaid", "tools"]
created_at: "2026-03-04"
updated_at: "2026-11-18"
quality: 4
complexity: "intermediate"
---

# Mermaid Tools

## Overview

This skill enables extraction of Mermaid diagrams from markdown files and generation of high-quality PNG images. The skill bundles `extract-and-generate.sh`, `extract_diagrams.py`, and `puppeteer-config.json`. Rendering requires external `mmdc` and Chrome. The bundled browser configuration targets Linux/WSL by default; set `PUPPETEER_EXECUTABLE_PATH` to the permitted Chrome executable on other hosts and verify browser compatibility there.

## Core Workflow

### Standard Diagram Extraction and Generation

Extract Mermaid diagrams from a markdown file and generate PNG images using the bundled `extract-and-generate.sh` script:

```bash
bash "<SKILL_ROOT>/scripts/extract-and-generate.sh" "<markdown_file>" "<output_directory>"
```

**Parameters:**
- `<markdown_file>`: Path to the markdown file containing Mermaid diagrams
- `<output_directory>`: (Optional) Directory for output files. Defaults to `<markdown_file_directory>/diagrams`

**Example:**
```bash
bash "<SKILL_ROOT>/scripts/extract-and-generate.sh" "/path/to/document.md" "/path/to/output"
```

### What the Script Does

1. **Extracts** Mermaid fenced code blocks, supporting backticks, tildes, whitespace before the language label and matching fence lengths. Mermaid text inside an outer example fence is ignored.
2. **Numbers** them sequentially (01, 02, 03, etc.) in order of appearance
3. **Stages** this run's `.mmd` files and explicit input manifest in a private batch directory under `TMPDIR` (or the output directory if unset). A valid document without diagrams succeeds with an empty manifest; read or encoding errors fail.
4. **Renders and validates** each current input's PNG with smart sizing, without scanning historical output files.
5. **Publishes each successful pair** of `.mmd` and PNG together using destination-local publication copies and backups. Reported publication errors roll back replaced files. Rendering or validation failures leave the old published pair unchanged; failed source inputs are saved in a separate `failed-mermaid.*` diagnostic directory.
6. **Aggregates errors** across diagrams and returns nonzero for any rendering, validation or publication failure. Other successful pairs can still be published. Review the per-file summary and inspect the images for semantic/visual correctness.

### Output Files

For each diagram, the script generates:
- `01-diagram-name.mmd` - Extracted Mermaid code
- `01-diagram-name.png` - High-resolution PNG image

The numbering ensures diagrams maintain their order from the source document.

The standalone `extract_diagrams.py` only extracts source files into its requested directory; use a scratch directory when reviewing input, and use the batch shell entry point for protected source/PNG publication.

## Advanced Usage

### Custom Dimensions and Scaling

Override default dimensions using environment variables:

```bash
MERMAID_WIDTH=1600 MERMAID_HEIGHT=1200 bash "<SKILL_ROOT>/scripts/extract-and-generate.sh" "<markdown_file>" "<output_directory>"
```

**Available variables:**
- `MERMAID_WIDTH` (default: 1200) - Base width in pixels
- `MERMAID_HEIGHT` (default: 800) - Base height in pixels
- `MERMAID_SCALE` (default: 2) - Scale factor for high-resolution output

### High-Resolution Output for Presentations

```bash
MERMAID_WIDTH=2400 MERMAID_HEIGHT=1800 MERMAID_SCALE=4 bash "<SKILL_ROOT>/scripts/extract-and-generate.sh" "<markdown_file>" "<output_directory>"
```

### Print-Quality Output

```bash
MERMAID_SCALE=5 bash "<SKILL_ROOT>/scripts/extract-and-generate.sh" "<markdown_file>" "<output_directory>"
```

## Smart Sizing Feature

The script automatically adjusts dimensions based on diagram type (detected from filename):

- **Timeline/Gantt**: 2400×400 (wide and short)
- **Architecture/System/Caching**: 2400×1600 (large and detailed)
- **Monitoring/Workflow/Sequence/API**: 2400×800 (wide for process flows)
- **Default**: 1200×800 (standard size)

Context-aware naming in the extraction process helps trigger appropriate smart sizing.

## Important Principles

### Use Bundled Scripts

Use the extraction helper at the actual installed `<SKILL_ROOT>`. The shell script resolves its helper/config paths from its own location; changing the working directory is not required. Use absolute input/output paths.

### Browser Isolation and Acceptance

The bundled `puppeteer-config.json` keeps Chrome sandboxing enabled. If the configured browser cannot run within host permissions, report rendering blocked or use an available permitted renderer; do not add sandbox-disabling flags as an automatic fix.

The script verifies PNG structure and CRCs through the final IEND, and aggregates generation, validation and publication errors. These checks do not prove visual correctness; inspect labels, layout and expected diagram count in the resulting images.

Pair publication restores previous files on handled filesystem errors. Two separate public filenames cannot be replaced in one atomic filesystem operation: abrupt process termination or power loss during publication requires checking both files and any retained `.mermaid-publish.*` recovery directory. If rollback itself fails, the script reports incomplete recovery and retains backups; do not treat that run as successful.

## Prerequisites Verification

Before running the script, verify dependencies are installed:

1. **mermaid-cli**: `mmdc --version`
2. **Google Chrome**: `google-chrome-stable --version`
3. **Python 3**: `python3 --version`

If any are missing, consult `references/setup_and_troubleshooting.md` for installation instructions.

## Troubleshooting

For detailed troubleshooting guidance, refer to `references/setup_and_troubleshooting.md`, which covers:

- Browser launch failures
- Permission issues
- No diagrams found
- Python extraction failures
- Output quality issues
- Diagram-specific sizing problems

Quick fixes for common issues:

**Permission denied:**
```bash
bash "<SKILL_ROOT>/scripts/extract-and-generate.sh" "<markdown_file>" "<output_directory>"
```

**Low quality output:**
```bash
MERMAID_SCALE=3 bash "<SKILL_ROOT>/scripts/extract-and-generate.sh" "<markdown_file>" "<output_directory>"
```

**Chrome/Puppeteer errors:**
Verify all WSL2 dependencies are installed (see references for full list).

## Bundled Resources

### scripts/

This skill bundles all necessary scripts for Mermaid diagram generation:

- **extract-and-generate.sh** - Main script that orchestrates extraction and PNG generation
- **extract_diagrams.py** - Python script for extracting Mermaid code blocks from markdown
- **puppeteer-config.json** - Chrome/Puppeteer configuration for WSL2 environment

The shell script locates bundled helpers from its own directory; substitute the actual installation path in examples.

### references/setup_and_troubleshooting.md

Comprehensive reference documentation including:
- Complete prerequisite installation instructions
- Detailed environment variable reference
- Extensive troubleshooting guide
- WSL2-specific Chrome dependency setup
- Validation procedures

Load this reference when dealing with setup issues, installation problems, or advanced customization needs.
