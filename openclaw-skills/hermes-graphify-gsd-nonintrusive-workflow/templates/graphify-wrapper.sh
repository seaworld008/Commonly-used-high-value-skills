#!/usr/bin/env bash
set -euo pipefail

if [ -n "${GRAPHIFY_PY:-}" ] && [ -x "${GRAPHIFY_PY}" ]; then
  exec "${GRAPHIFY_PY}" -m graphify "$@"
fi

candidates=(
  "/root/.hermes/hermes-agent/venv/bin/python3"
  "${HOME}/.hermes/hermes-agent/venv/bin/python3"
  "$(command -v python3 2>/dev/null || true)"
  "$(command -v python 2>/dev/null || true)"
)

for py in "${candidates[@]}"; do
  [ -n "$py" ] || continue
  [ -x "$py" ] || continue
  if "$py" -c "import graphify" >/dev/null 2>&1; then
    exec "$py" -m graphify "$@"
  fi
done

echo "[graphify-wrapper] ERROR: no Python interpreter with graphify installed was found." >&2
exit 1
