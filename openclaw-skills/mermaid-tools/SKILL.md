---
name: mermaid-tools
description: Extract Mermaid diagrams from Markdown and render PNG images with the bundled tools when a diagram image or batch conversion is needed.
zh_description: "提取 Markdown 中的 Mermaid 图并渲染为图片。"
version: "1.0.2"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["mermaid", "tools"]'
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 4
complexity: "intermediate"
---

# Mermaid Tools

## Overview

This skill enables extraction of Mermaid diagrams from markdown files and generation of high-quality PNG images. The skill bundles `extract-and-generate.sh`, `extract_diagrams.py`, and `puppeteer-config.json`. External `mmdc` and Chrome are required. The current rendering shell script targets configured Linux/WSL environments: it fixes Chrome at `/usr/bin/google-chrome-stable` and uses GNU `stat -c` and `sort -V`; it is not a portable macOS renderer.

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

1. **Extracts** all Mermaid code blocks from the markdown file
2. **Numbers** them sequentially (01, 02, 03, etc.) in order of appearance
3. **Generates** `.mmd` files for each diagram
4. **Attempts to create** high-resolution PNG images with smart sizing
5. **Validates expected PNG files** and returns nonzero if any validation fails. Review the per-file summary and inspect the generated diagrams for semantic/visual correctness.

### Output Files

For each diagram, the script generates:
- `01-diagram-name.mmd` - Extracted Mermaid code
- `01-diagram-name.png` - High-resolution PNG image

The numbering ensures diagrams maintain their order from the source document.

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

The renderer also needs a code fix to aggregate PNG validation failures and return nonzero. Until then, verify the expected diagram count, each file's existence/nonzero size and PNG signature, then inspect rendering. Missing or invalid outputs mean partial/failed delivery even if the script prints all-success.

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
