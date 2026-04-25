# Terraform Module Templates

Purpose: Use this file when you need Terraform layout, module boundaries, backend configuration, or reusable AWS-first module patterns.

Contents:
1. Recommended repository layout
2. Module design rules
3. Backend patterns
4. Minimal module skeletons

## Recommended Repository Layout

```text
modules/
  vpc/
  rds/
  ecs/
environments/
  dev/
  staging/
  prod/
```

## Module Design Rules

- Root module owns providers, backend, and environment wiring.
- Child modules own one responsibility only.
- `required_version` should be `>= 1.5.0`.
- Pin providers with bounded constraints such as `~> 5.0`.
- Validate user-facing variables.
- Expose only necessary outputs.
- Merge common tags/labels centrally.

## Backend Patterns

| Backend | Use when | Notes |
|---------|----------|-------|
| S3 + DynamoDB | AWS Terraform teams | encryption + locking required |
| GCS | GCP Terraform teams | separate bucket prefix per environment |
| Azure Blob | Azure Terraform teams | isolate by container/key |

Example:

```hcl
terraform {
  backend "s3" {
    bucket         = "myproject-terraform-state"
    key            = "dev/terraform.tfstate"
    region         = "ap-northeast-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

## Minimal Module Skeleton

### VPC-style module

```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
```

### Variable validation

```hcl
variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}
```

### Outputs

```hcl
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}
```
