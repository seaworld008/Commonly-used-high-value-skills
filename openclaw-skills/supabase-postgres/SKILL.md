---
name: supabase-postgres
description: '用于 Supabase 平台开发与 PostgreSQL 最佳实践，包含 RLS、Edge Functions 和实时订阅。来源：supabase 官方 52.5K installs。'
version: "1.0.0"
author: "seaworld008"
source: "skills.sh"
source_url: "https://skills.sh/supabase/agent-skills/supabase-postgres-best-practices"
tags: '["development", "postgres", "supabase"]'
created_at: "2026-03-27"
updated_at: "2026-03-27"
quality: 4
complexity: "intermediate"
license: "MIT"
---

# Supabase & PostgreSQL

## 触发条件
- 构建全栈 Web 或移动应用，需要快速实现后端能力（Auth, Database, Storage, Edge Functions）时。
- 面对复杂的数据安全需求，需要通过 PostgreSQL 的 Row Level Security (RLS) 实现多租户或多用户数据隔离时。
- 追求极致的应用性能，利用 PostgreSQL 索引优化查询、视图 (Views) 和存储过程 (Stored Procedures) 时。
- 实现实时功能（如聊天、通知、实时仪表盘），利用 Supabase Realtime 订阅数据库变更时。
- 需要编写逻辑执行在边缘侧（Edge Functions），以处理第三方 API 调用或复杂的业务校验时。
- 管理数据库架构演变，执行 Database Migrations 确保开发环境与生产环境一致时。

## 核心能力

### 1. Supabase 项目架构 (Project Architecture)
- **PostgREST 自动 API**: 无需编写传统的 REST API，Supabase 会自动基于数据库 Schema 生成对应的 API 接口。
- **GoTrue 身份验证 (Auth)**: 快速集成 OAuth (Google, GitHub)、Email/Password、Magic Link 和手机短信验证。
- **Storage 管理**: 管理文件的上传、下载和权限控制，支持 CDN 加速。

### 2. PostgreSQL 索引与查询优化 (Query Optimization)
- **B-Tree 索引**: 常规字段搜索加速。
- **GIN 索引**: 处理 JSONB 数据类型和全文搜索 (Full-Text Search)。
- **查询计划 (Explain Analyze)**: 分析慢查询原因，发现全表扫描 (Sequential Scan) 并实施针对性优化。
- **视图与物化视图 (Views/Materialized Views)**: 封装复杂的联表查询，提高代码复用性。

### 3. 行级安全策略 (Row Level Security - RLS)
- **启用 RLS**: 确保所有表都启用了 `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`。
- **策略编写 (Policy)**: 利用 `auth.uid()` 比较数据所属 ID。
- **多条件过滤**: 结合 `EXISTS` 或 `IN` 处理基于角色或团队的权限校验。
- **绕过 RLS**: 在特定后台任务中利用 `service_role` 密钥执行越权操作。

### 4. Edge Functions 开发 (Deno 运行时)
- **无服务器逻辑**: 使用 Deno 编写边缘函数，处理 Webhooks 或集成外部服务。
- **本地调试**: 利用 Supabase CLI 进行本地模拟测试。
- **环境变量**: 安全管理 API Keys，避免在客户端代码中暴露。

### 5. 实时订阅 (Realtime)
- **Channel 订阅**: 监听特定表的 `INSERT`, `UPDATE`, `DELETE` 变更。
- **Presence**: 追踪用户在线状态（类似 Slack 的“正在输入...”或在线列表）。
- **Broadcasting**: 实现客户端之间低延迟的直接通信，无需持久化到数据库。

### 6. 数据库迁移 (Database Migrations)
- **本地开发工作流**: 使用 `supabase start` 在本地启动全套环境。
- **版本控制**: 编写 `.sql` 迁移脚本，使用 `supabase db push` 或 `supabase db remote commit` 同步至生产环境。

### 7. Auth 集成与用户同步
- **Auth Hooks**: 利用 PostgreSQL Triggers 在新用户注册时自动创建 profile 记录。
- **Metadata 利用**: 在用户 metadata 中存储偏好设置，通过 `auth.jwt()` 在 RLS 中高效访问。

## 常用命令/模板

### Supabase CLI 工具组合
```bash
# 初始化并启动本地开发环境 (需 Docker)
supabase init
supabase start

# 生成 TypeScript 类型定义 (基于远程 DB Schema)
supabase gen types typescript --project-id your-id > types/supabase.ts

# 创建新的数据库迁移文件
supabase migration new create_profiles_table

# 推送本地迁移至生产环境
supabase db push

# 创建新的边缘函数
supabase functions new my-func
```

### RLS 权限策略模板 (PostgreSQL)
```sql
-- 允许用户只读自己的记录
CREATE POLICY "Users can only see their own items"
ON public.items
FOR SELECT
USING (auth.uid() = user_id);

-- 允许用户修改自己的记录
CREATE POLICY "Users can only update their own items"
ON public.items
FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- 基于角色的策略 (假设有 user_roles 表)
CREATE POLICY "Admins can delete anything"
ON public.items
FOR DELETE
USING (
  EXISTS (
    SELECT 1 FROM user_roles 
    WHERE user_id = auth.uid() AND role = 'admin'
  )
);
```

### Auth 注册触发器模板 (自动创建 Profile)
```sql
-- 函数：将新注册用户同步到 profiles 表
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, avatar_url)
  VALUES (new.id, new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'avatar_url');
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 触发器：在 auth.users 插入后执行
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

### 边缘函数示例 (TypeScript/Deno)
```typescript
// supabase/functions/my-func/index.ts
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

serve(async (req) => {
  const { name } = await req.json()
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL') ?? '',
    Deno.env.get('SUPABASE_ANON_KEY') ?? ''
  )

  const { data, error } = await supabase
    .from('profiles')
    .update({ full_name: name })
    .eq('id', 'some-id')

  return new Response(JSON.stringify({ data, error }), { headers: { "Content-Type": "application/json" } })
})
```

## 边界与限制
- **外键级联 RLS**: RLS 并不总是能自动处理复杂的关联查询，有时需要通过嵌套的 `EXISTS` 查询。
- **并发连接数**: 虽然 Supabase 提供了连接池 (Supavisor)，但在高并发写入场景下仍需关注 PostgreSQL 的连接上限。
- **实时订阅限制**: 单个项目同时在线订阅的数量有上限，且不建议在实时订阅中传输极其庞大的二进制数据。
- **边缘函数超时**: Edge Functions 有执行时长限制（通常为 60 秒），不适合长时间运行的计算任务。
- **PostgreSQL 锁**: 在执行 DDL 操作（如修改表结构）时，可能会锁定表，导致业务短暂不可用，需谨慎使用 `ALTER TABLE` 并结合 `CONCURRENTLY`（如索引创建）。
- **供应商锁定**: 深度使用 Supabase 特有的 API（如 Auth Hooks, Storage）在未来迁移至原生 PostgreSQL 会有一定改造成本。
