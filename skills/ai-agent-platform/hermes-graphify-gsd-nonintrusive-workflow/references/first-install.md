# First-install policy

This workflow is for machines where Hermes is already installed and the session has network access.

Rules:
- Hermes is a hard prerequisite
- do not auto-install Hermes from this skill
- if `hermes` is missing, stop and ask the user to install Hermes first
- if Hermes exists, the skill should automatically install or upgrade the latest graphify and GSD, then configure them globally

Recommended bootstrap sequence:

```bash
command -v hermes
hermes --version
PY_BIN="${PYTHON_BIN:-$HOME/.hermes/hermes-agent/venv/bin/python3}"
[ -x "$PY_BIN" ] || PY_BIN="$(command -v python3)"
if "$PY_BIN" -c 'import sys; print(int(sys.prefix != sys.base_prefix))' 2>/dev/null | grep -q '^1$'; then
  "$PY_BIN" -m pip install -U graphifyy
else
  "$PY_BIN" -m pip install --user -U graphifyy
fi
~/.local/bin/graphify install --platform hermes || graphify install --platform hermes
npx -y get-shit-done-cc@latest --codex --global --sdk
```

Why this policy exists:
- Hermes is the orchestrator and should remain a user-controlled installation decision
- graphify and GSD are workflow dependencies that can be safely installed or upgraded automatically after Hermes is present
- using upstream latest entrypoints reduces drift between local docs and real installation behavior
- graphify version warnings may come from any installed platform target, so post-install verification must consider more than just Hermes
