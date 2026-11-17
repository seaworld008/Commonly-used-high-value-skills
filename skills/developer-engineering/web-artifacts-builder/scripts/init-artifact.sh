#!/bin/bash
# Adapted from Anthropic's Apache-2.0 web-artifacts-builder script.
# Local changes: explicit engines, local tools, transactional delivery.
set -euo pipefail
if [ "$#" -ne 1 ] || [ -z "$1" ]; then
  echo 'Usage: init-artifact.sh <project-directory>' >&2
  exit 1
fi
for tool in node pnpm tar; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Error: $tool is required. Install it explicitly before running this script; no global installation was attempted." >&2
    exit 1
  fi
done
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec node "$SCRIPT_DIR/artifact-runtime.mjs" init "$(node --version)" "$1"
