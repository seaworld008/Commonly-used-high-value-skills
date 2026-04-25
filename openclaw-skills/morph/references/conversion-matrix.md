# Conversion Matrix

Purpose: Use this reference when selecting the best tool for a source/target format pair and estimating likely fidelity loss.

## Contents

- Format-pair matrix
- Scenario-based defaults
- Known limitations
- Dependency checks
- Quick commands

## Format-Pair Matrix

### Markdown As Source

| Target | Preferred tool | Quality | Notes |
|--------|----------------|---------|-------|
| PDF (Japanese, high fidelity) | `pandoc + xelatex` | `★★★★★` | Best typography and font embedding |
| PDF (speed-first) | `pandoc + wkhtmltopdf` | `★★★★☆` | Faster, CSS-friendly |
| Word (`.docx`) | `pandoc` | `★★★★☆` | Some style limits |
| HTML | `pandoc` | `★★★★★` | Native and reliable |
| Styled HTML | `pandoc + template/css` | `★★★★★` | Best for publication pages |
| EPUB | `pandoc` | `★★★★☆` | Good for ebook output |

### Word (`.docx`) As Source

| Target | Preferred tool | Quality | Notes |
|--------|----------------|---------|-------|
| PDF | `LibreOffice` | `★★★★★` | Best layout preservation |
| PDF (simple docs only) | `pandoc` | `★★★☆☆` | Use only for uncomplicated files |
| Markdown | `pandoc` | `★★★☆☆` | Complex formatting is lossy |
| HTML | `pandoc` | `★★★★☆` | Basic structure preserved |
| ODT | `LibreOffice` | `★★★★★` | Office-friendly |

### Excel (`.xlsx`) As Source

| Target | Preferred tool | Quality | Notes |
|--------|----------------|---------|-------|
| PDF | `LibreOffice` | `★★★★★` | Sheet-level export |
| CSV | `LibreOffice` | `★★★★★` | Best for raw data extraction |
| HTML | `LibreOffice` | `★★★★☆` | Table structure preserved |

### HTML As Source

| Target | Preferred tool | Quality | Notes |
|--------|----------------|---------|-------|
| PDF (modern CSS) | `Chrome/Puppeteer` | `★★★★★` | Best CSS support |
| PDF (simple, fast) | `wkhtmltopdf` | `★★★★☆` | Good for stable layouts |
| PDF (simple only) | `pandoc` | `★★★☆☆` | Avoid for rich HTML |
| Word (`.docx`) | `pandoc` | `★★★★☆` | Structure preserved |
| Markdown | `pandoc` | `★★★☆☆` | Lossy for complex HTML |

### Diagram Sources

| Source | Target | Preferred tool | Quality |
|--------|--------|----------------|---------|
| draw.io | PDF / PNG / SVG | `draw.io CLI` | `★★★★★` |
| Mermaid | PNG / PDF / SVG | `mermaid-cli` | `★★★★★` |

## Scenario Defaults

| Scenario | Default |
|---------|---------|
| Markdown -> PDF (Japanese business doc) | `pandoc + xelatex` or `pandoc + lualatex` with Japanese template |
| Markdown -> PDF (fast preview) | `pandoc + wkhtmltopdf` |
| Word -> PDF | `LibreOffice` |
| HTML -> PDF with modern layout | `Chrome/Puppeteer` |
| HTML -> PDF with simpler layout | `wkhtmltopdf` |
| Batch conversion | `pandoc` scripts or Makefile |
| Accessible PDF | `pandoc + lualatex` with tagged/accessibility settings |

## Known Limitations

| Pair | Main risk | Mitigation |
|------|-----------|------------|
| Markdown -> Word | Fine-grained styles and complex tables | Document loss and consider HTML fallback |
| Word -> Markdown | Complex tables and layout are lossy | Expect cleanup and review |
| HTML -> PDF via `wkhtmltopdf` | Modern CSS support gaps | Use legacy fallbacks or switch to Chrome/Puppeteer |
| Any PDF structural conversion | PDF is not a rich source format | Treat PDF as output-first and use PDF-specific tools for PDF operations |

## Japanese Defaults

- Encoding: `UTF-8`
- Typical page size: `A4`
- Common fonts: `Hiragino`, `Noto Serif CJK JP`, `Noto Sans CJK JP`

## Dependency Checks

```sh
pandoc --version
pandoc --list-input-formats
pandoc --list-output-formats
which xelatex
xelatex --version
soffice --version
wkhtmltopdf --version
```

## Quick Commands

```sh
# Markdown -> PDF (Japanese)
pandoc input.md -o output.pdf --pdf-engine=xelatex

# Word -> PDF
soffice --headless --convert-to pdf input.docx

# HTML -> PDF
wkhtmltopdf --encoding UTF-8 input.html output.pdf

# draw.io -> PDF
/Applications/draw.io.app/Contents/MacOS/draw.io --export --format pdf input.drawio
```
