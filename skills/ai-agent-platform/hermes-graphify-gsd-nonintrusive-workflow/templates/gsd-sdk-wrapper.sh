#!/usr/bin/env bash
set -euo pipefail

SDK_ROOT="${GSD_SDK_ROOT:-/data/ai-coding/get-shit-done/sdk}"
CLI_JS="$SDK_ROOT/dist/cli.js"
PACKAGE_JSON="$SDK_ROOT/package.json"

if [ ! -f "$PACKAGE_JSON" ]; then
  echo "[gsd-sdk-wrapper] ERROR: sdk package not found at $SDK_ROOT" >&2
  exit 1
fi

if [ ! -f "$CLI_JS" ]; then
  echo "[gsd-sdk-wrapper] ERROR: dist/cli.js missing under $SDK_ROOT" >&2
  echo "[gsd-sdk-wrapper] Try: cd $SDK_ROOT && npm install && npm run build" >&2
  exit 1
fi

exec node "$CLI_JS" "$@"
