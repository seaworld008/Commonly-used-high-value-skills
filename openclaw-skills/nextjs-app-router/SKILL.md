---
name: nextjs-app-router
description: '用于 Next.js App Router 模式开发，包含 RSC、Server Actions 和路由最佳实践。来源：skills.sh 10.2K installs。'
version: "1.0.0"
author: "seaworld008"
source: "skills.sh"
source_url: ""
tags: '["app", "development", "nextjs", "router"]'
created_at: "2026-03-27"
updated_at: "2026-03-27"
quality: 4
complexity: "intermediate"
license: "UNKNOWN - verify upstream"
---

# Next.js App Router

## 触发条件
- 构建现代 Web 应用，需要高性能的 React Server Components (RSC) 渲染架构时。
- 想要摆脱传统 API 路由模式，利用 Server Actions 直接在 UI 组件中处理表单提交和数据库变更时。
- 实现复杂的多级路由嵌套、并行路由 (Parallel Routes) 或拦截路由 (Intercepting Routes) 时。
- 需要利用 Next.js 14+ 的 Metadata API 优化 SEO 和动态社交卡片预览时。
- 追求极致的加载体验，利用 Streaming、Suspense 和局部加载 (Loading UI) 减少用户等待感时。
- 在页面级别细粒度控制缓存（Static vs Dynamic）、中间件 (Middleware) 和边缘运行时 (Edge Runtime) 时。

## 核心能力

### 1. App Router vs Pages Router 对比
- **文件系统**: `app/` 目录下默认所有组件为 Server Components，而 `pages/` 默认为 Client Components。
- **渲染模型**: App Router 支持更细粒度的部分渲染（Partial Rendering），而 Pages Router 更多依赖于全页面的 SSR/SSG。
- **布局流**: App Router 通过 `layout.tsx` 实现跨页面状态保持和 UI 共享，避免不必要的重新渲染。

### 2. React Server Components (RSC) 最佳实践
- **数据获取**: 在 Server Components 中直接使用 `async/await` 调用数据库（如 Prisma, Drizzle）或第三方 API，无需外部数据获取 Hook（如 SWR/React Query）。
- **组件边界**: 明确区分 Client Component (`"use client"`) 和 Server Component。尽可能将状态、事件处理器和浏览器 API（如 `useEffect`, `window`）封装在小的 Client Component 中，保持大块 UI 为 Server Component 以减少 JS Bundle 体积。

### 3. Server Actions (数据变更)
- **表单处理**: 使用 `action` 属性绑定 Server Action，结合 `useFormStatus` 和 `useFormState` 处理 Loading 状态和验证反馈。
- **安全性**: 默认具备 CSRF 防护。在 Action 内部执行身份验证 (`auth()`) 和权限校验。
- **数据更新**: 完成操作后通过 `revalidatePath("/")` 或 `revalidateTag("collection")` 触发局部数据缓存刷新。

### 4. 路由进阶 (Advanced Routing)
- **Parallel Routes**: 使用 `@folder` 语法在同一布局中同时显示多个独立页面（如仪表盘中同时展示统计表和通知列表）。
- **Intercepting Routes**: 使用 `(..)` 语法在当前上下文拦截路由（如点击图片在 Modal 中预览，但刷新页面则直接导航至详情页）。
- **动态路由**: 熟练使用 `[id]`、`[[...slug]]` (Catch-all) 进行动态路径匹配。

### 5. 流式传输与 Suspense (Streaming & Suspense)
- **Loading UI**: 在目录中创建 `loading.tsx` 实现即时的骨架屏反馈。
- **部分流式**: 使用 `<Suspense>` 包裹耗时的数据拉取组件，允许页面的非阻塞加载，优先显示已就绪的静态内容。

### 6. Metadata API & SEO
- **静态元数据**: 在 `layout.tsx` 或 `page.tsx` 中定义 `export const metadata` 对象。
- **动态元数据**: 使用 `generateMetadata` 函数基于路由参数或数据动态生成页面标题、描述和 OpenGraph 图像。

### 7. 中间件配置 (Middleware)
- **身份校验**: 拦截未授权访问并重定向至登录页。
- **多语言 (i18n)**: 根据浏览器 Header 自动切换语言路径。
- **匹配规则**: 在 `config.matcher` 中精确定义中间件执行的路径范围。

## 常用命令/模板

### 基础项目初始化与检查
```bash
# 启动本地开发服务 (带热更新)
pnpm dev

# 构建生产产物并分析体积 (Next.js Bundle Analyzer)
ANALYZE=true pnpm build

# 快速检查当前路由配置
find app/ -name "page.tsx" -o -name "route.ts" | sort

# 检查 Next.js 版本并升级
pnpm outdated next
pnpm add next@latest react@latest react-dom@latest
```

### Server Component 数据拉取模板
```tsx
// app/users/[id]/page.tsx
import { db } from "@/lib/db";
import { Suspense } from "react";
import UserSkeleton from "@/components/UserSkeleton";

async function UserProfile({ id }: { id: string }) {
  const user = await db.user.findUnique({ where: { id } });
  if (!user) return <div>User not found</div>;
  return <h1>{user.name}</h1>;
}

export default function Page({ params }: { params: { id: string } }) {
  return (
    <main>
      <Suspense fallback={<UserSkeleton />}>
        <UserProfile id={params.id} />
      </Suspense>
    </main>
  );
}
```

### Server Action 表单提交模板
```tsx
// actions/user-actions.ts
"use server";

import { revalidatePath } from "next/cache";

export async function updateUsername(formData: FormData) {
  const name = formData.get("username") as string;
  // 1. 权限校验 (例如使用 next-auth)
  // 2. 数据库更新 (例如 Prisma)
  await db.user.update({ data: { name } });
  
  // 3. 刷新缓存并重定向
  revalidatePath("/profile");
}
```

### 中间件权限保护模板
```typescript
// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('next-auth.session-token');

  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*', '/settings/:path*'],
};
```

## 边界与限制
- **客户端组件限制**: Client Components 不能包含 Server-only 库（如 `fs`, `pg`），必须通过 Props 传递数据。
- **序列化限制**: 从 Server Component 传递给 Client Component 的 Props 必须是可序列化的（不能传递复杂的函数、Map、Set 等，除非使用 `use server`）。
- **缓存复杂性**: App Router 的缓存机制（Request Memoization, Data Cache, Full Route Cache）较为复杂，需要理解 `force-dynamic` 等配置。
- **第三方库兼容性**: 部分旧版 React 库可能不支持 RSC，需要手动添加 `"use client"` 或使用 Wrapper。
- **边缘运行时限制**: Edge Runtime 不支持完整的 Node.js API，在进行大量加密、复杂计算或文件操作时需使用默认的 Node.js Runtime。
