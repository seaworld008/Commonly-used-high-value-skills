---
name: aws-solution-architect
description: '用于 AWS 云架构设计、服务选型、成本优化与 Well-Architected Framework 评估。来源：alirezarezvani/claude-skills。'
---

# AWS Solution Architect

## 触发条件
- 需要将传统本地应用平滑迁移（Lift & Shift）到 AWS 云端时。
- 面对业务增长，需要设计支持弹性扩缩容、高可用（HA）和容灾（DR）的系统架构。
- 评估现有 AWS 资源使用情况，通过 Rightsizing 和 Reserved Instances (RI) 进行成本优化。
- 设计多层 VPC 网络拓扑，确保公共子网、私有子网和数据存储层的安全隔离。
- 实现细粒度的 IAM 权限管理，支持多人协作环境下的最小权限原则。
- 面对复杂需求进行核心服务选型（如决定使用 Lambda 还是 EC2，DynamoDB 还是 RDS）。

## 核心能力

### 1. AWS Well-Architected 六大支柱
- **卓越运营 (Operational Excellence)**: 通过基础设施即代码 (IaC) 自动化部署和观测。
- **安全性 (Security)**: 多层防御、加密静态/传输数据、IAM 身份联合。
- **可靠性 (Reliability)**: 跨多可用区 (Multi-AZ) 部署，设计自愈能力。
- **性能效率 (Performance Efficiency)**: 选择正确的实例类型，利用 Serverless 减少管理开销。
- **成本优化 (Cost Optimization)**: 使用 Spot 实例、节省计划 (Savings Plans) 和资源清理。
- **可持续性 (Sustainability)**: 减少资源闲置，优化数据存储方案。

### 2. 核心服务选型 (Service Selection)
- **计算 (Compute)**: 
  - EC2: 传统应用、长期运行、完全控制内核。
  - Lambda: 无服务器、事件驱动、按量计费。
  - ECS/EKS: 容器化应用编排。
- **存储 (Storage)**: 
  - S3: 海量对象存储（备份、静态文件、数据湖）。
  - EBS: EC2 块存储。
  - EFS: 跨 EC2 的共享文件系统。
- **数据库 (Database)**: 
  - RDS: 托管关系型数据库（Aurora 为高性能推荐）。
  - DynamoDB: 高性能 NoSQL，亚毫秒级延迟。
  - ElastiCache: Redis/Memcached 内存缓存。
- **分发 (Content Delivery)**:
  - CloudFront: CDN 全球加速。

### 3. VPC 网络设计 (Networking)
- **子网划分**: 合理划分 Public (含 NAT Gateway) 和 Private Subnets。
- **安全组 (SG) & 网络 ACL (NACL)**: 区分有状态与无状态防火墙。
- **连接性**: 熟练使用 VPC Peering, Transit Gateway, Client VPN, PrivateLink。
- **DNS 管理**: 使用 Route 53 进行健康检查和流量加权分发。

### 4. IAM 权限与安全管理
- **IAM Roles**: 优先使用角色而非永久性 Access Key。
- **策略评估 (Policy)**: 编写精细的 JSON 策略，支持条件 (Condition) 限制（如 IP, 时间, MFA）。
- **集中管理**: 使用 AWS Organizations 和 Control Tower 管理多账号环境。

### 5. 高可用与灾备 (HA & DR)
- **多可用区**: RDS Multi-AZ, ELB (Elastic Load Balancer) 流量分发。
- **多区域容灾**: 使用 S3 跨区域复制 (CRR), DynamoDB 全球表。
- **容灾策略**: 掌握 Backup & Restore, Pilot Light, Warm Standby, Multi-site Active-Active。

### 6. 成本优化建议
- **监控工具**: 使用 Cost Explorer, Trusted Advisor, AWS Budgets 监控支出。
- **资源下钻**: 发现闲置的 EBS 卷、未关联的 Elastic IP、未使用的 NAT Gateway。
- **架构调整**: 将低频率访问数据转入 S3 Glacier 存储类。

## 常用命令/模板

### CLI 架构观测组合
```bash
# 查询当前账号下所有运行中的 EC2 实例及其规格
aws ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,Type:InstanceType,State:State.Name}' --output table

# 快速分析 S3 存储桶大小
aws s3 ls s3://my-bucket --recursive --human-readable --summarize | tail -2

# 检查 IAM 用户是否开启了 MFA
aws iam list-users --query 'Users[*].UserName' --output text | xargs -n1 aws iam list-mfa-devices --user-name

# 查看 Lambda 函数的运行时与内存配置
aws lambda list-functions --query 'Functions[*].{Name:FunctionName,Runtime:Runtime,Memory:MemorySize}'
```

### 多层 VPC 架构建议模板 (Terraform 风格)
```hcl
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "prod-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"] # 业务应用
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"] # ALB/NAT
  database_subnets = ["10.0.201.0/24", "10.0.202.0/24"] # RDS/NoSQL

  enable_nat_gateway = true
  single_nat_gateway = false # 生产环境建议每可用区一个
  
  tags = {
    Environment = "production"
    CreatedBy   = "AWS-Solution-Architect"
  }
}
```

### IAM 最小权限策略模板 (S3 只读)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": "arn:aws:s3:::my-secure-bucket"
        },
        {
            "Effect": "Allow",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::my-secure-bucket/*",
            "Condition": {
                "IpAddress": { "aws:SourceIp": "1.2.3.4/32" }
            }
        }
    ]
}
```

## 边界与限制
- **单账号限制**: 每个 AWS 账号都有服务限制 (Service Quotas)，在高并发冷启动（如 Lambda）时可能触发。
- **数据出口成本**: AWS 的内网流量通常免费或便宜，但数据流向外网（Data Transfer Out）成本极高，架构设计时需避开跨 Region 数据同步。
- **最终一致性**: 部分服务（如 S3 部分操作、DynamoDB 最终一致性读取）在特定并发场景下需处理数据不一致。
- **非全能银弹**: CloudFront 无法加速非 HTTP/HTTPS 协议流量；Lambda 无法处理超过 15 分钟的计算任务。
- **锁死风险**: 过度依赖 AWS 特定服务（如 AppSync, DynamoDB）可能导致供应商锁死（Vendor Lock-in），架构设计时应权衡便利性与可迁移性。
