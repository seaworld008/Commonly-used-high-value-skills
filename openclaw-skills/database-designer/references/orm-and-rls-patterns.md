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

- Use a non-owner application role **without** `BYPASSRLS`; grant only required privileges and exclude ownership keys (`project_id`, `created_by_id`) and `deleted_at` from direct `UPDATE`. Never grant `app_user` write access to `organization_members`.
- Enable RLS on **both** parent (`projects`, `organization_members`) and child (`tasks`) tables so subqueries like `project_id IN (SELECT id FROM projects)` cannot leak cross-tenant rows. Keep explicit `organization_members` membership checks in child policies as defense-in-depth.
- Set the authenticated actor per transaction so pooled connections never leak identity.
- Replace overlapping permissive `FOR ALL` policies in the same transaction as new scoped `SELECT` / `INSERT` / `UPDATE` / `DELETE` policies. If the table owner also executes application queries, add `ALTER TABLE ... FORCE ROW LEVEL SECURITY`.
- Because PostgreSQL also checks `FOR SELECT` policies against the new row on any `UPDATE ... WHERE ...`, a `FOR SELECT` rule with `deleted_at IS NULL` rejects direct `UPDATE ... SET deleted_at = NOW()`. Keep `deleted_at IS NULL` in `tasks_read` so soft-deleted rows stay invisible, and perform soft deletes through a `SECURITY DEFINER` function with `SET search_path = pg_catalog, public` and explicit membership/role checks.

```sql
-- Multi-tenant schema & composite indexes (executed by schema_owner)
CREATE TABLE organizations (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL
);

CREATE TABLE organization_members (
  id TEXT PRIMARY KEY,
  organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
  joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (organization_id, user_id)
);
CREATE INDEX org_members_user_idx ON organization_members (user_id, organization_id);

CREATE TABLE projects (
  id TEXT PRIMARY KEY,
  organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  owner_id TEXT NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  deleted_at TIMESTAMPTZ
);
CREATE INDEX projects_org_status_idx ON projects (organization_id, status) WHERE deleted_at IS NULL;

CREATE TABLE tasks (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title VARCHAR(500) NOT NULL,
  status TEXT NOT NULL DEFAULT 'todo',
  position REAL NOT NULL DEFAULT 0,
  version INTEGER NOT NULL DEFAULT 1,
  created_by_id TEXT NOT NULL REFERENCES users(id),
  updated_by_id TEXT NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);
CREATE INDEX tasks_project_status_idx ON tasks (project_id, status) WHERE deleted_at IS NULL;

-- Non-owner application role without BYPASSRLS
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
    CREATE ROLE app_user NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
  END IF;
END
$$;

GRANT SELECT ON organizations, organization_members, projects TO app_user;
GRANT SELECT, INSERT, DELETE ON tasks TO app_user;
GRANT UPDATE (title, status, position, version, updated_by_id, updated_at) ON tasks TO app_user;

-- Enable RLS on membership, parent, and child tables together
ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY org_members_self_read ON organization_members FOR SELECT TO app_user
  USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY projects_member_read ON projects FOR SELECT TO app_user
  USING (
    deleted_at IS NULL
    AND EXISTS (
      SELECT 1 FROM organization_members om
      WHERE om.organization_id = projects.organization_id
        AND om.user_id = current_setting('app.current_user_id', true)
    )
  );

CREATE POLICY tasks_read ON tasks FOR SELECT TO app_user
  USING (
    deleted_at IS NULL
    AND project_id IN (SELECT id FROM projects)
    AND EXISTS (
      SELECT 1
      FROM projects p
      JOIN organization_members om ON om.organization_id = p.organization_id
      WHERE p.id = tasks.project_id
        AND p.deleted_at IS NULL
        AND om.user_id = current_setting('app.current_user_id', true)
    )
  );

CREATE POLICY tasks_insert ON tasks FOR INSERT TO app_user
  WITH CHECK (
    deleted_at IS NULL
    AND created_by_id = current_setting('app.current_user_id', true)
    AND EXISTS (
      SELECT 1
      FROM projects p
      JOIN organization_members om ON om.organization_id = p.organization_id
      WHERE p.id = tasks.project_id
        AND p.deleted_at IS NULL
        AND om.user_id = current_setting('app.current_user_id', true)
        AND om.role IN ('owner', 'admin', 'member')
    )
  );

CREATE POLICY tasks_update ON tasks FOR UPDATE TO app_user
  USING (
    deleted_at IS NULL
    AND EXISTS (
      SELECT 1
      FROM projects p
      JOIN organization_members om ON om.organization_id = p.organization_id
      WHERE p.id = tasks.project_id
        AND p.deleted_at IS NULL
        AND om.user_id = current_setting('app.current_user_id', true)
        AND om.role IN ('owner', 'admin', 'member')
    )
  )
  WITH CHECK (
    deleted_at IS NULL
    AND EXISTS (
      SELECT 1
      FROM projects p
      JOIN organization_members om ON om.organization_id = p.organization_id
      WHERE p.id = tasks.project_id
        AND p.deleted_at IS NULL
        AND om.user_id = current_setting('app.current_user_id', true)
        AND om.role IN ('owner', 'admin', 'member')
    )
  );

CREATE POLICY tasks_delete ON tasks FOR DELETE TO app_user
  USING (
    deleted_at IS NULL
    AND project_id IN (SELECT id FROM projects)
    AND (
      (
        created_by_id = current_setting('app.current_user_id', true)
        AND EXISTS (
          SELECT 1
          FROM projects p
          JOIN organization_members om ON om.organization_id = p.organization_id
          WHERE p.id = tasks.project_id
            AND p.deleted_at IS NULL
            AND om.user_id = current_setting('app.current_user_id', true)
            AND om.role IN ('owner', 'admin', 'member')
        )
      )
      OR EXISTS (
        SELECT 1
        FROM projects p
        JOIN organization_members om ON om.organization_id = p.organization_id
        WHERE p.id = tasks.project_id
          AND p.deleted_at IS NULL
          AND om.user_id = current_setting('app.current_user_id', true)
          AND om.role IN ('owner', 'admin')
      )
    )
  );

-- Controlled soft-delete RPC (enforces membership and creator/admin check)
CREATE OR REPLACE FUNCTION soft_delete_task(p_task_id TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
  v_actor TEXT := current_setting('app.current_user_id', true);
BEGIN
  IF v_actor IS NULL OR v_actor = '' THEN
    RETURN FALSE;
  END IF;

  UPDATE tasks t
  SET deleted_at = NOW(),
      updated_by_id = v_actor,
      updated_at = NOW()
  FROM projects p
  JOIN organization_members om ON om.organization_id = p.organization_id
  WHERE t.id = p_task_id
    AND t.deleted_at IS NULL
    AND p.id = t.project_id
    AND p.deleted_at IS NULL
    AND om.user_id = v_actor
    AND (
      (t.created_by_id = v_actor AND om.role IN ('owner', 'admin', 'member'))
      OR om.role IN ('owner', 'admin')
    );

  RETURN FOUND;
END;
$$;

REVOKE ALL ON FUNCTION soft_delete_task(TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION soft_delete_task(TEXT) TO app_user;
```

Set the transaction-local identity before every application query:

```sql
SELECT set_config('app.current_user_id', $1, true);
```

- Always verify RLS policies with at least two tenants and an unprivileged non-owner role (`app_user`): confirm active-tenant reads/writes/soft-deletes succeed, foreign-tenant and soft-deleted rows are invisible, cross-tenant writes/ownership tampering fail, read-only `viewer` writes fail, and creator vs. same-organization admin deletion boundaries hold.

## ERD Tooling & Common Pitfalls

- Generate Mermaid ERDs from Prisma via `npx prisma-erd-generator` or `npx @dbml/cli prisma2dbml -i schema.prisma | npx dbml-to-mermaid`.
- Avoid unindexed `deleted_at IS NULL` filters, missing composite tenant indexes, non-nullable additions without defaults/backfills, and unverified RLS tested only as superuser.
