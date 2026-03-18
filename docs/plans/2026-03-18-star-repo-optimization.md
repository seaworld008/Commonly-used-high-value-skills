# Star Repo Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve repository conversion and growth by making the landing page more memorable, adding explicit contribution guidance, and creating reusable social/banner assets.

**Architecture:** Add a README-visible banner asset, create a contributor entrypoint with clear rules, add a PR template, and strengthen the top section of both Chinese and English README files with featured paths and contribution prompts.

**Tech Stack:** Markdown, SVG, GitHub repository conventions

---

### Task 1: Add a visual banner asset

**Files:**
- Create: `.github/assets/repo-banner.svg`

**Step 1: Design for GitHub README**

The asset should:

- work as a static SVG
- match the repository positioning
- stay lightweight and text-readable

**Step 2: Reference it in README**

Use the SVG as a header visual near the top of the repository landing page.

### Task 2: Add contributor onboarding

**Files:**
- Create: `CONTRIBUTING.md`
- Create: `.github/pull_request_template.md`

**Step 1: Add contribution guide**

Include:

- skill directory structure
- naming conventions
- OpenClaw export rule
- verification expectations
- README and metadata hygiene

**Step 2: Add PR template**

Make it easier for contributors to submit good changes with:

- what changed
- where the skill lives
- how it was verified
- whether OpenClaw export was refreshed

### Task 3: Strengthen landing-page conversion

**Files:**
- Modify: `README.md`
- Modify: `README.en.md`

**Step 1: Add banner**

Display the new SVG near the top.

**Step 2: Add featured paths**

Show readers where to start:

- first categories
- top representative skills
- how to contribute

**Step 3: Add contributor CTA**

Link directly to `CONTRIBUTING.md` from both README files.

### Task 4: Verify presentation

**Files:**
- Modify: repository working tree only

**Step 1: Inspect README top sections locally**

Confirm the first screen now includes:

- title
- visual banner
- bilingual entry
- value proposition
- quick start
- contribution path

**Step 2: Check git status sanity**

Ensure only intentional growth-related files were changed.

