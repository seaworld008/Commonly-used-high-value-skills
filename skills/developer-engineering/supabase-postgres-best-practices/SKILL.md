---
name: supabase-postgres-best-practices
description: 'Use when writing or reviewing Postgres schemas, queries, indexes, RLS policies, connection settings, or migrations with Supabase guidance; applicable to Postgres on any hosting platform.'
zh_description: "用于编写或评审 Supabase/Postgres 的查询、Schema、索引、RLS、连接配置与迁移。"
version: "1.0.4"
author: "seaworld008"
source: "github:supabase/agent-skills"
source_url: "https://skills.sh/supabase/agent-skills/supabase-postgres-best-practices"
license: MIT
tags: '["best", "development", "postgres", "supabase"]'
created_at: "2026-05-05"
updated_at: "2026-09-06"
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

## References

- https://www.postgresql.org/docs/current/
- https://supabase.com/docs
- https://wiki.postgresql.org/wiki/Performance_Optimization
- https://supabase.com/docs/guides/database/overview
- https://supabase.com/docs/guides/auth/row-level-security
<!-- LOCAL-QUALITY-SUPPLEMENT:START -->
## Review Workflow

Select only the rule files that match the task. Start with correctness and
access control, then measure performance before proposing tuning changes.

1. Identify the database version, hosting constraints, workload shape, and
   whether the task changes data or only reviews SQL.
2. Read the relevant `query-`, `conn-`, `security-`, `schema-`, `lock-`,
   `data-`, or `monitor-` references; avoid loading the full rule set by default.
3. Preserve existing RLS and privilege boundaries. Treat disabling RLS,
   broadening grants, destructive DDL, and production writes as separate,
   explicitly authorized actions.
4. For performance claims, capture the query shape and an `EXPLAIN` or
   `EXPLAIN (ANALYZE, BUFFERS)` result in a safe environment. Do not infer an
   improvement from the presence of an index alone.
5. Verify migrations on a representative schema, including rollback or a
   forward-fix path, lock duration, and compatibility with concurrent traffic.

## Acceptance Evidence

- Query tuning: compare plans and measured latency or buffer usage under the
  same parameters and representative data distribution.
- Index changes: confirm intended scans use the index and account for write,
  storage, and maintenance overhead.
- RLS or privilege changes: test allowed and denied paths with the actual roles;
  service-role success is not proof that end-user policies work.
- Connection changes: verify pool mode, transaction semantics, prepared
  statement compatibility, connection limits, and saturation behavior.
- Schema changes: verify constraints, backfill behavior, lock exposure, and the
  recovery procedure before production rollout.

## Boundaries

- Never run `EXPLAIN ANALYZE` on a mutating statement in production without an
  explicitly safe transaction and authorization; plain `EXPLAIN` is the safer
  default for uncertain statements.
- Do not present generic PostgreSQL advice as a Supabase platform guarantee.
- Static SQL review and local tests do not prove production capacity, failover,
  replication health, or zero-downtime migration behavior.
<!-- LOCAL-QUALITY-SUPPLEMENT:END -->
