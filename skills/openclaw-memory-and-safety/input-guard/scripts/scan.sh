#!/usr/bin/env bash
# Input Guard — Shell wrapper for scanning untrusted text
#
# Usage:
#   scan.sh "text to scan"                    # Scan inline text
#   scan.sh --file /path/to/file.txt          # Scan a file
#   echo "text" | scan.sh --stdin             # Scan from stdin
#   scan.sh --json "text to scan"             # JSON output
#   scan.sh --quiet "text to scan"            # Just severity + score
#   scan.sh --sensitivity paranoid "text"     # Paranoid mode
#
# Exit codes:
#   0 = SAFE or LOW (ok to proceed)
#   1 = MEDIUM, HIGH, or CRITICAL (should stop)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "${SCRIPT_DIR}/scan.py" "$@"
