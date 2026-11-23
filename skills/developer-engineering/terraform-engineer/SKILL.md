---
name: terraform-engineer
description: 'Use when designing Terraform IaC, reviewing modules, managing state, planning provider upgrades, or improving repeatable infrastructure deployment workflows.'
zh_description: "用于 Terraform IaC 设计、模块评审、状态管理、Provider 升级和基础设施部署优化。"
version: "1.0.2"
author: "seaworld008"
source: "skills.sh"
source_url: "https://skills.sh/jeffallan/claude-skills/terraform-engineer"
license: "MIT"
tags: ["development", "engineer", "terraform"]
created_at: "2026-03-27"
updated_at: "2026-11-23"
quality: 4
complexity: "intermediate"
---

# Terraform Engineer

## 触发条件
- 想要将云服务（AWS, Azure, GCP）配置实现自动化和代码化管理。
- 面对复杂的基础设施架构（VPC, RDS, EKS, IAM），需要版本化且可重复的部署流程。
- 需要在团队内部共享、复用基础设施模块（Module）以降低管理成本。
- 实施基础设施变更审查（Terraform Plan），确保生产环境变更的安全性。
- 解决环境漂移（Drift）问题，确保实际资源与代码定义的期望状态一致。
- 管理多租户或多环境（Dev/Staging/Prod）的基础设施资源。

## 核心能力

### 1. HCL 语法与最佳实践 (HCL Best Practices)
- **声明式配置**: 理解 HCL (HashiCorp Configuration Language) 的块（Blocks）、参数（Arguments）和表达式（Expressions）。
- **变量与输出**: 灵活使用 `variable`, `output`, `locals` 实现参数化和跨模块数据传递。
- **数据源**: 使用 `data` 源查询已存在或动态生成的云资源。
- **动态块**: 使用 `dynamic "block_name"` 配合 `for_each` 处理列表或映射，减少重复冗余。

### 2. 模块设计模式 (Module Design Patterns)
- **高内聚低耦合**: 将相关联的资源封装在模块中（如 VPC 模块包含 Subnet, Route Table, IGW）。
- **参数标准化**: 定义清晰的输入变量接口，通过 `validation` 块增强配置健壮性。
- **版本化发布**: 将模块发布到私有或公共 Registry，指定 Git Tag 实现版本锁定。
- **组合模式**: 通过顶层模块（Root Module）调用多个子模块构建完整系统。

### 3. 状态管理策略 (State Management)
- **远程状态 (Remote State)**: 使用 S3（Terraform 1.11+ 原生 `use_lockfile = true`，替代已弃用的 `dynamodb_table`）、GCS 或 Terraform Cloud 存储状态文件并启用加密和锁定。
- **敏感信息脱敏**: 理解状态文件中包含明文敏感信息，严格控制状态访问权限。
- **状态迁移与操作**: 优先使用声明式 `import`、`moved`、`removed` 块；仅在旧版本上退回 `terraform import` / `terraform state mv` / `rm`，且任何写状态命令执行前须获用户确认，切勿在日志中打印明文 state。

### 4. 工作流 (Plan/Apply Workflow)
- **Init**: 初始化 Backend 和下载 Providers。
- **Plan**: 预览变更差异，将其作为 PR 审查的核心依据。
- **Apply**: 安全执行变更，通常配合 CI/CD 工具（GitHub Actions, Terraform Cloud）自动化执行。
- **Destroy**: 慎用，仅在销毁整个实验性环境时使用。

### 5. Drift 检测与修复 (Drift Detection & Remediation)
- **检测漂移与校验测试**: 运行 `terraform fmt -recursive`、`terraform validate`、`tflint`、`trivy config`（`tfsec` 已弃用）与原生 `terraform test`（`.tftest.hcl` / `mock_provider`）；状态漂移对齐使用 `terraform apply -refresh-only`（`terraform refresh` 已弃用）。
- **修复策略**:
  - **Reconcile**: 审查 `-refresh-only` 计划后按需修改代码或应用状态对齐。
  - **Import / Refactor**: 使用声明式 `import`、`moved`、`removed` 块将现有或重构资源纳入代码管控。

### 6. Provider 配置与管理
- **锁定版本**: 在 `terraform` 块中明确指定 Provider 版本，防止自动升级导致的兼容性破坏。
- **多 Provider 实例**: 配合 `alias` 管理多区域（Multi-region）或多账号部署。

## 常用命令/模板

### 基础运维组合
```bash
# 初始化并拉取所有模块/插件
terraform init

# 生成变更计划并保存到文件（CI/CD 常用）
terraform plan -out=tfplan

# 应用之前保存的计划，跳过确认
terraform apply "tfplan"

# 请求替换资源，可能销毁并重建；先审查计划和依赖影响
terraform plan -replace="aws_instance.web" -out=replace.tfplan
# 仅在本次替换已获授权后应用
terraform apply "replace.tfplan"

# 图形化展示资源依赖关系
terraform graph | dot -Tsvg > graph.svg
```

### Module 定义模板 (VPC 示例)
```hcl
# modules/vpc/main.tf
resource "aws_vpc" "this" {
  cidr_block = var.vpc_cidr
  tags = {
    Name = var.project_name
  }
}

resource "aws_subnet" "public" {
  for_each = var.public_subnets
  vpc_id     = aws_vpc.this.id
  cidr_block = each.value
  map_public_ip_on_launch = true
}

# modules/vpc/variables.tf
variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
}

variable "public_subnets" {
  type        = map(string)
  default     = {
    "us-east-1a" = "10.0.1.0/24"
    "us-east-1b" = "10.0.2.0/24"
  }
}
```

### Backend 远程状态配置模板
```hcl
terraform {
  required_version = ">= 1.14"

  backend "s3" {
    bucket       = "my-tf-state-bucket"
    key          = "prod/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 8.0"
    }
  }
}

# 原生单元测试示例 (tests/vpc_unit_test.tftest.hcl)
run "rejects_invalid_cidr" {
  command = plan
  variables {
    vpc_cidr = "invalid"
  }
  expect_failures = [var.vpc_cidr]
}
```

## 边界与限制
- **循环依赖**: 两个资源互相引用会导致 Deadlock，通常通过引入中间层或拆分模块解决。
- **大规模状态**: 单个状态文件过大（数千个资源）会导致 Plan 速度极慢，此时应按功能域或环境拆分为多个 Workspace/State。
- **API 速率限制**: 调整 CI 频率与并发以减少 API 请求。漂移检测保留 refresh；`-refresh=false` 仅用于明确不检查实时状态的离线或特殊计划，不能据此宣称已检测漂移。
- **Provider 升级**: 仅在升级任务中使用 `terraform init -upgrade`，审查 lockfile 与计划差异后再应用。
- **Secrets 管理**: 状态文件中普通变量与资源属性仍为明文，优先集成 Secret Manager 与 Terraform 1.11+ `ephemeral` 资源及 write-only（`*_wo`）属性，避免将凭据写入 state；为所有变量与输出标注 `sensitive = true` / `type` / `description`。
- **应用层配置**: Terraform 擅长“修路”，不擅长“开车”。对于应用内部复杂的配置文件、用户账号管理等，应结合 Ansible 或云原生初始化脚本（Cloud-init）。
