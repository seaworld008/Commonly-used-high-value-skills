---
name: web-artifacts-builder
description: 'Build complex interactive HTML artifacts with React, Tailwind, and shadcn/ui when multiple components, routing, or state are needed.'
zh_description: "用于构建复杂多组件 HTML/React 网页 artifacts，尤其适合需要状态、路由或 shadcn/ui 的场景。"
version: "1.0.2"
author: "seaworld008"
source: "in-house"
source_url: ""
license: Complete terms in LICENSE.txt
tags: '["artifacts", "builder", "development", "web"]'
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 3
complexity: "intermediate"
---

# Web Artifacts Builder

To build powerful frontend claude.ai artifacts, follow these steps:
1. Initialize the frontend repo using `scripts/init-artifact.sh`
2. Develop your artifact by editing the generated code
3. Bundle all code into a single HTML file using `scripts/bundle-artifact.sh`
4. Check standalone opening and key interactions before delivery
5. Display the artifact with the actual verification status

**Stack**: React + TypeScript + Vite + Parcel (bundling) + Tailwind CSS + shadcn/ui.
The initializer uses an unpinned create-vite and does not fix the React version;
inspect the generated manifest/lockfile and verify compatibility.

## Design & Style Guidelines

VERY IMPORTANT: To avoid what is often referred to as "AI slop", avoid using excessive centered layouts, purple gradients, uniform rounded corners, and Inter font.

## Quick Start

### Step 1: Initialize Project

Resolve the loaded skill's real directory before changing directories:
```bash
ARTIFACT_SKILL_DIR="/absolute/path/to/loaded/web-artifacts-builder"
```
Inspect arguments, the new destination and available project package runners
first. The bundled initializer runs `npm install -g pnpm` when pnpm is missing,
even before checking arguments. Do not invoke it in that state. Reuse an existing
project runner, or acquire a compatible pinned runner locally under the task's
existing installation authorization; otherwise scaffold manually with available
tools. Do not install global packages as a side effect of loading this skill.

When pnpm is already available and a fresh scaffold is authorized:
```bash
bash "$ARTIFACT_SKILL_DIR/scripts/init-artifact.sh" <project-name>
cd <project-name>
```
Record the resolved template/dependency versions and validate them; the current
initializer does not pin create-vite or guarantee a compatible dependency set.

This creates a fully configured project with:
- ✅ React + TypeScript (via Vite)
- ✅ Tailwind CSS 3.4.1 with shadcn/ui theming system
- ✅ Path aliases (`@/`) configured
- ✅ 40+ shadcn/ui components pre-installed
- ✅ All Radix UI dependencies included
- ✅ Parcel configured for bundling (via .parcelrc)
- Node-major detection and a Vite 5.4.11 pin for Node 18; this is not a complete
  compatibility check for the unpinned scaffold and other dependencies

### Step 2: Develop Your Artifact

To build the artifact, edit the generated files. See **Common Development Tasks** below for guidance.

### Step 3: Bundle to Single HTML File

To bundle the React app into a single HTML artifact:
```bash
bash "$ARTIFACT_SKILL_DIR/scripts/bundle-artifact.sh"
```

This creates `bundle.html` - a self-contained artifact with all JavaScript, CSS, and dependencies inlined. This file can be directly shared in Claude conversations as an artifact.

**Requirements**: Your project must have an `index.html` in the root directory.

**What the script does**:
- Installs bundling dependencies (parcel, @parcel/config-default, parcel-resolver-tspaths, html-inline)
- Creates `.parcelrc` config with path alias support
- Builds with Parcel (no source maps)
- Inlines all assets into single HTML using html-inline

### Step 4: Check the Bundled Artifact

Before delivery, open `bundle.html` independently of the development server and
check key interactions and representative viewport sizes with available tools.
A successful build alone does not prove standalone behavior. If browser or
execution capability is unavailable, state which checks were not run and give
concrete acceptance steps.

### Step 5: Share Artifact with User

Share the bundled HTML and report build, standalone and interaction results.

## Reference

- **shadcn/ui components**: https://ui.shadcn.com/docs/components

## Artifact Quality Checklist

Before handing off the final HTML artifact, verify these points:

- The artifact opens without a build server and does not depend on local-only file paths.
- Core interactions work from the bundled `bundle.html`, not only during Vite development.
- Responsive layout has been considered for mobile, tablet, and desktop widths.
- State is initialized deterministically so the first render is useful without user setup.
- Any imported assets are embedded, copied, or replaced with stable remote URLs.
- The visual language is intentional; avoid default Tailwind spacing and generic component stacks when the user asks for design polish.

## Common Failure Modes

- **Missing path alias support**: rerun the bundling script and confirm `.parcelrc` contains the resolver configuration.
- **Oversized bundle**: remove unused component imports, large image assets, and debug-only dependencies.
- **Broken shadcn styles**: confirm generated components import from the expected `@/components/ui/*` paths.
- **Hydration-like mismatch**: avoid relying on `Date.now()`, random values, or browser-only APIs during first render unless guarded.

## Delivery Notes

When the user only asked for a quick static page, do not force this full React artifact workflow. Use it when complexity justifies the setup: multi-screen state, component libraries, rich interactions, or a reusable artifact that benefits from a local build loop.
