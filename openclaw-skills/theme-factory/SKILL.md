---
name: theme-factory
description: 'Use when styling artifacts with reusable themes, applying preset color/font systems, or generating new visual themes for slides, documents, reports, HTML pages, and landing pages.'
zh_description: "用于为幻灯片、文档、报告和网页应用预设主题或生成新的颜色字体系统。"
version: "1.0.2"
author: "Anthropic contributors; local curators"
source: "https://github.com/anthropics/skills"
source_url: "https://github.com/anthropics/skills/blob/e4bb5d960d87126ff3b3a8af1a104b7db67560ba/skills/theme-factory/SKILL.md"
license: "Apache-2.0"
tags: ["factory", "productivity", "theme"]
created_at: "2026-03-04"
updated_at: "2026-11-23"
quality: 3
complexity: "intermediate"
---

# Theme Factory Skill

This skill provides a curated collection of professional font and color themes, each with carefully selected color palettes and font pairings. Once a theme is chosen, it can be applied to any artifact.

## Purpose

To apply consistent, professional styling to presentation slide decks, use this skill. Each theme includes:
- A cohesive color palette with hex codes
- Complementary font pairings for headers and body text
- A distinct visual identity suitable for different contexts and audiences

## Usage Instructions

To apply styling to a slide deck or other artifact:

- If the user named a theme, read its preset and follow the application process below.
- If the user wants to compare themes, offer the bundled `theme-showcase.pdf` and ask which one fits.
- If the user delegated the choice, select a preset for the audience and content, explain the choice briefly, and apply it.

## Themes Available

The following 10 themes are available, each showcased in `theme-showcase.pdf`:

1. **Ocean Depths** - Professional and calming maritime theme
2. **Sunset Boulevard** - Warm and vibrant sunset colors
3. **Forest Canopy** - Natural and grounded earth tones
4. **Modern Minimalist** - Clean and contemporary grayscale
5. **Golden Hour** - Rich and warm autumnal palette
6. **Arctic Frost** - Cool and crisp winter-inspired theme
7. **Desert Rose** - Soft and sophisticated dusty tones
8. **Tech Innovation** - Bold and modern tech aesthetic
9. **Botanical Garden** - Fresh and organic garden colors
10. **Midnight Galaxy** - Dramatic and cosmic deep tones

## Theme Details

Each theme is defined in the `themes/` directory with complete specifications including:
- Cohesive color palette with hex codes
- Complementary font pairings for headers and body text
- Distinct visual identity suitable for different contexts and audiences

## Application Process

After a preferred theme is selected:
1. Read the corresponding theme file from the `themes/` directory
2. Apply the specified colors and fonts consistently throughout the deck
3. Ensure proper contrast and readability
4. Maintain the theme's visual identity across all slides

## Create your Own Theme
To handle cases where none of the existing themes work for an artifact, create a custom theme. Based on provided inputs, generate a new theme similar to the ones above. Give the theme a similar name describing what the font/color combinations represent. Use any basic description provided to choose appropriate colors/fonts. After generating the theme, show it for review and verification. Following that, apply the theme as described above.

## Example Theme Handoff

```yaml
theme_name: Harbor Ledger
headline_font: "Merriweather"
body_font: "Source Sans 3"
palette:
  primary: "#12324A"
  secondary: "#D88C3A"
  accent: "#E9F1F7"
usage_notes:
  - Use primary for titles and dividers
  - Use secondary only for emphasis and charts
  - Keep body text on light backgrounds for readability
```

## When to Use & Selection Matrix

Use this skill whenever an artifact (slide deck, HTML landing page, PDF report, or DOCX brief) needs cohesive colors and typography instead of ad-hoc styling.
- Skip when the user specifies an official brand guideline (`brand-guidelines`) or requests raw structural layout only.
- Read [Theme Selection Matrix](references/theme-selection-matrix.md) to pick the closest preset quickly by audience, tone, and surface contrast before reading an individual `themes/<name>.md` file.

## Contrast & Multi-Format Handoff Checklist

1. **Read one preset completely**: open `themes/<chosen-theme>.md` and verify every hex color and font role.
2. **Check readability**: enforce `>= 4.5:1` text-to-background contrast for body copy (`>= 3.0:1` for large headings and chart labels) and verify callout/accent legibility on both light and dark cards.
3. **Map semantic tokens**: assign `primary` (headers/dividers), `surface` (slide or page background), `body` (readable dark/light copy), `muted` (captions/axes), and `accent` (single highlight series or CTA).
4. **Deliver to format skill**:
   - Presentations: pass tokens into `pptx` master slide layouts or `guizang-ppt-skill` HTML slides.
   - Documents & web: emit CSS custom properties (`--color-primary`, `--color-surface`, `--font-heading`, `--font-body`) for `frontend-design`, `docx`, or `pdf` outputs.
5. **Custom themes**: only invent a new theme when none of the 10 presets fits the domain; document contrast notes and get approval if brand identity is sensitive.

## CSS Token Export Pattern

```css
:root {
  --color-primary: #1a2332;
  --color-secondary: #2d8b8b;
  --color-accent: #a8dadc;
  --color-surface: #f1faee;
  --color-ink: #1a2332;
  --font-heading: "DejaVu Sans", system-ui, sans-serif;
  --font-body: "DejaVu Sans", system-ui, sans-serif;
}
```
