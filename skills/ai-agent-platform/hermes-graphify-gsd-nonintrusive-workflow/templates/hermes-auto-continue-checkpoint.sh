#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/hermes-auto-continue-config.sh"
TRIGGER_SCRIPT="$ROOT/scripts/hermes-auto-continue-trigger.sh"
hermes_auto_continue_ensure_dirs
STAMP="$(date +%Y%m%d-%H%M%S)"
CHECKPOINT_FILE="$ROOT/.planning/checkpoints/${STAMP}.md"
MESSAGE="${*:-manual-checkpoint}"
cat > "$CHECKPOINT_FILE" <<EOF
# Auto Continue Checkpoint
- Time: $(date -Is)
- Repo: $ROOT
- Trigger: manual checkpoint
- Message: $MESSAGE
EOF
nohup bash "$TRIGGER_SCRIPT" checkpoint >> "$HERMES_AUTO_CONTINUE_LOG_FILE" 2>&1 &
echo "checkpoint_written=$CHECKPOINT_FILE"
echo "triggered=checkpoint"
