# Extended procedures and examples

Use [SKILL.md](SKILL.md) to select the task. Read only the sections it links for the current step.

<a id="section-1"></a>

### 7. Add CI or Pre-Commit Gates

Use different gates for different confidence levels.

Blocking gates:

- manifest references missing files;
- disk artifacts omitted from a required install manifest or generated catalog
  when the repository's publish contract says they belong there;
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

For changed-artifact scoring, test the selector itself. Enumerate all shipped NL
artifact layouts, including generated Codex or other client mirrors, and fail
when any publishable artifact cannot match the selector. When one source skill
is mirrored into multiple client layouts, compare normalized bodies so the
release gate cannot silently ship different rules to different clients.

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

For plugin monorepos or README badges, prefer upstream `nlpm-check` because it
knows how to isolate nested plugin roots and produce badge-ready JSON.

<a id="section-2"></a>

### 2. Check Manifest-vs-Disk Consistency

This is the highest-value deterministic check. Look for both directions:

- **Declared but missing:** a manifest references a skill, command, agent, hook,
  or script path that does not exist.
- **Present but unreachable:** a `SKILL.md`, command, agent, or hook exists on
  disk but is absent from the manifest, marketplace file, README index, catalog,
  or install surface users rely on.

The first case is a deterministic defect: a declared path cannot resolve. The
second case is initially an observation, because a repository may intentionally
ship only a curated subset. Escalate it to a blocking defect only when the
repository's own instructions, generated catalog contract, or package boundary
says that every artifact in that scope must be published. Quote that contract
with the diff. Otherwise report the omission as advisory and let the maintainer
choose whether to register the artifact or narrow the stated publish scope.

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

For badge output, use upstream `nlpm-badge` with the JSON stream from
`nlpm-check`:

```bash
nlpm-check --json . | nlpm-badge > nlpm-badge.json
```
