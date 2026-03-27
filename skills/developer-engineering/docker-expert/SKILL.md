---
name: docker-expert
description: '用于 Docker 容器化最佳实践、多阶段构建优化与 Docker Compose 编排。来源：skills.sh 8.7K installs。'
---

# Docker Expert

## 触发条件
- 当需要将应用容器化，并确保开发、测试、生产环境一致性时。
- 面对庞大的 Docker 镜像体积，需要优化构建流水线和存储效率时。
- 需要通过 Docker Compose 协调多个互相关联的微服务容器时。
- 需要解决复杂的网络通信、数据持久化卷管理或权限隔离问题时。
- 实施 CI/CD 流水线，将构建结果自动推送到镜像仓库并进行安全扫描时。

## 核心能力

### 1. Dockerfile 多阶段构建 (Multi-stage Builds)
- **分离构建与运行**: 使用 `AS` 关键字定义多个阶段。在第一阶段进行源码编译、依赖安装；在第二阶段仅拷贝最终产物（如编译后的二进制文件或静态资源）到轻量级基础镜像（如 Alpine 或 Distroless）中。
- **减少层数**: 合理合并 `RUN` 指令，清理构建过程中的临时文件（如 `npm cache clean`, `apt-get clean`）。
- **优化缓存**: 先拷贝依赖定义文件（`package.json`, `go.mod`），运行安装命令，最后再拷贝源代码。这能显著提高后续构建速度。

### 2. 镜像体积优化 (Image Optimization)
- **选择合适的基础镜像**: 优先使用 `alpine`, `slim` 版本，或 Google 的 `distroless` 镜像以降低攻击面。
- **.dockerignore**: 排除不必要的文件（`.git`, `node_modules`, `tests`, `docs`），减小上传给 Docker daemon 的上下文体积。
- **squash 选项**: 实验性功能，用于合并最终镜像层（慎用，通常多阶段构建已足够高效）。

### 3. Docker Compose 服务编排
- **YAML 结构化配置**: 管理服务、网络（Networks）和卷（Volumes）。
- **依赖顺序控制**: 使用 `depends_on` 及其 `condition: service_healthy`（结合 `healthcheck`）确保依赖服务就绪后再启动主应用。
- **多环境复用**: 利用 `docker-compose.override.yml` 或 `env_file` 实现不同环境的差异化配置。

### 4. 网络与卷管理 (Networking & Volumes)
- **网络模式**: 理解 `bridge`（默认隔离）、`host`（无隔离，高性能）、`none` 及自定义 overlay 网络。
- **卷持久化**: 区分 `bind mounts`（挂载主机目录，常用于开发）和 `named volumes`（由 Docker 管理，常用于生产）。
- **权限安全**: 避免使用 root 用户运行容器。在 Dockerfile 中通过 `USER` 指令切换到非特权用户。

### 5. 安全扫描与审计 (Security Scanning)
- **漏洞扫描**: 使用 `docker scan` (Snyk), `Trivy` 或 `Clair` 检查镜像中的已知 CVE。
- **秘密信息管理**: 绝不将 API Keys 或密码写入 Dockerfile 或环境变量。应使用 Docker Secrets 或外部 Vault。
- **资源限制**: 在 Compose 或容器启动时限制 `--cpus`, `--memory`，防止容器资源耗尽攻击（DoS）。

### 6. CI/CD 集成 (Pipeline Integration)
- **构建标记**: 结合 Git Commit SHA 或语义化版本号进行打标（Tagging）。
- **远程缓存**: 使用 `--cache-from` 提升流水线中的镜像构建速度。
- **镜像仓库交互**: 安全地执行 `docker login`, `push` 流程。

## 常用命令/模板

### 故障排查与清理组合
```bash
# 查看容器资源占用 (CPU, Memory, Network)
docker stats --no-stream

# 进入运行中的容器排查网络
docker exec -it <container_id> /bin/sh -c "ping db_host && nslookup api_service"

# 清理所有未使用的镜像、容器、卷和网络（一键释放磁盘）
docker system prune -af --volumes

# 查看镜像层级与体积详情
docker history <image_name>
```

### 多阶段构建 Dockerfile 模板 (Node.js 示例)
```dockerfile
# 阶段 1: 构建 (Build)
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

# 阶段 2: 运行 (Production)
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV production
# 拷贝构建产物
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# 创建非 root 用户并切换
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget --quiet --tries=1 --spider http://localhost:3000/health || exit 1

CMD ["node", "dist/main.js"]
```

### Docker Compose 编排模板
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "80:3000"
    environment:
      - DB_URL=postgres://user:pass@db:5432/mydb
    depends_on:
      db:
        condition: service_healthy
    networks:
      - frontend
      - backend

  db:
    image: postgres:16-alpine
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend

networks:
  frontend:
  backend:
    internal: true # 限制后端网络不可访问外网

volumes:
  db_data:
```

## 边界与限制
- **GUI 应用**: Docker 并非为图形化桌面应用设计，虽然可以通过 X11 转发实现，但体验较差。
- **内核依赖**: 容器共享宿主机内核，无法在 Linux 容器中运行原生 Windows 系统组件。
- **大规模编排**: 超过 10 个以上相互协作的微服务时，Docker Compose 的管理能力会变得捉襟见肘，此时应迁移至 Kubernetes。
- **IO 性能**: 在 macOS 和 Windows 下，挂载大量小文件（如 node_modules）会导致性能显著下降，建议使用高性能文件同步工具（如 VirtioFS）。
- **冷启动延迟**: 镜像层级过多或基础镜像过大会导致容器启动变慢，这在 Serverless 场景（如 AWS Lambda / Cloud Run）中尤为致命。
