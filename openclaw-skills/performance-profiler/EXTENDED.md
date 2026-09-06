# Extended procedures and examples

Use [SKILL.md](SKILL.md) to select the task. Read only the sections it links for the current step.

<a id="section-1"></a>

## Load Testing with k6

```javascript
// tests/load/api-load-test.js
import http from 'k6/http'
import { check, sleep } from 'k6'
import { Rate, Trend } from 'k6/metrics'

const errorRate = new Rate('errors')
const taskListDuration = new Trend('task_list_duration')

export const options = {
  stages: [
    { duration: '30s', target: 10 },   // Ramp up to 10 VUs
    { duration: '1m',  target: 50 },   // Ramp to 50 VUs
    { duration: '2m',  target: 50 },   // Sustain 50 VUs
    { duration: '30s', target: 100 },  // Spike to 100 VUs
    { duration: '1m',  target: 50 },   // Back to 50
    { duration: '30s', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],   // 95% of requests < 500ms
    http_req_duration: ['p(99)<1000'],  // 99% < 1s
    errors: ['rate<0.01'],              // Error rate < 1%
    task_list_duration: ['p(95)<200'],  // Task list specifically < 200ms
  },
}

const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000'

export function setup() {
  // Get auth token once
  const loginRes = http.post(`${BASE_URL}/api/auth/login`, JSON.stringify({
    email: 'loadtest@example.com',
    password: 'loadtest123',
  }), { headers: { 'Content-Type': 'application/json' } })

  return { token: loginRes.json('token') }
}

export default function(data) {
  const headers = {
    'Authorization': `Bearer ${data.token}`,
    'Content-Type': 'application/json',
  }

  // Scenario 1: List tasks
  const start = Date.now()
  const listRes = http.get(`${BASE_URL}/api/tasks?limit=20`, { headers })
  taskListDuration.add(Date.now() - start)

  check(listRes, {
    'list tasks: status 200': (r) => r.status === 200,
    'list tasks: has items': (r) => r.json('items') !== undefined,
  }) || errorRate.add(1)

  sleep(0.5)

  // Scenario 2: Create task
  const createRes = http.post(
    `${BASE_URL}/api/tasks`,
    JSON.stringify({ title: `Load test task ${Date.now()}`, priority: 'medium' }),
    { headers }
  )

  check(createRes, {
    'create task: status 201': (r) => r.status === 201,
  }) || errorRate.add(1)

  sleep(1)
}

export function teardown(data) {
  // Cleanup: delete load test tasks
}
```

```bash
# Run load test
k6 run tests/load/api-load-test.js \
  --env BASE_URL=https://staging.myapp.com

# With Grafana output
k6 run --out influxdb=http://localhost:8086/k6 tests/load/api-load-test.js
```

---

<a id="section-2"></a>

## Before/After Measurement Template

```markdown
## Performance Optimization: [What You Fixed]

**Date:** 2026-03-01
**Engineer:** @username
**Ticket:** PROJ-123

### Problem
[1-2 sentences: what was slow, how was it observed]

### Root Cause
[What the profiler revealed]

### Baseline (Before)
| Metric | Value |
|--------|-------|
| P50 latency | 480ms |
| P95 latency | 1,240ms |
| P99 latency | 3,100ms |
| RPS @ 50 VUs | 42 |
| Error rate | 0.8% |
| DB queries/req | 23 (N+1) |

Profiler evidence: [link to flamegraph or screenshot]

### Fix Applied
[What changed — code diff or description]

### After
| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| P50 latency | 480ms | 48ms | -90% |
| P95 latency | 1,240ms | 120ms | -90% |
| P99 latency | 3,100ms | 280ms | -91% |
| RPS @ 50 VUs | 42 | 380 | +804% |
| Error rate | 0.8% | 0% | -100% |
| DB queries/req | 23 | 1 | -96% |

### Verification
Load test run: [link to k6 output]
```

---

<a id="section-3"></a>

### Node.js Memory Profiling Script

```javascript
// scripts/memory-profile.mjs
// Run: node --experimental-vm-modules scripts/memory-profile.mjs

import { createRequire } from 'module'
const require = createRequire(import.meta.url)

function formatBytes(bytes) {
  return (bytes / 1024 / 1024).toFixed(2) + ' MB'
}

function measureMemory(label) {
  const mem = process.memoryUsage()
  console.log(`\n[${label}]`)
  console.log(`  RSS:       ${formatBytes(mem.rss)}`)
  console.log(`  Heap Used: ${formatBytes(mem.heapUsed)}`)
  console.log(`  Heap Total:${formatBytes(mem.heapTotal)}`)
  console.log(`  External:  ${formatBytes(mem.external)}`)
  return mem
}

const baseline = measureMemory('Baseline')

// Simulate your operation
for (let i = 0; i < 1000; i++) {
  // Replace with your actual operation
  const result = await someOperation()
}

const after = measureMemory('After 1000 operations')

console.log(`\n[Delta]`)
console.log(`  Heap Used: +${formatBytes(after.heapUsed - baseline.heapUsed)}`)

// If heap keeps growing across GC cycles, you have a leak
global.gc?.() // Run with --expose-gc flag
const afterGC = measureMemory('After GC')
if (afterGC.heapUsed > baseline.heapUsed * 1.1) {
  console.warn('⚠️  Possible memory leak detected (>10% growth after GC)')
}
```

---
