# Error Response, Pagination & Rate Limiting Patterns

## Error Response Design

### Standard Error Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request contains invalid data",
    "details": [
      {
        "field": "email",
        "code": "INVALID_FORMAT",
        "message": "Email must be a valid email address"
      },
      {
        "field": "password",
        "code": "TOO_SHORT",
        "message": "Password must be at least 8 characters"
      }
    ],
    "requestId": "req_abc123",
    "timestamp": "2024-01-15T10:30:00Z",
    "documentation": "https://api.example.com/docs/errors#VALIDATION_ERROR"
  }
}
```

### Error Code Catalog

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `INVALID_JSON` | 400 | Request body is not valid JSON |
| `MISSING_FIELD` | 400 | Required field not provided |
| `INVALID_FORMAT` | 400 | Field format is invalid |
| `UNAUTHORIZED` | 401 | Authentication required |
| `INVALID_TOKEN` | 401 | Token is invalid or expired |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource does not exist |
| `METHOD_NOT_ALLOWED` | 405 | HTTP method not supported |
| `CONFLICT` | 409 | Resource state conflict |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Unexpected server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

---

## Pagination Patterns

### Offset-based Pagination

```json
// Request
GET /api/v1/users?limit=10&offset=20

// Response
{
  "data": [...],
  "meta": {
    "total": 150,
    "limit": 10,
    "offset": 20,
    "hasMore": true
  },
  "links": {
    "self": "/api/v1/users?limit=10&offset=20",
    "first": "/api/v1/users?limit=10&offset=0",
    "prev": "/api/v1/users?limit=10&offset=10",
    "next": "/api/v1/users?limit=10&offset=30",
    "last": "/api/v1/users?limit=10&offset=140"
  }
}
```

### Cursor-based Pagination (Recommended for large datasets)

```json
// Request
GET /api/v1/users?limit=10&cursor=eyJpZCI6MTIzfQ==

// Response
{
  "data": [...],
  "meta": {
    "limit": 10,
    "hasMore": true,
    "nextCursor": "eyJpZCI6MTMzfQ==",
    "prevCursor": "eyJpZCI6MTEzfQ=="
  },
  "links": {
    "self": "/api/v1/users?limit=10&cursor=eyJpZCI6MTIzfQ==",
    "next": "/api/v1/users?limit=10&cursor=eyJpZCI6MTMzfQ==",
    "prev": "/api/v1/users?limit=10&cursor=eyJpZCI6MTEzfQ=="
  }
}
```

### Comparison

| Aspect | Offset | Cursor |
|--------|--------|--------|
| Random access | Yes | No |
| Consistent with changes | No | Yes |
| Performance on large sets | Poor | Good |
| Simple implementation | Yes | More complex |
| Use case | Small datasets, UI pages | Large datasets, feeds |

### Pagination Selection Criteria

```
予想レコード数は？
├─ <1,000件 → Offset (シンプルで十分)
├─ 1,000〜10,000件 → 用途次第
│   ├─ ランダムアクセス必要 → Offset
│   └─ 一貫性重視 → Cursor
└─ >10,000件 → Cursor (パフォーマンス優先)

リアルタイム更新があるか？
├─ はい（フィード、通知等） → Cursor
└─ いいえ → Offset でも可

ページ番号UIが必要か？
├─ はい（「3ページ目」表示） → Offset
└─ いいえ（無限スクロール等） → Cursor
```

**選択時の確認事項:**
- [ ] 既存APIの方式と整合性があるか
- [ ] クライアント実装の複雑さは許容範囲か
- [ ] 将来のデータ増加を考慮しているか

---

## Rate Limiting Patterns

### Algorithm Comparison

| Algorithm | Burst Support | Complexity | Recommended Use |
|-----------|---------------|------------|-----------------|
| Token Bucket | ✅ | Medium | General APIs |
| Leaky Bucket | ❌ | Low | Stable throughput |
| Fixed Window | ⚠️ Boundary issue | Low | Simple cases |
| Sliding Window | ✅ | High | Precise control |

### Rate Limit Definition in OpenAPI

> **Note:** IETF draft-ietf-httpapi-ratelimit-headers (Standards Track, draft-10 Sep 2025) defines standardized `RateLimit-Policy` and `RateLimit` header fields. Prefer these for new APIs. The `X-RateLimit-*` headers below remain widely deployed and should be supported for backward compatibility.

```yaml
components:
  headers:
    RateLimit-Policy:
      description: Quota policy (IETF standard)
      schema:
        type: string
        example: "1000;w=3600"
    RateLimit:
      description: Remaining quota for the policy (IETF standard)
      schema:
        type: string
        example: "limit=1000, remaining=999, reset=60"
    X-RateLimit-Limit:
      description: Request limit per window (legacy)
      schema:
        type: integer
        example: 1000
    X-RateLimit-Remaining:
      description: Remaining request count (legacy)
      schema:
        type: integer
        example: 999
    X-RateLimit-Reset:
      description: Reset time in Unix timestamp (legacy)
      schema:
        type: integer
        example: 1640995200
    Retry-After:
      description: 429時の待機秒数
      schema:
        type: integer
        example: 60

  responses:
    TooManyRequests:
      description: Rate limit exceeded
      headers:
        X-RateLimit-Limit:
          $ref: '#/components/headers/X-RateLimit-Limit'
        X-RateLimit-Remaining:
          $ref: '#/components/headers/X-RateLimit-Remaining'
        X-RateLimit-Reset:
          $ref: '#/components/headers/X-RateLimit-Reset'
        Retry-After:
          $ref: '#/components/headers/Retry-After'
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            code: "RATE_LIMIT_EXCEEDED"
            message: "Too many requests. Please retry after 60 seconds."
```

### Rate Limiting Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| Per User | Limit per user | Authenticated APIs |
| Per IP | Limit per IP address | Public APIs |
| Per API Key | Limit per API key | Third-party integrations |
| Per Endpoint | Limit per endpoint | Heavy processing APIs |
| Global | System-wide limit | System protection |
