---
name: obsidian
description: 'Read, search, create, or edit notes in an authorized Obsidian vault while preserving frontmatter, wikilinks, and unrelated notes.'
zh_description: "用于读取、搜索、创建和编辑 Obsidian 知识库笔记，并维护 Markdown 结构和链接关系。"
version: "1.0.5"
author: "seaworld008"
source: "github:NousResearch/hermes-agent"
source_url: "https://github.com/NousResearch/hermes-agent/blob/main/skills/note-taking/obsidian/SKILL.md"
license: MIT
tags: '["obsidian", "notes", "knowledge-base"]'
created_at: "2026-04-13"
updated_at: "2026-09-06"
quality: 3
complexity: "intermediate"
platforms: '[linux, macos, windows]'
metadata:
  hermes:
    tags: [Obsidian, Notes, Markdown, Vault]
    related_skills: []
---

# Obsidian Vault

Use this skill for filesystem-first Obsidian vault work: reading notes, listing notes, searching note files, creating notes, appending content, and adding wikilinks.

## Vault path

Use a known or resolved vault path before calling file tools.

The documented vault-path convention is the `OBSIDIAN_VAULT_PATH` environment variable, for example from `${HERMES_HOME:-~/.hermes}/.env`. If it is unset, use `~/Documents/Obsidian Vault`.

File tools do not expand shell variables. Do not pass paths containing `$OBSIDIAN_VAULT_PATH` to `read_file`, `write_file`, `patch`, or `search_files`; resolve the vault path first and pass a concrete absolute path. Vault paths may contain spaces, which is another reason to prefer file tools over shell commands.

If the vault path is unknown, `terminal` is acceptable for resolving `OBSIDIAN_VAULT_PATH` or checking whether the fallback path exists. Once the path is known, switch back to file tools.

## Read a note

Use `read_file` with the resolved absolute path to the note. Prefer this over `cat` because it provides line numbers and pagination.

## List notes

Use `search_files` with `target: "files"` and the resolved vault path. Prefer this over `find` or `ls`.

- To list all markdown notes, use `pattern: "*.md"` under the vault path.
- To list a subfolder, search under that subfolder's absolute path.

## Search

Use `search_files` for both filename and content searches. Prefer this over `grep`, `find`, or `ls`.

- For filenames, use `search_files` with `target: "files"` and a filename `pattern`.
- For note contents, use `search_files` with `target: "content"`, the content regex as `pattern`, and `file_glob: "*.md"` when you want to restrict matches to markdown notes.

## Create a note

Use `write_file` with the resolved absolute path and the full markdown content. Prefer this over shell heredocs or `echo` because it avoids shell quoting issues and returns structured results.

## Append to a note

Prefer a native file-tool workflow when it is not awkward:

- Read the target note with `read_file`.
- Use `patch` for an anchored append when there is stable context, such as adding a section after an existing heading or appending before a known trailing block.
- Use `write_file` when rewriting the whole note is clearer than constructing a fragile patch.

For an anchored append with `patch`, replace the anchor with the anchor plus the new content.

For a simple append with no stable context, `terminal` is acceptable if it is the clearest safe option.

## Targeted edits

Use `patch` for focused note changes when the current content gives you stable context. Prefer this over shell text rewriting.

## Wikilinks

Obsidian links notes with `[[Note Name]]` syntax. When creating notes, use these to link related content.
<!-- LOCAL-QUALITY-SUPPLEMENT:START -->
## Usage Notes

This supplement is maintained by the repository sync pipeline. It keeps the
imported upstream skill usable inside this curated collection when the upstream
source is intentionally concise.

## Common Patterns

```text
1. Confirm that the user's task matches the skill trigger.
2. Read the relevant project files or user-provided context before acting.
3. Choose the smallest reversible action that advances the task.
4. Run the verification command or manual check that proves the result.
5. Report the outcome, evidence, and any remaining risk.
```

## Boundaries

- Prefer the upstream workflow for Obsidian; this section only adds local quality
  guardrails.
- Do not invent project facts when required files, vaults, services, or tools are
  unavailable.
- Stop and ask for clarification when the next action could overwrite user work,
  expose private data, or change production state.
<!-- LOCAL-QUALITY-SUPPLEMENT:END -->

<!-- LOCAL-CURATION-SUPPLEMENT:START -->
## Vault Scope and Tool Portability

The tool names above describe the upstream Hermes surface. On another client,
discover its actual file-read, search, and patch capabilities before constructing
arguments. Do not invent `read_file` or `search_files` tools if they are absent.
The fallback vault path is a discovery hint, not permission to create a vault or
modify whichever directory happens to exist.

Resolve the requested vault to an absolute path and confirm the target note stays
inside it after resolving symlinks. If more than one vault matches, ask the user
which one owns the task. Avoid reading the whole environment or secret-bearing
configuration merely to locate a path; inspect only the necessary setting.

## Common Patterns: Safe Note Edit

```text
1. Identify the vault and one target note by full path.
2. Read the note and preserve its frontmatter, line endings and trailing content.
3. Locate a unique heading or paragraph that anchors the requested change.
4. Re-read before writing if another application may have edited the note.
5. Apply only the authorized change with the client's supported patch operation.
6. Read the resulting note and compare the exact before/after diff.
7. Report the edited path, changed section and unresolved link ambiguities.
```

Do not rebuild an entire note from an earlier summary. A missing or non-unique
anchor means re-read and refine the patch, not overwrite the file. For a new note,
check that the intended path does not already exist; preserve the existing file
and choose a non-conflicting name only with the user's agreement.

## Link and Metadata Preservation

Retain YAML frontmatter, tags, aliases, code fences, attachment references, and
existing `[[note#heading|label]]` links unless the request specifically changes
them. A note rename may require inbound-link updates across the vault; inventory
those links first and obtain scope for the wider edit instead of assuming a
filesystem rename updates them. Duplicate note titles need path-aware resolution.

## Acceptance and Boundaries

- Exactly the authorized note or reviewed note set changes.
- Frontmatter still parses and unrelated Markdown remains byte-for-byte intact.
- New wikilinks resolve to the intended note or are explicitly reported as absent.
- Search output is bounded; private notes are not uploaded to external services.
- `.obsidian` configuration, plugins, attachments and sync state remain untouched.
- Deletion, bulk rename and cross-vault moves require separate explicit scope.
- Report filesystem verification separately from rendering in the Obsidian app;
  do not claim a rendered result unless it was actually inspected.
<!-- LOCAL-CURATION-SUPPLEMENT:END -->
