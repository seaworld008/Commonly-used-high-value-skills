# First-install policy for repo integration

This repo integration skill assumes:
- Hermes is already installed
- network access is available for first-time bootstrap

Rules:
- do not auto-install Hermes
- if `hermes` is missing, stop and ask the user to install Hermes first
- before editing repo workflow files, automatically install or upgrade latest graphify and GSD globally

Recommended commands:

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

After the global toolchain is ready, continue with repo-local integration such as `graphify-sync.sh`, `ai-workflow.sh`, AGENTS.md, and README updates.

If `graphify --help` still warns after `--platform hermes`, do not assume Hermes install failed immediately. First check whether other installed platform targets (for example Claude) still have an older `.graphify_version`, then update those targets too.
