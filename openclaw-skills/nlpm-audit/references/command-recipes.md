# NLPM Command Recipes

Use these recipes when a user asks for original NLPM-style commands but the
full Claude Code plugin is not installed. They preserve the workflow intent
without requiring slash commands, subagents, or upstream binaries.

## Command Mapping

| Original intent | Local equivalent | Result |
|---|---|---|
| `/nlpm:ls` | Run discovery through `nl_artifact_check.py --json` and read `artifacts[]` | Classified inventory |
| `/nlpm:check` | Run `nl_artifact_check.py . --json` | Manifest, frontmatter, reference, and security findings |
| `/nlpm:score` | Read `scores[]` from `--json` output or the score table from `--markdown` | Per-file 100-point score |
| `/nlpm:report` | Run `nl_artifact_check.py . --markdown --output nl-artifact-audit.md` | Self-contained Markdown report |
| `/nlpm:security-scan` | Run local check, then read `security-patterns.md` for judgment review | Gate-oriented security findings |
| `/nlpm:vocab-drift` | Use the vocabulary drift recipe below | Advisory synonym and naming review |
| `/nlpm:fix` | Use findings as a repair plan; make scoped edits; rerun the check | Verified remediation loop |
| `/nlpm:init` | Create or update a local NLPM config/checklist manually | Project-specific threshold and gate decisions |
| `/nlpm:test` | Write `.nlpm-test/*.spec.md` expectations, then compare artifacts manually or with upstream NLPM | NL artifact TDD loop |
| `/nlpm:trend` | Save repeated score reports and compare before/after tables | Release-readiness trend |

## Quick CLI Recipes

Inventory:

```bash
python skills/ai-workflow/nlpm-audit/scripts/nl_artifact_check.py . --json
```

Markdown report:

```bash
python skills/ai-workflow/nlpm-audit/scripts/nl_artifact_check.py . \
  --markdown --output nl-artifact-audit.md
```

Strict local gate:

```bash
python skills/ai-workflow/nlpm-audit/scripts/nl_artifact_check.py . --strict
```

Upstream deterministic gate:

```bash
curl -fsSL -o ./nlpm-check \
  https://raw.githubusercontent.com/xiaolai/nlpm/main/bin/nlpm-check
python3 ./nlpm-check .
```

PowerShell report:

```powershell
python skills\ai-workflow\nlpm-audit\scripts\nl_artifact_check.py . `
  --markdown --output nl-artifact-audit.md
```

## Report Recipe

1. Run the Markdown report command.
2. Read the generated report.
3. Add a short human summary before sending it to the user:

```markdown
## NL Artifact Audit Summary

Decision: PASS | PASS WITH FIXES | BLOCKED
Main risk:
Highest-value fix:
Recommended next gate:

[Include or link the generated report below.]
```

4. If the target is a Claude Code plugin or marketplace package, compare the
   local output with upstream `nlpm-check` before release when feasible.

## Score Recipe

Use the local scores as a triage heuristic:

| Score | Meaning | Action |
|---:|---|---|
| 90-100 | strong | publish if high findings are zero |
| 80-89 | good | fix cheap medium findings |
| 70-79 | adequate | review trigger descriptions and examples |
| 60-69 | weak | improve before external users depend on it |
| below 60 | rewrite | redesign the artifact around real workflows |

The script score is intentionally deterministic and conservative. For nuanced
agent behavior, combine the score with `scoring-rubric.md` and inspect the file
manually.

## Security Scan Recipe

1. Run the local checker and filter findings where `rule` starts with
   `security/`.
2. Read `security-patterns.md` if the project contains hooks, MCP servers,
   shell scripts, install scripts, or commands that execute code.
3. Produce one of these gates:

```text
SECURITY GATE: BLOCKED
Critical/high executable risk found. Do not install or publish until resolved.

SECURITY GATE: REVIEW NEEDED
Medium executable risk or unclear permission boundary. Review before install.

SECURITY GATE: PASSED
No critical/high executable risks found by the lightweight check.
```

## Vocabulary Drift Recipe

Use this for repositories with at least ten NL artifacts, multiple authors, or
visible naming drift.

1. Inventory artifact names, headings, command names, and repeated verbs.
2. Cluster likely synonyms by role:
   - check, validate, lint, audit
   - score, rate, grade
   - scan, discover, list
   - agent, subagent, worker
   - rule, convention, policy
3. Do not flag cross-scope homonyms when the scope is clear.
4. Report only high-signal drift:

```markdown
### Vocabulary Drift
| Concept | Current variants | Suggested canonical | Why |
|---|---|---|---|
| deterministic validation | check, lint, validate | check | matches CI gate wording |
```

Vocabulary drift is advisory until the repository creates a registry and opts
into enforcement.

For the upstream R51-style flow:

1. Bootstrap a candidate registry from artifact names, headings, repeated verbs,
   and role nouns.
2. Keep one canonical term per distinct concept and record deprecated synonyms.
3. Declare the scope for each term so homonyms do not create false positives.
4. Enforce only after maintainers review the registry.

Do not penalize early-stage projects for vocabulary exploration.

## Badge Recipe

Use upstream NLPM when the user asks for a "Validated by NLPM" badge.

```bash
curl -fsSL -o ./nlpm-check \
  https://raw.githubusercontent.com/xiaolai/nlpm/main/bin/nlpm-check
curl -fsSL -o ./nlpm-badge \
  https://raw.githubusercontent.com/xiaolai/nlpm/main/bin/nlpm-badge
python3 ./nlpm-check --json . | python3 ./nlpm-badge > nlpm-badge.json
```

Then add a README badge that points at the committed `nlpm-badge.json` endpoint.
The upstream payload includes issue counts, validator version, and a checked-at
timestamp for downstream verification.

## Multi-Plugin Monorepo Recipe

Use upstream `nlpm-check` for repositories with multiple
`.claude-plugin/plugin.json` or tool-specific plugin roots. It isolates nested
plugins so a child plugin is not double-counted by the parent, and the JSON
output includes per-plugin findings under `plugins[]` plus an aggregate summary.

Use this local checker only as a lightweight fallback when upstream execution is
not available.

## Fix Loop Recipe

1. Run `--markdown` and identify high findings.
2. Fix deterministic breakage first:
   - missing manifest paths;
   - unregistered skills, agents, and commands;
   - missing frontmatter;
   - bad executable paths;
   - stale `@path` references.
3. Rerun the same command.
4. Only then improve medium and low findings such as trigger descriptions,
   examples, and vague wording.
5. Keep a before/after score table in the final note.

## Upstream Parity Notes

The local recipe layer intentionally does not reproduce:

- Claude Code slash command registration;
- upstream subagent dispatch;
- HTML report rendering;
- badge generation and `nlpm-badge` JSON shaping;
- the full NLPM auditor corpus.

When a user asks for those exact product behaviors, install or invoke upstream
NLPM. When they ask for an audit that is portable across Codex, Claude, Cursor,
Gemini, and repository CI, use this local recipe layer.
