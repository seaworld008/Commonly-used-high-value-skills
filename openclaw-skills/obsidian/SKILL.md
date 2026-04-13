---
name: obsidian
description: 'Read, search, and create notes in the Obsidian vault.'
version: 1.0.0
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["obsidian", "notes", "knowledge-base"]'
created_at: "2026-04-13"
updated_at: "2026-04-13"
quality: 3
complexity: "intermediate"
---

# Obsidian Vault

Read, search, and create Markdown notes inside an Obsidian vault with simple filesystem commands.

**Location:** Set via `OBSIDIAN_VAULT_PATH` environment variable (e.g. in `~/.hermes/.env`).

If unset, defaults to `~/Documents/Obsidian Vault`.

Note: Vault paths may contain spaces - always quote them.

## When to Use

Use this skill when the user wants to:

- read or search notes in an Obsidian vault
- create or append Markdown notes
- connect notes with wikilinks
- manage a local note vault without a Notion-style database workflow

Use another skill when:

- the task needs structured database-style properties and page relations → prefer Notion skills
- the task is specifically about a Karpathy-style persistent research wiki → consider `llm-wiki`

## Usage

Recommended flow:

```text
resolve vault path
-> search existing note or folder
-> read current note if it exists
-> create or append
-> add wikilinks to keep notes connected
```

Quick path check:

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"
test -d "$VAULT" && echo "$VAULT" || echo "Vault not found"
```

## Read a note

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"
cat "$VAULT/Note Name.md"
```

## List notes

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"

# All notes
find "$VAULT" -name "*.md" -type f

# In a specific folder
ls "$VAULT/Subfolder/"
```

## Search

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"

# By filename
find "$VAULT" -name "*.md" -iname "*keyword*"

# By content
grep -rli "keyword" "$VAULT" --include="*.md"
```

## Create a note

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"
cat > "$VAULT/New Note.md" << 'ENDNOTE'
# Title

Content here.
ENDNOTE
```

## Append to a note

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"
echo "
New content here." >> "$VAULT/Existing Note.md"
```

## Wikilinks

Obsidian links notes with `[[Note Name]]` syntax. When creating notes, use these to link related content.

## Common Pitfalls

- forgetting to quote vault paths with spaces
- creating duplicate notes instead of appending to the canonical one
- writing plain filenames instead of Obsidian wikilinks
- assuming Obsidian metadata behaves like a database schema
