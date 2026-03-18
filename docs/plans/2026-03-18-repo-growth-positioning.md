# Repository Growth Positioning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve GitHub discoverability and conversion for this repository by optimizing the Chinese landing README, adding an English entry page, and updating repository metadata.

**Architecture:** Keep `README.md` as the Chinese primary landing page, add a lightweight `README.en.md` as the English entry page, and align GitHub description and topics so repository search and sharing better reflect the actual value of the project.

**Tech Stack:** Markdown, GitHub CLI, repository metadata

---

### Task 1: Add a landing-page structure for Chinese readers

**Files:**
- Modify: `README.md`

**Step 1: Add bilingual entry buttons**

Add prominent links near the top:

- `简体中文`
- `English`

**Step 2: Add value-proposition blocks**

Add:

- one-sentence positioning
- who the repo is for
- why it is worth starring
- quick start path

**Step 3: Keep the detailed catalog intact**

Do not remove the current categorized overview. Reframe the top of the README so it works as a landing page before the long catalog begins.

### Task 2: Add an English entry page

**Files:**
- Create: `README.en.md`

**Step 1: Write a concise English overview**

Include:

- project positioning
- audience
- installation guidance for `skills/` and `openclaw-skills/`
- links back to Chinese README

**Step 2: Keep it short**

This file should be a strong entry page, not a full duplicate of the Chinese README.

### Task 3: Update GitHub repository metadata

**Files:**
- Modify: GitHub repository settings via `gh`

**Step 1: Update description**

Use a search-friendly description focused on AI developers, skills, agents, and automation.

**Step 2: Add topics**

Prioritize topics relevant to discoverability:

- `ai`
- `skills`
- `agent`
- `automation`
- `prompt-engineering`
- `codex`
- `claude-code`
- `openclaw`
- `ai-tools`

### Task 4: Verify presentation

**Files:**
- Modify: repository working tree and GitHub metadata only

**Step 1: Check README top section locally**

Ensure the first screen clearly communicates:

- what the repo is
- who it helps
- how to start

**Step 2: Verify GitHub metadata**

Run:

```bash
gh repo view seaworld008/Commonly-used-high-value-skills --json description,repositoryTopics,url
```

Expected:

- new description is visible
- topics list is populated

