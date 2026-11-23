# Theme Selection Matrix & Contrast Checklist

Quick lookup across all 10 preset themes in `themes/` plus contrast and cross-artifact handoff rules.

| Theme File | Visual Tone | Primary Palette Cue | Best Fit |
| --- | --- | --- | --- |
| `themes/ocean-depths.md` | Calm maritime navy & teal | Deep navy (`#1a2332`), teal (`#2d8b8b`), cream (`#f1faee`) | Corporate, financial, consulting |
| `themes/modern-minimalist.md` | Clean editorial grayscale | Neutral charcoal, crisp white, muted slate | Architecture, engineering, SaaS docs |
| `themes/tech-innovation.md` | High-contrast modern tech | Dark slate, electric accent, bold display sans | Product launches, AI/dev keynotes |
| `themes/midnight-galaxy.md` | Deep cosmic contrast | Midnight indigo, luminous violet/silver | Executive keynote, dark-mode showcase |
| `themes/arctic-frost.md` | Crisp cool winter | Ice blue, frost white, cool slate | Healthcare, security, enterprise |
| `themes/forest-canopy.md` | Grounded earth tones | Deep moss, warm sage, natural cream | Sustainability, ops, agriculture |
| `themes/botanical-garden.md` | Fresh organic botanical | Leaf green, soft petal, warm paper | Consumer brand, lifestyle, community |
| `themes/golden-hour.md` | Warm autumnal richness | Amber gold, deep espresso, warm ivory | Storytelling, retrospective, brand |
| `themes/sunset-boulevard.md` | Energetic warm gradient | Coral, warm tangerine, deep plum | Creative pitch, marketing, campaign |
| `themes/desert-rose.md` | Soft dusty editorial | Muted rose, terracotta, warm sand | Design portfolio, boutique brand |

## Contrast & Readability Verification

1. **WCAG AA minimums**: target `>= 4.5:1` contrast for body copy and `>= 3.0:1` for large headers/UI accents.
2. **Dark vs light surface parity**: never apply light-mode accent hues directly on dark backgrounds without checking text legibility.
3. **Font fallback rule**: pair each display font with a reliable system/office fallback when exporting PPTX (`pptx`) or PDF (`pdf`) on headless machines.
4. **Handoff rule**: select or customize the theme first, pass exact hex codes and typography roles (`display`, `body`, `muted`, `accent`), and keep one coherent theme per deliverable.
