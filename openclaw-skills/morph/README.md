# Morph

> Document format transformation specialist

Morph converts documents between formats (Markdown, PDF, Word, HTML, Excel) while preserving structure, styling, and intent. It enables seamless distribution to diverse audiences and systems.

## Capabilities

### Core Conversions

| Source | PDF | Word | HTML | Markdown |
|--------|-----|------|------|----------|
| Markdown | ✅ | ✅ | ✅ | - |
| Word | ✅ | - | ✅ | ✅ |
| HTML | ✅ | ✅ | - | ✅ |
| Excel | ✅ | - | - | - |

### Advanced Features

- **Quality Assurance** - Automated quality metrics and verification scripts
- **Japanese Typography** - Kinsoku, line spacing, font selection for Japanese documents
- **Accessibility** - PDF/UA and WCAG 2.1 compliance
- **Professional Output** - PDF/A archival, digital signatures, watermarks
- **Batch Processing** - Convert multiple files with consistent templates

## File Structure

```
morph/
├── SKILL.md                 # Main skill definition
├── README.md                # This file
└── references/
    ├── conversion-matrix.md     # Tool selection guide
    ├── pandoc-recipes.md        # Pandoc command recipes
    ├── handoff-formats.md       # Agent collaboration formats
    ├── quality-assurance.md     # Quality metrics and verification
    ├── japanese-typography.md   # Japanese typesetting guide
    ├── accessibility-guide.md   # PDF/UA and WCAG compliance
    ├── advanced-features.md     # PDF/A, signatures, watermarks
    └── template-library.md      # LaTeX, CSS, Word templates
```

## Quick Start

### Markdown to PDF

```bash
pandoc input.md -o output.pdf --pdf-engine=xelatex --toc
```

### Markdown to PDF (Japanese)

```bash
pandoc input.md -o output.pdf \
  --pdf-engine=lualatex \
  -V documentclass=ltjsarticle \
  -V CJKmainfont="Hiragino Mincho Pro"
```

### Accessible PDF

```bash
pandoc input.md -o output.pdf \
  --pdf-engine=xelatex \
  -V classoption=tagged \
  --metadata lang=ja \
  --metadata title="Document Title" \
  -V fontsize=12pt
```

### PDF/A Archival

```bash
gs -dPDFA=2 -dBATCH -dNOPAUSE \
   -sColorConversionStrategy=UseDeviceIndependentColor \
   -sDEVICE=pdfwrite \
   -sOutputFile=output-pdfa.pdf \
   input.pdf
```

## Quality Grades

| Score | Grade | Meaning |
|-------|-------|---------|
| 90-100 | A | Production ready |
| 80-89 | B | Minor issues |
| 70-79 | C | Review needed |
| <70 | D/F | Reconvert required |

## Dependencies

### Required

- **Pandoc** - Universal document converter
- **LaTeX** (BasicTeX or TeX Live) - PDF generation

### Optional

- **LibreOffice** - Office format conversions
- **wkhtmltopdf** - HTML to PDF
- **Ghostscript** - PDF/A conversion, compression
- **pdftk** - PDF manipulation (merge, split, watermark)
- **Poppler** (pdfinfo, pdffonts) - PDF inspection

## Collaboration

Morph works with other agents in the ecosystem:

| Input From | Output To |
|------------|-----------|
| Scribe (specs) | Guardian (PR attachments) |
| Harvest (reports) | External stakeholders |
| Canvas (diagrams) | Archive systems |
| Quill (documentation) | Management |

## References

See the `references/` directory for detailed guides:

- [Quality Assurance](references/quality-assurance.md) - Metrics, verification, automated checks
- [Japanese Typography](references/japanese-typography.md) - Kinsoku, fonts, line spacing
- [Accessibility Guide](references/accessibility-guide.md) - PDF/UA, WCAG 2.1
- [Advanced Features](references/advanced-features.md) - PDF/A, signatures, watermarks
- [Template Library](references/template-library.md) - LaTeX, CSS, Word templates
