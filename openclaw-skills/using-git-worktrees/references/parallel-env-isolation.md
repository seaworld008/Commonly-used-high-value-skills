# Parallel Worktree Port, Compose, Database & Monorepo Isolation

Reference patterns preserved from `git-worktree-manager` for running parallel services or multi-agent sessions across Git worktrees without port, database, or dependency collisions.

## Port Allocation Convention

Assign distinct local ports before starting dev servers in parallel worktrees:

```text
Main worktree:     localhost:3000 (dev), :5432 (db), :6379 (redis)
Worktree 1:        localhost:3010 (dev), :5442 (db), :6389 (redis)
Worktree 2:        localhost:3020 (dev), :5452 (db), :6399 (redis)
```

## Docker Compose Per-Worktree Override

Use a worktree-local override file instead of editing tracked `docker-compose.yml`:

```yaml
# docker-compose.worktree.yml (untracked / gitignored)
services:
  app:
    ports:
      - "3010:3000"
  db:
    ports:
      - "5442:5432"
  redis:
    ports:
      - "6389:6379"
```

Run with: `docker compose -f docker-compose.yml -f docker-compose.worktree.yml up`

## Database Isolation Options

- **Separate DB per worktree**: `createdb myapp_feature_auth` and point `DATABASE_URL` in `.env.local`.
- **SQLite**: file-based per-worktree path gives automatic isolation.
- **Migrations**: never run schema migrations from two worktrees against a shared database instance.

## Monorepo Sparse Checkout in a Worktree

```bash
git worktree add --no-checkout ../project-packages-only
cd ../project-packages-only
git sparse-checkout init --cone
git sparse-checkout set packages/shared packages/api
git checkout feature/api-refactor
```

## Parallel Session Pitfalls & Cleanup

- Never create worktrees inside the tracked source tree unless `.gitignore` / `git check-ignore` covers the directory.
- Keep separate IDE/terminal windows per worktree; commit or cleanly stage WIP before switching.
- Prune stale worktrees with `git worktree remove <path>` and `git worktree prune`.
