# PostgreSQL 17/18 Features Guide

Reference for PostgreSQL 17 and 18 new features relevant to schema design.

## JSON / SQL:JSON New Features

PostgreSQL 17 adds full SQL:JSON standard compliance with new constructor and query functions.

### JSON_TABLE

Converts JSON data into a relational rowset — useful for normalizing JSON columns or importing from external sources.

```sql
SELECT *
FROM JSON_TABLE(
  '[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]',
  '$[*]'
  COLUMNS (
    id    INT    PATH '$.id',
    name  TEXT   PATH '$.name'
  )
) AS jt;
```

**Schema design implication:** Use `JSON_TABLE` in views or CTEs to expose JSONB columns as typed rows without materializing a separate table.

### JSON_EXISTS

Returns a boolean indicating whether a JSON path expression matches any value.

```sql
-- Find orders that have at least one item with quantity > 10
SELECT order_id
FROM orders
WHERE JSON_EXISTS(items, '$[*] ? (@.quantity > 10)');
```

### JSON_VALUE / JSON_QUERY

```sql
-- JSON_VALUE: extract a scalar
SELECT JSON_VALUE(payload, '$.user.email' RETURNING TEXT) AS email
FROM events;

-- JSON_QUERY: extract an object or array (returns JSON)
SELECT JSON_QUERY(payload, '$.user' WITH WRAPPER) AS user_json
FROM events;
```

**Design rules:**
- Prefer typed extraction (`RETURNING INT`, `RETURNING TEXT`) over casting after extraction.
- Use `JSON_EXISTS` in partial index predicates instead of `->>` comparisons for readability.
- Add a GIN index on frequently queried JSONB columns: `CREATE INDEX ON t USING gin(payload);`

---

## Partitioning Improvements

### SPLIT PARTITION

PostgreSQL 17 supports `ALTER TABLE ... SPLIT PARTITION` to divide an existing partition into two without full table recreation.

```sql
-- Original: orders_2024 covers 2024-01-01 to 2024-12-31
ALTER TABLE orders
  SPLIT PARTITION orders_2024
  INTO (
    PARTITION orders_2024_h1 FOR VALUES FROM ('2024-01-01') TO ('2024-07-01'),
    PARTITION orders_2024_h2 FOR VALUES FROM ('2024-07-01') TO ('2025-01-01')
  );
```

**When to use:** Existing partitions have grown beyond target size (typically > 10GB) or query patterns have changed to favour smaller date ranges.

### MERGE PARTITION

```sql
-- Merge two under-utilized partitions into one
ALTER TABLE orders
  MERGE PARTITIONS (orders_2020, orders_2021)
  INTO PARTITION orders_2020_2021
    FOR VALUES FROM ('2020-01-01') TO ('2022-01-01');
```

**Design rules:**
- Target partition size: 1–10 GB for optimal parallel scan performance.
- Use SPLIT for rapidly-growing partitions before they exceed the target.
- Use MERGE for archive partitions with low query frequency.
- Both operations are online (no full table lock) in PostgreSQL 17.

---

## Logical Replication Improvements

### Failover Control

PostgreSQL 17 adds `failover` option to subscriptions, enabling automatic replication slot failover when a primary fails.

```sql
CREATE SUBSCRIPTION sub_name
  CONNECTION 'host=primary dbname=app user=replicator'
  PUBLICATION pub_name
  WITH (failover = true);
```

**Schema design implication:** Tables published via logical replication must have a replica identity. Set `REPLICA IDENTITY FULL` for tables without a primary key (rarely preferred — add a PK instead).

```sql
-- Preferred
ALTER TABLE event_log ADD COLUMN id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY;

-- Fallback for legacy tables
ALTER TABLE legacy_table REPLICA IDENTITY FULL;
```

### pg_createsubscriber

New utility `pg_createsubscriber` creates a logical replication subscriber from a physical standby, enabling zero-downtime migration from physical to logical replication.

**Migration pattern:**
1. Take a physical standby of the source cluster.
2. Run `pg_createsubscriber` on the standby to convert it to a logical subscriber.
3. Validate data consistency.
4. Promote the subscriber and switch application connections.

**Design rules:**
- All replicated tables must have a primary key (required for logical replication by default).
- Avoid `TRUNCATE` on published tables — use `DELETE` or partition detach/attach instead.
- Monitor `pg_replication_slots` for inactive slots; they block WAL recycling.

---

## PostgreSQL 18 Features (Released 2025-09-25)

### UUIDv7 Native Support

PostgreSQL 18 adds the built-in `uuidv7()` function that generates UUIDv7 values with embedded millisecond timestamps. UUIDv7 preserves global uniqueness while enabling B-tree-friendly chronological ordering.

```sql
-- Use as default for new primary keys
CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT uuidv7(),
  ...
);
```

**Design rules:**
- Prefer `uuidv7()` over `gen_random_uuid()` (UUIDv4) for new tables — eliminates random-write amplification on B-tree indexes.
- UUIDv7 is K-sortable: rows inserted close in time cluster on disk, improving range scans and vacuum efficiency.

### OLD/NEW in RETURNING Clause

INSERT, UPDATE, DELETE, and MERGE now support `OLD` and `NEW` references in `RETURNING`:

```sql
-- Verify data correctness during expand-contract migration backfill
UPDATE orders SET status_v2 = translate_status(status)
RETURNING OLD.status AS old_val, NEW.status_v2 AS new_val;
```

**Design rules:**
- Use during dual-write/backfill phases of expand-contract migrations to verify transformations without extra SELECT queries.
- Useful for audit logging: capture both before and after states in a single statement.

### Virtual Generated Columns (Default)

Generated columns now default to `VIRTUAL` (computed on read, not stored). Use `STORED` only when the computation is expensive and frequently read.

```sql
ALTER TABLE products ADD COLUMN display_price TEXT
  GENERATED ALWAYS AS (currency || ' ' || amount::text) VIRTUAL;
```

### B-tree Skip Scan

B-tree indexes now support skip scan lookups, allowing efficient queries on non-leading columns of composite indexes without requiring a separate index.

### Asynchronous I/O Subsystem

PostgreSQL 18 introduces an async I/O subsystem that can improve sequential scan, bitmap heap scan, and vacuum performance by up to 3× on storage-bound workloads.
