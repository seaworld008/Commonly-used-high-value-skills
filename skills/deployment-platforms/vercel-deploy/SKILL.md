---
name: vercel-deploy
description: Create Vercel preview or production deployments when the user selects Vercel or the repository already binds the project to Vercel.
zh_description: "用于将应用或网站部署到 Vercel，创建预览部署或生产发布链接。"
version: "1.0.1"
author: "OpenAI contributors; local curators"
source: "https://github.com/openai/skills"
source_url: "https://github.com/openai/skills/blob/49f948faa9258a0c61caceaf225e179651397431/skills/.curated/vercel-deploy/SKILL.md"
license: "MIT"
tags: ["deploy", "deployment", "vercel"]
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 3
complexity: "intermediate"
---

# Vercel Deploy

Use the selected Vercel account, project and team. Default to a preview unless production is explicitly requested.

## Prerequisites

- Check whether the Vercel CLI is installed **without** escalated permissions (for example, `command -v vercel`).
- Check that the host permits the requested upload to the selected Vercel target.
- The deployment might take a few minutes. Use appropriate timeout values.

## Quick Start

1. Check whether the Vercel CLI is installed (no escalation for this check):

```bash
command -v vercel
```

2. Verify the CLI identity and project/team binding match the requested target, then run the preview deploy:
```bash
vercel deploy [path] -y
```

**Important:** Use a 10 minute (600000ms) timeout for the deploy command since builds can take a while.

3. If the CLI or credentials are missing, report what is needed for the selected account.

## Optional claimable deployment

The bundled script posts to `https://codex-deploy-skills.vercel.sh/api/deploy`. It returns a claim link for subsequent ownership. Use this service only when the user selects that recipient and claim flow. It does not use the CLI's selected project/team binding.

Directory mode excludes `node_modules`, `.git`, `.env` and `.env.*` and packages the staged files. A supplied `.tgz` is sent as supplied. Review the exact contents, including hidden files and credentials, and confirm the upload scope before sending. Prefer a reviewed archive to make the approved contents reproducible.

```bash
bash "$skill_dir/scripts/deploy.sh" /path/to/reviewed-project.tgz
```

A returned `previewUrl` and `claimUrl` establish submission. The script may print "ready" for 4xx or return URLs after polling times out. Report build status from the platform and runtime status from an authorized application check.

## Production Deploys

Only if user explicitly asks:
```bash
vercel deploy [path] --prod -y
```

## Output

Return the deployment URL and, for a claimable deployment, the claim URL to the requester. When acceptance includes runtime verification, check the expected response and report the observed status, including access errors or timeout.

## Troubleshooting

### Network failures

Check the CLI error and platform status to distinguish authentication, DNS, service availability and host permission failures. For a confirmed permission denial, use the host approval mechanism only if available and permitted. If networking is unavailable, deliver the prepared artifacts and record which deployment checks are pending.

## Pre-deploy Checklist

Before deploying:

- Confirm the project root and framework detection are correct.
- Check for uncommitted changes if the deployment should represent a specific git state.
- Identify required environment variables and whether they are already configured in Vercel.
- Prefer preview deployments unless the user explicitly asks for production.
- Use a long timeout for builds and report build logs if deployment fails.
- Do not expose secrets in terminal output, PR comments, or final messages.

## Post-deploy Response

Return the deployment URL, whether it is preview or production, and any claim/manage URL produced by the fallback script. If the deploy command succeeds but runtime verification was not performed, say so directly. If verification is requested, use a normal browser or HTTP check only after the deployment URL is available.
