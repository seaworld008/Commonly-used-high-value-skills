#!/usr/bin/env bash
set -euo pipefail

TARGET_RUNTIME="${GSD_RUNTIME:-codex}"

if ! command -v hermes >/dev/null 2>&1; then
  echo "[bootstrap] Hermes is required but not installed." >&2
  echo "[bootstrap] Please install Hermes first. This bootstrap does not auto-install Hermes." >&2
  exit 1
fi

pick_python() {
  local candidates=(
    "${PYTHON_BIN:-}"
    "$HOME/.hermes/hermes-agent/venv/bin/python3"
    "$(command -v python3 2>/dev/null || true)"
    "$(command -v python 2>/dev/null || true)"
  )
  for py in "${candidates[@]}"; do
    [ -n "$py" ] || continue
    [ -x "$py" ] || continue
    if "$py" -m pip --version >/dev/null 2>&1; then
      echo "$py"
      return 0
    fi
    if "$py" -m ensurepip --upgrade >/dev/null 2>&1 && "$py" -m pip --version >/dev/null 2>&1; then
      echo "$py"
      return 0
    fi
  done
  return 1
}

PY_BIN="$(pick_python || true)"
[ -n "$PY_BIN" ] || { echo "[bootstrap] No usable Python with pip was found" >&2; exit 1; }

if "$PY_BIN" -c 'import sys; print(int(sys.prefix != sys.base_prefix))' 2>/dev/null | grep -q '^1$'; then
  "$PY_BIN" -m pip install -U graphifyy
else
  "$PY_BIN" -m pip install --user -U graphifyy
fi

export PATH="$HOME/.local/bin:$PATH"
if command -v graphify >/dev/null 2>&1; then
  graphify install --platform hermes
else
  "$HOME/.local/bin/graphify" install --platform hermes
fi

npx -y get-shit-done-cc@latest --"$TARGET_RUNTIME" --global --sdk

echo "[bootstrap] Hermes prerequisite satisfied"
echo "[bootstrap] graphify installed/upgraded and configured for Hermes"
echo "[bootstrap] GSD installed/upgraded globally for runtime: $TARGET_RUNTIME"