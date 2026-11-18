---
name: repomix-safe-mixer
description: 'Scan for hardcoded credentials, report redacted findings, and block repomix packaging when risks are found. Use when packaging code for distribution, creating reference packages, or checking credentials before sharing a codebase.'
zh_description: "打包代码前扫描凭据、输出脱敏报告，并在发现风险时阻止打包。"
version: "1.0.2"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: ["development", "mixer", "repomix", "safe"]
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 5
complexity: "intermediate"
---

# Repomix Safe Mixer

## Overview

Scan for hardcoded credentials before packaging codebases with repomix, report
redacted findings, and block packaging until the user resolves them.

This skill helps find common credential patterns before packaging. A pattern
scan cannot guarantee that a package is safe to share.

**When to use**: When packaging code with repomix for distribution, creating shareable reference packages, or whenever security concerns exist about hardcoded credentials in code.

## Core Workflow

### Standard Safe Packaging

The gate distinguishes **clean / findings / scan-error**. `safe_pack.py` proceeds only after a completed clean scan. Findings and scan failures have distinct nonzero exits; `--force` does not bypass either. The scanner includes env files and ordinary PEM keys.

Check the actual packing manifest and scanner limitations. A clean pattern scan means no matches in the completed scope, not a guarantee that no secret exists. Keep explicit config paths intact and review exclusions before sharing.

```bash
python3 scripts/safe_pack.py <directory>
```

**Current wrapper behavior**:
1. Invokes the bundled pattern scanner
2. Reports parsed findings with redacted locations
3. Blocks on findings or an incomplete scan; `--force` cannot bypass the gate
4. Packs on empty findings even when completeness is unproven

**Example**:
```bash
python3 scripts/safe_pack.py ./my-project
```

**Existing wrapper output for empty findings (not a safety verdict)**:
```
🔍 Scanning ./my-project for hardcoded secrets...
✅ No secrets detected!
📦 Packing ./my-project with repomix...
✅ Packaging complete!
   Package is safe to distribute.
```

**Output if secrets found**:
```
🔍 Scanning ./my-project for hardcoded secrets...
⚠️  Security Scan Found 3 Potential Secrets:

🔴 supabase_url: 1 instance(s)
   - src/client.ts:5
     Match: [REDACTED]

❌ Cannot pack: Secrets detected!
```

### Options

**Custom output file**:
```bash
python3 scripts/safe_pack.py \
  ./my-project \
  --output package.xml
```

**With repomix config**:
```bash
python3 scripts/safe_pack.py \
  ./my-project \
  --config repomix.config.json
```

**Exclude patterns from scanning**:
```bash
python3 scripts/safe_pack.py \
  ./my-project \
  --exclude '.*test.*' '.*\.example'
```

**Force pack (dangerous, bypass findings block)**:
The flag still scans; it allows packaging despite findings. Do not use it for
shareable packages or as a workaround for scan errors.
```bash
python3 scripts/safe_pack.py \
  ./my-project \
  --force  # legacy compatibility flag; cannot bypass findings or scan errors
```

## Standalone Secret Scanning

Use `scan_secrets.py` from this skill's `scripts/` directory for scanning only (without packing).

Text reports show file/line locations, a fixed `potential credential` label, and
`[REDACTED]` instead of match content. They never echo rule metadata. Use `--json`
when rule types are needed; its `type` field remains available while `match` and
`context` stay redacted. Findings still return exit code 1; a clean scan returns 0.

```bash
python3 scripts/scan_secrets.py <directory>
```

**Use cases**:
- Verify cleanup after removing credentials
- Pre-commit security checks
- Audit existing codebases

**Example**:
```bash
python3 scripts/scan_secrets.py ./my-project
```

**JSON output for programmatic use**:
```bash
python3 scripts/scan_secrets.py \
  ./my-project \
  --json
```

**Exclude patterns**:
```bash
python3 scripts/scan_secrets.py \
  ./my-project \
  --exclude '.*test.*' '.*example.*' '.*SECURITY_AUDIT\.md'
```

## Detected Secret Types

The scanner detects common credential patterns including:

**Cloud Providers**:
- AWS Access Keys (`AKIA...`)
- Cloudflare R2 Account IDs and Access Keys
- Supabase Project URLs and Anon Keys

**API Keys**:
- Stripe Keys (`sk_live_...`, `pk_live_...`)
- OpenAI API Keys (`sk-...`)
- Google Gemini API Keys (`AIza...`)
- Generic API Keys

**Authentication**:
- JWT Tokens (`eyJ...`)
- OAuth Client Secrets
- Qualified private-key headers (`RSA`, `EC`, `OPENSSH`, `DSA`); ordinary
  `-----BEGIN PRIVATE KEY-----` requires another reviewed check
- Turnstile Keys (`0x...`)

See `references/common_secrets.md` for complete list and patterns.

## Handling Detected Secrets

When secrets are found:

### Step 1: Review Findings

Examine each finding to verify it's a real credential (not a placeholder or example).

### Step 2: Replace with Environment Variables

**Before**:
```javascript
const SUPABASE_URL = "https://your-project-ref.supabase.co";
const API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...";
```

**After**:
```javascript
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || "https://your-project-ref.supabase.co";
const API_KEY = import.meta.env.VITE_API_KEY || "your-api-key-here";

// Validation
if (!import.meta.env.VITE_SUPABASE_URL) {
  console.error("⚠️ Missing VITE_SUPABASE_URL environment variable");
}
```

### Step 3: Create .env.example

```bash
# Example environment variables
VITE_SUPABASE_URL=https://your-project-ref.supabase.co
VITE_API_KEY=your-api-key-here

# Instructions:
# 1. Copy this file to .env
# 2. Replace placeholders with real values
# 3. Never commit .env to version control
```

### Step 4: Verify Cleanup

Run the scanner again for pattern candidates, then verify all intended targets
with the reviewed complete scan described above:
```bash
python3 scripts/scan_secrets.py ./my-project
```

### Step 5: Safe Pack

After the independent gate is complete and clean, packaging may proceed.
The legacy wrapper below does not replace that gate:
```bash
python3 scripts/safe_pack.py ./my-project
```

## Post-Exposure Actions

If credentials were already exposed (e.g., committed to git, shared publicly):

1. **Rotate credentials immediately** - Generate new keys/tokens
2. **Revoke old credentials** - Disable compromised credentials
3. **Audit usage** - Check logs for unauthorized access
4. **Monitor** - Set up alerts for unusual activity
5. **Update deployment** - Deploy code with new credentials
6. **Document incident** - Record what was exposed and actions taken

## Common False Positives

The scanner skips common false positives:

**Placeholders**:
- `your-api-key`, `example-key`, `placeholder-value`
- `<YOUR_API_KEY>`, `${API_KEY}`, `TODO: add key`

**Test/Example files**:
- Files matching `.*test.*`, `.*example.*`, `.*sample.*`

**Comments**:
- Lines starting with `//`, `#`, `/*`, `*`

**Environment variable references** (correct usage):
- `process.env.API_KEY`
- `import.meta.env.VITE_API_KEY`
- `Deno.env.get('API_KEY')`

Use `--exclude` to skip additional patterns if needed.

## Integration with Repomix

This skill works with standard repomix:

**Default usage** (no config):
```bash
python3 scripts/safe_pack.py ./project
```

**With repomix config**:
```bash
python3 scripts/safe_pack.py \
  ./project \
  --config repomix.config.json
```

**Custom output location**:
```bash
python3 scripts/safe_pack.py \
  ./project \
  --output ~/Downloads/package-clean.xml
```

The wrapper runs repomix after its limited findings check, passing config and
output options. Review the actual packing manifest and exclusions. Report only
“no matches in the verified scanned scope”; do not repeat the wrapper's absolute
“safe to distribute” verdict as evidence.

## Example Workflows

### Workflow 1: Package a Clean Project

```bash
# Legacy scan-and-pack example; requires the independent gate above
python3 scripts/safe_pack.py \
  ~/workspace/my-project \
  --output ~/Downloads/my-project-package.xml
```

### Workflow 2: Clean and Package a Project with Secrets

```bash
# Step 1: Scan to discover secrets
python3 scripts/scan_secrets.py ~/workspace/my-project

# Step 2: Review findings and replace credentials with env vars
# (Edit files manually or with automation)

# Step 3: Verify cleanup
python3 scripts/scan_secrets.py ~/workspace/my-project

# Step 4: Package safely
python3 scripts/safe_pack.py \
  ~/workspace/my-project \
  --output ~/Downloads/my-project-clean.xml
```

### Workflow 3: Audit Before Commit

```bash
# Pre-commit hook: scan for secrets
python3 scripts/scan_secrets.py . --json

# Exit code 1 if secrets found (blocks commit)
# Exit code 0 means no findings, not complete coverage; scan errors must block commit
```

## Resources

**References**:
- `references/common_secrets.md` - Complete credential pattern catalog

**Scripts**:
- `scripts/scan_secrets.py` - Standalone security scanner
- `scripts/safe_pack.py` - Complete scan → pack workflow

**Related Skills**:
- `repomix-unmixer` - Extracts files from repomix packages
- `skill-creator` - Creates new Claude Code skills

## Security Note

This skill detects common patterns but may not catch all credential types. Always:
- Review findings manually
- Rotate exposed credentials
- Use .env.example templates
- Validate environment variables
- Monitor for unauthorized access

**Not a replacement for**: Secret scanning in CI/CD, git history scanning, or comprehensive security audits.
