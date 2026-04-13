---
name: brand-guidelines
description: 'Applies Anthropic''s official brand colors and typography to any sort of artifact that may benefit from having Anthropic''s look-and-feel. Use it when brand colors or style guidelines, visual formatting, or company design standards apply.'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["brand", "guidelines", "productivity"]'
created_at: "2026-03-04"
updated_at: "2026-03-20"
quality: 3
complexity: "intermediate"
license: Complete terms in LICENSE.txt
---

# Anthropic Brand Styling

## When to Use

Use this skill when the user wants to:

- apply Anthropic brand colors or typography
- restyle an artifact to feel consistent with Anthropic visual identity
- normalize headings, body text, and accent colors across a deliverable

## Usage

Recommended flow:

```text
inspect artifact
-> apply brand palette
-> assign typography roles
-> style shapes and accents
-> verify consistency and readability
```

## Overview

To access Anthropic's official brand identity and style resources, use this skill.

**Keywords**: branding, corporate identity, visual identity, post-processing, styling, brand colors, typography, Anthropic brand, visual formatting, visual design

## Brand Guidelines

### Colors

**Main Colors:**

- Dark: `#141413` - Primary text and dark backgrounds
- Light: `#faf9f5` - Light backgrounds and text on dark
- Mid Gray: `#b0aea5` - Secondary elements
- Light Gray: `#e8e6dc` - Subtle backgrounds

**Accent Colors:**

- Orange: `#d97757` - Primary accent
- Blue: `#6a9bcc` - Secondary accent
- Green: `#788c5d` - Tertiary accent

### Typography

- **Headings**: Poppins (with Arial fallback)
- **Body Text**: Lora (with Georgia fallback)
- **Note**: Fonts should be pre-installed in your environment for best results

## Features

### Smart Font Application

- Applies Poppins font to headings (24pt and larger)
- Applies Lora font to body text
- Automatically falls back to Arial/Georgia if custom fonts unavailable
- Preserves readability across all systems

### Text Styling

- Headings (24pt+): Poppins font
- Body text: Lora font
- Smart color selection based on background
- Preserves text hierarchy and formatting

### Shape and Accent Colors

- Non-text shapes use accent colors
- Cycles through orange, blue, and green accents
- Maintains visual interest while staying on-brand

## Technical Details

### Font Management

- Uses system-installed Poppins and Lora fonts when available
- Provides automatic fallback to Arial (headings) and Georgia (body)
- No font installation required - works with existing system fonts
- For best results, pre-install Poppins and Lora fonts in your environment

### Color Application

- Uses RGB color values for precise brand matching
- Applied via python-pptx's RGBColor class
- Maintains color fidelity across different systems

### Example

```python
from pptx.dml.color import RGBColor

ANTHROPIC_ORANGE = RGBColor(0xD9, 0x77, 0x57)
ANTHROPIC_DARK = RGBColor(0x14, 0x14, 0x13)
```
