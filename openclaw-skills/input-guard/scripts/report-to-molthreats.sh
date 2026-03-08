#!/bin/bash
# Report an input-guard detection to MoltThreats
# Usage: report-to-molthreats.sh <severity> <source_url> <description>
#
# Severity: MEDIUM, HIGH, or CRITICAL (from input-guard)
# Source: URL or description of where the threat was found
# Description: What was detected (the finding)
#
# Environment variables:
#   PROMPTINTEL_API_KEY     — Required. API key for MoltThreats service.
#   OPENCLAW_WORKSPACE     — Path to openclaw workspace (default: ~/.openclaw/workspace)
#   MOLTHREATS_SCRIPT      — Path to molthreats.py (default: $OPENCLAW_WORKSPACE/skills/molthreats/scripts/molthreats.py)

set -e

if [ $# -lt 3 ]; then
  echo "Usage: $0 <severity> <source_url> <description>" >&2
  echo "" >&2
  echo "Example:" >&2
  echo "  $0 HIGH https://example.com/article 'Prompt injection: SYSTEM_INSTRUCTION detected in article body'" >&2
  echo "" >&2
  echo "Environment variables:" >&2
  echo "  PROMPTINTEL_API_KEY     Required. API key for MoltThreats service." >&2
  echo "  OPENCLAW_WORKSPACE     Path to openclaw workspace (default: ~/.openclaw/workspace)" >&2
  echo "  MOLTHREATS_SCRIPT      Path to molthreats.py (default: \$OPENCLAW_WORKSPACE/skills/molthreats/scripts/molthreats.py)" >&2
  exit 1
fi

# Resolve workspace and script paths
OPENCLAW_WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
MOLTHREATS_SCRIPT="${MOLTHREATS_SCRIPT:-$OPENCLAW_WORKSPACE/skills/molthreats/scripts/molthreats.py}"

# Check API key
if [ -z "$PROMPTINTEL_API_KEY" ]; then
  echo "Error: PROMPTINTEL_API_KEY environment variable is not set." >&2
  echo "Get your API key from the MoltThreats service and export it before running this script." >&2
  exit 1
fi

# Check molthreats script exists
if [ ! -f "$MOLTHREATS_SCRIPT" ]; then
  echo "Error: molthreats.py not found at $MOLTHREATS_SCRIPT" >&2
  echo "Set MOLTHREATS_SCRIPT or OPENCLAW_WORKSPACE to the correct path." >&2
  exit 1
fi

INPUT_SEVERITY="$1"
SOURCE_URL="$2"
DESCRIPTION="$3"

# Map input-guard severity to MoltThreats severity
case "$INPUT_SEVERITY" in
  CRITICAL)
    MOLT_SEVERITY="critical"
    ;;
  HIGH)
    MOLT_SEVERITY="high"
    ;;
  MEDIUM)
    MOLT_SEVERITY="medium"
    ;;
  *)
    echo "Error: Invalid severity '$INPUT_SEVERITY'. Must be MEDIUM, HIGH, or CRITICAL" >&2
    exit 1
    ;;
esac

# Generate title from description (first 80 chars)
TITLE=$(echo "$DESCRIPTION" | cut -c1-80)

# Build recommendation
RECOMMENDATION="BLOCK: External content from source $SOURCE_URL containing prompt injection patterns"

echo "🔒 Reporting to MoltThreats..."
echo ""
echo "Title: $TITLE"
echo "Category: prompt"
echo "Severity: $MOLT_SEVERITY"
echo "Source: $SOURCE_URL"
echo "Description: $DESCRIPTION"
echo ""

# Report using molthreats.py (absolute path, no cd)
python3 "$MOLTHREATS_SCRIPT" report \
  "$TITLE" \
  "prompt" \
  "$MOLT_SEVERITY" \
  "0.9" \
  "$DESCRIPTION. Source: $SOURCE_URL. Detected by input-guard automated scanning." \
  "$RECOMMENDATION" \
  "$SOURCE_URL"

echo ""
echo "✅ Report submitted to MoltThreats"
