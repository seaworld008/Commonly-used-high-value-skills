## AI workflow (Hermes + graphify + GSD)

This repository uses:
- Hermes for orchestration and persistent workflow context
- graphify for architecture recall and code graph refresh
- GSD for planning, phase management, and execution cadence

Recommended loop:

```bash
./scripts/ai-workflow.sh doctor
./scripts/ai-workflow.sh context
./scripts/ai-workflow.sh sync
```

Then:
1. read `graphify-out/GRAPH_REPORT.md`
2. read `.planning/STATE.md` and `.planning/ROADMAP.md`
3. progress the current GSD phase/plan
4. implement and test
5. run `./scripts/ai-workflow.sh sync` again
