# Integration checklist

Use this checklist when applying repo-level integration.

1. Global prerequisite layer
- Hermes already installed
- if Hermes is missing, stop and request manual install
- graphify installed or upgraded globally via a venv-aware pip flow, for example:
  ```bash
  PY_BIN="${PYTHON_BIN:-$HOME/.hermes/hermes-agent/venv/bin/python3}"
  [ -x "$PY_BIN" ] || PY_BIN="$(command -v python3)"
  if "$PY_BIN" -c 'import sys; print(int(sys.prefix != sys.base_prefix))' 2>/dev/null | grep -q '^1$'; then
    "$PY_BIN" -m pip install -U graphifyy
  else
    "$PY_BIN" -m pip install --user -U graphifyy
  fi
  ```
- graphify integrated for Hermes via `~/.local/bin/graphify install --platform hermes || graphify install --platform hermes`
- GSD installed or upgraded globally via `npx -y get-shit-done-cc@latest --codex --global --sdk`

2. Repo audit
- AGENTS.md present or planned
- README.md present
- scripts/ directory present or creatable
- `.planning/` present or bootstrappable via `gsd-graphify-brownfield-bootstrap`
- `.codex/` present or intentionally absent
- `graphify-out/` present or buildable

3. Script layer
- add or verify `scripts/graphify-sync.sh`
- add optional `scripts/ai-workflow.sh`
- mark scripts executable

4. Documentation layer
- add workflow section to AGENTS.md
- add workflow section to README.md
- add `.planning/` and `graphify-out/` to `.gitignore`

5. Verification layer
- run `./scripts/graphify-sync.sh status`
- run `./scripts/graphify-sync.sh smart`
- run `./scripts/ai-workflow.sh doctor` if present
- verify graphify report exists
- verify planning files exist if expected
- if testing in a git worktree, do not require `graphify hook install` to succeed there; verify hooks from the primary checkout instead

6. Brownfield caution
- do not force a full re-bootstrap if the repo already has working planning/graph workflow
- extend the existing workflow instead of replacing it blindly
- if `.planning/` is truly missing and needed, use `gsd-graphify-brownfield-bootstrap` rather than silently inventing partial planning state here
