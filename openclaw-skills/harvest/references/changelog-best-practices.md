# Changelog Best Practices

Purpose: Use this reference when Harvest must produce release notes or changelog entries that are readable, category-accurate, and audience-fit.

## Contents

- Keep a Changelog principles
- Conventional Commits mapping
- Audience split
- Anti-patterns
- Harvest quality gates

## Keep a Changelog Principles

- Changelogs are for humans.
- Every version gets an entry.
- Group similar changes together.
- Latest release appears first.
- Include release date.
- Use linkable version headers when possible.

## Categories

| Category | Use for |
|----------|---------|
| `Added` | New features |
| `Changed` | Behavior or performance changes |
| `Deprecated` | Features scheduled for removal |
| `Removed` | Deleted capabilities |
| `Fixed` | Bug fixes |
| `Security` | Security fixes |

## Conventional Commits Mapping

| Commit type | Changelog category | SemVer hint |
|-------------|-------------------|-------------|
| `feat` | `Added` | Minor |
| `fix` | `Fixed` | Patch |
| `feat!` / `BREAKING CHANGE` | `Changed` + breaking note | Major |
| `perf` | `Changed` | Patch |
| `security` | `Security` | Patch |
| `deprecate` | `Deprecated` | N/A |

Internal-only types (`refactor`, `docs`, `test`, `chore`, `ci`, `build`, `style`) are usually omitted unless they change user-facing behavior.

## Audience Split

| Audience | Focus |
|----------|-------|
| Customer-facing | User impact, business language, minimal technical detail |
| Developer-facing | PR numbers, technical specificity, implementation detail |

## Anti-Patterns

| ID | Anti-pattern | Guardrail |
|----|--------------|-----------|
| `CL-01` | Copy-pasting `git log` | Curate from PR titles and verified summaries |
| `CL-02` | Missing major changes | Review all merged PRs in scope |
| `CL-03` | Missing deprecations | Always emit `Deprecated` when relevant |
| `CL-04` | Inconsistent date format | Use ISO `YYYY-MM-DD` |
| `CL-05` | No version number | Pair version and date |
| `CL-06` | Everything marked `Fixed` | Use the category system correctly |
| `CL-07` | Internal noise in user notes | Filter to user-visible impact |
| `CL-08` | Breaking changes buried | Put them at the top or in a dedicated section |

## Harvest Quality Gates

- If all entries fall into one category, verify classification.
- If breaking changes exist, highlight them explicitly.
- If the report is customer-facing, rewrite implementation detail into user-facing impact language.
