## Hermes + graphify + GSD workflow

- GSD local runtime is expected under `./.codex/` for this repo.
- Graphify outputs live in `graphify-out/`.
- Before answering architecture questions or planning large refactors, read `graphify-out/GRAPH_REPORT.md` first.
- After code changes, prefer `./scripts/graphify-sync.sh smart` to keep the code graph fresh.
- If docs/media changes should affect semantic understanding, run a fuller graph refresh manually when needed.
- Treat `.planning/` and `graphify-out/` as local workflow artifacts unless the user explicitly wants them committed.
- If `scripts/ai-workflow.sh` exists, use it as the repo entrypoint for doctor/context/sync operations.
