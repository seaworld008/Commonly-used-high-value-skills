---
name: supabase-postgres-best-practices
description: 'Postgres performance optimization and best practices from Supabase. Use this skill when writing, reviewing, or optimizing Postgres queries, schema designs, or database configurations.'
version: "1.0.0"
author: "seaworld008"
source: "github:supabase/agent-skills"
source_url: "https://skills.sh/supabase/agent-skills/supabase-postgres-best-practices"
license: MIT
tags: '["best", "development", "postgres", "supabase"]'
created_at: "2026-05-05"
updated_at: "2026-05-05"
quality: 3
complexity: "intermediate"
metadata:
  author: supabase
  version: "1.1.1"
  organization: Supabase
  date: January 2026
  abstract: Comprehensive Postgres performance optimization guide for developers using Supabase and Postgres. Contains performance rules across 8 categories, prioritized by impact from critical (query performance, connection management) to incremental (advanced features). Each rule includes detailed explanations, incorrect vs. correct SQL examples, query plan analysis, and specific performance metrics to guide automated optimization and code generation.
---

# Supabase Postgres Best Practices

Comprehensive performance optimization guide for Postgres, maintained by Supabase. Contains rules across 8 categories, prioritized by impact to guide automated query optimization and schema design.

## When to Apply

Reference these guidelines when:
- Writing SQL queries or designing schemas
- Implementing indexes or query optimization
- Reviewing database performance issues
- Configuring connection pooling or scaling
- Optimizing for Postgres-specific features
- Working with Row-Level Security (RLS)

## Rule Categories by Priority

| Priority | Category | Impact | Prefix |
|----------|----------|--------|--------|
| 1 | Query Performance | CRITICAL | `query-` |
| 2 | Connection Management | CRITICAL | `conn-` |
| 3 | Security & RLS | CRITICAL | `security-` |
| 4 | Schema Design | HIGH | `schema-` |
| 5 | Concurrency & Locking | MEDIUM-HIGH | `lock-` |
| 6 | Data Access Patterns | MEDIUM | `data-` |
| 7 | Monitoring & Diagnostics | LOW-MEDIUM | `monitor-` |
| 8 | Advanced Features | LOW | `advanced-` |

## How to Use

Read individual rule files for detailed explanations and SQL examples:

```
references/query-missing-indexes.md
references/query-partial-indexes.md
references/_sections.md
```

Each rule file contains:
- Brief explanation of why it matters
- Incorrect SQL example with explanation
- Correct SQL example with explanation
- Optional EXPLAIN output or metrics
- Additional context and references
- Supabase-specific notes (when applicable)

## Review Workflow

Use this skill as a focused checklist before shipping database changes:

1. Start with the query shape: identify predicates, joins, sort keys, limits, and
   whether the query runs in a hot path.
2. Compare indexes against `references/query-missing-indexes.md`,
   `references/query-composite-indexes.md`, and
   `references/query-partial-indexes.md`.
3. Check RLS policies for both correctness and performance; prefer the
   `security-*` reference files when auth context appears in predicates.
4. Inspect connection behavior for serverless or high-concurrency apps using
   the `conn-*` references before changing pool settings.
5. For writes, review lock duration, transaction size, upsert behavior, and
   batch insert patterns before recommending schema or code changes.
6. Require `EXPLAIN (ANALYZE, BUFFERS)` evidence for risky performance claims
   whenever a database is available.
7. Summarize the expected impact, tradeoffs, and rollback plan alongside the SQL
   diff so reviewers can judge safety quickly.

## Common Patterns

```sql
-- Verify whether a suspected slow query uses the intended index.
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM public.orders
WHERE customer_id = $1
ORDER BY created_at DESC
LIMIT 25;
```

```sql
-- Prefer partial indexes for common filtered access patterns.
CREATE INDEX CONCURRENTLY IF NOT EXISTS orders_open_by_customer_created_at
ON public.orders (customer_id, created_at DESC)
WHERE status = 'open';
```

## References

- https://www.postgresql.org/docs/current/
- https://supabase.com/docs
- https://wiki.postgresql.org/wiki/Performance_Optimization
- https://supabase.com/docs/guides/database/overview
- https://supabase.com/docs/guides/auth/row-level-security
