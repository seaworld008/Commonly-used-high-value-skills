# NL Artifact Scoring Rubric

Use this reference when a user asks for a score, release readiness, or a
before/after quality comparison.

## Formula

```text
base_score = 100
final_score = max(0, min(100, base_score - penalties))
```

Use the score to communicate risk. Do not pretend it is a scientific
measurement.

## Score Bands

| Score | Label | Meaning |
|---:|---|---|
| 90-100 | Excellent | Production-ready |
| 80-89 | Good | Solid with minor gaps |
| 70-79 | Adequate | Usable but should improve |
| 60-69 | Weak | Significant issues |
| below 60 | Rewrite | Core design is unreliable |

## Common Penalties

| Finding | Penalty |
|---|---:|
| Missing required frontmatter field | -25 |
| Frontmatter `name` does not match directory name | -15 |
| Generic description with one or fewer trigger phrases | -15 |
| Description longer than 800 characters | -10 |
| Body exceeds 500 lines | -10 |
| Technical skill has no example | -10 |
| Missing scope note when related skills exist | -3 |
| Agent has zero examples | -15 |
| Agent has no output format | -10 |
| Review-only agent declares write tools | -10 |
| Command lacks empty-input behavior | -10 |
| Command lacks output format | -10 |
| Rule is not enforceable | -10 |
| Rule duplicates linter behavior | -10 |
| Hook script path is missing | -20 |
| Hook event name has wrong case | -10 |
| Memory file lacks build/run command | -10 |
| Memory file lacks test command | -5 |
| Broken `@path` import or stale file reference | -10 |
| Vague quantifier without criteria | -2 each, cap -20 |

## Deterministic vs Judgment Findings

Blocking deterministic findings:

- missing files referenced by manifests;
- files present on disk but unreachable from manifests or generated catalogs;
- invalid JSON/TOML/YAML syntax;
- missing required frontmatter;
- wrong hook event case;
- version drift across release surfaces.

Advisory judgment findings:

- weak trigger language;
- missing examples;
- overlong theory sections;
- output format lacks detail;
- vocabulary drift candidates.

## Calibration Examples

### Excellent Skill, 92

Characteristics:

- description names five concrete trigger situations;
- body under 500 lines;
- examples use real syntax;
- scope note distinguishes related skills;
- output format is explicit.

### Adequate Skill, 74

Characteristics:

- frontmatter is complete;
- workflow is useful;
- description has two trigger phrases;
- no examples;
- boundaries are vague.

Action: add examples, tighten description, and replace vague terms.

### Rewrite Skill, 45

Characteristics:

- missing description or title-like description only;
- body says "do the right thing" without criteria;
- no examples, no output format, no boundaries;
- duplicates another existing skill.

Action: rewrite around real user workflows instead of patching line by line.

## Reporting Pattern

```markdown
### Quality Scores
| File | Score | Band | Main penalties | Fix priority |
|---|---:|---|---|---|

### Blocking Findings
| File | Finding | Evidence | Required fix |
|---|---|---|---|

### Advisory Findings
| File | Finding | Why it matters | Suggested fix |
|---|---|---|---|
```

## Anti-Patterns

- Do not add penalties that cannot be tied to a listed rule.
- Do not count markdown documentation examples as executable security risks.
- Do not fail CI on subjective quality scores unless maintainers agreed to that
  gate.
- Do not reward bloated completeness; every extra line still costs context.
