#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/hermes-auto-continue-config.sh"
hermes_auto_continue_ensure_dirs
writer_status="$(hermes_auto_continue_writer_surface_status)"
writer_recommended="$(printf '%s\n' "$writer_status" | awk -F= '$1=="writer_recommended"{print $2}')"
execution_surface="$(printf '%s\n' "$writer_status" | awk -F= '$1=="execution_surface"{print $2}')"
TRIGGER_SCRIPT="$ROOT/scripts/hermes-auto-continue-trigger.sh"
CRON_TAG="# HERMES_AUTO_CONTINUE_REPO"
CRON_LINE="*/15 * * * * cd $ROOT && /usr/bin/env bash $TRIGGER_SCRIPT cron >> $HERMES_AUTO_CONTINUE_LOG_FILE 2>&1 $CRON_TAG"
current_crontab="$(crontab -l 2>/dev/null || true)"
current_crontab="$(printf '%s\n' "$current_crontab" | grep -v "$CRON_TAG" || true)"
mode="${1:-install}"
case "$mode" in
  install)
    if [ "$writer_recommended" != "yes" ] && [ "${HERMES_AUTO_CONTINUE_ALLOW_INCOMPLETE_ROOT:-0}" != "1" ]; then
      echo "refused: writer_recommended=no execution_surface=$execution_surface" >&2
      exit 2
    fi
    {
      printf '%s\n' "$current_crontab"
      printf '%s\n' "$CRON_LINE"
    } | sed '/^$/N;/^\n$/D' | crontab -
    echo "installed"
    ;;
  uninstall)
    printf '%s\n' "$current_crontab" | sed '/^$/N;/^\n$/D' | crontab -
    echo "uninstalled"
    ;;
  *)
    echo "Usage: $0 {install|uninstall}" >&2
    exit 1
    ;;
esac
