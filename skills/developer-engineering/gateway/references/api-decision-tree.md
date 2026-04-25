# API Design Decision Tree

## Protocol Selection

| Requirement | REST | GraphQL | gRPC |
|-------------|------|---------|------|
| Public API | ✅ Recommended | ⚠️ Conditional | ❌ |
| Microservices | ⚠️ | ❌ | ✅ Recommended |
| Mobile apps | ✅ | ✅ Recommended | ⚠️ |
| Real-time | WebSocket | Subscription | Streaming |
| File transfer | ✅ | ❌ | ✅ |
| Browser direct call | ✅ | ✅ | ❌ (grpc-web required) |

## Selection Flowchart

```
Q1: Who is the client?
├─ Browser/Mobile → Q2
├─ Internal services → gRPC recommended
└─ Third party → REST recommended

Q2: Data fetching pattern?
├─ Fixed fields → REST
├─ Flexible field selection → GraphQL
└─ Real-time updates → WebSocket/SSE
```

## GraphQL vs REST Decision Criteria

| GraphQL is better | REST is better |
|-------------------|----------------|
| Fetch multiple resources in one request | Simple CRUD operations |
| Mobile bandwidth is critical | Caching is important (CDN) |
| Frontend-driven development | API contract via OpenAPI is important |
| UI changes frequently | Stable API contract |
