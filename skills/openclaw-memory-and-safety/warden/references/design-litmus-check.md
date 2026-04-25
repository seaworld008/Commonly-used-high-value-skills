# Design Litmus Check

Purpose: Use this reference for quick design quality evaluation and rejection criteria for AI-generated or templated frontend designs.

## Contents

- 6-Point Litmus Test
- 6 Rejection Criteria
- V.A.I.R.E. Dimension Mapping
- Quick Evaluation Workflow

---

## 6-Point Litmus Test

Ask these 6 questions about any design before it ships. Each question maps to a quality signal.

| # | Question | What You're Testing | Expected Answer |
|---|----------|-------------------|-----------------|
| 1 | **Is the brand clear within 2 seconds?** | Visual identity — logo, colors, typography communicate who this is | Brand is immediately recognizable, not generic |
| 2 | **Is there a single visual anchor in the first viewport?** | Composition — one element draws the eye first | Hero image, headline, or illustration dominates |
| 3 | **Do the headlines tell a story without the rest of the page?** | Content quality — headlines alone communicate the value proposition | Reading only H1-H3 gives a coherent narrative |
| 4 | **Does each section have exactly one job?** | Layout discipline — no multi-purpose sections | Each section's purpose is nameable in 3 words |
| 5 | **Are cards actually needed, or just filling space?** | Layout restraint — cards serve interactive purpose | Cards contain actionable, comparable items only |
| 6 | **Is motion purposeful or just present?** | Motion intentionality — animation serves feedback or hierarchy | Each animation has a named purpose (not "looks nice") |

### Scoring

- 6/6: Design passes litmus — proceed to full V.A.I.R.E. evaluation
- 4-5/6: Design needs targeted fixes before full evaluation
- ≤3/6: Design needs significant revision — return to Vision

---

## 6 Rejection Criteria

These patterns indicate design quality issues that require action. Each criterion has a severity level that maps to V.A.I.R.E. evaluation outcomes.

### 1. Generic SaaS Grid → FAIL(Identity)

**Pattern:** First viewport is a grid of cards, stats, or icons that could belong to any SaaS product.

**Signals:**
- Hero section is a card grid or feature icon grid
- No brand-specific visual elements above the fold
- Interchangeable with any competitor's landing page

**Action:** Return to Vision. Redesign first viewport with composition principles. Brand identity must be established in the hero.

**V.A.I.R.E. Impact:** Identity score cannot exceed 1. The design does not feel like "our product."

---

### 2. Beautiful Images, Weak Brand → CONDITIONAL

**Pattern:** High-quality visuals (stock photos, illustrations) that look professional but don't connect to the brand or product.

**Signals:**
- Hero image is impressive but generic (abstract shapes, stock lifestyle)
- Removing the logo makes the brand unidentifiable
- Images don't reinforce the headline or value proposition

**Action:** Replace generic visuals with product-specific imagery. If real product photos are unavailable, create custom illustrations that reflect the product's actual interface or workflow.

**V.A.I.R.E. Impact:** Identity and Value scores at risk. Beautiful but disconnected visuals fail to communicate what the product does.

---

### 3. Strong Headlines, No Action → FAIL(Value)

**Pattern:** Compelling, well-written headlines paired with missing or weak calls to action.

**Signals:**
- Headlines create interest but CTA is buried, unclear, or absent
- Multiple CTAs competing for attention (no primary)
- CTA text is generic ("Learn More", "Get Started") without context

**Action:** Ensure one clear primary CTA per viewport. CTA must directly connect to the headline's promise. Secondary actions are visually subordinate.

**V.A.I.R.E. Impact:** Value score fails. Users understand the proposition but cannot act on it.

---

### 4. Busy Images Behind Text → FAIL(Resilience)

**Pattern:** Text overlaid on complex, detailed, or high-contrast imagery without adequate protection.

**Signals:**
- Body text or headlines over unprocessed photographs
- No overlay, gradient, or knockout treatment to ensure readability
- Text readability depends on the specific image (fails if image changes)

**Action:** Add sufficient contrast treatment (overlay, text shadow, knockout area) OR move text outside the image. Test with multiple images to ensure resilience.

**V.A.I.R.E. Impact:** Resilience fails. The design breaks when content changes. Accessibility contrast ratios likely violated.

---

### 5. Carousels Without Narrative → CONDITIONAL

**Pattern:** Auto-rotating or swipeable carousels where slide order is arbitrary and content is interchangeable.

**Signals:**
- Carousel slides could be in any order without losing meaning
- Auto-rotation distracts from reading content
- No clear narrative progression across slides
- Key information hidden in non-visible slides

**Action:** If carousel is necessary, ensure narrative progression (slides build on each other). Consider replacing with a single strong slide or a scroll-based reveal. Disable auto-rotation.

**V.A.I.R.E. Impact:** Agency (auto-rotation removes control) and Value (information hidden in slides) at risk.

---

### 6. Stacked Cards as Layout → CONDITIONAL

**Pattern:** Entire page structure built from stacked card components, creating a uniform, flat visual rhythm.

**Signals:**
- Every section is wrapped in a card-like container
- Visual weight is uniform across the page (no hierarchy)
- Removing card borders would reveal that sections work fine without them
- Cards contain static content that isn't actionable

**Action:** Remove card containers from static content sections. Use spacing, typography, and background color shifts for section separation. Reserve cards for interactive content only.

**V.A.I.R.E. Impact:** Identity (generic template feel) and Value (no visual hierarchy to guide attention) at risk.

---

## V.A.I.R.E. Dimension Mapping

| Rejection Criterion | Primary Dimension | Secondary Dimension | Severity |
|--------------------|-------------------|---------------------|----------|
| Generic SaaS grid | **Identity** | Value | FAIL |
| Beautiful images, weak brand | **Identity** | Value | CONDITIONAL |
| Strong headlines, no action | **Value** | — | FAIL |
| Busy images behind text | **Resilience** | — | FAIL |
| Carousels without narrative | **Agency** | Value | CONDITIONAL |
| Stacked cards as layout | **Identity** | Value | CONDITIONAL |

### Severity Rules

| Severity | Action Required |
|----------|----------------|
| **FAIL** | Must be resolved before V.A.I.R.E. evaluation can pass. Return to relevant agent |
| **CONDITIONAL** | Can proceed if documented as known limitation with remediation timeline |

---

## Quick Evaluation Workflow

### Step 1: Litmus Test (2 minutes)

Run the 6-point litmus test. Score each question Yes/No.

### Step 2: Rejection Scan (3 minutes)

Check for the 6 rejection criteria. Flag any matches.

### Step 3: Triage

| Litmus Score | Rejections Found | Action |
|-------------|-----------------|--------|
| 6/6 | None | Proceed to full V.A.I.R.E. evaluation |
| 6/6 | CONDITIONAL only | Proceed with conditions documented |
| 4-5/6 | None or CONDITIONAL | Fix litmus gaps, then proceed |
| 4-5/6 | Any FAIL | Return to Vision/relevant agent for revision |
| ≤3/6 | Any | Full redesign needed. Return to Vision |

### Step 4: Document

Include litmus results and rejection findings in the V.A.I.R.E. scorecard under the relevant dimension's evidence section.
