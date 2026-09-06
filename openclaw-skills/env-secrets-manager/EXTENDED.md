# Extended procedures and examples

Use [SKILL.md](SKILL.md) to select the task. Read only the sections it links for the current step.

<a id="section-1"></a>

## Required Variable Validation Script

```bash
#!/bin/bash
# scripts/validate-env.sh
# Run at app startup or in CI before deploy
# Exit 1 if any required var is missing or empty

set -euo pipefail

MISSING=()
WARNINGS=()

# --- Define required vars by environment ---
ALWAYS_REQUIRED=(
  APP_SECRET
  APP_URL
  DATABASE_URL
  AUTH_JWT_SECRET
  AUTH_REFRESH_SECRET
)

PROD_REQUIRED=(
  STRIPE_SECRET_KEY
  STRIPE_WEBHOOK_SECRET
  SENTRY_DSN
)

# --- Check always-required vars ---
for var in "${ALWAYS_REQUIRED[@]}"; do
  if [ -z "${!var:-}" ]; then
    MISSING+=("$var")
  fi
done

# --- Check prod-only vars ---
if [ "${APP_ENV:-}" = "production" ] || [ "${NODE_ENV:-}" = "production" ]; then
  for var in "${PROD_REQUIRED[@]}"; do
    if [ -z "${!var:-}" ]; then
      MISSING+=("$var (required in production)")
    fi
  done
fi

# --- Validate format/length constraints ---
if [ -n "${AUTH_JWT_SECRET:-}" ] && [ ${#AUTH_JWT_SECRET} -lt 32 ]; then
  WARNINGS+=("AUTH_JWT_SECRET is shorter than 32 chars — insecure")
fi

if [ -n "${DATABASE_URL:-}" ]; then
  if ! echo "$DATABASE_URL" | grep -qE "^(postgres|postgresql|mysql|mongodb|redis)://"; then
    WARNINGS+=("DATABASE_URL doesn't look like a valid connection string")
  fi
fi

if [ -n "${APP_PORT:-}" ]; then
  if ! [[ "$APP_PORT" =~ ^[0-9]+$ ]] || [ "$APP_PORT" -lt 1 ] || [ "$APP_PORT" -gt 65535 ]; then
    WARNINGS+=("APP_PORT=$APP_PORT is not a valid port number")
  fi
fi

# --- Report ---
if [ ${#WARNINGS[@]} -gt 0 ]; then
  echo "WARNINGS:"
  for w in "${WARNINGS[@]}"; do
    echo "  ⚠️  $w"
  done
fi

if [ ${#MISSING[@]} -gt 0 ]; then
  echo ""
  echo "FATAL: Missing required environment variables:"
  for var in "${MISSING[@]}"; do
    echo "  ❌  $var"
  done
  echo ""
  echo "Copy .env.example to .env and fill in missing values."
  exit 1
fi

echo "✅  All required environment variables are set"
```

Node.js equivalent:
```typescript
// src/config/validateEnv.ts
const required = [
  'APP_SECRET', 'APP_URL', 'DATABASE_URL',
  'AUTH_JWT_SECRET', 'AUTH_REFRESH_SECRET',
]

const missing = required.filter(key => !process.env[key])

if (missing.length > 0) {
  console.error('FATAL: Missing required environment variables:', missing)
  process.exit(1)
}

if (process.env.AUTH_JWT_SECRET && process.env.AUTH_JWT_SECRET.length < 32) {
  console.error('FATAL: AUTH_JWT_SECRET must be at least 32 characters')
  process.exit(1)
}

export const config = {
  appSecret: process.env.APP_SECRET!,
  appUrl: process.env.APP_URL!,
  databaseUrl: process.env.DATABASE_URL!,
  jwtSecret: process.env.AUTH_JWT_SECRET!,
  refreshSecret: process.env.AUTH_REFRESH_SECRET!,
  stripeKey: process.env.STRIPE_SECRET_KEY,  // optional
  port: parseInt(process.env.APP_PORT ?? '3000', 10),
} as const
```

---

<a id="section-2"></a>

### Scan Working Tree
```bash
#!/bin/bash
# scripts/scan-secrets.sh
# Scan staged files and working tree for common secret patterns

FAIL=0

check() {
  local label="$1"
  local pattern="$2"
  local matches

  matches=$(git diff --cached -U0 2>/dev/null | grep "^+" | grep -vE "^(\+\+\+|#|\/\/)" | \
    grep -E "$pattern" | grep -v ".env.example" | grep -v "test\|mock\|fixture\|fake" || true)

  if [ -n "$matches" ]; then
    echo "SECRET DETECTED [$label]:"
    echo "$matches" | head -5
    FAIL=1
  fi
}

# AWS Access Keys
check "AWS Access Key" "AKIA[0-9A-Z]{16}"
check "AWS Secret Key" "aws_secret_access_key\s*=\s*['\"]?[A-Za-z0-9/+]{40}"

# Stripe
check "Stripe Live Key"   "sk_live_[0-9a-zA-Z]{24,}"
check "Stripe Test Key"   "sk_test_[0-9a-zA-Z]{24,}"
check "Stripe Webhook"    "whsec_[0-9a-zA-Z]{32,}"

# JWT / Generic secrets
check "Hardcoded JWT"     "eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"
check "Generic Secret"    "(secret|password|passwd|api_key|apikey|token)\s*[:=]\s*['\"][^'\"]{12,}['\"]"

# Private keys
check "Private Key Block" "-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
check "PEM Certificate"   "-----BEGIN CERTIFICATE-----"

# Connection strings with credentials
check "DB Connection"     "(postgres|mysql|mongodb)://[^:]+:[^@]+@"
check "Redis Auth"        "redis://:[^@]+@\|rediss://:[^@]+@"

# Google
check "Google API Key"    "AIza[0-9A-Za-z_-]{35}"
check "Google OAuth"      "[0-9]+-[0-9A-Za-z_]{32}\.apps\.googleusercontent\.com"

# GitHub
check "GitHub Token"      "gh[ps]_[A-Za-z0-9]{36,}"
check "GitHub Fine-grained" "github_pat_[A-Za-z0-9_]{82}"

# Slack
check "Slack Token"       "xox[baprs]-[0-9A-Za-z]{10,}"
check "Slack Webhook"     "https://hooks\.slack\.com/services/[A-Z0-9]{9,}/[A-Z0-9]{9,}/[A-Za-z0-9]{24,}"

# Twilio
check "Twilio SID"        "AC[a-z0-9]{32}"
check "Twilio Token"      "SK[a-z0-9]{32}"

if [ $FAIL -eq 1 ]; then
  echo ""
  echo "BLOCKED: Secrets detected in staged changes."
  echo "Remove secrets before committing. Use environment variables instead."
  echo "If this is a false positive, add it to .secretsignore or use:"
  echo "  git commit --no-verify  (only if you're 100% certain it's safe)"
  exit 1
fi

echo "No secrets detected in staged changes."
```

<a id="section-3"></a>

## .env.example Auto-Generation

```bash
#!/bin/bash
# scripts/gen-env-example.sh
# Strips values from .env, preserves keys, defaults, and comments

INPUT="${1:-.env}"
OUTPUT="${2:-.env.example}"

if [ ! -f "$INPUT" ]; then
  echo "ERROR: $INPUT not found"
  exit 1
fi

python3 - "$INPUT" "$OUTPUT" << 'PYEOF'
import sys, re

input_file = sys.argv[1]
output_file = sys.argv[2]
lines = []

with open(input_file) as f:
    for line in f:
        stripped = line.rstrip('\n')
        # Keep blank lines and comments as-is
        if stripped == '' or stripped.startswith('#'):
            lines.append(stripped)
            continue
        # Match KEY=VALUE or KEY="VALUE"
        m = re.match(r'^([A-Z_][A-Z0-9_]*)=(.*)$', stripped)
        if m:
            key = m.group(1)
            value = m.group(2).strip('"\'')
            # Keep non-sensitive defaults (ports, regions, feature flags)
            safe_defaults = re.compile(
                r'^(APP_PORT|APP_ENV|APP_NAME|AWS_REGION|DATABASE_POOL_|LOG_LEVEL|'
                r'FEATURE_|CACHE_TTL|RATE_LIMIT_|PAGINATION_|TIMEOUT_)',
                re.I
            )
            sensitive = re.compile(
                r'(SECRET|KEY|TOKEN|PASSWORD|PASS|CREDENTIAL|DSN|AUTH|PRIVATE|CERT)',
                re.I
            )
            if safe_defaults.match(key) and value:
                lines.append(f"{key}={value}  # default")
            else:
                lines.append(f"{key}=")
        else:
            lines.append(stripped)

with open(output_file, 'w') as f:
    f.write('\n'.join(lines) + '\n')

print(f"Generated {output_file} from {input_file}")
PYEOF
```

Usage:
```bash
bash scripts/gen-env-example.sh .env .env.example
# Commit .env.example, never .env
git add .env.example
```

---
