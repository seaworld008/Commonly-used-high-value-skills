# nlpm-audit Usage Guide

This guide explains how to install and invoke the `nlpm-audit` skill in Codex,
Claude Code, OpenClaw, or a source-browsing agent.

## What The Skill Does

`nlpm-audit` audits natural-language programming artifacts as if they were
code. Use it for:

- `SKILL.md` quality and trigger-description review;
- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, and memory-file checks;
- Claude/Codex plugin manifest consistency;
- slash command, agent, rule, hook, prompt, and MCP config review;
- lightweight 100-point scoring;
- Markdown audit reports;
- basic executable-risk checks for hooks, scripts, and MCP commands;
- vocabulary and version drift review.

It is a curated, portable version of the durable NLPM workflow. It does not
replace the full upstream Claude Code plugin when you need exact `/nlpm:*`
slash commands, HTML report rendering, badges, or the full auditor pipeline.

## Install For Codex

Recommended user-level install:

```bash
python3 scripts/sync_codex_skills.py \
  --source-root ./skills \
  --codex-root ~/.codex/skills
```

Windows PowerShell:

```powershell
python scripts/sync_codex_skills.py `
  --source-root ".\skills" `
  --codex-root "$env:USERPROFILE\.codex\skills"
```

After sync, the skill should be available at:

```text
~/.codex/skills/nlpm-audit/SKILL.md
```

Codex can invoke skills implicitly when the task matches the skill description.
You can also explicitly call it with:

```text
$nlpm-audit audit this repository's SKILL.md, AGENTS.md, plugin manifests, and hooks
```

## Install For Claude Code

Personal install:

```bash
python3 scripts/sync_codex_skills.py \
  --source-root ./skills \
  --codex-root ~/.claude/skills
```

Project install:

```bash
python3 scripts/sync_codex_skills.py \
  --source-root ./skills \
  --codex-root ./.claude/skills
```

Windows PowerShell:

```powershell
python scripts/sync_codex_skills.py `
  --source-root ".\skills" `
  --codex-root "$env:USERPROFILE\.claude\skills"
```

After sync, the skill should be available at:

```text
~/.claude/skills/nlpm-audit/SKILL.md
```

or:

```text
<project>/.claude/skills/nlpm-audit/SKILL.md
```

Claude Code can load the skill automatically when the request is relevant. You
can also call it explicitly:

```text
/nlpm-audit check whether this Claude Code plugin is installable and safe to publish
```

## Install For OpenClaw

Generate the flat export:

```bash
python3 scripts/export_openclaw_skills.py
```

Use:

```text
openclaw-skills/nlpm-audit/
```

The OpenClaw export includes:

- `SKILL.md`
- `references/`
- `scripts/nl_artifact_check.py`

## When It Should Auto-Trigger

AI agents are more likely to auto-select `nlpm-audit` when the user asks for:

- "audit this skill";
- "check whether this Claude/Codex plugin can install";
- "review AGENTS.md or CLAUDE.md";
- "check plugin.json against files on disk";
- "score these SKILL.md files";
- "generate an NL artifact audit report";
- "find prompt/rules/manifest drift";
- "security scan hooks, MCP servers, or executable commands";
- "compare our skill repository with NLPM-style rules".

It should not normally trigger for ordinary implementation tasks, UI changes,
business writing, or code-only debugging unless the task includes AI-facing
markdown, skills, prompts, manifests, hooks, agents, or commands.

## Explicit Invocation Examples

Codex:

```text
$nlpm-audit please audit the current repository's skills, AGENTS.md, commands, and plugin manifests
```

Claude Code:

```text
/nlpm-audit score the skills in this plugin and report blocking findings first
```

Plain agent prompt:

```text
Use the nlpm-audit skill. Generate a Markdown audit report for this repository's SKILL.md files, AGENTS.md, plugin manifests, hooks, and MCP configs.
```

## Local CLI Usage

The bundled script gives the skill a reusable executable core.

JSON output:

```bash
python skills/ai-workflow/nlpm-audit/scripts/nl_artifact_check.py . --json
```

Markdown report:

```bash
python skills/ai-workflow/nlpm-audit/scripts/nl_artifact_check.py . \
  --markdown --output nl-artifact-audit.md
```

Strict gate:

```bash
python skills/ai-workflow/nlpm-audit/scripts/nl_artifact_check.py . --strict
```

Windows PowerShell:

```powershell
python skills\ai-workflow\nlpm-audit\scripts\nl_artifact_check.py . `
  --markdown --output nl-artifact-audit.md
```

When the skill has been synced into a client-local directory, adjust the script
path to that local skill directory, for example:

```bash
python ~/.codex/skills/nlpm-audit/scripts/nl_artifact_check.py . --markdown
```

## How To Interpret The Output

The JSON output contains:

- `summary`: overall counts and average score;
- `artifacts`: discovered NL artifacts and types;
- `scores`: per-file score, band, and finding count;
- `findings`: high, medium, and low findings with suggested fixes.

Default gate:

- high finding: block release or publishing;
- medium finding: fix before release when cheap, otherwise track explicitly;
- low finding: batch into cleanup or style maintenance;
- no finding: pass the lightweight local check.

The Markdown output is designed to be attached to a PR, release review, or
maintenance issue.

## Upstream Upgrade Policy

This repository tracks `xiaolai/nlpm` in monitor-only mode. That means:

- upstream changes are detected by sync tooling;
- local curated content is not automatically overwritten;
- maintainers review upstream changes and selectively absorb durable rules,
  command patterns, scoring improvements, or validator behavior;
- executable upstream code should be pinned to a reviewed commit when used in CI.

Check upstream freshness with:

```bash
python scripts/sync_upstream.py --check-only --source github:xiaolai/nlpm
```

If the output says `[monitor-only]`, review upstream manually before editing the
curated skill.
