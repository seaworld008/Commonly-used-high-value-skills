# GitHub CLI Command Patterns

Purpose: Use these commands when Harvest must fetch PR data safely, filter it precisely, or aggregate it into report-ready structures.

## Contents

- Preflight checks
- Core PR fetch patterns
- Filter dimensions
- Date filtering
- Aggregation snippets
- Release-note data
- Rate-limit aware execution

## Preflight Checks

Run these before any non-trivial collection:

```bash
gh auth status
gh repo view --json nameWithOwner
gh api rate_limit --jq '.resources.core.remaining'
```

Use `gh repo view -R owner/repo --json nameWithOwner` when the repository is not the current checkout.

## Core PR Fetch Patterns

### Standard PR list

```bash
gh pr list \
  --state all \
  --limit 100 \
  --json number,title,state,author,createdAt,updatedAt,mergedAt,additions,deletions,changedFiles,labels,url
```

### Merged PRs only

```bash
gh pr list \
  --state merged \
  --limit 100 \
  --json number,title,author,createdAt,mergedAt,additions,deletions,changedFiles,labels,url
```

### Repository-scoped query

```bash
gh pr list \
  -R owner/repo \
  --state merged \
  --limit 100 \
  --json number,title,author,createdAt,mergedAt,additions,deletions,changedFiles,labels,url
```

## Filter Dimensions

| Filter | Example | Use when |
|--------|---------|----------|
| State | `--state merged` | Building release notes or completed-work reports |
| Author | `--author simota` | Building an individual report |
| Label | `--label bug` | Narrowing to a category or release subset |
| Base branch | `--base main` | Limiting to a release or trunk branch |
| Search | `--search "label:feature review:approved"` | Combining advanced GitHub search filters |
| Repo | `-R owner/repo` | Working outside the current checkout |

## Date Filtering

`gh pr list` does not provide a native date-range flag. Filter after retrieval with `jq`.

### Cross-platform start-date helper

```bash
# macOS
start_date="$(date -v-7d +%Y-%m-%d)"

# Linux
start_date="$(date -d '7 days ago' +%Y-%m-%d)"
```

### Filter merged PRs by date

```bash
gh pr list --state merged --limit 200 --json number,title,author,mergedAt |
  jq --arg start "$start_date" '[.[] | select(.mergedAt >= $start)]'
```

### Filter created PRs by date

```bash
gh pr list --state all --limit 200 --json number,title,state,author,createdAt |
  jq --arg start "$start_date" '[.[] | select(.createdAt >= $start)]'
```

## Aggregation Snippets

### Count by author

```bash
gh pr list --state merged --limit 200 --json author |
  jq 'group_by(.author.login) | map({author: .[0].author.login, count: length})'
```

### Count by label

```bash
gh pr list --state merged --limit 200 --json labels |
  jq '[.[].labels[].name] | group_by(.) | map({label: .[0], count: length})'
```

### Size distribution

```bash
gh pr list --state merged --limit 200 --json additions,deletions |
  jq 'map((.additions + .deletions) as $size |
    if $size < 50 then "XS"
    elif $size < 200 then "S"
    elif $size < 500 then "M"
    elif $size < 1000 then "L"
    else "XL" end
  ) | group_by(.) | map({size: .[0], count: length})'
```

### Change volume by author

```bash
gh pr list --state merged --limit 200 --json author,additions,deletions |
  jq 'group_by(.author.login)
    | map({
        author: .[0].author.login,
        additions: (map(.additions) | add),
        deletions: (map(.deletions) | add)
      })'
```

## Release Notes Data

Use a tag range or release period, then classify titles with the category rules in `report-templates.md`.

```bash
gh pr list \
  --state merged \
  --limit 200 \
  --search "merged:>=2026-01-01 merged:<=2026-01-31" \
  --json number,title,author,mergedAt,labels,url
```

## Rate-Limit Aware Execution

### Pre-check remaining quota

```bash
remaining="$(gh api rate_limit --jq '.resources.core.remaining' 2>/dev/null)"
reset="$(gh api rate_limit --jq '.resources.core.reset' 2>/dev/null)"
```

### Recommended behavior

| Remaining quota | Action |
|-----------------|--------|
| `>= 100` | Proceed normally |
| `< 100` | Warn and consider cache or smaller query |
| `0` | Wait for reset or return a partial/blocking report |

For retries, backoff, health checks, and graceful degradation, read `error-handling.md`.
