---
name: github-ops
description: 'Operate GitHub repositories, PRs, issues, reviews, labels, releases, and Actions through gh CLI and GitHub API when repository coordination or automation is requested.'
zh_description: "通过 gh CLI 和 API 处理 GitHub 仓库、PR、Issue、Review、标签、发布和 Actions 协作。"
version: "1.1.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["devops", "github", "ops", "sre"]'
created_at: "2026-03-04"
updated_at: "2026-11-04"
quality: 5
complexity: "intermediate"
---

# GitHub Operations

## Overview

This skill provides comprehensive guidance for GitHub operations using the `gh` CLI tool and GitHub REST/GraphQL APIs. Use this skill when performing any GitHub-related tasks including pull request management, issue tracking, repository operations, workflow automation, and API interactions.

## When to Use This Skill

This skill activates for tasks involving:
- Creating, viewing, editing, or merging pull requests
- Managing labels, milestones, and releases
- Managing GitHub issues or repository settings
- Querying GitHub API endpoints (REST or GraphQL)
- Working with GitHub Actions workflows
- Performing bulk operations on repositories
- Integrating with GitHub Enterprise
- Automating GitHub operations via CLI or API

## Core Operations

### Pull Requests

```bash
# Create a PR; follow the repository's own title convention (check CONTRIBUTING.md,
# PR templates, and recent merged titles before choosing a prefix or ticket key)
gh pr create --title "feat: concise summary" --body-file pr-body.md --base main
gh pr create --fill --draft           # draft from commit messages

# List and view PRs
gh pr list --state open
gh pr view 123 --json title,state,mergeable,reviewDecision,statusCheckRollup

# Review, check, and merge
gh pr checks 123 --watch
gh pr review 123 --approve
gh pr merge 123 --squash --delete-branch
gh pr comment 123 --body "Addressed in 1a2b3c4"
```

📚 See `references/pr_operations.md` for comprehensive PR workflows

**Before merging:** confirm the latest head SHA has passing required checks,
review threads are resolved or answered, and `mergeable` is not `CONFLICTING`.
Complex conflicts are resolved in a local git checkout, not through `gh`.

### Issues

```bash
# Create and manage issues
gh issue create --title "Bug: Issue title" --body "Issue description"
gh issue list --state open --label bug
gh issue edit 456 --add-label "priority-high"
gh issue close 456
```

📚 See `references/issue_operations.md` for detailed issue management

### Repositories

```bash
# View and manage repos
gh repo view --web
gh repo clone owner/repo
gh repo create my-new-repo --public
```

### Workflows

```bash
# Manage GitHub Actions
gh workflow list
gh workflow run workflow-name
gh run watch run-id
gh run download run-id
```

📚 See `references/workflow_operations.md` for advanced workflow operations

### GitHub API

The `gh api` command provides direct access to GitHub REST API endpoints. Refer to `references/api_reference.md` for comprehensive API endpoint documentation.

**Basic API operations:**
```bash
# Get PR details via API
gh api repos/{owner}/{repo}/pulls/{pr_number}

# Add PR comment
gh api repos/{owner}/{repo}/issues/{pr_number}/comments \
  -f body="Comment text"

# List workflow runs
gh api repos/{owner}/{repo}/actions/runs
```

For complex queries requiring multiple related resources, use GraphQL. See `references/api_reference.md` for GraphQL examples.

## Authentication and Configuration

```bash
# Login to GitHub
gh auth login

# Login to GitHub Enterprise
gh auth login --hostname github.enterprise.com

# Check authentication status
gh auth status

# Set default repository
gh repo set-default owner/repo

# Configure gh settings
gh config set editor vim
gh config set git_protocol ssh
gh config list
```

### Authentication and rate limits

Run `gh auth status` before automation. When a script calls the GitHub API and no
explicit `GITHUB_TOKEN` / `GH_TOKEN` is set, reuse the authenticated `gh` session
(`gh api`, or `GH_TOKEN=$(gh auth token)` for that one process) instead of anonymous
requests, which hit `401` and early rate limits. Never print the token. Use the
least-privileged token that covers the task; bulk `gh api` or `gh search` loops can
trigger secondary rate limits, so page with `--paginate` and back off on `403`/`429`.

## Recurring Maintenance and Warning Triage

- `git fetch origin --prune` before discovery, sync, or release work.
- Split a small, certain fix and a large batch sync into separate branches and PRs;
  merge the focused PR first so a rollback does not drag unrelated changes.
- Classify warnings: a repository quality regression is fixed in place; an external
  `401` from anonymous calls, an intermediate `404` during upstream fallback probes,
  or a transient network error is recorded separately and named in the PR, not
  reported as a repository failure.
- Fetch failing CI logs before proposing a fix; `gh-fix-ci` covers the full loop:

```bash
RUN_ID=$(gh run list --status failure --limit 1 --json databaseId -q '.[0].databaseId')
gh run view "$RUN_ID" --log-failed > ci-failure.log
```

Destructive or broad actions (force push, deleting branches or releases, bulk
closing issues, changing collaborators) follow the user's explicit request; state
the exact target set in the summary.

## Output Formats

Control output format for programmatic processing:

```bash
# JSON output
gh pr list --json number,title,state,author

# JSON with jq processing
gh pr list --json number,title | jq '.[] | select(.title | contains("bug"))'

# Template output
gh pr list --template '{{range .}}{{.number}}: {{.title}}{{"\n"}}{{end}}'
```

📚 See `references/best_practices.md` for shell patterns and automation strategies

## Quick Reference

**Most Common Operations:**
```bash
gh pr create --title "Title" --body "Description"         # Create PR
gh pr list                                                  # List PRs
gh pr view 123                                              # View PR details
gh pr checks 123                                            # Check PR status
gh pr merge 123 --squash                                    # Merge PR
gh pr comment 123 --body "LGTM"                            # Comment on PR
gh issue create --title "Title" --body "Description"       # Create issue
gh workflow run workflow-name                               # Run workflow
gh repo view --web                                          # Open repo in browser
gh api repos/{owner}/{repo}/pulls/{pr_number}              # Direct API call
```

## Resources

### references/pr_operations.md

Comprehensive pull request operations including:
- Detailed PR creation patterns (ticket-key titles, body from file, targeting branches)
- Viewing and filtering strategies
- Review workflows and approval patterns
- PR lifecycle management
- Bulk operations and automation examples

Load this reference when working with complex PR workflows or bulk operations.

### references/issue_operations.md

Detailed issue management examples including:
- Issue creation with labels and assignees
- Advanced filtering and search
- Issue lifecycle and state management
- Bulk operations on multiple issues
- Integration with PRs and projects

Load this reference when managing issues at scale or setting up issue workflows.

### references/workflow_operations.md

Advanced GitHub Actions workflow operations including:
- Workflow triggers and manual runs
- Run monitoring and debugging
- Artifact management
- Secrets and variables
- Performance optimization strategies

Load this reference when working with CI/CD workflows or debugging failed runs.

### references/best_practices.md

Shell scripting patterns and automation strategies including:
- Output formatting (JSON, templates, jq)
- Pagination and large result sets
- Error handling and retry logic
- Bulk operations and parallel execution
- Enterprise GitHub patterns
- Performance optimization

Load this reference when building automation scripts or handling enterprise deployments.

### references/api_reference.md

Contains comprehensive GitHub REST API endpoint documentation including:
- Complete API endpoint reference with examples
- Request/response formats
- Authentication patterns
- Rate limiting guidance
- Webhook configurations
- Advanced GraphQL query patterns

Load this reference when performing complex API operations or when needing detailed endpoint specifications.
