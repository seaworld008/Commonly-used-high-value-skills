# ORM Migrations, Multi-Tenancy, and PostgreSQL RLS Patterns

Reference patterns preserved from `database-schema-designer` for Drizzle, Prisma, Alembic, multi-tenant Row-Level Security (RLS), and seed/ERD workflows.

## Cross-Cutting Schema Conventions

- **Primary keys**: Use immutable UUIDv7 or CUID2 identifiers rather than sequential integers or mutable emails/slugs.
- **Multi-tenancy**: Scope tenant-owned tables with `organization_id` and index `(organization_id, status)` / `(organization_id, created_at DESC)`.
- **Soft deletes**: Use `deleted_at TIMESTAMPTZ` with partial indexes (`WHERE deleted_at IS NULL`) so active queries stay fast.
- **Optimistic locking**: Include `version INTEGER NOT NULL DEFAULT 1` on concurrently edited entities.
- **Audit trail**: Record `created_by`, `updated_by`, `created_at`, `updated_at`, plus append-only `audit_logs` (`before`/`after` JSONB).

## Drizzle ORM (PostgreSQL + TypeScript)

```typescript
import { pgTable, text, timestamp, integer, varchar, real, pgEnum, index } from 'drizzle-orm/pg-core'
import { createId } from '@paralleldrive/cuid2'

export const taskStatusEnum = pgEnum('task_status', ['todo', 'in_progress', 'in_review', 'done', 'cancelled'])

export const tasks = pgTable('tasks', {
  id: text('id').primaryKey().$defaultFn(() => createId()),
  projectId: text('project_id').notNull().references(() => projects.id),
  title: varchar('title', { length: 500 }).notNull(),
  status: taskStatusEnum('status').notNull().default('todo'),
  position: real('position').notNull().default(0),
  version: integer('version').notNull().default(1),
  createdById: text('created_by_id').notNull().references(() => users.id),
  updatedById: text('updated_by_id').notNull().references(() => users.id),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
  deletedAt: timestamp('deleted_at', { withTimezone: true }),
}, (table) => ({
  projectStatusIdx: index('tasks_project_status_idx').on(table.projectId, table.status),
}))

export type Task = typeof tasks.$inferSelect
export type NewTask = typeof tasks.$inferInsert
```

## Prisma Multi-Tenant & Polymorphic Model Pattern

```prisma
model AuditLog {
  id             String   @id @default(cuid())
  organizationId String   @map("organization_id")
  userId         String?  @map("user_id")
  action         String
  entityType     String   @map("entity_type")
  entityId       String   @map("entity_id")
  before         Json?
  after          Json?
  createdAt      DateTime @default(now()) @map("created_at")

  @@index([organizationId, createdAt(sort: Desc)])
  @@index([entityType, entityId])
  @@map("audit_logs")
}
```

- For polymorphic attachments (`entity_type` + `entity_id`), index `(entity_type, entity_id)` and enforce referential validation in the application or trigger layer.
- For Prisma partial indexes (`where: { deletedAt: null }`), confirm the target database and Prisma preview/version support before generating migrations.

## Alembic Partial Index Example (Python / SQLAlchemy)

```python
op.create_index(
    "tasks_due_date_active_idx",
    "tasks",
    ["due_date"],
    postgresql_where=sa.text("deleted_at IS NULL"),
)
```

## PostgreSQL Row-Level Security (RLS)

- Use a non-owner application role **without** `BYPASSRLS`; grant only required columns (exclude ownership keys such as `project_id` and `created_by_id` from `UPDATE`).
- Set the authenticated actor per transaction (`SELECT set_config('app.current_user_id', $1, true);`) so pooled connections never leak identity.
- Replace overlapping permissive `FOR ALL` policies in the same transaction as new scoped `SELECT` / `INSERT` / `UPDATE` / `DELETE` policies.

```sql
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY tasks_read ON tasks FOR SELECT TO app_user
  USING (deleted_at IS NULL AND project_id IN (SELECT id FROM projects));

CREATE POLICY tasks_insert ON tasks FOR INSERT TO app_user
  WITH CHECK (
    deleted_at IS NULL
    AND project_id IN (SELECT id FROM projects)
    AND created_by_id = current_setting('app.current_user_id', true)
  );
```

- Always verify RLS policies with at least two tenants and an unprivileged role (`app_user`): confirm foreign-tenant and soft-deleted rows are invisible and cross-tenant writes fail.

## ERD Tooling & Common Pitfalls

- Generate Mermaid ERDs from Prisma via `npx prisma-erd-generator` or `npx @dbml/cli prisma2dbml -i schema.prisma | npx dbml-to-mermaid`.
- Avoid unindexed `deleted_at IS NULL` filters, missing composite tenant indexes, non-nullable additions without defaults/backfills, and unverified RLS tested only as superuser.
