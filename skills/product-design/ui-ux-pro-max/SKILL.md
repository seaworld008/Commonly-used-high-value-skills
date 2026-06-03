---
name: ui-ux-pro-max
description: 'Front-end UI/UX design intelligence for creating, reviewing, and hardening polished product interfaces across web, mobile, dashboards, SaaS, ecommerce, and content-heavy apps.'
version: "1.0.0"
author: seaworld008
source: github:nextlevelbuilder/ui-ux-pro-max-skill
source_url: "https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/.claude/skills/ui-ux-pro-max/SKILL.md"
license: MIT
tags: '[ui, ux, design-system, frontend, accessibility, typography, color, responsive-design]'
created_at: "2026-06-03"
updated_at: "2026-06-03"
quality: 4
complexity: advanced
---

# UI/UX Pro Max

Use this skill when an agent must make front-end work look intentional, usable, accessible, and appropriate for the product domain. It is a design intelligence layer for turning vague UI requests into concrete design decisions, implementation constraints, and review gates.

The skill is inspired by the public `ui-ux-pro-max` workflow, but this repository version is self-contained: it does not require a bundled database, CLI, or hidden scripts. Use it as a rigorous design reasoning system that pairs well with React, Next.js, Vue, Svelte, Tailwind, shadcn/ui, SwiftUI, React Native, Flutter, and plain HTML/CSS.

## When to Use

- Creating a new page, flow, dashboard, admin panel, landing page, app screen, or design system.
- Improving an interface that feels generic, unbalanced, cramped, overdecorated, or hard to scan.
- Choosing color systems, typography, spacing, layout density, chart treatment, or component states.
- Refactoring UI code where the visual result matters as much as the code structure.
- Auditing accessibility, responsive behavior, visual hierarchy, form feedback, or interaction quality.
- Translating a product domain into an interface personality, such as fintech, healthcare, education, developer tools, marketplaces, media, or internal operations.
- Building with component systems such as shadcn/ui, Radix, Chakra, MUI, Ant Design, Headless UI, or native platform controls.
- Reviewing whether AI-generated UI output has fallen into common patterns such as giant hero sections, repetitive cards, low contrast gray text, random gradients, or decorative motion.

## Skip When

- The task is pure backend logic, infrastructure, data modeling, or batch scripting.
- The user explicitly asks for no design changes.
- The requested change is a tiny copy edit that cannot affect layout, affordance, or accessibility.
- A formal design file is provided and the task is only to implement it exactly. In that case, use the design file as the source of truth, then use this skill only for accessibility and implementation checks.

## Core Capabilities

1. Convert product intent into a design brief: audience, domain, device mix, density, tone, primary jobs, and risk areas.
2. Select an appropriate visual direction without defaulting to a one-note palette or generic SaaS layout.
3. Define a practical token set for color, type, spacing, radius, shadows, motion, and state layers.
4. Design screens around task success: information hierarchy, progressive disclosure, clear calls to action, and predictable navigation.
5. Check accessibility early: contrast, labels, keyboard behavior, focus states, reduced motion, and screen-reader semantics.
6. Make responsive behavior explicit instead of hoping flexbox happens to work.
7. Review charts, tables, forms, filters, menus, modals, sidebars, and empty states as first-class UI.
8. Produce implementation-ready guidance that a coding agent can apply directly in components and CSS.

## Design Brief Workflow

Before touching UI code, answer these questions in one compact pass:

- Product type: What kind of product is this: tool, marketplace, consumer app, portfolio, docs site, game, dashboard, mobile app, or marketing site?
- User mode: Are users browsing, deciding, operating, comparing, creating, recovering from error, or monitoring?
- Density: Should the interface be spacious, editorial, medium-density, or operations-dense?
- Trust level: Does the product need to feel playful, clinical, premium, technical, secure, fast, calm, or authoritative?
- Primary surfaces: Which parts matter most: forms, tables, charts, media, cards, maps, timelines, chat, search, checkout, onboarding, or settings?
- Device reality: Is mobile primary, desktop primary, or both?
- Constraints: Existing design system, component library, brand colors, accessibility level, and performance requirements.

## Visual Direction Rules

- Pick a direction that fits the domain, not the model's favorite style.
- For operational SaaS and internal tools, prefer restrained density, scannable tables, calm surfaces, and clear controls.
- For consumer or brand-led pages, use stronger imagery, typography, and product-specific visual cues.
- For healthcare, finance, security, and legal products, bias toward clarity, trust, strong contrast, and low decorative noise.
- For creative tools, games, creator platforms, and education products, allow richer expression while protecting usability.
- Avoid applying glassmorphism, neumorphism, claymorphism, brutalism, or bento layouts by habit. Use them only when they support the product's meaning.
- Use actual product, place, object, workflow, or data visuals where possible. Avoid purely atmospheric decorative backgrounds when the user must inspect or act.
- Do not let the whole UI collapse into one hue family. Use neutral surfaces, semantic colors, and controlled accents.

## Token Starter

Use a small token system before writing components:

```css
:root {
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-text: #0f172a;
  --color-muted: #475569;
  --color-border: #d7dee8;
  --color-primary: #2563eb;
  --color-success: #15803d;
  --color-warning: #b45309;
  --color-danger: #b91c1c;
  --radius-control: 6px;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
}
```

Adjust these tokens to the domain, but keep semantic naming. Raw hex values should not spread through components.

## Accessibility Gate

- Text contrast meets WCAG AA: 4.5:1 for normal text and 3:1 for large text.
- Every icon-only control has an accessible name.
- Focus states are visible, not removed.
- Keyboard order follows visual order.
- Forms use persistent labels, not placeholder-only labels.
- Error messages appear near the field and describe the recovery action.
- Touch targets are at least 44px by 44px, with enough spacing to avoid accidental taps.
- Motion respects `prefers-reduced-motion`.
- Data visualizations do not rely only on color.
- Modals trap focus, restore focus on close, and provide an escape route.

## Responsive Gate

- Start from the smallest meaningful viewport.
- Prevent horizontal scroll caused by fixed widths, long words, tables, charts, or toolbars.
- Use `min()`, `max()`, `clamp()` for layout dimensions, but do not scale font sizes with viewport width.
- Give fixed-format UI such as boards, grids, charts, and icon toolbars stable dimensions.
- Reserve media dimensions with `aspect-ratio`, width/height, or skeletons to avoid layout shift.
- Keep primary actions reachable on mobile, but do not hide critical actions behind hover.
- Use responsive table strategies: column priority, stacked rows, horizontal scroll inside the table only when unavoidable, or summary cards.

## Component Review Checklist

- Button: one primary action per region, loading and disabled states, clear label, icon alignment.
- Card: not nested inside another card, clear purpose, stable dimensions, no excessive radius.
- Form: label, helper, error, valid state, submit feedback, keyboard and screen-reader behavior.
- Table: sorting state, empty state, density, sticky headers only when useful, readable numeric alignment.
- Chart: title, unit, time range, legend, tooltip, accessible palette, no misleading axis.
- Modal: focus trap, close route, destructive confirmation, sensible width, no hidden scroll trap.
- Navigation: current state, predictable back behavior, mobile equivalent, no overloaded menu.
- Empty state: explains what happened and offers the next useful action.
- Error state: specific, recoverable, and not visually identical to a warning.

## Implementation Pattern

Use this sequence when generating UI:

```text
1. Identify product domain and primary workflow.
2. Choose visual direction and density.
3. Define tokens and component states.
4. Build the smallest complete screen.
5. Test responsive layout at mobile and desktop widths.
6. Run accessibility checks.
7. Polish spacing, hierarchy, copy fit, and state behavior.
```

## Anti-Patterns

- Generic centered hero, three feature cards, and gradient background for every product.
- Low-contrast gray text on gray surfaces.
- Decorative blobs, random gradients, or novelty effects that do not support the task.
- Text inside controls that wraps unpredictably or overflows.
- Components that resize when hover, badges, counters, or loading text appear.
- Icon buttons without accessible labels.
- Cards nested inside cards as page structure.
- Unstable dashboards where charts, filters, and counters jump during loading.
- Mobile layouts that simply shrink desktop panels.
- Animation that blocks input or hides state changes.

## Output Format

For design work, return:

```markdown
## Design Direction
- Product fit:
- Density:
- Visual language:
- Token decisions:

## Implementation Notes
- Layout:
- Components:
- Accessibility:
- Responsive behavior:

## Review Gates
- Must verify:
- Known tradeoffs:
```

## Boundaries

This skill does not replace a provided brand guide, design file, regulatory accessibility requirement, or user research. When those exist, treat them as primary sources. This skill supplies design judgment and implementation discipline around them.
