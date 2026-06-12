---
name: nlpm-audit
description: 'Audits natural-language programming artifacts such as SKILL.md, AGENTS.md, CLAUDE.md, slash commands, plugin manifests, hooks, rules, and prompt files. Use when reviewing AI-agent repositories, checking manifest-vs-disk consistency, scoring skill or agent quality, adding NL artifact CI gates, or diagnosing vocabulary and version drift across Claude Code, Codex, Cursor, Gemini, and Antigravity-style projects.'
version: "1.0.0"
author: seaworld008
source: github:xiaolai/nlpm
source_url: "https://github.com/xiaolai/nlpm"
license: ISC
tags: '[nlpm, natural-language-programming, skill-quality, agent-audit, ci, prompt-engineering]'
created_at: "2026-06-12"
updated_at: "2026-06-12"
quality: 4
complexity: advanced
---

# NLPM Audit

Audit natural-language programming artifacts as first-class code. Use this
skill when a repository contains AI-facing markdown, agent definitions, skills,
commands, rules, hooks, prompts, or plugin manifests that need quality review,
cross-file consistency checks, or CI enforcement.

This skill is inspired by the NLPM project, but it is a portable audit workflow:
you can apply the method manually, with repository scripts, or with the upstream
`nlpm-check` validator when the project wants a standalone CI gate.

## Quick Start

For most repository reviews:

1. Inventory NL artifacts with local search.
2. Run the bundled lightweight checker when filesystem access is available:

   ```bash
   python skills/ai-workflow/nlpm-audit/scripts/nl_artifact_check.py . --json
   ```

   For a shareable report:

   ```bash
   python skills/ai-workflow/nlpm-audit/scripts/nl_artifact_check.py . --markdown --output nl-artifact-audit.md
   ```

3. Read only the references needed for the task:

| Need | Read |
|---|---|
| Recreate original `/nlpm:*` command workflows without installing upstream NLPM | `references/command-recipes.md` |
| Detailed rules for skills, agents, commands, hooks, memory files, prompts, plugins | `references/audit-rules.md` |
| Score a file or compare before/after quality | `references/scoring-rubric.md` |
| Add CI, pre-commit hooks, or an upstream refresh plan | `references/ci-and-maintenance.md` |
| Review hooks, scripts, MCP configs, install scripts, or executable command paths | `references/security-patterns.md` |

The bundled script catches common deterministic and semi-deterministic issues,
classifies artifacts, computes lightweight 100-point scores, and can emit a
Markdown audit report. Read `references/command-recipes.md` when the user asks
for NLPM-style commands such as check, score, report, security scan, vocabulary
drift, or fix.
For original NLPM behavior, install upstream NLPM or run upstream `nlpm-check`.

## Capability Model

There are two useful operating modes:

| Mode | What you get | When to choose it |
|---|---|---|
| This repository skill | A portable review workflow that any Codex/Claude/Cursor-style agent can follow after installation | You want durable guidance, review reports, and integration with this curated skills repository |
| Upstream NLPM | Claude Code slash commands, multiple NLPM agents, rule skills, `bin/nlpm-check`, templates, tests, and the auditor pipeline | You want behavior closest to the original product, especially `/nlpm:*` commands or CI with the upstream validator |

The skill mode is installable and useful on its own, but it is not a byte-for-byte
replacement for upstream NLPM. Use upstream NLPM when a user explicitly asks for
the original slash commands, badge generator, auditor workflows, or exact
upstream scoring behavior.

## Local Command Equivalents

Use these local equivalents before reaching for the upstream plugin:

| User asks for | Do this |
|---|---|
| "list NL artifacts" | Run the checker with `--json` and read `artifacts[]` |
| "check this plugin/skill repo" | Run the checker with `--json`; fix high findings first |
| "score these artifacts" | Use the generated `scores[]` table, then apply `references/scoring-rubric.md` for judgment |
| "make a report" | Run the checker with `--markdown --output nl-artifact-audit.md` |
| "security scan" | Run the checker, filter `security/*` findings, then read `references/security-patterns.md` |
| "find vocabulary drift" | Read `references/command-recipes.md` and perform the vocabulary drift recipe |
| "fix NLPM issues" | Apply the fix loop in `references/command-recipes.md`, then rerun the same check |

## Upstream NLPM Usage

When the user wants the original tool experience, point them to the upstream
installation path instead of pretending this skill contains every command.

Claude Code plugin path:

```bash
claude plugin marketplace add xiaolai/claude-plugin-marketplace
claude plugin install nlpm@xiaolai --scope project
```

Standalone validator path:

```bash
curl -fsSL -o ./nlpm-check https://raw.githubusercontent.com/xiaolai/nlpm/main/bin/nlpm-check
python3 ./nlpm-check .
```

For CI, pin to a reviewed commit instead of `main` when reproducibility matters:

```bash
curl -fsSL -o ./nlpm-check \
  https://raw.githubusercontent.com/xiaolai/nlpm/<reviewed-commit>/bin/nlpm-check
python3 ./nlpm-check .
```

## When to Use

Use this skill for:

- reviewing a skill, agent, plugin, prompt pack, or rules repository before
  publishing it;
- checking that files listed in manifests actually exist, and that files on disk
  are reachable from the target manifest or catalog;
- scoring `SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, slash commands,
  hooks, rule files, and prompt files for clarity and trigger reliability;
- adding pre-commit, CI, or release gates for AI-agent repositories;
- finding drift between names, versions, commands, examples, and vocabulary;
- separating deterministic defects from judgment-based quality findings.

Route elsewhere when:

- the task is creating a single new skill from scratch: use `skill-creator`;
- the task is optimizing one user prompt or requirement: use `prompt-optimizer`;
- the task is setting up project context for a coding agent: use
  `context-engineering`;
- the task is security-only red teaming: use the repository's security audit
  skill first, then apply this skill to AI artifact structure.

## Core Principles

Treat natural-language artifacts like executable code:

- **Inventory before judging.** Build a complete map of artifacts, manifests,
  references, and generated files before scoring quality.
- **Separate deterministic failures from subjective quality.** Missing files,
  broken references, invalid frontmatter, bad hook event names, and version drift
  should fail CI. Tone, examples, and trigger quality may need human review.
- **Descriptions are triggers.** A skill or agent description must contain
  concrete action phrases that match real user requests, not a summary like
  "helps with testing".
- **Every line must change agent behavior.** Long, ornamental, or duplicated
  instructions consume attention budget and reduce reliability.
- **Prefer positive, testable rules.** "Use named exports because refactors stay
  reliable" is easier to follow than "do not use default exports".
- **Track drift over time.** NL artifacts degrade through vocabulary synonyms,
  stale examples, renamed files, old test commands, and version numbers updated
  in only one place.

## Audit Workflow

Run this sequence for a repository-level review.

### 1. Discover Artifacts

Create an inventory before opening files one by one.

```bash
find . -name 'SKILL.md' -o -name 'AGENTS.md' -o -name 'CLAUDE.md' -o -name 'GEMINI.md'
find . -path '*/commands/*.md' -o -path '*/agents/*.md' -o -path '*/rules/*.md'
find . -name 'plugin.json' -o -name 'marketplace.json' -o -name 'hooks.json' -o -name 'settings.json'
```

On Windows PowerShell:

```powershell
Get-ChildItem -Recurse -File |
  Where-Object {
    $_.Name -in @('SKILL.md','AGENTS.md','CLAUDE.md','GEMINI.md','plugin.json','marketplace.json','hooks.json','settings.json') -or
    $_.FullName -match '\\(commands|agents|rules)\\[^\\]+\.md$'
  } |
  Select-Object FullName
```

Classify each artifact:

| Artifact | Primary checks |
|---|---|
| `SKILL.md` | frontmatter, trigger description, examples, scope, line budget |
| agent definitions | description, examples, model/tool fit, output format |
| slash commands | numbered flow, empty-input behavior, outputs, error paths |
| rules files | imperative wording, rationale, enforceability, path scope |
| memory files | project map, commands, test instructions, architecture, boundaries |
| plugin manifests | declared files exist, disk files are declared, version consistency |
| hooks | event names, script paths, fail-open/fail-closed intent, permissions |
| prompts | layered intent, exact output shape, injection resistance |

### 2. Check Manifest-vs-Disk Consistency

This is the highest-value deterministic check. Look for both directions:

- **Declared but missing:** a manifest references a skill, command, agent, hook,
  or script path that does not exist.
- **Present but unreachable:** a `SKILL.md`, command, agent, or hook exists on
  disk but is absent from the manifest, marketplace file, README index, catalog,
  or install surface users rely on.

Example report:

```text
BROKEN  .claude-plugin/plugin.json references skills/reviewer/SKILL.md
        file not found; actual path is skills/code-reviewer/SKILL.md

ORPHAN  skills/refactor-helper/SKILL.md
        skill exists on disk but is not listed in plugin.json or catalog

DRIFT   plugin.json version 1.4.0, marketplace.json version 1.3.9
        release metadata will publish a stale version
```

For machine checks, prefer a deterministic script over manual review. If the
project only needs a lightweight bundled check:

```bash
python skills/ai-workflow/nlpm-audit/scripts/nl_artifact_check.py . --json
```

If the project wants the upstream NLPM validator:

```bash
curl -fsSL -o ./nlpm-check https://raw.githubusercontent.com/xiaolai/nlpm/main/bin/nlpm-check
python3 ./nlpm-check .
```

Pin the downloaded script to a reviewed commit in CI if supply-chain stability is
more important than receiving upstream fixes immediately.

### 3. Score Artifact Quality

Use a 100-point score as a communication tool, not as an absolute truth. Start
at 100 and subtract penalties for concrete defects.

| Finding | Typical penalty | Why it matters |
|---|---:|---|
| Missing description/frontmatter | -25 | artifact cannot be discovered or routed reliably |
| Generic trigger description | -15 | model cannot tell when to invoke it |
| No examples for an agent or user-invocable skill | -10 to -15 | trigger behavior is under-specified |
| Missing output format | -10 | downstream users cannot compare results |
| Tool permissions exceed body needs | -5 to -10 | unnecessary security and review risk |
| Broken manifest/reference path | -10 to -20 | installed artifact silently disappears |
| Vague terms without criteria | -2 each, cap at -20 | "appropriate" and "as needed" hide decisions |
| Overgrown body with repeated theory | -5 to -10 | context budget is wasted |
| Missing test/build commands in memory file | -5 | agent cannot verify work |

Suggested bands:

| Score | Meaning | Action |
|---:|---|---|
| 90-100 | production-ready | publish after deterministic checks pass |
| 80-89 | good | fix high-signal gaps before release if cheap |
| 70-79 | acceptable | publish only for legacy artifacts or internal use |
| 60-69 | weak | improve before users depend on it |
| below 60 | rewrite | redesign the artifact around real workflows |

### 4. Review Trigger Descriptions

A description should be a router. It should name user intents, file types,
contexts, and nearby phrases a real user might type.

Weak:

```yaml
description: "Helps with code review."
```

Better:

```yaml
description: "Reviews pull request diffs for correctness, security, performance, and maintainability. Use when checking an auth refactor, API endpoint, migration, or dependency change before merge."
```

Check each description for:

- three or more specific trigger phrases;
- the artifact's boundary against adjacent skills or agents;
- verbs that name work, such as "review", "score", "migrate", "audit",
  "summarize", or "generate";
- absence of empty intensifiers such as "useful", "helpful", and criteria-free
  adverbs that hide decisions.

### 5. Check Examples and Output Contracts

For skills and agents, examples are executable documentation for the model.

Minimum useful example:

```markdown
<example>
Context: Developer preparing a Claude Code plugin for release.
user: "Check whether my new skill is actually installable from plugin.json."
assistant: "I'll inventory the manifest and disk paths, then report missing,
orphaned, and version-drift findings before scoring the skill body."
</example>
```

For commands and agents, require an output contract:

```markdown
## Output Format

### Summary
N artifacts scanned | N deterministic failures | N quality findings

### Blocking Findings
| File | Rule | Evidence | Fix |
|---|---|---|---|

### Advisory Findings
| File | Score | Reason | Suggested next action |
|---|---:|---|---|
```

### 6. Find Vocabulary and Version Drift

Drift appears when a project uses multiple words for the same operation or
updates version metadata in only one location.

Look for:

- `lint`, `score`, `audit`, `validate`, and `check` used interchangeably;
- renamed agents or skills still referenced by old names;
- README command examples that no longer match scripts;
- version numbers split across plugin manifest, marketplace metadata, changelog,
  README tables, badges, and release notes;
- contradictory memory files, such as `AGENTS.md` saying `pnpm test` while
  `CLAUDE.md` says `npm test`.

When drift is large, create a small vocabulary registry:

```yaml
canonical:
  check:
    definition: "deterministic structural validation"
    deprecated: [lint, validate]
  score:
    definition: "100-point quality judgment with penalties"
    deprecated: [grade, rate]
```

Do not enforce vocabulary too early. Use it once a project has at least ten NL
artifacts or multiple authors.

### 7. Add CI or Pre-Commit Gates

Use different gates for different confidence levels.

Blocking gates:

- manifest references missing files;
- disk artifacts missing from install manifest or generated catalog;
- invalid YAML/TOML/JSON frontmatter;
- hook scripts referenced but absent;
- version metadata inconsistent across release surfaces;
- security-sensitive executable artifact added without review.

Advisory gates:

- quality score below threshold;
- too many vague terms;
- missing examples;
- description has weak trigger phrases;
- vocabulary drift candidates.

Example GitHub Actions shape:

```yaml
name: nl-artifact-check
on:
  pull_request:
    paths:
      - "skills/**"
      - "agents/**"
      - "commands/**"
      - ".claude-plugin/**"
      - ".codex-plugin/**"
      - "AGENTS.md"
      - "CLAUDE.md"
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run deterministic NL artifact checks
        run: |
          curl -fsSL -o nlpm-check https://raw.githubusercontent.com/xiaolai/nlpm/main/bin/nlpm-check
          python3 nlpm-check .
```

For repositories like this one, keep using the local canonical pipeline first.
Add NLPM-style checks only when they catch a gap the repository pipeline does
not already cover.

## Triage Rules

Classify findings so maintainers know what to fix now.

| Severity | Criteria | Default action |
|---|---|---|
| Blocking | artifact cannot install, trigger, run, or pass manifest checks | fix in the same PR |
| High | security-sensitive permission, executable hook risk, or stale release metadata | fix before publish |
| Medium | trigger ambiguity, missing examples, weak output format | schedule before next release |
| Low | wording cleanup, minor drift, optional score improvement | batch with maintenance |
| External noise | API rate limit, stale upstream clone, network failure | report separately and retry |

Never mix external-state noise with repository regressions. A GitHub API rate
limit is not a quality failure; a generated catalog drift is.

## Maintenance Guidance

For upstream-derived NLPM practices:

- re-check the upstream repository before major refreshes because artifact
  schemas and supported tools evolve quickly;
- keep copied guidance small and method-oriented, not a mirror of every upstream
  rule;
- prefer stable checks such as manifest consistency, trigger specificity, and
  output contracts over tool-specific details that may change;
- record the upstream license and source URL in frontmatter;
- pin CI scripts to reviewed commits when adopting upstream executable files.

Read `references/ci-and-maintenance.md` before changing sync behavior, CI
templates, or the upstream refresh process.

Detailed refresh commands, monitor-only sync expectations, and upstream review
targets live in `references/ci-and-maintenance.md`.

## Deliverable Template

Use this structure for audit results:

```markdown
## NL Artifact Audit

### Decision
PASS | PASS WITH FIXES | BLOCKED

### Inventory
- Skills:
- Agents:
- Commands:
- Rules:
- Manifests:
- Hooks:

### Blocking Findings
| File | Finding | Evidence | Fix |
|---|---|---|---|

### Quality Scores
| File | Score | Band | Main penalties |
|---|---:|---|---|

### Drift Findings
| Concept | Current variants | Canonical recommendation |
|---|---|---|

### CI Recommendation
[blocking/advisory gates to add or skip]

### Maintenance Notes
[upstream version checked, license, false positives, unresolved external noise]
```

## Boundaries

- Do not copy unlicensed upstream artifacts into a project.
- Do not make subjective scoring the only release gate.
- Do not fail CI on advisory vocabulary drift until maintainers opt in.
- Do not replace a repository's established generated-file pipeline unless the
  maintainers explicitly choose that migration.
- Do not grant hook or command execution permissions just because an artifact
  asks for them; audit executable paths separately.
