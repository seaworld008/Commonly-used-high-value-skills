# AI Workflow Agent Skills Sync

`skills/ai-workflow/` is the local AI workflow category for engineering-agent skills. It combines existing local workflow skills with a full import of [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills).

## Refresh From Upstream

```bash
python scripts/sync_addyosmani_agent_skills.py --apply --run-pipeline
```

The sync script:

- clones `addyosmani/agent-skills` from `main`
- imports every upstream `skills/*/SKILL.md` into `skills/ai-workflow/`
- copies upstream shared `references/` into imported skills
- stores Claude commands, plugin metadata, personas, hooks, docs, and references under `skills/ai-workflow/using-agent-skills/upstream-bundle/`
- updates `docs/sources/addyosmani-agent-skills-2026-04.skills.json`
- moves existing local workflow skills from `task-understanding-decomposition` into `ai-workflow`

## Install Locally For Codex

After the repository pipeline has run, sync the curated skills into the local Codex skill root:

```bash
python scripts/sync_codex_skills.py --source-root skills --codex-root ~/.codex/skills
```

Or do the upstream refresh, repository pipeline, and local Codex sync in one command:

```bash
python scripts/sync_addyosmani_agent_skills.py --apply --run-pipeline --sync-codex-root ~/.codex/skills
```

For all upstream-backed skills across the whole repository, use:

```bash
python scripts/sync_all_upstream_skills.py --apply --run-pipeline
```

OpenClaw should continue to use the generated flat export:

```text
openclaw-skills/
```

## Upstream Bundle

The upstream project includes Claude Code slash commands, plugin metadata, specialist personas, hooks, and setup docs. These are preserved under:

```text
skills/ai-workflow/using-agent-skills/upstream-bundle/
```

Keep this bundle source-driven. Do not hand-edit those copied files; refresh with `scripts/sync_addyosmani_agent_skills.py --apply`.
