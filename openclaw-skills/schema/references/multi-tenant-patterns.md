# Multi-Tenant Database Patterns

Reference for designing multi-tenant database schemas.

## Architecture Pattern Comparison

| Pattern | Description | Isolation | Cost | Best for |
|---------|-------------|-----------|------|----------|
| **Database per Tenant** | Each tenant has a dedicated database | Highest — full schema, data, and connection isolation | Highest — one DB per tenant | Regulated industries (HIPAA, SOC 2), large enterprise tenants |
| **Schema per Tenant** | Single cluster, one schema per tenant (PostgreSQL `search_path`) | High — separate DDL, no data sharing | Medium — shared cluster, separate objects | Mid-market SaaS, 10–500 tenants, custom schema per tenant needed |
| **Shared Schema + RLS** | All tenants in the same tables, isolated by Row Level Security | Medium — policy-enforced, not DDL-enforced | Lowest — fully shared infra | Consumer SaaS, thousands of small tenants, uniform schema |

---

## Row Level Security (RLS) Implementation

### Policy Setup

```sql
-- 1. Add tenant_id to every shared table
ALTER TABLE orders ADD COLUMN tenant_id UUID NOT NULL;

-- 2. Enable RLS
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders FORCE ROW LEVEL SECURITY;  -- applies to table owner too

-- 3. Create isolation policy
CREATE POLICY tenant_isolation ON orders
  USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- 4. Set tenant context at connection time (application layer)
-- SET app.current_tenant_id = '<tenant-uuid>';
-- Or via: SELECT set_config('app.current_tenant_id', $1, true);
```

### RLS Checklist

- [ ] `ENABLE ROW LEVEL SECURITY` on every multi-tenant table
- [ ] `FORCE ROW LEVEL SECURITY` to prevent table-owner bypass
- [ ] Index on `tenant_id` column for every table (`CREATE INDEX CONCURRENTLY`)
- [ ] Application layer always sets `app.current_tenant_id` before any query

### Partial Index for Performance

```sql
-- Prefix all indexes with tenant_id to avoid cross-tenant scan
CREATE INDEX idx_orders_tenant_status
  ON orders(tenant_id, status, created_at DESC);
```

---

## Schema Isolation Pattern (Schema per Tenant)

```sql
-- Create a schema for the tenant
CREATE SCHEMA tenant_abc123;

-- Set search path for the session
SET search_path TO tenant_abc123, public;

-- Provision tenant schema using a template schema
-- (copy DDL from a template, or use a migration tool per-schema)
CREATE TABLE tenant_abc123.orders (LIKE public.orders_template INCLUDING ALL);
```

**When to choose schema isolation:**
- Tenants need different table structures or extensions.
- Data export / deletion per tenant must be clean (`DROP SCHEMA tenant_abc123 CASCADE`).
- Regulatory requirement for logical data separation without full database cost.

---

## Tenant Column Pattern

**Design rules for shared-schema multi-tenancy:**

1. `tenant_id` must be the **first column** in every composite index to allow index-only scans per tenant.
2. Use `UUID` for `tenant_id` to avoid enumeration attacks and allow distributed ID generation.
3. Foreign keys between multi-tenant tables must include `tenant_id`: `FOREIGN KEY (tenant_id, order_id) REFERENCES orders(tenant_id, id)`.
4. Never expose raw `tenant_id` values in API responses — map to opaque identifiers at the application boundary.

```sql
-- Composite FK that enforces same-tenant integrity
CREATE TABLE order_items (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id  UUID NOT NULL,
  order_id   UUID NOT NULL,
  CONSTRAINT fk_order FOREIGN KEY (tenant_id, order_id)
    REFERENCES orders(tenant_id, id) ON DELETE CASCADE
);

CREATE INDEX idx_order_items_tenant_order ON order_items(tenant_id, order_id);
```

---

## Design Gate

Before shipping a multi-tenant schema, verify:

- Every table has `tenant_id` and RLS (or resides in a dedicated schema/DB).
- No query joins across tenants without an explicit `tenant_id` filter.
- `tenant_id` is the leading column in all composite indexes.
- Tenant provisioning and deprovisioning are tested (create + delete + data verification).
- Connection pooling (e.g., PgBouncer) is configured to reset `app.current_tenant_id` between sessions in transaction-mode pooling.
