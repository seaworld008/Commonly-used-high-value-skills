---
name: performance-profiler
description: 'Profile Node.js, Python, or Go CPU, memory, I/O, and query bottlenecks; use flamegraphs and representative load tests to verify improvements.'
zh_description: "分析 CPU、内存、I/O 和查询瓶颈并验证优化效果。"
version: "1.0.1"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["development", "performance", "profiler"]'
created_at: "2026-03-04"
updated_at: "2026-09-06"
quality: 5
complexity: "intermediate"
---

# Performance Profiler

**Tier:** POWERFUL  
**Category:** Engineering  
**Domain:** Performance Engineering  

---

## Overview

Systematic performance profiling for Node.js, Python, and Go applications. Identifies CPU, memory, and I/O bottlenecks; generates flamegraphs; analyzes bundle sizes; optimizes database queries; detects memory leaks; and runs load tests with k6 and Artillery. Always measures before and after.

## Core Capabilities

- **CPU profiling** — flamegraphs for Node.js, py-spy for Python, pprof for Go
- **Memory profiling** — heap snapshots, leak detection, GC pressure
- **Bundle analysis** — webpack-bundle-analyzer, Next.js bundle analyzer
- **Database optimization** — EXPLAIN ANALYZE, slow query log, N+1 detection
- **Load testing** — k6 scripts, Artillery scenarios, ramp-up patterns
- **Before/after measurement** — establish baseline, profile, optimize, verify

---

## When to Use

- App is slow and you don't know where the bottleneck is
- P99 latency exceeds SLA before a release
- Memory usage grows over time (suspected leak)
- Bundle size increased after adding dependencies
- Preparing for a traffic spike (load test before launch)
- Database queries taking >100ms

---

## Golden Rule: Measure First

```bash
# Establish baseline BEFORE any optimization
# Record: P50, P95, P99 latency | RPS | error rate | memory usage

# Wrong: "I think the N+1 query is slow, let me fix it"
# Right: Profile → confirm bottleneck → fix → measure again → verify improvement
```

---

## Node.js Profiling

### CPU Flamegraph

```bash
# Method 1: clinic.js (best for development)
npm install -g clinic

# CPU flamegraph
clinic flame -- node dist/server.js

# Heap profiler
clinic heapprofiler -- node dist/server.js

# Bubble chart (event loop blocking)
clinic bubbles -- node dist/server.js

# Load with autocannon while profiling
autocannon -c 50 -d 30 http://localhost:3000/api/tasks &
clinic flame -- node dist/server.js
```

```bash
# Method 2: Node.js built-in profiler
node --prof dist/server.js
# After running some load:
node --prof-process isolate-*.log | head -100
```

```bash
# Method 3: V8 CPU profiler via inspector
node --inspect dist/server.js
# Open Chrome DevTools → Performance → Record
```

### Heap Snapshot / Memory Leak Detection

```javascript
// Add to your server for on-demand heap snapshots
import v8 from 'v8'
import fs from 'fs'

// Endpoint: POST /debug/heap-snapshot (protect with auth!)
app.post('/debug/heap-snapshot', (req, res) => {
  const filename = `heap-${Date.now()}.heapsnapshot`
  const snapshot = v8.writeHeapSnapshot(filename)
  res.json({ snapshot })
})
```

```bash
# Take snapshots over time and compare in Chrome DevTools
curl -X POST http://localhost:3000/debug/heap-snapshot
# Wait 5 minutes of load
curl -X POST http://localhost:3000/debug/heap-snapshot
# Open both snapshots in Chrome → Memory → Compare
```

### Detect Event Loop Blocking

```javascript
// Add blocked-at to detect synchronous blocking
import blocked from 'blocked-at'

blocked((time, stack) => {
  console.warn(`Event loop blocked for ${time}ms`)
  console.warn(stack.join('\n'))
}, { threshold: 100 }) // Alert if blocked > 100ms
```

### Node.js Memory Profiling Script

Read [the detailed procedure and examples](EXTENDED.md#section-3) when working on this part of the task.

## Python Profiling

### CPU Profiling with py-spy

```bash
# Install
pip install py-spy

# Profile a running process (no code changes needed)
py-spy top --pid $(pgrep -f "uvicorn")

# Generate flamegraph SVG
py-spy record -o flamegraph.svg --pid $(pgrep -f "uvicorn") --duration 30

# Profile from the start
py-spy record -o flamegraph.svg -- python -m uvicorn app.main:app

# Open flamegraph.svg in browser — look for wide bars = hot code paths
```

### cProfile for function-level profiling

```python
# scripts/profile_endpoint.py
import cProfile
import pstats
import io
from app.services.task_service import TaskService

def run():
    service = TaskService()
    for _ in range(100):
        service.list_tasks(user_id="user_1", page=1, limit=20)

profiler = cProfile.Profile()
profiler.enable()
run()
profiler.disable()

# Print top 20 functions by cumulative time
stream = io.StringIO()
stats = pstats.Stats(profiler, stream=stream)
stats.sort_stats('cumulative')
stats.print_stats(20)
print(stream.getvalue())
```

### Memory profiling with memory_profiler

```python
# pip install memory-profiler
from memory_profiler import profile

@profile
def my_function():
    # Function to profile
    data = load_large_dataset()
    result = process(data)
    return result
```

```bash
# Run with line-by-line memory tracking
python -m memory_profiler scripts/profile_function.py

# Output:
# Line #    Mem usage    Increment   Line Contents
# ================================================
#     10   45.3 MiB   45.3 MiB   def my_function():
#     11   78.1 MiB   32.8 MiB       data = load_large_dataset()
#     12  156.2 MiB   78.1 MiB       result = process(data)
```

---

## Go Profiling with pprof

```go
// main.go — add pprof endpoints
import _ "net/http/pprof"
import "net/http"

func main() {
    // pprof endpoints at /debug/pprof/
    go func() {
        log.Println(http.ListenAndServe(":6060", nil))
    }()
    // ... rest of your app
}
```

```bash
# CPU profile (30s)
go tool pprof -http=:8080 http://localhost:6060/debug/pprof/profile?seconds=30

# Memory profile
go tool pprof -http=:8080 http://localhost:6060/debug/pprof/heap

# Goroutine leak detection
curl http://localhost:6060/debug/pprof/goroutine?debug=1

# In pprof UI: "Flame Graph" view → find the tallest bars
```

---

## Bundle Size Analysis

### Next.js Bundle Analyzer

```bash
# Install
pnpm add -D @next/bundle-analyzer

# next.config.js
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
})
module.exports = withBundleAnalyzer({})

# Run analyzer
ANALYZE=true pnpm build
# Opens browser with treemap of bundle
```

### What to look for

```bash
# Find the largest chunks
pnpm build 2>&1 | grep -E "^\s+(λ|○|●)" | sort -k4 -rh | head -20

# Check if a specific package is too large
# Visit: https://bundlephobia.com/package/moment@2.29.4
# moment: 67.9kB gzipped → replace with date-fns (13.8kB) or dayjs (6.9kB)

# Find duplicate packages
pnpm dedupe --check

# Visualize what's in a chunk
npx source-map-explorer .next/static/chunks/*.js
```

### Common bundle wins

```typescript
// Before: import entire lodash
import _ from 'lodash'  // 71kB

// After: import only what you need
import debounce from 'lodash/debounce'  // 2kB

// Before: moment.js
import moment from 'moment'  // 67kB

// After: dayjs
import dayjs from 'dayjs'  // 7kB

// Before: static import (always in bundle)
import HeavyChart from '@/components/HeavyChart'

// After: dynamic import (loaded on demand)
const HeavyChart = dynamic(() => import('@/components/HeavyChart'), {
  loading: () => <Skeleton />,
})
```

---

## Database Query Optimization

### Find slow queries

```sql
-- PostgreSQL: enable pg_stat_statements
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Top 20 slowest queries
SELECT
  round(mean_exec_time::numeric, 2) AS mean_ms,
  calls,
  round(total_exec_time::numeric, 2) AS total_ms,
  round(stddev_exec_time::numeric, 2) AS stddev_ms,
  left(query, 80) AS query
FROM pg_stat_statements
WHERE calls > 10
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Reset stats
SELECT pg_stat_statements_reset();
```

```bash
# MySQL slow query log
mysql -e "SET GLOBAL slow_query_log = 'ON'; SET GLOBAL long_query_time = 0.1;"
tail -f /var/log/mysql/slow-query.log
```

### EXPLAIN ANALYZE

```sql
-- Always use EXPLAIN (ANALYZE, BUFFERS) for real timing
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT t.*, u.name as assignee_name
FROM tasks t
LEFT JOIN users u ON u.id = t.assignee_id
WHERE t.project_id = 'proj_123'
  AND t.deleted_at IS NULL
ORDER BY t.created_at DESC
LIMIT 20;

-- Look for:
-- Seq Scan on large table → needs index
-- Nested Loop with high rows → N+1, consider JOIN or batch
-- Sort → can index handle the sort?
-- Hash Join → fine for moderate sizes
```

### Detect N+1 Queries

```typescript
// Add query logging in dev
import { db } from './client'

// Drizzle: enable logging
const db = drizzle(pool, { logger: true })

// Or use a query counter middleware
let queryCount = 0
db.$on('query', () => queryCount++)

// In tests:
queryCount = 0
const tasks = await getTasksWithAssignees(projectId)
expect(queryCount).toBe(1)  // Fail if it's 21 (1 + 20 N+1s)
```

```python
# Django: detect N+1 with django-silk or nplusone
from nplusone.ext.django.middleware import NPlusOneMiddleware
MIDDLEWARE = ['nplusone.ext.django.middleware.NPlusOneMiddleware']
NPLUSONE_RAISE = True  # Raise exception on N+1 in tests
```

### Fix N+1 — Before/After

```typescript
// Before: N+1 (1 query for tasks + N queries for assignees)
const tasks = await db.select().from(tasksTable)
for (const task of tasks) {
  task.assignee = await db.select().from(usersTable)
    .where(eq(usersTable.id, task.assigneeId))
    .then(r => r[0])
}

// After: 1 query with JOIN
const tasks = await db
  .select({
    id: tasksTable.id,
    title: tasksTable.title,
    assigneeName: usersTable.name,
    assigneeEmail: usersTable.email,
  })
  .from(tasksTable)
  .leftJoin(usersTable, eq(usersTable.id, tasksTable.assigneeId))
  .where(eq(tasksTable.projectId, projectId))
```

---

## Load Testing with k6

Read [the detailed procedure and examples](EXTENDED.md#section-1) when working on this part of the task.

## Before/After Measurement Template

Read [the detailed procedure and examples](EXTENDED.md#section-2) when working on this part of the task.

## Optimization Checklist

### Quick wins (check these first)

```
Database
□ Missing indexes on WHERE/ORDER BY columns
□ N+1 queries (check query count per request)
□ Loading all columns when only 2-3 needed (SELECT *)
□ No LIMIT on unbounded queries
□ Missing connection pool (creating new connection per request)

Node.js
□ Sync I/O (fs.readFileSync) in hot path
□ JSON.parse/stringify of large objects in hot loop
□ Missing caching for expensive computations
□ No compression (gzip/brotli) on responses
□ Dependencies loaded in request handler (move to module level)

Bundle
□ Moment.js → dayjs/date-fns
□ Lodash (full) → lodash/function imports
□ Static imports of heavy components → dynamic imports
□ Images not optimized / not using next/image
□ No code splitting on routes

API
□ No pagination on list endpoints
□ No response caching (Cache-Control headers)
□ Serial awaits that could be parallel (Promise.all)
□ Fetching related data in a loop instead of JOIN
```

---

## Common Pitfalls

- **Optimizing without measuring** — you'll optimize the wrong thing
- **Testing in development** — profile against production-like data volumes
- **Ignoring P99** — P50 can look fine while P99 is catastrophic
- **Premature optimization** — fix correctness first, then performance
- **Not re-measuring** — always verify the fix actually improved things
- **Load testing production** — use staging with production-size data

---

## Best Practices

1. **Baseline first, always** — record metrics before touching anything
2. **One change at a time** — isolate the variable to confirm causation
3. **Profile with realistic data** — 10 rows in dev, millions in prod — different bottlenecks
4. **Set performance budgets** — `p(95) < 200ms` in CI thresholds with k6
5. **Monitor continuously** — add Datadog/Prometheus metrics for key paths
6. **Cache invalidation strategy** — cache aggressively, invalidate precisely
7. **Document the win** — before/after in the PR description motivates the team
