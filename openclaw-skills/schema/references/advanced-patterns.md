# Advanced Schema Patterns

Reference for event sourcing, CQRS projections, pgvector/AI schema, and bitemporal design.

---

## Event Sourcing Schema

### Core Tables

```sql
-- Append-only event store
CREATE TABLE event_store (
  event_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  aggregate_id    UUID        NOT NULL,
  aggregate_type  TEXT        NOT NULL,
  event_type      TEXT        NOT NULL,
  event_version   INT         NOT NULL,
  payload         JSONB       NOT NULL,
  metadata        JSONB       NOT NULL DEFAULT '{}',
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (aggregate_id, event_version)
);

CREATE INDEX idx_event_store_aggregate ON event_store(aggregate_id, event_version);
CREATE INDEX idx_event_store_type_time ON event_store(aggregate_type, occurred_at);

-- Snapshot table for aggregate state cache
CREATE TABLE aggregate_snapshots (
  aggregate_id    UUID        PRIMARY KEY,
  aggregate_type  TEXT        NOT NULL,
  snapshot_data   JSONB       NOT NULL,
  last_event_id   UUID        NOT NULL REFERENCES event_store(event_id),
  last_version    INT         NOT NULL,
  taken_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Design Rules

1. `event_store` is **append-only** — never UPDATE or DELETE rows.
2. Use `(aggregate_id, event_version)` unique constraint to detect optimistic concurrency conflicts.
3. Rebuild projections from `event_store` on demand; snapshots are a performance optimization, not the source of truth.
4. Partition `event_store` by `occurred_at` for long-running systems (> 1M events/month).

---

## CQRS Projection Tables

Projections are read-optimized materialized views of aggregate state, updated by event handlers.

```sql
-- Order summary projection (read model)
CREATE TABLE order_summary_projection (
  order_id        UUID        PRIMARY KEY,
  tenant_id       UUID        NOT NULL,
  customer_id     UUID        NOT NULL,
  status          TEXT        NOT NULL,
  total_amount    NUMERIC(12,2) NOT NULL,
  item_count      INT         NOT NULL DEFAULT 0,
  created_at      TIMESTAMPTZ NOT NULL,
  updated_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_order_summary_tenant_status ON order_summary_projection(tenant_id, status, created_at DESC);

-- Projection checkpoint tracker
CREATE TABLE projection_checkpoints (
  projection_name TEXT        PRIMARY KEY,
  last_event_id   UUID,
  last_position   BIGINT      NOT NULL DEFAULT 0,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Design rules:**
- Projections can be dropped and rebuilt from `event_store` at any time — they are dispensable.
- Use `projection_checkpoints` to track replay progress and support resumable rebuilds.
- Keep projections in a separate schema (`read_models`) to make the CQRS boundary explicit.

---

## pgvector / AI Schema Extensions

### Document Embeddings Table

```sql
-- Requires: CREATE EXTENSION vector;
CREATE TABLE document_embeddings (
  id              BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source_id       UUID        NOT NULL,
  source_type     TEXT        NOT NULL,  -- 'article', 'product', 'support_ticket'
  chunk_index     INT         NOT NULL DEFAULT 0,
  content         TEXT        NOT NULL,
  embedding       vector(1536),          -- OpenAI text-embedding-3-small dimension
  model_version   TEXT        NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  metadata        JSONB       NOT NULL DEFAULT '{}'
);

-- IVFFlat index (faster build, good for static datasets)
CREATE INDEX idx_embeddings_ivfflat
  ON document_embeddings
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- HNSW index (slower build, better recall, good for dynamic datasets)
-- CREATE INDEX idx_embeddings_hnsw
--   ON document_embeddings
--   USING hnsw (embedding vector_cosine_ops)
--   WITH (m = 16, ef_construction = 64);
```

### IVFFlat vs HNSW Comparison

| Dimension | IVFFlat | HNSW |
|-----------|---------|------|
| Build speed | Fast (minutes) | Slow (hours for large datasets) |
| Search recall | ~95% at nprobe=10 | ~99% at ef=64 |
| Memory usage | Low | High (graph stored in RAM) |
| Dynamic inserts | Requires periodic rebuild | Fully dynamic |
| Recommended for | Batch-loaded, static datasets | Live-updated, recall-critical datasets |
| Key parameter | `lists = sqrt(n_rows)` | `m = 16`, `ef_construction = 64` |

### Hybrid Search SQL

```sql
-- Combine semantic similarity with keyword filter
SELECT
  d.id,
  d.source_id,
  d.content,
  1 - (d.embedding <=> $1::vector) AS similarity
FROM document_embeddings d
WHERE
  d.source_type = 'article'
  AND d.metadata @> '{"language": "en"}'::jsonb
ORDER BY d.embedding <=> $1::vector
LIMIT 20;
```

### Design Rules

1. Store the `model_version` so embeddings can be invalidated and regenerated when the model changes.
2. Use `chunk_index` to track position within a document when chunking long text.
3. Choose `vector_cosine_ops` for normalized embeddings (OpenAI, Cohere); use `vector_l2_ops` for unnormalized embeddings.
4. Add a GIN index on `metadata` if filtering by metadata fields is frequent.
5. On pgvector 0.8+, enable iterative index scans (`SET hnsw.iterative_scan = relaxed_order`) for filtered queries — prevents under-fetching when prefilters are highly selective. Use `strict_order` when exact distance ordering is required; `relaxed_order` for better performance with approximate ordering.

---

## Bitemporal Design

Bitemporal tables track two time axes independently:
- **Valid time** (`valid_from` / `valid_to`): when the fact was true in the real world.
- **Transaction time** (`recorded_at` / `invalidated_at`): when the database recorded the fact.

### Employee Contracts (Bitemporal)

```sql
CREATE TABLE employee_contracts (
  id                BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  employee_id       UUID        NOT NULL,
  role              TEXT        NOT NULL,
  salary            NUMERIC(10,2) NOT NULL,
  -- Valid time (business reality)
  valid_from        DATE        NOT NULL,
  valid_to          DATE        NOT NULL DEFAULT 'infinity',
  -- Transaction time (audit trail)
  recorded_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  invalidated_at    TIMESTAMPTZ NOT NULL DEFAULT 'infinity',
  recorded_by       UUID        NOT NULL,
  CONSTRAINT no_valid_overlap EXCLUDE USING gist (
    employee_id WITH =,
    daterange(valid_from, valid_to, '[)') WITH &&
  ) WHERE (invalidated_at = 'infinity')
);

CREATE INDEX idx_contracts_employee_valid
  ON employee_contracts(employee_id, valid_from, valid_to)
  WHERE invalidated_at = 'infinity';
```

### Bitemporal vs SCD Type 2

| Dimension | Bitemporal | SCD Type 2 |
|-----------|-----------|------------|
| Time axes | Valid time + Transaction time | Valid time only |
| Retroactive corrections | Supported (invalidate old row, insert corrected row with original valid_from) | Not natively supported |
| Audit trail | Complete (who recorded what, when) | Partial (only current chain) |
| Query complexity | Higher | Lower |
| Use when | Compliance, audit, corrections to historical data | Analytics, slowly-changing dimensions |

### Design Gate

Apply bitemporal design when any of the following are true:
- The system must support **retroactive corrections** to historical records.
- Regulatory or audit requirements demand knowing what the database believed at a given time.
- Temporal queries like "what did the system show on 2023-06-01 for events in Q1 2023?" are required.
