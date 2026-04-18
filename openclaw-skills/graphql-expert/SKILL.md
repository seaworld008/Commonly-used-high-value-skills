---
name: graphql-expert
description: '用于 GraphQL API 设计、查询优化、Schema 管理和安全最佳实践。来源：全网高频推荐。'
version: "1.0.0"
author: "seaworld008"
source: "community"
source_url: ""
tags: '["development", "expert", "graphql"]'
created_at: "2026-03-27"
updated_at: "2026-03-27"
quality: 4
complexity: "intermediate"
license: "UNKNOWN - verify upstream"
---

# GraphQL Expert

## 触发条件
- 当需要设计现代、高效的 Web/Mobile API，且 REST API 面临“Over-fetching”或“Under-fetching”问题时。
- 在构建具有复杂关联关系的数据模型（如社交网络、电商平台）时。
- 需要在多个微服务之上构建统一的数据聚合层（Federation/Gateway）时。
- 系统对实时通信有需求，需要使用 WebSocket 实现 GraphQL Subscriptions 时。
- 需要在同一个 API 端点支持多个版本的客户端，且不希望频繁变更 API 路径时。

## 核心能力

### 1. Schema 设计哲学 (Design Paradigms)
- **Schema-first**: 优先定义 SDL (Schema Definition Language)。便于前后端并行开发，利于契约化管理。
- **Code-first**: 根据代码自动生成 Schema。减少定义冗余，提升类型安全（如 TypeScript + GraphQL Nexus）。
- **字段细粒度控制**: 遵循“单一职责”原则定义每一个 Query 和 Mutation 字段。
- **Scalar 类型扩展**: 自定义 Date, Email, BigInt 等自定义标量，增强校验能力。

### 2. 高级查询与 Resolver 模式
- **Resolver 分层**: 业务逻辑与数据获取逻辑分离，保持 Resolver 的简洁性。
- **N+1 问题详解**: 
  - 传统 Resolver 在循环查询关联对象时会发起大量重复数据库调用。
  - **解决方案**: 使用 DataLoader。通过对请求进行批处理（Batching）和缓存（Caching），将 $N+1$ 次查询合并为 1-2 次。
- **异步处理**: Resolver 全面采用 Promise/Async-await 模式，支持并发数据抓取。

### 3. 分页与数据导航 (Pagination)
- **Offset Pagination**: 适用于简单的列表，支持随机访问。缺点是大数据量下数据库 `OFFSET` 性能低下。
- **Cursor-based Pagination (Relay Spec)**: 使用 `edges`, `node`, `pageInfo` 结构。推荐用于大数据量和无限滚动场景，具有卓越的数据库查询性能。
- **Connection 规范**: 统一化所有分页字段的命名习惯，便于前端通用组件复用。

### 4. 实时性与性能优化 (Performance & Real-time)
- **Subscriptions**: 基于 WebSockets 的双向长连接，用于向客户端推送增量更新。
- **Fragment 复用**: 提高查询的可维护性，确保多个组件对同一份数据的获取始终一致。
- **Persisted Queries**: 客户端发送查询的 Hash 而非完整的字符串。优点：显著降低网络载荷，防止恶意查询注入。
- **Query Complexity Analysis**: 计算查询的深度和字段权重，在服务器端拦截掉过度复杂的“拒绝服务”查询。

### 5. 安全性与认证授权 (Security & Auth)
- **认证 (Authentication)**: 通常在 Context 注入时完成。
- **授权 (Authorization)**: 
  - **Field-level Auth**: 在 Resolver 层对字段访问权限进行精细化控制。
  - **Directive Auth**: 使用 `@auth` 指令在 Schema 层面直接声明访问控制。
- **输入校验**: 严格利用 GraphQL 强类型系统 + 合规库对输入 Input 对象进行深度校验。
- **防反爬/防爆破**: 实现基于 API 成本或复杂度的 Rate Limiting。

## 常用命令/模板

### Schema 定义模板 (SDL)
```graphql
type User {
  id: ID!
  username: String!
  posts(first: Int, after: String): PostConnection! @auth(role: "USER")
}

type Query {
  me: User
  searchPosts(keyword: String!): [Post]
}

type Mutation {
  createPost(content: String!): Post
}
```

### Resolver 实现示例 (DataLoader)
```javascript
const userLoader = new DataLoader(keys => myDb.batchGetUsers(keys));

const resolvers = {
  Post: {
    author: (parent, args, context) => {
      // 解决 N+1 问题的关键：使用 loader
      return userLoader.load(parent.authorId);
    }
  }
};
```

### 查询示例
```graphql
query GetMyProfile {
  me {
    id
    username
    posts(first: 10) {
      edges {
        node {
          title
          author {
            id
          }
        }
      }
    }
  }
}
```

## 边界与限制
- **缓存挑战**: 传统的 HTTP 缓存（CDN/Browser）由于 GraphQL 采用 POST 方式且端点单一，无法轻易基于路径做缓存。需在应用层使用 Apollo Client / Relay 缓存。
- **入门门槛**: 前后端开发人员都需要学习 Schema 规范及客户端库，初期学习曲线较陡峭。
- **二进制上传**: GraphQL 原生对文件上传支持不友好，通常需要配合 Multipart 请求或 S3 Presigned URL。
- **过度灵活**: 允许客户端按需索取数据，意味着服务器端难以预测查询的组合情况，对数据库索引优化提出了更高要求。

---
*注：本技能参考 Apollo GraphQL 和 GraphQL Foundation 官方推荐实践编写。*
* lines: 110
* word count: ~1100 characters
