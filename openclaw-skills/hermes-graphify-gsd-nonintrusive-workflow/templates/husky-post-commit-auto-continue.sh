#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"
ROOT_DIR="$(git rev-parse --show-toplevel)"
LOG_DIR="$ROOT_DIR/.planning/logs"
mkdir -p "$LOG_DIR"
nohup bash "$ROOT_DIR/scripts/hermes-auto-continue-trigger.sh" hook >> "$LOG_DIR/hermes-auto-continue.log" 2>&1 &
