---
name: kubernetes-specialist
description: '用于 Kubernetes 集群管理、部署编排、Pod 调试与 Helm Chart 设计。来源：skills.sh 5K+ installs。'
version: "1.0.0"
author: "seaworld008"
source: "skills.sh"
source_url: "https://skills.sh/jeffallan/claude-skills/kubernetes-specialist"
license: "MIT"
tags: '["development", "kubernetes", "specialist"]'
created_at: "2026-03-27"
updated_at: "2026-03-27"
quality: 4
complexity: "intermediate"
---

# Kubernetes Specialist

## 触发条件
- 需要部署新的微服务到 Kubernetes 集群时。
- 现有 Pod 出现故障、重启或性能瓶颈（如 CPU/Memory 限制）时。
- 需要设计或维护 Helm Charts 以实现应用的参数化部署。
- 配置集群自动扩缩容（HPA/VPA）以应对流量波动。
- 实施 RBAC 权限控制，确保多租户环境的安全。
- 进行集群范围的资源审计或配置优化（ConfigMap/Secret 管理）。

## 核心能力

### 1. 资源管理 (Resource Management)
- **Deployment**: 理解声明式更新，管理副本集、滚动更新策略（RollingUpdate vs Recreate）。
- **Service**: 熟练配置 ClusterIP、NodePort、LoadBalancer，理解 Endpoints 机制。
- **ConfigMap & Secret**: 将配置与代码解耦，理解 Secret 的 base64 编码及其实时挂载特性。
- **Volume**: 管理 PersistentVolume (PV) 和 PersistentVolumeClaim (PVC)，配置持久化存储。

### 2. Pod 故障排查流程
- **Phase 1: 查看状态** - `kubectl get pods` 确认状态（Pending, Error, CrashLoopBackOff）。
- **Phase 2: 详情检查** - `kubectl describe pod <name>` 查看事件日志（Events），定位调度失败或探针失败原因。
- **Phase 3: 日志分析** - `kubectl logs <name> [-c container] [--previous]` 查看标准输出/错误流。
- **Phase 4: 运行时调试** - `kubectl exec -it <name> -- /bin/sh` 进入容器内部排查（如网络连通性）。
- **Phase 5: 临时调试容器** - 使用 `kubectl debug` 注入诊断容器。

### 3. Helm Chart 最佳实践
- **模板化**: 合理使用 `{{ .Values.xxx }}` 提取配置，支持多环境部署（values-dev.yaml, values-prod.yaml）。
- **依赖管理**: 使用 `Chart.yaml` 管理子 Chart 依赖。
- **Hook 机制**: 利用 `pre-install`, `post-upgrade` 等 Hooks 处理数据库迁移或清理任务。
- **版本控制**: 严格遵守 Semantic Versioning，确保 Chart 与应用镜像版本同步。

### 4. 自动扩缩容 (HPA/VPA)
- **HPA (Horizontal Pod Autoscaler)**: 基于 CPU/内存利用率或自定义指标（Custom Metrics）自动增减副本数。
- **VPA (Vertical Pod Autoscaler)**: 自动调整 Pod 的资源请求（Requests）和限制（Limits）。
- **Cluster Autoscaler**: 与云厂商集成，自动调整节点池大小。

### 5. 安全与 RBAC
- **Namespace 隔离**: 逻辑上划分开发、测试、生产环境。
- **RBAC**: 定义 Role/ClusterRole 和 RoleBinding/ClusterRoleBinding，遵循最小权限原则。
- **Network Policy**: 控制 Pod 间的流量出入，实施微服务间的安全隔离。

## 常用命令/模板

### 故障排查组合拳
```bash
# 查看所有 Namespace 下异常的 Pod
kubectl get pods -A --field-selector=status.phase!=Running

# 追踪实时日志并显示时间戳
kubectl logs -f <pod-name> --timestamps

# 查看资源占用排行
kubectl top nodes
kubectl top pods

# 导出资源定义的干净版本（去除 runtime 信息）
kubectl get deployment <name> -o yaml | kubectl-neat > deployment.yaml
```

### Deployment 模板 (Best Practice)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: main
        image: my-app:v1.2.3
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 15
          periodSeconds: 20
        readinessProbe:
          httpGet:
            path: /readyz
            port: 8080
```

### HPA 配置示例
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## 边界与限制
- **有状态应用**: 对于复杂的有状态应用（如数据库），优先考虑使用 Operator 而非简单的 StatefulSet。
- **本地存储**: 避免在 Pod 中使用 HostPath 存储持久数据，除非是特定的系统级组件。
- **配置更新**: 修改 ConfigMap 不会自动触发 Deployment 重启，除非在 Annotation 中加入了 ConfigMap 的 Hash 或使用 Reloader 等工具。
- **安全边界**: Kubernetes 容器不是强隔离边界，对于极高安全性要求的场景（如运行不受信任的代码），应考虑 Kata Containers 或 gVisor。
- **监控缺失**: 如果没有 Prometheus/Grafana 等监控系统，Kubernetes 的自动扩缩容和自愈能力将大打折扣。
