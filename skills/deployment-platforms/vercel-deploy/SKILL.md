---
name: vercel-deploy
description: 'Deploy applications and websites to Vercel. Use when the user requests deployment actions like "deploy my app", "deploy and give me the link", "push this live", or "create a preview deployment".'
zh_description: "用于将应用或网站部署到 Vercel，创建预览部署或生产发布链接。"
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["deploy", "deployment", "vercel"]'
created_at: "2026-03-04"
updated_at: "2026-06-29"
quality: 3
complexity: "intermediate"
---

# Vercel Deploy

Deploy any project to Vercel instantly. **Always deploy as preview** (not production) unless the user explicitly asks for production.

## Prerequisites

- Check whether the Vercel CLI is installed **without** escalated permissions (for example, `command -v vercel`).
- Only escalate the actual deploy command if sandboxing blocks the deployment network calls (`sandbox_permissions=require_escalated`).
- The deployment might take a few minutes. Use appropriate timeout values.

## Quick Start

1. Check whether the Vercel CLI is installed (no escalation for this check):

```bash
command -v vercel
```

2. If `vercel` is installed, run this (with a 10 minute timeout):
```bash
vercel deploy [path] -y
```

**Important:** Use a 10 minute (600000ms) timeout for the deploy command since builds can take a while.

3. If `vercel` is not installed, or if the CLI fails with "No existing credentials found", use the fallback method below.

## Fallback (No Auth)

If CLI fails with auth error, use the deploy script:

```bash
skill_dir="<path-to-skill>"

# Deploy current directory
bash "$skill_dir/scripts/deploy.sh"

# Deploy specific project
bash "$skill_dir/scripts/deploy.sh" /path/to/project

# Deploy existing tarball
bash "$skill_dir/scripts/deploy.sh" /path/to/project.tgz
```

The script handles framework detection, packaging, and deployment. It waits for the build to complete and returns JSON with `previewUrl` and `claimUrl`.

**Tell the user:** "Your deployment is ready at [previewUrl]. Claim it at [claimUrl] to manage your deployment."

## Production Deploys

Only if user explicitly asks:
```bash
vercel deploy [path] --prod -y
```

## Output

Show the user the deployment URL. For fallback deployments, also show the claim URL.

**Do not** curl or fetch the deployed URL to verify it works. Just return the link.

## Troubleshooting

### Escalated Network Access

If deployment fails due to network issues (timeouts, DNS errors, connection resets), rerun the actual deploy command with escalated permissions (use `sandbox_permissions=require_escalated`). Do not escalate the `command -v vercel` installation check. The deploy requires escalated network access when sandbox networking blocks outbound requests.

Example guidance to the user:

```
The deploy needs escalated network access to deploy to Vercel. I can rerun the command with escalated permissions—want me to proceed?
```

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
