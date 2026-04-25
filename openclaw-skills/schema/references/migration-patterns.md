# Migration Patterns

Purpose: Use this file when planning safe schema changes, rollback, or framework-specific migration commands.

Contents:
1. Safe change decision tree
2. Expand-contract pattern
3. Zero-downtime index creation
4. Framework commands
5. Pre-migration checklist

## Safe Change Decision Tree

```text
Schema change needed
├── Adding new?
│   ├── New table -> CREATE TABLE (safe)
│   ├── New nullable column -> ADD COLUMN (safe)
│   ├── New NOT NULL column -> Expand-contract
│   └── New index -> Online / concurrent creation
├── Modifying existing?
│   ├── Rename column -> Expand-contract
│   ├── Change type -> Verify conversion safety first
│   ├── Add constraint -> Validate existing data first
│   └── Change default -> Usually safe
└── Removing?
    ├── Drop column -> Backup first, then phased removal
    ├── Drop table -> Backup required, irreversible
    ├── Drop index -> Safe, but verify query impact
    └── Drop constraint -> Safe, but verify integrity risk
```

## Expand-Contract Pattern

| Phase | Goal | Required actions |
|------|------|------------------|
| Expand | Introduce the new structure safely | Add new column/table, keep it nullable, dual-write if needed |
| Migrate | Backfill and validate | Batch copy data, validate consistency, add `NOT NULL` only after backfill |
| Contract | Remove the old structure | Switch reads, remove sync path, drop old column only after verification |

## Zero-Downtime Index Creation

```sql
-- PostgreSQL
CREATE INDEX CONCURRENTLY idx_name ON table_name(column_name);

-- MySQL 8.0+
ALTER TABLE t
  ADD INDEX idx_name (col),
  ALGORITHM=INPLACE,
  LOCK=NONE;
```

## Framework Migration Commands

| Framework | Create | Run | Rollback |
|-----------|--------|-----|----------|
| Prisma | `prisma migrate dev --name [name]` | `prisma migrate deploy` | Manual |
| TypeORM | `typeorm migration:generate -n [Name]` | `typeorm migration:run` | `typeorm migration:revert` |
| Drizzle | `drizzle-kit generate:pg` | `drizzle-kit push:pg` | Manual |
| Knex | `knex migrate:make [name]` | `knex migrate:latest` | `knex migrate:rollback` |

## Pre-Migration Checklist

- Backup is available and verified
- Migration was tested on production-like data
- Rollback path was tested or explicitly marked backup-required
- Lock duration was estimated
- Disk space and index-build impact were checked
- Low-traffic window is selected if blocking work remains
- Post-migration monitoring is prepared

---

## Drizzle ORM Best Practices

```typescript
// drizzle.config.ts — recommended settings
import { defineConfig } from 'drizzle-kit';

export default defineConfig({
  schema: './src/db/schema.ts',
  out: './drizzle',
  dialect: 'postgresql',
  strict: true,     // fail on ambiguous schema changes (column drops, renames)
  verbose: true,    // print SQL statements before execution
  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
});
```

**Key rules:**
- Always use `strict: true` — prevents silent data-loss migrations.
- Use `verbose: true` in CI to surface generated SQL for review.
- Run `drizzle-kit check` in CI before `drizzle-kit migrate` to detect breaking changes.
- Store generated migration files in version control; never hand-edit them.

---

## Prisma 7 Migration Notes

Prisma 7 replaces the Rust-based query engine with a pure TypeScript implementation.

**Breaking changes from Prisma 6:**
- The `prisma-engines` binary is no longer included; remove it from Dockerfile `COPY` commands.
- `datasource.binaryTargets` is deprecated — remove from `schema.prisma`.
- Cold-start time improves significantly (no native binary load), but first-query memory increases slightly.

**Migration steps:**
```bash
npm install prisma@7 @prisma/client@7
npx prisma generate  # regenerates the TypeScript client
```

**Verify:**
- Remove `binaryTargets = ["native", "linux-musl"]` from `schema.prisma`.
- Remove `prisma-engines` from `.dockerignore` allowlist if present.
- Test connection pooling configuration — `connectionLimit` semantics unchanged.

---

## Shadow Tables Pattern

Shadow tables allow zero-downtime schema changes on high-traffic tables by building the new schema alongside the old one.

**6-step procedure:**

1. **Create** the shadow table with the new schema alongside the original.
   ```sql
   CREATE TABLE orders_v2 (LIKE orders INCLUDING ALL);
   ALTER TABLE orders_v2 ADD COLUMN currency TEXT NOT NULL DEFAULT 'USD';
   ```

2. **Backfill** existing rows from original to shadow in batches.
   ```sql
   INSERT INTO orders_v2
   SELECT *, 'USD' AS currency FROM orders
   WHERE id BETWEEN $batch_start AND $batch_end
   ON CONFLICT (id) DO NOTHING;
   ```

3. **Dual-write** — application writes to both tables simultaneously.

4. **Verify** row counts and checksums between tables.

5. **Cut over** — rename tables atomically.
   ```sql
   BEGIN;
   ALTER TABLE orders RENAME TO orders_old;
   ALTER TABLE orders_v2 RENAME TO orders;
   COMMIT;
   ```

6. **Drop** the old table after a monitoring period (typically 1–7 days).
   ```sql
   DROP TABLE orders_old;
   ```
